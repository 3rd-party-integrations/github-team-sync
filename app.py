import atexit
import os
import time
from distutils.util import strtobool
from pprint import pprint

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import Flask

from githubapp import GitHubApp, DirectoryClient, CRON_INTERVAL, TEST_MODE

app = Flask(__name__)
github_app = GitHubApp(app)
directory = DirectoryClient()

# Schedule a full sync
scheduler = BackgroundScheduler(daemon=True)
scheduler.start()
atexit.register(lambda: scheduler.shutdown(wait=False))


@github_app.on("team.created")
def sync_new_team():
    """
    Sync a new team when it is created
    :return:
    """
    owner = github_app.payload["organization"]["login"]
    team_id = github_app.payload["team"]["id"]
    slug = github_app.payload["team"]["slug"]
    client = github_app.installation_client
    sync_team(client=client, owner=owner, team_id=team_id, slug=slug)


def sync_team(client=None, owner=None, team_id=None, slug=None):
    """
    Prepare the team sync
    :param client:
    :param owner:
    :param team_id:
    :param slug:
    :return:
    """
    org = client.organization(owner)
    team = org.team(team_id)
    custom_map = load_custom_map()
    directory_group = custom_map[slug] if slug in custom_map else slug
    directory_members = directory_group_members(group=directory_group)
    team_members = github_team_members(
        client=client, owner=owner, team_id=team_id, attribute="username"
    )
    compare = compare_members(
        group=directory_members, team=team_members, attribute="username"
    )
    if TEST_MODE:
        print("Skipping execution due to TEST_MODE...")
        pprint(compare)
    else:
        try:
            execute_sync(org=org, team=team, slug=slug, state=compare)
        except ValueError as e:
            if strtobool(os.environ["OPEN_ISSUE_ON_FAILURE"]):
                open_issue(client=client, slug=slug, message=e)
        except AssertionError as e:
            if strtobool(os.environ["OPEN_ISSUE_ON_FAILURE"]):
                open_issue(client=client, slug=slug, message=e)


def directory_group_members(group=None):
    """
    Look up members of a group in your user directory
    :param group: The name of the group to query in your directory server
    :type group: str
    :return: group_members
    :rtype: list
    """
    members = directory.get_group_members(group)
    group_members = [member for member in members]
    return group_members


def github_team_info(client=None, owner=None, team_id=None):
    """
    Look up team info in GitHub
    :param client:
    :param owner:
    :param team_id:
    :return:
    """
    org = client.organization(owner)
    return org.team(team_id)


def github_team_members(client=None, owner=None, team_id=None, attribute="username"):
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
    team = github_team_info(client=client, owner=owner, team_id=team_id)
    if attribute == "email":
        for m in team.members():
            user = client.user(m.login)
            team_members.append(
                {
                    "username": str(user.login).casefold(),
                    "email": str(user.email).casefold(),
                }
            )
    else:
        for member in team.members():
            team_members.append({"username": str(member).casefold(), "email": ""})
    return team_members


def compare_members(group, team, attribute="username"):
    """
    Compare users in GitHub and the User Directory to see which users need to be added or removed
    :param group:
    :param team:
    :param attribute:
    :return: sync_state
    :rtype: dict
    """
    directory_list = [x[attribute] for x in group]
    github_list = [x[attribute] for x in team]
    add_users = list(set(directory_list) - set(directory_list))
    remove_users = list(set(github_list) - set(directory_list))
    sync_state = {
        "directory": group,
        "github": team,
        "action": {"add": add_users, "remove": remove_users},
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
    total_changes = len(state["action"]["remove"]) + len(state["action"]["add"])
    if len(state["directory"]) == 0:
        message = f"{os.environ.get('USER_DIRECTORY', 'LDAP').upper()} group returned empty: {slug}"
        raise ValueError(message)
    elif int(total_changes) > int(os.environ.get("CHANGE_THRESHOLD", 25)):
        message = "Skipping sync for {}.<br>".format(slug)
        message += "Total number of changes ({}) would exceed the change threshold ({}).".format(
            str(total_changes), str(os.environ.get("CHANGE_THRESHOLD", 25))
        )
        message += "<br>Please investigate this change and increase your threshold if this is accurate."
        raise AssertionError(message)
    else:
        for user in state["action"]["add"]:
            # Validate that user is in org
            if org.is_member(user):
                pprint(f"Adding {user} to {slug}")
                team.add_or_update_membership(user)
            else:
                pprint(f"Skipping {user} as they are not part of the org")

        for user in state["action"]["remove"]:
            pprint(f"Removing {user} from {slug}")
            team.revoke_membership(user)


def open_issue(client, slug, message):
    """
    Open an issue with the failed sync details
    :param client: Our installation client
    :param slug: Team slug
    :param message: Error message to detail
    :return:
    """
    repo_for_issues = os.environ["REPO_FOR_ISSUES"]
    owner = repo_for_issues.split("/")[0]
    repository = repo_for_issues.split("/")[1]
    assignee = os.environ["ISSUE_ASSIGNEE"]
    client.create_issue(
        owner=owner,
        repository=repository,
        assignee=assignee,
        title="Team sync failed for @{}/{}".format(owner, slug),
        body=str(message),
    )


def load_custom_map(file="syncmap.yml"):
    """
    Custom team synchronization
    :param file:
    :return:
    """
    syncmap = {}
    if os.path.isfile(file):
        from yaml import load, Loader

        with open(file, "r") as f:
            data = load(f, Loader=Loader)
        for d in data["mapping"]:
            syncmap[d["github"]] = d["directory"]

    return syncmap


@scheduler.scheduled_job(
    trigger=CronTrigger.from_crontab(CRON_INTERVAL), id="sync_all_teams"
)
def sync_all_teams():
    """
    Lookup teams in a GitHub org and synchronize all teams with your user directory
    :return:
    """
    pprint(f'Syncing all teams: {time.strftime("%A, %d. %B %Y %I:%M:%S %p")}')
    with app.app_context() as ctx:
        c = ctx.push()
        gh = GitHubApp(c)
        installations = gh.app_client.app_installations
        for i in installations():
            client = gh.app_installation(installation_id=i.id)
            org = client.organization(i.account["login"])
            for team in org.teams():
                sync_team(
                    client=client,
                    owner=i.account["login"],
                    team_id=team.id,
                    slug=team.slug,
                )


if __name__ == "__main__":
    sync_all_teams()
    app.run(
        host=os.environ.get("FLASK_RUN_HOST", "0.0.0.0"),
        port=os.environ.get("FLASK_RUN_PORT", "5000"),
    )
