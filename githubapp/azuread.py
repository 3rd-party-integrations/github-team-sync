import os
import json
import logging
from distutils.util import strtobool
import requests
import msal

# Optional logging
# logging.basicConfig(level=logging.DEBUG)  # Enable DEBUG log for entire script
# logging.getLogger("msal").setLevel(logging.INFO)  # Optionally disable MSAL DEBUG logs

LOG = logging.getLogger(__name__)


class AzureAD:
    def __init__(self):
        self.AZURE_TENANT_ID = os.environ["AZURE_TENANT_ID"]
        self.AZURE_CLIENT_ID = os.environ["AZURE_CLIENT_ID"]
        self.AZURE_CLIENT_SECRET = os.environ["AZURE_CLIENT_SECRET"]
        self.AZURE_APP_SCOPE = [
            f"https://graph.microsoft.com/{x}"
            for x in os.environ["AZURE_APP_SCOPE"].split(" ")
        ]
        self.AZURE_API_ENDPOINT = os.environ.get(
            "AZURE_API_ENDPOINT", "https://graph.microsoft.com/v1.0"
        )
        self.USERNAME_ATTRIBUTE = os.environ.get(
            "AZURE_USERNAME_ATTRIBUTE", "userPrincipalName"
        )
        self.AZURE_USER_IS_UPN = strtobool(
            os.environ.get("AZURE_USER_IS_UPN", "False"))

    def get_access_token(self):
        """
        Get the access token for this Azure Service Principal
        :return access_token:
        """
        app = msal.ConfidentialClientApplication(
            self.AZURE_CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{self.AZURE_TENANT_ID}",
            client_credential=self.AZURE_CLIENT_SECRET,
        )

        # Lookup the token in cache
        result = app.acquire_token_silent(self.AZURE_APP_SCOPE, account=None)

        if not result:
            logging.info(
                "No suitable token exists in cache. Let's get a new one from AAD."
            )
            result = app.acquire_token_for_client(scopes=self.AZURE_APP_SCOPE)

        if "access_token" in result:
            # print("Successfully authenticated!")
            return result["access_token"]

        else:
            print(result.get("error"))
            print(result.get("error_description"))
            print(
                result.get("correlation_id")
            )  # You may need this when reporting a bug

    def get_group_members(self, token=None, group_name=None):
        """
        Get a list of members for a given group
        :param token:
        :param group_name:
        :return:
        """
        token = self.get_access_token() if not token else token
        member_list = []
        # Calling graph using the access token
        # url encode the group name
        group_name = requests.utils.quote(group_name)
        graph_data = requests.get(  # Use token to call downstream service
            f"{self.AZURE_API_ENDPOINT}/groups?$filter=startswith(displayName,'{group_name}')",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        # print("Graph API call result: %s" % json.dumps(graph_data, indent=2))
        try:
            group_info = json.loads(json.dumps(
                graph_data, indent=2))["value"][0]
            members = requests.get(
                f'{self.AZURE_API_ENDPOINT}/groups/{group_info["id"]}/members',
                headers={"Authorization": f"Bearer {token}"},
            ).json()["value"]
        except IndexError as e:
            members = []
        for member in members:
            user_info = self.get_user_info(token=token, user=member["id"])
            if self.AZURE_USER_IS_UPN:
                user = {
                    "username": user_info[self.USERNAME_ATTRIBUTE].split("@")[0],
                    "email": user_info["mail"],
                }
            else:
                user = {
                    "username": user_info[self.USERNAME_ATTRIBUTE],
                    "email": user_info["mail"],
                }
            member_list.append(user)
        return member_list

    def get_user_info(self, token=None, user=None):
        """
        Get user info
        :param token:
        :param user:
        :return user_info:
        :rtype user_info: dict
        """
        token = self.get_access_token() if not token else token
        graph_data = requests.get(  # Use token to call downstream service
            f"{self.AZURE_API_ENDPOINT}/users/{user}?$select=id,mail,{self.USERNAME_ATTRIBUTE}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        user_info = json.loads(json.dumps(graph_data, indent=2))
        return user_info
