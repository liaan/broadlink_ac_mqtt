#!/usr/bin/python
import os

import time
import sys
import logging
import commands
import argparse
import binascii


logger = logging.getLogger(__name__)
softwareversion = 0.001

mqtt_host = "10.0.0.247"
mqtt_port = 1883
debug = False


ac_host = "10.0.0.204"
ac_port = 80
ac_mac = "b4430da741af"


sys.path.insert(1, os.path.join(os.path.dirname(__file__), './ext/paho-mqtt-client'))
import client as mqtt
sys.path.insert(1, os.path.join(os.path.dirname(__file__), './ext/broadlink'))
import ac_db as broadlink

class AcToMqtt:
	devices = {}
	def __init__(self):
		self._connect_mqtt()
		##disover the devices
		discover_devices = broadlink.discover(timeout=1)			
		
		if discover_devices == None:
			logger.debug("No Devices Found")
			#print "nothing found"
			sys.exit()
			
		for device in discover_devices:	
			#print device.host
			#print device.mac
			if device.devtype == 0x4E2a:
				self.devices[device.status['macaddress']] = device
		
		#device = self.devices["a"]
		
		
		#self.device = broadlink.ac_db(host=device.host, mac=device.mac,debug=False)		
		
		#logger.debug(self.device.host)
		#logger.debug( "Device type detected: " +self.device.type)
		#logger.debug( "Starting device test()")			
		
		
		#device.switch_on()
		while True:
			try:
		
				for device in discover_devices:	
					status = device.get_ac_states()
					#print status
					if status:
						self.publish_mqtt_info(status);
					else:
						logger.debug("No status")
						
				time.sleep(5)
				
			except ValueError:
				print e
				print "oops"
		
			
			
	def publish_mqtt_info(self,status):
	
			##Publish all values in status
			for value,key in enumerate(status):
				self._publish(status['macaddress']+'/'+key+ '/value',bytes(status[key]))			
			return 

			#self._publish(binascii.hexlify(status['macaddress'])+'/'+ 'temp/value',status['temp']);
				
				
	def _publish(self,topic,value):

			topic = '/aircon/' + topic
			payload = value
			logger.debug('publishing on topic "%s", data "%s"' % (topic, payload))
			self._mqtt.publish(topic, payload=payload, qos=0, retain=False)
			
	def _connect_mqtt(self):
			
			logger.debug("Coneccting to MQTT: " + mqtt_host)
			self._mqtt = mqtt.Client(client_id="MeMySelfAndI", clean_session=True, userdata=None)
			self._mqtt.loop_start()  # creates new thread and runs Mqtt.loop_forever() in it.

			self._mqtt.on_connect = self._on_mqtt_connect
			self._mqtt.on_message = self._on_mqtt_message

			logger.debug('Connecting to host')
			self._mqtt.connect_async(mqtt_host, port=mqtt_port, keepalive=60, bind_address="")
			logger.debug('our client id (and also topic) is %s' % "abc")

					
	def _on_mqtt_message(self, client, userdata, msg):
		
		try:
			
			logger.debug('message! userdata: %s, message %s' % (userdata, msg.topic+" "+str(msg.payload)))
			##Function is second last
			function = msg.topic.split('/')[-2]
			address = msg.topic.split('/')[-3]
			value = msg.payload
			logger.debug('Function: %s, Address %s , value %s' %(function,address,value))
			
		except:
			return


		##Process received		
		if function ==  "temp":		
			if self.devices.get(address):
				self.devices[address].set_temperature(float(value[0:3]))
			else:
				logger.debug("Device not on list of desocvered devices")
				return
			
		elif function == "power":
			if value.lower() == "on":
				self.devices[address].switch_on()
			elif value.lower() == "off":
				self.devices[address].switch_off()
			else:
				logger.debug("Switch on has invalid value, values is on/off received %s",value)
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

		logger.debug('connected! client=%s, userdata=%s, flags=%s, rc=%s' % (client, userdata, flags, rc))
		# Subscribing in on_connect() means that if we lose the connection and
		# reconnect then subscriptions will be renewed.
		client.subscribe("/aircon/+/+/set")
				
				
def stop_if_already_running():
			script_name = os.path.basename(__file__)
			l = commands.getstatusoutput("ps aux | grep -e '%s' | grep -v grep | awk '{print $2}'| awk '{print $2}'" % script_name)
			if l[1]:
				sys.exit(0);
				
def main():
		global ac_host
		global mqtt_port
		global mqtt_host
		global ac_mac
		global ac_port
		
		
		##Make sure not already running
		stop_if_already_running()
		
        # Argument parsing
		parser = argparse.ArgumentParser(		
			description='Duhnham Bush v%s: Mqtt publisher of Duhnham Bush on the Pi.' % softwareversion			
		)

		parser.add_argument("-d", "--debug", help="set logging level to debug",action="store_true")
		
		#parser.add_argument("-dh", "--devicehost", help='Aircon Host IP, Default: %s ' % ac_host)
		#parser.add_argument("-dm", "--devicemac", help="Ac Mac Address, Default:  %s" % ac_mac)
		
		parser.add_argument("-ms", "--mqttserver", help='Mqtt Server, Default: %s ' % mqtt_host)
		parser.add_argument("-mp", "--mqttport", help="Mqtt Port, Default:  %s" % mqtt_port)
		
		args = parser.parse_args()
		
		# Init logging
		logging.basicConfig(level=(logging.DEBUG if args.debug else logging.INFO))
		
		#if args.devicehost: 
		#		ac_host = args.devicehost
		#		logger.debug("Host: %s"%ac_host)
				
		#if args.devicemac:
		#		ac_mac = args.devicemac				
         #       logger.debug("Mac: %s"%ac_mac)
				
				
		if args.mqttserver:
			mqtt_host = args.mqttserver
			logger.debug("Host: %s"%mqtt_host)

		if args.mqttport:
			mqtt_port = args.port
			logger.debug("Port: %s"%mqttport)
				
				
		logger.debug("%s v%s is starting up" % (__file__, softwareversion))
		logLevel = {0: 'NOTSET', 10: 'DEBUG', 20: 'INFO', 30: 'WARNING', 40: 'ERROR'}
		logger.debug('Loglevel set to ' + logLevel[logging.getLogger().getEffectiveLevel()])
		
        # Start and run the mainloop
		logger.debug("Starting mainloop, responding on only events")
		q = AcToMqtt()		
			

		
	
if __name__ == "__main__":
	
	main()