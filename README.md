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
simply run monitor.py , will discover all aircons and publish to specified MQTT server
errors logs to file error.log

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
AC2MQTT can be utilised with Home-Assistant using the [climate.mqtt](https://www.home-assistant.io/integrations/climate.mqtt/) integration.

In order to utilise AC2MQTT in Home-Assistant there is an additional MQTT value that must be used instead of `mode` as Home-Assistant expects the modes in a specific case.

Instead of using `mode` for the mode commands, you'll need to use `homeassist` instead.

An example of a Home-Assistant config using AC2MQTT is below.

```
# configuration.yaml

climate:
  - platform: mqtt
    name: Bedroom AC
    modes:
      - "off"
      - "cool"
      - "heat"
    fan_modes:
      - "auto"
      - "high"
      - "mid"
      - "low"
    power_command_topic: "/aircon/mac_address/power/set"
    power_state_topic: "/aircon/mac_address/power/value"
    payload_off: "OFF"
    payload_on: "ON"
    current_temperature_topic: "/aircon/mac_address/temp/value"
    mode_command_topic: "/aircon/mac_address/homeassist/set"
    mode_state_topic: "/aircon/mac_address/homeassist/value"
    temperature_command_topic: "/aircon/mac_address/temp/set"
    temperature_state_topic: "/aircon/mac_address/temp/value"
    fan_mode_command_topic: "/aircon/mac_address/fanspeed/set"
    fan_mode_state_topic: "/aircon/mac_address/fanspeed/value"
    min_temp: 16
    max_temp: 32
    temp_step: 0.5
```
