#! /usr/bin/env python
# -*- coding: utf-8 -*-
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# RPFrameworkDevice by RogueProeliator <adam.d.ashe@gmail.com>
# 	Base class for all RogueProeliator's devices created by plugins for Perceptive
#	Automation's Indigo software.
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////

#/////////////////////////////////////////////////////////////////////////////////////////
#region Python imports
from __future__ import absolute_import

import functools
import random
import sys
import time
if sys.version_info > (3,):
	import queue as Queue
else:
	import Queue

try:
	import indigo
except:
	from .RPFrameworkIndigoMock import RPFrameworkIndigoMock as indigo

from .RPFrameworkCommand import RPFrameworkCommand
from .RPFrameworkPlugin  import RPFrameworkPlugin
from .RPFrameworkThread  import RPFrameworkThread
from .RPFrameworkUtils   import to_unicode

#endregion
#/////////////////////////////////////////////////////////////////////////////////////////

#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# RPFrameworkDevice
#	Base class for Indigo plugin devices that provides standard functionality such as
#	multi-threaded communications and attribute management
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
class RPFrameworkDevice(object):
	
	#/////////////////////////////////////////////////////////////////////////////////////
	#region Class Construction and Destruction Methods
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor called once upon plugin class receiving a command to start device
	# communication. The plugin will call other commands when needed, simply zero out the
	# member variables
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, plugin, device):
		self.hostPlugin                = plugin
		self.indigoDevice              = device
		self.childDevices              = dict()
		self.deviceInstanceIdentifier  = random.getrandbits(16)

		self.commandQueue              = Queue.Queue()
		self.concurrentThread          = None
		self.failedConnectionAttempts  = 0
		self.emptyQueueThreadSleepTime = 0.1
		
		self.upgradedDeviceStates      = list()
		self.upgradedDeviceProperties  = list()

	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////
	
	#/////////////////////////////////////////////////////////////////////////////////////
	#region Validation and GUI functions
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called to retrieve a dynamic list of elements for an action (or
	# other ConfigUI based) routine
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getConfigDialogMenuItems(self, filter, valuesDict, typeId, targetId):
		return []
	
	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////
		
	#/////////////////////////////////////////////////////////////////////////////////////
	#region Public Communication-Interface Methods	
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This call will be made from the plugin in order to start the communications with the
	# hardware device... this will spin up the concurrent processing thread.
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def initiateCommunications(self, initializeConnect=True):
		# determine if this device is missing any properties that were added
		# during device/plugin upgrades
		propertiesDictUpdateRequired = False
		pluginPropsCopy = self.indigoDevice.pluginProps
		for newPropertyDefn in self.upgradedDeviceProperties:
			if not (newPropertyDefn[0] in pluginPropsCopy):
				self.hostPlugin.logger.info(u'Triggering property update due to missing device property: {0}'.format(to_unicode(newPropertyDefn[0])))
				pluginPropsCopy[newPropertyDefn[0]] = newPropertyDefn[1]
				propertiesDictUpdateRequired        = True
				
				# safeguard in case the device doesn't get updated...
				self.indigoDevice.pluginProps[newPropertyDefn[0]] = newPropertyDefn[1]

		if propertiesDictUpdateRequired == True:
			self.indigoDevice.replacePluginPropsOnServer(pluginPropsCopy)
	
		# determine if this device is missing any states that were defined in upgrades
		stateReloadRequired = False
		for newStateName in self.upgradedDeviceStates:
			if not (newStateName in self.indigoDevice.states):
				self.hostPlugin.logger.info(u'Triggering state reload due to missing device state: {0}'.format(to_unicode(newStateName)))
				stateReloadRequired = True	
		if stateReloadRequired == True:
			self.indigoDevice.stateListOrDisplayStateIdChanged()
		
		# start concurrent processing thread by injecting a placeholder
		# command to the queue
		if initializeConnect == True:
			self.queueDeviceCommand(RPFrameworkCommand(RPFrameworkCommand.CMD_INITIALIZE_CONNECTION))

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will shut down communications with the hardware device
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def terminateCommunications(self):
		self.hostPlugin.logger.debug(u'Initiating shutdown of communications with {0}'.format(self.indigoDevice.name))
		if not (self.concurrentThread is None) and self.concurrentThread.isAlive() == True:
			self.concurrentThread.terminateThread()
			self.concurrentThread.join()
		self.concurrentThread = None
		self.hostPlugin.logger.debug(u'Shutdown of communications with {0} complete'.format(self.indigoDevice.name))
	
	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////
		
	#/////////////////////////////////////////////////////////////////////////////////////
	#region Queue and Command Processing Methods	
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Add new command to queue, which is polled and emptied by 
	# concurrentCommandProcessingThread funtion
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def queueDeviceCommand(self, command):
		self.commandQueue.put(command)
		
		# if connection to the device has not started, or has timed out, then start up a
		# concurrent thread to handle communications
		if self.concurrentThread is None or self.concurrentThread.isAlive() == False:
			self.concurrentThread = RPFrameworkThread.RPFrameworkThread(target=functools.partial(self.concurrentCommandProcessingThread, self.commandQueue))
			self.concurrentThread.start()
			
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Add new commands to queue as a list, ensuring that they are executed in-order
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def queueDeviceCommands(self, commandList):
		for rpCmd in commandList:
			self.queueDeviceCommand(rpCmd)
			
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is designed to run in a concurrent thread and will continuously monitor
	# the commands queue for work to do.
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def concurrentCommandProcessingThread(self, commandQueue):
		pass
		
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will process a device's reconnection attempt... note that by default
	# a device will NOT attempt to re-initialize communications; it must be enabled via
	# the GUI Configuration
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def scheduleReconnectionAttempt(self):
		self.hostPlugin.logger.debug(u'Scheduling reconnection attempt...')
		try:
			self.failedConnectionAttempts = self.failedConnectionAttempts + 1
			maxReconnectAttempts = int(self.hostPlugin.getGUIConfigValue(self.indigoDevice.deviceTypeId, RPFrameworkPlugin.GUI_CONFIG_RECONNECTIONATTEMPT_LIMIT, u'0'))
			if self.failedConnectionAttempts > maxReconnectAttempts:
				self.hostPlugin.logger.debug(u'Maximum reconnection attempts reached (or not allowed) for device {0}'.format(self.indigoDevice.id))
			else:
				reconnectAttemptDelay = int(self.hostPlugin.getGUIConfigValue(self.indigoDevice.deviceTypeId, RPFrameworkPlugin.GUI_CONFIG_RECONNECTIONATTEMPT_DELAY, u'60'))
				reconnectAttemptScheme = self.hostPlugin.getGUIConfigValue(self.indigoDevice.deviceTypeId, RPFrameworkPlugin.GUI_CONFIG_RECONNECTIONATTEMPT_SCHEME, RPFrameworkPlugin.GUI_CONFIG_RECONNECTIONATTEMPT_SCHEME_REGRESS)
			
				if reconnectAttemptScheme == RPFrameworkPlugin.GUI_CONFIG_RECONNECTIONATTEMPT_SCHEME_FIXED:
					reconnectSeconds = reconnectAttemptDelay
				else:
					reconnectSeconds = reconnectAttemptDelay * self.failedConnectionAttempts
				reconnectAttemptTime = time.time() + reconnectSeconds

				self.hostPlugin.pluginCommandQueue.put(RPFrameworkCommand.RPFrameworkCommand(RPFrameworkCommand.CMD_DEVICE_RECONNECT, commandPayload=(self.indigoDevice.id, self.deviceInstanceIdentifier, reconnectAttemptTime)))
				self.hostPlugin.logger.debug(u'Reconnection attempt scheduled for {0} seconds'.format(reconnectSeconds))
		except:
			self.hostPlugin.logger.error(u'Failed to schedule reconnection attempt to device')			
	
	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////
		
	#/////////////////////////////////////////////////////////////////////////////////////
	#region Device Hierarchy (Parent/Child Relationship) Routines
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will generate the key to use in the managed child devices dictionary
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getChildDeviceKeyByDevice(self, device):
		# the key into the dictionary will be specified by the GUI configuration variable
		# of THIS (parent) device... by default it will just be the child device's ID
		childDeviceKey = self.hostPlugin.substituteIndigoValues(self.hostPlugin.getGUIConfigValue(self.indigoDevice.deviceTypeId, RPFrameworkPlugin.GUI_CONFIG_CHILDDICTIONARYKEYFORMAT, u''), device, None)
		if childDeviceKey == u'':
			childDeviceKey = to_unicode(device.indigoDevice.id)
		return childDeviceKey
	
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will add a new child device to the device; the parameter will be of
	# RPFrameworkDevice descendant
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def addChildDevice(self, device):
		self.hostPlugin.logger.threaddebug(u'Adding child device {0} to {1}'.format(device.indigoDevice.id, self.indigoDevice.id))
		
		# the key into the dictionary will be specified by the GUI configuration variable
		childDeviceKey = self.getChildDeviceKeyByDevice(device)
		self.hostPlugin.logger.threaddebug(u'Created device key: {0}'.format(childDeviceKey))
			
		# add the device to the list of those managed by this device...
		self.childDevices[childDeviceKey] = device
		
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will remove a child device from the list of managed devices; note that
	# the plugin continues to handle all device lifecycle calls!
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def removeChildDevice(self, device):
		self.hostPlugin.logger.threaddebug(u'Removing child device {0} from {1}'.format(device.indigoDevice.id, self.indigoDevice.id))
		
		# the key into the dictionary will be specified by the GUI configuration variable
		childDeviceKey = self.getChildDeviceKeyByDevice(device)
		
		# remove the device...
		del self.childDevices[childDeviceKey]

	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////	
		
	#/////////////////////////////////////////////////////////////////////////////////////
	#region Utility Routines
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will reload the Indigo device from the database; useful if we need to
	# get updated states or information 
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def reloadIndigoDevice(self):
		self.indigoDevice = indigo.devices[self.indigoDevice.id]
		
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will update both the device's state list and the server with the new
	# device states
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def updateStatesForDevice(self, statesToUpdate):
		for updateValue in statesToUpdate:
			self.indigoDevice.states[updateValue["key"]] = updateValue["value"]
		self.indigoDevice.updateStatesOnServer(statesToUpdate)
	
	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////
	