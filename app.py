import yaml
from pprint import pprint
from flask import Flask
from githubapp import GitHubApp, LDAPClient

app = Flask(__name__)
github_app = GitHubApp(app)
ldap = LDAPClient('settings.yml')


@github_app.on('team.created')
def sync_team():
    #pprint(github_app.payload)
    payload = github_app.payload
    slug = payload['team']['slug']
    parent = payload['team']['parent']
    ldap_members = ldap_lookup(group=slug)
    team_members = github_lookup(team_id=payload['team']['id'])
    sync = compare_members(ldap_group=ldap_members, github_team=team_members)
    pprint(sync)


def ldap_lookup(group=None):
    """
    Look up members of a group in LDAP
    :param group: The name of the group to query in LDAP
    :type group: str
    :return: ldap_members
    :rtype: list
    """
    group_members = ldap.get_group_members(group)
    ldap_members = [str(member).casefold() for member in group_members]
    return ldap_members


def github_lookup(team_id=None):
    """
    Look up members of a give team in GitHub
    :param team_id:
    :type team_id: int
    :return: team_members
    :rtype: list
    """
    owner = github_app.payload['organization']['login']
    org = github_app.installation_client.organization(owner)
    team = org.team(team_id)
    team_members = [str(member).casefold() for member in team.members()]
    return team_members


def compare_members(ldap_group, github_team):
    """
    Compare users in GitHub and LDAP to see which users need to be added or removed
    :param ldap_group:
    :param github_team:
    :return: sync_state
    :rtype: dict
    """
    add_users = list(set(ldap_group) - set(github_team))
    remove_users = list(set(github_team) - set(ldap_group))
    sync_state = {
        'ldap': ldap_group,
        'github': github_team,
        'action': {
            'add': add_users,
            'remove': remove_users
        }
    }
    return sync_state


def sync_users():
    pass