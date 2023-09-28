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
        self.AZURE_USER_IS_UPN = strtobool(os.environ.get("AZURE_USER_IS_UPN", "False"))
        self.AZURE_USE_TRANSITIVE_GROUP_MEMBERS = strtobool(
            os.environ.get("AZURE_USE_TRANSITIVE_GROUP_MEMBERS", "False")
        )

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
            f"{self.AZURE_API_ENDPOINT}/groups?$filter=displayName eq '{group_name}'",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        # print("Graph API call result: %s" % json.dumps(graph_data, indent=2))
        try:
            group_info = json.loads(json.dumps(graph_data, indent=2))["value"][0]
            members_endpoint = (
                "transitiveMembers"
                if self.AZURE_USE_TRANSITIVE_GROUP_MEMBERS
                else "members"
            )
            members = self.get_group_members_pages(
                token,
                f'{self.AZURE_API_ENDPOINT}/groups/{group_info["id"]}/{members_endpoint}',
            )
        except IndexError as e:
            members = []
        for member in members:
            if member["@odata.type"] == "#microsoft.graph.group":
                print("Nested group: ", member["displayName"])
            else:
                user_info = self.get_user_info(token=token, user=member["id"])
                if self.USERNAME_ATTRIBUTE.startswith("extensionAttribute"):
                    username = user_info["onPremisesExtensionAttributes"][
                        self.USERNAME_ATTRIBUTE
                    ]
                    if username is None:
                        continue
                else:
                    username = user_info[self.USERNAME_ATTRIBUTE]
                if self.AZURE_USER_IS_UPN:
                    if r"\\" in username:
                        username = username.split(r"\\")[1]
                    username = username.split("@")[0].split("#")[0].split("_")[0]
                    username = username.translate(str.maketrans("._!#^~", "------"))
                    username = username.lower()
                if "EMU_SHORTCODE" in os.environ:
                    username = username + "_" + os.environ["EMU_SHORTCODE"]
                user = {
                    "username": username,
                    "email": user_info["mail"],
                }
                member_list.append(user)
        return member_list

    def get_group_members_pages(self, token=None, url=None):
        """
        Get group members
        :param token:
        :param url:
        :return members:
        :rtype members: dict
        """
        members_data = requests.get(url, headers={"Authorization": f"Bearer {token}"})
        if members_data.ok != True:
            print(
                f"[GetMembers]: Error getting members data error code {members_data.status_code}"
            )
            return []

        members_data_content = members_data.json()
        members = members_data_content["value"]
        if "@odata.nextLink" in members_data_content:
            members.extend(
                self.get_group_members_pages(
                    token, members_data_content["@odata.nextLink"]
                )
            )
        return members

    def get_user_info(self, token=None, user=None):
        """
        Get user info
        :param token:
        :param user:
        :return user_info:
        :rtype user_info: dict
        """
        token = self.get_access_token() if not token else token
        attribute = self.USERNAME_ATTRIBUTE
        if self.USERNAME_ATTRIBUTE.startswith("extensionAttribute"):
            attribute = "onPremisesExtensionAttributes"
        graph_data = requests.get(  # Use token to call downstream service
            f"{self.AZURE_API_ENDPOINT}/users/{user}?$select=id,mail,{attribute}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        user_info = json.loads(json.dumps(graph_data, indent=2))
        return user_info
