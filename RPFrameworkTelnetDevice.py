#! /usr/bin/env python
# -*- coding: utf-8 -*-
#/////////////////////////////////////////////////////////////////////////////////////////
# RPFrameworkTelnetDevice by RogueProeliator <adam.d.ashe@gmail.com>
# 	This class is a concrete implementation of the RPFrameworkDevice as a device which
#	communicates via a telnet session
#/////////////////////////////////////////////////////////////////////////////////////////

#/////////////////////////////////////////////////////////////////////////////////////////
#region Python Imports
import re
import socket
import telnetlib
import time

try:
	import indigo
except:
	pass

from .RPFrameworkCommand import RPFrameworkCommand
from .RPFrameworkDevice  import RPFrameworkDevice
from .RPFrameworkUtils   import to_unicode

#endregion
#/////////////////////////////////////////////////////////////////////////////////////////


#/////////////////////////////////////////////////////////////////////////////////////////
# RPFrameworkTelnetDevice
#	This class is a concrete implementation of the RPFrameworkDevice as a device which
#	communicates via a telnet session
#/////////////////////////////////////////////////////////////////////////////////////////
class RPFrameworkTelnetDevice(RPFrameworkDevice):

	#/////////////////////////////////////////////////////////////////////////////////////////
	#region Constants and Configuration Variables
	CONNECTIONTYPE_TELNET = 1
	CONNECTIONTYPE_SERIAL = 2
	CONNECTIONTYPE_SOCKET = 3

	GUI_CONFIG_COMMANDREADTIMEOUT          = "commandReadTimeout"

	GUI_CONFIG_ISCONNECTEDSTATEKEY         = "telnetConnectionDeviceStateBoolean"
	GUI_CONFIG_CONNECTIONSTATEKEY          = "telnetConnectionDeviceStateName"
	GUI_CONFIG_EOL                         = "telnetConnectionEOLString"
	GUI_CONFIG_SENDENCODING                = "telnetConnectionStringEncoding"
	GUI_CONFIG_REQUIRES_LOGIN_DP           = "telnetConnectionRequiresLoginProperty"
	GUI_CONFIG_STATUSPOLL_INTERVALPROPERTY = "updateStatusPollerIntervalProperty"
	GUI_CONFIG_STATUSPOLL_ACTIONID         = "updateStatusPollerActionId"

	GUI_CONFIG_SERIALPORT_PORTNAME         = "serialPortName"
	GUI_CONFIG_SERIALPORT_BAUDRATE         = "serialPortBaud"
	GUI_CONFIG_SERIALPORT_PARITY           = "serialPortParity"
	GUI_CONFIG_SERIALPORT_BYTESIZE         = "serialPortByteSize"
	GUI_CONFIG_SERIALPORT_STOPBITS         = "serialPortStopBits"
	GUI_CONFIG_SERIALPORT_READTIMEOUT      = "telnetDeviceReadTimeout"
	GUI_CONFIG_SERIALPORT_WRITETIMEOUT     = "telnetDeviceWriteTimeout"

	GUI_CONFIG_SOCKET_CONNECTIONTIMEOUT    = "socketConnectionTimeout"

	GUI_CONFIG_TELNETDEV_EMPTYQUEUE_SPEEDUPCYCLES = "emptyQueueReducedWaitCycles"

	CMD_WRITE_TO_DEVICE = "writeToTelnetConn"

	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////////
	
	#/////////////////////////////////////////////////////////////////////////////////////
	#region Construction and Destruction Methods
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor called once upon plugin class receiving a command to start device
	# communication. Defers to the base class for processing but initializes params
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, plugin, device, connectionType=CONNECTIONTYPE_TELNET):
		super().__init__(plugin, device)
		self.connectionType = connectionType

	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////
		
	#/////////////////////////////////////////////////////////////////////////////////////
	#region Processing and Command Functions
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is designed to run in a concurrent thread and will continuously monitor
	# the commands queue for work to do.
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def concurrentCommandProcessingThread(self, commandQueue):
		try:
			# retrieve the keys and settings that will be used during the command processing
			# for this telnet device
			is_connected_state_key = self.hostPlugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_ISCONNECTEDSTATEKEY, "")
			connection_state_key   = self.hostPlugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_CONNECTIONSTATEKEY, "")
			self.hostPlugin.logger.threaddebug(f"Read device state config... isConnected: {is_connected_state_key}; connectionState: {connection_state_key}")
			telnet_connection_info = self.getDeviceAddressInfo()
		
			# establish the telnet connection to the telnet-based which handles the primary
			# network remote operations
			self.hostPlugin.logger.debug(f"Establishing connection to {telnet_connection_info[0]}")
			ip_connection                 = self.establishDeviceConnection(telnet_connection_info)
			self.failedConnectionAttempts = 0
			self.hostPlugin.logger.debug(f"Connection established")
			
			# update the states on the server to show that we have established a connectionStateKey
			self.indigoDevice.setErrorStateOnServer(None)
			if is_connected_state_key != "":
				self.indigoDevice.updateStateOnServer(key=is_connected_state_key, value="true")
			if connection_state_key != "":
				self.indigoDevice.updateStateOnServer(key=connection_state_key, value="Connected")
				
			# retrieve any configuration information that may have been setup in the
			# plugin configuration and/or device configuration	
			line_ending_token                 = self.hostPlugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_EOL, "\r")
			line_encoding                     = self.hostPlugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_SENDENCODING, "ascii")
			command_response_timeout          = float(self.hostPlugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_COMMANDREADTIMEOUT, "0.5"))
			
			telnet_connection_requires_login_dp = self.hostPlugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_REQUIRES_LOGIN_DP, "")
			telnet_connection_requires_login    = (to_unicode(self.indigoDevice.pluginProps.get(telnet_connection_requires_login_dp, "False")).lower() == "true")
			
			update_status_poller_property_name  = self.hostPlugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_STATUSPOLL_INTERVALPROPERTY, "updateInterval")
			update_status_poller_interval       = int(self.indigoDevice.pluginProps.get(update_status_poller_property_name, "90"))
			update_status_poller_next_run       = None
			update_status_poller_action_id      = self.hostPlugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_STATUSPOLL_ACTIONID, "")
			
			empty_queue_reduced_wait_cycles     = int(self.hostPlugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_TELNETDEV_EMPTYQUEUE_SPEEDUPCYCLES, "200"))
			
			# begin the infinite loop which will run as long as the queue contains commands
			# and we have not received an explicit shutdown request
			continue_processing_commands  = True
			last_queued_command_completed = 0
			while continue_processing_commands:
				# process pending commands now...
				while not commandQueue.empty():
					len_queue = commandQueue.qsize()
					self.hostPlugin.logger.threaddebug(f"Command queue has {len_queue} command(s) waiting")
					
					# the command name will identify what action should be taken... we will handle the known
					# commands and dispatch out to the device implementation, if necessary, to handle unknown
					# commands
					command = commandQueue.get()
					if command.commandName == RPFrameworkCommand.CMD_INITIALIZE_CONNECTION:
						# specialized command to instantiate the thread/telnet connection
						# safely ignore this... just used to spin up the thread
						self.hostPlugin.logger.threaddebug(u'Create connection command de-queued')
						
						# if the device supports polling for status, it may be initiated here now that
						# the connection has been established; no additional command will come through
						if not telnet_connection_requires_login:
							commandQueue.put(RPFrameworkCommand.RPFrameworkCommand(RPFrameworkCommand.CMD_UPDATE_DEVICE_STATUS_FULL, parentAction=update_status_poller_action_id))
						
					elif command.commandName == RPFrameworkCommand.CMD_TERMINATE_PROCESSING_THREAD:
						# a specialized command designed to stop the processing thread indigo
						# the event of a shutdown
						continue_processing_commands = False
						
					elif command.commandName == RPFrameworkCommand.CMD_PAUSE_PROCESSING:
						# the amount of time to sleep should be a float found in the
						# payload of the command
						try:
							pause_time = float(command.commandPayload)
							self.hostPlugin.logger.threaddebug(f"Initiating sleep of {pause_time} seconds from command.")
							time.sleep(pause_time)
						except:
							self.hostPlugin.logger.error("Invalid pause time requested")
							
					elif command.commandName == RPFrameworkCommand.CMD_UPDATE_DEVICE_STATUS_FULL:
						# this command instructs the plugin to update the full status of the device (all statuses
						# that may be read from the device should be read)
						if update_status_poller_action_id != "":
							self.hostPlugin.logger.debug("Executing full status update request...")
							self.hostPlugin.execute_action(None, indigoActionId=update_status_poller_action_id, indigoDeviceId=self.indigoDevice.id, paramValues=None)
							if update_status_poller_interval > 0:
								update_status_poller_next_run = time.time() + update_status_poller_interval
						else:
							self.hostPlugin.logger.threaddebug("Ignoring status update request, no action specified to update device status")
					
					elif command.commandName == RPFrameworkCommand.CMD_UPDATE_DEVICE_STATE:
						# this command is to update a device state with the payload (which may be an
						# eval command)
						new_state_info = re.match(r'^\{ds\:([a-zA-Z\d]+)\}\{(.+)\}$', command.commandPayload, re.I)
						if new_state_info is None:
							self.hostPlugin.logger.error(f"Invalid new device state specified")
						else:
							# the new device state may include an eval statement...
							update_state_name  = new_state_info.group(1)
							update_state_value = new_state_info.group(2)
							if update_state_value.startswith(u'eval'):
								update_state_value = eval(update_state_value.replace("eval:", ""))
							
							self.hostPlugin.logger.debug(f"Updating state '{update_state_name}' to: '{update_state_value}'")
							self.indigoDevice.updateStateOnServer(key=update_state_name, value=update_state_value)
					
					elif command.commandName == RPFrameworkTelnetDevice.CMD_WRITE_TO_DEVICE:
						# this command initiates a write of data to the device
						self.hostPlugin.logger.debug(f"Sending command: {command.commandPayload}")
						write_command = command.commandPayload + line_ending_token
						ip_connection.write(write_command.encode(line_encoding))
						self.hostPlugin.logger.threaddebug("Write command completed.")
					
					else:
						# this is an unknown command; dispatch it to another routine which is
						# able to handle the commands (to be overridden for individual devices)
						self.handleUnmanagedCommandInQueue(ip_connection, command)
						
					# determine if any response has been received from the telnet device...
					response_text = to_unicode(self.readLine(ip_connection, line_ending_token, command_response_timeout))
					if response_text != "":
						self.hostPlugin.logger.threaddebug(f"Received: {response_text}")
						self.handleDeviceResponse(response_text.replace(line_ending_token, ""), command)
						
					# if the command has a pause defined for after it is completed then we
					# should execute that pause now
					if command.postCommandPause > 0.0 and continue_processing_commands:
						self.hostPlugin.logger.threaddebug(f"Post Command Pause: {command.postCommandPause}")
						time.sleep(command.postCommandPause)
					
					# complete the de-queuing of the command, allowing the next
					# command in queue to rise to the top
					commandQueue.task_done()
					last_queued_command_completed = empty_queue_reduced_wait_cycles
					
				# continue with empty-queue processing unless the connection is shutting down...
				if continue_processing_commands:
					# check for any pending data coming IN from the telnet connection; note this is after the
					# command queue has been emptied so it may be un-prompted incoming data
					response_text = to_unicode(self.readIfAvailable(ip_connection, line_ending_token, command_response_timeout))
					if response_text != "":
						self.hostPlugin.logger.threaddebug(f"Received w/o Command: {response_text}")
						self.handleDeviceResponse(response_text.replace(line_ending_token, ""), None)
				
					# when the queue is empty, pause a bit on each iteration
					if last_queued_command_completed > 0:
						time.sleep(self.emptyQueueThreadSleepTime/2)
						last_queued_command_completed = last_queued_command_completed - 1
					else:
						time.sleep(self.emptyQueueThreadSleepTime)
				
					# check to see if we need to issue an update...
					if update_status_poller_next_run is not None and time.time() > update_status_poller_next_run:
						commandQueue.put(RPFrameworkCommand.RPFrameworkCommand(RPFrameworkCommand.CMD_UPDATE_DEVICE_STATUS_FULL, parentAction=update_status_poller_action_id))
				
		# handle any exceptions that are thrown during execution of the plugin... note that this
		# should terminate the thread, but it may get spun back up again
		except SystemExit:
			# the system is shutting down communications... we can kill access now by allowing
			# the thread to expire
			pass
		except (socket.timeout, EOFError):
			# this is a standard timeout/disconnect
			if self.failedConnectionAttempts == 0 or self.hostPlugin.debug:
				self.hostPlugin.logger.error(f"Connection timed out for device {self.indigoDevice.id}")
				
			if connection_state_key != "":
				self.indigoDevice.updateStateOnServer(key=connection_state_key, value="Unavailable")
				connection_state_key = ""  # prevents the finally from re-updating to disconnected
				
			# this really is an error from the user's perspective, so set that state now
			self.indigoDevice.setErrorStateOnServer("Connection Error")
				
			# check to see if we should attempt reconnection
			self.scheduleReconnectionAttempt()
		except socket.error as e:
			# this is a standard socket error, such as a reset... we can attempt to recover from this with
			# a scheduled reconnect
			if self.failedConnectionAttempts == 0 or self.hostPlugin.debug:
				self.hostPlugin.logg.error(f"Connection failed for device {self.indigoDevice.id}: {e}")

			if connection_state_key != "":
				self.indigoDevice.updateStateOnServer(key=connection_state_key, value="Unavailable")
				connection_state_key = ""  # prevents the finally from re-updating to disconnected
				
			# this really is an error from the user's perspective, so set that state now
			self.indigoDevice.setErrorStateOnServer("Connection Error")
				
			# check to see if we should attempt a reconnect
			self.scheduleReconnectionAttempt()
		except:
			self.indigoDevice.setErrorStateOnServer("Error")
			self.hostPlugin.logger.exception("Error during background processing")
		finally:			
			# update the device's connection state to no longer connected...
			self.hostPlugin.logger.debug("Closing connection to device")
			if is_connected_state_key != "":
				self.indigoDevice.updateStateOnServer(key=is_connected_state_key, value="false", clearErrorState=False)
			if connection_state_key != "":
				self.indigoDevice.updateStateOnServer(key=connection_state_key, value="Disconnected", clearErrorState=False)
			
			# execute the close of the connection now
			if ip_connection is not None:
				ip_connection.close()
				ip_connection = None

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine should return a tuple of information about the connection - in the
	# format of (ipAddress/HostName, portNumber)
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getDeviceAddressInfo(self):
		if self.connectionType == RPFrameworkTelnetDevice.CONNECTIONTYPE_TELNET:
			return u'', 0
		else:
			port_name     = to_unicode(self.hostPlugin.substitute_indigo_values(self.hostPlugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_SERIALPORT_PORTNAME, ""), self, None))
			baud_rate     = int(self.hostPlugin.substitute_indigo_values(self.hostPlugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_SERIALPORT_BAUDRATE, "115200"), self, None))
			parity        = eval("serial." + self.hostPlugin.substitute_indigo_values(self.hostPlugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_SERIALPORT_PARITY, "PARITY_NONE"), self, None))
			byte_size     = eval("serial." + self.hostPlugin.substitute_indigo_values(self.hostPlugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_SERIALPORT_BYTESIZE, "EIGHTBITS"), self, None))
			stop_bits     = eval("serial." + self.hostPlugin.substitute_indigo_values(self.hostPlugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_SERIALPORT_STOPBITS, "STOPBITS_ONE"), self, None))
			timeout       = float(self.hostPlugin.substitute_indigo_values(self.hostPlugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_SERIALPORT_READTIMEOUT, "1.0"), self, None))
			write_timeout = float(self.hostPlugin.substitute_indigo_values(self.hostPlugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_SERIALPORT_WRITETIMEOUT, "1.0"), self, None))
			return port_name, (baud_rate, parity, byte_size, stop_bits, timeout, write_timeout)
		
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine should return a tuple of information about the connection - in the
	# format of (ipAddress/HostName, portNumber)
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def establishDeviceConnection(self, connectionInfo):
		if self.connectionType == RPFrameworkTelnetDevice.CONNECTIONTYPE_TELNET:
			return telnetlib.Telnet(connectionInfo[0], connectionInfo[1])
		elif self.connectionType == RPFrameworkTelnetDevice.CONNECTIONTYPE_SERIAL:
			return self.hostPlugin.openSerial(self.indigoDevice.name, connectionInfo[0], baudrate=connectionInfo[1][0], parity=connectionInfo[1][1], bytesize=connectionInfo[1][2], stopbits=connectionInfo[1][3], timeout=connectionInfo[1][4], writeTimeout=connectionInfo[1][5])
		elif self.connectionType == RPFrameworkTelnetDevice.CONNECTIONTYPE_SOCKET:
			command_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			command_socket.settimeout(int(self.hostPlugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_SOCKET_CONNECTIONTIMEOUT, "5")))
			command_socket.connect((connectionInfo[0], connectionInfo[1]))
			command_socket.setblocking(0)
			return command_socket
		else:
			raise "Invalid connection type specified"
		
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine should be overridden in individual device classes whenever they must
	# handle custom commands that are not already defined
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def handleUnmanagedCommandInQueue(self, ipConnection, rpCommand):
		pass
		
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine should attempt to read a line of text from the connection, using the
	# provided timeout as the upper-limit to wait
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def readLine(self, connection, lineEndingToken, commandResponseTimeout):
		if self.connectionType == RPFrameworkTelnetDevice.CONNECTIONTYPE_TELNET:
			return to_unicode(connection.read_until(lineEndingToken, commandResponseTimeout))
		elif self.connectionType == RPFrameworkTelnetDevice.CONNECTIONTYPE_SERIAL:
			# Python 2.6 changed the readline signature to not include a line-ending token,
			# so we have to "manually" re-create that here
			#return connection.readline(None)
			line_read = ""
			line_ending_token_len = len(lineEndingToken)
			while True:
				c = connection.read(1)
				if c:
					line_read += c
					if line_read[-line_ending_token_len:] == lineEndingToken:
						break
				else:
					break
			return to_unicode(line_read)
			
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine should attempt to read a line of text from the connection only if there
	# is an indication of waiting data (there is no waiting until a specified timeout)
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def readIfAvailable(self, connection, lineEndingToken, commandResponseTimeout):
		if self.connectionType == RPFrameworkTelnetDevice.CONNECTIONTYPE_TELNET:
			return to_unicode(connection.read_eager())
		elif connection.inWaiting() > 0:
			return to_unicode(self.readLine(connection, lineEndingToken, commandResponseTimeout))
		else:
			return ""
		
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will process any response from the device following the list of
	# response objects defined for this device type. For telnet this will always be
	# a text string
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def handleDeviceResponse(self, responseText, rpCommand):
		# loop through the list of response definitions defined in the (base) class
		# and determine if any match
		for rpResponse in self.hostPlugin.get_device_response_definitions(self.indigoDevice.deviceTypeId):
			if rpResponse.isResponseMatch(responseText, rpCommand, self, self.hostPlugin):
				self.hostPlugin.logger.threaddebug(f"Found response match: {rpResponse.responseId}")
				rpResponse.executeEffects(responseText, rpCommand, self, self.hostPlugin)

	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////	
		