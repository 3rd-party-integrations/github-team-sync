# GitHub Team Sync
This utility is intended to enable synchronization between GitHub and various LDAP and SAML providers.
This is particularly useful for large organizations with many teams that either use GitHub Enterprise Cloud,
do not use LDAP for authentication, or use a SAML provider other than what is natively supported.
It supports both GitHub.com, GitHub Enterprise Server (GHES) and GitHub, but it will need to live in a location that can access your LDAP servers.

## Supported user directories
- LDAP
- Active Directory
- Azure AD
- Okta
- OneLogin
- Google Workspace
- Keycloak

## Features
This utility provides the following functionality:

| Feature | Supported | Description |
| --- | --- | --- |
| Sync Users | Yes | Add or remove users from `Teams` in GitHub to keep in sync with Active Directory groups |
| Dynamic Config | Yes | Utilize a `settings` file to derive Active Directory and GitHub settings |
| LDAP SSL | Yes | SSL or TLS connections. |
| Failure notifications | Yes | Presently supports opening a GitHub issue when sync failed. The repo is configurable. |
| Sync on new team | Yes | Synchronize users when a new team is created |
| Sync on team edit | No | This event is not processed currently |
| Custom team/group maps | Yes | The team `slug` and group name will be matched automatically, unless you define a custom mapping with `syncmap.yml` |
| Force custom map | Yes | Sync only team defined in `syncmap.yml` |
| Dry run / Test mode | Yes | Run and print the differences, but make no changes |
| Nested teams/groups | No | Synchronize groups within groups. Presently, if a group is a member of another group, it is skipped |

## Creating the GitHub App on your GitHub instance
1. On your GitHub instance, visit the `settings` page on the organization that you want to own the **GitHub** App, and navigate to the `GitHub Apps` section.
    - You can access this page by visiting the following url:
      `https://<MY_GITHUB_HOSTNAME>/organizations/<MY_ORG_NAME>/settings/apps`
