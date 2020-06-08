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
sys.path.insert(1, os.path.join(os.path.dirname(__file__), './ext/broadlink'))
import ac_db as broadlink

pid = str(os.getpid())
pidfile = tempfile.gettempdir() + "/ac_to_mqtt.pid"
pid_stale_time = 60
pid_last_update = 0
logger = logging.getLogger(__name__)
debug = False
softwareversion = "1.0.7"
 

#*****************************************  Main Class ************************************************
class AcToMqtt:
	config  = {}
	 
	device_objects = {}
	previous_status = {}
	last_update = {};
	
	def __init__(self,config):
		self.config = config
		"" 
		 
	def discover(self):		 
		##Go discovery
		discovered_devices = broadlink.discover(timeout=5)			
		devices = {}
		
		if discovered_devices == None:
			error_msg = "No Devices Found, make sure you on the same network segment"
			if self.config["daemon_mode"]:
				logger.debug(error_msg)
			else:
				print (error_msg)
			#print "nothing found"
			sys.exit()
			
		##Make sure correct device id 
		for device in discovered_devices:		  			
			if device.devtype == 0x4E2a:
				devices[device.status['macaddress']] = device
				
		
		return devices
			
		
				
		#device = self.devices["a"]
		#self.device = broadlink.ac_db(host=device.host, mac=device.mac,debug=False)				
		#logger.debug(self.device.host)
		#logger.debug( "Device type detected: " +self.device.type)
		#logger.debug( "Starting device test()")			
		
	
	def print_yaml_discovered_devices(self):	
		print (yaml.dump(self.discover_devices));
		
	def make_device_objects(self,device_list = None):
		device_objects = {}
		if  device_list == [] or device_list == None:
			error_msg = " Cannot make device objects, empty list given"
			logger.error(error_msg)
			print (error_msg)
			sys.exit()
			
		for device in device_list:			
			device_objects[device['mac']] = broadlink.gendevice(devtype=0x4E2a, host=(device['ip'],device['port']),mac = bytearray.fromhex(device['mac']), name=device['name'],update_interval = self.config['update_interval'])		
			
		
		return device_objects
	
	
	def do_loop (self,config, devices = None):
		 	
		self.device_objects = devices		
		self.config = config
		
		##If there no devices so throw error
		if 	devices == [] or devices == None:
			print ("No devices defined")
			logger.error("No Devices defined, either enable discovery or add them to config")
			sys.exit()
		
		while True:
			##we are alive ##Update PID file
			touch_pid_file()	
			
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
						self.last_update[key] = time.time();
						
						self.publish_mqtt_info(status);
						
					else:
						logger.debug("No status")
				
				
			except Exception as e:					
				logger.critical(e)	
				##Something went wrong, so just exit and let system restart	
				continue;
			
			##Exit if not daemon_mode
			if self.config["daemon_mode"] != True:
				break
			##Set last update 
				
	def dump_homeassistant_config_from_devices(self,devices):	
		
		if devices == {}:
			print ("No devices defined")
			sys.exit()
		
		devices_array = self.make_devices_array_from_devices(devices)
		if devices_array ==  {}:
			print ("something went wrong, no devices found")
			sys.exit();
			
		print ("*********** Start copy below ****************")
		a = []
		for key in devices_array:
			##Echo					
			device = devices_array[key]
			device['platform'] = 'mqtt'			
			a.append(device)
		print (yaml.dump({'climate':a}))
		print ("*********** Stop copy here ****************")
		
	def make_devices_array_from_devices(self,devices):
		
		devices_array = {}
		
		for device in devices.values():
			topic = self.config["mqtt_auto_discovery_topic"]+"/climate/"+device.status["macaddress"]+"/config"
			if not device.name :
				name = device.status["macaddress"]
			else:
				name = device.name.encode('ascii','ignore') 
				
				
			device_array = { 
				"name": name
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
				,"fan_modes": ["Auto","Low","Medium", "High"]
				,"modes": ['off',"cool","heat","fan_only","dry"]
				,"max_temp":32.0
				,"min_temp":16.0
				,"precision": 0.5
			}
			
			devices_array[device.status["macaddress"]] = device_array
			
		return devices_array
	
	def publish_mqtt_auto_discovery(self,devices):
		if 	devices == [] or devices == None:
			print ("No devices defined")
			logger.error("No Devices defined, either enable discovery or add them to config");
			sys.exit()
		
		##Make an array
		devices_array = self.make_devices_array_from_devices(devices)
		if devices_array == {}:
			print ("something went wrong, no devices found")
			sys.exit();		
		
		for key in devices_array:
			device = devices_array[key]			
			topic = self.config["mqtt_auto_discovery_topic"]+"/climate/"+key+"/config"
			##Publish
			self._publish(topic,json.dumps(device))
			
		 
		#sys.exit();	
		
		
				
	def publish_mqtt_info(self,status):
		
		##Publish all values in status
		for key in status:
			value = status[key]			
			##check if device already in previous_status
			if status['macaddress'] in self.previous_status:
				##Check if key in state
				if key in self.previous_status[status['macaddress']]:					
					##If the values are same, skip it to make mqtt less chatty #17
					if self.previous_status[status['macaddress']][key] == value:
						#print ("value same key:%s, value:%s vs : %s" %  (key,value,self.previous_status[status['macaddress']][key]))					
						continue
					else:
						""
						#print ("value NOT Same key:%s, value:%s vs : %s" %  (key,value,self.previous_status[status['macaddress']][key]))						
				
				
			pubResult = self._publish(self.config["mqtt_topic_prefix"] + status['macaddress']+'/'+key+ '/value',bytes(status[key]))			
			
			if pubResult != None:					
				logger.warning('Publishing Result: "%s"' % mqtt.error_string(pubResult))
				if pubResult == mqtt.MQTT_ERR_NO_CONN:
					self._connect_mqtt();
					
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
			
	def _connect_mqtt(self):
		
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
			logger.debug("Mqtt log" + buf)
		
	def _mqtt_on_subscribe(self,client, userdata, mid, granted_qos):
		logger.debug("Mqtt Subscribed")
		
	def _on_mqtt_message(self, client, userdata, msg):		
	
		try:
			logger.debug('Mqtt Message Received! Userdata: %s, Message %s' % (userdata, msg.topic+" "+str(msg.payload)))
			##Function is second last
			function = msg.topic.split('/')[-2]			
			address = msg.topic.split('/')[-3]
			address = address.encode('ascii','ignore')
			value = msg.payload
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
				logger.debug("Switch on has invalid value, values is on/off received %s",value)
				return
				
		elif function == "mode":
			
			status = self.device_objects[address].set_mode(value)
			if status :
				self.publish_mqtt_info(status)
				
			else:
				logger.debug("Mode on has invalid value %s",value)
				return
		elif function == "fanspeed":
			
			status = self.device_objects[address].set_fanspeed(value)
			if status :
				self.publish_mqtt_info(status)
				
			else:
				logger.debug("Fanspeed on has invalid value %s",value)
				return
				
		elif function == "fanspeed_homeassistant":
			
			status = self.device_objects[address].set_fanspeed(value)
			if status :
				self.publish_mqtt_info(status)
				
			else:
				logger.debug("Fanspeed on has invalid value %s",value)
				return
				
		elif function == "mode_homekit":
			
			status = self.device_objects[address].set_homekit_mode(value)
			if status :
				self.publish_mqtt_info(status)
				
			else:
				logger.debug("Fanspeed on has invalid value %s",value)
				return
		elif function == "mode_homeassistant":
			
			status = self.device_objects[address].set_homeassistant_mode(value)
			if status :
				self.publish_mqtt_info(status)
				
			else:
				logger.debug("Fanspeed on has invalid value %s",value)
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
		sub_topic = self.config["mqtt_topic_prefix"]+"+/+/set"
		client.subscribe(sub_topic)
		logger.debug('Listing on %s for messages' % (sub_topic))
		##LWT
		self._publish(self.config["mqtt_topic_prefix"]+'LWT','online')
