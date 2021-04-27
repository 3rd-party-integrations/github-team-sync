import os
from distutils.util import strtobool

from .core import GitHubApp

if os.environ.get("USER_DIRECTORY", "LDAP").upper() == "LDAP":
    from .ldap import LDAPClient as DirectoryClient
elif os.environ.get("USER_DIRECTORY", "LDAP").upper() == "AAD":
    from .azuread import AzureAD as DirectoryClient
elif os.environ.get("USER_DIRECTORY", "LDAP").upper() == "OKTA":
    from .okta import Okta as DirectoryClient
elif os.environ.get("USER_DIRECTORY", "LDAP").upper() == "ONELOGIN":
    from .onelogin import OneLogin as DirectoryClient
from .version import __version__

__all__ = ["GitHubApp", "DirectoryClient"]

# Set default logging handler to avoid "No handler found" warnings.
import logging

# Set initial level to WARN. Users must manually enable logging for
# flask_githubapp to see our logging.
rootlogger = logging.getLogger(__name__)
# rootlogger.addHandler(NullHandler())

if rootlogger.level == logging.NOTSET:
    rootlogger.setLevel(logging.WARN)

CRON_INTERVAL = os.environ.get("SYNC_SCHEDULE", "0 * * * *")
# CHANGE_THRESHOLD = os.environ.get('CHANGE_THRESHOLD', 25)
# REPO_FOR_ISSUES = os.environ.get('REPO_FOR_ISSUES')
# ISSUE_ASSIGNEE = os.environ.get('ISSUE_ASSIGNEE')
# OPEN_ISSUE_ON_FAILURE = strtobool(os.environ.get('OPEN_ISSUE_ON_FAILURE', 'False'))
try:
    TEST_MODE = strtobool(os.environ.get("TEST_MODE", "False"))
except ValueError as e:
    rootlogger.warn('TEST_MODE should be set to "true" or "false"')
    rootlogger.warn(e)
    TEST_MODE = False
# Check if should add member to organization
ADD_MEMBER = strtobool(os.environ.get("ADD_MEMBER", "False"))
