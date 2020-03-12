#!/usr/bin/python

'''

This is a test-use-only driver derived from mwall's maxbotix example (thanks Matthew!)
Any hacks/errors/omissions/crimes-against-python are all mine.

1.  install this driver in bin/user
2.  define this as the station_type

    [Station]
        station_type = vincetest

3. add a stanza for this station type

   [vincetest]
      driver = user.vincetest
      max_tries = 10
      retry_wait = 5
      poll_interval = 20
      url = http://192.168.0.115:80/v1/current_conditions

4. to test the driver standalone

    # do this at least once to catch python modules you need to install
    PYTHONPATH=/home/weewx/bin python3 /home/weewx/bin/user/vincetest.py --test-driver

5. run the driver in the foreground

    /home/weewx/bin/weewxd /home/weewx/weewx.conf

6. run weewx in the background

    # probably move your old archive/weewx.sdb aside to start anew
    
    # start weewx and verify it's running
    systemctl start weewx
    systemctl status weewx

    # wait 5 minutes, watching your syslog to see it save an archive record then:
      echo 'select * from archive; | sqlite3 /home/weewx/archive/weewx.sdb
    
'''


import json
import requests
import sys
import syslog
import time

import weewx.drivers
import weewx.engine
import weewx.units

DRIVER_NAME = "vincetest"
DRIVER_VERSION = "0.0.3"

#----- test use only -------
#
# this is the test URL that is used for --test-driver
# (it must return the expected JSON, see /var/log/messages for errors)
#
# this is 'not' used when you are running the real driver,
# which uses the url setting in [vincetest] in weewx.conf
#
# this is effectively a fallback url if you have nothing in weewx.conf
# but it is necessary if you want to run --test-driver before trying
# this as a driver
TEST_URL="http://192.168.1.18:80/v1/current_conditions"

def logmsg(dst, msg):
    syslog.syslog(dst, 'vincetest: %s' % msg)

def logdbg(msg):
    logmsg(syslog.LOG_DEBUG, msg)

def loginf(msg):
    logmsg(syslog.LOG_INFO, msg)

def logerr(msg):
    logmsg(syslog.LOG_ERR, msg)

# do we need this ?
def loader(config_dict, engine):
    return vincetestDriver(**config_dict['vincetest'])

class vincetestDriver(weewx.drivers.AbstractDevice):

    # the quick poll_interval lets us run --test-driver and see info quicker
    # in general this shouldn't be faster than 60 secs, defined in weewx.conf

    def __init__(self, **stn_dict):
        loginf("driver version is %s" % DRIVER_VERSION)
        self.max_tries = int(stn_dict.get('max_tries', 5))
        self.retry_wait = int(stn_dict.get('retry_wait', 10))
        self.poll_interval = float(stn_dict.get('poll_interval', 2))
        loginf("polling interval is %s" % self.poll_interval)
        self.url = stn_dict.get('url', TEST_URL)

    # delete me
    @property
    def hardware_name(self):
        return "vincetest"

    def genLoopPackets(self):

        ntries = 0
        while ntries < self.max_tries:
            ntries += 1
            try:

                # "expecting value: line 1 column 1 (char 0)" is returned if not JSON
                # or if the file being requested isn't found.  Ideally we should key off
                # the return status from the webserver, but servers returning a default
                # web page will return 200 when they should actually 404, meaning that if
                # anything goes wrong here, syslog isn't going to tell you which failed here

                try:
                    r = requests.get(url=self.url)
                    data = r.json()
                    # print('\n') ; print(data); print('\n')    # vdsdebug
                except Exception as e:
                    loginf("failure to get data %s - try %s - (%s)" % (self.url,ntries, e))
                    if self.poll_interval:
                        time.sleep(self.poll_interval)
                    return

                # if you got to here, you should have valid JSON to parse

                # to do - punt back to the loop unless data['data']['errors'] == 'none'

                #-----------------------------------------------------------------------------
                # The WeatherLink Live returns JSON containing an array of sensors with their 
                # individual unique content, so we need to loop through the sensors one by one
                #
                # see https://weatherlink.github.io/weatherlink-live-local-api/
                #
                # the mappings below are incomplete but should be enough
                # to test that weewx will generate at least some graphs
                #-----------------------------------------------------------------------------

                for s in data['data']['conditions']:

                    if s['data_structure_type'] == 1 :
                        outTemp = s['temp']
                        outHumidity = s['hum']
                        windSpeed = s['wind_speed_last']
                        windDir = s['wind_dir_last']
                    elif s['data_structure_type'] == 2 :
                        # temp_1 to 4
                        # moist_soil_1 to 4
                        # wet_leaf_1 to 2
                        # rx_state
                        # trans_battery_flag
                        pass
                    elif s['data_structure_type'] == 3 :
                        # bar_sea_level
                        # bar_absolute
                        pass
                    elif s['data_structure_type'] == 4 :
                        inTemp = s['temp_in']
                        inHumidity = s['hum_in']

                # got the data ok so reset the flag counter
                ntries = 0

                _packet = {'dateTime': int(time.time() + 0.5),
                           'usUnits': weewx.US,
                           'outTemp': outTemp,
                           'inTemp':  inTemp,
                           'inHumidity':  inHumidity,
                           'outHumidity': outHumidity,
                           'windSpeed' : windSpeed,
                           'windDir' : windDir,
                           }
                yield _packet
                if self.poll_interval:
                    time.sleep(self.poll_interval)

            except (weewx.WeeWxIOError) as e:
                logerr("Failed attempt %d of %d to get LOOP data: %s" %
                       (ntries, self.max_tries, e))
                time.sleep(self.retry_wait)
        else:
            msg = "Max retries (%d) exceeded for LOOP data" % self.max_tries
            logerr(msg)
            raise weewx.RetriesExceeded(msg)


class Sensor():
    def __init__(self, model):
        self.model = model
        self.timeout = timeout

# To test this driver, do the following:
#   PYTHONPATH=/home/weewx/bin python3 /home/weewx/bin/user/vincetest.py
if __name__ == "__main__":
    usage = """%prog [options] [--help]"""

    def main():
        import optparse
        syslog.openlog('wee_vincetest', syslog.LOG_PID | syslog.LOG_CONS)
        parser = optparse.OptionParser(usage=usage)
        parser.add_option('--test-driver', dest='td', action='store_true',
                          help='test the driver')
        (options, args) = parser.parse_args()

        if  options.td:
            test_driver()

    def test_driver():
        import weeutil.weeutil
        driver = vincetestDriver()
        print("testing driver")
        for pkt in driver.genLoopPackets():
            print((weeutil.weeutil.timestamp_to_string(pkt['dateTime']), pkt))

    main()

#---- that's all folks ----

