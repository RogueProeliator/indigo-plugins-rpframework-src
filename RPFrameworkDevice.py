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
import queue as Queue

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
# RPFrameworkDevice
#	Base class for Indigo plugin devices that provides standard functionality such as
#	multithreaded communications and attribute management
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
		properties_dict_update_required = False
		plugin_props_copy = self.indigoDevice.pluginProps
		for newPropertyDefn in self.upgradedDeviceProperties:
			if not (newPropertyDefn[0] in plugin_props_copy):
				self.hostPlugin.logger.info(f"Triggering property update due to missing device property: {newPropertyDefn[0]}")
				plugin_props_copy[newPropertyDefn[0]]  = newPropertyDefn[1]
				properties_dict_update_required        = True
				
				# safeguard in case the device doesn't get updated...
				self.indigoDevice.pluginProps[newPropertyDefn[0]] = newPropertyDefn[1]

		if properties_dict_update_required:
			self.indigoDevice.replacePluginPropsOnServer(plugin_props_copy)
	
		# determine if this device is missing any states that were defined in upgrades
		state_reload_required = False
		for newStateName in self.upgradedDeviceStates:
			if not (newStateName in self.indigoDevice.states):
				self.hostPlugin.logger.info(f"Triggering state reload due to missing device state: {newStateName}")
				state_reload_required = True
		if state_reload_required:
			self.indigoDevice.stateListOrDisplayStateIdChanged()
		
		# start concurrent processing thread by injecting a placeholder
		# command to the queue
		if initializeConnect:
			self.queueDeviceCommand(RPFrameworkCommand(RPFrameworkCommand.CMD_INITIALIZE_CONNECTION))

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will shut down communications with the hardware device
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def terminateCommunications(self):
		self.hostPlugin.logger.debug(f"Initiating shutdown of communications with {self.indigoDevice.name}")
		if not (self.concurrentThread is None) and self.concurrentThread.isAlive():
			self.concurrentThread.terminateThread()
			self.concurrentThread.join()
		self.concurrentThread = None
		self.hostPlugin.logger.debug(f"Shutdown of communications with {self.indigoDevice.name} complete")
	
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
		for rp_cmd in commandList:
			self.queueDeviceCommand(rp_cmd)
			
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
		self.hostPlugin.logger.debug("Scheduling reconnection attempt...")
		try:
			self.failedConnectionAttempts = self.failedConnectionAttempts + 1
			max_reconnect_attempts = int(self.hostPlugin.getGUIConfigValue(self.indigoDevice.deviceTypeId, RPFrameworkPlugin.GUI_CONFIG_RECONNECTIONATTEMPT_LIMIT, "0"))
			if self.failedConnectionAttempts > max_reconnect_attempts:
				self.hostPlugin.logger.debug(f"Maximum reconnection attempts reached (or not allowed) for device {self.indigoDevice.id}")
			else:
				reconnect_attempt_delay  = int(self.hostPlugin.getGUIConfigValue(self.indigoDevice.deviceTypeId, RPFrameworkPlugin.GUI_CONFIG_RECONNECTIONATTEMPT_DELAY, "60"))
				reconnect_attempt_scheme = self.hostPlugin.getGUIConfigValue(self.indigoDevice.deviceTypeId, RPFrameworkPlugin.GUI_CONFIG_RECONNECTIONATTEMPT_SCHEME, RPFrameworkPlugin.GUI_CONFIG_RECONNECTIONATTEMPT_SCHEME_REGRESS)
			
				if reconnect_attempt_scheme == RPFrameworkPlugin.GUI_CONFIG_RECONNECTIONATTEMPT_SCHEME_FIXED:
					reconnect_seconds = reconnect_attempt_delay
				else:
					reconnect_seconds = reconnect_attempt_delay * self.failedConnectionAttempts
				reconnect_attempt_time = time.time() + reconnect_seconds

				self.hostPlugin.pluginCommandQueue.put(RPFrameworkCommand.RPFrameworkCommand(RPFrameworkCommand.CMD_DEVICE_RECONNECT, commandPayload=(self.indigoDevice.id, self.deviceInstanceIdentifier, reconnect_attempt_time)))
				self.hostPlugin.logger.debug(f"Reconnection attempt scheduled for {reconnect_seconds} seconds")
		except:
			self.hostPlugin.logger.error("Failed to schedule reconnection attempt to device")
	
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
		child_device_key = self.hostPlugin.substituteIndigoValues(self.hostPlugin.getGUIConfigValue(self.indigoDevice.deviceTypeId, RPFrameworkPlugin.GUI_CONFIG_CHILDDICTIONARYKEYFORMAT, ""), device, None)
		if child_device_key == "":
			child_device_key = to_unicode(device.indigoDevice.id)
		return child_device_key
	
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will add a new child device to the device; the parameter will be of
	# RPFrameworkDevice descendant
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def addChildDevice(self, device):
		self.hostPlugin.logger.threaddebug(f"Adding child device {device.indigoDevice.id} to {self.indigoDevice.id}")
		
		# the key into the dictionary will be specified by the GUI configuration variable
		child_device_key = self.getChildDeviceKeyByDevice(device)
		self.hostPlugin.logger.threaddebug(f"Created device key: {child_device_key}")
			
		# add the device to the list of those managed by this device...
		self.childDevices[child_device_key] = device
		
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will remove a child device from the list of managed devices; note that
	# the plugin continues to handle all device lifecycle calls!
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def removeChildDevice(self, device):
		self.hostPlugin.logger.threaddebug(f"Removing child device {device.indigoDevice.id} from {self.indigoDevice.id}")
		
		# the key into the dictionary will be specified by the GUI configuration variable
		child_device_key = self.getChildDeviceKeyByDevice(device)
		
		# remove the device...
		del self.childDevices[child_device_key]

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
		for update_value in statesToUpdate:
			self.indigoDevice.states[update_value["key"]] = update_value["value"]
		self.indigoDevice.updateStatesOnServer(statesToUpdate)
	
	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////
	