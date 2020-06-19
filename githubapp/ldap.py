import os
import json
import logging
from ldap3 import Server, Connection, ALL
from pprint import pprint

LOG = logging.getLogger(__name__)


class LDAPClient:
    def __init__(self):
        # Read settings from the config file and store them as constants
        self.LDAP_SERVER_HOST = os.environ['LDAP_SERVER_HOST']
        self.LDAP_SERVER_PORT = os.environ['LDAP_SERVER_PORT']
        self.LDAP_BASE_DN = os.environ['LDAP_BASE_DN']
        self.LDAP_USER_BASE_DN = os.environ['LDAP_USER_BASE_DN']
        self.LDAP_USER_ATTRIBUTE = os.environ['LDAP_USER_ATTRIBUTE']
        self.LDAP_USER_FILTER = os.environ['LDAP_USER_FILTER'].replace(
            '{ldap_user_attribute}',
            self.LDAP_USER_ATTRIBUTE
        )
        self.LDAP_USER_MAIL_ATTRIBUTE = os.environ['LDAP_USER_MAIL_ATTRIBUTE']
        self.LDAP_GROUP_BASE_DN = os.environ['LDAP_GROUP_BASE_DN']
        self.LDAP_GROUP_FILTER = os.environ['LDAP_GROUP_FILTER']
        self.LDAP_GROUP_MEMBER_ATTRIBUTE = os.environ['LDAP_GROUP_MEMBER_ATTRIBUTE']
        if 'LDAP_BIND_USER' in os.environ:
            self.LDAP_BIND_USER = os.environ['LDAP_BIND_USER']
        elif 'LDAP_BIND_DN' in os.environ:
            self.LDAP_BIND_USER = os.environ['LDAP_BIND_DN']
        else:
            raise Exception('LDAP credentials have not been specified')
        if 'LDAP_PAGE_SIZE' in os.environ:
            self.LDAP_PAGE_SIZE = os.environ['LDAP_SEARCH_PAGE_SIZE']
        else:
            self.LDAP_PAGE_SIZE = 1000
        if 'LDAP_BIND_PASSWORD' in os.environ:
            self.LDAP_BIND_PASSWORD = os.environ['LDAP_BIND_PASSWORD']
        else:
            raise Exception('LDAP credentials have not been specified')
        self.conn = Connection(
            self.LDAP_SERVER_HOST,
            user=self.LDAP_BIND_USER,
            password=self.LDAP_BIND_PASSWORD,
            auto_bind=True,
            auto_range=True
        )

    def get_group_members(self, group_name):
        """
        Get members of the requested group in LDAP/Active Directory
        :param group_name: The name of the group
        :type group_name: str
        :return member_list: List of members found in this LDAP group
        :rtype member_list: list
        """
        member_list = []
        entries = self.conn.extend.standard.paged_search(
            search_base=self.LDAP_BASE_DN,
            search_filter=self.LDAP_GROUP_FILTER.replace(
                '{group_name}',
                group_name
            ),
            attributes=[self.LDAP_GROUP_MEMBER_ATTRIBUTE],
            paged_size=self.LDAP_PAGE_SIZE
        )
        for entry in entries:
            if entry['type'] == 'searchResEntry':
                for member in entry['attributes'][self.LDAP_GROUP_MEMBER_ATTRIBUTE]:
                    if self.LDAP_GROUP_BASE_DN in member:
                        pass
                        # print("Nested groups are not yet supported.")
                        # print("This feature is currently under development.")
                        # print("{} was not processed.".format(member))
                        # print("Unable to look up '{}'".format(member))
                        # print(e)
                    else:
                        try:
                            member_dn = self.get_user_info(member)
                            pprint(member_dn)
                            username = str(member_dn['attributes'][self.LDAP_USER_ATTRIBUTE][0]).casefold()
                            email = str(member_dn['attributes'][self.LDAP_USER_MAIL_ATTRIBUTE][0]).casefold()
                            user_info = {'username': username, 'email': email}
                            member_list.append(user_info)
                        except Exception as e:
                            pass
        return member_list

    def get_user_info(self, member=None):
        """
        Look up user info from LDAP
        :param member:
        :type member:
        :return:
        :rtype:
        """
        if any(attr in member.casefold() for attr in ['uid=', 'cn=']):
            search_base = member
        else:
            search_base = self.LDAP_USER_BASE_DN
        try:
            try:
                self.conn.search(
                    search_base=search_base,
                    search_filter=self.LDAP_USER_FILTER.replace('{username}', member),
                    attributes=["*"]
                )
                data = json.loads(self.conn.entries[0].entry_to_json())
                return data
            except Exception as e:
                print(e)
        except Exception as e:
            print(e)
