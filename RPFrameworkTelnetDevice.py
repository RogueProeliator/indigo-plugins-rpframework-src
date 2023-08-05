#! /usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################################
# RPFrameworkTelnetDevice by RogueProeliator <adam.d.ashe@gmail.com>
# This class is a concrete implementation of the RPFrameworkDevice as a device which
# communicates via a telnet session
#######################################################################################

# region Python Imports
import re
import serial
import socket
import telnetlib
import time

try:
	import indigo
except:
	pass

from .RPFrameworkCommand import RPFrameworkCommand
from .RPFrameworkDevice  import RPFrameworkDevice
# endregion


class RPFrameworkTelnetDevice(RPFrameworkDevice):

	#######################################################################################
	# region Constants and Configuration Variables
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

	# endregion
	#######################################################################################
	
	#######################################################################################
	# region Construction and Destruction Methods
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor called once upon plugin class receiving a command to start device
	# communication. Defers to the base class for processing but initializes params
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, plugin, device, connection_type=CONNECTIONTYPE_TELNET):
		super().__init__(plugin, device)
		self.connection_type = connection_type

	# endregion
	#######################################################################################
		
	#######################################################################################
	# region Processing and Command Functions
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is designed to run in a concurrent thread and will continuously monitor
	# the commands queue for work to do.
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def concurrent_command_processing_thread(self, command_queue):
		try:
			# retrieve the keys and settings that will be used during the command processing
			# for this telnet device
			is_connected_state_key = self.host_plugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_ISCONNECTEDSTATEKEY, "")
			connection_state_key   = self.host_plugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_CONNECTIONSTATEKEY, "")
			self.host_plugin.logger.threaddebug(f"Read device state config... isConnected: {is_connected_state_key}; connectionState: {connection_state_key}")
			telnet_connection_info = self.get_device_address_info()
		
			# establish the telnet connection to the telnet-based which handles the primary
			# network remote operations
			self.host_plugin.logger.debug(f"Establishing connection to {telnet_connection_info[0]}")
			ip_connection = self.establish_device_connection(telnet_connection_info)
			if ip_connection is None:
				# this may return None instead of throwing an error for serial devices... throw the equivalent
				# error to allow the reconnection attempt
				raise EOFError()
			self.failed_connection_attempts = 0
			self.host_plugin.logger.debug("Connection established")
			
			# update the states on the server to show that we have established a connectionStateKey
			self.indigoDevice.setErrorStateOnServer(None)
			if is_connected_state_key != "":
				self.indigoDevice.updateStateOnServer(key=is_connected_state_key, value="true")
			if connection_state_key != "":
				self.indigoDevice.updateStateOnServer(key=connection_state_key, value="Connected")
				
			# retrieve any configuration information that may have been set up in the
			# plugin configuration and/or device configuration	
			line_ending_token                 = self.host_plugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_EOL, "\r")
			line_encoding                     = self.host_plugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_SENDENCODING, "ascii")
			command_response_timeout          = float(self.host_plugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_COMMANDREADTIMEOUT, "0.5"))
			
			telnet_connection_requires_login_dp = self.host_plugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_REQUIRES_LOGIN_DP, "")
			telnet_connection_requires_login    = (f"{self.indigoDevice.pluginProps.get(telnet_connection_requires_login_dp, 'False')}".lower() == "true")
			
			update_status_poller_property_name  = self.host_plugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_STATUSPOLL_INTERVALPROPERTY, "updateInterval")
			update_status_poller_interval       = int(self.indigoDevice.pluginProps.get(update_status_poller_property_name, "90"))
			update_status_poller_next_run       = None
			update_status_poller_action_id      = self.host_plugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_STATUSPOLL_ACTIONID, "")
			
			empty_queue_reduced_wait_cycles     = int(self.host_plugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_TELNETDEV_EMPTYQUEUE_SPEEDUPCYCLES, "200"))
			
			# begin the infinite loop which will run as long as the queue contains commands
			# and we have not received an explicit shutdown request
			continue_processing_commands  = True
			last_queued_command_completed = 0
			while continue_processing_commands:
				# process pending commands now...
				while not command_queue.empty():
					len_queue = command_queue.qsize()
					self.host_plugin.logger.threaddebug(f"Command queue has {len_queue} command(s) waiting")
					
					# the command name will identify what action should be taken... we will handle the known
					# commands and dispatch out to the device implementation, if necessary, to handle unknown
					# commands
					command = command_queue.get()
					if command.command_name == RPFrameworkCommand.CMD_INITIALIZE_CONNECTION:
						# specialized command to instantiate the thread/telnet connection
						# safely ignore this... just used to spin up the thread
						self.host_plugin.logger.threaddebug("Create connection command de-queued")
						
						# if the device supports polling for status, it may be initiated here now that
						# the connection has been established; no additional command will come through
						if not telnet_connection_requires_login:
							command_queue.put(RPFrameworkCommand(RPFrameworkCommand.CMD_UPDATE_DEVICE_STATUS_FULL, parent_action=update_status_poller_action_id))
						
					elif command.command_name == RPFrameworkCommand.CMD_TERMINATE_PROCESSING_THREAD:
						# a specialized command designed to stop the processing thread indigo
						# the event of a shutdown
						continue_processing_commands = False
						
					elif command.command_name == RPFrameworkCommand.CMD_PAUSE_PROCESSING:
						# the amount of time to sleep should be a float found in the
						# payload of the command
						try:
							pause_time = float(command.command_payload)
							self.host_plugin.logger.threaddebug(f"Initiating sleep of {pause_time} seconds from command.")
							time.sleep(pause_time)
						except:
							self.host_plugin.logger.error("Invalid pause time requested")
							
					elif command.command_name == RPFrameworkCommand.CMD_UPDATE_DEVICE_STATUS_FULL:
						# this command instructs the plugin to update the full status of the device (all statuses
						# that may be read from the device should be read)
						if update_status_poller_action_id != "":
							self.host_plugin.logger.debug("Executing full status update request...")
							self.host_plugin.execute_action(None, indigoActionId=update_status_poller_action_id, indigoDeviceId=self.indigoDevice.id, paramValues=None)
							if update_status_poller_interval > 0:
								update_status_poller_next_run = time.time() + update_status_poller_interval
						else:
							self.host_plugin.logger.threaddebug("Ignoring status update request, no action specified to update device status")
					
					elif command.command_name == RPFrameworkCommand.CMD_UPDATE_DEVICE_STATE:
						# this command is to update a device state with the payload (which may be an
						# eval command)
						new_state_info = re.match(r'^\{ds\:([a-zA-Z\d]+)\}\{(.+)\}$', command.command_payload, re.I)
						if new_state_info is None:
							self.host_plugin.logger.error(f"Invalid new device state specified")
						else:
							# the new device state may include an eval statement...
							update_state_name  = new_state_info.group(1)
							update_state_value = new_state_info.group(2)
							if update_state_value.startswith("eval"):
								update_state_value = eval(update_state_value.replace("eval:", ""))
							
							self.host_plugin.logger.debug(f"Updating state '{update_state_name}' to: '{update_state_value}'")
							self.indigoDevice.updateStateOnServer(key=update_state_name, value=update_state_value)
					
					elif command.command_name == RPFrameworkTelnetDevice.CMD_WRITE_TO_DEVICE:
						# this command initiates a write of data to the device
						self.host_plugin.logger.debug(f"Sending command: {command.command_payload}")
						write_command = command.command_payload + line_ending_token
						ip_connection.write(write_command.encode(line_encoding))
						self.host_plugin.logger.threaddebug("Write command completed.")
					
					else:
						# this is an unknown command; dispatch it to another routine which is
						# able to handle the commands (to be overridden for individual devices)
						self.handle_unmanaged_command_in_queue(ip_connection, command)
						
					# determine if any response has been received from the telnet device...
					response_text = f"{self.read_line(ip_connection, line_ending_token, command_response_timeout)}"
					if response_text != "":
						self.host_plugin.logger.threaddebug(f"Received: {response_text}")
						self.handle_device_response(response_text.replace(line_ending_token, ""), command)
						
					# if the command has a pause defined for after it is completed then we
					# should execute that pause now
					if command.post_command_pause > 0.0 and continue_processing_commands:
						self.host_plugin.logger.threaddebug(f"Post Command Pause: {command.post_command_pause}")
						time.sleep(command.post_command_pause)
					
					# complete the de-queuing of the command, allowing the next
					# command in queue to rise to the top
					command_queue.task_done()
					last_queued_command_completed = empty_queue_reduced_wait_cycles
					
				# continue with empty-queue processing unless the connection is shutting down...
				if continue_processing_commands:
					# check for any pending data coming IN from the telnet connection; note this is after the
					# command queue has been emptied, so it may be un-prompted incoming data
					response_text = f"{self.read_if_available(ip_connection, line_ending_token, command_response_timeout)}"
					if response_text != "":
						self.host_plugin.logger.threaddebug(f"Received w/o Command: {response_text}")
						self.handle_device_response(response_text.replace(line_ending_token, ""), None)
				
					# when the queue is empty, pause a bit on each iteration
					if last_queued_command_completed > 0:
						time.sleep(self.empty_queue_sleep_time / 2)
						last_queued_command_completed = last_queued_command_completed - 1
					else:
						time.sleep(self.empty_queue_sleep_time)
				
					# check to see if we need to issue an update...
					if update_status_poller_next_run is not None and time.time() > update_status_poller_next_run:
						command_queue.put(RPFrameworkCommand(RPFrameworkCommand.CMD_UPDATE_DEVICE_STATUS_FULL, parent_action=update_status_poller_action_id))
				
		# handle any exceptions that are thrown during execution of the plugin... note that this
		# should terminate the thread, but it may get spun back up again
		except SystemExit:
			# the system is shutting down communications... we can kill access now by allowing
			# the thread to expire
			pass
		except (socket.timeout, EOFError):
			# this is a standard timeout/disconnect
			if self.failed_connection_attempts == 0 or self.host_plugin.debug:
				self.host_plugin.logger.error(f"Connection timed out for device {self.indigoDevice.id}")
				
			if connection_state_key != "":
				self.indigoDevice.updateStateOnServer(key=connection_state_key, value="Unavailable")

				# prevent the finally clause from re-updating to disconnected
				connection_state_key = ""
				
			# this really is an error from the user's perspective, so set that state now
			self.indigoDevice.setErrorStateOnServer("Connection Error")
				
			# check to see if we should attempt reconnection
			self.schedule_reconnection_attempt()
		except socket.error as e:
			# this is a standard socket error, such as a reset... we can attempt to recover from this with
			# a scheduled reconnect
			if self.failed_connection_attempts == 0 or self.host_plugin.debug:
				self.host_plugin.logger.error(f"Connection failed for device {self.indigoDevice.id}: {e}")

			if connection_state_key != "":
				self.indigoDevice.updateStateOnServer(key=connection_state_key, value="Unavailable")
				connection_state_key = ""  # prevents the finally from re-updating to disconnected
				
			# this really is an error from the user's perspective, so set that state now
			self.indigoDevice.setErrorStateOnServer("Connection Error")
				
			# check to see if we should attempt a reconnect
			self.schedule_reconnection_attempt()
		except:
			self.indigoDevice.setErrorStateOnServer("Error")
			self.host_plugin.logger.exception("Error during background processing")
		finally:			
			# update the device's connection state to no longer connected...
			self.host_plugin.logger.debug("Closing connection to device")
			if is_connected_state_key != "":
				self.indigoDevice.updateStateOnServer(key=is_connected_state_key, value="false", clearErrorState=False)
			if connection_state_key != "":
				self.indigoDevice.updateStateOnServer(key=connection_state_key, value="Disconnected", clearErrorState=False)
			
			# execute the close of the connection now
			if ip_connection is not None:
				ip_connection.close()
				ip_connection = None

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine should return a tuple of information about the connection - in the
	# format of (ipAddress/HostName, portNumber)
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def get_device_address_info(self):
		if self.connection_type == RPFrameworkTelnetDevice.CONNECTIONTYPE_TELNET:
			return "", 0
		else:
			port_name     = f"{self.host_plugin.substitute_indigo_values(self.host_plugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_SERIALPORT_PORTNAME, ''), self, None)}"
			baud_rate     = int(self.host_plugin.substitute_indigo_values(self.host_plugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_SERIALPORT_BAUDRATE, '115200'), self, None))
			parity        = eval("serial." + self.host_plugin.substitute_indigo_values(self.host_plugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_SERIALPORT_PARITY, 'PARITY_NONE'), self, None))
			byte_size     = eval("serial." + self.host_plugin.substitute_indigo_values(self.host_plugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_SERIALPORT_BYTESIZE, 'EIGHTBITS'), self, None))
			stop_bits     = eval("serial." + self.host_plugin.substitute_indigo_values(self.host_plugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_SERIALPORT_STOPBITS, 'STOPBITS_ONE'), self, None))
			timeout       = float(self.host_plugin.substitute_indigo_values(self.host_plugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_SERIALPORT_READTIMEOUT, '1.0'), self, None))
			write_timeout = float(self.host_plugin.substitute_indigo_values(self.host_plugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_SERIALPORT_WRITETIMEOUT, '1.0'), self, None))
			return port_name, (baud_rate, parity, byte_size, stop_bits, timeout, write_timeout)
		
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine should return a tuple of information about the connection - in the
	# format of (ipAddress/HostName, portNumber)
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def establish_device_connection(self, connection_info):
		if self.connection_type == RPFrameworkTelnetDevice.CONNECTIONTYPE_TELNET:
			return telnetlib.Telnet(connection_info[0], connection_info[1])
		elif self.connection_type == RPFrameworkTelnetDevice.CONNECTIONTYPE_SERIAL:
			return self.host_plugin.openSerial(self.indigoDevice.name, connection_info[0], baudrate=connection_info[1][0], parity=connection_info[1][1], bytesize=connection_info[1][2], stopbits=connection_info[1][3], timeout=connection_info[1][4], writeTimeout=connection_info[1][5])
		elif self.connection_type == RPFrameworkTelnetDevice.CONNECTIONTYPE_SOCKET:
			command_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			command_socket.settimeout(int(self.host_plugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkTelnetDevice.GUI_CONFIG_SOCKET_CONNECTIONTIMEOUT, "5")))
			command_socket.connect((connection_info[0], connection_info[1]))
			command_socket.setblocking(0)
			return command_socket
		else:
			raise "Invalid connection type specified"
		
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine should be overridden in individual device classes whenever they must
	# handle custom commands that are not already defined
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def handle_unmanaged_command_in_queue(self, ip_connection, rp_command):
		pass
		
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine should attempt to read a line of text from the connection, using the
	# provided timeout as the upper-limit to wait
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def read_line(self, connection, line_ending_token, command_response_timeout):
		if self.connection_type == RPFrameworkTelnetDevice.CONNECTIONTYPE_TELNET:
			return connection.read_until(line_ending_token, command_response_timeout)
		elif self.connection_type == RPFrameworkTelnetDevice.CONNECTIONTYPE_SERIAL:
			line_read = ""
			line_ending_token_len = len(line_ending_token)
			while True:
				c = str(connection.read(1))
				if c:
					line_read += c
					if line_read[-line_ending_token_len:] == line_ending_token:
						break
				else:
					break
			return line_read
			
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine should attempt to read a line of text from the connection only if there
	# is an indication of waiting data (there is no waiting until a specified timeout)
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def read_if_available(self, connection, line_ending_token, command_response_timeout):
		if self.connection_type == RPFrameworkTelnetDevice.CONNECTIONTYPE_TELNET:
			return connection.read_eager()
		elif connection.inWaiting() > 0:
			return self.read_line(connection, line_ending_token, command_response_timeout)
		else:
			return ""
		
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will process any response from the device following the list of
	# response objects defined for this device type. For telnet this will always be
	# a text string
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def handle_device_response(self, response_text, rp_command):
		# loop through the list of response definitions defined in the (base) class
		# and determine if any match
		for rpResponse in self.host_plugin.get_device_response_definitions(self.indigoDevice.deviceTypeId):
			if rpResponse.is_response_match(response_text, rp_command, self, self.host_plugin):
				self.host_plugin.logger.threaddebug(f"Found response match: {rpResponse.response_id}")
				rpResponse.execute_effects(response_text, rp_command, self, self.host_plugin)

	# endregion
	#######################################################################################
		