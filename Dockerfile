FROM python:3-alpine

LABEL version="0.9"
LABEL description="LDAP Team Sync for GitHub"

MAINTAINER GitHub Services <services@github.com>

COPY . /opt/teamsync
WORKDIR /opt/teamsync
    
RUN pip install --upgrade -r requirements.txt

CMD /bin/bash
