#!python3
#
# quick script to verify we can get current conditions
#


#------- edit in your ip address and port here -------

# Vince's test file
URL="http://192.168.1.18:80/conditions.json"

# David's live site
### URL="http://192.168.0.115:80/v1/current_conditions"

from datetime import datetime, timezone
import json
import requests
import sys
import time

print("\n")
print("#------- current data from the station ------")

r = requests.get(url=URL)
data = r.json()
print(data)

# print out the date+time of the information
# in human-friendly format

print("\n")
print("#------- timestamp from the returned data ------")

timestamp = datetime.fromtimestamp(data['data']['ts'], timezone.utc)
print(timestamp)

print("\n")
print("#------- current time ------")
print(datetime.now())

print("\n")
