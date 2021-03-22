FROM python:3-alpine

LABEL version="2.0"
LABEL description="LDAP Team Sync for GitHub"

MAINTAINER GitHub Services <services@github.com>

COPY . /opt/github-team-sync
WORKDIR /opt/github-team-sync

RUN apk add --no-cache \
        libxml2-dev \
        libxslt-dev \
        python3-dev \
        make \
        gcc \
        libffi-dev \
        build-base \
        openssl-dev \
        cargo

RUN pip install --no-cache-dir --upgrade pipenv

RUN pipenv install

CMD pipenv run flask run
