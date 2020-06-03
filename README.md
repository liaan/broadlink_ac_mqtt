# Broadlink Air Conditioners to mqtt .... very much still in dev
Dunham bush aircons and might work Rinnai.  Broadlink devtype == 0x4E2a (20010)

uses Pahoo MQTT so run :

```
pip install paho-mqtt
```

simply run monitor.py , will discover all aircons and publish to specified MQTT server
errors logs to file error.log

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
run with full debugging (logs to error.log)
./monitor.py -d

Dump all discovered devices so one can copy paste
./monitor.py -S
```

to set values just publish to /aircon/mac_address/value/set  new_value  

