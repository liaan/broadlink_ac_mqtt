#!/usr/bin/python
import sys
import yaml
import logging
import os
import tempfile
import argparse
import time
import broadlink_ac_mqtt.AcToMqtt as AcToMqtt
import broadlink_ac_mqtt.classes.broadlink.ac_db as ac_db_version

import signal
import traceback

logger = logging.getLogger(__name__)
AC = None
softwareversion = "1.2.1"


pid = str(os.getpid())
pidfile = "ac_to_mqtt.pid"
pid_stale_time = 5
pid_last_update = 0


do_loop = False
running = False
 


#*****************************************  Get going methods ************************************************

def discover_and_dump_for_config(config):
	AC = AcToMqtt.AcToMqtt(config)
	devices = AC.discover()
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
		
	sys.exit()



	
def read_config(config_file_path):
	
	config = {} 
	##Load config
	
	with open(config_file_path, "r") as ymlfile:
		config_file = yaml.load(ymlfile,Loader=yaml.SafeLoader)
	 
	##Service settings
	config["daemon_mode"] = config_file["service"]["daemon_mode"]
	config["update_interval"] = config_file["service"]["update_interval"]	
	config["self_discovery"] = config_file["service"]["self_discovery"]	
	##What ip to bind to
	config['bind_to_ip'] = config_file["service"].get("bind_to_ip") or None

	 
	
	##Mqtt settings
	config["mqtt_host"] = config_file["mqtt"].get("host")
	config["mqtt_port"] = config_file["mqtt"].get("port")
	config["mqtt_user"]= config_file["mqtt"].get("user")
	config["mqtt_password"] = config_file["mqtt"].get("passwd")
	##set client id if set, otherwise just add timestamp to generic to prevent conflicts
	config["mqtt_client_id"] = config_file["mqtt"]["client_id"] if config_file["mqtt"]["client_id"] else 'broadlink_to_mqtt-'+str(time.time())
	config["mqtt_topic_prefix"] = config_file["mqtt"]["topic_prefix"]
	config["mqtt_auto_discovery_topic"] = config_file["mqtt"]["auto_discovery_topic"] if "auto_discovery_topic" in config_file["mqtt"] else False
	config["mqtt_auto_discovery_topic_retain"] = config_file["mqtt"]["auto_discovery_topic_retain"] if "auto_discovery_topic_retain" in config_file["mqtt"] else False
	
	

	if config["mqtt_topic_prefix"] and config["mqtt_topic_prefix"].endswith("/") == False:
		config["mqtt_topic_prefix"] = config["mqtt_topic_prefix"] + "/"
		
	
	##Devices	 
	if config_file['devices'] != None:
		config["devices"] = config_file['devices']
	else:
		config["devices"] = None	
	
	return config
				

def stop_if_already_running():	
	if(check_if_running()):		
		sys.exit()

def init_logging(level,log_file_path):
		
		# Init logging
		logging.basicConfig(
			filename=log_file_path,
			level=level,
			format="%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s",
		 
		)
		
		console = logging.StreamHandler()
		console.setLevel(logging.INFO)
		# set a format which is simpler for console use
		formatter = logging.Formatter('%(message)s')
		
		# tell the handler to use this format
		console.setFormatter(formatter)
		logging.getLogger('').addHandler(console)

def touch_pid_file():
		global pid_last_update
		
		##No need to update very often
		if(pid_last_update + pid_stale_time -2 > time.time()):	
			return
		
		pid_last_update = time.time() 
		with open(pidfile, 'w') as f:
			f.write("%s,%s" % (os. getpid() ,pid_last_update))	

def check_if_running():
	
	##Check if there is pid, if there is, then check if valid or stale .. probably should add process id for race conditions but damn, this is a simple scripte.....
	logger.debug("Checking if already running")
	
	if os.path.isfile(pidfile):	
		
		logger.debug("%s already exists, checking if stale" % pidfile)
		
		##Check if stale
		f = open(pidfile, 'r') 
		if f.mode =="r":
			contents =f.read()
			contents = contents.split(',')
			
			##Stale, so go ahead
			if (1 in contents and (float(contents[1])+ pid_stale_time) < time.time()):
				logger.info("Pid is stale, so we'll just overwrite it go on")								
					
			else:				
				logger.info("Pid is still valid, so exit")																
				sys.exit()
			
	##Write current time
	touch_pid_file()
				

################ Signal handlers
def receiveSignal(signalNumber, frame):
	#print('Received:', signalNumber)
	stop(signalNumber, frame)
	return

def stop(signalNumber = 0, frame = 0):
	logger.info("Stopping")
	do_loop = False
	while running:
		logger.info("Waiting to stop")
		time.sleep(1)


	if AC is not None:
		AC.stop()
	##clean pid file
	if os.path.isfile(pidfile):
		os.unlink(pidfile)
	sys.exit()
	

