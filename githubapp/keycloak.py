import collections
import os
import logging
import threading
from keycloak import KeycloakAdmin
from . import urls_patterns
from .exceptions import (
    KeycloakGetError,
    raise_error_from_response,
)

LOG = logging.getLogger(__name__)


class Keycloak:
    _shared_client = None
    _lock = threading.Lock()
    PAGE_SIZE = 100

    def __init__(self):
        self.UseGithubIDP = os.environ.get("KEYCLOAK_USE_GITHUB_IDP", "true") == "true"

        with Keycloak._lock:
            if Keycloak._shared_client is not None:
                self.client = Keycloak._shared_client
                return

            self._init_client()
            Keycloak._shared_client = self.client

    def _init_client(self):

        if not os.environ.get("KEYCLOAK_SERVER_URL", None):
            raise Exception("KEYCLOAK_SERVER_URL not defined")

        if not os.environ.get("KEYCLOAK_USERNAME", None):
            raise Exception("KEYCLOAK_USERNAME not defined")

        if not os.environ.get("KEYCLOAK_PASSWORD", None):
            raise Exception("KEYCLOAK_PASSWORD not defined")

        if not os.environ.get("KEYCLOAK_REALM"):
            os.environ["KEYCLOAK_REALM"] = "master"
        
        if not os.environ.get("KEYCLOAK_ADMIN_REALM"):
            os.environ["KEYCLOAK_ADMIN_REALM"] = os.environ.get("KEYCLOAK_REALM")

        self.client = KeycloakAdmin(
            server_url=os.environ["KEYCLOAK_SERVER_URL"],
            username=os.environ["KEYCLOAK_USERNAME"],
            password=os.environ["KEYCLOAK_PASSWORD"],
            realm_name=os.environ["KEYCLOAK_REALM"],
            user_realm_name=os.environ["KEYCLOAK_ADMIN_REALM"],
            auto_refresh_token=["get", "put", "post", "delete"],
        )
    def __fetch_paginated(self, url, query=None):
        """Make a specific paginated request.

        :param url: The url on which the query is executed
        :type url: str
        :param query: Pagination settings
        :type query: dict
        :returns: Response
        :rtype: dict
        """
        query = query or {}
        return raise_error_from_response(self.client.connection.raw_get(url, **query), KeycloakGetError)
    

    def __fetch_all(self, url, query=None):
        """Paginate over get requests.

        Wrapper function to paginate GET requests.

        :param url: The url on which the query is executed
        :type url: str
        :param query: Existing query parameters (optional)
        :type query: dict

        :return: Combined results of paginated queries
        :rtype: list
        """
        results = []

        # initialize query if it was called with None
        if not query:
            query = {}
        page = 0
        query["max"] = self.PAGE_SIZE

        # fetch until we can
        while True:
            query["first"] = page * self.PAGE_SIZE
            partial_results = raise_error_from_response(
                self.client.connection.raw_get(url, **query), KeycloakGetError
            )
            if not partial_results:
                break
            results.extend(partial_results)
            if len(partial_results) < query["max"]:
                break
            page += 1
        return results

    def get_group_members(self, group_name: str = None):
        """
        Get a list of users that are in a group in Keycloak

        :param group_name: Group name to look up
        :type group_name: str

        :return member_list: A list of dictionaries containing usernames and email
        s
        :rtype member_list: list
        """
        member_list = []

        def get_group_id(client: KeycloakAdmin = None, group_name: str = None):
            """
            Get the UUID of the provided group from Keycloak

            :param client: A KeycloakAdmin client

            :return: The group's UUID in Keycloak
            """

            group = client.get_groups(query={"search": group_name, "exact": True, "populateHierarchy": False, "briefRepresentation": True})
            if not group:
                print(f"Cannot find group {group_name} in Keycloak")
                return ""
            else:
                return group[0]["id"]

        def get_members(client: KeycloakAdmin = None, group_id: str = None):
            """
            Get the users that are in this group

            :param client: A KeycloakAdmin client
            :param group_id: The group's UUID in Keycloak

            :return: A list containing all users in the group
            """
            # Keycloak paginates the response when grabbing the list of members
            # The response doesn't contain any info on the next page either
            # Therefore, we'll need to iterate over the pages until the returned
            # list is smaller than the provided page size
            page_start = 0
            page_size = 100
            members = []
            group_members = client.get_group_members(
                group_id=group_id,
                query={"first": page_start, "max": page_size}
            )
            members += group_members
            while len(group_members) == page_size:
                page_start += page_size
                group_members = client.get_group_members(
                    group_id=group_id,
                    query={"first": page_start, "max": page_size}
                )
                members += group_members
            return members

        def get_github_username(client: KeycloakAdmin = None, user_id: str = None):
            """
            Gets the GitHub username from the user's Keycloak profile
            This only works if the Keycloak realm has GitHub set up
            as an Identity provider.

            :param client: A KeycloakAdmin client
            :param user_id: The user's UUID in Keycloak

            :return: The user's GitHub username
            """
            profile = client.get_user(user_id=user_id)
            github_username = None
            for provider in profile["federatedIdentities"]:
                if provider["identityProvider"] == "github":
                    github_username = provider["userName"]
            if not github_username:
                raise Exception("Cannot find Github username")
            return github_username

        gid = get_group_id(client=self.client, group_name = group_name)
        if gid == "":
            return []
        users: collections.Iterable = get_members(client=self.client, group_id=gid)
        for user in users:
            try:
                if self.UseGithubIDP:
                    username = get_github_username(client=self.client, user_id=user["id"])
                else:
                    username = user["username"]
                    if not username:
                        raise Exception("Unable to find username in profile")
                    if "EMU_SHORTCODE" in os.environ:
                        username = username + "_" + os.environ["EMU_SHORTCODE"]
                member_list.append(
                    {
                        "username": username,
                        "email": user["email"],
                        "email_slug": user["email"].split("@")[0].lower()
                    }
                )
            except Exception as e:
                user_info = f'{user["username"]} ({user["email"]})'
                print(f"User {user_info}: {e}")
        return member_list

    def get_group_children(self, group_id, query=None):
        query = query or {}
        params_path = {"realm-name": self.client.connection.realm_name, "id": group_id}
        url = urls_patterns.URL_ADMIN_GROUP_CHILD.format(**params_path)
        if "first" in query or "max" in query:
            groups = self.__fetch_paginated(url, query)
        groups = self.__fetch_all(url, query)

        return groups



    def list_groups(self):
        """
        List all groups in Keycloak under the configured parent group.
        """
        group_id = os.environ.get("KEYCLOAK_PARENT_GROUP_ID")
        if not group_id:
            return []
        group = self.client.get_group(group_id)
        # populate subgroups
        if group.get("subGroupCount"):
            group["subGroups"] = self.get_group_children(group.get("id"), query={'max':1000})
        # print(group)
        # return group.get("subGroups", [])
        names = []
        stack = list(group.get("subGroups", []))
        print(stack)
        while stack:
            g = stack.pop()
            names.append(g.get("name"))
            local_subGroups = self.get_group_children(g.get("id"), {})
            if local_subGroups:
                stack.extend(local_subGroups)
        return names


