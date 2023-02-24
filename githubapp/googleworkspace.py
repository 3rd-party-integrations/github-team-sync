import os
import traceback
import sys
import json
import logging
from google.oauth2 import service_account
import googleapiclient.discovery
from pprint import pprint

LOG = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/admin.directory.group.readonly',
    'https://www.googleapis.com/auth/admin.directory.group.member.readonly',
    'https://www.googleapis.com/auth/admin.directory.user.readonly'
]


class GOOGLE_WORKSPACEClient:
    def __init__(self):
        # Read settings from the config file and store them as constants
        self.GOOGLE_WORKSPACE_SA_CREDS_FILE = os.environ["GOOGLE_WORKSPACE_SA_CREDS_FILE"]
        self.GOOGLE_WORKSPACE_ADMIN_EMAIL = os.environ["GOOGLE_WORKSPACE_ADMIN_EMAIL"]
        self.GOOGLE_WORKSPACE_USER_MAIL_ATTRIBUTE = os.environ.get(
            "GOOGLE_WORKSPACE_USER_MAIL_ATTRIBUTE", "primaryEmail")
        self.GOOGLE_WORKSPACE_USERNAME_СUSTOM_SCHEMA_NAME = os.environ.get(
            "GOOGLE_WORKSPACE_СUSTOM_SCHEMA_NAME")
        self.GOOGLE_WORKSPACE_USERNAME_FIELD = os.environ.get(
            "GOOGLE_WORKSPACE_USERNAME_FIELD")
        self.USER_SYNC_ATTRIBUTE = os.environ["USER_SYNC_ATTRIBUTE"]

        credentials = service_account.Credentials.from_service_account_file(self.GOOGLE_WORKSPACE_SA_CREDS_FILE, scopes=SCOPES)
        delegated_credentials = credentials.with_subject(self.GOOGLE_WORKSPACE_ADMIN_EMAIL)
        self.service = googleapiclient.discovery.build(
            'admin',
            'directory_v1',
            credentials=delegated_credentials)

    def get_group_members(self, group_name):
        """
        Get members of the requested group in GOOGLE_WORKSPACE/Active Directory
        :param group_name: The name of the group
        :type group_name: str
        :return member_list: List of members found in this GOOGLE_WORKSPACE group
        :rtype member_list: list
        """
        # member_list = []
        # entries = self.conn.extend.standard.paged_search(
        #     search_base=self.GOOGLE_WORKSPACE_BASE_DN,
        #     search_filter=self.GOOGLE_WORKSPACE_GROUP_FILTER.replace(
        #         "{group_name}", group_name),
        #     attributes=[self.GOOGLE_WORKSPACE_GROUP_MEMBER_ATTRIBUTE],
        #     paged_size=self.GOOGLE_WORKSPACE_PAGE_SIZE,
        # )
        # for entry in entries:
        #     if entry["type"] == "searchResEntry":
        #         for member in entry["attributes"][self.GOOGLE_WORKSPACE_GROUP_MEMBER_ATTRIBUTE]:
        #             if self.GOOGLE_WORKSPACE_GROUP_BASE_DN in member:
        #                 pass
        #             # print("Nested groups are not yet supported.")
        #             # print("This feature is currently under development.")
        #             # print("{} was not processed.".format(member))
        #             # print("Unable to look up '{}'".format(member))
        #             # print(e)
        #             else:
        #                 try:
        #                     member_dn = self.get_user_info(user=member)
        #                     # pprint(member_dn)
        #                     if (
        #                         member_dn
        #                         and member_dn["attributes"]
        #                         and member_dn["attributes"][self.GOOGLE_WORKSPACE_USER_ATTRIBUTE]
        #                     ):
        #                         username = str(
        #                             member_dn["attributes"][self.GOOGLE_WORKSPACE_USER_ATTRIBUTE][0]
        #                         ).casefold()
        #                         if (
        #                             self.USER_SYNC_ATTRIBUTE == "mail"
        #                             and self.GOOGLE_WORKSPACE_USER_MAIL_ATTRIBUTE
        #                             not in member_dn["attributes"]
        #                         ):
        #                             raise Exception(
        #                                 f"{self.USER_SYNC_ATTRIBUTE} not found"
        #                             )
        #                         elif (
        #                             self.GOOGLE_WORKSPACE_USER_MAIL_ATTRIBUTE
        #                             in member_dn["attributes"]
        #                         ):
        #                             email = str(
        #                                 member_dn["attributes"][
        #                                     self.GOOGLE_WORKSPACE_USER_MAIL_ATTRIBUTE
        #                                 ][0]
        #                             ).casefold()
        #                         else:
        #                             email = None

        #                         user_info = {
        #                             "username": username, "email": email}
        #                         member_list.append(user_info)
        #                 except Exception as e:
        #                     traceback.print_exc(file=sys.stderr)
        # return member_list
        return []

    def get_user_info(self, user=None):
        """
        Look up user info from GOOGLE_WORKSPACE
        :param user:
        :type user:
        :return:
        :rtype:
        """
        return []
        # if any(attr in user.casefold() for attr in ["uid=", "cn="]):
        #     search_base = user
        # else:
        #     search_base = self.GOOGLE_WORKSPACE_USER_BASE_DN
        # try:
        #     try:
        #         self.conn.search(
        #             search_base=search_base,
        #             search_filter=self.GOOGLE_WORKSPACE_USER_FILTER.replace(
        #                 "{username}", escape_filter_chars(user)
        #             ),
        #             attributes=["*"],
        #         )
        #         if len(self.conn.entries) > 0:
        #             data = json.loads(self.conn.entries[0].entry_to_json())
        #             return data
        #     except Exception as e:
        #         traceback.print_exc(file=sys.stderr)
        # except Exception as e:
        #     traceback.print_exc(file=sys.stderr)
