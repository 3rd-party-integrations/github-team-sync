FROM python:3.9-alpine

LABEL version="2.7"
LABEL description="LDAP Team Sync for GitHub"
LABEL maintainer="GitHub Services <services@github.com>"

ARG TZ='UTC'

ENV DEFAULT_TZ=${TZ}

# Fix the warning where no timezone is specified
RUN cp /usr/share/zoneinfo/${DEFAULT_TZ} /etc/localtime

RUN pip install --no-cache-dir --upgrade pipenv

WORKDIR /opt/github-team-sync
COPY Pipfile Pipfile.lock .

RUN pipenv install

COPY . /opt/github-team-sync

CMD ["pipenv", "run", "flask", "run"]
