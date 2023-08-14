from onelogin.api.client import OneLoginClient
import os


class OneLogin:
    def __init__(self):
        CLIENT_ID = os.environ["ONELOGIN_CLIENT_ID"]
        CLIENT_SECRET = os.environ["ONELOGIN_CLIENT_SECRET"]
        REGION = os.environ.get("ONELOGIN_REGION", "US").upper()
        self.client = OneLoginClient(CLIENT_ID, CLIENT_SECRET, REGION)

    def get_group_members(self, group_name=None):
        """
        This is technically not named well, since we're getting users assigned to a role, but
        because of the existing framework, the matching the function name keeps it reusable
        :param group_name:
        :return:
        """
        member_list = []
        role = self.client.get_roles(query_parameters={"name": group_name})
        users = self.client.get_users(query_parameters={"role_id": role[0].id})
        for user in users:
            if "EMU_SHORTCODE" in os.environ:
                username = user.username + "_" + os.environ["EMU_SHORTCODE"]
            else:
                username = user.username
            member_list.append({"username": username, "email": user.email})

        return member_list
