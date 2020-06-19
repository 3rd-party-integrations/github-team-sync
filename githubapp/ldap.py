import os
import logging
from ldap3 import Server, Connection, ALL

LOG = logging.getLogger(__name__)

class LDAPClient:
    def __init__(self):
        # Read settings from the config file and store them as constants
        self.LDAP_SERVER_HOST = os.environ['LDAP_SERVER_HOST']
        self.LDAP_SERVER_PORT = os.environ['LDAP_SERVER_PORT']
        self.LDAP_BASE_DN = os.environ['LDAP_BASE_DN']
        self.LDAP_USER_BASE_DN = os.environ['LDAP_USER_BASE_DN']
        self.LDAP_USER_FILTER = os.environ['LDAP_USER_FILTER']
        self.LDAP_USER_ATTRIBUTE = os.environ['LDAP_USER_ATTRIBUTE']
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
        self.LDAP_PAGE_SIZE = os.environ['LDAP_SEARCH_PAGE_SIZE']
        self.LDAP_BIND_PASSWORD = os.environ['LDAP_BIND_PASSWORD']
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
                    try:
                        if any(attr in member.casefold() for attr in ['uid=', 'cn=']):
                            member_dn = member
                        else:
                            member_dn = f'uid={member},{self.LDAP_USER_BASE_DN}'
                        member_list.append(self.get_attr_by_dn(member_dn))
                    except IndexError:
                        if self.LDAP_GROUP_BASE_DN in member:
                            pass
                            # print("Nested groups are not yet supported.")
                            # print("This feature is currently under development.")
                            # print("{} was not processed.".format(member))
                        else:
                            print("Unable to look up '{}'".format(member))
                    except Exception as e:
                        print(e)
        return member_list

    def get_attr_by_dn(self, user_dn):
        """
        Get an attribute for a given object. Right now we only care about the sAMAccountName/uid,
        so it's hard-coded... we can adjust this if we see a need later down the line
        :param user_dn: Object's full DN to lookup
        :type user_dn: str
        :return username: The user's UID or username
        :rtype username: str
        """
        try:
            self.conn.search(
                search_base=user_dn,
                search_filter=self.LDAP_USER_FILTER,
                attributes=[
                    self.LDAP_USER_ATTRIBUTE,
                    self.LDAP_USER_MAIL_ATTRIBUTE
                ]
            )
        except Exception as e:
            print(e)
        username = str(self.conn.entries[0][self.LDAP_USER_ATTRIBUTE]).casefold()
        email = str(self.conn.entries[0][self.LDAP_USER_MAIL_ATTRIBUTE]).casefold()
        user_info = {'username': username, 'email': email}
        return user_info
