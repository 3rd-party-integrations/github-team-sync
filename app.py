import atexit
from operator import truediv
import os
import time
import json
import github3
from distutils.util import strtobool
import threading
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor


from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import Flask
from keycloak import KeycloakAdmin

from githubapp import (
    GitHubApp,
    DirectoryClient,
    CRON_INTERVAL,
    TEST_MODE,
    ADD_MEMBER,
    REMOVE_ORG_MEMBERS_WITHOUT_TEAM,
    USER_SYNC_ATTRIBUTE,
    SYNCMAP_ONLY,
    SSO_EMAIL_DOMAIN,
    EXPORT_TO_JSON,
)
from githubapp.keycloak import Keycloak

app = Flask(__name__)
github_app = GitHubApp(app)

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
    if os.environ["USER_DIRECTORY"].upper() == "AAD":
        # Azure APIs don't currently support case insensitive searching
        slug = github_app.payload["team"]["name"].replace(" ", "-")
    else:
        slug = github_app.payload["team"]["slug"]
    client = github_app.installation_client
    sync_team(client=client, owner=owner, team_id=team_id, slug=slug)


def sync_team_from_directory(client=None, owner=None, team_name=None, team_id=None):
    """
    Prepare the team sync
    :param client:
    :param owner:
    :param team_id:
    :param slug:
    :return:
    """
    print("-------------------------------")
    print(f"Processing Team: {team_name}, {team_id}")

    try:
        org = client.organization(owner)
        team = org.team(team_id)
        custom_map, group_prefix, ignore_users = load_custom_map()
        try:
            # directory_group = get_directory_from_slug(team_name, custom_map, org)
            # If we're filtering on group prefix, skip if the group doesn't match
            if len(group_prefix) > 0 and not team_name.startswith(
                tuple(group_prefix)
            ):
                print(f"skipping team {team_name} - not in group prefix")
                return
            directory_members = directory_group_members(group=team_name, ignore_users=ignore_users)
            print("Team: ",team_name, "Directory members: ",directory_members)
        except Exception as e:
            directory_members = []
            traceback.print_exc(file=sys.stderr)

        team_members = github_team_members(
            client=client,
            owner=owner,
            team_id=team_id,
            attribute=USER_SYNC_ATTRIBUTE,
            ignore_users=ignore_users,
        )
        print(f" {team_id} github_members: ",team_members)
        compare = compare_members(
            group=directory_members, team=team_members, attribute=USER_SYNC_ATTRIBUTE
        )
        if TEST_MODE:
            print(f"TEST_MODE: Pending changes for team {team_name}:")
            print(json.dumps(compare, indent=2))
            return {"team": team_name, **compare}
        else:
            try:
                execute_sync(org=org, team=team, slug=team_name, state=compare)
            except (AssertionError, ValueError) as e:
                if strtobool(os.environ["OPEN_ISSUE_ON_FAILURE"]):
                    open_issue(client=client, slug=team_name, message=e)
                raise Exception(f"Team {team_name} sync failed: {e}")
        print(f"Processing Team Successful: {team_name}")
    except Exception:
        traceback.print_exc(file=sys.stderr)
        raise



