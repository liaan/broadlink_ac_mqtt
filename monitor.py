#!/usr/bin/python
import os
import time
import sys
import logging
import commands
import argparse
import binascii
import yaml
import paho.mqtt.client as mqtt
sys.path.insert(1, os.path.join(os.path.dirname(__file__), './ext/broadlink'))
import ac_db as broadlink
import tempfile

pid = str(os.getpid())
pidfile = tempfile.gettempdir() +"/ac_to_mqtt.pid"
pid_stale_time = 60
pid_last_update = 0



logger = logging.getLogger(__name__)
softwareversion = 1.0

mqtt_host = "mqtt"
mqtt_port = 1883
mqtt_client_id = "AcToMqtt"

debug = False
daemon_mode = False;
update_interval = 30
devices = {}

#*****************************************  Main Class ************************************************
class AcToMqtt:
	
	devices	= {}
	global daemon_mode
	discover_devices = {}
	last_update = 0
	
	def __init__(self):
		##dunno
		""	 
	
		 
	def discover(self):
		self.discover_devices = broadlink.discover(timeout=5)			
		
		if self.discover_devices == None:
			error_msg = "No Devices Found, make sure you on the same network segment"
			if daemon_mode:
				logger.debug(error_msg)
			else:
				print error_msg			
			#print "nothing found"
			sys.exit()
			
		for device in self.discover_devices:	
			#print device.host
			#print device.mac
			if device.devtype == 0x4E2a:
				self.devices[device.status['macaddress']] = device
				
			
				
		#device = self.devices["a"]
		#self.device = broadlink.ac_db(host=device.host, mac=device.mac,debug=False)				
		#logger.debug(self.device.host)
		#logger.debug( "Device type detected: " +self.device.type)
		#logger.debug( "Starting device test()")			
		
	
	def print_yaml_discovered_devices(self):	
		print yaml.dump(self.discover_devices);
		
	def main (self):
		global update_interval
		 
		
		self._connect_mqtt()
		last_update = 0;
		if self.discover_devices == {}: 
			self.discover()
		
		while daemon_mode:
			
			touch_pid_file()
				
		
			##Just check status on every update interval
			if (last_update + update_interval) > time.time():
				#logger.debug("Timeout not done, so lets wait a abit : %s : %s" %(last_update + update_interval,time.time()))				
				time.sleep(0.5)
				continue
			
			
			try:
				last_update = time.time();
				##Update PID file
				
				
				for device in self.discover_devices:
					##Get the status, the global update interval is used as well to reduce requests to aircons as they slow
					status = device.get_ac_status()								
					#print status
					if status:
						self.publish_mqtt_info(status);
					else:
						logger.debug("No status")
				
				
			except Exception as e:					
				logger.critical(e)	
				##Something went wrong, so just exit and let system restart	
				continue;
			
			##Set last update 
			
				
				
	def publish_mqtt_info(self,status):
	
			##Publish all values in status
			for value,key in enumerate(status):
				pubResult = self._publish(status['macaddress']+'/'+key+ '/value',bytes(status[key]))			
				if pubResult != None:
					
					logger.warning('Publishing Result: "%s"' % mqtt.error_string(pubResult))
					if pubResult == mqtt.MQTT_ERR_NO_CONN:
						self._connect_mqtt();
						
					break
			return 

			#self._publish(binascii.hexlify(status['macaddress'])+'/'+ 'temp/value',status['temp']);
				
				
	def _publish(self,topic,value):

			topic = '/aircon/' + topic
			payload = value
			logger.debug('publishing on topic "%s", data "%s"' % (topic, payload))			
			pubResult = self._mqtt.publish(topic, payload=payload, qos=0, retain=False)
			
			##If there error, then debug log and return not None
			if pubResult[0] != 0:				
				logger.debug('Publishing Result: "%s"' % mqtt.error_string(pubResult[0]))
				return pubResult[0]
				
			
				
			
			
	def _connect_mqtt(self):
	
		 
			self._mqtt = mqtt.Client(client_id=mqtt_client_id, clean_session=True, userdata=None)
			##Set last will and testament
			self._mqtt.will_set("/aircon/LWT","offline",True)
			
			

			self._mqtt.on_connect = self._on_mqtt_connect
			self._mqtt.on_message = self._on_mqtt_message
			self._mqtt.on_log = self._on_mqtt_log
			self._mqtt.on_subscribed = self._mqtt_on_subscribe

			logger.debug("Coneccting to MQTT: %s with client ID = %s" % (mqtt_host,mqtt_client_id))
			self._mqtt.connect_async(mqtt_host, port=mqtt_port, keepalive=60, bind_address="")
			##Start
			self._mqtt.loop_start()  # creates new thread and runs Mqtt.loop_forever() in it.
			
	 

	def _on_mqtt_log(self,client, userdata, level, buf):
		if level == mqtt.MQTT_LOG_ERR:
			logger.debug("Mqtt log" + buf)
		
	def _mqtt_on_subscribe(self,client, userdata, mid, granted_qos):
		logger.debug("Mqtt Subscribed")
		
	def _on_mqtt_message(self, client, userdata, msg):
		
	
		try:
			logger.debug('message! userdata: %s, message %s' % (userdata, msg.topic+" "+str(msg.payload)))
			##Function is second last
			function = msg.topic.split('/')[-2]
			address = msg.topic.split('/')[-3]
			value = msg.payload
			logger.debug('Function: %s, Address %s , value %s' %(function,address,value))			
	
		except Exception as e:	
			logger.critical(e)			
			return
			
		
		##Process received		##Probably need to exit here as well if command not send, but should exit on status update above .. grr, hate stupid python
		if function ==  "temp":	
			try:
				if self.devices.get(address):
					status = self.devices[address].set_temperature(float(value))
					
					if status :
						self.publish_mqtt_info(status)
				else:
					logger.debug("Device not on list of desocvered devices")
					return
			except Exception as e:	
				logger.critical(e)
				return
			
		elif function == "power":
			if value.lower() == "on":
				status = self.devices[address].switch_on()
				if status :
					self.publish_mqtt_info(status)
			elif value.lower() == "off":
				status = self.devices[address].switch_off()
				if status :
					self.publish_mqtt_info(status)
			else:
				logger.debug("Switch on has invalid value, values is on/off received %s",value)
				return
				
		elif function == "mode":
			
			status = self.devices[address].set_mode(value)
			if status :
				self.publish_mqtt_info(status)
				
			else:
				logger.debug("Mode on has invalid value %s",value)
				return
		elif function == "fanspeed":
			
			status = self.devices[address].set_fanspeed(value)
			if status :
				self.publish_mqtt_info(status)
				
			else:
				logger.debug("Fanspeed on has invalid value %s",value)
				return
		elif function == "homekit":
			
			status = self.devices[address].set_homekit_status(value)
			if status :
				self.publish_mqtt_info(status)
				
			else:
				logger.debug("Fanspeed on has invalid value %s",value)
				return
		elif function == "homeassist":
			
			status = self.devices[address].set_homeassist_status(value)
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
		sub_topic = "/aircon/+/+/set"
		client.subscribe(sub_topic)
		logger.debug('Listing on %s for messages' % (sub_topic))
		##LWT
		self._publish('LWT','online')
