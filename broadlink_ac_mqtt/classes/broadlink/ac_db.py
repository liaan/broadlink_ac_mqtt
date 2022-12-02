#!/usr/bin/python
# -*- coding: utf8 -*-

from datetime import datetime

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

import time
import random
import socket
import threading

import struct

version = "1.1.3"

def gendevice(devtype , host, mac,name=None, cloud=None,update_interval = 0):
	#print format(devtype,'02x')
	##We only care about 1 device type...  
	if devtype == 0x4E2a: # Danham Bush
		return ac_db(host=host, mac=mac,name=name, cloud=cloud,devtype= devtype,update_interval = 0)
	if devtype == 0xFFFFFFF: # test
		return ac_db_debug(host=host, mac=mac,name=name, cloud=cloud,devtype= devtype,update_interval = 0)
	else:
		return device(host=host, mac=mac,devtype =devtype,update_interval = update_interval)


def discover(timeout=None, bind_to_ip=None):
	if bind_to_ip is None:
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		s.connect(('8.8.8.8', 53))  # connecting to a UDP address doesn't send packets
		bind_to_ip = s.getsockname()[0]

		
	address = bind_to_ip.split('.')
	cs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	cs.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	cs.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
	
	cs.bind((bind_to_ip,0))

	port = cs.getsockname()[1]
	starttime = time.time()

	devices = []

	timezone = int(time.timezone/-3600)
	packet = bytearray(0x30)

	year = datetime.now().year

	if timezone < 0:
		packet[0x08] = 0xff + timezone - 1
		packet[0x09] = 0xff
		packet[0x0a] = 0xff
		packet[0x0b] = 0xff
	else:
		packet[0x08] = timezone
		packet[0x09] = 0
		packet[0x0a] = 0
		packet[0x0b] = 0
	packet[0x0c] = year & 0xff
	packet[0x0d] = year >> 8
	packet[0x0e] = datetime.now().minute
	packet[0x0f] = datetime.now().hour
	subyear = str(year)[2:]
	packet[0x10] = int(subyear)
	packet[0x11] = datetime.now().isoweekday()
	packet[0x12] = datetime.now().day
	packet[0x13] = datetime.now().month
	packet[0x18] = int(address[0])
	packet[0x19] = int(address[1])
	packet[0x1a] = int(address[2])
	packet[0x1b] = int(address[3])
	packet[0x1c] = port & 0xff
	packet[0x1d] = port >> 8
	packet[0x26] = 6
	checksum = 0xbeaf

	for i in range(len(packet)):
		checksum += packet[i]
	checksum = checksum & 0xffff
	packet[0x20] = checksum & 0xff
	packet[0x21] = checksum >> 8

	cs.sendto(packet, ('255.255.255.255', 80))
	if timeout is None:
		response = cs.recvfrom(1024)
		responsepacket = bytearray(response[0])
		host = response[1]	
		mac = responsepacket[0x3a:0x40]	
		mac = mac[::-1]  ##Flip correct
		devtype = responsepacket[0x34] | responsepacket[0x35] << 8
		name = responsepacket[0x40:].split(b'\x00')[0].decode('utf-8')
		if not name:
			name = mac
		cloud = bool(responsepacket[-1])
		cs.close()
		return gendevice(devtype, host, mac,name=name,cloud=cloud)
	else:
		while (time.time() - starttime) < timeout:
			cs.settimeout(timeout - (time.time() - starttime))
			try:
				response = cs.recvfrom(1024)
			except socket.timeout:
				return devices
			responsepacket = bytearray(response[0])

			#print ":".join("{:02x}".format(c) for c in responsepacket)
			#print ":".join("{:c}".format(c) for c in responsepacket)

			host = response[1]
			devtype = responsepacket[0x34] | responsepacket[0x35] << 8
			mac = responsepacket[0x3a:0x40]
			mac = mac[::-1] ##flip Correct
			name = responsepacket[0x40:].split(b'\x00')[0].decode('utf-8')
			##Make sure there is some name
			if not name:
				name = mac		
				
			cloud = bool(responsepacket[-1])
			dev = gendevice(devtype, host, mac,name=name,cloud=cloud)
			devices.append(dev)

	cs.close()
	return devices


