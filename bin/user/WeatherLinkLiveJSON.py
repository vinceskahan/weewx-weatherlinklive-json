#!/usr/bin/python3

'''

Driver for Davis WeatherLinkLive via periodic queries of current conditions through the web api

This driver is derived from mwall's maxbotix example (thanks Matthew!)
Any hacks/errors/omissions/crimes-against-python are all mine.

Note - these instructions assume you are doing a setup.py installation of weewx,
       so the paths for manually testing things will vary if you use a packaged weewx.

Installation instructions
-------------------------
1.  install this driver in bin/user as WeatherLinkLiveJSON.py
            or
    install this driver with the extension installer (preferred)

2.  define this as the station_type in weewx.conf

    [Station]
        station_type = WeatherLinkLiveJSON

3. add a stanza for this station type in weewx.conf

   [WeatherLinkLiveJSON]
      driver = user.WeatherLinkLiveJSON
      max_tries = 10
      retry_wait = 5
      poll_interval = 20
      url = http://192.168.0.115:80/v1/current_conditions

4. to test the driver standalone

    # do this at least once to catch python modules you need to install
    PYTHONPATH=/home/weewx/bin python3 /home/weewx/bin/user/WeatherLinkLiveJSON.py --test-driver

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

#-------------- start editing here -------------------------------------
#-------------- start editing here -------------------------------------
#-------------- start editing here -------------------------------------
#
# OPTIONAL - edit the url to hit here for testing with --test-driver
# (it must return the expected JSON, see /var/log/messages for errors)
#

TEST_URL="http://192.168.1.18:80/v1/current_conditions"

#-------------- stop editing here -------------------------------------
#-------------- stop editing here -------------------------------------
#-------------- stop editing here -------------------------------------

# and now for the driver itself......

DRIVER_NAME = "WeatherLinkLiveJSON"
DRIVER_VERSION = "0.0.5"

import json
import requests
import sys
import time

import weewx.drivers
import weewx.engine
import weewx.units

# support both new and old formats for weewx logging
# ref: https://github.com/weewx/weewx/wiki/WeeWX-v4-and-logging
try:
    import weeutil.logger
    import logging
    log = logging.getLogger(__name__)
    def logdbg(msg):
        log.debug(msg)
    def loginf(msg):
        log.info(msg)
    def logerr(msg):
        log.error(msg)
except ImportError:
    import syslog
    def logmsg(level, msg):
        syslog.syslog(level, 'WeatherLinkLiveJSON: %s:' % msg)
    def logdbg(msg):
        logmsg(syslog.LOG_DEBUG, msg)
    def loginf(msg):
        logmsg(syslog.LOG_INFO, msg)
    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)

def loader(config_dict, engine):
    return WeatherLinkLiveJSONDriver(**config_dict[DRIVER_NAME])

class WeatherLinkLiveJSONDriver(weewx.drivers.AbstractDevice):

    # These settings contain default values you should set in weewx.conf
    # The quick poll_interval default here lets us run --test-driver and see
    # info quicker, but in general this shouldn't be faster than 60 secs
    # in your weewx.conf settings

    def __init__(self, **stn_dict):
        self.vendor = "Davis"
        self.product = "WeatherLinkLive"
        self.model = "WeatherLinkLiveJSON"
        self.max_tries = int(stn_dict.get('max_tries', 5))
        self.retry_wait = int(stn_dict.get('retry_wait', 10))
        self.poll_interval = float(stn_dict.get('poll_interval', 2))
        self.url = stn_dict.get('url', TEST_URL)
        loginf("driver is %s" % DRIVER_NAME)
        loginf("driver version is %s" % DRIVER_VERSION)
        loginf("polling interval is %s" % self.poll_interval)

    # the hardware does not define a model so use what is in the __init__ settings
    @property
    def hardware_name(self):
        return self.model

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
                #
                # in that case, the user should manually curl the url defined in weewx.conf
                # to investigate futher to see what's happening

                try:
                    r = requests.get(url=self.url)
                    data = r.json()
                    # print('\n') ; print(data); print('\n')    # vdsdebug
                except Exception as e:
                    loginf("failure to get data %s - try %s - (%s)" % (self.url,ntries, e))
                    if self.poll_interval:
                        time.sleep(self.poll_interval)
                    return

                # to do - return back to the loop unless data['data']['errors'] == 'none'

                # if you got to here, you should have valid JSON to parse

                #-----------------------------------------------------------------------------
                # The WeatherLink Live returns JSON containing an array of sensors with their 
                # individual unique content, so we need to loop through the sensors one by one
                #
                # for details - see https://weatherlink.github.io/weatherlink-live-local-api/
                #
                # the mappings to weewx data elements below are incomplete but should be enough
                # to test that weewx will generate at least some graphs
                #
                # consult the Davis doc for units, which in general are US units
                #-----------------------------------------------------------------------------

                for s in data['data']['conditions']:

                    # keep these in the order defined in the Davis doc for readability
                    if s['data_structure_type'] == 1 :
                        outTemp = s['temp']
                        outHumidity = s['hum']
                        dewpoint = s['dew_point']
                        heatindex = s['heat_index']
                        windchill = s['wind_chill']
                        windSpeed = s['wind_speed_last']
                        windDir = s['wind_dir_last']
                        # rainRate
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
                        inDewpoint = s['dew_point_in']

                # got the data ok so reset the flag counter
                ntries = 0

                # keep these in the order defined above for readability
                _packet = {'dateTime': int(time.time() + 0.5),
                           'usUnits': weewx.US,
                           'outTemp': outTemp,
                           'outHumidity': outHumidity,
                           'dewpoint': dewpoint,
                           'heatindex': heatindex,
                           'windchill': windchill,
                           'windSpeed' : windSpeed,
                           'windDir' : windDir,
                           'inTemp':  inTemp,
                           'inHumidity':  inHumidity,
                           'inDewpoint' : dewpoint,
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


#==============================================================================
# Main program
#
# To test this driver, do the following:
#   PYTHONPATH=/home/weewx/bin python3 /home/weewx/bin/user/WeatherLinkLiveJSON.py
#
# This is not tested under python2 but is believed to work.
# This is not tested under weewx3 but is believed to work.
#==============================================================================

if __name__ == "__main__":
    usage = """%prog [options] [--help]"""

    def main():
        try:
            import logging
            import weeutil.logger
            log = logging.getLogger(__name__)
            weeutil.logger.setup('WeatherLinkLiveJSON', {} )
        except ImportError:
            import syslog
            syslog.openlog('WeatherLinkLiveJSON', syslog.LOG_PID | syslog.LOG_CONS)

        import optparse
        parser = optparse.OptionParser(usage=usage)
        parser.add_option('--test-driver', dest='td', action='store_true',
                          help='test the driver')
        (options, args) = parser.parse_args()

        if  options.td:
            test_driver()

    def test_driver():
        import weeutil.weeutil
        driver = WeatherLinkLiveJSONDriver()
        print("testing driver")
        for pkt in driver.genLoopPackets():
            print((weeutil.weeutil.timestamp_to_string(pkt['dateTime']), pkt))

    main()

#---- that's all folks ----

