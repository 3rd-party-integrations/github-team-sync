#!/usr/bin/env python3
import sys
import yaml
import argparse
import os
from ldap3 import Server, Connection, ALL
from github import Github, GithubException
from urllib.parse import urlparse

class LDAPSync:
    def __init__(self, settings_file):
        with open(settings_file, 'rb') as stream:
            # Read settings from the config file and store them as constants
            settings = yaml.load(stream, Loader=yaml.FullLoader)
            self.GITHUB_SERVER = settings['github']['server_url']
            self.LDAP_SERVERS = settings['ldap']['servers']
            self.LDAP_SERVER_PORT = settings['ldap']['port']
            self.LDAP_BASEDN = settings['ldap']['base_dn']
            self.LDAP_USER_BASEDN = settings['ldap']['user_base_dn']
            self.LDAP_GROUP_BASEDN = settings['ldap']['group_base_dn']
            self.LDAP_USER_FILTER = settings['ldap']['user_filter']
            self.LDAP_GROUP_FILTER = settings['ldap']['group_filter']
            self.LDAP_BIND_USER = settings['ldap']['bind_user']
            self.LDAP_PAGE_SIZE = settings['ldap']['page_size']
            self.LDAP_GROUP_ATTR = settings['ldap']['group_attr']
            self.LDAP_USER_ATTR = settings['ldap']['user_attr']
            self.LDAP_START_TLS = settings['ldap']['start_tls']
            if 'token' in settings['github']:
                if settings['github']['token']:
                    self.GITHUB_TOKEN = settings['github']['token']
            elif os.environ['GITHUB_TOKEN']:
                self.GITHUB_TOKEN = os.environ['GITHUB_TOKEN']
            else:
                print('Please set a GitHub token')
                os.exit(255)
            if 'bind_password' in settings['ldap']:
                if settings['ldap']['bind_password']:
                    self.LDAP_BIND_PWD = settings['ldap']['bind_password']
            elif os.environ['AD_BIND_PASSWORD']:
                self.LDAP_BIND_PWD = os.environ['AD_BIND_PASSWORD']
            self.SERVER = urlparse(self.GITHUB_SERVER)

        server = Server(self.LDAP_SERVERS[0], use_ssl=self.LDAP_START_TLS)
        self.conn = Connection(server,
                               user=self.LDAP_BIND_USER,
                               password=self.LDAP_BIND_PWD,
                               auto_bind=True,
                               auto_range=True)


    def get_group_members(self, group_name):
        """
        Get members of the requested group in AD/LDAP
        :param group_name: The name of the group
        :type group_name: str
        :return: members
        :rtype: list
        """
        member_list = []
        entries = self.conn.extend.standard.paged_search(search_base=self.LDAP_BASEDN,
                                                         search_filter=self.LDAP_GROUP_FILTER.replace('{group_name}', group_name),
                                                         attributes=[self.LDAP_GROUP_ATTR],
                                                         paged_size=self.LDAP_PAGE_SIZE)
        for entry in entries:
            if entry['type'] == 'searchResEntry':
                for member in entry['attributes'][self.LDAP_GROUP_ATTR]:
                    member_list.append(self.get_attr_by_dn(member))
        return member_list

    def get_attr_by_dn(self, userdn):
        """
        Get an attribute for a given object.
        :param userdn: Object's full DN to lookup
        :return: username
        """
        self.conn.search(search_base=userdn,
                         search_filter=self.LDAP_USER_FILTER,
                         attributes=[self.LDAP_USER_ATTR])
        username = self.conn.entries[0][self.LDAP_USER_ATTR]
        return str(username)