class device:
	__INIT_KEY = "097628343fe99e23765c1513accf8b02"
	__INIT_VECT = "562e17996d093d28ddb3ba695a2e6f58"
		
	def __init__(self, host, mac, timeout=10,name=None,cloud=None,devtype=None,update_interval=0,bind_to_ip=None):

		
		self.host = host
		self.mac = mac
		self.name = name    
		self.cloud = cloud
		self.timeout = timeout
		self.devtype = devtype
		self.count = random.randrange(0xffff)
		##AES
		self.key = bytearray([0x09, 0x76, 0x28, 0x34, 0x3f, 0xe9, 0x9e, 0x23, 0x76, 0x5c, 0x15, 0x13, 0xac, 0xcf, 0x8b, 0x02])
		self.iv = bytearray([0x56, 0x2e, 0x17, 0x99, 0x6d, 0x09, 0x3d, 0x28, 0xdd, 0xb3, 0xba, 0x69, 0x5a, 0x2e, 0x6f, 0x58])		
		

		self.id = bytearray([0, 0, 0, 0])
		self.cs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.cs.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.cs.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		#self.cs.bind(('',0))
		self.type = "Unknown"
		self.lock = threading.Lock()
		self.update_interval = update_interval
		self.bind_to_ip = bind_to_ip
		self.aes = None
		self.update_aes(bytes.fromhex(self.__INIT_KEY))

		

	def update_aes(self, key: bytes) -> None:
		"""Update AES."""
		self.aes = Cipher(
			algorithms.AES(bytes(key)), modes.CBC(self.iv), backend=default_backend()
		)

	def encrypt(self, payload: bytes) -> bytes:
		"""Encrypt the payload."""
		encryptor = self.aes.encryptor()
		return encryptor.update(bytes(payload)) + encryptor.finalize()

	def decrypt(self, payload: bytes) -> bytes:
		"""Decrypt the payload."""
		decryptor = self.aes.decryptor()
		return decryptor.update(bytes(payload)) + decryptor.finalize()


	def auth(self):
		payload = bytearray(0x50)
		payload[0x04] = 0x31
		payload[0x05] = 0x31
		payload[0x06] = 0x31
		payload[0x07] = 0x31
		payload[0x08] = 0x31
		payload[0x09] = 0x31
		payload[0x0a] = 0x31
		payload[0x0b] = 0x31
		payload[0x0c] = 0x31
		payload[0x0d] = 0x31
		payload[0x0e] = 0x31
		payload[0x0f] = 0x31
		payload[0x10] = 0x31
		payload[0x11] = 0x31
		payload[0x12] = 0x31
		payload[0x1e] = 0x01
		payload[0x2d] = 0x01
		payload[0x30] = ord('T')
		payload[0x31] = ord('e')
		payload[0x32] = ord('s')
		payload[0x33] = ord('t')
		payload[0x34] = ord(' ')
		payload[0x35] = ord(' ')
		payload[0x36] = ord('1')

	
		response = self.send_packet(0x65, payload)    

		enc_payload = response[0x38:]

		
		payload = self.decrypt(bytes(enc_payload))
		
		if not payload:
			return False

		key = payload[0x04:0x14]
		if len(key) % 16 != 0:
			return False

		self.id = payload[0x00:0x04]
		self.key = key

		self.update_aes(payload[0x04:0x14])

		return True

	def get_type(self):
		return self.type

	def	 send_packet(self, command, payload):
		self.count = (self.count + 1) & 0xffff
		packet = bytearray(0x38)
		packet[0x00] = 0x5a
		packet[0x01] = 0xa5
		packet[0x02] = 0xaa
		packet[0x03] = 0x55
		packet[0x04] = 0x5a
		packet[0x05] = 0xa5
		packet[0x06] = 0xaa
		packet[0x07] = 0x55
		packet[0x24] = 0x2a #==> Type
		packet[0x25] = 0x4e #==> Type
		packet[0x26] = command
		packet[0x28] = self.count & 0xff
		packet[0x29] = self.count >> 8
		packet[0x2a] = self.mac[0]
		packet[0x2b] = self.mac[1]
		packet[0x2c] = self.mac[2]
		packet[0x2d] = self.mac[3]
		packet[0x2e] = self.mac[4]
		packet[0x2f] = self.mac[5]
		packet[0x30] = self.id[0]
		packet[0x31] = self.id[1]
		packet[0x32] = self.id[2]
		packet[0x33] = self.id[3]

		checksum = 0xbeaf
		for i in range(len(payload)):
			checksum += payload[i]
			checksum = checksum & 0xffff

		 
		
		payload = self.encrypt(bytes(payload))

		packet[0x34] = checksum & 0xff
		packet[0x35] = checksum >> 8

		for i in range(len(payload)):
		 	packet.append(payload[i])

		checksum = 0xbeaf
		for i in range(len(packet)):
			checksum += packet[i]
			checksum = checksum & 0xffff
		packet[0x20] = checksum & 0xff
		packet[0x21] = checksum >> 8

		#print 'Sending Packet:\n'+''.join(format(x, '02x') for x in packet)+"\n"
		starttime = time.time()
		with self.lock:
			while True:
				try:
					self.cs.sendto(packet, self.host)
					self.cs.settimeout(1)
					response = self.cs.recvfrom(1024)

					break
				except socket.timeout:
					if (time.time() - starttime) < self.timeout:
						pass
					raise ConnectTimeout(200,self.host)
		return bytearray(response[0])



