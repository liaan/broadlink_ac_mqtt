# broadlink_ac_mqtt
dunham bush aircon and should work on Rinnai

uses Pahoo MQTT so run :
pip install 
```
pip install paho-mqtt
```

simply run monitor.py , will discover all aircons and publish to specified MQTT server
errors logs to file error.log

command line arguments: 

```

-d Print debug to error file
-b runs in deamon mode

example: Run in background
./monitor.py -b
run with full debugging (logs to error.log)
./monitor.py -d
```

to set values just publish to /aircon/mac_address/value/set  new_value  

