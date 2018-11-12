FROM python:2

LABEL version="0.9"
LABEL description="LDAP Team Sync for GitHub"

MAINTAINER GitHub Services <services@github.com>

COPY . /opt/saml-ad-team-sync
WORKDIR /opt/saml-ad-team-sync

RUN apt-get update && \
    apt-get -y install lib{ldap,sasl}2-dev && \
    apt-get clean && \
    rm -fr /var/lib/apt/lists/* 
    
RUN pip install --upgrade -r requirements.txt

CMD /bin/bash
