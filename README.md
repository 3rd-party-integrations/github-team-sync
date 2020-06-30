# GitHub LDAP Team Sync
This utility is intended to enable synchronization between LDAP/Active Directory and GitHub.
This is particularly useful for large organizations with many teams that either do not use LDAP for authentication,
or else do not use the team sync feature for one reason or another. 
It supports both GitHub.com and GitHub Enterprise, but it will need to live in a location that can access your LDAP servers.

## Features
This utility provides the following functionality:

| Feature | Supported | Description | 
| --- | --- | --- |
| Sync Users | Yes | Add or remove users from `Teams` in GitHub to keep in sync with Active Directory groups |
| Dynamic Config | Yes | Utilize a `settings` file to derive Active Directory and GitHub settings |
| LDAP SSL | No | SSL or TLS connections. This is a WIP |
| Failure notifications | Yes | Presently supports opening a GitHub issue when sync failed. The repo is configurable. |
| Sync on new team | Yes | Synchronize users when a new team is created |
| Sync on team edit | No | This event is not processed currently, but can be easily added |
| Custom team/group maps | No | The team `slug` and group name must match. Custom mapping will be in a future release |

## Getting Started
To get started, ensure that you are using **Python 3.4+**. The following additional libraries are required:

- [ ] Flask
- [ ] github3.py
- [ ] python-ldap3
- [ ] APScheduler

Install the required libraries.

```bash
pipenv install
```

Once you have all of the requirements installed, be sure to edit the `.env` to match your environment.

### Sample `.env` for Active Directory

```env
## GitHub App settings
WEBHOOK_SECRET=development
APP_ID=12345
PRIVATE_KEY_PATH=.ssh/team-sync.pem
GHE_HOST=github.example.com

## LDAP Settings
LDAP_SERVER_HOST=dc1.example.com
LDAP_SERVER_PORT=389
LDAP_BASE_DN="DC=example,DC=com"
LDAP_USER_BASE_DN="CN=Users,DC=example,DC=example"
LDAP_GROUP_BASE_DN="OU=Groups,DC=example,DC=example"
LDAP_USER_FILTER="(objectClass=person)"
LDAP_USER_ATTRIBUTE=sAMAccountName
LDAP_USER_MAIL_ATTRIBUTE=mail
LDAP_GROUP_FILTER="(&(objectClass=group)(cn={group_name}))"
LDAP_GROUP_MEMBER_ATTRIBUTE=member
LDAP_BIND_USER="bind-user@example.com"
LDAP_BIND_PASSWORD="p4$$w0rd"
LDAP_SEARCH_PAGE_SIZE=1000

## Additional settings
CHANGE_THRESHOLD=25
OPEN_ISSUE_ON_FAILURE=true
REPO_FOR_ISSUES=github-demo/demo-repo
ISSUE_ASSIGNEE=githubber
SYNC_SCHEDULE=0 * * * *
```

### Sample `.env` for OpenLDAP
```env
## GitHub App settings
WEBHOOK_SECRET=development
APP_ID=12345
PRIVATE_KEY_PATH=.ssh/team-sync.pem
GHE_HOST=github.example.com

## LDAP Settings
LDAP_SERVER_HOST=dc1.example.com
LDAP_SERVER_PORT=389
LDAP_BASE_DN="dc=example,dc=com"
LDAP_USER_BASE_DN="ou=People,dc=example,dc=com"
LDAP_GROUP_BASE_DN="ou=Groups,dc=example,dc=com"
LDAP_USER_FILTER="(&(objectClass=person)({ldap_user_attribute}={username}))"
LDAP_USER_ATTRIBUTE=uid
LDAP_USER_MAIL_ATTRIBUTE=mail
LDAP_GROUP_FILTER="(&(objectClass=posixGroup)(cn={group_name}))"
LDAP_GROUP_MEMBER_ATTRIBUTE=memberUid
LDAP_BIND_USER="cn=admin,dc=example,dc=com"
LDAP_BIND_PASSWORD="p4$$w0rd"
LDAP_SEARCH_PAGE_SIZE=1000

## Additional settings
CHANGE_THRESHOLD=25
OPEN_ISSUE_ON_FAILURE=true
REPO_FOR_ISSUES=github-demo/demo-repo
ISSUE_ASSIGNEE=githubber
SYNC_SCHEDULE=0 * * * *
```

## Usage Examples

### Start the application from Pipenv
This example runs the app in a standard Flask environment

```bash
$ pipenv run flask run --host=0.0.0.0
```

Or you can run the app with Python directly

```bash
pipenv run python app.py
```