#*****************************************************************************************************
#*****************************************  Get going methods ************************************************

def discover_and_dump_for_config(config):
	actomqtt = AcToMqtt(config);
	devices = actomqtt.discover();
	yaml_devices = []
	if devices == {}:
		print ("No devices found, make sure you are on same network broadcast segment as device/s")
		sys.exit()
	
	print ("*********** start copy below ************")
	for device in devices.values():
		yaml_devices.append(
			{'name':device.name.encode('ascii','ignore'),
			'ip':device.host[0]
			,'port':device.host[1]
			,'mac':device.status['macaddress']}
			)
		
	print (yaml.dump({'devices':yaml_devices}))
	print ("*********** stop copy above ************")
		
	sys.exit();
	
def read_config():
	
	config = {} 
	##Load config
	
	with open(os.path.dirname(os.path.realpath(__file__))+'/config.yml', "r") as ymlfile:
		config_file = yaml.load(ymlfile,Loader=yaml.SafeLoader)
	 
	##Service settings
	config["daemon_mode"] = config_file["service"]["daemon_mode"]
	config["update_interval"] = config_file["service"]["update_interval"]	
	config["self_discovery"] = config_file["service"]["self_discovery"]	
	
	##Mqtt settings
	config["mqtt_host"] = config_file["mqtt"]["host"]
	config["mqtt_port"] = config_file["mqtt"]["port"]
	config["mqtt_user"]= config_file["mqtt"]["user"]
	config["mqtt_password"] = config_file["mqtt"]["passwd"]
	config["mqtt_client_id"] = config_file["mqtt"]["client_id"]	
	config["mqtt_topic_prefix"] = config_file["mqtt"]["topic_prefix"]
	config["mqtt_auto_discovery_topic"] = config_file["mqtt"]["auto_discovery_topic"]
	
	if config["mqtt_topic_prefix"] and config["mqtt_topic_prefix"].endswith("/") == False:
		config["mqtt_topic_prefix"] = config["mqtt_topic_prefix"] + "/"
		
	
	##Devices	 
	if config_file['devices'] != None:
		config["devices"] = config_file['devices']
	else:
		config["devices"] = None

	
	
	return config
				
