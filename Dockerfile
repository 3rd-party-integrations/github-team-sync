FROM python:3.9-alpine

LABEL version="2.7"
LABEL description="LDAP Team Sync for GitHub"
LABEL maintainer="GitHub Services <services@github.com>"

ARG TZ='Asia/Kolkata'

ENV DEFAULT_TZ=${TZ}
# Force Python to run in unbuffered mode to ensure logs appear immediately in containers
ENV PYTHONUNBUFFERED=1

# Fix the warning where no timezone is specified
RUN cp /usr/share/zoneinfo/${DEFAULT_TZ} /etc/localtime

RUN apk add --no-cache gcc musl-dev libffi-dev

RUN pip install --no-cache-dir --upgrade pipenv

RUN echo "setuptools<72" > /tmp/pip-constraints.txt
ENV PIP_CONSTRAINT=/tmp/pip-constraints.txt

WORKDIR /opt/github-team-sync
COPY Pipfile Pipfile.lock ./

RUN pipenv install

COPY . /opt/github-team-sync
CMD ["pipenv", "run", "flask", "run"]