#******************************************************** ac db debug class *****************************************
class ac_db(device):
	
	import logging
	
	type = "ac_db"
	
	class STATIC:
		##Static stuff
		class FIXATION:
			class VERTICAL:
				#STOP= 0b00000000
				TOP= 0b00000001
				MIDDLE1= 0b00000010
				MIDDLE2 = 0b00000011
				MIDDLE3 = 0b00000100
				BOTTOM= 0b00000101
				SWING= 0b00000110
				AUTO = 0b00000111
				
			class HORIZONTAL:		##Don't think this really works for all devices.
				LEFT_FIX = 2
				LEFT_FLAP = 1
				LEFT_RIGHT_FIX = 7
				LEFT_RIGHT_FLAP = 0
				RIGHT_FIX = 6
				RIGHT_FLAP = 5
				ON = 0
				OFF = 1
			
		class FAN:
			LOW 	= 	0b00000011
			MEDIUM 	= 	0b00000010
			HIGH 	=	0b00000001
			AUTO 	= 	0b00000101  
			NONE 	=	0b00000000
		
				 
		class MODE:
			COOLING	=	0b00000001
			DRY		=	0b00000010
			HEATING	=	0b00000100
			AUTO	=	0b00000000
			FAN 	=	0b00000110   
			
		class ONOFF:
			OFF = 0
			ON = 1
	def get_ac_status(self,force_update = False):
		
		
	 
		##Get AC info(also populates the current temp)
		self.logger.debug("Getting AC Info")
		status = self.get_ac_info()
		self.logger.debug("AC Info Retrieved")
	 
		return status
	
 
	def __init__ (self, host, mac,name=None,cloud=None,debug = False,update_interval = 0,devtype=None,bind_to_ip=None):			
		
		device.__init__(self, host, mac,name=name,cloud=cloud,devtype=devtype,update_interval=update_interval)	
		
		devtype = devtype
		self.status = {}		
		self.logger = self.logging.getLogger(__name__)	
		 
		self.update_interval = update_interval
		
		##Set default values
		#mac = mac[::-1]
		
		self.set_default_values()		
		self.status['macaddress'] = ''.join(format(x, '02x') for x in mac) 
		self.status['hostip'] = host
		self.status['name'] = name
		self.status['lastupdate'] = 0
		
		
		self.logging.basicConfig(level=(self.logging.DEBUG if debug else self.logging.INFO))
		self.logger.debug("Debugging Enabled")	
		
		
		##Populate array with latest data
		self.logger.debug("Authenticating")
		if self.auth() == False:
			self.logger.critical("Authentication Failed to AC")					
			return False
		
		self.logger.debug("Getting current details in init")		
		
		##Get the current details
		self.get_ac_status(force_update = True)

	def get_ac_status(self,force_update = False):
		
		
		##Check if the status is up to date to reduce timeout issues. Can be overwritten by force_update
		self.logger.debug("Last update was: %s"%self.status['lastupdate'] )

		if (force_update == False and (self.status['lastupdate'] + self.update_interval) > time.time()) :
			return self.make_nice_status(self.status)
			
		##Get AC info(also populates the current temp)
		self.logger.debug("Getting AC Info")
		self.get_ac_info()
		self.logger.debug("AC Info Retrieved")
		##Get the current status ... get_ac_states does make_nice_status in return.
		self.logger.debug("Getting AC States")
		status = self.get_ac_states(True)
		self.logger.debug("AC States retrieved")
		return status
		
		
	def set_default_values(self):
				
		self.status['temp'] = float(19)
		self.status['fixation_v'] = self.STATIC.FIXATION.VERTICAL.AUTO
		self.status['power'] = self.STATIC.ONOFF.ON
		self.status['mode'] = self.STATIC.MODE.AUTO
		self.status['sleep'] = self.STATIC.ONOFF.OFF
		self.status['display'] = self.STATIC.ONOFF.ON
		self.status['health'] = self.STATIC.ONOFF.OFF  
		self.status['ifeel'] = self.STATIC.ONOFF.OFF
		self.status['fixation_h'] = self.STATIC.FIXATION.HORIZONTAL.LEFT_RIGHT_FIX
		self.status['fanspeed']  = self.STATIC.FAN.AUTO
		self.status['turbo'] = self.STATIC.ONOFF.OFF
		self.status['mute'] = self.STATIC.ONOFF.OFF
		self.status['clean'] = self.STATIC.ONOFF.OFF
		self.status['mildew'] = self.STATIC.ONOFF.OFF
		self.status['macaddress'] = None
		self.status['hostip'] = None
		self.status['lastupdate'] = None
		self.status['ambient_temp'] = None
		self.status['devicename'] = None
		
		
		
	def set_temperature(self,temperature):
		self.logger.debug("Setting temprature to %s",temperature)
		self.get_ac_states()		
		self.status['temp'] = float(temperature)
		
		self.set_ac_status()
		return self.make_nice_status(self.status)
		
	def switch_off(self):
		##Make sure latest info as cannot just update one things, have set all
		self.get_ac_states()
		self.status['power'] =  self.STATIC.ONOFF.OFF
		self.set_ac_status()
		return self.make_nice_status(self.status)
		
	def switch_on(self):
		##Make sure latest info as cannot just update one things, have set all
		self.get_ac_states()
		self.status['power'] =  self.STATIC.ONOFF.ON
		self.set_ac_status()
		
		return self.make_nice_status(self.status)
		
	def set_mode(self,mode_text):
		##Make sure latest info as cannot just update one things, have set all
		self.get_ac_states()
		
		mode = self.STATIC.MODE.__dict__.get(mode_text.upper())
		if mode != None:
			self.status['mode'] = mode
			self.set_ac_status()
			return self.make_nice_status(self.status)
		else:
			self.logger.debug("Not found mode value %s" , str(mode_text))
			return False
			
	def set_fanspeed(self,mode_text):
		##Make sure latest info as cannot just update one things, have set all
		self.get_ac_states()
		
		mode = self.STATIC.FAN.__dict__.get(mode_text.upper())
		if mode != None:
			self.status['fanspeed'] = mode
			self.status['turbo']  = self.STATIC.ONOFF.OFF
			self.status['mute']  = self.STATIC.ONOFF.OFF
			self.set_ac_status()
			return self.make_nice_status(self.status)
		else:
			self.logger.debug("Not found mode value %s" , str(mode_text))
			return False
	def set_mute(self,value):
		##Make sure latest info as cannot just update one things, have set all
		self.get_ac_states()
		
		mode = self.STATIC.ONOFF.__dict__.get(value)
		if mode != None:
			self.status['mute'] = mode
			self.status['turbo']  = self.STATIC.ONOFF.OFF			
			self.status['fanspeed'] = self.STATIC.FAN.NONE
			self.set_ac_status()
			return self.make_nice_status(self.status)
		else:
			self.logger.debug("Not found mute value %s" , str(value))
			return False
	def set_turbo(self,value):
		##Make sure latest info as cannot just update one things, have set all
		self.get_ac_states()
		
		mode = self.STATIC.ONOFF.__dict__.get(value)
		if mode != None:
			self.status['turbo'] = mode
			self.status['mute']  = self.STATIC.ONOFF.OFF
			self.status['fanspeed'] = self.STATIC.FAN.NONE
			self.set_ac_status()
			return self.make_nice_status(self.status)
		else:
			self.logger.debug("Not found Turbo value %s" , str(value))
			return False
	def set_fixation_v(self,fixation_text):
		##Make sure latest info as cannot just update one things, have set all
		self.get_ac_states()
		
		fixation = self.STATIC.FIXATION.VERTICAL.__dict__.get(fixation_text.upper())
		if fixation != None:
			self.status['fixation_v'] = fixation
			self.set_ac_status()
			return self.make_nice_status(self.status)
		else:
			self.logger.debug("Not found mode value %s" , str(fixation_text))
			return False

	def set_fixation_h(self,fixation_text):
		##Make sure latest info as cannot just update one things, have set all
		self.get_ac_states()
		
		fixation = self.STATIC.FIXATION.HORIZONTAL.__dict__.get(fixation_text.upper())
		if fixation != None:
			self.status['fixation_h'] = fixation
			self.set_ac_status()
			return self.make_nice_status(self.status)
		else:
			self.logger.debug("Not found mode value %s" , str(fixation_text))
			return False
			
	def set_display(self,value):
		##Make sure latest info as cannot just update one things, have set all
		self.get_ac_states()

		mode = self.STATIC.ONOFF.__dict__.get(value)
		if mode != None:
			self.status['display'] = mode
			self.set_ac_status()
			return self.make_nice_status(self.status)
		else:
			self.logger.debug("Not found display value %s" , str(value))
			return False

	def set_mildew(self,value):
		##Make sure latest info as cannot just update one things, have set all
		self.get_ac_states()
		
		mode = self.STATIC.ONOFF.__dict__.get(value)
		if mode != None:
			self.status['mildew'] = mode
			self.set_ac_status()
			return self.make_nice_status(self.status)
		else:
			self.logger.debug("Not found display value %s" , str(value))
			return False

	def set_clean(self,value):
		##Make sure latest info as cannot just update one things, have set all
		self.get_ac_states()
		
		mode = self.STATIC.ONOFF.__dict__.get(value)
		if mode != None:
			self.status['clean'] = mode
			self.set_ac_status()
			return self.make_nice_status(self.status)
		else:
			self.logger.debug("Not found display value %s" , str(value))
			return False

	def set_health(self,value):
		##Make sure latest info as cannot just update one things, have set all
		self.get_ac_states()
		
		mode = self.STATIC.ONOFF.__dict__.get(value)
		if mode != None:
			self.status['health'] = mode
			self.set_ac_status()
			return self.make_nice_status(self.status)
		else:
			self.logger.debug("Not found display value %s" , str(value))
			return False

	def set_sleep(self,value):
		##Make sure latest info as cannot just update one things, have set all
		self.get_ac_states()
		
		mode = self.STATIC.ONOFF.__dict__.get(value)
		if mode != None:
			self.status['sleep'] = mode
			self.set_ac_status()
			return self.make_nice_status(self.status)
		else:
			self.logger.debug("Not found display value %s" , str(value))
			return False
		
	def set_homekit_mode(self,status):
		if type(status) is not str:
			self.logger.debug('Status variable is not string %s',type(status))
			return False
		
		if status.lower() == 'coolon':
			self.status['mode'] = self.STATIC.MODE.COOLING
			self.status['power'] =  self.STATIC.ONOFF.ON
			self.set_ac_status()
			return self.make_nice_status(self.status)
		elif status.lower() == 'heaton':
			self.status['mode'] = self.STATIC.MODE.HEATING
			self.status['power'] =  self.STATIC.ONOFF.ON
			self.set_ac_status()
			return self.make_nice_status(self.status)
	  
		elif status.lower() == 'auto':
			self.status['mode'] = self.STATIC.MODE.AUTO
			self.status['power'] =  self.STATIC.ONOFF.ON
			self.set_ac_status()
			return self.make_nice_status(self.status)
			
		if status.lower() == 'dry':
			self.status['mode'] = self.STATIC.MODE.DRY
			self.status['power'] =  self.STATIC.ONOFF.ON
			self.set_ac_status()
			return self.make_nice_status(self.status)
		if status.lower() == 'fan_only':
			self.status['mode'] = self.STATIC.MODE.FAN
			self.status['power'] =  self.STATIC.ONOFF.ON
			self.set_ac_status()
			return self.make_nice_status(self.status)
		elif status.lower() == "off":
			self.status['power'] =  self.STATIC.ONOFF.OFF
			self.set_ac_status()
			return self.make_nice_status(self.status)
		else:
			self.logger.debug('Invalid status for homekit %s',status)
			return False
			
	def set_homeassistant_mode(self,status):
		if type(status) is not str:
			self.logger.debug('Status variable is not string %s',type(status))
			return False
		
		if status.lower() == 'cool':
			self.status['mode'] = self.STATIC.MODE.COOLING
			self.status['power'] =  self.STATIC.ONOFF.ON
			self.set_ac_status()
			return self.make_nice_status(self.status)
		elif status.lower() == 'heat':
			self.status['mode'] = self.STATIC.MODE.HEATING
			self.status['power'] =  self.STATIC.ONOFF.ON
			self.set_ac_status()
			return self.make_nice_status(self.status)
	  
		elif status.lower() == 'auto':
			self.status['mode'] = self.STATIC.MODE.AUTO
			self.status['power'] =  self.STATIC.ONOFF.ON
			self.set_ac_status()
			return self.make_nice_status(self.status)
		
		if status.lower() == 'dry':
			self.status['mode'] = self.STATIC.MODE.DRY
			self.status['power'] =  self.STATIC.ONOFF.ON
			self.set_ac_status()
			return self.make_nice_status(self.status)
		if status.lower() == 'fan_only':
			self.status['mode'] = self.STATIC.MODE.FAN
			self.status['power'] =  self.STATIC.ONOFF.ON
			self.set_ac_status()
			return self.make_nice_status(self.status)
		elif status.lower() == "off":
			self.status['power'] =  self.STATIC.ONOFF.OFF
			self.set_ac_status()
			return self.make_nice_status(self.status)
		else:
			self.logger.debug('Invalid status for homekit %s',status)
			return False

			
	def get_ac_info(self):
		GET_AC_INFO = bytearray.fromhex("0C00BB0006800000020021011B7E0000")
		response = self.send_packet(0x6a, GET_AC_INFO)
		#print "Resposnse:" + ''.join(format(x, '02x') for x in response)
		#print "Response:" + ' '.join(format(x, '08b') for x in response[9:])		
		
		err = response[0x22] | (response[0x23] << 8)
		if err == 0:
			

			# response = bytearray.fromhex("5aa5aa555aa5aa55000000000000000000000000000000000000000000000000c6d000002a4e6a0055b9af41a70d43b401000000b9c00000aeaac104468cf91b485f38c67f7bf57f");
			#response = bytearray.fromhex("5aa5aa555aa5aa5547006f008d9904312c003e00000000003133a84d00400000d8d500002a4e6a0070a1b88c08b043a001000000b9c0000038821c66e3b38a5afe79dcb145e215d7")
		
			response_payload = self.decrypt(bytes(response[0x38:]))
			response_payload = bytearray(response_payload)
		  
		   
		  
			self.logger.debug ("Acinfo Raw Response: " + ' '.join(format(x, '08b') for x in response_payload )  )	
			self.logger.debug ("Acinfo Raw Hex: " + ' '.join(format(x, '02x') for x in response_payload )  )	
		
			
		  
			response_payload  = response_payload[2:]  ##Drop leading stuff as dont need
			self.logger.debug ("AcInfo: " + ' '.join(format(x, '08b') for x in response_payload[9:] )  )	
			
		  
			if len(response_payload) < 40: ##Hack for some invalid packets. should get proper length at some point.  #54
				self.logger.debug ("AcInfo: Invalid, seems to short?")	
				return 0

			##Its only the last 5 bits?		  
			ambient_temp = response_payload[15] & 0b00011111
			
			self.logger.debug("Ambient Temp Decimal: %s" % float(response_payload[31] & 0b00011111) ) ## @Anonym-tsk

			if ambient_temp:
				self.status['ambient_temp'] = ambient_temp
		
		  
			return self.make_nice_status(self.status)
		else:			
			self.logger.debug("Invalid packet received Errorcode %s" % err)
			self.logger.debug ("Failed Raw Response: " + ' '.join(format(x, '08b') for x in response )  )	
			return 0
		  
		  
	### Get AC Status
	## GEt the current status of the aircon and parse into status array a one have to send full status each time for update, cannot just send one setting
	##
	def get_ac_states(self,force_update = False):    
		GET_STATES =  bytearray.fromhex("0C00BB0006800000020011012B7E0000")  ##From app queryAuxinfo:bb0006800000020011012b7e
				
		##Check if the status is up to date to reduce timeout issues. Can be overwritten by force_update			
		self.logger.debug("Last update was: %s"%self.status['lastupdate'] )
		if (force_update == False and (self.status['lastupdate'] + self.update_interval) > time.time()) :
			return self.make_nice_status(self.status)
		
		
		response = self.send_packet(0x6a, GET_STATES)	
		##Check response, the checksums should be 0
		err = response[0x22] | (response[0x23] << 8)
		
		if err == 0:
			
			response_payload = bytes(self.decrypt(bytes(response[0x38:])))			
			
			response_payload = bytearray(response_payload)
			packet_type = response_payload[4]			
			if packet_type != 0x07:  ##Should be result packet, otherwise something weird
				return False
			
			packet_len = response_payload[0]
			if packet_len != 0x19:  ##should be 25, if not, then wrong packet
				return False
		
			self.logger.debug ("Raw AC Status: " + ' '.join(format(x, '08b') for x in response_payload[9:] )  )	
				
			response_payload  = response_payload[2:]  ##Drop leading stuff as dont need
			
			self.logger.debug ("Raw AC Status: " + ' '.join(format(x, '02x') for x in response_payload )  )
			#self.logger.debug ("" + ' '.join(format(x, '08b') for x in response_payload[9:] )  )
			
			#AuxInfo [tem=18, panMode=7, panType=1, nowTimeHour=5, setTem05=0, antoSenseYards=0, nowTimeMin=51, windSpeed=5, timerHour=0, voice=0, timerMin=0, mode=4, hasDew=0, hasSenseYards=0, hasSleep=0, isFollow=0, roomTem=0, roomHum=0, timeEnable=0, open=1, hasElectHeat=0, hasEco=0, hasClean=0, hasHealth=0, hasAir=0, weedSet=0, electronicLock=0, showDisplyBoard=1, mouldProof=0, controlMode=0, sleepMode=0]
			
			
			self.status['temp'] = 8+ (response_payload[10]>>3) + (0.5 * float(response_payload[12]>>7))
			self.status['power'] = response_payload[18] >>5 & 0b00000001
			self.status['fixation_v'] = response_payload[10] & 0b00000111
			self.status['mode'] = response_payload[15] >> 5 & 0b00001111
			self.status['sleep'] = response_payload[15] >> 2 & 0b00000001
			self.status['display'] =response_payload[20] >> 4 & 0b00000001
			self.status['mildew'] = response_payload[20] >> 3 & 0b00000001
			self.status['health'] = response_payload[18] >> 1 & 0b00000001
			self.status['fixation_h'] = response_payload[10]  & 0b00000111
			self.status['fanspeed']  = response_payload[13] >> 5 & 0b00000111
			self.status['ifeel'] = response_payload[15] >> 3& 0b00000001
			self.status['mute'] = response_payload[14] >> 7& 0b00000001
			self.status['turbo'] =response_payload[14] >> 6& 0b00000001
			self.status['clean'] = response_payload[18] >> 2& 0b00000001
			


			self.status['lastupdate'] = time.time()
			 
			return self.make_nice_status(self.status)
			
		else:
			return 0
			
			
		return self.status
		
		
	def make_nice_status(self,status):
		status_nice = {}
		status_nice['temp'] = status['temp']
		status_nice['ambient_temp'] = status['ambient_temp']
		status_nice['power'] = self.get_key(self.STATIC.ONOFF.__dict__,status['power'])
		status_nice['fixation_v'] = self.get_key(self.STATIC.FIXATION.VERTICAL.__dict__,status['fixation_v'])
		status_nice['mode'] = self.get_key(self.STATIC.MODE.__dict__,status['mode'])
		status_nice['sleep'] = self.get_key(self.STATIC.ONOFF.__dict__,status['sleep'])
		status_nice['display'] = self.get_key(self.STATIC.ONOFF.__dict__,status['display'])
		status_nice['mildew'] = self.get_key(self.STATIC.ONOFF.__dict__,status['mildew'])
		status_nice['health'] = self.get_key(self.STATIC.ONOFF.__dict__,status['health'])
		status_nice['fixation_h'] = self.get_key(self.STATIC.FIXATION.HORIZONTAL.__dict__,status['fixation_h'])
		
		
		status_nice['ifeel'] = self.get_key(self.STATIC.ONOFF.__dict__,status['ifeel'])
		status_nice['mute'] = self.get_key(self.STATIC.ONOFF.__dict__,status['mute'])
		status_nice['turbo'] = self.get_key(self.STATIC.ONOFF.__dict__,status['turbo'])
		status_nice['clean'] = self.get_key(self.STATIC.ONOFF.__dict__,status['clean'])
		
		status_nice['macaddress'] = status['macaddress']
		status_nice['device_name'] = status['devicename']
		
		##HomeKit topics
		if self.status['power'] == self.STATIC.ONOFF.OFF:
			status_nice['mode_homekit'] = "Off"		
		elif status['power'] == self.STATIC.ONOFF.ON and status['mode'] == self.STATIC.MODE.AUTO :
			status_nice['mode_homekit'] = "Auto"		
		elif status['power'] == self.STATIC.ONOFF.ON and status['mode'] == self.STATIC.MODE.HEATING :
			status_nice['mode_homekit'] = "HeatOn"
		elif status['power'] == self.STATIC.ONOFF.ON and status['mode'] == self.STATIC.MODE.COOLING :
			status_nice['mode_homekit'] = "CoolOn"
		else:
			status_nice['mode_homekit'] = "Error"
			
		##Home Assist topic	
		if self.status['power'] == self.STATIC.ONOFF.OFF:
			status_nice['mode_homeassistant'] = "off"		
		elif status['power'] == self.STATIC.ONOFF.ON and status['mode'] == self.STATIC.MODE.AUTO :
			status_nice['mode_homeassistant'] = "auto"		
		elif status['power'] == self.STATIC.ONOFF.ON and status['mode'] == self.STATIC.MODE.HEATING :
			status_nice['mode_homeassistant'] = "heat"
		elif status['power'] == self.STATIC.ONOFF.ON and status['mode'] == self.STATIC.MODE.COOLING :
			status_nice['mode_homeassistant'] = "cool"
		elif status['power'] == self.STATIC.ONOFF.ON and status['mode'] == self.STATIC.MODE.DRY :
			status_nice['mode_homeassistant'] = "dry"
		elif status['power'] == self.STATIC.ONOFF.ON and status['mode'] == self.STATIC.MODE.FAN :
			status_nice['mode_homeassistant'] = "fan_only"
		else:
			status_nice['mode_homeassistant'] = "Error"
		 
		##Make fanspeed logic
		status_nice['fanspeed']  = self.get_key(self.STATIC.FAN.__dict__,status['fanspeed'])
		status_nice['fanspeed_homeassistant']  = self.get_key(self.STATIC.FAN.__dict__,status['fanspeed']).title()

		if status_nice['mute'] == "ON":
			status_nice['fanspeed_homeassistant']  = "Mute"
			status_nice['fanspeed']  = "MUTE"
		elif status_nice['turbo'] == "ON":
			status_nice['fanspeed_homeassistant']  = "Turbo"
			status_nice['fanspeed']  = "TURBO"
		
			
		return status_nice
			
	def get_key(self,list,search_value):
		
		for key,value in list.items():  			
			if value == search_value:
				return key
		##Not found so return value;
		return search_value
			
			
	###  UDP checksum function
	def checksum_func(self,data):
		checksum = 0
		data_len = len(data)
		if (data_len%2) == 1:
			data_len += 1
			data += struct.pack('!B', 0)

		for i in range(0, len(data), 2):
			w = (data[i] << 8) + (data[i + 1])
			checksum += w

		checksum = (checksum >> 16) + (checksum & 0xFFFF)
		checksum = ~checksum&0xFFFF
		return checksum
		
  
	def set_ac_status(self):
		self.logger.debug("Start set_ac_status")
		#packet = bytearray(32)
		#10111011 00000000 00000110 10000000 00000000 00000000 00001111 00000000 00000001 9 00000001 10 01000111 11 00101000  12 00100000 13 10100000 14 00000000 15 00100000  16 00000000 17 00000000 18 00100000 19 00000000 20 00010000 21 00000000 22 00000101 10010001 10010101
		
		if self.status['temp'] < 16:			
			temperature = 16-8
			temperature_05 = 0
			
			##Make sure to fix the global status as well
			self.status['temp'] = 16
			
		elif self.status['temp'] > 32:
			temperature = 32-8
			temperature_05 = 0
			##Make sure to fix the global status as well
			self.status['temp'] = 32
			
		else:
			##if 0.5 then make true	. Also  offset with 8
			if self.status['temp'].is_integer():
				temperature = int( self.status['temp'] - 8 ) 
				temperature_05 = 0
			else:
				temperature_05 = 1	
				temperature = int(self.status['temp'] -8)
		
		
		payload  = bytearray(23)
		payload[0] = 0xbb
		payload[1] = 0x00
		payload[2] = 0x06  # Send command, seems like 07 is response
		payload[3] = 0x80
		payload[4] = 0x00
		payload[5] = 0x00
		payload[6] = 0x0f  # Set status .. #02 -> get info?
		payload[7] = 0x00
		payload[8] = 0x01
		payload[9] = 0x01
		payload[10] = 0b00000000 | temperature << 3 | self.status['fixation_v'] 
		payload[11] = 0b00000000 | self.status['fixation_h'] <<5
		payload[12] = 0b00001111 | temperature_05 << 7   # bit 1:  0.5  #bit   if 0b?1 then nothing done....  last 6 is some sort of packet_id
		payload[13] = 0b00000000 | self.status['fanspeed'] << 5
		payload[14] = 0b00000000 | self.status['turbo'] << 6 | self.status['mute'] << 7
		payload[15] = 0b00000000 | self.status['mode'] << 5 | self.status['sleep'] << 2   
		payload[16] = 0b00000000
		payload[17] = 0x00
		payload[18] = 0b00000000 | self.status['power']<<5 | self.status['health'] << 1 | self.status['clean'] << 2
		payload[19] = 0x00
		payload[20] = 0b00000000 |  self.status['display'] <<4  | self.status['mildew'] << 3
		payload[21] = 0b00000000  
		payload[22] = 0b00000000 
		
		self.logger.debug ("Payload:"+ ''.join(format(x, '02x') for x in payload))
		
		# first byte is length, Then placeholder then payload +2 for CRC16	
		request_payload = bytearray(32)		
		request_payload[0] = len(payload) + 2  ##Length plus of payload plus crc			
		request_payload[2:len(payload)+2] = payload  ##Add the Payload
		
		# append CRC
		crc = self.checksum_func(payload)
		self.logger.debug ("Checksum:"+format(crc,'02x'))
		request_payload[len(payload)+1] = ((crc >> 8) & 0xFF)
		request_payload[len(payload)+2] = crc & 0xFF
		
		
		
		self.logger.debug ("Packet:"+ ''.join(format(x, '02x') for x in request_payload))
		
		response = self.send_packet(0x6a, request_payload)
		self.logger.debug ("Resposnse:" + ''.join(format(x, '02x') for x in response))

		err = response[0x22] | (response[0x23] << 8)
		if err == 0:
			
			
			response_payload = self.decrypt(bytes(response[0x38:]))
			response_payload = bytearray(response_payload)


			packet_type = response_payload[4]						
			if packet_type == 0x07:  ##Should be result packet, otherwise something weird
				return self.status
			else:
				return False
				
		
			
			self.logger.debug ("Payload: Nice:" + ''.join(x.encode('hex') for x in response_payload ))

		return "done"