def sync_team(client=None, owner=None, team_id=None, slug=None):
    """
    Prepare the team sync
    :param client:
    :param owner:
    :param team_id:
    :param slug:
    :return:
    """
    print("-------------------------------")
    print(f"Processing Team: {slug}")

    try:
        org = client.organization(owner)
        team = org.team(team_id)
        custom_map, group_prefix, ignore_users = load_custom_map()
        try:
            directory_group = get_directory_from_slug(slug, custom_map, org)
            # If we're filtering on group prefix, skip if the group doesn't match
            if len(group_prefix) > 0 and not directory_group.startswith(
                tuple(group_prefix)
            ):
                print(f"skipping team {team.slug} - not in group prefix")
                return
            directory_members = directory_group_members(group=directory_group)
        except Exception as e:
            directory_members = []
            traceback.print_exc(file=sys.stderr)

        team_members = github_team_members(
            client=client,
            owner=owner,
            team_id=team_id,
            attribute=USER_SYNC_ATTRIBUTE,
            ignore_users=ignore_users,
        )
        print(f" {team_id} github_members: ",team_members)
        compare = compare_members(
            group=directory_members, team=team_members, attribute=USER_SYNC_ATTRIBUTE
        )
        if TEST_MODE:
            print(f"TEST_MODE: Pending changes for team {team.slug}:")
            print(json.dumps(compare, indent=2))
            return {"team": team.slug, **compare}
        else:
            try:
                execute_sync(org=org, team=team, slug=slug, state=compare)
            except (AssertionError, ValueError) as e:
                if strtobool(os.environ["OPEN_ISSUE_ON_FAILURE"]):
                    open_issue(client=client, slug=slug, message=e)
                raise Exception(f"Team {team.slug} sync failed: {e}")
        print(f"Processing Team Successful: {team.slug}")
    except Exception:
        traceback.print_exc(file=sys.stderr)
        raise


def directory_group_members(group=None, ignore_users=[]):
    """
    Look up members of a group in your user directory
    :param group: The name of the group to query in your directory server
    :type group: str
    :return: group_members
    :rtype: list
    """
    try:
        directory = DirectoryClient()
        members = directory.get_group_members(group_name=group)
        group_members = [member for member in members]
    except Exception as e:
        group_members = []
        traceback.print_exc(file=sys.stderr)
    ignore_set = {u.casefold() for u in ignore_users}
    group_members = [m for m in group_members if m[USER_SYNC_ATTRIBUTE].casefold() not in ignore_set and m["email_slug"].casefold() not in ignore_set]
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

_cached_user_json_map = None


def get_user_info_map_from_github():
    private_key_path = os.environ["PRIVATE_KEY_PATH"]
    private_key_path = os.path.expanduser(private_key_path)
    with open(private_key_path, "rb") as key_file:
        key = key_file.read()
    app_id = str(os.environ["APP_ID"])
    installation_id = int(os.environ["USERS_MAP_INSTALLATION_ID"])
    repo_owner = "zeptonow"
    repo_name = os.environ["USERS_MAP_REPO_NAME"]
    file_path = os.environ.get("USERS_MAP_FILE_PATH", "users.json")
    gh = github3.GitHub()
    gh.login_as_app_installation(key, app_id, installation_id)
    repo = gh.repository(repo_owner, repo_name)
    content = repo.file_contents(file_path)
    map = json.loads(content.decoded.decode("utf-8"))
    global GITHUB_USER_CACHE
    GITHUB_USER_CACHE = {value['verified_emails'][0].split("@")[0].lower(): key for key, value in map["users"].items()}
    return map

def get_email_info_from_github(username):
    if _cached_user_json_map is None:
        map = get_user_info_map_from_github()
    else:
        map = _cached_user_json_map
    matching_emails =  [email for email in map["users"][username]["verified_emails"] if SSO_EMAIL_DOMAIN in email]
    if len(matching_emails) == 0:
        if len(map["users"][username]["verified_emails"]) > 0:
            return map["users"][username]["verified_emails"][0]
        else:
            return ""
    return matching_emails[0]

