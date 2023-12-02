#!/bin/sh
#


# can only run with env variables passed in for everything that's needed
if [ -z "$MQTTHOST" ]; then echo MQTTHOST is not set; fail=1; fi
if [ -z "$MQTTUSER" ]; then echo MQTTUSER is not set; fail=1; fi
if [ -z "$MQTTPASS" ]; then echo MQTTPASS is not set; fail=1; fi
if [ -z "$HARVEYUSER" ]; then echo HARVEYUSER is not set; fail=1; fi
if [ -z "$HARVEYPASS" ]; then echo HARVEYPASS is not set; fail=1; fi

if [ $fail ]; then exit; fi



# bogus - force availability on every run
# todo - mark availability offline based on "last reported date" in the JSON payload
echo Sending fake online availability
mosquitto_pub -r -h $MQTTHOST -u $MQTTUSER -P $MQTTPASS -t 'harvey2mqtt/bridge/state' -m 'online'



CONFIGSENT=""



## TODO: auto config the max range for daysleft gauge
#
#

while :; do

  echo Awake at $( date )

  # scrape the JSON, extract the first item, remove some fluff, and save it
  echo Scraping payload
  python3 ./scrape-it.py | jq '.[]' | jq 'del(.dealer) | del(.thresholds) | del(.location)' > /tmp/payload


  # First run; extract water softener specifics and send auto-configuration with retention flag set
  if [ -z "$CONFIGSENT" ]; then
    export SERIAL=$( cat /tmp/payload | jq -r '.ssn' | tr / _ )
    export MODEL=$( cat /tmp/payload | jq -r '.dsn' )
    export SWVER=$( cat /tmp/payload | jq -r '.fwVersion' )
    export BRAND=$( cat /tmp/payload | jq -r '.brand' )

    echo Sending reconfiguration messages
    mosquitto_pub -r -h $MQTTHOST -u $MQTTUSER -P $MQTTPASS -t "harvey2mqtt/$SERIAL/availability" -m 'online'
    for a in battery leftsalt rightsalt daysleft; do
      cat autoconfig-$a.json | envsubst > /tmp/new-$a.json    
      mosquitto_pub -r -h $MQTTHOST -u $MQTTUSER -P $MQTTPASS -t "homeassistant/sensor/$SERIAL/$a/config" -f /tmp/new-$a.json
    done
  fi

  
  echo Sending payload
  mosquitto_pub -r -h $MQTTHOST -u $MQTTUSER -P $MQTTPASS -t "harvey2mqtt/$SERIAL" -f /tmp/payload


  echo Sleeping ...
  sleep 12h

done

