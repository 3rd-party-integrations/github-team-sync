from pprint import pprint
from flask import Flask
from githubapp import GitHubApp, LDAPClient
from distutils.util import strtobool
import os
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import time

app = Flask(__name__)
github_app = GitHubApp(app)
ldap = LDAPClient()

# Schedule a full sync
scheduler = BackgroundScheduler(daemon=True)
scheduler.start()
atexit.register(lambda: scheduler.shutdown(wait=False))

@github_app.on('team.created')
def sync_new_team():
    """
    Sync a new team when it is created
    :return:
    """
    owner = github_app.payload['organization']['login']
    team_id = github_app.payload['team']['id']
    slug = github_app.payload['team']['slug']
    client = github_app.installation_client
    sync_team(client=client, owner=owner, team_id=team_id, slug=slug)


def sync_team(client=None, owner=None, team_id=None, slug=None):
    """

    :param client:
    :param owner:
    :param team_id:
    :param slug:
    :return:
    """
    org = client.organization(owner)
    team = org.team(team_id)
    ldap_members = ldap_lookup(group=slug)
    team_members = github_lookup(
        client=client,
        owner=owner,
        team_id=team_id,
        attribute='username'
    )
    compare = compare_members(
        ldap_group=ldap_members,
        github_team=team_members,
        attribute='username'
    )
    pprint(compare)
    try:
        execute_sync(
            org=org,
            team=team,
            slug=slug,
            state=compare
        )
    except ValueError as e:
        if strtobool(os.environ['OPEN_ISSUE_ON_FAILURE']):
            open_issue(client=client, slug=slug, message=e)
    except AssertionError as e:
        if strtobool(os.environ['OPEN_ISSUE_ON_FAILURE']):
            open_issue(client=client, slug=slug, message=e)


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


def github_team(client=None, owner=None, team_id=None):
    """
    Look up team info in GitHub
    :param client:
    :param owner:
    :param team_id:
    :return:
    """
    org = client.organization(owner)
    return org.team(team_id)


def github_lookup(client=None, owner=None, team_id=None, attribute='username'):
    """
    Look up members of a give team in GitHub
    :param client:
    :param owner:
    :param team_id:
    :param attribute:
    :type owner: str
    :type team_id: int
    :type attribute: str
    :return: team_members
    :rtype: list
    """
    team_members = []
    team = github_team(client=client, owner=owner, team_id=team_id)
    if attribute == 'email':
        for m in team.members():
            user = client.user(m.login)
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


def execute_sync(org, team, slug, state):
    """
    Perform the synchronization
    :param org:
    :param team:
    :param slug:
    :param state:
    :return:
    """
    total_changes = len(state['action']['remove']) + len(state['action']['add'])
    if len(state['ldap']) == 0:
        message = "LDAP group returned empty: {}".format(slug)
        raise ValueError(message)
    elif int(total_changes) > int(os.environ['CHANGE_THRESHOLD']):
        message = "Skipping sync for {}.<br>".format(slug)
        message += "Total number of changes ({}) would exceed the change threshold ({}).".format(
            str(total_changes), str(os.environ['CHANGE_THRESHOLD'])
        )
        message += "<br>Please investigate this change and increase your threshold if this is accurate."
        raise AssertionError(message)
    else:
        for user in state['action']['add']:
            # Validate that user is in org
            if org.is_member(user):
                pprint(f'Adding {user} to {slug}')
                team.add_or_update_membership(user)
            else:
                pprint(f'Skipping {user} as they are not part of the org')

        for user in state['action']['remove']:
            pprint(f'Removing {user} from {slug}')
            team.revoke_membership(user)


def open_issue(client, slug, message):
    repo_for_issues = os.environ['REPO_FOR_ISSUES']
    owner = repo_for_issues.split('/')[0]
    repository = repo_for_issues.split('/')[1]
    assignee = os.environ['ISSUE_ASSIGNEE']
    client.create_issue(
        owner=owner,
        repository=repository,
        assignee=assignee,
        title="Team sync failed for @{}/{}".format(owner, slug),
        body=str(message)
    )


@scheduler.scheduled_job('interval', id='sync_all_teams', seconds=45)
def sync_all_teams():
    """

    :return:
    """
    pprint(f'Syncing all teams: {time.strftime("%A, %d. %B %Y %I:%M:%S %p")}')
    with app.app_context() as ctx:
        c = ctx.push()
        gh = GitHubApp(c)
        installations = gh.app_client.app_installations
        for i in installations():
            client = gh.app_installation(installation_id=i.id)
            org = client.organization(i.account['login'])
            for team in org.teams():
                pprint(team.as_json())
                sync_team(
                    client=client,
                    owner=i.account['login'],
                    team_id=team.id,
                    slug=team.slug
                )

# Sync right when we start
# For some reason this kicks off twice
sync_all_teams()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)