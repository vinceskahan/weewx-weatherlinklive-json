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

import serial   # vds: not needed in the real json/http based driver, to be deleted
import syslog
import time

import weewx.drivers
import weewx.engine
import weewx.units

DRIVER_NAME = "vincetest"
DRIVER_VERSION = "0.0.1"

def logmsg(dst, msg):
    syslog.syslog(dst, 'vincetest: %s' % msg)

def logdbg(msg):
    logmsg(syslog.LOG_DEBUG, msg)

def loginf(msg):
    logmsg(syslog.LOG_INFO, msg)

def logerr(msg):
    logmsg(syslog.LOG_ERR, msg)

def loader(config_dict, engine):
    return vincetestDriver(**config_dict['vincetest'])

schema = [('dateTime',  'INTEGER NOT NULL UNIQUE PRIMARY KEY'),
          ('usUnits',   'INTEGER NOT NULL'),
          ('interval',  'INTEGER NOT NULL'),
          ('range',     'REAL')]

weewx.units.obs_group_dict['range'] = 'group_range'
weewx.units.obs_group_dict['range2'] = 'group_range'
weewx.units.obs_group_dict['range3'] = 'group_range'
weewx.units.USUnits['group_range'] = 'inch'
weewx.units.MetricUnits['group_range'] = 'cm'
weewx.units.MetricWXUnits['group_range'] = 'cm'


class vincetestDriver(weewx.drivers.AbstractDevice):

    def __init__(self, **stn_dict):
        loginf("driver version is %s" % DRIVER_VERSION)
        self.max_tries = int(stn_dict.get('max_tries', 5))
        self.retry_wait = int(stn_dict.get('retry_wait', 10))
        self.poll_interval = float(stn_dict.get('poll_interval', 2))
        loginf("polling interval is %s" % self.poll_interval)
        self.url = stn_dict.get('url', 'http://192.168.1.18:80/conditions.json')

    @property
    def hardware_name(self):
        return "vincetest"

    def genLoopPackets(self):

        ntries = 0
        while ntries < self.max_tries:
            ntries += 1
            try:
                r = requests.get(url=self.url)
                data = r.json()
                # print('\n') ; print(data); print('\n')    # vdsdebug

                # could have multiple sensors with varying content
                # so we need to loop through the sensors individually
                #
                # also each sensor has different content
                # see https://weatherlink.github.io/weatherlink-live-local-api/

                # the mappings below are incomplete but should be enough
                # to test that weewx will generate at least some graphs

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

                _packet = {'dateTime': int(time.time() + 0.5),
                           'usUnits': weewx.US,
                           'outTemp': outTemp,
                           'inTemp':  inTemp,
                           'inHumidity':  inHumidity,
                           'outHumidity': outHumidity,
                           'windSpeed' : windSpeed,
                           'windDir' : windDir,
                           }

                #vds: commented out mwalls' example - we'd do our json query and packet construction here
                #with Sensor(self.model, self.port) as sensor:
                    #v = sensor.get_range()
                ntries = 0
                # vds - this is a clearly bogus packet for test purposes
                # _packet = {'dateTime': int(time.time() + 0.5),
                           # 'usUnits': weewx.US,
                           # 'outTemp': 31.23 }
                yield _packet
                if self.poll_interval:
                    time.sleep(self.poll_interval)
            # vds: this won't check for serial connection in a real json http query driver of course
            except (serial.serialutil.SerialException, weewx.WeeWxIOError) as e:
                logerr("Failed attempt %d of %d to get LOOP data: %s" %
                       (ntries, self.max_tries, e))
                time.sleep(self.retry_wait)
        else:
            msg = "Max retries (%d) exceeded for LOOP data" % self.max_tries
            logerr(msg)
            raise weewx.RetriesExceeded(msg)


class Sensor():

    # information about each type of sensor.  the key is the model number.  the
    # associated tuple contains the units of the value that is returned, the
    # value the sensor returns when the range is maxxed out, and the number or
    # characters (excluding the R and trailing newline) in the value string.
    MODEL_INFO = {
        'MB1040': ['inch', 254, 3], # 6in min; 254in max; 1in res
        }

    def __init__(self, model, port, baudrate=9600, timeout=1):
        self.model = model
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_port = None
        model_info = Sensor.MODEL_INFO[self.model]
        self.units = model_info[0]
        self.no_target = model_info[1]
        self.data_length = model_info[2]
        self.JSON=None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, _, value, traceback):
        self.close()

    def open(self):
        self.serial_port = serial.Serial(self.port, self.baudrate,
                                         timeout=self.timeout)

    def close(self):
        if self.serial_port is not None:
            self.serial_port.close()
            self.serial_port = None

# this is where we'd get the json and deconstruct it
    def get_range(self):
        # return value is always mm
        line = self.serial_port.read(self.data_length + 2)
        if line:
            line = line.strip()
        if line and len(line) == self.data_length + 1 and line[0] == 'R':
            try:
                v = int(line[1:])
                if v == self.no_target:
                    logdbg("no target detected: v=%s" % v)
                    v = None
                if self.units == 'inch':
                    v *= 25.4
                return v
            except ValueError as e:
                raise weewx.WeeWxIOError("bogus value: %s" % e)
        else:
            raise weewx.WeeWxIOError("unexpected line: '%s'" % line)

    def get_json(self):
        print(self.JSON)

    def getJSON(self):
        # get the data
        r = requests.et(url="http://192.168.1.18:80/conditions.json")
        data = r.json()
        if data['error']:
            print("error in json returned")
        else:
            print(data['data']['ts'])
        return data

# To test this driver, do the following:
#   PYTHONPATH=/home/weewx/bin python /home/weewx/bin/user/vincetest.py
if __name__ == "__main__":
    usage = """%prog [options] [--help]"""

    def main():
        import optparse
        syslog.openlog('wee_vincetest', syslog.LOG_PID | syslog.LOG_CONS)
        parser = optparse.OptionParser(usage=usage)
        parser.add_option('--url', dest="url", metavar="URL ",
                default='http://192.168.1.18:80/conditions.json',
                help="The URL to query.  Default is 'http://192.168.1.18:80/conditions.json'")
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

