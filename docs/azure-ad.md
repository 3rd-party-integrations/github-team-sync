# Azure AD

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
USER_DIRECTORY=AAD
USER_SYNC_ATTRIBUTE=username
#CHANGE_THRESHOLD=25
#OPEN_ISSUE_ON_FAILURE=true
#REPO_FOR_ISSUES=github-demo/demo-repo
#ISSUE_ASSIGNEE=githubber
SYNC_SCHEDULE=0 * * * *
TEST_MODE=false
ADD_MEMBER=falsepart of a team
REMOVE_ORG_MEMBERS_WITHOUT_TEAM=false

#######################
## Azure AD Settings ##
#######################
AZURE_TENANT_ID="<tenant_id>"
AZURE_CLIENT_ID="<client_id>"
AZURE_CLIENT_SECRET="<client_secret>"
AZURE_APP_SCOPE=".default"
AZURE_API_ENDPOINT="https://graph.microsoft.com/v1.0"
AZURE_USERNAME_ATTRIBUTE=userPrincipalName
#AZURE_USE_TRANSITIVE_GROUP_MEMBERS=true

####################
## Flask Settings ##
####################
FLASK_APP=app
FLASK_ENV=development
FLASK_RUN_PORT=5000
FLASK_RUN_HOST=0.0.0.0
```