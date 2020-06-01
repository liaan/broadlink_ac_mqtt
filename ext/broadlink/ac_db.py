#!/usr/bin/python
# -*- coding: utf8 -*-

from datetime import datetime
from Crypto.Cipher import AES
import time
import random
import socket
import threading
import parser
import struct

def gendevice(devtype, host, mac):
  #print format(devtype,'02x')
  if devtype == 0: # SP1
    return sp1(host=host, mac=mac)
  if devtype == 0x2711: # SP2
    return sp2(host=host, mac=mac)
  if devtype == 0x2719 or devtype == 0x7919 or devtype == 0x271a or devtype == 0x791a: # Honeywell SP2
    return sp2(host=host, mac=mac)
  if devtype == 0x2720: # SPMini
    return sp2(host=host, mac=mac)
  elif devtype == 0x753e: # SP3
    return sp2(host=host, mac=mac)
  elif devtype == 0x2728: # SPMini2
    return sp2(host=host, mac=mac)
  elif devtype == 0x2733 or devtype == 0x273e: # OEM branded SPMini
    return sp2(host=host, mac=mac)
  elif devtype >= 0x7530 and devtype <= 0x7918: # OEM branded SPMini2
    return sp2(host=host, mac=mac)
  elif devtype == 0x2736: # SPMiniPlus
    return sp2(host=host, mac=mac)
  elif devtype == 0x2712: # RM2
    return rm(host=host, mac=mac)
  elif devtype == 0x2737: # RM Mini
    return rm(host=host, mac=mac)
  elif devtype == 0x273d: # RM Pro Phicomm
    return rm(host=host, mac=mac)
  elif devtype == 0x2783: # RM2 Home Plus
    return rm(host=host, mac=mac)
  elif devtype == 0x277c: # RM2 Home Plus GDT
    return rm(host=host, mac=mac)
  elif devtype == 0x272a: # RM2 Pro Plus
    return rm(host=host, mac=mac)
  elif devtype == 0x2787: # RM2 Pro Plus2
    return rm(host=host, mac=mac)
  elif devtype == 0x278b: # RM2 Pro Plus BL
    return rm(host=host, mac=mac)
  elif devtype == 0x278f: # RM Mini Shate
    return rm(host=host, mac=mac)
  elif devtype == 0x2714: # A1
    return a1(host=host, mac=mac)
  elif devtype == 0x4EB5: # MP1
    return mp1(host=host, mac=mac)
  elif devtype == 0x4E2a: # Danham Bush
    return ac_db(host=host, mac=mac)
  else:
    return device(host=host, mac=mac)

def discover(timeout=None, local_ip_address=None):
  if local_ip_address is None:
      s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      s.connect(('8.8.8.8', 53))  # connecting to a UDP address doesn't send packets
      local_ip_address = s.getsockname()[0]
  address = local_ip_address.split('.')
  cs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  cs.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  cs.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
  cs.bind((local_ip_address,0))
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
    devtype = responsepacket[0x34] | responsepacket[0x35] << 8
    return gendevice(devtype, host, mac)
  else:
    while (time.time() - starttime) < timeout:
      cs.settimeout(timeout - (time.time() - starttime))
      try:
        response = cs.recvfrom(1024)
      except socket.timeout:
        return devices
      responsepacket = bytearray(response[0])
      
      #print ":".join("{:02x}".format(c) for c in responsepacket)

      host = response[1]
      devtype = responsepacket[0x34] | responsepacket[0x35] << 8
      mac = responsepacket[0x3a:0x40]
	  
      dev = gendevice(devtype, host, mac)
      devices.append(dev)
    return devices


