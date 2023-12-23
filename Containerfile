FROM docker.io/library/python:3.11-alpine
MAINTAINER Dave Baker <dave@dsb3.com>

RUN apk update && \
    apk upgrade && \
    apk add rsync bash procps coreutils && \
    apk add jq mosquitto-clients envsubst

RUN adduser -h /app -u 1000 -D appuser
COPY requirements.txt /app

RUN pip install --upgrade pip && \
    pip install -r /app/requirements.txt


COPY *.py /app
COPY json /app


USER 1000

WORKDIR /app
CMD ["/app/harvey2mqtt.py" ]


