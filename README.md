# Broadlink Air Conditioners to mqtt .... very much still in dev
Dunham bush aircons and might work Rinnai.  Broadlink devtype == 0x4E2a (20010)

## Requirements
```
python
python-pip
```

### Python pip Requirements
```
paho-mqtt
pyyaml
pycrypto
```
Install the python pip packages with `python pip install paho-mqtt pyyaml pycrypto`

## Usage

1. copy sample_config.ym_ to config.yml
2. Edit config to match your enviroment
3. run ./monitor.py

If you lazy and just want to copy and paste your devices, use the -S option and discovered devicesconfig will be printed to screen for copy/paste

## Command line arguments: 

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

# Docker
AC2MQTT can also run as a Docker container.
## Usage

Here is a docker-compose snippet to help you get started creating a container.

### docker-compose

Compatible with docker-compose v2+ schemas.

```
---
version: "2.1"
services:
  ac2mqtt:
    image: wjbeckett/broadlink_ac
    container_name: ac2mqtt
    hostname: ac2mqtt
    network_mode: host
    volumes:
      - <path to data>:/config
    restart: unless-stopped

```
The container needs to use the host network to ensure it runs on the same subnet as your AC units.


Once the container starts you will need to edit your config.yml file with your MQTT host address and username/password.

After you have edited the config.yml file, restart your container. 

You can then use a program like [MQTT Explorer](http://mqtt-explorer.com/) to watch for the `aircon` topic to start populating with your AC unit mac addresses.

# MQTT Usage

to set values just publish to /aircon/mac_address/option/value/set  new_value  :
```
/aircon/b4430dce73f1/temp/set 20
``` 

## MQTT values
| Parameter | Accepted Value | Function |
| :----: | --- | --- |
| `power` | `ON` or `OFF` | Power on/off the AC unit|
| `temp` | `16` to `32` | Sets the AC temperature. Values are between 16 and 32 and in 0.5 increments. e.g. 20.5 |
| `mode` | `AUTO`, `HEATING`, `COOLING`, `OFF` | Sets the mode of the AC unit |
| `homeassist` | `auto`, `heat`, `cool`, `off` | Same as `mode` but specifically for Home-Assistant. For Home-Assistant integration see [home-assistant](https://github.com/liaan/broadlink_ac_mqtt#home-assistant) |
| `fanspeed` | `AUTO`, `LOW`, `MID`, `HIGH` | Sets the fans speed for the AC unit |

# Home-Assistant
AC2MQTT can be utilised with Home-Assistant using MQTT auto-discovery (https://www.home-assistant.io/docs/mqtt/discovery/)

To enable MQTT autodisocvery:

Edit config.yml and add below if not there. If already there, then make sure prefix matches configuration.yml file settings (in Home-Assistant)

```
mqtt:
  discovery: true
  discovery_prefix: homeassistant
  
```