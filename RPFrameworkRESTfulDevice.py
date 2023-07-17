#! /usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################################
# RPFrameworkRESTfulDevice by RogueProeliator <adam.d.ashe@gmail.com>
# This class is a concrete implementation of the RPFrameworkDevice as a device which
# communicates via a REST style HTTP connection.
#######################################################################################

# region Python imports
from __future__ import absolute_import
import re
import subprocess
import time

try:
	import indigo
except:
	from .RPFrameworkIndigoMock import RPFrameworkIndigoMock as indigo

import requests
from   requests.auth             import HTTPDigestAuth
from   .RPFrameworkCommand       import RPFrameworkCommand
from   .RPFrameworkDevice        import RPFrameworkDevice
from   .RPFrameworkNetworkingWOL import sendWakeOnLAN
from   .RPFrameworkUtils         import to_str
from   .RPFrameworkUtils         import to_unicode
# endregion


class RPFrameworkRESTfulDevice(RPFrameworkDevice):

	#######################################################################################
	# region Constants and Configuration Variables
	CMD_RESTFUL_PUT   = "RESTFUL_PUT"
	CMD_RESTFUL_GET   = "RESTFUL_GET"
	CMD_SOAP_REQUEST  = "SOAP_REQUEST"
	CMD_JSON_REQUEST  = "JSON_REQUEST"
	CMD_DOWNLOADFILE  = "DOWNLOAD_FILE"
	CMD_DOWNLOADIMAGE = "DOWNLOAD_IMAGE"

	GUI_CONFIG_RESTFULSTATUSPOLL_INTERVALPROPERTY = "updateStatusPollerIntervalProperty"
	GUI_CONFIG_RESTFULSTATUSPOLL_ACTIONID         = "updateStatusPollerActionId"
	GUI_CONFIG_RESTFULSTATUSPOLL_STARTUPDELAY     = "updateStatusPollerStartupDelay"

	GUI_CONFIG_RESTFULDEV_EMPTYQUEUE_SPEEDUPCYCLES = "emptyQueueReducedWaitCycles"

	# endregion
	#######################################################################################
	
	#######################################################################################
	# region Class Construction and Destruction Methods
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor called once upon plugin class receiving a command to start device
	# communication. Defers to the base class for processing but initializes params
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, plugin, device):
		super().__init__(plugin, device)

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
			self.host_plugin.logger.debug(f"Concurrent Processing Thread started for device {self.indigoDevice.id}")
		
			# obtain the IP or host address that will be used in connecting to the
			# RESTful service via a function call to allow overrides
			device_http_address = self.get_restful_device_address()
			if device_http_address is None:
				self.host_plugin.logger.error(f"No IP address specified for device {self.indigoDevice.id}; ending command processing thread.")
				return
			
			# retrieve any configuration information that may have been set up in the
			# plugin configuration and/or device configuration
			update_status_poller_property_name = self.host_plugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkRESTfulDevice.GUI_CONFIG_RESTFULSTATUSPOLL_INTERVALPROPERTY, "updateInterval")
			update_status_poller_interval      = int(self.indigoDevice.pluginProps.get(update_status_poller_property_name, "90"))
			update_status_poller_next_run      = None
			update_status_poller_action_id     = self.host_plugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkRESTfulDevice.GUI_CONFIG_RESTFULSTATUSPOLL_ACTIONID, "")
			empty_queue_reduced_wait_cycles    = int(self.host_plugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkRESTfulDevice.GUI_CONFIG_RESTFULDEV_EMPTYQUEUE_SPEEDUPCYCLES, "80"))
			
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
						# specialized command to instantiate the concurrent thread
						# safely ignore this... just used to spin up the thread
						self.host_plugin.logger.threaddebug(f"Create connection command de-queued")
						
						# if the device supports polling for status, it may be initiated here now; however, we should implement a pause to ensure that
						# devices are created properly (RESTFul devices may respond too fast since no connection need be established)
						status_update_startup_delay = float(self.host_plugin.get_gui_config_value(self.indigoDevice.deviceTypeId, RPFrameworkRESTfulDevice.GUI_CONFIG_RESTFULSTATUSPOLL_STARTUPDELAY, "3"))
						if status_update_startup_delay > 0.0:
							command_queue.put(RPFrameworkCommand(RPFrameworkCommand.CMD_PAUSE_PROCESSING, command_payload=str(status_update_startup_delay)))
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
							self.host_plugin.logger.warning(f"Invalid pause time requested")
							
					elif command.command_name == RPFrameworkCommand.CMD_UPDATE_DEVICE_STATUS_FULL:
						# this command instructs the plugin to update the full status of the device (all statuses
						# that may be read from the device should be read)
						if update_status_poller_action_id != "":
							self.host_plugin.logger.debug("Executing full status update request...")
							self.host_plugin.execute_action(None, indigoActionId=update_status_poller_action_id, indigoDeviceId=self.indigoDevice.id, paramValues=None)
							update_status_poller_next_run = time.time() + update_status_poller_interval
						else:
							self.host_plugin.logger.threaddebug("Ignoring status update request, no action specified to update device status")
							
					elif command.command_name == RPFrameworkCommand.CMD_NETWORKING_WOL_REQUEST:
						# this is a request to send a Wake-On-LAN request to a network-enabled device
						# the command payload should be the MAC address of the device to wake up
						try:
							sendWakeOnLAN(command.command_payload)
						except:
							self.host_plugin.logger.error("Failed to send Wake-on-LAN packet")
						
					elif command.command_name == RPFrameworkRESTfulDevice.CMD_RESTFUL_GET or command.command_name == RPFrameworkRESTfulDevice.CMD_RESTFUL_PUT or command.command_name == RPFrameworkRESTfulDevice.CMD_DOWNLOADFILE or command.command_name == RPFrameworkRESTfulDevice.CMD_DOWNLOADIMAGE:
						try:
							self.host_plugin.logger.debug(f"Processing GET operation: {command.command_payload}")
							
							# gather all the parameters from the command payload
							# the payload should have the following format:
							# [0] => request method (http|https|etc.)
							# [1] => path for the GET operation
							# [2] => authentication type: none|basic|digest
							# [3] => username
							# [4] => password
							#
							# CMD_DOWNLOADFILE or CMD_DOWNLOADIMAGE
							# [5] => download filename/path
							# [6] => image resize width
							# [7] => image resize height
							#
							# CMD_RESTFUL_PUT
							# [5] => data to post as the body (if any, may be blank)
							command_payload_list = command.get_payload_as_list()
							full_get_url = f"{command_payload_list[0]}://{device_http_address[0]}:{device_http_address[1]}{command_payload_list[1]}"
							self.host_plugin.logger.threaddebug(f"Full URL for GET: {full_get_url}")
							
							custom_headers = {}
							self.add_custom_http_headers(custom_headers)
							
							authentication_param = None
							authentication_type  = "none"
							username = ""
							password = ""
							if len(command_payload_list) >= 3:
								authentication_type = command_payload_list[2]
							if len(command_payload_list) >= 4:
								username = command_payload_list[3]
							if len(command_payload_list) >= 5:
								password = command_payload_list[4]
							if authentication_type != "none" and username != "":
								self.host_plugin.logger.threaddebug(f"Using login credentials... Username=> {username}; Password=>{len(password)} characters long")
								if authentication_type.lower() == "digest":
									self.host_plugin.logger.threaddebug("Enabling digest authentication")
									authentication_param = HTTPDigestAuth(username, password)
								else:
									authentication_param = (username, password)
							
							# execute the URL fetching depending upon the method requested
							if command.command_name == RPFrameworkRESTfulDevice.CMD_RESTFUL_GET or command.command_name == RPFrameworkRESTfulDevice.CMD_DOWNLOADFILE or command.command_name == RPFrameworkRESTfulDevice.CMD_DOWNLOADIMAGE:
								response_obj = requests.get(full_get_url, auth=authentication_param, headers=custom_headers, verify=False)
							elif command.command_name == RPFrameworkRESTfulDevice.CMD_RESTFUL_PUT:
								data_to_post = None
								if len(command_payload_list) >= 6:
									data_to_post = command_payload_list[5]
								response_obj = requests.post(full_get_url, auth=authentication_param, headers=custom_headers, verify=False, data=data_to_post)
								
							# if the network command failed then allow the error processor to handle the issue
							if response_obj.status_code == 200:
								# the response handling will depend upon the type of command... binary returns must be
								# handled separately from (expected) text-based ones
								if command.command_name == RPFrameworkRESTfulDevice.CMD_DOWNLOADFILE or command.command_name == RPFrameworkRESTfulDevice.CMD_DOWNLOADIMAGE:
									# this is a binary return that should be saved to the file system without modification
									if len(command_payload_list) >= 6:
										save_location = command_payload_list[5]
									
										# execute the actual save from the binary response stream
										try:
											local_file = open(to_str(save_location), "wb")
											local_file.write(response_obj.content)
											self.host_plugin.logger.threaddebug(f"Command Response: [{response_obj.status_code}] -=- binary data written to {save_location}-=-")
										
											if command.command_name == RPFrameworkRESTfulDevice.CMD_DOWNLOADIMAGE:
												image_resize_width  = 0
												image_resize_height = 0
												if len(command.command_payload) >= 7:
													image_resize_width = int(command.command_payload[6])
												if len(command.command_payload) >= 8:
													image_resize_height = int(command.command_payload[7])
								
												resize_command_line = ""
												if image_resize_width > 0 and image_resize_height > 0:
													# we have a specific size as a target...
													resize_command_line = f"sips -z {image_resize_height} {image_resize_width} {save_location}"
												elif image_resize_width > 0:
													# we have a maximum size measurement
													resize_command_line = f"sips -Z {image_resize_width} {save_location}"
									
												# if a command line has been formed, fire that off now...
												if resize_command_line == "":
													self.host_plugin.logger.debug(f"No image size specified for {save_location}; skipping resize.")
												else:
													self.host_plugin.logger.threaddebug(f"Executing resize via command line '{resize_command_line}'")
													try:
														subprocess.Popen(resize_command_line, shell=True)
														self.host_plugin.logger.debug(f"{save_location} resized via sip shell command")
													except:
														self.host_plugin.logger.error("Error resizing image via sips")
														
											# we have completed the download and processing successfully... allow the
											# device (or its descendants) to process successful operations
											self.notify_successful_download(command, save_location)
										finally:
											if local_file is not None:
												local_file.close()
									else:
										self.host_plugin.logger.error("Unable to complete download action - no filename specified")
								else:
									# handle this return as a text-based return
									self.host_plugin.logger.threaddebug(f"Command Response: [{response_obj.status_code}] {response_obj.text}")
									self.host_plugin.logger.threaddebug(f"{command.command_name} command completed; beginning response processing")
									self.handle_device_text_response(response_obj, command)
									self.host_plugin.logger.threaddebug(f"{command.command_name} command response processing completed")
									
							elif response_obj.status_code == 401:
								self.handle_restful_error(command, "401 - Unauthorized", response_obj)
							
							else:
								self.handle_restful_error(command, str(response_obj.status_code), response_obj)

						except Exception as e:
							# the response value really should not be defined here as it bailed without
							# catching any of our response error conditions
							self.handle_restful_error(command, e, None)
						
					elif command.command_name == RPFrameworkRESTfulDevice.CMD_SOAP_REQUEST or command.command_name == RPFrameworkRESTfulDevice.CMD_JSON_REQUEST:
						response_obj = None
						try:
							# this is to post a SOAP request to a web service... this will be similar to a restful put request
							# but will contain a body payload
							self.host_plugin.logger.threaddebug(f"Received SOAP/JSON command request: {command.command_payload}")
							soap_payload_parser = re.compile(r"^\s*([^\n]+)\n\s*([^\n]+)\n(.*)$", re.DOTALL)
							soap_payload_data  = soap_payload_parser.match(command.command_payload)
							soap_path          = soap_payload_data.group(1).strip()
							soap_action        = soap_payload_data.group(2).strip()
							soap_body          = soap_payload_data.group(3).strip()
							full_get_url       = f"http://{device_http_address[0]}:{device_http_address[1]}{soap_path}"
							self.host_plugin.logger.debug(f"Processing SOAP/JSON operation to {full_get_url}")

							custom_headers = {}
							self.add_custom_http_headers(custom_headers)
							if command.command_name == RPFrameworkRESTfulDevice.CMD_SOAP_REQUEST:
								custom_headers["Content-type"] = "text/xml; charset=\"UTF-8\""
								custom_headers["SOAPAction"]   = to_str(soap_action)
							else:
								custom_headers["Content-type"] = "application/json"
							
							# execute the URL post to the web service
							self.host_plugin.logger.threaddebug(f"Sending SOAP/JSON request:\n{soap_body}")
							self.host_plugin.logger.threaddebug(f"Using headers: \n{custom_headers}")
							response_obj = requests.post(full_get_url, headers=custom_headers, verify=False, data=to_str(soap_body))
							
							if response_obj.status_code == 200:
								# handle this return as a text-based return
								self.host_plugin.logger.threaddebug(f"Command Response: [{response_obj.status_code}] {response_obj.text}")
								self.host_plugin.logger.threaddebug(f"{command.command_name} command completed; beginning response processing")
								self.handle_device_text_response(response_obj, command)
								self.host_plugin.logger.threaddebug(f"{command.command_name} command response processing completed")
								
							else:
								self.host_plugin.logger.threaddebug("Command Response was not HTTP OK, handling RESTful error")
								self.handle_restful_error(command, str(response_obj.status_code), response_obj)

						except Exception as e:
							self.handle_restful_error(command, e, response_obj)
					
					else:
						# this is an unknown command; dispatch it to another routine which is
						# able to handle the commands (to be overridden for individual devices)
						self.handle_unmanaged_command_in_queue(device_http_address, command)
					
					# if the command has a pause defined for after it is completed then we
					# should execute that pause now
					if command.post_command_pause > 0.0 and continue_processing_commands == True:
						self.host_plugin.logger.threaddebug(f"Post Command Pause: {command.post_command_pause}")
						time.sleep(command.post_command_pause)
					
					# complete the dequeuing of the command, allowing the next
					# command in queue to rise to the top
					command_queue.task_done()
					last_queued_command_completed = empty_queue_reduced_wait_cycles
				
				# when the queue is empty, pause a bit on each iteration
				if continue_processing_commands:
					# if we have just completed a command recently, half the amount of
					# wait time, assuming that a subsequent command could be forthcoming
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
			pass
		except Exception:
			self.host_plugin.logger.exception("Exception in background processing")
		except:
			self.host_plugin.logger.exception("Exception in background processing")
		finally:
			self.host_plugin.logger.debug("Command thread ending processing")
		
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine should return the HTTP address that will be used to connect to the
	# RESTful device. It may connect via IP address or a host name
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def get_restful_device_address(self):
		return None
	
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine should be overridden in individual device classes whenever they must
	# handle custom commands that are not already defined
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def handle_unmanaged_command_in_queue(self, device_http_address, rp_command):
		pass
		
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will be called prior to any network operation to allow the addition
	# of custom headers to the request (does not include file download)
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def add_custom_http_headers(self, http_request):
		pass
		
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will process any response from the device following the list of
	# response objects defined for this device type. For telnet this will always be
	# a text string
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def handle_device_text_response(self, response_obj, rp_command):
		# loop through the list of response definitions defined in the (base) class
		# and determine if any match
		response_text = response_obj.text
		for rpResponse in self.host_plugin.get_device_response_definitions(self.indigoDevice.deviceTypeId):
			if rpResponse.is_response_match(response_text, rp_command, self, self.host_plugin):
				self.host_plugin.logger.threaddebug(f"Found response match: {rpResponse.response_id}")
				rpResponse.execute_effects(response_text, rp_command, self, self.host_plugin)
	
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will handle an error as thrown by the REST call... it allows 
	# descendant classes to do their own processing
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def handle_restful_error(self, rp_command, err, response=None):
		if rp_command.command_name == RPFrameworkRESTfulDevice.CMD_RESTFUL_PUT or rp_command.command_name == RPFrameworkRESTfulDevice.CMD_RESTFUL_GET:
			self.host_plugin.logger.exception(f"An error occurred executing the GET/PUT request (Device: {self.indigoDevice.id}): {err}")
		else:
			self.host_plugin.logger.exception(f"An error occurred processing the SOAP/JSON POST request: (Device: {self.indigoDevice.id}): {err}")
			
		if response is not None and response.text is not None:
			self.host_plugin.logger.debug(to_unicode(response.text))
			
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will handle notification to the device whenever a file was successfully
	# downloaded via a DOWNLOAD_FILE or DOWNLOAD_IMAGE command
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def notify_successful_download(self, rp_command, output_file_name):
		pass
	
	# endregion
	#######################################################################################
	