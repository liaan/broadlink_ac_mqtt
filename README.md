# ALERT:!!!   Archived

There are simply to many new aircons that don't work with this code anymore, and enough other forks to keep older AC's going

also, my AC's are working fine.. so no motiviation to keep this up to date

------------------------------------------------------------------------------



# Broadlink Air Conditioners to mqtt  
##  Telegram Group 
https://t.me/+1Xw9Kwr2P7k2YjY0 


## Donations 

[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](http://www.paypal.me/liaanvdm)

#### BTC Donations: 1DaGtHqaYvvDrXcpiNoNkNJgkmm6dEp7Lq
----------------------------------------------------------------------------------------------------------------
## Docker version:  https://github.com/broadlink-ac/broadlink_ac_mqtt_docker

#### Air Conditioners compatibility 
  * Dunham bush --> Tested and working

  * Rcool Solo --> Tested and working
  * Akai 9000BTU  --> Tested and working
  * Rinnai  --> Tested and working .. autodiscovery name seems to be buggy
  * Kenwood --> In Testing
  * Tornado X (2019 and up) --> Tested and working
    * Tornado top wifi 12x a.c Tested and reported as working
  * AUX ASW-H09A4/DE-R1DI (Broadlink module) --> Tested and working
  * Ballu BSUI/IN-12HN8 (with intergated Wi-Fi module and AC Freedom app). --> Tested and working
  * In theory any Broadlink devtype == 0x4E2a (20010) using the AC Freedom APP

## Installation: 
```
pip install -r requirements.txt 
```

1. copy sample_config.yml to config.yml under /settings folder or the data-dir you speified
2. Edit config to match your enviroment
3. run ./monitor.py (or python monitor.py)

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
**Note:**  
Some devices (confirmed on AUX  conditioner) return device **name** in chineese, like '奥克斯空调'.  
Device renaming in 'AC Freedom' app does not affect. You can see empty **name** in '-S' option output or any artifacts.  
So in case '-S' returns empty value and you plan to use HASS autodiscovery - the best way to configure yout device manually in config.yml and set 'self_discovery: False'.

command line arguments: 

```

optional arguments:
optional arguments:
  -h, --help            show this help message and exit
  -Hd, --dumphaconfig   Dump the devices as a HA manual config entry
  -Hat MQTT_AUTO_DISCOVERY_TOPIC, --mqtt_auto_discovery_topic MQTT_AUTO_DISCOVERY_TOPIC
                        If specified, will Send the MQTT autodiscovery config
                        for all devices to topic
  -b, --background      Run in background
  -S, --discoverdump    Discover devices and dump config
  -ms MQTTSERVER, --mqttserver MQTTSERVER
                        Mqtt Server, Default:
  -mp MQTTPORT, --mqttport MQTTPORT
                        Mqtt Port
  -mU MQTTUSER, --mqttuser MQTTUSER
                        Mqtt User
  -mP MQTTPASSWORD, --mqttpassword MQTTPASSWORD
                        Mqtt Password
  -s, --discover        Discover devices
  -d, --debug           Set logging level to debug
  -v, --version         Print Versions
  -dir DATA_DIR, --data_dir DATA_DIR
                        Data Folder -- Default to folder script is located
  -c CONFIG, --config CONFIG
                        Config file path -- Default to folder script is located + 'config.yml'

  

example: Run in background
./monitor.py -b
run with full debugging (logs to log/out.log )
./monitor.py -d

Dump all discovered devices so one can copy paste
./monitor.py -S
```

to set values just publish to /aircon/mac_address/option/value/set  new_value  :
```
/aircon/b4430dce73f1/temp/set 20
```

# Home Assistant (www.home-assistant.io) Options

### Now MQTT autodiscovery works for HomeAsssitant  (https://www.home-assistant.io/docs/mqtt/discovery/)

#### Enabling MQTT autodiscovery:

1. Edit config.yml and add below if not there. If already there, then make sure prefix matches configuration.yml file settings (in HA) 

```
mqtt:
  discovery: true
  auto_discovery_topic: homeassistant
  
```


**To add a device manually using the configuration.yml in HA you can create a easy config to copy/paste by using -Hd (--dumphaconfig) . Just make sure your config.yml is updated with correct settings before running.**

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
  - Turbo
  - Mute
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
