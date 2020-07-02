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
| Custom team/group maps | Yes | The team `slug` and group name will be matched automatically, unless you define a custom mapping with `syncmap.yml` |
| Dry run / Test mode | Yes | Run and print the differences, but make no changes |
| Nested teams/groups | No | Synchronize groups within groups. Presently, if a group is a member of another group it is skipped |

## Permissions and Events
This application will need to be able to manage teams in GitHub,
so the following `events` and `permissions` will be required.

| Category | Attribute | Permission |
| --- | --- | --- |
| Organization permissions | `Members` | `Read & write` | 
| User permissions | `Email addresses` | `Read-only` |
| Repository permissions | `Issues` | `Read & write` |
| Repostiroy permissions | `Metadata` | `Read-only` |

| Event | Required? | Description |
| --- | --- | --- |
| `Team` | Optional | Trigger when a new team is `created`, `deleted`, `edited`, `renamed`, etc. |

## Getting Started
To get started, ensure that you are using **Python 3.4+**. The following additional libraries are required:

- [ ] Flask
- [ ] github3.py
- [ ] python-ldap3
- [ ] APScheduler
- [ ] python-dotenv
- [ ] PyYAML

Install the required libraries.

```bash
pipenv install
```

Once you have all of the requirements installed, be sure to edit the `.env` to match your environment.

### Sample `.env` for GitHub App settings
```env
## GitHub App settings
WEBHOOK_SECRET=development
APP_ID=12345
PRIVATE_KEY_PATH=.ssh/team-sync.pem
GHE_HOST=github.example.com
```

### Sample `.env` for Active Directory

```env
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
```

### Sample `.env` for OpenLDAP
```env
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
```

### Sample `.env` settings for additional settings
```env
## Additional settings
CHANGE_THRESHOLD=25
OPEN_ISSUE_ON_FAILURE=true
REPO_FOR_ISSUES=github-demo/demo-repo
ISSUE_ASSIGNEE=githubber
SYNC_SCHEDULE=0 * * * *
TEST_MODE=false
```

### Sample `syncmap.yml` custom mapping file
```yaml
---
mapping:
  - github: demo-team
    ldap: ldap super users
  - github: demo-admin-2
    ldap: some other group
```

## Usage Examples

### Start the application from Pipenv
This example runs the app in a standard Flask environment

```bash
$ pipenv run flask run --host=0.0.0.0 --port=5000
```

Or you can run the app with Python directly

```bash
pipenv run python app.py
```

## Credits
This project draws much from:
- [Flask-GitHubApp](https://github.com/bradshjg/flask-githubapp)
- [github3.py](https://github.com/sigmavirus24/github3.py)
