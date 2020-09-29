#!/usr/bin/python
import os
import time
import sys
import logging
import argparse
import yaml
import paho.mqtt.client as mqtt
import tempfile
import json

sys.path.insert(1, os.path.join(os.path.dirname(os.path.realpath(__file__)),'classes','broadlink'))
import ac_db as broadlink


logger = logging.getLogger(__name__)

config  = {}	
device_objects = {}





class AcToMqtt:
	previous_status = {}
	last_update = {}
	
	def __init__(self,config):
		self.config = config
		"" 
			
	
	def discover(self):		 
		##Go discovery
		discovered_devices = broadlink.discover(timeout=5)			
		devices = {}
		
		if discovered_devices == None:
			error_msg = "No Devices Found, make sure you on the same network segment"
			logger.debug(error_msg)
			
			#print "nothing found"
			sys.exit()
			
		##Make sure correct device id 
		for device in discovered_devices:		  			
			if device.devtype == 0x4E2a:
				devices[device.status['macaddress']] = device				
		
		return devices
		

	
	def make_device_objects(self,device_list = None):
		device_objects = {}
		if  device_list == [] or device_list == None:
			error_msg = " Cannot make device objects, empty list given"
			logger.error(error_msg)			
			sys.exit()
			
		for device in device_list:			
			device_objects[device['mac']] = broadlink.gendevice(devtype=0x4E2a, host=(device['ip'],device['port']),mac = bytearray.fromhex(device['mac']), name=device['name'],update_interval = self.config['update_interval'])		
					
		return device_objects

	def stop(self):
		
		try:
			self._mqtt.disconnect()
		except:
			""
				
	def start (self,config, devices = None):
			
		self.device_objects = devices		
		self.config = config
		
		##If there no devices so throw error
		if 	devices == [] or devices == None:
			print ("No devices defined")
			logger.error("No Devices defined, either enable discovery or add them to config")
			return
		
		##we are alive ##Update PID file			
		try:
			
			for key in devices:
				device = devices[key]
				##Just check status on every update interval
				if key in self.last_update:
					if (self.last_update[key] + self.config["update_interval"]) > time.time():
						logger.debug("Timeout %s not done, so lets wait a abit : %s : %s" %(self.config["update_interval"],self.last_update[key] + self.config["update_interval"],time.time()))				
						time.sleep(0.5)
						continue
					else:
						""
						#print "timeout done"					
			
				##Get the status, the global update interval is used as well to reduce requests to aircons as they slow
				status = device.get_ac_status()						
				#print status
				if status:
					##Update last time checked
					self.last_update[key] = time.time()						
					self.publish_mqtt_info(status)		

				else:
					logger.debug("No status")				
				
		except Exception as e:					
			logger.critical(e)	
			##Something went wrong, so just exit and let system restart	
			

		return 1
			
				
	def dump_homeassistant_config_from_devices(self,devices):	
		
		if devices == {}:
			print ("No devices defined")
			sys.exit()
		
		devices_array = self.make_devices_array_from_devices(devices)
		if devices_array ==  {}:
			print ("something went wrong, no devices found")
			sys.exit()
			
		print ("**************** Start copy below ****************")
		a = []
		for key in devices_array:
			##Echo					
			device = devices_array[key]
			device['platform'] = 'mqtt'			
			a.append(device)
		print (yaml.dump({'climate':a}))
		print ("**************** Stop copy above ****************")
		
	def make_devices_array_from_devices(self,devices):
		
		devices_array = {}
		
		for device in devices.values():
			##topic = self.config["mqtt_auto_discovery_topic"]+"/climate/"+device.status["macaddress"]+"/config"
			name = ""	
			if not device.name :
				name = device.status["macaddress"]
			else:
				name = device.name.encode('ascii','ignore')
				
			device_array = { 
				"name": str(name.decode("utf-8"))
				#,"power_command_topic" : self.config["mqtt_topic_prefix"]+  device.status["macaddress"]+"/power/set"
				,"mode_command_topic" : self.config["mqtt_topic_prefix"]+  device.status["macaddress"]+"/mode_homeassistant/set"
				,"temperature_command_topic" : self.config["mqtt_topic_prefix"]  + device.status["macaddress"]+"/temp/set"
				,"fan_mode_command_topic" : self.config["mqtt_topic_prefix"] + device.status["macaddress"]+"/fanspeed_homeassistant/set"
				,"action_topic" : self.config["mqtt_topic_prefix"] +  device.status["macaddress"]+"/homeassistant/set"
				##Read values
				,"current_temperature_topic" : self.config["mqtt_topic_prefix"]  + device.status["macaddress"]+"/ambient_temp/value"				
				,"mode_state_topic" : self.config["mqtt_topic_prefix"]  + device.status["macaddress"]+"/mode_homeassistant/value"	
				,"temperature_state_topic" : self.config["mqtt_topic_prefix"]  + device.status["macaddress"]+"/temp/value"	
				,"fan_mode_state_topic" : self.config["mqtt_topic_prefix"]  + device.status["macaddress"]+"/fanspeed_homeassistant/value"	
				,"fan_modes": ["Auto","Low","Medium", "High","Turbo","Mute"]
				,"modes": ['off',"cool","heat","fan_only","dry"]
				,"max_temp":32.0
				,"min_temp":16.0
				,"temp_step": 0.5
				,"unique_id": device.status["macaddress"]
				,"device" : {"ids":device.status["macaddress"],"name":str(name.decode("utf-8")),"model":'Aircon',"mf":"Broadlink","sw":broadlink.version}				
				,"pl_avail":"online"
				,"pl_not_avail":"offline"
				,"availability_topic": self.config["mqtt_topic_prefix"]  +"LWT"
			}
			
			devices_array[device.status["macaddress"]] = device_array
			
		return devices_array

	def publish_mqtt_auto_discovery(self,devices):
		if 	devices == [] or devices == None:
			print ("No devices defined")
			logger.error("No Devices defined, either enable discovery or add them to config")
			sys.exit()
		
		##Make an array
		devices_array = self.make_devices_array_from_devices(devices)
		if devices_array == {}:
			print ("something went wrong, no devices found")
			sys.exit()

		##If retain is set for MQTT, then retain it		
		if(self.config["mqtt_auto_discovery_topic_retain"]):
			retain = self.config["mqtt_auto_discovery_topic_retain"]
			
		else: 
			retain = False	

		logger.debug("HA config Retain set to: " + str(retain))
			
		##Loop da loop all devices and publish discovery settings
		for key in devices_array:
			device = devices_array[key]			
			topic = self.config["mqtt_auto_discovery_topic"]+"/climate/"+key+"/config"
			##Publish						
			self._publish(topic,json.dumps(device), retain = retain)			
				
	def publish_mqtt_info(self,status,force_update = False) :	
		##If auto discovery is used, then always update
		if not force_update:
			force_update = True if "mqtt_auto_discovery_topic" in self.config and self.config["mqtt_auto_discovery_topic"] else False

		logger.debug("Force update is: " + str(force_update))

		##Publish all values in status
		for key in status:
			##Make sure its a string
			value = status[key]				
		 
			##check if device already in previous_status
			if not force_update and status['macaddress'] in self.previous_status:
				##Check if key in state
				if key in self.previous_status[status['macaddress']]:					
					##If the values are same, skip it to make mqtt less chatty #17
				
					if self.previous_status[status['macaddress']][key] == value:
						#print ("value same key:%s, value:%s vs : %s" %  (key,value,self.previous_status[status['macaddress']][key]))					
						continue
					else:
						""
						#print ("value NOT Same key:%s, value:%s vs : %s" %  (key,value,self.previous_status[status['macaddress']][key]))										
			
			pubResult = self._publish(self.config["mqtt_topic_prefix"] + status['macaddress']+'/'+key+ '/value',value)			
			
			
			if pubResult != None:					
				logger.warning('Publishing Result: "%s"' % mqtt.error_string(pubResult))
				if pubResult == mqtt.MQTT_ERR_NO_CONN:
					self.connect_mqtt()
					
				break
			
		##Set previous to current
		self.previous_status[status['macaddress']] = status
		
		return 

		#self._publish(binascii.hexlify(status['macaddress'])+'/'+ 'temp/value',status['temp']);
				
				
	def _publish(self,topic,value,retain=False,qos=0):
		payload = value
		logger.debug('publishing on topic "%s", data "%s"' % (topic, payload))			
		pubResult = self._mqtt.publish(topic, payload=payload, qos=qos, retain=retain)
		
		##If there error, then debug log and return not None
		if pubResult[0] != 0:				
			logger.debug('Publishing Result: "%s"' % mqtt.error_string(pubResult[0]))
			return pubResult[0]
			
	def connect_mqtt(self):
	
		##Setup client
		self._mqtt = mqtt.Client(client_id=self.config["mqtt_client_id"], clean_session=True, userdata=None)
		
		
		##Set last will and testament
		self._mqtt.will_set(self.config["mqtt_topic_prefix"]+"LWT","offline",True)
		
		##Auth		
		if self.config["mqtt_user"] and self.config["mqtt_password"]:			
			self._mqtt.username_pw_set(self.config["mqtt_user"],self.config["mqtt_password"])
				
		
		##Setup callbacks
		self._mqtt.on_connect = self._on_mqtt_connect
		self._mqtt.on_message = self._on_mqtt_message
		self._mqtt.on_log = self._on_mqtt_log
		self._mqtt.on_subscribed = self._mqtt_on_subscribe
		
		##Connect
		logger.debug("Coneccting to MQTT: %s with client ID = %s" % (self.config["mqtt_host"],self.config["mqtt_client_id"]))			
		self._mqtt.connect(self.config["mqtt_host"], port=self.config["mqtt_port"], keepalive=60, bind_address="")
		
		
		##Start
		self._mqtt.loop_start()  # creates new thread and runs Mqtt.loop_forever() in it.
			
		

	def _on_mqtt_log(self,client, userdata, level, buf):
			
		if level == mqtt.MQTT_LOG_ERR:
			logger.debug("Mqtt log: " + buf)
		
	def _mqtt_on_subscribe(self,client, userdata, mid, granted_qos):
		logger.debug("Mqtt Subscribed")
		
	def _on_mqtt_message(self, client, userdata, msg):		

		try:
			logger.debug('Mqtt Message Received! Userdata: %s, Message %s' % (userdata, msg.topic+" "+str(msg.payload)))
			##Function is second last .. decode to str #43
			function = str(msg.topic.split('/')[-2])
			address = msg.topic.split('/')[-3]
			##Make sure its proper STR .. python3  #43 .. very
			address = address.encode('ascii','ignore').decode("utf-8")
			#43 decode to force to str
			value = str(msg.payload.decode("ascii"))
			logger.debug('Mqtt decoded --> Function: %s, Address: %s, value: %s' %(function,address,value))			

		except Exception as e:	
			logger.critical(e)			
			return
			
		
		##Process received		##Probably need to exit here as well if command not send, but should exit on status update above .. grr, hate stupid python
		if function ==  "temp":	
			try:
				if self.device_objects.get(address):
					status = self.device_objects[address].set_temperature(float(value))
					
					if status :
						self.publish_mqtt_info(status)
				else:
					logger.debug("Device not on list of devices %s, type:%s" % (address,type(address)))
					return
			except Exception as e:	
				logger.critical(e)
				return
			
		elif function == "power":
			if value.lower() == "on":
				status = self.device_objects[address].switch_on()
				if status :
					self.publish_mqtt_info(status)
			elif value.lower() == "off":
				status = self.device_objects[address].switch_off()
				if status :
					self.publish_mqtt_info(status)
			else:
				logger.debug("Switch has invalid value, values is on/off received %s",value)
				return
				
		elif function == "mode":
			
			status = self.device_objects[address].set_mode(value)
			if status :
				self.publish_mqtt_info(status)
				
			else:
				logger.debug("Mode has invalid value %s",value)
				return
	
		elif function == "fanspeed":
			if value.lower() == "turbo":
				status = self.device_objects[address].set_turbo("ON")
				
				#status = self.device_objects[address].set_mute("OFF")
			elif value.lower() == "mute":				
				status = self.device_objects[address].set_mute("ON")
				
			else:
				#status = self.device_objects[address].set_mute("ON")
				#status = self.device_objects[address].set_turbo("OFF")
				status = self.device_objects[address].set_fanspeed(value)

			if status :
				self.publish_mqtt_info(status)
				
			else:
				logger.debug("Fanspeed has invalid value %s",value)
				return
				
		elif function == "fanspeed_homeassistant":
			if value.lower() == "turbo":
				status = self.device_objects[address].set_turbo("ON")
				
				#status = self.device_objects[address].set_mute("OFF")
			elif value.lower() == "mute":				
				status = self.device_objects[address].set_mute("ON")
				
			else:
				#status = self.device_objects[address].set_mute("ON")
				#status = self.device_objects[address].set_turbo("OFF")
				status = self.device_objects[address].set_fanspeed(value)
			 
			if status :
				self.publish_mqtt_info(status)
				
			else:
				logger.debug("Fanspeed_homeassistant has invalid value %s",value)
				return
				
		elif function == "mode_homekit":
			
			status = self.device_objects[address].set_homekit_mode(value)
			if status :
				self.publish_mqtt_info(status)
				
			else:
				logger.debug("Mode_homekit has invalid value %s",value)
				return
		elif function == "mode_homeassistant":
			
			status = self.device_objects[address].set_homeassistant_mode(value)
			if status :
				self.publish_mqtt_info(status)
				
			else:
				logger.debug("Mode_homeassistant has invalid value %s",value)
				return		
		elif function == "state" :
			
			if value == "refresh":
				logger.debug("Refreshing states")
				status = self.device_objects[address].get_ac_status()
			else:
				logger.debug("Command not valid: "+ value)
				return

				
			if status:
				self.publish_mqtt_info(status,force_update=True)				
			else:
				logger.debug("Unable to refresh")
				return
			return
		else:
			logger.debug("No function match")
			return
			
	def _on_mqtt_connect(self, client, userdata, flags, rc):

		"""
		RC definition:
		0: Connection successful
		1: Connection refused - incorrect protocol version
		2: Connection refused - invalid client identifier
		3: Connection refused - server unavailable
		4: Connection refused - bad username or password
		5: Connection refused - not authorised
		6-255: Currently unused.
		"""

		logger.debug('Mqtt connected! client=%s, userdata=%s, flags=%s, rc=%s' % (client, userdata, flags, rc))
		# Subscribing in on_connect() means that if we lose the connection and
		# reconnect then subscriptions will be renewed.
		sub_topic = self.config["mqtt_topic_prefix"]+ "+/+/set"
		client.subscribe(sub_topic)
		logger.debug('Listing on %s for messages' % (sub_topic))


		##LWT
		self._publish(self.config["mqtt_topic_prefix"]+'LWT','online',retain=True)

