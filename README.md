# Broadlink Air Conditioners to mqtt .... very much still in dev
Dunham bush aircons and might work Rinnai.  Broadlink devtype == 0x4E2a (20010)

uses Pahoo MQTT so run :

```
pip install paho-mqtt
```
1. copy sample_config.ym_ to config.yml
2. Edit config to match your enviroment
3. run ./monitor.py

If you lazy and just want to copy and paste your devices, use the -S option and discovered devicesconfig will be printed to screen for copy/paste
Example:
```
root@berry1:~/ac_db# ./monitor.py -S
*********** start copy below ************
devices:
- ip: 10.0.0.227
  mac: b4430da741af
  name: Office
  port: 80

*********** stop copy above ************


```


command line arguments: 

```

optional arguments:
  -h, --help            show this help message and exit
  -d, --debug           set logging level to debug
  -s, --discover        Discover devices
  -S, --discoverdump    Discover devices and dump config
  -Hd, --dumphaconfig   Dump the devices as a HA manual config entry
  -b, --background      Run in background
  -ms MQTTSERVER, --mqttserver MQTTSERVER
                        Mqtt Server, Default:
  -mp MQTTPORT, --mqttport MQTTPORT
                        Mqtt Port
  -mU MQTTUSER, --mqttuser MQTTUSER
                        Mqtt User
  -mP MQTTPASSWORD, --mqttpassword MQTTPASSWORD
                        Mqtt Password
  -Ma MQTT_AUTO_DISCOVERY_TOPIC, --mqtt_auto_discovery_topic MQTT_AUTO_DISCOVERY_TOPIC
                        If specified, will Send the MQTT autodiscovery config
                        for all devices to topic
  


example: Run in background
./monitor.py -b
run with full debugging (logs to ac_to_mqtt.log in folder where monitor.py is located)
./monitor.py -d

Dump all discovered devices so one can copy paste
./monitor.py -S
```

to set values just publish to /aircon/mac_address/option/value/set  new_value  :
```
/aircon/b4430dce73f1/temp/set 20
```

# Home Assistant (www.home-assistant.io) Options

### Now MQTT autodiscovery workes for HomeAsssitant  (https://www.home-assistant.io/docs/mqtt/discovery/)

#### Enabling MQTT autodisocvery:

1. Edit config.yml and add below if not there. If already there, then make sure prefix matches configuration.yml file settings (in HA) 

```
mqtt:
  discovery: true
  discovery_prefix: homeassistant
  
```


**To add a device manually useing the configuration.yml in HA you can create a easy config to copy/paste by using -Hd (--dumphaconfig) . Just make sure your config.yml is updated with correct settings before running.**

This is also nice to verify the autoconfig is correct that gets sent to HA using mqtt autoconfig

Example:

```
root@berry1:~/ac_db# ./monitor.py -Hd
 
*********** start copy below ****************
climate:
- action_topic: /aircon/b4430dce73f1/homeassistant/set
  current_temperature_topic: /aircon/b4430dce73f1/ambient_temp/value
  fan_mode_command_topic: /aircon/b4430dce73f1/fanspeed_homeassistant/set
  fan_mode_state_topic: /aircon/b4430dce73f1/fanspeed_homeassistant/value
  fan_modes:
  - Auto
  - Low
  - Medium
  - High
  max_temp: 32.0
  min_temp: 16.0
  mode_command_topic: /aircon/b4430dce73f1/mode_homeassistant/set
  mode_state_topic: /aircon/b4430dce73f1/mode_homeassistant/value
  modes:
  - 'off'
  - cool
  - heat
  - fan_only
  - dry
  name: Living Room
  platform: mqtt
  precision: 0.5
  temperature_command_topic: /aircon/b4430dce73f1/temp/set
  temperature_state_topic: /aircon/b4430dce73f1/temp/value


```
