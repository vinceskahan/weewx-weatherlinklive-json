
## WeatherFlowLiveJSON driver for weewx
This driver feeds weewx with data via periodic queries of current conditions via http

### Install via the extension installer
Usual procedure applies:
* clone or download this repo
* wee_extension --install [directory_name_or_zipfile]
* wee_config --reconfigure
* edit the WeatherLinkLiveJSON stanza in weewx.conf to set your desired url
* stop/start or restart weewx
* check your syslogs to make sure things are working

### Install manually
See the instructions in the driver itself please

### Additional files
* conditions.json = test file with valid JSON returned by /v1/current_conditions typically
* test1.py = quick script to query your Davis WeatherLink Live current conditions

### Credits
This driver is derived (with thanks) from the nice work of:
* Matthew Wall
* Bob Atchley
* and of course Tom Keffer
