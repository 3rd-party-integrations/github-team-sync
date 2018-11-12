#!/usr/bin/env python3

import ldap
import yaml
import argparse
#from urllib.parse import urlparse
from pprint import pprint
from urlparse import urlparse
from github import Github, GithubException


class ADSync:
    def __init__(self, settings_file):
        with open(settings_file, 'r') as stream:
            # Read settings from the config file and store them as constants
            settings = yaml.load(stream)
            self.GITHUB_SERVER = settings['github']['server_url']
            self.GITHUB_TOKEN = settings['github']['token']
            self.AD_SERVERS = settings['ldap']['servers']
            self.AD_SERVER_PORT = settings['ldap']['port']
            self.AD_USER_BASEDN = settings['ldap']['user_base_dn']
            self.AD_GROUP_BASEDN = settings['ldap']['group_base_dn']
            self.AD_USER_FILTER = settings['ldap']['user_filter']
            self.AD_USER_FILTER2 = settings['ldap']['user_filter2']
            self.AD_GROUP_FILTER = settings['ldap']['group_filter']
            self.AD_BIND_USER = settings['ldap']['bind_user']
            self.AD_BIND_PWD = settings['ldap']['bind_password']
            self.AD_SEARCH_DN = settings['ldap']['search_dn']
            self.SERVER = urlparse(self.GITHUB_SERVER)

    def ad_auth(self, server=None, username=None, password=None, port=None, start_tls=False):
        """
        Connect to Active Directory
        :param username: Username of account to search with
        :param password: Password of the account to search with
        :param server: IP Address or hostname of the domain controller
        :param port: LDAP port to connect to
        :param start_tls: Whether or not to start TLS
        :return:
        """
        server = self.AD_SERVERS[0] if not server else server
        username = self.AD_BIND_USER if not username else username
        password = self.AD_BIND_PWD if not password else password
        port = self.AD_SERVER_PORT if not port else port
        prefix = 'ldaps' if start_tls else 'ldap'
        conn = ldap.initialize('{}://{}:{}'.format(prefix, server, port))
        conn.protocol_version = 3
        conn.set_option(ldap.OPT_REFERRALS, 0)
        result = True
        try:
            conn.simple_bind_s(username, password)
            print("Succesfully authenticated to {}".format(server))
        except ldap.INVALID_CREDENTIALS:
            print("Invalid Active Directory credentials")
            return "Invalid credentials", False
        except ldap.SERVER_DOWN:
            print("{}: Server is unreachable".format(server))
            return "{}: Server is unreachable".format(server), False
        except ldap.LDAPError as e:
            if type(e.message) == dict and e.message.has_key('desc'):
                print("Other LDAP error: {}".format(e.message['desc']))
                return "Other LDAP error: {}".format(e.message['desc']), False
            else:
                print("Other LDAP error: {}".format(e))
                return "Other LDAP error: {}".format(e), False
        return conn, result

    def get_dn_by_username(self, username, ad_conn, basednx):
        """
        Get the Distinguished Name of a given user
        :param username: Username of the account to search
        :param ad_conn: Active Directory connection object
        :param basedn: Base DN to search
        :return: return_dn
        """
        basedn = self.AD_USER_BASEDN
        return_dn = ''
        ad_filter = self.AD_USER_FILTER.replace('{username}', username)
        results = ad_conn.search_s(basedn, ldap.SCOPE_SUBTREE, ad_filter)
        if results:
            for dn, others in results:
                return_dn = dn
        return return_dn

    def get_attr_by_dn(self, dn, ad_conn, attr=None):
        """
        Get attributes of a given user in Active Directory. If no attributes are specified,
        a dictionary of all attributes will be returned

        We'll only be querying enabled users with the following filter: (!(userAccountControl:1.2.840.113556.1.4.803:=2))
        :param dn: Distinguished Name
        :param ad_conn: Active Directory Connection object
        :param attr: Optional - the attribute to return
        :return: result
        :type dn: str
        :type attr: str
        """
        result = ad_conn.search_s(dn, ldap.SCOPE_BASE,
                                  '(&(objectCategory=person)(objectClass=user)\
                                  (!(userAccountControl:1.2.840.113556.1.4.803:=2)))')
        d = 0
        if attr is not None:
            if result:
                for dn, attrb in result:
                    if attr in attrb and attrb[attr]:
                        d = attrb[attr][0].lower()
                        break
            return d
        else:
            return result

    def get_group_members(self, group_name, ad_conn):
        """
        Get members of the requested group in Active Directory
        :param group_name: The name of the group
        :param ad_conn: Active Directory Connection object
        :param basedn: Base DN for searching
        :return: members
        :rtype: list
        """
        basedn = self.AD_GROUP_BASEDN
        members = []
        ad_filter = self.AD_GROUP_FILTER.replace('{group_name}', group_name)
        result = ad_conn.search_s(basedn, ldap.SCOPE_SUBTREE, ad_filter)
        if result:
            if len(result[0]) >= 2 and 'member' in result[0][1]:
                members_tmp = result[0][1]['member']
                members_tmp = [u for u in members_tmp if u != 0]
                for m in members_tmp:
                    try:
                        attr = self.get_attr_by_dn(str(m), ad_conn, attr='sAMAccountName')
                        if attr != 0:
                            members.append(str(attr))
                    except Exception as exc:
                        print(exc)
        return members