def github_team_members(
    client=None, owner=None, team_id=None, attribute="username", ignore_users=[]
):
    """
    Look up members of a given team in GitHub
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
    if attribute == "email" or attribute == "email_slug":
        for m in team.members():
            user = client.user(m.login)
            if user.email is None:
                # add users.json logic.
                user.email = get_email_info_from_github(user.login)
            team_members.append(
                {
                    "username": str(user.login),
                    "email": str(user.email),
                    "email_slug": str(user.email).split("@")[0].lower(),
                }
            )
    else:
        for member in team.members():
            team_members.append({"username": str(member), "email": ""})
    return [m for m in team_members if m[attribute] not in ignore_users]


def compare_members(group, team, attribute="username"):
    """
    Compare users in GitHub and the User Directory to see which users need to be added or removed
    :param group:
    :param team:
    :param attribute:
    :return: sync_state
    :rtype: dict
    """
    
    directory_list = [x[attribute].casefold() for x in group]
    github_list = [x[attribute].casefold() for x in team]
    add_users = list(set(directory_list) - set(github_list))
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
            if user in GITHUB_USER_CACHE:
                user = GITHUB_USER_CACHE[user]
            else:
                print(f"User: {user} not found in GITHUB_USER_CACHE")
            # Add user to org if they are not already a member and the ADD_MEMBER attribute is "true"
            if not org.is_member(user) and ADD_MEMBER:
                try:
                    print(f"User: {user} is not in the {org.login} organization. Attempting to add.")
                    user_email = get_email_info_from_github(user)
                    org.add_or_update_membership(user_email)
                except Exception as e:
                    print(f"Error adding {user} to {org.login}: {e}")
                    pass
            else:
                print(f"User: {user} is already a member of the {org.login} organization or ADD_MEMBER is false")

            # Add user to team if they are a member of the org
            if org.is_member(user):
                try:
                    print(f"Adding {user} to {slug}")
                    team.add_or_update_membership(user)
                except github3.exceptions.NotFoundError:
                    print(f"User: {user} not found")
                    pass
            else:
                print(f"Skipping {user} as they are not part of the org")

        for user in state["action"]["remove"]:
            if user in GITHUB_USER_CACHE:
                user = GITHUB_USER_CACHE[user]
            else:
                print(f"User: {user} not found in GITHUB_USER_CACHE")
            print(f"Removing {user} from {slug}")
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
    ignore_users = []
    group_prefix = []
    if os.path.isfile(file):
        from yaml import load, Loader

        with open(file, "r") as f:
            data = load(f, Loader=Loader)
        if "mapping" in data:
            for d in data["mapping"]:
                if "org" in d:
                    syncmap[(d["org"], d["github"])] = d["directory"]
                else:
                    syncmap[d["github"]] = d["directory"]
        else:
            syncmap = {}
        if "allow_groups" in data:
            syncmap["allow_groups"] = data["allow_groups"]
        if "ignore_groups" in data:
            syncmap["ignore_groups"] = data["ignore_groups"]
        group_prefix = data.get("group_prefix", [])
        ignore_users = data.get("ignore_users", [])

    return (syncmap, group_prefix, ignore_users)


def get_app_installations():
    """
    Get a list of installations for this app
    :return:
    """
    with app.app_context() as ctx:
        try:
            c = ctx.push()
            gh = GitHubApp(c)
            installations = gh.app_client.app_installations
        finally:
            ctx.pop()
    return installations


@scheduler.scheduled_job(
    trigger=CronTrigger.from_crontab(CRON_INTERVAL), id="sync_all_teams"
)
def sync_all_teams():
    """
    Lookup teams in a GitHub org and synchronize all teams with your user directory
    :return:
    """

    print(f'Syncing all teams: {time.strftime("%A, %d. %B %Y %I:%M:%S %p")}')

    installations = get_app_installations()
    custom_map, _, _ = load_custom_map()
    futures = []
    install_count = 0
    github_teams_map = {}
    with ThreadPoolExecutor(max_workers=10) as exe:
        for i in installations():
            install_count += 1
            print("========================================================")
            print(f"## Processing Organization: {i.account['login']}")
            print("========================================================")
            with app.app_context() as ctx:
                try:
                    gh = GitHubApp(ctx.push())
                    client = gh.app_installation(installation_id=i.id)
                    org = client.organization(i.account["login"])
                    github_teams = org.teams()
                    for team in github_teams:
                        github_teams_map[team.name] = team.id
                    # get keycloak teams
                    keycloak = Keycloak()
                    keycloak_teams = keycloak.list_groups()
                    if "allow_groups" in custom_map and custom_map["allow_groups"]:
                        keycloak_teams = [team for team in keycloak_teams if team in custom_map["allow_groups"]]
                    if "ignore_groups" in custom_map and custom_map["ignore_groups"]:
                        keycloak_teams = [team for team in keycloak_teams if team not in custom_map["ignore_groups"]]
                    for team in keycloak_teams:
                        futures.append(
                            exe.submit(sync_team_helper_directory, team, custom_map, client, org, github_teams_map)
                        )
                except Exception as e:
                    print(f"DEBUG1: {e}")
                finally:
                    ctx.pop()
    if not install_count:
        raise Exception(f"No installation defined for APP_ID {os.getenv('APP_ID')}")
    results = []
    for future in futures:
        result = future.result()
        if result is not None:
            results.append(result)
    if TEST_MODE and EXPORT_TO_JSON and results:
        filename = f'sync_results_{time.strftime("%Y%m%d_%H%M%S")}.json'
        with open(filename, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Dry run results exported to {filename}")
    if REMOVE_ORG_MEMBERS_WITHOUT_TEAM:
        remove_org_members_without_team(installations)
    print(f'Syncing all teams successful: {time.strftime("%A, %d. %B %Y %I:%M:%S %p")}')


def remove_org_members_without_team(installations):
    for i in installations():
        with app.app_context() as ctx:
            try:
                gh = GitHubApp(ctx.push())
                client = gh.app_installation(installation_id=i.id)
                org = client.organization(i.account["login"])
                org_members = [member for member in org.members()]
                team_members = [
                    member for team in org.teams() for member in team.members()
                ]
                remove_members = list(set(org_members) - set(team_members))
                for member in remove_members:
                    print(f"Removing {member}")
                    if not TEST_MODE:
                        org.remove_membership(str(member))
            except Exception as e:
                print(f"DEBUG2: {e}")
            finally:
                ctx.pop()

def sync_team_helper_directory(team, custom_map, client, org, github_teams_map):
    print(f"Keycloak team: {team}")
    print(f"custom_map: {custom_map}")
    try:
        # if SYNCMAP_ONLY and not is_team_in_map(team, custom_map, org):
        #     print(f"skipping team {team} - not in sync map")
        #     return None
        if team in github_teams_map:
            github_team_id = github_teams_map[team]
        else:
            print(f"Team: {team} not found in github_org")
            return None
            # TODO: create github team with keycloak team template.
        return sync_team_from_directory(
            client=client,
            owner=org.login,
            team_name=team,
            team_id=github_team_id,
        )
    except Exception as e:
        print(f"Organization: {org.login}")
        print(f"Unable to sync team: {team}")
        print(f"DEBUG3: {e}")
        return None

def sync_team_helper(team, custom_map, client, org):
    print(f"Organization: {org.login}")
    try:
        if SYNCMAP_ONLY and not is_team_in_map(team.slug, custom_map, org):
            print(f"skipping team {team.slug} - not in sync map")
            return None
        return sync_team(
            client=client,
            owner=org.login,
            team_id=team.id,
            slug=team.slug,
        )
    except Exception as e:
        print(f"Organization: {org.login}")
        print(f"Unable to sync team: {team.slug}")
        print(f"DEBUG4: {e}")
        return None


def is_team_in_ignore_groups(team, custom_map):
    if "ignore_groups" in custom_map:
        ignore_groups = custom_map["ignore_groups"]
        if team.casefold() in [group.casefold() for group in ignore_groups]:
            return True
        else:
            return False
    else:
        return False

def is_team_in_map(slug, custom_map, org):
    key_with_org = (org.login, slug)
    key_without_org = slug
    if key_with_org in custom_map or key_without_org in custom_map:
        return True
    else:
        return False


def get_directory_from_slug(slug, custom_map, org):
    if not is_team_in_map(slug, custom_map, org):
        return slug
    elif (org.login, slug) in custom_map:
        return custom_map[(org.login, slug)]
    elif slug in custom_map:
        return custom_map[slug]


if "FLASK_APP" in os.environ:
    thread = threading.Thread(target=sync_all_teams)
    thread.start()

if __name__ == "__main__":
    if "FLASK_APP" in os.environ:
        app.run(
            host=os.environ.get("FLASK_RUN_HOST", "0.0.0.0"),
            port=os.environ.get("FLASK_RUN_PORT", "5000"),
        )
        
    else:
        sync_all_teams()
