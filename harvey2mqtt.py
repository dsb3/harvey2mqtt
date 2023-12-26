#!/usr/bin/env -S python3 -u
#
# harvey2mqtt
#
# Dave Baker <dave@dsb3.com>
#
# Given environment variables that permit logging into the Harvey SWS interface, scrape
# device information, and pass through to MQTT broker under harvey2mqtt/ prefix
#
# If JSONs are present, also inject MQTT auto-configuration entries for Home Assistant.
#
#
# CHANGELOG
#  2023-12-23  dbaker   Updated to loop and handle AWS/Cognito and MQTT in single script
#  2023-12-02  dbaker   Initial "one shot" script, requiring python and bash to update
#

import os, re, glob, time, json, socket
from datetime import datetime, timedelta


import boto3, requests
from pycognito.aws_srp import AWSSRP
from pycognito import Cognito
from requests_aws4auth import AWS4Auth

import paho.mqtt.client as mqtt


# MANDATORY : parameters for harvey interface
harveyuser = os.environ['HARVEYUSER']
harveypass = os.environ['HARVEYPASS']


# MANDATORY : parameters for mqtt broker
# (todo: these could be optional, and simply not publish messages is missing)
mqtthost = os.getenv("MQTTHOST", default="localhost")
mqttport = os.getenv("MQTTPORT", default="1883")   # note: only supports plain text at the moment

# OPTIONAL : login information for mqtt broker
# (todo: more optional fields - to include/allow mqtts:// or wss:// with ssl cert verification)
mqttuser = os.getenv("MQTTUSER", default=False)
mqttpass = os.getenv("MQTTPASS", default=False)



# debug -- because I don't know how long it is until a failure to use the refresh token
# happens, we can try to simulate a failure, and use MQTT to trigger it
simulatefail = False


# timestamp on when we want to poll for updates - this initial value
# means to poll immediately when ready
poll = datetime.now()


