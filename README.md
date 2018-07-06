# broadlink_ac_mqtt
dunham bush aircon and should work on Rinnai

simply run monitor.py , will discover all aircons and publish to specified MQTT server

to set values just publish to /aircon/mac_address/value/set  new_value  

Currenly only power on/off and temp supported