def main():
    """
    This is the main function, wherein the arguments are passed and logic is applied
    :return:
    """
    # Let's add arguments with defaults.
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--remove", dest="remove", const=True, default=False,
                        action="store_const", help="Remove users from the GitHub Team that are not in the AD group")
    parser.add_argument("-a", "--add", dest="add", const=True, default=True,
                        action="store_const", help="Add users in the AD group to the GitHub Team")
    parser.add_argument("-g", "--group", dest="ad_group", default=None,
                        help="The name of the Active Directory group to sync with GitHub", type=str)
    parser.add_argument("-s", "--sync", dest="sync", const=True, action="store_const", default=False,
                        help="Perform a full sync, removing users from the GitHub team "
                             "that are not present in the AD group, and adding users to"
                             "the GitHub Team that are in the AD group missing in the Team")
    parser.add_argument("-t", "--team", dest="team", default=None,
                        help="The name of the GitHub Team to sync users with", type=str)
    parser.add_argument("-o", "--org", dest="org", help="The name of the GitHub Organization where the Teams reside",
                        default=None, type=str)
    parser.add_argument("-l", "--list", dest="list", help="List users in groups/teams and exit. No changes are made",
                        default=False, const=True, action="store_const")
    parser.add_argument("-i", "--init", dest="initfile", help="Full path to settings.yml file. Default is "
                        "settings.yml in your current directory", default=None)
    args = parser.parse_args()

    # Location of the settings file. Default is the current working path
    if args.initfile:
        settings_file = args.initfile
    else:
        settings_file = "settings.yml"
    adsync = ADSync(settings_file)
    # Get AD users
    if args.ad_group:
        print(args.ad_group)
        # Make the Active Directory connection
        ad_conn, result = adsync.ad_auth()
        # Get a list of users in the group
        ad_members = []
        if result:
            group_members = adsync.get_group_members(args.ad_group, ad_conn)
            for m in group_members:
                ad_members.append(m)
    # If we specify a GitHub Team (-t, --team)
    if args.team:
        if not args.org:
            # Don't run without an Organization (-o, --org)
            print("Please specify an organization in GitHub.")
            exit(255)
        else:
            # Get the GitHub info
            g = Github(base_url=adsync.GITHUB_SERVER, login_or_token=adsync.GITHUB_TOKEN)
            print(args.org)
            org = g.get_organization(args.org)
            try:
                # Get the Team info
                team = org.get_teams()[0]
                # Get a list of members in the Team
                ghe_members = []
                for m in team.get_members():
                    ghe_members.append(m.login)
            except GithubException as exc:
                print("No teams for Org {}".format(org))
                print(exc)
    # Just list the users and exit
    if args.list:
        # If we want AD users listed
        if args.ad_group:
            print("AD Group: {}".format(args.ad_group))
            print("---------------")
            for member in ad_members:
                print(member)
            print("")
        # If we want GHE users listed
        if args.team:
            print("GitHub Team: {}".format(args.team))
            print("---------------")
            for member in ghe_members:
                print(member)
        exit(0)
    # Add users to the GitHub Team if they're found in Active Directory but not in the GitHub Team
    if args.add or args.sync:
        if not args.team:
            print("Please specify a GitHub Team.")
            exit(255)
        elif not args.ad_group:
            print("Please specify an AD Group.")
            exit(255)
        else:
            # Compare the lists and remove matching users
            add_users = list(set(ad_members) - set(ghe_members))
            if not add_users:
                print("There are no users to add to {}".format(args.team))
            else:
                for u in add_users:
                    # Get the user object
                    try:
                        user = g.get_user(login=u)
                        print("Adding user {} to {}".format(u, args.team))
                        # Add the user to the team
                        team.add_membership(user)
                    except GithubException as exc:
                        print("User {} not found on {}".format(u, adsync.SERVER.netloc))
                        print(exc)
    # Remove users from the GitHub Team if they're not found in the Active Directory group
    if args.remove or args.sync:
        if not args.team:
            print("Please specify a GitHub Team.")
            exit(255)
        elif not args.ad_group:
            print("Please specify an AD Group.")
            exit(255)
        else:
            # Compare the lists of users and remove matches, leaving only extra users
            remove_users = list(set(ghe_members) - set(ad_members))
            if not remove_users:
                print("There are no users to remove from {}".format(args.team))
            else:
                for u in remove_users:
                    try:
                        user = g.get_user(login=u)
                        print("Removing user {} from {}".format(u, args.team))
                        # Remove the user from the Team
                        team.remove_from_members(user)
                    except GithubException as exc:
                        print("User {} not found in Github".format(u))
                        print(exc)


if __name__ == "__main__":
    main()
