#! /usr/bin/env python
# -*- coding: utf-8 -*-
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# RPFrameworkRESTfulDevice by RogueProeliator <adam.d.ashe@gmail.com>
# 	This class is a concrete implementation of the RPFrameworkDevice as a device which
#	communicates via a REST style HTTP connection.
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////

#/////////////////////////////////////////////////////////////////////////////////////////
#region Python imports
from __future__ import absolute_import
import re
import subprocess
import sys
import time

if sys.version_info > (3,):
	import http.client as httplib
	import queue as Queue
else:
	import httplib
	import Queue

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

#endregion
#/////////////////////////////////////////////////////////////////////////////////////////

#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# RPFrameworkRESTfulDevice
#	This class is a concrete implementation of the RPFrameworkDevice as a device which
#	communicates via a REST style HTTP connection.
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
class RPFrameworkRESTfulDevice(RPFrameworkDevice):

	#/////////////////////////////////////////////////////////////////////////////////////////
	#region Constants and Configuration Variables
	CMD_RESTFUL_PUT   = u'RESTFUL_PUT'
	CMD_RESTFUL_GET   = u'RESTFUL_GET'
	CMD_SOAP_REQUEST  = u'SOAP_REQUEST'
	CMD_JSON_REQUEST  = u'JSON_REQUEST'
	CMD_DOWNLOADFILE  = u'DOWNLOAD_FILE'
	CMD_DOWNLOADIMAGE = u'DOWNLOAD_IMAGE'

	GUI_CONFIG_RESTFULSTATUSPOLL_INTERVALPROPERTY = u'updateStatusPollerIntervalProperty'
	GUI_CONFIG_RESTFULSTATUSPOLL_ACTIONID         = u'updateStatusPollerActionId'
	GUI_CONFIG_RESTFULSTATUSPOLL_STARTUPDELAY     = u'updateStatusPollerStartupDelay'

	GUI_CONFIG_RESTFULDEV_EMPTYQUEUE_SPEEDUPCYCLES = u'emptyQueueReducedWaitCycles'

	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////////
	
	#/////////////////////////////////////////////////////////////////////////////////////
	#region Class Construction and Destruction Methods
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor called once upon plugin class receiving a command to start device
	# communication. Defers to the base class for processing but initializes params
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, plugin, device):
		super(RPFrameworkRESTfulDevice, self).__init__(plugin, device)

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
			self.hostPlugin.logger.debug(u'Concurrent Processing Thread started for device {0}'.format(self.indigoDevice.id))
		
			# obtain the IP or host address that will be used in connecting to the
			# RESTful service via a function call to allow overrides
			deviceHTTPAddress = self.getRESTfulDeviceAddress()
			if deviceHTTPAddress is None:
				self.hostPlugin.logger.error(u'No IP address specified for device {0}; ending command processing thread.'.format(self.indigoDevice.id))
				return
			
			# retrieve any configuration information that may have been setup in the
			# plugin configuration and/or device configuration
			updateStatusPollerPropertyName = self.hostPlugin.getGUIConfigValue(self.indigoDevice.deviceTypeId, RPFrameworkRESTfulDevice.GUI_CONFIG_RESTFULSTATUSPOLL_INTERVALPROPERTY, u'updateInterval')
			updateStatusPollerInterval     = int(self.indigoDevice.pluginProps.get(updateStatusPollerPropertyName, u'90'))
			updateStatusPollerNextRun      = None
			updateStatusPollerActionId     = self.hostPlugin.getGUIConfigValue(self.indigoDevice.deviceTypeId, RPFrameworkRESTfulDevice.GUI_CONFIG_RESTFULSTATUSPOLL_ACTIONID, u'')
			emptyQueueReducedWaitCycles    = int(self.hostPlugin.getGUIConfigValue(self.indigoDevice.deviceTypeId, RPFrameworkRESTfulDevice.GUI_CONFIG_RESTFULDEV_EMPTYQUEUE_SPEEDUPCYCLES, u'80'))
			
			# begin the infinite loop which will run as long as the queue contains commands
			# and we have not received an explicit shutdown request
			continueProcessingCommands = True
			lastQueuedCommandCompleted = 0
			while continueProcessingCommands == True:
				# process pending commands now...
				while not commandQueue.empty():
					lenQueue = commandQueue.qsize()
					self.hostPlugin.logger.threaddebug(u'Command queue has {0} command(s) waiting'.format(lenQueue))
					
					# the command name will identify what action should be taken... we will handle the known
					# commands and dispatch out to the device implementation, if necessary, to handle unknown
					# commands
					command = commandQueue.get()
					if command.commandName == RPFrameworkCommand.CMD_INITIALIZE_CONNECTION:
						# specialized command to instanciate the concurrent thread
						# safely ignore this... just used to spin up the thread
						self.hostPlugin.logger.threaddebug(u'Create connection command de-queued')
						
						# if the device supports polling for status, it may be initiated here now; however, we should implement a pause to ensure that
						# devices are created properly (RESTFul devices may respond too fast since no connection need be established)
						statusUpdateStartupDelay = float(self.hostPlugin.getGUIConfigValue(self.indigoDevice.deviceTypeId, RPFrameworkRESTfulDevice.GUI_CONFIG_RESTFULSTATUSPOLL_STARTUPDELAY, u'3'))
						if statusUpdateStartupDelay > 0.0:
							commandQueue.put(RPFrameworkCommand.RPFrameworkCommand(RPFrameworkCommand.CMD_PAUSE_PROCESSING, commandPayload=str(statusUpdateStartupDelay)))
						commandQueue.put(RPFrameworkCommand.RPFrameworkCommand(RPFrameworkCommand.CMD_UPDATE_DEVICE_STATUS_FULL, parentAction=updateStatusPollerActionId))
						
					elif command.commandName == RPFrameworkCommand.CMD_TERMINATE_PROCESSING_THREAD:
						# a specialized command designed to stop the processing thread indigo
						# the event of a shutdown						
						continueProcessingCommands = False
						
					elif command.commandName == RPFrameworkCommand.CMD_PAUSE_PROCESSING:
						# the amount of time to sleep should be a float found in the
						# payload of the command
						try:
							pauseTime = float(command.commandPayload)
							self.hostPlugin.logger.threaddebug(u'Initiating sleep of {0} seconds from command.'.format(pauseTime))
							time.sleep(pauseTime)
						except:
							self.hostPlugin.logger.warning(u'Invalid pause time requested')
							
					elif command.commandName == RPFrameworkCommand.CMD_UPDATE_DEVICE_STATUS_FULL:
						# this command instructs the plugin to update the full status of the device (all statuses
						# that may be read from the device should be read)
						if updateStatusPollerActionId != u'':
							self.hostPlugin.logger.debug(u'Executing full status update request...')
							self.hostPlugin.executeAction(None, indigoActionId=updateStatusPollerActionId, indigoDeviceId=self.indigoDevice.id, paramValues=None)
							updateStatusPollerNextRun = time.time() + updateStatusPollerInterval
						else:
							self.hostPlugin.logger.threaddebug(u'Ignoring status update request, no action specified to update device status')
							
					elif command.commandName == RPFrameworkCommand.CMD_NETWORKING_WOL_REQUEST:
						# this is a request to send a Wake-On-LAN request to a network-enabled device
						# the command payload should be the MAC address of the device to wake up
						try:
							sendWakeOnLAN(command.commandPayload)
						except:
							self.hostPlugin.logger.error(u'Failed to send Wake-on-LAN packet')
						
					elif command.commandName == RPFrameworkRESTfulDevice.CMD_RESTFUL_GET or command.commandName == RPFrameworkRESTfulDevice.CMD_RESTFUL_PUT or command.commandName == RPFrameworkRESTfulDevice.CMD_DOWNLOADFILE or command.commandName == RPFrameworkRESTfulDevice.CMD_DOWNLOADIMAGE:
						try:
							self.hostPlugin.logger.debug(u'Processing GET operation: {0}'.format(command.commandPayload))
							
							# gather all of the parameters from the command payload
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
							commandPayloadList = command.getPayloadAsList()
							fullGetUrl = commandPayloadList[0] + u'://' + deviceHTTPAddress[0] + u':' + to_unicode(deviceHTTPAddress[1]) + commandPayloadList[1]
							self.hostPlugin.logger.threaddebug(u'Full URL for GET: {0}'.format(fullGetUrl))
							
							customHeaders = {}
							self.addCustomHTTPHeaders(customHeaders)
							
							authenticationParam = None
							authenticationType = u'none'
							username = u''
							password = u''
							if len(commandPayloadList) >= 3:
								authenticationType = commandPayloadList[2]
							if len(commandPayloadList) >= 4:
								username = commandPayloadList[3]
							if len(commandPayloadList) >= 5:
								password = commandPayloadList[4]
							if authenticationType != 'none' and username != u'':
								self.hostPlugin.logger.threaddebug(u'Using login credentials... Username=> {0}; Password=>{1} characters long'.format(username, len(password)))
								if authenticationType.lower() == 'digest':
									self.hostPlugin.logger.threaddebug(u'Enabling digest authentication')
									authenticationParam = HTTPDigestAuth(username, password)
								else:
									authenticationParam = (username, password)
							
							# execute the URL fetching depending upon the method requested
							if command.commandName == RPFrameworkRESTfulDevice.CMD_RESTFUL_GET or command.commandName == RPFrameworkRESTfulDevice.CMD_DOWNLOADFILE or command.commandName == RPFrameworkRESTfulDevice.CMD_DOWNLOADIMAGE:
								responseObj = requests.get(fullGetUrl, auth=authenticationParam, headers=customHeaders, verify=False)
							elif command.commandName == RPFrameworkRESTfulDevice.CMD_RESTFUL_PUT:
								dataToPost = None
								if len(commandPayloadList) >= 6:
									dataToPost = commandPayloadList[5]
								responseObj = requests.post(fullGetUrl, auth=authenticationParam, headers=customHeaders, verify=False, data=dataToPost)
								
							# if the network command failed then allow the error processor to handle the issue
							if responseObj.status_code == 200:
								# the response handling will depend upon the type of command... binary returns must be
								# handled separately from (expected) text-based ones
								if command.commandName == RPFrameworkRESTfulDevice.CMD_DOWNLOADFILE or command.commandName == RPFrameworkRESTfulDevice.CMD_DOWNLOADIMAGE:
									# this is a binary return that should be saved to the file system without modification
									if len(commandPayloadList) >= 6:
										saveLocation = commandPayloadList[5]
									
										# execute the actual save from the binary response stream
										try:
											localFile = open(to_str(saveLocation), "wb")
											localFile.write(responseObj.content)
											self.hostPlugin.logger.threaddebug(u'Command Response: [{0}] -=- binary data written to {1}-=-'.format(responseObj.status_code, saveLocation))
										
											if command.commandName == RPFrameworkRESTfulDevice.CMD_DOWNLOADIMAGE:
												imageResizeWidth = 0
												imageResizeHeight = 0
												if len(command.commandPayload) >= 7:
													imageResizeWidth = int(command.commandPayload[6])
												if len(command.commandPayload) >= 8:
													imageResizeHeight = int(command.commandPayload[7])
								
												resizeCommandLine = u''
												if imageResizeWidth > 0 and imageResizeHeight > 0:
													# we have a specific size as a target...
													resizeCommandLine = u'sips -z {0} {1} {2}'.format(imageResizeHeight, imageResizeWidth, saveLocation)
												elif imageResizeWidth > 0:
													# we have a maximum size measurement
													resizeCommandLine = u'sips -Z {0} {1}'.format(imageResizeWidth, saveLocation)
									
												# if a command line has been formed, fire that off now...
												if resizeCommandLine == u'':
													self.hostPlugin.logger.debug(u'No image size specified for {0}; skipping resize.'.format(saveLocation))
												else:
													self.hostPlugin.logger.threaddebug(u'Executing resize via command line "{0}"'.format(resizeCommandLine))
													try:
														subprocess.Popen(resizeCommandLine, shell=True)
														self.hostPlugin.logger.debug(u'{0} resized via sip shell command'.format(saveLocation))
													except:
														self.hostPlugin.logger.error(u'Error resizing image via sips')
														
											# we have completed the download and processing successfully... allow the
											# device (or its descendants) to process successful operations
											self.notifySuccessfulDownload(command, saveLocation)
										finally:
											if not localFile is None:
												localFile.close()					
									else:
										self.hostPlugin.logger.error(u'Unable to complete download action - no filename specified')
								else:
									# handle this return as a text-based return
									self.hostPlugin.logger.threaddebug(u'Command Response: [{0}] {1}'.format(responseObj.status_code, responseObj.text))
									self.hostPlugin.logger.threaddebug(u'{0} command completed; beginning response processing'.format(command.commandName))
									self.handleDeviceTextResponse(responseObj, command)
									self.hostPlugin.logger.threaddebug(u'{0} command response processing completed'.format(command.commandName))
									
							elif responseObj.status_code == 401:
								self.handleRESTfulError(command, u'401 - Unauthorized', responseObj)
							
							else:
								self.handleRESTfulError(command, str(responseObj.status_code), responseObj)
							 	
						except Exception as e:
							# the response value really should not be defined here as it bailed without
							# catching any of our response error conditions
							self.handleRESTfulError(command, e, None)
						
					elif command.commandName == RPFrameworkRESTfulDevice.CMD_SOAP_REQUEST or command.commandName == RPFrameworkRESTfulDevice.CMD_JSON_REQUEST:
						responseObj = None
						try:
							# this is to post a SOAP request to a web service... this will be similar to a restful put request
							# but will contain a body payload
							self.hostPlugin.logger.threaddebug(u'Received SOAP/JSON command request: {0}'.format(command.commandPayload))
							soapPayloadParser = re.compile(r"^\s*([^\n]+)\n\s*([^\n]+)\n(.*)$", re.DOTALL)
							soapPayloadData   = soapPayloadParser.match(command.commandPayload)
							soapPath          = soapPayloadData.group(1).strip()
							soapAction        = soapPayloadData.group(2).strip()
							soapBody          = soapPayloadData.group(3).strip()
							fullGetUrl        = u'http://' + deviceHTTPAddress[0] + u':' + to_str(deviceHTTPAddress[1]) + to_str(soapPath)
							self.hostPlugin.logger.debug(u'Processing SOAP/JSON operation to {0}'.format(fullGetUrl))

							customHeaders = {}
							self.addCustomHTTPHeaders(customHeaders)
							if command.commandName == RPFrameworkRESTfulDevice.CMD_SOAP_REQUEST:
								customHeaders["Content-type"] = "text/xml; charset=\"UTF-8\""
								customHeaders["SOAPAction"]   = to_str(soapAction)
							else:
								customHeaders["Content-type"] = "application/json"
							
							# execute the URL post to the web service
							self.hostPlugin.logger.threaddebug(u'Sending SOAP/JSON request:\n{0}'.format(soapBody))
							self.hostPlugin.logger.threaddebug(u'Using headers: \n{0}'.format(customHeaders))
							responseObj = requests.post(fullGetUrl, headers=customHeaders, verify=False, data=to_str(soapBody))
							
							if responseObj.status_code == 200:
								# handle this return as a text-based return
								self.hostPlugin.logger.threaddebug(u'Command Response: [{0}] {1}'.format(responseObj.status_code, responseObj.text))
								self.hostPlugin.logger.threaddebug(u'{0} command completed; beginning response processing'.format(command.commandName))
								self.handleDeviceTextResponse(responseObj, command)
								self.hostPlugin.logger.threaddebug(u'{0} command response processing completed'.format(command.commandName))
								
							else:
								self.hostPlugin.logger.threaddebug(u'Command Response was not HTTP OK, handling RESTful error')
								self.handleRESTfulError(command, str(responseObj.status_code), responseObj)

						except Exception as e:
							self.handleRESTfulError(command, e, responseObj)
					
					else:
						# this is an unknown command; dispatch it to another routine which is
						# able to handle the commands (to be overridden for individual devices)
						self.handleUnmanagedCommandInQueue(deviceHTTPAddress, command)
					
					# if the command has a pause defined for after it is completed then we
					# should execute that pause now
					if command.postCommandPause > 0.0 and continueProcessingCommands == True:
						self.hostPlugin.logger.threaddebug(u'Post Command Pause: {0}'.format(command.postCommandPause))
						time.sleep(command.postCommandPause)
					
					# complete the dequeuing of the command, allowing the next
					# command in queue to rise to the top
					commandQueue.task_done()
					lastQueuedCommandCompleted = emptyQueueReducedWaitCycles
				
				# when the queue is empty, pause a bit on each iteration
				if continueProcessingCommands == True:
					# if we have just completed a command recently, half the amount of
					# wait time, assuming that a subsequent command could be forthcoming
					if lastQueuedCommandCompleted > 0:
						time.sleep(self.emptyQueueThreadSleepTime/2)
						lastQueuedCommandCompleted = lastQueuedCommandCompleted - 1
					else:
						time.sleep(self.emptyQueueThreadSleepTime)
				
				# check to see if we need to issue an update...
				if updateStatusPollerNextRun is not None and time.time() > updateStatusPollerNextRun:
					commandQueue.put(RPFrameworkCommand.RPFrameworkCommand(RPFrameworkCommand.CMD_UPDATE_DEVICE_STATUS_FULL, parentAction=updateStatusPollerActionId))
				
		# handle any exceptions that are thrown during execution of the plugin... note that this
		# should terminate the thread, but it may get spun back up again
		except SystemExit:
			pass
		except Exception:
			self.hostPlugin.logger.exception(u'Exception in background processing')
		except:
			self.hostPlugin.logger.exception(u'Exception in background processing')
		finally:
			self.hostPlugin.logger.debug(u'Command thread ending processing')
		
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine should return the HTTP address that will be used to connect to the
	# RESTful device. It may connect via IP address or a host name
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getRESTfulDeviceAddress(self):
		return None
	
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine should be overridden in individual device classes whenever they must
	# handle custom commands that are not already defined
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def handleUnmanagedCommandInQueue(self, deviceHTTPAddress, rpCommand):
		pass
		
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will be called prior to any network operation to allow the addition
	# of custom headers to the request (does not include file download)
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def addCustomHTTPHeaders(self, httpRequest):
		pass
		
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will process any response from the device following the list of
	# response objects defined for this device type. For telnet this will always be
	# a text string
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def handleDeviceTextResponse(self, responseObj, rpCommand):
		# loop through the list of response definitions defined in the (base) class
		# and determine if any match
		responseText = responseObj.text
		for rpResponse in self.hostPlugin.getDeviceResponseDefinitions(self.indigoDevice.deviceTypeId):
			if rpResponse.isResponseMatch(responseText, rpCommand, self, self.hostPlugin):
				self.hostPlugin.logger.threaddebug(u'Found response match: {0}'.format(rpResponse.responseId))
				rpResponse.executeEffects(responseText, rpCommand, self, self.hostPlugin)
	
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will handle an error as thrown by the REST call... it allows 
	# descendant classes to do their own processing
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-		
	def handleRESTfulError(self, rpCommand, err, response=None):
		if rpCommand.commandName == RPFrameworkRESTfulDevice.CMD_RESTFUL_PUT or rpCommand.commandName == RPFrameworkRESTfulDevice.CMD_RESTFUL_GET:
			self.hostPlugin.logger.exception(u'An error occurred executing the GET/PUT request (Device: {0}): {1}'.format(self.indigoDevice.id, err))
		else:
			self.hostPlugin.logger.exception(u'An error occurred processing the SOAP/JSON POST request: (Device: {0}): {1}'.format(self.indigoDevice.id, err))
			
		if not response is None and not response.text is None:
			self.hostPlugin.logger.debug(to_unicode(response.text))
			
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will handle notification to the device whenever a file was successfully
	# downloaded via a DOWNLOAD_FILE or DOWNLOAD_IMAGE command
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def notifySuccessfulDownload(self, rpCommand, outputFileName):
		pass
	
	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////
	