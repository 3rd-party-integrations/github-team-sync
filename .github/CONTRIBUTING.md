# Contributing
:wave: Hi there!
We're thrilled that you'd like to contribute to this project. Your help is essential for keeping it great.

## Submitting a pull request
[Pull Requests][pulls] are used for adding new functionality, fixing bugs, improving documentation, and improving the developer experience overall.

**With write access**
1. Clone the repository (only if you do not have write access)
1. Run `pipenv install`
1. Create a new branch: `git checkout -b <username>/<my-branch-name>`
1. Setup a [GitHub App][GitHub App] and follow the instructions in the [README][README]
1. Configure your `.env` using the `.env.example` as a template
1. Make your change
1. Push and [submit a pull request][pr]
1. Pat yourself on the back and wait for your pull request to be reviewed and merged.

**Without write access**
1. [Fork][fork] and clone the repository
1. Run `pipenv install`
1. Create a new branch: `git checkout -b <username>/<my-branch-name>`
1. Setup a [GitHub App][GitHub App] and follow the instructions in the [README][README]
1. Configure your `.env` using the `.env.example` as a template
1. Make your change
1. Push to your fork and [submit a pull request][pr]
1. Pat your self on the back and wait for your pull request to be reviewed and merged.

Here are a few things you can do that will increase the likelihood of your pull request being accepted:

- Keep your change as focused as possible. If there are multiple changes you would like to make that are not dependent upon each other, consider submitting them as separate pull requests.
- Write [good commit messages](http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html).
- Please honor the `<username>/<branch-name>` naming convention to help with sorting branches in the UI
- **Test your changes**. Many users depend on this app's reliability. Please be sure to test your changes to make sure they do not break the functionality

Work in Progress pull requests are also welcome to get feedback early on, or if there is something blocking you.

- Create a branch with a name that identifies the user and nature of the changes (similar to `<username>/<branch-purpose>`)
- Open a pull request and request a review from a member of the appropriate `@github/services-delivery` and/or `@github/services-devops-engineering` teams

## Resources
- [How to Contribute to Open Source](https://opensource.guide/how-to-contribute/)
- [Using Pull Requests](https://help.github.com/articles/about-pull-requests/)
- [GitHub Help](https://help.github.com)

[pulls]: https://github.com/github/saml-ldap-team-sync/pulls
[pr]: https://github.com/github/saml-ldap-team-sync/compare
[fork]: https://github.com/github/saml-ldap-team-sync/fork
[README]: https://github.com/github/saml-ldap-team-sync#creating-the-github-app-on-your-github-instance
[GitHub App]: https://github.com/settings/apps/new
