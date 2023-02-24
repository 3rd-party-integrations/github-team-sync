from google.oauth2 import service_account
import os
import googleapiclient.discovery

SCOPES = [
   'https://www.googleapis.com/auth/admin.directory.group.readonly',
   'https://www.googleapis.com/auth/admin.directory.group.member.readonly',
   'https://www.googleapis.com/auth/admin.directory.user.readonly'
   ]
SERVICE_ACCOUNT_FILE = '/tmp/credentials.json'

def create_service():
  credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
  delegated_credentials = credentials.with_subject(os.environ.get("ADMIN"))

  service = googleapiclient.discovery.build(
    'admin',
    'directory_v1',
    credentials=delegated_credentials)

  return service

def main():
    """Shows basic usage of the Admin SDK Directory API.
    Prints the emails and names of the first 10 users in the domain.
    """
    service = create_service().users()
    request = service.list(customer="my_customer", viewType="admin_view", projection="custom", customFieldMask="GithubUsername")
    while request is not None:
        users = request.execute()
        for u in users.get('users', []):
            githubUsername = u.get('customSchemas', {}).get("GithubUsername", {}).get("GithubUsername")
            if githubUsername:
                print(f"{u['primaryEmail']}: {githubUsername}")
        request = service.list_next(request, users)

if __name__ == '__main__':
    main()
# [END admin_sdk_directory_quickstart]