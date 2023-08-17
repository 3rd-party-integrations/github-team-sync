import asyncio
import os
import logging
import re
from okta.client import Client as OktaClient


LOG = logging.getLogger(__name__)


class Okta:
    def __init__(self):
        self.USERNAME_ATTRIBUTE = os.environ.get("OKTA_USERNAME_ATTRIBUTE", "login")
        auth_method = os.environ.get("OKTA_AUTH_METHOD", "token")
        config = {"orgUrl": os.environ["OKTA_ORG_URL"]}
        if auth_method == "oauth":
            config["authorizationMode"] = "PrivateKey"
            config["clientId"] = os.environ["OKTA_CLIENT_ID"]
            config["scopes"] = os.environ["OKTA_SCOPES"].split(" ")
            config["privateKey"] = os.environ["OKTA_PRIVATE_KEY"]
        else:
            config["token"] = os.environ["OKTA_ACCESS_TOKEN"]
        self.client = OktaClient(config)

    def get_group_members(self, group_name=None):
        """
        Get a list of users that are part of a given group in Okta
        :param group_name: Group name to look up
        :type group_name: str
        :return member_list: A list of dictionaries containing usernames and emails
        :rtype member_list: list
        """
        member_list = []

        async def get_group_id(client=None):
            """
            Get the group ID
            :return:
            """
            group = await client.list_groups(query_params={"q": group_name})
            return group[0][0].id

        async def get_members(client=None, groupId=None):
            """
            Get the users that belong to this group
            :param groupId:
            :return:
            """
            members = await client.list_group_users(groupId=groupId)
            return members[0]

        def get_or_create_eventloop():
            """
            Create an async loop if we're in a child thread
            :return:
            """
            try:
                return asyncio.get_event_loop()
            except RuntimeError as ex:
                if "There is no current event loop in thread" in str(ex):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    return asyncio.get_event_loop()

        loop = get_or_create_eventloop()
        gid = loop.run_until_complete(get_group_id(client=self.client))
        users = loop.run_until_complete(get_members(client=self.client, groupId=gid))
        for user in users:
            try:
                username = getattr(user.profile, self.USERNAME_ATTRIBUTE)
                username = username.split("@")[0]
                username = re.sub("[^0-9a-zA-Z-]+", "-", username)
                if "EMU_SHORTCODE" in os.environ:
                    username = username + "_" + os.environ["EMU_SHORTCODE"]
                member_list.append(
                    {
                        "username": username,
                        "email": user.profile.email,
                    }
                )
            except AttributeError as e:
                if user.links:
                    user_info = user.links["self"]["href"]
                else:
                    user_info = user
                print(f"User {user_info}: {e}")
        return member_list
