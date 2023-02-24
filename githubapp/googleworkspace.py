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


class GoogleWorkspaceClient:
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
        member_list = []

        request = self.service.list(groupKey=group_name)
        while request is not None:
            members = request.execute()
            for m in members.get('members', []):
                user_info = self.get_user_info(m['id'])
                if user_info.get("email") or user_info.get("email"):
                    member_list.append(user_info)
            request = self.service.list_next(request, members)
        return member_list

    def get_user_info(self, id):
        """
        Look up user info from Google Workspace
        :param user:
        :type user:
        :return:
        :rtype:
        """

        if self.USER_SYNC_ATTRIBUTE == 'username':
            user = self.service.users().get(userKey=id, projection="custom", customFieldMask=self.GOOGLE_WORKSPACE_USERNAME_СUSTOM_SCHEMA_NAME).execute()
            if not user['suspended'] and not user['archived']:
                return {"username": user.get('customSchemas', {}).get(self.GOOGLE_WORKSPACE_USERNAME_СUSTOM_SCHEMA_NAME, {}).get(self.GOOGLE_WORKSPACE_USERNAME_FIELD), "email": None}
        elif self.USER_SYNC_ATTRIBUTE == 'email':
            user = self.service.users().get(userKey=id).execute()
            if not user['suspended'] and not user['archived']:
                return {"username": None, "email": user[self.GOOGLE_WORKSPACE_USER_MAIL_ATTRIBUTE]}
        return {"username": None, "email": None}
