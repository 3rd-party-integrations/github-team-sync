# Active Directory

## Example ENV

```env
#####################
## GitHub Settings ##
#####################
WEBHOOK_SECRET=development
APP_ID=12345
PRIVATE_KEY_PATH=.ssh/team-sync.pem
#GHE_HOST=github.example.comEnterprise.

##################
## App Settings ##
##################
#VERIFY_SSL=False
USER_DIRECTORY=LDAP
USER_SYNC_ATTRIBUTE=username
#CHANGE_THRESHOLD=25
#OPEN_ISSUE_ON_FAILURE=true
#REPO_FOR_ISSUES=github-demo/demo-repo
#ISSUE_ASSIGNEE=githubber
SYNC_SCHEDULE=0 * * * *
TEST_MODE=false
ADD_MEMBER=falsepart of a team
REMOVE_ORG_MEMBERS_WITHOUT_TEAM=false

###############################
## Active Directory Settings ##
###############################
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
LDAP_USE_SSL=true
LDAP_SSL_PRIVATE_KEY=private.key
LDAP_SSL_CERTIFICATE=cert.pem
LDAP_SSL_VALIDATE=CERT_REQUIRED
LDAP_SSL_VERSION=PROTOCOL_TLS
LDAP_SSL_CA_CERTS=cacert.b64

####################
## Flask Settings ##
####################
FLASK_APP=app
FLASK_ENV=development
FLASK_RUN_PORT=5000
FLASK_RUN_HOST=0.0.0.0
```