"""
Flask extension for rapid GitHub app development
"""
import os.path
import hmac
import logging
import distutils

from flask import abort, current_app, jsonify, request, _app_ctx_stack
from github3 import GitHub, GitHubEnterprise

LOG = logging.getLogger(__name__)

STATUS_FUNC_CALLED = "HIT"
STATUS_NO_FUNC_CALLED = "MISS"


class GitHubApp(object):
    """
    The GitHubApp object provides the central interface for interacting GitHub hooks
    and creating GitHub app clients.

    GitHubApp object allows using the "on" decorator to make GitHub hooks to functions
    and provides authenticated github3.py clients for interacting with the GitHub API.

    Keyword Arguments:
        app {Flask object} -- App instance - created with Flask(__name__) (default: {None})
    """

    def __init__(self, app=None):
        self._hook_mappings = {}
        if app is not None:
            self.init_app(app)

    @staticmethod
    def load_env(app):
        app.config["GITHUBAPP_ID"] = int(os.environ["APP_ID"])
        app.config["GITHUBAPP_SECRET"] = os.environ["WEBHOOK_SECRET"]
        if "GHE_HOST" in os.environ:
            app.config["GITHUBAPP_URL"] = "https://{}".format(os.environ["GHE_HOST"])
            app.config["VERIFY_SSL"] = bool(
                distutils.util.strtobool(os.environ.get("VERIFY_SSL", "false"))
            )
        with open(os.environ["PRIVATE_KEY_PATH"], "rb") as key_file:
            app.config["GITHUBAPP_KEY"] = key_file.read()

    def init_app(self, app):
        """
        Initializes GitHubApp app by setting configuration variables.

        The GitHubApp instance is given the following configuration variables by calling on Flask's configuration:

        `GITHUBAPP_ID`:

            GitHub app ID as an int (required).
            Default: None

        `GITHUBAPP_KEY`:

            Private key used to sign access token requests as bytes or utf-8 encoded string (required).
            Default: None

        `GITHUBAPP_SECRET`:

            Secret used to secure webhooks as bytes or utf-8 encoded string (required).
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
            if not app.config.get(setting):
                raise RuntimeError(
                    "Flask-GitHubApp requires the '%s' config var to be set" % setting
                )

        app.add_url_rule(
            app.config.get("GITHUBAPP_ROUTE", "/"),
            view_func=self._flask_view_func,
            methods=["POST"],
        )

        app.add_url_rule("/health_check", endpoint="health_check")
        @app.endpoint("health_check")
        def health_check():
            return "Web server is running.", 200

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
    def client(self):
        """Unauthenticated GitHub client"""
        if current_app.config.get("GITHUBAPP_URL"):
            return GitHubEnterprise(
                current_app.config["GITHUBAPP_URL"],
                verify=current_app.config["VERIFY_SSL"],
            )
        return GitHub()

    @property
    def payload(self):
        """GitHub hook payload"""
        if request and request.json and "installation" in request.json:
            return request.json

        raise RuntimeError(
            "Payload is only available in the context of a GitHub hook request"
        )

    @property
    def installation_client(self):
        """GitHub client authenticated as GitHub app installation"""
        ctx = _app_ctx_stack.top
        if ctx is not None:
            if not hasattr(ctx, "githubapp_installation"):
                client = self.client
                client.login_as_app_installation(
                    self.key, self.id, self.payload["installation"]["id"]
                )
                ctx.githubapp_installation = client
            return ctx.githubapp_installation

    @property
    def app_client(self):
        """GitHub client authenticated as GitHub app"""
        ctx = _app_ctx_stack.top
        if ctx is not None:
            if not hasattr(ctx, "githubapp_app"):
                client = self.client
                client.login_as_app(self.key, self.id)
                ctx.githubapp_app = client
            return ctx.githubapp_app

    @property
    def installation_token(self):
        """

        :return:
        """
        return self.installation_client.session.auth.token

    def app_installation(self, installation_id=None):
        """
        Login as installation when triggered on a non-webhook event.
        This is necessary for scheduling tasks
        :param installation_id:
        :return:
        """
        """GitHub client authenticated as GitHub app installation"""
        ctx = _app_ctx_stack.top
        if installation_id is None:
            raise RuntimeError("Installation ID is not specified.")
        if ctx is not None:
            if not hasattr(ctx, "githubapp_installation"):
                client = self.client
                client.login_as_app_installation(self.key, self.id, installation_id)
                ctx.githubapp_installation = client
            return ctx.githubapp_installation

    def on(self, event_action):
        """
        Decorator routes a GitHub hook to the wrapped function.

        Functions decorated as a hook recipient are registered as the function for the given GitHub event.

        @github_app.on('issues.opened')
        def cruel_closer():
            owner = github_app.payload['repository']['owner']['login']
            repo = github_app.payload['repository']['name']
            num = github_app.payload['issue']['id']
            issue = github_app.installation_client.issue(owner, repo, num)
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

    def _flask_view_func(self):
        functions_to_call = []
        calls = {}

        event = request.headers["X-GitHub-Event"]
        action = request.json.get("action")

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
        hub_signature = "X-HUB-SIGNATURE"
        if hub_signature not in request.headers:
            LOG.warning("Github Hook Signature not found.")
            abort(400)

        signature = request.headers[hub_signature].split("=")[1]

        mac = hmac.new(self.secret, msg=request.data, digestmod="sha1")

        if not hmac.compare_digest(mac.hexdigest(), signature):
            LOG.warning("GitHub hook signature verification failed.")
            abort(400)
