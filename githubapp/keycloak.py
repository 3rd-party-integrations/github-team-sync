import asyncio
import collections
import os
import logging
import re
from keycloak import KeycloakAdmin


LOG = logging.getLogger(__name__)


class Keycloak:
    def __init__(self):
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

        self.UseGithubIDP = os.environ.get("KEYCLOAK_USE_GITHUB_IDP", "true") == "true"

        self.client = KeycloakAdmin(
            server_url=os.environ["KEYCLOAK_SERVER_URL"],
            username=os.environ["KEYCLOAK_USERNAME"],
            password=os.environ["KEYCLOAK_PASSWORD"],
            realm_name=os.environ["KEYCLOAK_REALM"],
            user_realm_name=os.environ["KEYCLOAK_ADMIN_REALM"]
        )

    def get_group_members(self, group_name: str = None):
        """
        Get a list of users that are in a group in Keycloak

        :param group_name: Group name to look up
        :type group_name: str

        :return member_list: A list of dictionaries containing usernames and emails
        :rtype member_list: list
        """
        member_list = []

        def get_group_id(client: KeycloakAdmin = None):
            """
            Get the UUID of the provided group from Keycloak

            :param client: A KeycloakAdmin client

            :return: The group's UUID in Keycloak
            """

            group = client.get_groups(query={"search": group_name, "briefRepresentation": "true", "exact": "true"})
            if not group:
                raise Exception(f"Cannot find group {group_name} in Keycloak")
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

        gid = get_group_id(client=self.client)
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
                        "email": user["email"]
                    }
                )
            except Exception as e:
                user_info = f'{user["username"]} ({user["email"]})'
                print(f"User {user_info}: {e}")
        return member_list