class device:
  def __init__(self, host, mac, timeout=10):
    self.host = host
    self.mac = mac
    self.timeout = timeout
    self.count = random.randrange(0xffff)
    self.key = bytearray([0x09, 0x76, 0x28, 0x34, 0x3f, 0xe9, 0x9e, 0x23, 0x76, 0x5c, 0x15, 0x13, 0xac, 0xcf, 0x8b, 0x02])
    self.iv = bytearray([0x56, 0x2e, 0x17, 0x99, 0x6d, 0x09, 0x3d, 0x28, 0xdd, 0xb3, 0xba, 0x69, 0x5a, 0x2e, 0x6f, 0x58])
    self.id = bytearray([0, 0, 0, 0])
    self.cs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.cs.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.cs.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    self.cs.bind(('',0))
    self.type = "Unknown"
    self.lock = threading.Lock()

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

    aes = AES.new(bytes(self.key), AES.MODE_CBC, bytes(self.iv))
    payload = aes.decrypt(bytes(enc_payload))

    if not payload:
     return False

    key = payload[0x04:0x14]
    if len(key) % 16 != 0:
     return False

    self.id = payload[0x00:0x04]
    self.key = key
    return True

  def get_type(self):
    return self.type

  def send_packet(self, command, payload):
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

    aes = AES.new(bytes(self.key), AES.MODE_CBC, bytes(self.iv))
    payload = aes.encrypt(bytes(payload))

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
          raise
    return bytearray(response[0])


class mp1(device):
  def __init__ (self, host, mac):
    device.__init__(self, host, mac)
    self.type = "MP1"

  def set_power_mask(self, sid_mask, state):
    """Sets the power state of the smart power strip."""

    packet = bytearray(16)
    packet[0x00] = 0x0d
    packet[0x02] = 0xa5
    packet[0x03] = 0xa5
    packet[0x04] = 0x5a
    packet[0x05] = 0x5a
    packet[0x06] = 0xb2 + ((sid_mask<<1) if state else sid_mask)
    packet[0x07] = 0xc0
    packet[0x08] = 0x02
    packet[0x0a] = 0x03
    packet[0x0d] = sid_mask
    packet[0x0e] = sid_mask if state else 0

    response = self.send_packet(0x6a, packet)

    err = response[0x22] | (response[0x23] << 8)

  def set_power(self, sid, state):
    """Sets the power state of the smart power strip."""
    sid_mask = 0x01 << (sid - 1)
    return self.set_power_mask(sid_mask, state)

  def check_power(self):
    """Returns the power state of the smart power strip."""
    packet = bytearray(16)
    packet[0x00] = 0x0a
    packet[0x02] = 0xa5
    packet[0x03] = 0xa5
    packet[0x04] = 0x5a
    packet[0x05] = 0x5a
    packet[0x06] = 0xae
    packet[0x07] = 0xc0
    packet[0x08] = 0x01

    response = self.send_packet(0x6a, packet)
    err = response[0x22] | (response[0x23] << 8)
    if err == 0:
      aes = AES.new(bytes(self.key), AES.MODE_CBC, bytes(self.iv))
      payload = aes.decrypt(bytes(response[0x38:]))
      if type(payload[0x4]) == int:
        state = payload[0x0e]
      else:
        state = ord(payload[0x0e])
      data = {}
      data['s1'] = bool(state & 0x01)
      data['s2'] = bool(state & 0x02)
      data['s3'] = bool(state & 0x04)
      data['s4'] = bool(state & 0x08)
      return data


class sp1(device):
  def __init__ (self, host, mac):
    device.__init__(self, host, mac)
    self.type = "SP1"

  def set_power(self, state):
    packet = bytearray(4)
    packet[0] = state
    self.send_packet(0x66, packet)


class sp2(device):
  def __init__ (self, host, mac):
    device.__init__(self, host, mac)
    self.type = "SP2"

  def set_power(self, state):
    """Sets the power state of the smart plug."""
    packet = bytearray(16)
    packet[0] = 2
    packet[4] = 1 if state else 0
    self.send_packet(0x6a, packet)

  def check_power(self):
    """Returns the power state of the smart plug."""
    packet = bytearray(16)
    packet[0] = 1
    response = self.send_packet(0x6a, packet)
    err = response[0x22] | (response[0x23] << 8)
    if err == 0:
      aes = AES.new(bytes(self.key), AES.MODE_CBC, bytes(self.iv))
      payload = aes.decrypt(bytes(response[0x38:]))
      return bool(payload[0x4])

