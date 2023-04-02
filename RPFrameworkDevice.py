#! /usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################################
# RPFrameworkDevice by RogueProeliator <adam.d.ashe@gmail.com>
# Base class for all RogueProeliator's devices created by plugins for Perceptive
# Automation's Indigo software.
#######################################################################################

# region Python imports
from __future__ import absolute_import

import functools
import random
import time
import queue as Queue

try:
	import indigo
except:
	from .RPFrameworkIndigoMock import RPFrameworkIndigoMock as indigo

from .RPFrameworkCommand import RPFrameworkCommand
from .RPFrameworkThread  import RPFrameworkThread
from .RPFrameworkUtils   import to_unicode

from .RPFrameworkPlugin import GUI_CONFIG_RECONNECTIONATTEMPT_LIMIT
from .RPFrameworkPlugin import GUI_CONFIG_RECONNECTIONATTEMPT_DELAY
from .RPFrameworkPlugin import GUI_CONFIG_RECONNECTIONATTEMPT_SCHEME
from .RPFrameworkPlugin import GUI_CONFIG_RECONNECTIONATTEMPT_SCHEME_REGRESS
from .RPFrameworkPlugin import GUI_CONFIG_RECONNECTIONATTEMPT_SCHEME_FIXED
from .RPFrameworkPlugin import GUI_CONFIG_CHILDDICTIONARYKEYFORMAT
# endregion


