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


command line arguments: 

```

optional arguments:  This should overide the config file (not tested )
  -h, --help            show this help message and exit
  -d, --debug           set logging level to debug
  -s, --discover        Discover devices
  -S, --discoverdump    Discover devices and dump config
  -b, --background      Run in background
  -ms MQTTSERVER, --mqttserver MQTTSERVER
                        Mqtt Server, Default:
  -mp MQTTPORT, --mqttport MQTTPORT
                        Mqtt Port
  -mU MQTTUSER, --mqttuser MQTTUSER
                        Mqtt User
  -mP MQTTPASSWORD, --mqttpassword MQTTPASSWORD
                        Mqtt Password
  


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

*** Now MQTT autodiscovery workes for HomeAsssitant  (https://www.home-assistant.io/docs/mqtt/discovery/)

Enable MQTT autodisocvery:

Edit config.yml and add below if not there. If already there, then make sure prefix matches config.yml file settings

```
mqtt:
  discovery: true
  discovery_prefix: homeassistant
  
```