def restart(signalNumber = 0, frame = 0):
	""

def init_signal():
#	signal.signal(signal.SIGUSR2, receiveSignal)
	#signal.signal(signal.SIGPIPE, receiveSignal)
	#signal.signal(signal.SIGALRM, receiveSignal)
	signal.signal(signal.SIGTERM, stop)


#################  Main startup ####################
				
def start():
	
	##Handle signal
	init_signal()
	
	##Just some defaults
	##Defaults		
	global AC	
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
	parser.add_argument("-mp", "--mqttport", help="Mqtt Port", type=int )
	parser.add_argument("-mU", "--mqttuser", help="Mqtt User" )
	parser.add_argument("-mP", "--mqttpassword", help="Mqtt Password" )
	
	##Generic
	parser.add_argument("-s", "--discover", help="Discover devices",action="store_true",default=False)
	parser.add_argument("-d", "--debug", help="set logging level to debug",action="store_true",default=False)
	parser.add_argument("-v", "--version", help="Print Verions",action="store_true")
	parser.add_argument("-dir", "--data_dir", help="Data Folder -- Default to folder script is located", default=False)
	parser.add_argument("-c", "--config", help="Config file path -- Default to folder script is located + 'config.yml'", default=False)
	parser.add_argument("-l", "--logfile", help="Logfile path -- Default to logs folder script is located", default=False)
	parser.add_argument("-T", "--test",help="send test set temperature packet, for testing only",action="store_true",default=False)
			
	##Parse args
	args = parser.parse_args()
	
	##Set the base path, if set use it, otherwise default to running folder
	if args.data_dir:
		if os.path.exists(args.data_dir):
			data_dir = args.data_dir
		else:
			print ("Path Not found for Datadir: %s" % (args.data_dir))
			sys.exit()
	else:
		data_dir = os.path.dirname(os.path.realpath(__file__))
		
	##Config File
	if args.config:
		if os.path.exists(args.config):
			config_file_path = args.config
		else:
			print ("Config file not found: %s" % (args.config))
			sys.exit()
			
	else:
		if os.path.exists(data_dir+'/settings/config.yml'):
			config_file_path = data_dir+'/settings/config.yml'
		# elif  os.path.exists(data_dir+'\\settings\\config.yml'):
		# 	config_file_path = data_dir+'\\settings\\config.yml'
		else:
			# config_file_path = data_dir+'/config.yml'
			config_file_path = data_dir+'\\settings\config.yml'
		
	
	##LogFile
	if args.logfile:			
		log_file_path = args.logfile			 
	else:			
		log_file_path = os.path.dirname(os.path.realpath(__file__))+'/log/out.log'
		
	log_level = logging.DEBUG if args.debug else logging.INFO
	init_logging(log_level,log_file_path)
	
	logger.debug("%s v%s is starting up" % (__file__, softwareversion))
	logLevel = {0: 'NOTSET', 10: 'DEBUG', 20: 'INFO', 30: 'WARNING', 40: 'ERROR'}
	logger.debug('Loglevel set to ' + logLevel[logging.getLogger().getEffectiveLevel()])
	
	
	##Apply the config, then if arguments, override the config values with args
	config = read_config(config_file_path)

	
	
	##Print verions
	if args.version:
		print ("Monitor Version: %s, Class version:%s" % (softwareversion,ac_db_version.version))
		sys.exit()
	
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
		
	##mmmm.. this looks dodgy.. but i'm not python expert 			
	AC = AcToMqtt.AcToMqtt(config)
	##Just do a test
	if args.test:			
			AC.test(config)
			sys.exit()
	
	try:				
		##Make sure not already running		
		stop_if_already_running()		
	
		
		logging.info("Starting Monitor...")
		# Start and run the mainloop
		logger.debug("Starting mainloop, responding on only events")
	
		##Connect to Mqtt
		AC.connect_mqtt()				
		
		if config["self_discovery"]:	
			devices = AC.discover()
		else:
			devices = AC.make_device_objects(config['devices'])
		
		
		if args.dumphaconfig:
			AC.dump_homeassistant_config_from_devices(devices)			
			sys.exit()

		
		
			
		##Publish mqtt auto discovery if topic  set
		if config["mqtt_auto_discovery_topic"]:
			AC.publish_mqtt_auto_discovery(devices)			
	
		##One loop
		do_loop = True if config["daemon_mode"] else False			
				
		##Run main loop
		while do_loop :
			running = True
			
			AC.start(config,devices)
			 
			touch_pid_file()
		
		running = False
	except KeyboardInterrupt:
		logging.debug("User Keyboard interuped")	
		
	except Exception as e:								
		
		logger.debug(traceback.format_exc())			
		logger.error(e)
		
			
	finally:
		##cleanup
		stop()
			

				
if __name__ == "__main__":	
	start()
