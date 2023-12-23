# harvey2mqtt

Harvey SWS to MQTT Interface

This scrapes json information from the water softener and pushes it to MQTT.

Sequence was determined by watching network traffic to get the API endpoint, and then duplicating the AWS cognito-idp sign-in sequence to get a suitable access key / secret key to perform the API call.

This Only supports a single water softener in the results set.  If you have more, send your JSON data to confirm what it looks like, and I'll update to support it.




## TODO - autoconfig

The autoconfig JSON are not yet sent in the all-in-one harvey2mqtt.py script


## TODO - cleanup

Various messages are sent with Retain=True.  This will leave cruft behind if the process is stopped without also sending clean-up.

It might be nice to have a "--cleanup" mode that looks for any harvey2mqtt/ retained fields and wipes anything found.


