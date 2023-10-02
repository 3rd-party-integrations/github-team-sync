"""
Flask extension for rapid GitHub app development
"""
import hmac
import time
import logging
import requests
import jwt

from flask import abort, current_app, jsonify, make_response, request, _app_ctx_stack
from distutils.util import strtobool
from os import environ
from ghapi.all import GhApi


LOG = logging.getLogger(__name__)

STATUS_FUNC_CALLED = "HIT"
STATUS_NO_FUNC_CALLED = "MISS"


class GitHubAppError(Exception):
    pass


class GitHubAppValidationError(Exception):
    pass


class GitHubAppBadCredentials(Exception):
    pass


class GithubUnauthorized(Exception):
    pass


class GithubAppUnkownObject(Exception):
    pass


class InstallationAuthorization:
    """
    This class represents InstallationAuthorizations
    """

    def __init__(self, token, expires_at):
        self.token = token
        self.expires_at = expires_at

    def token(self):
        return self._token

    def expires_at(self):
        return self._expires_at

    def expired(self):
        if self.expires_at:
            return time.time() > self.expires_at
        return False


class GitHubApp(object):
    """The GitHubApp object provides the central interface for interacting GitHub hooks
    and creating GitHub app clients.

    GitHubApp object allows using the "on" decorator to make GitHub hooks to functions
    and provides authenticated github3.py clients for interacting with the GitHub API.

    Keyword Arguments:
        app {Flask object} -- App instance - created with Flask(__name__) (default: {None})
    """

    def __init__(self, app=None):
        self._hook_mappings = {}
        self._access_token = None
        if app is not None:
            self.init_app(app)

    @staticmethod
    def load_env(app):
        app.config["GITHUBAPP_ID"] = int(environ["APP_ID"])
        app.config["GITHUBAPP_SECRET"] = environ["WEBHOOK_SECRET"]
        if "GHE_HOST" in environ:
            app.config["GITHUBAPP_URL"] = "https://{}".format(environ["GHE_HOST"])
            app.config["VERIFY_SSL"] = bool(
                strtobool(environ.get("VERIFY_SSL", "false"))
            )
        with open(environ["PRIVATE_KEY_PATH"], "rb") as key_file:
            app.config["GITHUBAPP_KEY"] = key_file.read()

    def init_app(self, app):
        """Initializes GitHubApp app by setting configuration variables.

        The GitHubApp instance is given the following configuration variables by calling on Flask's configuration:

        `GITHUBAPP_ID`:

            GitHub app ID as an int (required).
            Default: None

        `GITHUBAPP_KEY`:

            Private key used to sign access token requests as bytes or utf-8 encoded string (required).
            Default: None

        `GITHUBAPP_SECRET`:

            Secret used to secure webhooks as bytes or utf-8 encoded string (required). set to `False` to disable
            verification (not recommended for production).
            Default: None

        `GITHUBAPP_URL`:

            URL of GitHub API (used for GitHub Enterprise) as a string.
            Default: None

        `GITHUBAPP_ROUTE`:

            Path used for GitHub hook requests as a string.
            Default: '/'
        """
        self.load_env(app)
        required_settings = ["GITHUBAPP_ID", "GITHUBAPP_KEY", "GITHUBAPP_SECRET"]
        for setting in required_settings:
            if not setting in app.config:
                raise RuntimeError(
                    "Flask-GitHubApplication requires the '%s' config var to be set"
                    % setting
                )

        if app.config.get("GITHUBAPP_URL"):
            self.base_url = app.config.get("GITHUBAPP_URL")
        else:
            self.base_url = "https://api.github.com"

        app.add_url_rule(
            app.config.get("GITHUBAPP_ROUTE", "/"),
            view_func=self._flask_view_func,
            methods=["POST"],
        )

    @property
    def id(self):
        return current_app.config["GITHUBAPP_ID"]

    @property
    def key(self):
        key = current_app.config["GITHUBAPP_KEY"]
        if hasattr(key, "encode"):
            key = key.encode("utf-8")
        return key

    @property
    def secret(self):
        secret = current_app.config["GITHUBAPP_SECRET"]
        if hasattr(secret, "encode"):
            secret = secret.encode("utf-8")
        return secret

    @property
    def _api_url(self):
        return current_app.config["GITHUBAPP_URL"]

    @property
    def payload(self):
        """GitHub hook payload"""
        if request and request.json and "installation" in request.json:
            return request.json

        raise RuntimeError(
            "Payload is only available in the context of a GitHub hook request"
        )

    @property
    def installation_token(self):
        return self._access_token

    def client(self, installation_id=None):
        """GitHub client authenticated as GitHub app installation"""
        ctx = _app_ctx_stack.top
        if ctx is not None:
            if not hasattr(ctx, "githubapp_installation"):
                if installation_id is None:
                    installation_id = self.payload["installation"]["id"]
                self._access_token = self.get_access_token(installation_id).token
                ctx.githubapp_installation = GhApi(token=self._access_token)
            return ctx.githubapp_installation

    def _create_jwt(self, expiration=60):
        """
        Creates a signed JWT, valid for 60 seconds by default.
        The expiration can be extended beyond this, to a maximum of 600 seconds.
        :param expiration: int
        :return string:
        """
        now = int(time.time())
        payload = {"iat": now, "exp": now + expiration, "iss": self.id}
        encrypted = jwt.encode(payload, key=self.key, algorithm="RS256")

        if isinstance(encrypted, bytes):
            encrypted = encrypted.decode("utf-8")
        return encrypted

    def get_access_token(self, installation_id, user_id=None):
        """
        Get an access token for the given installation id.
        POSTs https://api.github.com/app/installations/<installation_id>/access_tokens
        :param user_id: int
        :param installation_id: int
        :return: :class:`github.InstallationAuthorization.InstallationAuthorization`
        """
        body = {}
        if user_id:
            body = {"user_id": user_id}
        response = requests.post(
            f"{self.base_url}/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {self._create_jwt()}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Flask-GithubApplication/Python",
            },
            json=body,
        )
        if response.status_code == 201:
            return InstallationAuthorization(
                token=response.json()["token"], expires_at=response.json()["expires_at"]
            )
        elif response.status_code == 403:
            raise GitHubAppBadCredentials(
                status=response.status_code, data=response.text
            )
        elif response.status_code == 404:
            raise GithubAppUnkownObject(status=response.status_code, data=response.text)
        raise Exception(status=response.status_code, data=response.text)

    def list_installations(self, per_page=30, page=1):
        """
        GETs https://api.github.com/app/installations
        :return: :obj: `list` of installations
        """
        params = {"page": page, "per_page": per_page}

        response = requests.get(
            f"{self.base_url}/app/installations",
            headers={
                "Authorization": f"Bearer {self._create_jwt()}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Flask-GithubApplication/python",
            },
            params=params,
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            raise GithubUnauthorized(status=response.status_code, data=response.text)
        elif response.status_code == 403:
            raise GitHubAppBadCredentials(
                status=response.status_code, data=response.text
            )
        elif response.status_code == 404:
            raise GithubAppUnkownObject(status=response.status_code, data=response.text)
        raise Exception(status=response.status_code, data=response.text)

    def on(self, event_action):
        """Decorator routes a GitHub hook to the wrapped function.

        Functions decorated as a hook recipient are registered as the function for the given GitHub event.

        @github_app.on('issues.opened')
        def cruel_closer():
            owner = github_app.payload['repository']['owner']['login']
            repo = github_app.payload['repository']['name']
            num = github_app.payload['issue']['id']
            issue = github_app.client.issue(owner, repo, num)
            issue.create_comment('Could not replicate.')
            issue.close()

        Arguments:
            event_action {str} -- Name of the event and optional action (separated by a period), e.g. 'issues.opened' or
                'pull_request'
        """

        def decorator(f):
            if event_action not in self._hook_mappings:
                self._hook_mappings[event_action] = [f]
            else:
                self._hook_mappings[event_action].append(f)

            # make sure the function can still be called normally (e.g. if a user wants to pass in their
            # own Context for whatever reason).
            return f

        return decorator

    def _validate_request(self):
        if not request.is_json:
            raise GitHubAppValidationError(
                "Invalid HTTP Content-Type header for JSON body "
                "(must be application/json or application/*+json)."
            )
        try:
            request.json
        except BadRequest:
            raise GitHubAppValidationError("Invalid HTTP body (must be JSON).")

        event = request.headers.get("X-GitHub-Event")

        if event is None:
            raise GitHubAppValidationError("Missing X-GitHub-Event HTTP header.")

        action = request.json.get("action")

        return event, action

    def _flask_view_func(self):
        functions_to_call = []
        calls = {}

        try:
            event, action = self._validate_request()
        except GitHubAppValidationError as e:
            LOG.error(e)
            error_response = make_response(
                jsonify(status="ERROR", description=str(e)), 400
            )
            return abort(error_response)

        if current_app.config["GITHUBAPP_SECRET"] is not False:
            self._verify_webhook()

        if event in self._hook_mappings:
            functions_to_call += self._hook_mappings[event]

        if action:
            event_action = ".".join([event, action])
            if event_action in self._hook_mappings:
                functions_to_call += self._hook_mappings[event_action]

        if functions_to_call:
            for function in functions_to_call:
                calls[function.__name__] = function()
            status = STATUS_FUNC_CALLED
        else:
            status = STATUS_NO_FUNC_CALLED
        return jsonify({"status": status, "calls": calls})

    def _verify_webhook(self):
        signature_header = "X-Hub-Signature-256"
        signature_header_legacy = "X-Hub-Signature"

        if request.headers.get(signature_header):
            signature = request.headers[signature_header].split("=")[1]
            digestmod = "sha256"
        elif request.headers.get(signature_header_legacy):
            signature = request.headers[signature_header_legacy].split("=")[1]
            digestmod = "sha1"
        else:
            LOG.warning(
                "Signature header missing. Configure your GitHub App with a secret or set GITHUBAPP_SECRET"
                "to False to disable verification."
            )
            return abort(400)

        mac = hmac.new(self.secret, msg=request.data, digestmod=digestmod)

        if not hmac.compare_digest(mac.hexdigest(), signature):
            LOG.warning("GitHub hook signature verification failed.")
            return abort(400)