def touch_pid_file():
	global pid_last_update
	
	##No need to update very often
	if(pid_last_update + pid_stale_time -2 > time.time()):	
		return
	
	pid_last_update = time.time() 
	with open(pidfile, 'w') as f:
		f.write("%s,%s" % (os. getpid() ,pid_last_update))	
	
		
def stop_if_already_running():
	
	
	##Check if there is pid, if there is, then check if valid or stale .. probably should add process id for race conditions but damn, this is a simple scripte.....
	if os.path.isfile(pidfile):

		logger.debug("%s already exists, checking if stale" % pidfile)
		##Check if stale
		f = open(pidfile, 'r') 
		if f.mode =="r":
			contents =f.read()
			contents = contents.split(',')
			
			##Stale, so go ahead
			if (float(contents[1])+ pid_stale_time) < time.time():
				logger.info("Pid is stale, so we'll just overwrite it go on")								
				
			else:
				logger.debug("Pid is still valid, so exit")												
				sys.exit()
	 
	##Write current time
	touch_pid_file();
	
	
#################  Main startup ####################
				
def main():
		
		##Just some defaults
		##Defaults		
		daemon_mode = False;		
		devices = {}			 
		
				
        # Argument parsing
		parser = argparse.ArgumentParser(		
			description='Aircon To MQTT v%s : Mqtt publisher of Duhnham Bush on the Pi.' % softwareversion			
		)
		
		##HomeAssistant stuff
		parser.add_argument("-Hd", "--dumphaconfig",help="Dump the devices as a HA manual config entry",action="store_true",default=False)
		parser.add_argument("-Hat", "--mqtt_auto_discovery_topic", help="If specified, will Send the MQTT autodiscovery config for all devices to topic")
		parser.add_argument("-b", "--background", help="Run in background",action="store_true",default=False)
		##Config helpers
		parser.add_argument("-S", "--discoverdump", help="Discover devices and dump config",action="store_true",default=False)
		
		#parser.add_argument("-dh", "--devicehost", help='Aircon Host IP, Default: %s ' % ac_host)
		#parser.add_argument("-dm", "--devicemac", help="Ac Mac Address, Default:  %s" % ac_mac)
		##MQTT stuff
		parser.add_argument("-ms", "--mqttserver", help='Mqtt Server, Default:')
		parser.add_argument("-mp", "--mqttport", help="Mqtt Port" )
		parser.add_argument("-mU", "--mqttuser", help="Mqtt User" )
		parser.add_argument("-mP", "--mqttpassword", help="Mqtt Password" )
		
		##Generic
		parser.add_argument("-s", "--discover", help="Discover devices",action="store_true",default=False)
		parser.add_argument("-d", "--debug", help="set logging level to debug",action="store_true",default=False)
		parser.add_argument("-v", "--version", help="Print Verions",action="store_true")
				
		
		args = parser.parse_args()
		
		# Init logging
		
		logging.basicConfig(filename=os.path.dirname(os.path.realpath(__file__))+'/ac_to_mqtt.log',level=(logging.DEBUG if args.debug else logging.INFO),format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s')
		#logging.basicConfig(filename='ac_to_mqtt.log',level=(logging.DEBUG if args.debug else logging.INFO),format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s')
		
		logger.debug("%s v%s is starting up" % (__file__, softwareversion))
		logLevel = {0: 'NOTSET', 10: 'DEBUG', 20: 'INFO', 30: 'WARNING', 40: 'ERROR'}
		logger.debug('Loglevel set to ' + logLevel[logging.getLogger().getEffectiveLevel()])
				
	 
		##Apply the config, then if arguments, override the config values with args
		config = read_config();
		
		##Print verions
		if args.version:
			print ("Monitor Version: %s, Class version:%s" % (softwareversion,broadlink.version))
			sys.exit();
		
		##Mqtt Host
		if args.mqttserver:
			config["mqtt_host"] = args.mqttserver
			
		##Mqtt Port
		if args.mqttport:
			config["mqtt_port"] = args.mqttport
		##Mqtt User
		if args.mqttuser:
			config["mqtt_user"] = args.mqttuser
		
		##Mqtt Password
		if args.mqttpassword:
			config["mqtt_password"] = args.mqttpassword
			
		##Mqtt auto discovery topic
		if args.mqtt_auto_discovery_topic:
			config["mqtt_auto_discovery_topic"] = args.mqtt_auto_discovery_topic
		  
		
		##Self Discovery
		if args.discover:
			config["self_discovery"] = True			
	 
		if args.discoverdump:
			discover_and_dump_for_config(config)
			
		##Deamon Mode
		if args.background:
			config["daemon_mode"] = True
			 
		
		##Make sure not already running		
		stop_if_already_running()		
		
		logging.info("Starting Monitor...")
        # Start and run the mainloop
		logger.debug("Starting mainloop, responding on only events")
		
		try:
			##class
			actomqtt = AcToMqtt(config);
		
			##Connect to Mqtt
			actomqtt._connect_mqtt()	

			
			if config["self_discovery"]:	
				devices = actomqtt.discover()
			else:
				devices = actomqtt.make_device_objects(config['devices'])
			
			if args.dumphaconfig:
				actomqtt.dump_homeassistant_config_from_devices(devices)			
				sys.exit();
				
 			##Publish mqtt auto discovery if topic  set
			if config["mqtt_auto_discovery_topic"]:
				actomqtt.publish_mqtt_auto_discovery(devices)			
		
			
			##Run main loop
			actomqtt.do_loop(config,devices);
			
		except KeyboardInterrupt:
			logging.debug("User Keyboard interuped")
		finally:
			os.unlink(pidfile)
			logging.info("Stopping Monitor...")

				
if __name__ == "__main__":
	
	main()
