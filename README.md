# harvey2mqtt

Harvey SWS to MQTT Interface

This scrapes json information from the water softener iLid system and publishes it to MQTT.

The login/authentication sequence was determined by intercepting and decrypting network traffic to get the API endpoint and paramters, and then
duplicating the AWS cognito-idp sign-in sequence to get a suitable access key / secret key to perform the API call.

Currently this only supports a single water (or the first?) softener in the results set.  If you have more, send me your JSON data to confirm
what it looks like, and I'll update to support multiples.



## TODO - cleanup

Various messages are sent with Retain=True.  This will leave cruft behind if the process is stopped without also sending clean-up.  The
autoconfigure entries are deleted by Home Assistant when you delete the MQTT entry - the rest will remain.

It might be nice to have a "--cleanup" mode that looks for any harvey2mqtt/ retained fields and wipes anything found.