class RPFrameworkDevice(object):
	
	#######################################################################################
	# region Class Construction and Destruction Methods
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor called once upon plugin class receiving a command to start device
	# communication. The plugin will call other commands when needed, simply zero out the
	# member variables
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, plugin, device):
		self.host_plugin                = plugin
		self.indigoDevice               = device
		self.child_devices              = dict()
		self.device_instance_identifier = random.getrandbits(16)

		self.command_queue              = Queue.Queue()
		self.concurrent_thread          = None
		self.failed_connection_attempts = 0
		self.empty_queue_sleep_time     = 0.1
		
		self.upgraded_device_states     = list()
		self.upgraded_device_properties = list()

	# endregion
	#######################################################################################

	#######################################################################################
	# region Validation and GUI functions
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called to retrieve a dynamic list of elements for an action (or
	# other ConfigUI based) routine
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getConfigDialogMenuItems(self, filter, values_dict, type_id, target_id):
		return []
	
	# endregion
	#######################################################################################
		
	#######################################################################################
	# region Public Communication-Interface Methods
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This call will be made from the plugin in order to start the communications with the
	# hardware device... this will spin up the concurrent processing thread.
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def initiate_communications(self, initialize_connect=True):
		# determine if this device is missing any properties that were added
		# during device/plugin upgrades
		properties_dict_update_required = False
		plugin_props_copy = self.indigoDevice.pluginProps
		for newPropertyDefn in self.upgraded_device_properties:
			if not (newPropertyDefn[0] in plugin_props_copy):
				self.host_plugin.logger.info(f"Triggering property update due to missing device property: {newPropertyDefn[0]}")
				plugin_props_copy[newPropertyDefn[0]]  = newPropertyDefn[1]
				properties_dict_update_required        = True
				
				# safeguard in case the device doesn't get updated...
				self.indigoDevice.pluginProps[newPropertyDefn[0]] = newPropertyDefn[1]

		if properties_dict_update_required:
			self.indigoDevice.replacePluginPropsOnServer(plugin_props_copy)
	
		# determine if this device is missing any states that were defined in upgrades
		state_reload_required = False
		for newStateName in self.upgraded_device_states:
			if not (newStateName in self.indigoDevice.states):
				self.host_plugin.logger.info(f"Triggering state reload due to missing device state: {newStateName}")
				state_reload_required = True
		if state_reload_required:
			self.indigoDevice.stateListOrDisplayStateIdChanged()
		
		# start concurrent processing thread by injecting a placeholder
		# command to the queue
		if initialize_connect:
			self.queue_device_command(RPFrameworkCommand(RPFrameworkCommand.CMD_INITIALIZE_CONNECTION))

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will shut down communications with the hardware device
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def terminate_communications(self):
		self.host_plugin.logger.debug(f"Initiating shutdown of communications with {self.indigoDevice.name}")
		if not (self.concurrent_thread is None) and self.concurrent_thread.isAlive():
			self.concurrent_thread.terminateThread()
			self.concurrent_thread.join()
		self.concurrent_thread = None
		self.host_plugin.logger.debug(f"Shutdown of communications with {self.indigoDevice.name} complete")
	
	# endregion
	#######################################################################################
		
	#######################################################################################
	# region Queue and Command Processing Methods
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Add new command to queue, which is polled and emptied by 
	# concurrent_command_processing_thread funtion
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def queue_device_command(self, command):
		self.command_queue.put(command)
		
		# if connection to the device has not started, or has timed out, then start up a
		# concurrent thread to handle communications
		if self.concurrent_thread is None or self.concurrent_thread.isAlive() == False:
			self.concurrent_thread = RPFrameworkThread.RPFrameworkThread(target=functools.partial(self.concurrent_command_processing_thread, self.command_queue))
			self.concurrent_thread.start()
			
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Add new commands to queue as a list, ensuring that they are executed in-order
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def queue_device_commands(self, command_list):
		for rp_cmd in command_list:
			self.queue_device_command(rp_cmd)
			
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is designed to run in a concurrent thread and will continuously monitor
	# the commands queue for work to do.
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def concurrent_command_processing_thread(self, command_queue):
		pass
		
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will process a device's reconnection attempt... note that by default
	# a device will NOT attempt to re-initialize communications; it must be enabled via
	# the GUI Configuration
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def schedule_reconnection_attempt(self):
		self.host_plugin.logger.debug("Scheduling reconnection attempt...")
		try:
			self.failed_connection_attempts = self.failed_connection_attempts + 1
			max_reconnect_attempts = int(self.host_plugin.get_gui_config_value(self.indigoDevice.deviceTypeId, GUI_CONFIG_RECONNECTIONATTEMPT_LIMIT, "0"))
			if self.failed_connection_attempts > max_reconnect_attempts:
				self.host_plugin.logger.debug(f"Maximum reconnection attempts reached (or not allowed) for device {self.indigoDevice.id}")
			else:
				reconnect_attempt_delay  = int(self.host_plugin.get_gui_config_value(self.indigoDevice.deviceTypeId, GUI_CONFIG_RECONNECTIONATTEMPT_DELAY, "60"))
				reconnect_attempt_scheme = self.host_plugin.get_gui_config_value(self.indigoDevice.deviceTypeId, GUI_CONFIG_RECONNECTIONATTEMPT_SCHEME, GUI_CONFIG_RECONNECTIONATTEMPT_SCHEME_REGRESS)
			
				if reconnect_attempt_scheme == GUI_CONFIG_RECONNECTIONATTEMPT_SCHEME_FIXED:
					reconnect_seconds = reconnect_attempt_delay
				else:
					reconnect_seconds = reconnect_attempt_delay * self.failed_connection_attempts
				reconnect_attempt_time = time.time() + reconnect_seconds

				self.host_plugin.plugin_command_queue.put(RPFrameworkCommand(RPFrameworkCommand.CMD_DEVICE_RECONNECT, command_payload=(self.indigoDevice.id, self.device_instance_identifier, reconnect_attempt_time)))
				self.host_plugin.logger.debug(f"Reconnection attempt scheduled for {reconnect_seconds} seconds")
		except:
			self.host_plugin.logger.error("Failed to schedule reconnection attempt to device")
	
	# endregion
	#######################################################################################
		
	#######################################################################################
	# region Device Hierarchy (Parent/Child Relationship) Routines
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will generate the key to use in the managed child devices dictionary
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def get_child_device_key_by_device(self, device):
		# the key into the dictionary will be specified by the GUI configuration variable
		# of THIS (parent) device... by default it will just be the child device's ID
		child_device_key = self.host_plugin.substitute_indigo_values(self.host_plugin.get_gui_config_value(self.indigoDevice.deviceTypeId, GUI_CONFIG_CHILDDICTIONARYKEYFORMAT, ""), device, None)
		if child_device_key == "":
			child_device_key = to_unicode(device.indigoDevice.id)
		return child_device_key
	
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will add a new child device to the device; the parameter will be of
	# RPFrameworkDevice descendant
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def add_child_device(self, device):
		self.host_plugin.logger.threaddebug(f"Adding child device {device.indigoDevice.id} to {self.indigoDevice.id}")
		
		# the key into the dictionary will be specified by the GUI configuration variable
		child_device_key = self.get_child_device_key_by_device(device)
		self.host_plugin.logger.threaddebug(f"Created device key: {child_device_key}")
			
		# add the device to the list of those managed by this device...
		self.child_devices[child_device_key] = device
		
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will remove a child device from the list of managed devices; note that
	# the plugin continues to handle all device lifecycle calls!
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def remove_child_device(self, device):
		self.host_plugin.logger.threaddebug(f"Removing child device {device.indigoDevice.id} from {self.indigoDevice.id}")
		
		# the key into the dictionary will be specified by the GUI configuration variable
		child_device_key = self.get_child_device_key_by_device(device)
		
		# remove the device...
		del self.child_devices[child_device_key]

	# endregion
	#######################################################################################
		
	#######################################################################################
	# region Utility Routines
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will reload the Indigo device from the database; useful if we need to
	# get updated states or information 
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def reload_indigo_device(self):
		self.indigoDevice = indigo.devices[self.indigoDevice.id]
		
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will update both the device's state list and the server with the new
	# device states
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def update_states_for_device(self, states_to_update):
		for update_value in states_to_update:
			self.indigoDevice.states[update_value["key"]] = update_value["value"]
		self.indigoDevice.updateStatesOnServer(states_to_update)
	
	# endregion
	#######################################################################################
	