class a1(device):
  def __init__ (self, host, mac):
    device.__init__(self, host, mac)
    self.type = "A1"

  def check_sensors(self):
    packet = bytearray(16)
    packet[0] = 1
    response = self.send_packet(0x6a, packet)
    err = response[0x22] | (response[0x23] << 8)
    if err == 0:
      data = {}
      aes = AES.new(bytes(self.key), AES.MODE_CBC, bytes(self.iv))
      payload = aes.decrypt(bytes(response[0x38:]))
      if type(payload[0x4]) == int:
        data['temperature'] = (payload[0x4] * 10 + payload[0x5]) / 10.0
        data['humidity'] = (payload[0x6] * 10 + payload[0x7]) / 10.0
        light = payload[0x8]
        air_quality = payload[0x0a]
        noise = payload[0xc]
      else:
        data['temperature'] = (ord(payload[0x4]) * 10 + ord(payload[0x5])) / 10.0
        data['humidity'] = (ord(payload[0x6]) * 10 + ord(payload[0x7])) / 10.0
        light = ord(payload[0x8])
        air_quality = ord(payload[0x0a])
        noise = ord(payload[0xc])
      if light == 0:
        data['light'] = 'dark'
      elif light == 1:
        data['light'] = 'dim'
      elif light == 2:
        data['light'] = 'normal'
      elif light == 3:
        data['light'] = 'bright'
      else:
        data['light'] = 'unknown'
      if air_quality == 0:
        data['air_quality'] = 'excellent'
      elif air_quality == 1:
        data['air_quality'] = 'good'
      elif air_quality == 2:
        data['air_quality'] = 'normal'
      elif air_quality == 3:
        data['air_quality'] = 'bad'
      else:
        data['air_quality'] = 'unknown'
      if noise == 0:
        data['noise'] = 'quiet'
      elif noise == 1:
        data['noise'] = 'normal'
      elif noise == 2:
        data['noise'] = 'noisy'
      else:
        data['noise'] = 'unknown'
      return data

  def check_sensors_raw(self):
    packet = bytearray(16)
    packet[0] = 1
    response = self.send_packet(0x6a, packet)
    err = response[0x22] | (response[0x23] << 8)
    if err == 0:
      data = {}
      aes = AES.new(bytes(self.key), AES.MODE_CBC, bytes(self.iv))
      payload = aes.decrypt(bytes(response[0x38:]))
      if type(payload[0x4]) == int:
        data['temperature'] = (payload[0x4] * 10 + payload[0x5]) / 10.0
        data['humidity'] = (payload[0x6] * 10 + payload[0x7]) / 10.0
        data['light'] = payload[0x8]
        data['air_quality'] = payload[0x0a]
        data['noise'] = payload[0xc]
      else:
        data['temperature'] = (ord(payload[0x4]) * 10 + ord(payload[0x5])) / 10.0
        data['humidity'] = (ord(payload[0x6]) * 10 + ord(payload[0x7])) / 10.0
        data['light'] = ord(payload[0x8])
        data['air_quality'] = ord(payload[0x0a])
        data['noise'] = ord(payload[0xc])
      return data


class rm(device):
  def __init__ (self, host, mac):
    device.__init__(self, host, mac)
    self.type = "RM2"

  def check_data(self):
    packet = bytearray(16)
    packet[0] = 4
    response = self.send_packet(0x6a, packet)
    err = response[0x22] | (response[0x23] << 8)
    if err == 0:
      aes = AES.new(bytes(self.key), AES.MODE_CBC, bytes(self.iv))
      payload = aes.decrypt(bytes(response[0x38:]))
      return payload[0x04:]

  def send_data(self, data):
    packet = bytearray([0x02, 0x00, 0x00, 0x00])
    packet += data
    self.send_packet(0x6a, packet)

  def enter_learning(self):
    packet = bytearray(16)
    packet[0] = 3
    self.send_packet(0x6a, packet)

  def check_temperature(self):
    packet = bytearray(16)
    packet[0] = 1
    response = self.send_packet(0x6a, packet)
    err = response[0x22] | (response[0x23] << 8)
    if err == 0:
      aes = AES.new(bytes(self.key), AES.MODE_CBC, bytes(self.iv))
      payload = aes.decrypt(bytes(response[0x38:]))
      if type(payload[0x4]) == int:
        temp = (payload[0x4] * 10 + payload[0x5]) / 10.0
      else:
        temp = (ord(payload[0x4]) * 10 + ord(payload[0x5])) / 10.0
      return temp
	  
