FROM python:3-alpine

LABEL version="2.1"
LABEL description="LDAP Team Sync for GitHub"
LABEL maintainer="GitHub Services <services@github.com>"

ARG TZ='UTC'

ENV DEFAULT_TZ ${TZ}

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
        cargo \
        tzdata

# Fix the warning where no timezone is specified
RUN cp /usr/share/zoneinfo/${DEFAULT_TZ} /etc/localtime

RUN pip install --no-cache-dir --upgrade pipenv

RUN pipenv install

CMD pipenv run flask run
