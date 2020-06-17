import yaml
from pprint import pprint
from flask import Flask
from githubapp import GitHubApp, LDAPClient

app = Flask(__name__)
github_app = GitHubApp(app)
ldap = LDAPClient('settings.yml')


@github_app.on('team.created')
def sync_team():
    pprint(github_app.payload)
    payload = github_app.payload
    slug = payload['team']['slug']
    parent = payload['team']['parent']
    ldap_members = ldap_lookup(group=slug)
    team_members = github_lookup(team_id=payload['team']['id'])
    difference = compare_members(ldap_group=ldap_members, github_team=team_members)


def ldap_lookup(group=None):
    """
    Look up members of a group in LDAP
    :param group:
    :return:
    """
    group_members = ldap.get_group_members(group)
    ldap_members = [str(member).casefold() for member in group_members]
    return ldap_members


def github_lookup(team_id=None):
    """
    Look up members of a give team in GitHub
    :param team_id:
    :return:
    """
    owner = github_app.payload['organization']['login']
    org = github_app.installation_client.organization(owner)
    team = org.team(team_id)
    team_members = [str(member).casefold() for member in team.members()]
    return team_members


def compare_members(ldap_group, github_team):
    add_users = list(set(ldap_group) - set(github_team))
    print(ldap_group)
    print(github_team)
    print(add_users)


def sync_users():
    pass