#*****************************************************************************************************
#*****************************************  Get going methods ************************************************

	
def apply_config(PrintConfig = False):
	global daemon_mode
	global mqtt_host
	global mqtt_port
	global mqtt_client
	global update_interval
	
	##Load config
	
	with open(os.path.dirname(os.path.realpath(__file__))+'/config.yml', "r") as ymlfile:
		config = yaml.load(ymlfile,Loader=yaml.SafeLoader)

	daemon_mode = config["service"]["daemon_mode"]
	update_interval = config["service"]["update_interval"]
	mqtt_host = config["mqtt"]["host"]
	mqtt_port = config["mqtt"]["port"]
	
	if(PrintConfig):
		print(config["mqtt"])
		print(config["service"])
		print(config["devices"])
	
	return
				
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
		global ac_host
		global mqtt_port
		global mqtt_host
		global ac_mac
		global ac_port
		global discover_devices
		
		 
		
		##class
		actomqtt = AcToMqtt();
				
        # Argument parsing
		parser = argparse.ArgumentParser(		
			description='Duhnham Bush v%s: Mqtt publisher of Duhnham Bush on the Pi.' % softwareversion			
		)

		parser.add_argument("-d", "--debug", help="set logging level to debug",action="store_true",default=False)
		parser.add_argument("-f", "--discover", help="Discover devices only",action="store_true",default=False)
		parser.add_argument("-b", "--background", help="Run in background",action="store_true",default=False)
		
		#parser.add_argument("-dh", "--devicehost", help='Aircon Host IP, Default: %s ' % ac_host)
		#parser.add_argument("-dm", "--devicemac", help="Ac Mac Address, Default:  %s" % ac_mac)
		
		parser.add_argument("-ms", "--mqttserver", help='Mqtt Server, Default: %s ' % mqtt_host)
		parser.add_argument("-mp", "--mqttport", help="Mqtt Port, Default:  %s" % mqtt_port)
		parser.add_argument("-P", "--printconfig", help="Print config ",action="store_true")		
		parser.add_argument("-w", "--writeconfig", help="Write to config",action="store_true")
		
		
		args = parser.parse_args()
		
		# Init logging
		
		logging.basicConfig(filename=os.path.dirname(os.path.realpath(__file__))+'/acdb_mqtt.log',level=(logging.DEBUG if args.debug else logging.INFO),format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s')
		#logging.basicConfig(filename='ac_to_mqtt.log',level=(logging.DEBUG if args.debug else logging.INFO),format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s')
		
		
		
		#if args.devicehost: 
		#		ac_host = args.devicehost
		#		logger.debug("Host: %s"%ac_host)
				
		#if args.devicemac:
		#		ac_mac = args.devicemac				
         #       logger.debug("Mac: %s"%ac_mac)
				
	 
		##Apply the config, then if arguments, override the config values with args
		apply_config();
		
		if args.mqttserver:
			mqtt_host = args.mqttserver
			logger.debug("Host: %s"%mqtt_host)

		if args.mqttport:
			mqtt_port = args.port
			logger.debug("Port: %s"%mqttport)
	
		
		
		##prtint config
		if args.printconfig:	
			apply_config(True)
			sys.exit() 
		
		if args.writeconfig:
			actomqtt.write_discovered()
			sys.exit()
			
		 	
		if devices == None:
			print "No devices defined, please run discovery or configure it in config.yml"
			sys.exit()
			
		if args.background:
			daemon_mode = True
		
		
		if args.discover: 
			actomqtt.discover()
			sys.exit(); 
				
		logger.debug("%s v%s is starting up" % (__file__, softwareversion))
		logLevel = {0: 'NOTSET', 10: 'DEBUG', 20: 'INFO', 30: 'WARNING', 40: 'ERROR'}
		logger.debug('Loglevel set to ' + logLevel[logging.getLogger().getEffectiveLevel()])
	 	
		
		##Make sure not already running		
		stop_if_already_running()		
		
		logging.info("Starting Monitor...")
        # Start and run the mainloop
		logger.debug("Starting mainloop, responding on only events")
		
	 
		try:
			actomqtt.main();
		except KeyboardInterrupt:
			logging.debug("User Keyboard interuped")
		finally:
			os.unlink(pidfile)
			logging.info("Stopping Monitor...")

			

		
	
if __name__ == "__main__":
	
	main()
