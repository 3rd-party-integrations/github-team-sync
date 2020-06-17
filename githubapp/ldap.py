import yaml
import os
from ldap3 import Server, Connection, ALL


class LDAPClient:
    def __init__(self, settings_file):
        with open(settings_file, 'rb') as stream:
            # Read settings from the config file and store them as constants
            settings = yaml.load(stream, Loader=yaml.FullLoader)
            self.LDAP_SERVERS = settings['ldap']['servers']
            self.LDAP_SERVER_PORT = settings['ldap']['port']
            self.LDAP_BASEDN = settings['ldap']['base_dn']
            self.LDAP_USER_BASEDN = settings['ldap']['user_base_dn']
            self.LDAP_USER_FILTER = settings['ldap']['user_filter']
            self.LDAP_USER_ATTRIBUTE = settings['ldap']['user_attribute']
            self.LDAP_GROUP_BASEDN = settings['ldap']['group_base_dn']
            self.LDAP_GROUP_FILTER = settings['ldap']['group_filter']
            self.LDAP_GROUP_MEMBER_ATTRIBUTE = settings['ldap']['group_member_attribute']
            self.LDAP_BIND_USER = settings['ldap']['bind_user']
            self.LDAP_PAGE_SIZE = settings['ldap']['page_size']
            if 'bind_password' in settings['ldap']:
                if settings['ldap']['bind_password']:
                    self.LDAP_BIND_PWD = settings['ldap']['bind_password']
            elif os.environ['LDAP_BIND_PASSWORD']:
                self.LDAP_BIND_PWD = os.environ['LDAP_BIND_PASSWORD']

        self.conn = Connection(self.LDAP_SERVERS[0],
                               user=self.LDAP_BIND_USER,
                               password=self.LDAP_BIND_PWD,
                               auto_bind=True,
                               auto_range=True)

    def get_group_members(self, group_name):
        """
        Get members of the requested group in LDAP/Active Directory
        :param group_name: The name of the group
        :type group_name: str
        :return member_list: List of members found in this LDAP group
        :rtype member_list: list
        """
        member_list = []
        entries = self.conn.extend.standard.paged_search(search_base=self.LDAP_BASEDN,
                                                         search_filter=self.LDAP_GROUP_FILTER.replace('{group_name}',
                                                                                                      group_name),
                                                         attributes=[self.LDAP_GROUP_MEMBER_ATTRIBUTE],
                                                         paged_size=self.LDAP_PAGE_SIZE)
        for entry in entries:
            if entry['type'] == 'searchResEntry':
                for member in entry['attributes'][self.LDAP_GROUP_MEMBER_ATTRIBUTE]:
                    try:
                        member_list.append(self.get_attr_by_dn(member))
                    except IndexError:
                        if self.LDAP_GROUP_BASEDN in member:
                            pass
                            #print("Nested groups are not yet supported.")
                            #print("This feature is currently under development.")
                            #print("{} was not processed.".format(member))
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
            self.conn.search(search_base=user_dn,
                             search_filter=self.LDAP_USER_FILTER,
                             attributes=[self.LDAP_USER_ATTRIBUTE])
        except Exception as e:
            print(e)
        username = self.conn.entries[0][self.LDAP_USER_ATTRIBUTE]
        return str(username).casefold()