def main():
    """
    This is the main function, wherein the arguments are passed and logic is applied
    :return:
    """
    # Let's add arguments with defaults.
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--remove", dest="remove", const=True, default=False,
                        action="store_const", help="Remove users from the GitHub Team that are not in the AD/LDAP group")
    parser.add_argument("-a", "--add", dest="add", const=True, default=True,
                        action="store_const", help="Add users in the AD/LDAP group to the GitHub Team")
    parser.add_argument("-g", "--group", dest="ldap_group", default=None,
                        help="The name of the AD/LDAP group to sync with GitHub", type=str)
    parser.add_argument("-s", "--sync", dest="sync", const=True, action="store_const", default=False,
                        help="Perform a full sync, removing users from the GitHub team "
                             "that are not present in the AD/LDAP group, and adding users to"
                             "the GitHub Team that are in the AD/LDAP group missing in the Team")
    parser.add_argument("-t", "--team", dest="team", default=None,
                        help="The name of the GitHub Team to sync users with", type=str)
    parser.add_argument("-o", "--org", dest="org", help="The name of the GitHub Organization where the Teams reside",
                        default=None, type=str)
    parser.add_argument("-l", "--list", dest="list", help="List users in groups/teams and exit. No changes are made",
                        default=False, const=True, action="store_const")
    parser.add_argument("-i", "--init", dest="initfile", help="Full path to settings.yml file. Default is "
                        "settings.yml in your current directory", default=None)
    parser.add_argument("-n", "--skip-null", dest="skip_null", const=True, default=False, action="store_const",
                        help="Skip empty groups in AD/LDAP, to avoid emptying the GitHub group")
    args = parser.parse_args()

    # Location of the settings file. Default is the current working path
    if args.initfile:
        settings_file = args.initfile
    else:
        settings_file = "settings.yml"
    ldapsync = LDAPSync(settings_file)
    # Get LDAP users
    if args.ldap_group:
        # Get a list of users in the group
        ldap_members = []
        group_members = ldapsync.get_group_members(args.ldap_group)
        for m in group_members:
            ldap_members.append(m)
    # If we specify a GitHub Team (-t, --team)
    if args.team:
        if not args.org:
            # Don't run without an Organization (-o, --org)
            print("Please specify an organization in GitHub.")
            exit(255)
        else:
            # Get the GitHub info
            g = Github(base_url=ldapsync.GITHUB_SERVER, login_or_token=ldapsync.GITHUB_TOKEN)
            print(args.org + '\\' + args.team)
            org = g.get_organization(args.org)
            try:
                # Get the Team info
                team = next(t for t in org.get_teams() if t.name == args.team)
                # Get a list of members in the Team
                ghe_members = []
                for m in team.get_members():
                    ghe_members.append(m.login)
            except GithubException as exc:
                print("No teams for Org {}".format(org))
                print(exc)
    # Just list the users and exit
    if args.list:
        # If we want LDAP users listed
        if args.ldap_group:
            print("AD/LDAP Group: {}".format(args.ldap_group))
            print("-----------------")
            for member in ldap_members:
                print(member)
            print("")
        # If we want GHE users listed
        if args.team:
            print("GitHub Team: {}".format(args.team))
            print("---------------")
            for member in ghe_members:
                print(member)
        exit(0)
    # Add users to the GitHub Team if they're found in AD/LDAP but not in the GitHub Team
    if args.add or args.sync:
        if not args.team:
            print("Please specify a GitHub Team.")
            exit(255)
        elif not args.ldap_group:
            print("Please specify an AD/LDAP Group.")
            exit(255)
        else:
            # Compare the lists and remove matching users
            add_users = list(set(ldap_members) - set(ghe_members))
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
                        print("User {} not found on {}".format(u, ldapsync.SERVER.netloc))
                        print(exc)
    # Remove users from the GitHub Team if they're not found in the AD/LDAP group
    if args.remove or args.sync:
        if not args.team:
            print("Please specify a GitHub Team.")
            exit(255)
        elif not args.ldap_group:
            print("Please specify an AD/LDAP Group.")
            exit(255)
        else:
            # Compare the lists of users and remove matches, leaving only extra users
            remove_users = list(set(ghe_members) - set(ldap_members))
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