class ConnectError(Exception):
	"""Base error class"""
	pass

class ConnectTimeout(ConnectError):
	"""Connection Timeout"""
	pass


class ac_db_debug(device):
	import logging
	
	type = "ac_db"

	def __init__ (self, host, mac,name=None,cloud=None,debug = False,update_interval = 0,devtype=None,auth=False):			
		device.__init__(self, host, mac,name=name,cloud=cloud,devtype=devtype,update_interval=update_interval)	
		
		devtype = devtype
		self.status = {}		
		self.logger = self.logging.getLogger(__name__)	
		 
		self.update_interval = update_interval
		
		##Set default values
		#mac = mac[::-1]
		
		self.set_default_values()	

		self.status['macaddress'] = ''.join(format(x, '02x') for x in mac) 
		self.status['hostip'] = host
		self.status['name'] = name
		
		
		self.logging.basicConfig(level=(self.logging.DEBUG if debug else self.logging.INFO))
		self.logger.debug("Debugging Enabled")		
		
		
		
		self.logger.debug("Authenticating")
		if self.auth() == False:
			print ("Authentication Failed to AC")					
			
		
		
		self.logger.debug("Setting test temperature")			
		self.set_temperature(25)
		
		##Get the current details
		self.logger.debug("Getting current details in init")			
		#self.get_ac_states(force_update = True)

	def get_ac_states(self,force_update = False):    
		GET_STATES =  bytearray.fromhex("0C00BB0006800000020011012B7E0000")  ##From app queryAuxinfo:bb0006800000020011012b7e
				
		##Check if the status is up to date to reduce timeout issues. Can be overwritten by force_update			
		self.logger.debug("Last update was: %s"%self.status['lastupdate'] )
		if (force_update == False and (self.status['lastupdate'] + self.update_interval) > time.time()) :
			return self.make_nice_status(self.status)
		
		
		response = self.send_packet(0x6a, GET_STATES)	
		##Check response, the checksums should be 0
		err = response[0x22] | (response[0x23] << 8)
		
		if err == 0:
			
			response_payload = bytes(self.decrypt(bytes(response[0x38:])))			
			
			response_payload = bytearray(response_payload)
			packet_type = response_payload[4]			
			if packet_type != 0x07:  ##Should be result packet, otherwise something weird
				return False
			
			packet_len = response_payload[0]
			if packet_len != 0x19:  ##should be 25, if not, then wrong packet
				return False
		
			self.logger.debug ("Raw AC Status: " + ' '.join(format(x, '08b') for x in response_payload[9:] )  )	
				
			response_payload  = response_payload[2:]  ##Drop leading stuff as dont need
			
			self.logger.debug ("Raw AC Status: " + ' '.join(format(x, '02x') for x in response_payload )  )
			#self.logger.debug ("" + ' '.join(format(x, '08b') for x in response_payload[9:] )  )
			
			#AuxInfo [tem=18, panMode=7, panType=1, nowTimeHour=5, setTem05=0, antoSenseYards=0, nowTimeMin=51, windSpeed=5, timerHour=0, voice=0, timerMin=0, mode=4, hasDew=0, hasSenseYards=0, hasSleep=0, isFollow=0, roomTem=0, roomHum=0, timeEnable=0, open=1, hasElectHeat=0, hasEco=0, hasClean=0, hasHealth=0, hasAir=0, weedSet=0, electronicLock=0, showDisplyBoard=1, mouldProof=0, controlMode=0, sleepMode=0]
			
			
			self.status['temp'] = 8+ (response_payload[10]>>3) + (0.5 * float(response_payload[12]>>7))
			self.status['power'] = response_payload[18] >>5 & 0b00000001
			self.status['fixation_v'] = response_payload[10] & 0b00000111
			self.status['mode'] = response_payload[15] >> 5 & 0b00001111
			self.status['sleep'] = response_payload[15] >> 2 & 0b00000001
			self.status['display'] =response_payload[20] >> 4 & 0b00000001
			self.status['mildew'] = response_payload[20] >> 3 & 0b00000001
			self.status['health'] = response_payload[18] >> 1 & 0b00000001
			self.status['fixation_h'] = response_payload[11] >> 5 & 0b00000111
			self.status['fanspeed']  = response_payload[13] >> 5 & 0b00000111
			self.status['ifeel'] = response_payload[15] >> 3& 0b00000001
			self.status['mute'] = response_payload[14] >> 7& 0b00000001
			self.status['turbo'] =response_payload[14] >> 6& 0b00000001
			self.status['clean'] = response_payload[18] >> 2& 0b00000001
			


			self.status['lastupdate'] = time.time()
			 
			return self.make_nice_status(self.status)
			
		else:
			return 0
			
			
		return self.status

	def set_default_values(self):
				
		

		self.status['temp'] = float(19)
		self.status['fixation_v'] =  ac_db.STATIC.FIXATION.VERTICAL.AUTO
		self.status['power'] = ac_db.STATIC.ONOFF.ON
		self.status['mode'] = ac_db.STATIC.MODE.AUTO
		self.status['sleep'] = ac_db.STATIC.ONOFF.OFF
		self.status['display'] = ac_db.STATIC.ONOFF.ON
		self.status['health'] = ac_db.STATIC.ONOFF.OFF  
		self.status['ifeel'] = ac_db.STATIC.ONOFF.OFF
		self.status['fixation_h'] = ac_db.STATIC.FIXATION.HORIZONTAL.LEFT_RIGHT_FIX
		self.status['fanspeed']  = ac_db.STATIC.FAN.AUTO
		self.status['turbo'] = ac_db.STATIC.ONOFF.OFF
		self.status['mute'] = ac_db.STATIC.ONOFF.OFF
		self.status['clean'] = ac_db.STATIC.ONOFF.OFF
		self.status['mildew'] = ac_db.STATIC.ONOFF.OFF
		self.status['macaddress'] = None
		self.status['hostip'] = None
		self.status['lastupdate'] = None
		self.status['ambient_temp'] = None
		self.status['devicename'] = None
		
		
		
	def set_temperature(self,temperature):
		self.logger.debug("Setting temprature to %s",temperature)
		#self.get_ac_states()		
		self.status['temp'] = float(temperature)
		
		self.set_ac_status()
		#return self.make_nice_status(self.status)

	def set_ac_status(self):
		self.logger.debug("Start set_ac_status")
		#packet = bytearray(32)
		#10111011 00000000 00000110 10000000 00000000 00000000 00001111 00000000 00000001 9 00000001 10 01000111 11 00101000  12 00100000 13 10100000 14 00000000 15 00100000  16 00000000 17 00000000 18 00100000 19 00000000 20 00010000 21 00000000 22 00000101 10010001 10010101
		#print "setting something"
		if self.status['temp'] < 16:			
			temperature = 16-8
			temperature_05 = 0
			
			##Make sure to fix the global status as well
			self.status['temp'] = 16
			
		elif self.status['temp'] > 32:
			temperature = 32-8
			temperature_05 = 0
			##Make sure to fix the global status as well
			self.status['temp'] = 32
			
		else:
			##if 0.5 then make true	. Also  offset with 8
			if self.status['temp'].is_integer():
				temperature = int( self.status['temp'] - 8 ) 
				temperature_05 = 0
			else:
				temperature_05 = 1	
				temperature = int(self.status['temp'] -8)
		#print temperature
		
		payload  = bytearray(23)
		payload[0] = 0xbb
		payload[1] = 0x00
		payload[2] = 0x06  # Send command, seems like 07 is response
		payload[3] = 0x80
		payload[4] = 0x00
		payload[5] = 0x00
		payload[6] = 0x0f  # Set status .. #02 -> get info?
		payload[7] = 0x00
		payload[8] = 0x01
		payload[9] = 0x01
		payload[10] = 0b00000000 | temperature << 3 | self.status['fixation_v'] 
		payload[11] = 0b00000000 | self.status['fixation_h'] <<5
		payload[12] = 0b00001111 | temperature_05 << 7   # bit 1:  0.5  #bit   if 0b?1 then nothing done....  last 6 is some sort of packet_id
		payload[13] = 0b00000000 | self.status['fanspeed'] << 5
		payload[14] = 0b00000000 | self.status['turbo'] << 6 | self.status['mute'] << 7
		payload[15] = 0b00000000 | self.status['mode'] << 5 | self.status['sleep'] << 2   
		payload[16] = 0b00000000
		payload[17] = 0x00
		payload[18] = 0b00000000 | self.status['power']<<5 | self.status['health'] << 1 | self.status['clean'] << 2
		payload[19] = 0x00
		payload[20] = 0b00000000 |  self.status['display'] <<4  | self.status['mildew'] << 3
		payload[21] = 0b00000000  
		payload[22] = 0b00000000 
		
		#print ("Payload:"+ ''.join(format(x, '02x') for x in payload))
		
		# first byte is length, Then placeholder then payload +2 for CRC16	
		request_payload = bytearray(32)		
		request_payload[0] = len(payload) + 2  ##Length plus of payload plus crc			
		request_payload[2:len(payload)+2] = payload  ##Add the Payload
		
		# append CRC
		
		crc = self.checksum_func(payload)
		#print ("Checksum:"+format(crc,'02x'))
		request_payload[len(payload)+1] = ((crc >> 8) & 0xFF)
		request_payload[len(payload)+2] = crc & 0xFF
		
		
		
		#print ("Packet:"+ ''.join(format(x, '02x') for x in request_payload))
		
		response = self.send_packet(0x6a, request_payload)
		self.logger.debug ("Resposnse:" + ''.join(format(x, '02x') for x in response))

		err = response[0x22] | (response[0x23] << 8)
		if err == 0:
			
			response_payload = self.decrypt(bytes(response[0x38:]))
			response_payload = bytearray(response_payload)
			packet_type = response_payload[4]						
			if packet_type == 0x07:  ##Should be result packet, otherwise something weird
				return self.status
			else:
				return False
				
		
			
			self.logger.debug ("Payload: Nice:" + ''.join(x.encode('hex') for x in response_payload ))

		return "done"
	def checksum_func(self,data):
		checksum = 0
		data_len = len(data)
		if (data_len%2) == 1:
			data_len += 1
			data += struct.pack('!B', 0)

		for i in range(0, len(data), 2):
			w = (data[i] << 8) + (data[i + 1])
			checksum += w

		checksum = (checksum >> 16) + (checksum & 0xFFFF)
		checksum = ~checksum&0xFFFF
		return checksum

	def	 send_packet(self, command, payload):
		self.count = (self.count + 1) & 0xffff
		packet = bytearray(0x38)
		packet[0x00] = 0x5a
		packet[0x01] = 0xa5
		packet[0x02] = 0xaa
		packet[0x03] = 0x55
		packet[0x04] = 0x5a
		packet[0x05] = 0xa5
		packet[0x06] = 0xaa
		packet[0x07] = 0x55
		packet[0x24] = 0x2a #==> Type
		packet[0x25] = 0x4e #==> Type
		packet[0x26] = command
		packet[0x28] = self.count & 0xff
		packet[0x29] = self.count >> 8
		packet[0x2a] = self.mac[0]
		packet[0x2b] = self.mac[1]
		packet[0x2c] = self.mac[2]
		packet[0x2d] = self.mac[3]
		packet[0x2e] = self.mac[4]
		packet[0x2f] = self.mac[5]
		packet[0x30] = self.id[0]
		packet[0x31] = self.id[1]
		packet[0x32] = self.id[2]
		packet[0x33] = self.id[3]

		checksum = 0xbeaf
		for i in range(len(payload)):
			checksum += payload[i]
			checksum = checksum & 0xffff

		
		payload = self.encrypt(bytes(payload))

		packet[0x34] = checksum & 0xff
		packet[0x35] = checksum >> 8

		for i in range(len(payload)):
		 	packet.append(payload[i])

		checksum = 0xbeaf
		for i in range(len(packet)):
			checksum += packet[i]
			checksum = checksum & 0xffff
		packet[0x20] = checksum & 0xff
		packet[0x21] = checksum >> 8

		#print 'Sending Packet:\n'+''.join(format(x, '02x') for x in packet)+"\n"
		starttime = time.time()

		with self.lock:
			while True:
				try:
					self.cs.sendto(packet, self.host)
					self.cs.settimeout(1)
					response = self.cs.recvfrom(1024)
					#print response
					break
				except socket.timeout:
					if (time.time() - starttime) < self.timeout:
						pass
					#print "timedout"
					raise ConnectTimeout(200,self.host)
		return bytearray(response[0])	

	def auth(self):
		payload = bytearray(0x50)
		payload[0x04] = 0x31
		payload[0x05] = 0x31
		payload[0x06] = 0x31
		payload[0x07] = 0x31
		payload[0x08] = 0x31
		payload[0x09] = 0x31
		payload[0x0a] = 0x31
		payload[0x0b] = 0x31
		payload[0x0c] = 0x31
		payload[0x0d] = 0x31
		payload[0x0e] = 0x31
		payload[0x0f] = 0x31
		payload[0x10] = 0x31
		payload[0x11] = 0x31
		payload[0x12] = 0x31
		payload[0x1e] = 0x01
		payload[0x2d] = 0x01
		payload[0x30] = ord('T')
		payload[0x31] = ord('e')
		payload[0x32] = ord('s')
		payload[0x33] = ord('t')
		payload[0x34] = ord(' ')
		payload[0x35] = ord(' ')
		payload[0x36] = ord('1')

	
		response = self.send_packet(0x65, payload)    

		enc_payload = response[0x38:]

		
		payload = self.decrypt(bytes(enc_payload))
		
		if not payload:
			return False

		key = payload[0x04:0x14]
		if len(key) % 16 != 0:
			return False

		self.id = payload[0x00:0x04]
		self.key = key
		return True