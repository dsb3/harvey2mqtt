# harvey2mqtt

Harvey SWS to MQTT Interface

This scrapes json information from the water softener and pushes it to MQTT.

Sequence was determined by watching network traffic to get the API endpoint, and then duplicating the AWS cognito-idp sign-in sequence to get a suitable access key / secret key to perform the API call.


Only supports a single water softener in the results set.  If you have more, send your JSON data and I'll update to support it.


MQTT is hacked together to push data for homeassist to autoconfigure entries


