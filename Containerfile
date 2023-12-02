FROM docker.io/library/python:3.11-alpine
MAINTAINER Dave Baker <dave@dsb3.com>

RUN apk update && \
    apk upgrade && \
    apk add rsync bash procps coreutils && \
    apk add jq mosquitto-clients envsubst

RUN pip install --upgrade pip && \
    pip install boto3 python-decouple && \
    pip install pycognito requests-aws4auth && \
    pip install paho-mqtt



RUN adduser -h /app -u 1000 -D appuser

COPY scrape-it.py /app
COPY entrypoint.sh /app
COPY json /app

RUN chmod a+rx /app/*.py /app/*.sh

USER 1000

WORKDIR /app
CMD ["/app/entrypoint.sh" ]


