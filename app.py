from pprint import pprint
from flask import Flask
from githubapp import GitHubApp, LDAPClient
import os

app = Flask(__name__)
github_app = GitHubApp(app)
ldap = LDAPClient()

@github_app.on('team.created')
def sync_team():
    pprint(github_app.payload)
    payload = github_app.payload
    owner = github_app.payload['organization']['login']
    org = github_app.installation_client.organization(owner)
    team = org.team(payload['team']['id'])
    slug = payload['team']['slug']
    parent = payload['team']['parent']
    ldap_members = ldap_lookup(group=slug)
    team_members = github_lookup(
        team_id=payload['team']['id'],
        attribute='username'
    )
    
    compare = compare_members(
        ldap_group=ldap_members,
        github_team=team_members,
        attribute='username'
    )
    pprint(compare)
    execute_sync(
        org=org,
        team=team,
        state=compare
    )


def ldap_lookup(group=None):
    """
    Look up members of a group in LDAP
    :param group: The name of the group to query in LDAP
    :type group: str
    :return: ldap_members
    :rtype: list
    """
    group_members = ldap.get_group_members(group)
    ldap_members = [member for member in group_members]
    return ldap_members

def github_team(team_id):
    owner = github_app.payload['organization']['login']
    org = github_app.installation_client.organization(owner)
    return org.team(team_id)

def github_lookup(team_id=None, attribute='username'):
    """
    Look up members of a give team in GitHub
    :param team_id:
    :param attribute:
    :type team_id: int
    :type attribute: str
    :return: team_members
    :rtype: list
    """
    team_members = []
    team = github_team(team_id)
    if attribute == 'email':
        for m in team.members():
            user = github_app.installation_client.user(m.login)
            team_members.append({'username': str(user.login).casefold(),
                                 'email': str(user.email).casefold()})
    else:
        for member in team.members():
            team_members.append({'username': str(member).casefold(),
                                 'email': ''})
    return team_members


def compare_members(ldap_group, github_team, attribute='username'):
    """
    Compare users in GitHub and LDAP to see which users need to be added or removed
    :param ldap_group:
    :param github_team:
    :param attribute:
    :return: sync_state
    :rtype: dict
    """
    ldap_list = [x[attribute] for x in ldap_group]
    github_list = [x[attribute] for x in github_team]
    add_users = list(set(ldap_list) - set(github_list))
    remove_users = list(set(github_list) - set(ldap_list))
    sync_state = {
        'ldap': ldap_group,
        'github': github_team,
        'action': {
            'add': add_users,
            'remove': remove_users
        }
    }
    return sync_state


def execute_sync(org, team ,state):
    for user in state['action']['add']:
        # Validate that user is in org
        if org.is_member(user):
            team.add_or_update_membership(user)
        else:
            pprint(f'Skipping {user} as they are not part of the org')

    for user in state['action']['remove']:
        pprint(f'Removing {user}')
        team.revoke_membership(user)