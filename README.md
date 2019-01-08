# GitHub LDAP Team Sync
This utility is intended to enable synchronization between LDAP/Active Directory and GitHub when using SAML for authentication. This is particularly useful for large organizations with many teams, including nested teams. It supports GitHub.com and GitHub Enterprise

## Features
This utility provides the following functionality:

| Feature | Supported | Description | 
| --- | --- | --- |
| List | Yes | List users in Active Directory groups or GitHub Teams |
| Add Users | Yes | Add users to `Teams` in GitHub when they are present in the AD group and not in the GitHub `Team` |
| Remove Users | Yes | Remove users from `Teams` in GitHub when they are not present in the Active Directory group |
| Sync Users | Yes | Add or remove users from `Teams` in GitHub to keep in sync with Active Directory groups |
| Dynamic Config | Yes | Utilize a `settings` file to derive Active Directory and GitHub settings |
| Email Notifications | No | Email administrators when the script fails and, optionally, succeeds. This is a WIP |
| LDAP SSL | No | SSL or TLS connections. This is a WIP |
| Slack Messaging | No | Send a notification to Slack. This is a WIP |

## Getting Started
To get started, ensure that you are using **Python 2.7** or **Python 3.4+**. The following additional libraries are required:

- [ ] PyGithub
- [ ] python-ldap
- [ ] PyYAML

Install the required libraries.

```bash
pip install -r requirements.txt
```

Once you have all of the requirements installed, be sure to edit the `settings.yml` to match your environment.

#### Sample `settings.yml`

```yaml
default:
  # This section will be used for sending email alerts
  # when sync succeeds or fails. It is currently not used
  resource_owner_email: <ghe-admin@example.com>
  email_template_success: email-template-success.html
  email_template_failure: email-template-failure.html
  # Slack notifications
  slack_token: <token>
  slack_room: #general
  slack_send_as: github-sync-robot

github:
  # This server URL should be the API endpoint for
  # GitHub. To use on github.com, simply use https://api.github.com
  #server_url: https://api.github.com
  server_url: https://github.example.com/api/v3
  token: e92ff0813a76da15f32a675dcd54ea1a97339e82

ldap:
  # A list of server hostnames or IP addresses to try connecting to
  servers:
    - dc1.example.com
    - 10.10.10.10
  # The port to connect to for LDAP
  port: 389
  # If using SSL, specify that port
  ssl_port: 636
  # Specify the path to the AD cert, if using SSL
  ssl_cert:
  # Whether or not to start TLS
  start_tls: false
  # The Base DN to lookup users
  user_base_dn: CN=Users,DC=example,DC=com
  # The Base DN for groups
  group_base_dn: OU=Groups,DC=example,DC=com
  # User Filter
  user_filter: (&(objectClass=USER)(sAMAccountName={username}))
  # Optional second User Filter
  user_filter2: (&(objectClass=USER)(dn={userdn}))
  # Group Filter
  group_filter: (&(objectClass=GROUP)(cn={group_name}))
  # Active Directory bind user. This must be in <user>@<domain> format
  bind_user: bind_user@example.com
  # The password to use for binding
  bind_password: asqw!234
```

## Usage Examples
#### Using the Help

```bash
$ python ADTeamSyncGHE.py --help
usage: ADTeamSyncGHE2.py [-h] [-r] [-a] [-g AD_GROUP] [-s] [-t TEAM] [-o ORG]
                         [-l]

optional arguments:
  -h, --help            show this help message and exit
  -r, --remove          Remove users from the GitHub Team that are not in the
                        AD group
  -a, --add             Add users in the AD group to the GitHub Team
  -g AD_GROUP, --group AD_GROUP
                        The name of the Active Directory group to sync with
                        GitHub
  -s, --sync            Perform a full sync, removing users from the GitHub
                        team that are not present in the AD group, and adding
                        users tothe GitHub Team that are in the AD group
                        missing in the Team
  -t TEAM, --team TEAM  The name of the GitHub Team to sync users with
  -o ORG, --org ORG     The name of the GitHub Organization where the Teams
                        reside
  -l, --list            List users in groups/teams and exit. No changes are
                        made
  -i INITFILE, --init INITFILE
                        Full path to settings.yml file. Default is 
                        settings.yml in your current directory
  -m MAPPING, --mapping MAPPING
                        A mappings file for teams and groups.Default is
                        mappings.yml
```

#### Listing Active Directory Group Members
This option will list members in Active Directory groups
```bash
$ python SAMLTeamSyncAD.py --list --group ADGroupA
Succesfully authenticated
AD Group: ADGroupA
---------------
ghusera
```

#### Listing GitHub Team Members
This option will list members in GitHub teams
```bash
$ python SAMLTeamSyncAD.py --list --team GHETeamA
GitHub Team: GHETeamA
---------------
primetheus
```

#### Add Users to GitHub Teams from AD
This option will only add users to GitHub teams when they are found in Active Directory. It will not remove users from teams
```bash
$ python SAMLTeamSyncAD.py --add --team GHETeamA --group ADGroupA

-- OR --
$ python SAMLTeamSyncAD.py -a -t GHETeamA -g ADGroupA
```

#### Full User Sync from Active Directory Group to GitHub Team
This option will add users to GitHub teams when found in Active Directory, as well as remove users from GitHub teams when they don't exist in the AD group. 

```bash
$ python SAMLTeamSyncAD.py --sync --team GHETeamA --group ADGroupA
```
