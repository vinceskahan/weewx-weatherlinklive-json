#
# installer for WeatherLinkLiveJSON driver
#
# (derived with thanks from the WS6in1 driver installer by Bob Atchley)
#

from setup import ExtensionInstaller

def loader():
    return WeatherLinkLiveJSONInstaller()

class WeatherLinkLiveJSONInstaller(ExtensionInstaller):
    def __init__(self):
        super(WeatherLinkLiveJSONInstaller, self).__init__(
            version="0.0.5",
            name='WeatherLinkLiveJSON',
            description='Collect data from WeatherLinkLive by periodic queries of current_conditions',
            author="Vince Skahan",
            author_email="vince.skahan@gmail.com",
            config={
                'WeatherLinkLiveJSON': {
                    'driver': 'user.WeatherLinkLiveJSON',
                    'max_tries':'10',
                    'retry_wait': '5',
                    'poll_interval': 60,
                    'url': 'http://your_weatherlink_live_ip_here:80/v1/current_conditions'
                }
            },
            files=[('bin/user', ['bin/user/WeatherLinkLiveJSON.py'])]
        )
