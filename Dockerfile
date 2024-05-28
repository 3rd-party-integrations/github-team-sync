FROM python:3.9-alpine

LABEL version="2.7"
LABEL description="LDAP Team Sync for GitHub"
LABEL maintainer="GitHub Services <services@github.com>"

ARG TZ='UTC'

ENV DEFAULT_TZ ${TZ}

RUN apk add --no-cache \
        libxml2-dev \
        libxslt-dev \
        python3-dev \
        make \
        gcc \
        libffi-dev \
        build-base \
        openssl-dev \
        cargo \
        tzdata

# Fix the warning where no timezone is specified
RUN cp /usr/share/zoneinfo/${DEFAULT_TZ} /etc/localtime

RUN pip install --no-cache-dir --upgrade pipenv

WORKDIR /opt/github-team-sync
COPY Pipfile Pipfile.lock .

RUN pipenv install

COPY . /opt/github-team-sync

CMD pipenv run flask run