# The callback for when the client receives a CONNACK response from the server.
# TODO: rc=5 is a "wrong password" response.  If there are too many errors, we
# should exit and let the container running the script respawn.
def on_connect(client, userdata, flags, rc):
    print("Connected to " + mqtthost + " port " + mqttport + " with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("harvey2mqtt/poll/#")

    # Publishing in on_connect() means we are sure to resend autoconfig
    # when we start, or need to reconnect to the broker
    client.publish("harvey2mqtt/bridge/state", "online", retain=True)

    # Any time we re-connect to the MQTT broker, do a poll as soon as possible
    global poll
    poll = datetime.now()




# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))

    # crude - just look for substrings in the topic
    if ( "now" in msg.topic ):
        print ("  Received message to poll now")
        global poll
        poll = datetime.now()

    if ( "fail" in msg.topic ):
        print ("  Received message to simulate failure")
        global simulatefail
        simultatefail = True;




# In a container, the fqdn will be the full pod name.  Putting this in the client_id
# gives better logging options from the mqtt broker
client = mqtt.Client(client_id="h2m-" + socket.getfqdn())
client.on_connect = on_connect
client.on_message = on_message


# if user/pass are both defined
if mqttuser and mqttpass:
  client.username_pw_set(mqttuser, password=mqttpass)


# LWT - if enabled, we mark the bridge as offline when the program disconnects from the broker
if (os.getenv("MQTTLWT", default=False)):
  print ("Setting LWT for harvey2mqtt/bridge/state to go offline when disconnecting")
  client.will_set("harvey2mqtt/bridge/state", payload="offline", retain=True)


# Finally, we connect, and loop in the background to allow for our poller to run
client.connect(mqtthost, int(mqttport), 30)
client.loop_start()


# Debug
for file in glob.glob("./json/*.json"):
    print ("Will send autoconfig for: " + file)


# Do the first time login to the harvey interface.

## all hard coded values taken from watching traffic generated by the mobile app.  It's also
## in the Android APK if you want to disassemble it and extract the strings.

identityid = 'eu-west-1:30070db9-1478-46b4-ae5a-7d38053cd66c'
poolid     = 'eu-west-1_gtX9aUXzh'
clientid   = '67c9dtgnbjid8l9dh5juih2iq4'
loginsid   = 'cognito-idp.eu-west-1.amazonaws.com/' + poolid

# Authenticate ... this gives AccessToken, RefreshToken, etc
botoclient = boto3.client('cognito-idp', 'eu-west-1')
aws = AWSSRP(username=harveyuser, password=harveypass, pool_id=poolid, client_id=clientid, client=botoclient)
tokens = aws.authenticate_user()

# debug - print them
#tokens['AuthenticationResult']['IdToken']}

# Get Credentials ... this gives us AccessKey, SecretKeyId, etc
cog = boto3.client('cognito-identity', 'eu-west-1')


# If we want a one-shot, without option to check_token() to renew, we could just run cog.get_credentials()
# here, and not bother with the u = Cognito(...) part.
#### r = cog.get_credentials_for_identity( IdentityId = identityid, Logins={loginsid: tokens['AuthenticationResult']['IdToken']} )


# todo - switch out for constant vars for the settings
u = Cognito(poolid, clientid, id_token=tokens['AuthenticationResult']['IdToken'], refresh_token=tokens['AuthenticationResult']['RefreshToken'], access_token=tokens['AuthenticationResult']['AccessToken'])



# Setup a regex, and value extractor to format JSON files later.  We can't use
# string.format(**hdata) because the JSON file contents have too many {}
_simple_re = re.compile(r'(?<!\\)\$\{([A-Za-z0-9_]+)\}')
def getval(m):
    return hdata[m.group(1)] if m.group(1) in hdata.keys() else ""
                    


while True:

    # Sleep one minute at a time, poll when we arrive at our timestamp; then reset the timestamp into the future
    if datetime.now() > poll:
        print ( datetime.now() )
        print ("  polling ...")
        poll = datetime.now() + timedelta(minutes = 45)

        # Check and refresh our token if it's needed
        u.check_token()


        # Simulated exception to debug the failure that would otherwise take a long time to trigger
        if (simulatefail):
            # cut/paste from exception handling below
            print ("Simulated exception - attempting to re-login")
            simulatefail = False
            tokens = aws.authenticate_user()
            u = Cognito(poolid, clientid, id_token=tokens['AuthenticationResult']['IdToken'], refresh_token=tokens['AuthenticationResult']['RefreshToken'], access_token=tokens['AuthenticationResult']['AccessToken'])
            r = cog.get_credentials_for_identity( IdentityId = identityid, Logins={loginsid: u.id_token})
            print ( r['Credentials']['AccessKeyId'] )


       
        # This will (presumably) fail if the refresh token is also expired
        try:
            r = cog.get_credentials_for_identity( IdentityId = identityid, Logins={loginsid: u.id_token})
            # debug - print them
            ###  r['Credentials']['AccessKeyId']

        except botocore.errorfactory.NotAuthorizedException as e:
            print ("Failed to get credentials for identity - presumed refresh token expired")
            print (e.message)
            print (e.args)

            ### I don't know how far back to start in the process
            ### to do -- how often do we need to back to re-auth?  12 hours might be a default.
            tokens = aws.authenticate_user()
            u = Cognito(poolid, clientid, id_token=tokens['AuthenticationResult']['IdToken'], refresh_token=tokens['AuthenticationResult']['RefreshToken'], access_token=tokens['AuthenticationResult']['AccessToken'])
            r = cog.get_credentials_for_identity( IdentityId = identityid, Logins={loginsid: u.id_token})

            ## todo - if this also fails, we need to restart earlier and log in from even sooner.



        # Use the AWS4Auth to sign our request, and python requests to call the API
        auth = AWS4Auth( r['Credentials']['AccessKeyId'], r['Credentials']['SecretKey'], 'eu-west-1', 'execute-api', session_token=r['Credentials']['SessionToken'] )
        response = requests.get('https://y7xyrocicl.execute-api.eu-west-1.amazonaws.com/prod/v1/softeners/all', auth=auth)

        ## currently we just support a single water softener (json element 0)
        try:
            jsonall = json.loads(response.text)
            jsondata = jsonall[0]
        except:
            print ("Dataset is not JSON")
            print (response.text)
            client.publish("harvey2mqtt/" + hdata["SERIAL"] + "/availability", "offline")
            jsondata = {}


        ## Valid dataset??
        # todo - if invalid data is seen "too many times", just exit and allow
        # the container running this script to respawn fresh
        if "ssn" not in jsondata.keys():
            print ("Dataset is invalid")
            print (json.dumps(jsondata))
            client.publish("harvey2mqtt/" + hdata["SERIAL"] + "/availability", "offline")


        else:
            ## extract info for autoconfig json entries
            hdata = {
              "SERIAL": jsondata["ssn"].replace("/", "_"),
              "MODEL":  jsondata["dsn"],
              "SWVER":  jsondata["fwVersion"],
              "BRAND":  jsondata["brand"]
            }

            ## delete the json entries we don't want to pass through
            #  (including some of the data we just extracted)
            jsondata.pop("thresholds", None)
            jsondata.pop("dealer", None)
            jsondata.pop("location", None)
            jsondata.pop("dummy", None)
            jsondata.pop("fwVersion", None)
            jsondata.pop("dsn", None)
            jsondata.pop("brand", None)
    
    
            ## Send the (re)configuration entries
            for file in glob.glob("./json/*.json"):
                try:
                    fac = open(file, "r")
                    fcontents = fac.read()

                    # read contents, and format/interpolate ${VARS} with a hack from envsubst
                    acjson = _simple_re.sub( getval, fcontents )

                    # filename is .../directories/(type)-(name).json
                    # ... type could also be light, switch, etc, but we only expect binary_sensor or sensor
                    m = re.search(r'.*/(binary_sensor|sensor)-(\w+)\.json', file)

                    # publish home-assistant auto-config
                    # todo: also consider clean up of old autoconfig entries if we remove the "integration"
                    if m:
                        cdata = { "SERIAL": hdata["SERIAL"], "TYPE": m.group(1), "NAME": m.group(2) }
                        client.publish("homeassistant/{TYPE}/h2m_{SERIAL}/{NAME}/config".format(**cdata), acjson, retain=True)

                    fac.close()

                except Exception as e:
                    print ("Failed to send autoconfig information for " + file)
                    print (e.message)
                    print (e.args)
            
   
            ## TODO - it might be more sensible to just send data as 
            #  harvey2mqtt/0 and harvey2mqtt/1 to support multi-devices,
            #  instead of embedding the device serial number in the message
            #  topic, especially as we assume full control of the harvey2mqtt/
            #  "data structure"


            # If we have two instances running, and the other has LWT it will mark the bridge
            # offline.  So, when we publish we refresh to mark this instance online.
            # todo: it might be better to abandon the LWT configuration entirely
            client.publish("harvey2mqtt/bridge/state", "online", retain=True)


            ## Send availability
            #    todo - mark offline if jsondata["lastUpdate"] is too old
            client.publish("harvey2mqtt/" + hdata["SERIAL"] + "/availability", "online")
    
            ## Send the payload
            client.publish("harvey2mqtt/" + hdata["SERIAL"], json.dumps(jsondata), retain=True)
    
            print (json.dumps(jsondata))


    # Wait between runs
    time.sleep(60)