class ac_db(device):
	import logging
	 
	type = "ac_db"
	devtype =  0x4E2a
	update_interval = 30
	
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
				LEFT_FIX = 2;
				LEFT_FLAP = 1;
				LEFT_RIGHT_FIX = 7;
				LEFT_RIGHT_FLAP = 0;
				RIGHT_FIX = 6;
				RIGHT_FLAP = 5;
				ON = 0
				OFF = 1
			
		class FAN:
			LOW = 	0b00000011
			MID = 	0b00000010
			HIGH =	0b00000001
			AUTO = 	0b00000101  
				
		class MODE:
			COOLING	=	0b00000001
			DRY		=	0b00000010
			HEATING	=	0b00000100
			AUTO	=	0b00000000
			FAN 	=	0b00000110   
			
		class ONOFF:
			OFF = 0
			ON = 1
	
	
 
	def __init__ (self, host, mac,debug = False,update_interval = 30):			
		device.__init__(self, host, mac)	
		
		
		self.status = {}		
		self.logger = self.logging.getLogger(__name__)		
		self.update_interval = update_interval
		
		##Set default values
		mac = mac[::-1]
		
		self.set_default_values()		
		self.status['macaddress'] = ''.join(format(x, '02x') for x in mac) 
		self.status['hostip'] = host
		
		self.logging.basicConfig(level=(self.logging.DEBUG if debug else self.logging.INFO))
		self.logger.debug("Debugging Enabled");		
			
		
		
		##Populate array with latest data
		self.logger.debug("Authenticating")
		if self.auth() == False:
			return False;
		
		self.logger.debug("Getting current details in init")		
		
		self.get_ac_status(force_update = True);

	def get_ac_status(self,force_update = False):
		
		if (force_update == False and (self.status['lastupdate'] + self.update_interval) > time.time()) :
			return self.make_nice_status(self.status)
			
		##Get AC info(also populates the current temp)
		self.get_ac_info()
		##Get the current status
		status = self.get_ac_states(True)
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
		debug  = 0;
		
		
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
			self.set_ac_status()
			return self.make_nice_status(self.status)
		else:
			self.logger.debug("Not found mode value %s" , str(mode_text))
			return False
	
	def set_homekit_status(self,status):
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
			
		elif status.lower() == "off":
			self.status['power'] =  self.STATIC.ONOFF.OFF
			self.set_ac_status()
			return self.make_nice_status(self.status)
		else:
			self.logger.debug('Invalid status for homekit %s',status)
			return False
			
	def set_homeassist_status(self,status):
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
		  aes = AES.new(bytes(self.key), AES.MODE_CBC, bytes(self.iv))

		  response_payload = aes.decrypt(bytes(response[0x38:]))

		  #print "AC INFO Payload:" + response_payload+"\n"
		  #print "AC INFO::" + ''.join(x.encode('hex') for x in response_payload )
		  response_payload = bytearray(response_payload)
		  
		  
		  #print "AC INFO Payload:" + response_payload+"\n"
		  #print "bla"  + ' '.join(format(x, '08b') for x in response_payload[9:] )  
		  
		  #print "AC INFO2:" + ''.join(x.encode('binary') for x in response_payload )
		  
		  response_payload  = response_payload[2:]  ##Drop leading stuff as dont need
		  self.logger.debug ("AcInfo: " + ' '.join(format(x, '08b') for x in response_payload[9:] )  )	

		  
		  
		  ##Its only the last 5 bits?
		  self.status['ambient_temp'] = response_payload[15] & 0b00011111
		  
		  return self.make_nice_status(self.status)
		else:
		  return 0
		  
		  
	### Get AC Status
	## GEt the current status of the aircon and parse into status array a one have to send full status each time for update, cannot just send one setting
	##
	def get_ac_states(self,force_update = False):    
		GET_STATES =  bytearray.fromhex("0C00BB0006800000020011012B7E0000")  ##From app
		
		##Check if the status is up to date to reduce timeout issues. Can be overwritten by force_update
		if (force_update == False and (self.status['lastupdate'] + self.update_interval) > time.time()) :
			return self.make_nice_status(self.status)
		
		response = self.send_packet(0x6a, GET_STATES)	
		##Check response, the checksums should be 0
		err = response[0x22] | (response[0x23] << 8)
		
		if err == 0:
			aes = AES.new(bytes(self.key), AES.MODE_CBC, bytes(self.iv))
			response_payload = bytes(aes.decrypt(bytes(response[0x38:])))			
			
			response_payload = bytearray(response_payload)
			packet_type = response_payload[4]			
			if packet_type != 0x07:  ##Should be result packet, otherwise something weird
				return False
			
			packet_len = response_payload[0]
			if packet_len != 0x19:  ##should be 25, if not, then wrong packet
				return False
		
			self.logger.debug ("" + ' '.join(format(x, '08b') for x in response_payload[9:] )  )	
			response_payload  = response_payload[2:]  ##Drop leading stuff as dont need
			#self.logger.debug ("" + ' '.join(format(x, '08b') for x in response_payload[9:] )  )
			
			
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
		status_nice['fixation_h'] = self.get_key(self.STATIC.FIXATION.VERTICAL.__dict__,status['fixation_h'])
		status_nice['fanspeed']  = self.get_key(self.STATIC.FAN.__dict__,status['fanspeed'])
		status_nice['ifeel'] = self.get_key(self.STATIC.ONOFF.__dict__,status['ifeel'])
		status_nice['mute'] = self.get_key(self.STATIC.ONOFF.__dict__,status['mute'])
		status_nice['turbo'] = self.get_key(self.STATIC.ONOFF.__dict__,status['turbo'])
		status_nice['clean'] = self.get_key(self.STATIC.ONOFF.__dict__,status['clean'])
		
		status_nice['macaddress'] = status['macaddress']
		##HomeKit topics
		if self.status['power'] == self.STATIC.ONOFF.OFF:
			status_nice['homekit'] = "Off"		
		elif status['power'] == self.STATIC.ONOFF.ON and status['mode'] == self.STATIC.MODE.AUTO :
			status_nice['homekit'] = "Auto"		
		elif status['power'] == self.STATIC.ONOFF.ON and status['mode'] == self.STATIC.MODE.HEATING :
			status_nice['homekit'] = "HeatOn"
		elif status['power'] == self.STATIC.ONOFF.ON and status['mode'] == self.STATIC.MODE.COOLING :
			status_nice['homekit'] = "CoolOn"
		else:
			status_nice['homekit'] = "Error"
		##Home Assist topic	
		if self.status['power'] == self.STATIC.ONOFF.OFF:
			status_nice['homeassist'] = "off"		
		elif status['power'] == self.STATIC.ONOFF.ON and status['mode'] == self.STATIC.MODE.AUTO :
			status_nice['homeassist'] = "auto"		
		elif status['power'] == self.STATIC.ONOFF.ON and status['mode'] == self.STATIC.MODE.HEATING :
			status_nice['homeassist'] = "heat"
		elif status['power'] == self.STATIC.ONOFF.ON and status['mode'] == self.STATIC.MODE.COOLING :
			status_nice['homeassist'] = "cool"
		else:
			status_nice['homeassist'] = "Error"
 			
			
		return status_nice
			
	def get_key(self,list,search_value):
		
		for key,value in list.iteritems():  			
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
		elif self.status['temp'] > 32:
			temperature = 32-8
			temperature_05 = 0
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
			aes = AES.new(bytes(self.key), AES.MODE_CBC, bytes(self.iv))		
			response_payload = aes.decrypt(bytes(response[0x38:]))
			response_payload = bytearray(response_payload)
			packet_type = response_payload[4]						
			if packet_type == 0x07:  ##Should be result packet, otherwise something weird
				return self.status
			else:
				return False
				
		
			
			self.logger.debug ("Payload: Nice:" + ''.join(x.encode('hex') for x in response_payload ))

		return "done"

	
# For legay compatibility - don't use this
class rm2(rm):
  def __init__ (self):
    device.__init__(self, None, None)

  def discover(self):
    dev = discover()
    self.host = dev.host
    self.mac = dev.mac