2. Create a new **GitHub App** with the following settings:
    - **Webhook URL**: URL of the machine on which this app has been deployed (Example: `http://ip.of.machine:3000`)
    - **Homepage URL**: URL of the machine on which this app has been deployed (Example: `http://ip.of.machine:3000`)
    - **Webhook Secret**: The webhook secret that will be or has been defined as an environment variable in your deployment environment as `WEBHOOK_SECRET`
    - **Permissions and Events**: This application will need to be able to manage teams on GitHub, so the `events` and `permissions` listed below will be required. For more information on how to create a GitHub App, please visit [https://developer.github.com/apps/building-github-apps/creating-a-github-app](https://developer.github.com/apps/building-github-apps/creating-a-github-app)
3. Once these have been configured, select the `Create GitHub App` button at the bottom of the page to continue
4. Make a note of the `APP ID` on your newly-created **GitHub App**. You will need to set this as an environment variable when configuring the app.
5. Generate and download a private key from the new App page, and store it in your deployment environment. You can either do this by saving the file directly in the environment and specifying its path with the environment variable `PRIVATE_KEY_PATH`
6. After you have created the **GitHub** App, you will need to install it to the desired **GitHub** Organizations.
    - Select `Install App`
    - Select `All Repositories` or the desired repositories you wish to watch

### Permissions and Events

#### Permissions

| Category | Attribute | Permission |
| --- | --- | --- |
| Repository permissions | `Issues` | `Read & write` |
| Repository permissions | `Metadata` | `Read-only` |
| Organization permissions | `Members` | `Read & write` |
| User permissions | `Email addresses` | `Read-only` |

#### Events

| Event | Required? | Description |
| --- | --- | --- |
| `Team` | Optional | Trigger when a new team is `created`, `deleted`, `edited`, `renamed`, etc. |

#### Azure AD Permissions
**Authentication methods**
- [ ] Username/Password
- [x] Service Principal
- [ ] Certificate
- [ ] Device Auth

This app requires the following Azure permissions:

- `GroupMember.Read.All`
- `User.Read.All`

#### Keycloak Permissions
If you have `ADMIN_FINE_GRAINED_AUTHZ` enabled, you only need the following permission for the user realm:
- `view-users`

## Getting Started
To get started, ensure that you are using **Python 3.9** (or update your `Pipfile` to the version you're running, 3.4+). The following additional libraries are required:

- [ ] Flask
- [ ] github3.py
- [ ] python-ldap3
- [ ] APScheduler
- [ ] python-dotenv
- [ ] PyYAML
- [ ] msal
- [ ] asyncio
- [ ] okta
- [ ] onelogin
- [ ] python-keycloak

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

### Sample `.env` for choosing your backend
```env
## AzureAD = AAD
## AD/LDAP = LDAP
## Okta = OKTA
## OneLogin = ONELOGIN
USER_DIRECTORY=LDAP

## Sync users on username or email attribute
USER_SYNC_ATTRIBUTE=username

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

### Sample `.env` for AzureAD
```env
AZURE_TENANT_ID="<tenant_id>"
AZURE_CLIENT_ID="<client_id>"
AZURE_CLIENT_SECRET="<client_secret>"
AZURE_APP_SCOPE="default"
AZURE_API_ENDPOINT="https://graph.microsoft.com/v1.0"
# can also be an extensionAttribute
AZURE_USERNAME_ATTRIBUTE=userPrincipalName
AZURE_USER_IS_UPN=true
# use transitive members of a group instead of direct members
AZURE_USE_TRANSITIVE_GROUP_MEMBERS=false
```

### Sample `.env` for Okta
```env
OKTA_ORG_URL=https://example.okta.com
OKTA_USERNAME_ATTRIBUTE=github_username

# token login
OKTA_ACCESS_TOKEN=asdfghkjliptojkjsj00294759

# OAuth login
OKTA_AUTH_METHOD=oauth
OKTA_CLIENT_ID=abcdefghijkl
OKTA_SCOPES='okta.users.read okta.groups.read'
OKTA_PRIVATE_KEY='{"kty": "RSA", ...}'
```

### Sample `.env` for Keycloak
```env
KEYCLOAK_USERNAME=api-account
KEYCLOAK_PASSWORD=ExamplePassword
KEYCLOAK_REALM=ExampleCorp
KEYCLOAK_ADMIN_REALM=master
KEYCLOAK_USE_GITHUB_IDP=true
```

### Sample `.env` for OneLogin
```env
ONELOGIN_CLIENT_ID='asdafsflkjlk13q33433445wee'
ONELOGIN_CLIENT_SECRET='ca3a86f982fjjkjjkfkhls'
REGION=US
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
SYNCMAP_ONLY=false
EMU_SHORTCODE=volcano

### Automatically add users missing from the organization
ADD_MEMBER=false
## Automatically remove users from the organization that are not part of a team
REMOVE_ORG_MEMBERS_WITHOUT_TEAM=false
```

### Sample `.env` setting for flask app
```env
####################
## Flask Settings ##
####################
## Default: app, comment out to run once as a script
FLASK_APP=app
## Default: production
FLASK_ENV=development
## Default: 5000
FLASK_RUN_PORT=5000
## Default: 127.0.0.1
FLASK_RUN_HOST=0.0.0.0

```

### Sample `syncmap.yml` custom mapping file
```yaml
---
mapping:
  - github: demo-team
    directory: ldap super users
    org: my github org
  - github: demo-admin-2
    directory: some other group
```

The custom map uses slugs that are lowercase. If you don't specify organization name, it will synchronize all teams with same name in any organization. 

## Usage Examples

### Start the application from Pipenv
This example runs the app in a standard Flask environment.

```bash
pipenv run flask run --host=0.0.0.0 --port=5000
```

Or you can run the app with Python directly.

```bash
pipenv run python app.py
```

## Support

⚠️ This is free and open-source software that is supported by the open-source community, and is not included as part of GitHub's official platform support.

## Credits
This project draws much from:
- [Flask-GitHubApp](https://github.com/bradshjg/flask-githubapp)
- [github3.py](https://github.com/sigmavirus24/github3.py)
- [msal](https://github.com/AzureAD/microsoft-authentication-library-for-python)
- [okta](https://github.com/okta/okta-sdk-python)
- [ldap3](https://github.com/cannatag/ldap3)
