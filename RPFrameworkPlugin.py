#! /usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################################
# RPFrameworkPlugin by RogueProeliator <adam.d.ashe@gmail.com>
# Base class for all RogueProeliator's plugins for Perceptive Automation's Indigo
# home automation software.
#######################################################################################

# region Python Imports
from __future__ import absolute_import
import logging
import queue as Queue
import os
import re
import shutil
from   subprocess import call
import time
import xml.etree.ElementTree

try:
	import indigo
except:
	from .RPFrameworkIndigoMock import RPFrameworkIndigoMock as indigo

from .RPFrameworkCommand        import RPFrameworkCommand
from .RPFrameworkDeviceResponse import RPFrameworkDeviceResponse
from .RPFrameworkDeviceResponse import RPFrameworkDeviceResponseEffect
from .RPFrameworkIndigoAction   import RPFrameworkIndigoActionDfn
from .RPFrameworkIndigoParam    import RPFrameworkIndigoParamDefn
from .RPFrameworkNetworkingUPnP import uPnPDiscover
from .RPFrameworkUtils          import to_str
from .RPFrameworkUtils          import to_unicode

# endregion

# region Constants and configuration variables

GUI_CONFIG_PLUGINSETTINGS                        = "plugin"
GUI_CONFIG_PLUGIN_COMMANDQUEUEIDLESLEEP          = "pluginCommandQueueIdleSleep"
GUI_CONFIG_PLUGIN_DEBUG_SHOWUPNPOPTION           = "showUPnPDebug"
GUI_CONFIG_PLUGIN_DEBUG_UPNPOPTION_SERVICEFILTER = "UPnPDebugServiceFilter"

GUI_CONFIG_ADDRESSKEY                            = "deviceAddressFormat"

GUI_CONFIG_UPNP_SERVICE                          = "deviceUPNPServiceId"
GUI_CONFIG_UPNP_CACHETIMESEC                     = "deviceUPNPSeachCacheTime"
GUI_CONFIG_UPNP_ENUMDEVICESFIELDID               = "deviceUPNPDeviceFieldId"
GUI_CONFIG_UPNP_DEVICESELECTTARGETFIELDID        = "deviceUPNPDeviceSelectedFieldId"

GUI_CONFIG_ISCHILDDEVICEID                       = "deviceIsChildDevice"
GUI_CONFIG_PARENTDEVICEIDPROPERTYNAME            = "deviceParentIdProperty"
GUI_CONFIG_CHILDDICTIONARYKEYFORMAT              = "childDeviceDictionaryKeyFormat"

GUI_CONFIG_RECONNECTIONATTEMPT_LIMIT             = "reconnectAttemptLimit"
GUI_CONFIG_RECONNECTIONATTEMPT_DELAY             = "reconnectAttemptDelay"
GUI_CONFIG_RECONNECTIONATTEMPT_SCHEME            = "reconnectAttemptScheme"
GUI_CONFIG_RECONNECTIONATTEMPT_SCHEME_FIXED      = "fixed"
GUI_CONFIG_RECONNECTIONATTEMPT_SCHEME_REGRESS    = "regress"

GUI_CONFIG_DATABASE_CONN_ENABLED                 = "databaseConnectionEnabled"
GUI_CONFIG_DATABASE_CONN_TYPE                    = "databaseConnectionType"
GUI_CONFIG_DATABASE_CONN_DBNAME                  = "databaseConnectionDBName"

DEBUGLEVEL_NONE                                  = 0		# no .debug() logs will be shown in the Indigo log
DEBUGLEVEL_LOW                                   = 1		# show .debug() logs in the Indigo log
DEBUGLEVEL_HIGH                                  = 2		# show .ThreadDebug() log calls in the Indigo log

# endregion


class RPFrameworkPlugin(indigo.PluginBase):

	#######################################################################################
	# region Class construction and destruction methods
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor called once upon plugin class creation; set up the basic functionality
	# common to all plugins based on the framework
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, plugin_id, plugin_display_name, plugin_version, plugin_prefs, managed_device_class_module=None, supports_upnp=False):
		# flag the plugin as undergoing initialization so that we know the full
		# indigo plugin is not yet available
		self.plugin_initializing = True
		self.supports_upnp_debug = supports_upnp

		# call the base class' initialization to begin setup...
		super().__init__(plugin_id, plugin_display_name, plugin_version, plugin_prefs)

		# set up a custom logging format to make it easier to look through (this applies only to the plugin's
		# individual file handler
		logging_format_string = logging.Formatter("%(asctime)s.%(msecs)03d\t%(levelname)-12s\t%(name)s.%(funcName)-25s %(msg)s", datefmt="%Y-%m-%d %H:%M:%S")
		self.plugin_file_handler.setFormatter(logging_format_string)

		# determine what the user has set for the debug level; this will determine how we set
		# the python logging to show in the event log
		try:
			self.debugLevel = int(plugin_prefs.get("debugLevel", DEBUGLEVEL_NONE))
			if self.debugLevel < 0 or self.debugLevel > 2:
				self.debugLevel = DEBUGLEVEL_NONE
		except:
			self.debugLevel = DEBUGLEVEL_NONE

		# set up the logging level of the INDIGO logging handler to the selected level
		if self.debugLevel == DEBUGLEVEL_LOW:
			self.indigo_log_handler.setLevel(logging.DEBUG)
		elif self.debugLevel == DEBUGLEVEL_HIGH:
			self.indigo_log_handler.setLevel(logging.THREADDEBUG)
		else:
			self.indigo_log_handler.setLevel(logging.INFO)

		# show the debug message since we are in the middle of initializing the plugin base class
		self.logger.threaddebug("Initializing RPFrameworkPlugin")

		# create the generic device dictionary which will store a reference to each device that
		# is defined in indigo; the ID mapping will map the deviceTypeId to a class name
		self.managed_devices           = dict()
		self.managed_dev_class_module  = managed_device_class_module
		self.managed_dev_class_mapping = dict()
		self.managed_dev_params        = dict()
		self.managed_dev_gui_configs   = dict()

		# create a list of actions that are known to the base plugin (these will be processed
		# automatically when possible by the base classes alone)
		self.indigo_actions            = dict()
		self.device_response_defns     = dict()

		# the plugin defines the Events processing so that we can handle the update trigger,
		# if it exists
		self.indigo_events = dict()

		# this list stores a list of enumerated devices for those devices which support
		# enumeration via uPNP
		self.enumerated_devices      = []
		self.last_device_enumeration = time.time() - 9999

		# create the command queue that will be used at the device level
		self.plugin_command_queue = Queue.Queue()

		# create plugin-level configuration variables
		self.plugin_config_params = []

		# parse the RPFramework plugin configuration XML provided for this plugin,
		# if it is present
		self.parse_framework_config(plugin_display_name.replace(" Plugin", ""))

		# perform any upgrade steps if the plugin is running for the first time after
		# an upgrade
		old_plugin_version = plugin_prefs.get("loadedPluginVersion", "")
		if old_plugin_version != to_unicode(plugin_version):
			self.perform_plugin_upgrade_maintenance(old_plugin_version, to_unicode(plugin_version))

		# initialization is complete...
		self.plugin_initializing = False

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will parse the RPFrameworkConfig.xml file that is present in the
	# plugin's directory, if it is present
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def parse_framework_config(self, plugin_name):
		plugin_base_path   = os.getcwd()
		plugin_config_path = os.path.join(plugin_base_path, "RPFrameworkConfig.xml")

		if os.path.exists(plugin_config_path):
			self.logger.debug("Beginning processing of RPFrameworkConfig.xml file")
			try:
				# read in the XML using the XML ElementTree implementation/module
				config_dom         = xml.etree.ElementTree.parse(plugin_config_path)
				plugin_config_node = config_dom.getroot().find("pluginConfig")

				# read in any plugin-level parameter definitions
				plugin_param_node = plugin_config_node.find("pluginParams")
				if plugin_param_node is not None:
					for pluginParam in plugin_param_node:
						rp_plugin_param = self.read_indigo_param_node(pluginParam)
						self.plugin_config_params.append(rp_plugin_param)
						self.logger.threaddebug(f"Found plugin param: {rp_plugin_param.indigo_id}")

				# read in any plugin-level guiConfigSettings
				plugin_gui_config_node = plugin_config_node.find("guiConfiguration")
				if plugin_gui_config_node is not None:
					for gui_setting in plugin_gui_config_node:
						self.logger.threaddebug(f"Found plugin setting: {gui_setting.tag} = {gui_setting.text}")
						self.put_gui_config_value(GUI_CONFIG_PLUGINSETTINGS, gui_setting.tag, gui_setting.text)

				# determine if any device mappings are present
				device_mappings = plugin_config_node.find("deviceMapping")
				if device_mappings is not None:
					for deviceMapping in device_mappings.findall("device"):
						indigo_id  = to_unicode(deviceMapping.get("indigoId"))
						class_name = to_unicode(deviceMapping.get("className"))
						self.managed_dev_class_mapping[indigo_id] = class_name
						self.logger.threaddebug(f"Found device mapping; id: {indigo_id} to class: {class_name}")
				else:
					self.logger.threaddebug("No device mappings found")

				# read in any device definition information such as device properties for
				# validation and retrieval
				devices_node = plugin_config_node.find("devices")
				if devices_node is not None:
					for deviceDfn in devices_node.findall("device"):
						indigo_device_id = to_unicode(deviceDfn.get("indigoId"))

						# process all the parameters for this device
						device_params_node = deviceDfn.find("params")
						if device_params_node is not None:
							params_list = list()
							for device_param in device_params_node.findall("param"):
								rp_dev_param = self.read_indigo_param_node(device_param)
								self.logger.threaddebug(f"Created device parameter for managed device '{indigo_device_id}': {rp_dev_param.indigo_id}")
								params_list.append(rp_dev_param)
							self.managed_dev_params[indigo_device_id] = params_list

						# process any GUI configurations -- these are settings that affect how the
						# plugin appears to Indigo users
						gui_config_node = deviceDfn.find("guiConfiguration")
						if gui_config_node is not None:
							for gui_setting in gui_config_node:
								self.logger.threaddebug(f"Found device setting: {gui_setting.tag}={gui_setting.text}")
								self.put_gui_config_value(indigo_device_id, gui_setting.tag, gui_setting.text)

						# process any device response definitions... these define what the plugin will do
						# when a response is received from the device (definition is agnostic of type of device,
						# though they may be handled differently in code)
						device_responses_node = deviceDfn.find("deviceResponses")
						if device_responses_node is not None:
							for devResponse in device_responses_node.findall("response"):
								response_id            = to_unicode(devResponse.get("id"))
								response_to_action_id  = to_unicode(devResponse.get("respondToActionId"))
								criteria_format_string = to_unicode(devResponse.find("criteriaFormatString").text)
								match_expression       = to_unicode(devResponse.find("matchExpression").text)
								self.logger.threaddebug(f"Found device response: {response_id}")

								# create the object so that effects may be added from child nodes
								dev_response_defn = RPFrameworkDeviceResponse(response_id, criteria_format_string, match_expression, response_to_action_id)

								# add in any effects that are defined
								effects_list_node = devResponse.find("effects")
								if effects_list_node is not None:
									for effectDefn in effects_list_node.findall("effect"):
										effect_type         = eval(f"RPFrameworkDeviceResponse.{effectDefn.get('effectType')}")
										effect_update_param = to_unicode(effectDefn.find("updateParam").text)
										effect_value_format = to_unicode(effectDefn.find("updateValueFormat").text)

										effect_value_format_ex_val  = ""
										effect_value_format_ex_node = effectDefn.find("updateValueExFormat")
										if effect_value_format_ex_node is not None:
											effect_value_format_ex_val = to_unicode(effect_value_format_ex_node.text)

										effect_value_eval_result = to_unicode(effectDefn.get("evalResult")).lower() == "true"

										effect_exec_condition      = ""
										effect_exec_condition_node = effectDefn.find("updateExecCondition")
										if effect_exec_condition_node is not None:
											effect_exec_condition = to_unicode(effect_exec_condition_node.text)

										self.logger.threaddebug(f"Found response effect: Type={effect_type}; Param: {effect_update_param}; ValueFormat={effect_value_format}; ValueFormatEx={effect_value_format_ex_val}; Eval={effect_value_eval_result}; Condition={effect_exec_condition}")
										dev_response_defn.add_response_effect(RPFrameworkDeviceResponseEffect(effect_type, effect_update_param, effect_value_format, effect_value_format_ex_val, effect_value_eval_result, effect_exec_condition))

								# add the definition to the plugin's list of response definitions
								self.add_device_response_definition(indigo_device_id, dev_response_defn)

				# attempt to read any actions that will be automatically processed by
				# the framework
				managed_actions = plugin_config_node.find("actions")
				if managed_actions is not None:
					for managedAction in managed_actions.findall("action"):
						indigo_action_id = to_unicode(managedAction.get("indigoId"))
						rp_action        = RPFrameworkIndigoActionDfn(indigo_action_id)
						self.logger.threaddebug(f"Found managed action: {indigo_action_id}")

						# process/add in the commands for this action
						command_list_node = managedAction.find("commands")
						if command_list_node is not None:
							for commandDefn in command_list_node.findall("command"):
								command_name_node          = commandDefn.find("commandName")
								command_format_string_node = commandDefn.find("commandFormat")

								command_execute_condition      = ""
								command_execute_condition_node = commandDefn.find("commandExecCondition")
								if command_execute_condition_node is not None:
									command_execute_condition = to_unicode(command_execute_condition_node.text)

								command_repeat_count      = ""
								command_repeat_count_node = commandDefn.find("commandRepeatCount")
								if command_repeat_count_node is not None:
									command_repeat_count = to_unicode(command_repeat_count_node.text)

								command_repeat_delay      = ""
								command_repeat_delay_node = commandDefn.find("commandRepeatDelay")
								if command_repeat_delay_node is not None:
									command_repeat_delay = to_unicode(command_repeat_delay_node.text)

								rp_action.addIndigoCommand(to_unicode(command_name_node.text), to_unicode(command_format_string_node.text), command_repeat_count, command_repeat_delay, command_execute_condition)

						params_node = managedAction.find("params")
						if params_node is not None:
							self.logger.threaddebug(f"Processing {len(params_node)} params for action")
							for actionParam in params_node.findall("param"):
								rp_param = self.read_indigo_param_node(actionParam)
								self.logger.threaddebug(f"Created parameter for managed action '{rp_action.indigoActionId}': {rp_param.indigo_id}")
								rp_action.addIndigoParameter(rp_param)
						self.add_indigo_action(rp_action)
				self.logger.debug("Successfully completed processing of RPFrameworkConfig.xml file")
			except Exception as err:
				self.logger.error(f"Plugin Config: Error reading RPFrameworkConfig.xml file at: {plugin_config_path}\n{err}")
		else:
			self.logger.warning(f"RPFrameworkConfig.xml not found at {plugin_config_path}, skipping processing")

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will read in a parameter definition from the given XML node, returning
	# a RPFrameworkIndigoParam object fully filled in from the node
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def read_indigo_param_node(self, param_node):
		param_indigo_id   = to_unicode(param_node.get("indigoId"))
		param_type        = eval(f"RPFrameworkIndigoParamDefn.{param_node.get('paramType')}")
		param_is_required = (param_node.get("isRequired").lower() == "true")
		rp_param          = RPFrameworkIndigoParamDefn(param_indigo_id, param_type, is_required=param_is_required)

		min_value_node = param_node.find("minValue")
		if min_value_node is not None:
			min_value_string = min_value_node.text
			if rp_param.param_type == RPFrameworkIndigoParamDefn.ParamTypeFloat:
				rp_param.min_value = float(min_value_string)
			else:
				rp_param.min_value = int(min_value_string)

		max_value_node = param_node.find("maxValue")
		if max_value_node is not None:
			max_value_string = max_value_node.text
			if rp_param.param_type == RPFrameworkIndigoParamDefn.ParamTypeFloat:
				rp_param.max_value = float(max_value_string)
			else:
				rp_param.max_value = int(max_value_string)

		validation_expression_node = param_node.find("validationExpression")
		if validation_expression_node is not None:
			rp_param.validation_expression = to_unicode(validation_expression_node.text)

		default_value_node = param_node.find("defaultValue")
		if default_value_node is not None:
			if rp_param.param_type == RPFrameworkIndigoParamDefn.ParamTypeFloat:
				rp_param.default_value = float(default_value_node.text)
			elif rp_param.param_type == RPFrameworkIndigoParamDefn.ParamTypeInteger:
				rp_param.default_value = int(default_value_node.text)
			elif rp_param.param_type == RPFrameworkIndigoParamDefn.ParamTypeBoolean:
				rp_param.default_value = (default_value_node.text.lower() == "true")
			else:
				rp_param.default_value = default_value_node.text

		invalid_message_node = param_node.find("invalidValueMessage")
		if invalid_message_node is not None:
			rp_param.invalid_value_message = to_unicode(invalid_message_node.text)

		return rp_param

	# endregion
	#######################################################################################

	#######################################################################################
	# region Indigo control methods
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# startup is called by Indigo whenever the plugin is first starting up (by a restart
	# of Indigo server or the plugin or an update
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def startup(self):
		pass

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# shutdown is called by Indigo whenever the entire plugin is being shut down from
	# being disabled, during an update process or if the server is being shut down
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def shutdown(self):
		pass

	# endregion
	#######################################################################################

	#######################################################################################
	# region Indigo device life-cycle call-back routines
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called whenever the plugin should be connecting / communicating with
	# the physical device... here is where we will begin tracking the device as well
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def deviceStartComm(self, dev):
		self.logger.debug(f"Entering deviceStartComm for {dev.name}; ID={dev.id}")

		# create the plugin device object and add it to the managed list
		new_device_object             = self.create_device_object(dev)
		self.managed_devices[dev.id]   = new_device_object
		new_device_object.initiate_communications()

		# this object may be a child object... if it is then we need to see if its
		# parent has already been created (and if so add it to that parent)
		is_child_device_type = self.get_gui_config_value(dev.deviceTypeId, GUI_CONFIG_ISCHILDDEVICEID, "false").lower() == "true"
		if is_child_device_type:
			self.logger.threaddebug("Device is child object, attempting to find parent")
			parent_device_id = int(dev.pluginProps[self.get_gui_config_value(dev.deviceTypeId, GUI_CONFIG_PARENTDEVICEIDPROPERTYNAME, "")])
			self.logger.threaddebug(f"Found parent ID of device {dev.id}: {parent_device_id}")
			if parent_device_id in self.managed_devices:
				self.logger.threaddebug("Parent object found, adding this child device now")
				self.managed_devices[parent_device_id].add_child_device(new_device_object)

		# this object could be a parent object whose children have already been created; we need to add those children
		# to this parent object now
		for found_device_id in self.managed_devices:
			found_device = self.managed_devices[found_device_id]
			if self.get_gui_config_value(found_device.indigoDevice.deviceTypeId, GUI_CONFIG_ISCHILDDEVICEID, "false").lower() == "true" and int(found_device.indigoDevice.pluginProps[self.get_gui_config_value(found_device.indigoDevice.deviceTypeId, GUI_CONFIG_PARENTDEVICEIDPROPERTYNAME, "")]) == dev.id:
				self.logger.threaddebug(f"Found previously-created child object for parent; child ID: {found_device.indigoDevice.id}")
				new_device_object.add_child_device(found_device)

		self.logger.debug(f"Exiting deviceStartComm for {dev.name}")

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine must be implemented in ancestor classes in order to return the device
	# object that is to be created/managed
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def create_unmanaged_device_object(self, device):
		raise "create_unmanaged_device_object not implemented"
	def create_device_object(self, device):
		if not (self.managed_dev_class_module is None) and device.deviceTypeId in self.managed_dev_class_mapping:
			device_class = getattr(self.managed_dev_class_module, self.managed_dev_class_mapping[device.deviceTypeId])
			return device_class(self, device)
		else:
			return self.create_unmanaged_device_object(device)

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called whenever the plugin should cease communicating with the
	# hardware, breaking the connection
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def deviceStopComm(self, dev):
		self.logger.debug(f"Entering deviceStopComm for {dev.name}; ID={dev.id}")

		# dequeue any pending reconnection attempts...

		# first remove the device from the parent if this is a child device...
		is_child_device_type = self.get_gui_config_value(dev.deviceTypeId, GUI_CONFIG_ISCHILDDEVICEID, "false").lower() == "true"
		if is_child_device_type:
			self.logger.threaddebug("Device is child object, attempting to remove from parent...")
			parent_device_id = int(dev.pluginProps[self.get_gui_config_value(dev.deviceTypeId, GUI_CONFIG_PARENTDEVICEIDPROPERTYNAME, "")])
			if parent_device_id in self.managed_devices:
				self.logger.threaddebug(f"Removing device from parent ID: {parent_device_id}")
				self.managed_devices[parent_device_id].remove_child_device(self.managed_devices[dev.id])

		# remove the primary managed object
		self.managed_devices[dev.id].terminate_communications()
		del self.managed_devices[dev.id]

		self.logger.debug(f"Exiting deviceStopComm for {dev.name}")

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called whenever the server is defining an event / trigger setup
	# by the user
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def triggerStartProcessing(self, trigger):
		self.logger.threaddebug(f"Registering trigger: {trigger.id}")

		# if the descendent class does not handle the trigger then we process it by
		# storing it against the trigger type
		if not self.registerCustomTrigger(trigger):
			trigger_type = trigger.pluginTypeId
			if not (trigger_type in self.indigo_events):
				self.indigo_events[trigger_type] = dict()
			self.indigo_events[trigger_type][trigger.id] = trigger

		self.logger.debug(f"Registered trigger: {trigger.id}")

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine gives descendant plugins the chance to process the event
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def registerCustomTrigger(self, trigger):
		return False

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called whenever the server is un-registering a trigger
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def triggerStopProcessing(self, trigger):
		self.logger.threaddebug(f"Stopping trigger: {trigger.id}")

		# if the descendent class does not handle the de-registration then we process it by
		# removing it from the dictionary
		if not self.registerCustomTrigger(trigger):
			trigger_type = trigger.pluginTypeId
			if trigger_type in self.indigo_events:
				if trigger.id in self.indigo_events[trigger_type]:
					del self.indigo_events[trigger_type][trigger.id]

		self.logger.debug(f"Stopped trigger: {trigger.id}")

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine gives descendant plugins the chance to unregister the event
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def unRegisterCustomTrigger(self, trigger):
		return False

	# endregion
	#######################################################################################

	#######################################################################################
	# region Asynchronous processing routines
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will run the concurrent processing thread used at the plugin (not
	# device) level - such things as update checks and device reconnections
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def runConcurrentThread(self):
		try:
			# read in any configuration values necessary...
			empty_queue_thread_sleep_time = float(self.get_gui_config_value(GUI_CONFIG_PLUGINSETTINGS, GUI_CONFIG_PLUGIN_COMMANDQUEUEIDLESLEEP, u'20'))

			while True:
				# process pending commands now...
				re_queue_commands_list = list()
				while not self.plugin_command_queue.empty():
					len_queue = self.plugin_command_queue.qsize()
					self.logger.threaddebug(f"Plugin Command queue has {len_queue} command(s) waiting")

					# the command name will identify what action should be taken...
					re_queue_command = False
					command = self.plugin_command_queue.get()
					if command.command_name == RPFrameworkCommand.CMD_DEVICE_RECONNECT:
						# the command payload will be in the form of a tuple:
						# (DeviceID, DeviceInstanceIdentifier, ReconnectTime)
						# ReconnectTime is the datetime where the next reconnection attempt should occur
						time_now = time.time()
						if time_now > command.command_payload[2]:
							if command.command_payload[0] in self.managed_devices:
								if self.managed_devices[command.command_payload[0]].device_instance_identifier == command.command_payload[1]:
									self.logger.debug(f"Attempting reconnection to device {command.command_payload[0]}")
									self.managed_devices[command.command_payload[0]].initiate_communications()
								else:
									self.logger.threaddebug(f"Ignoring reconnection command for device {command.command_payload[0]}; new instance detected")
							else:
								self.logger.debug(f"Ignoring reconnection command for device {command.command_payload[0]}; device not created")
						else:
							re_queue_command = True

					elif command.command_name == RPFrameworkCommand.CMD_DEBUG_LOGUPNPDEVICES:
						# kick off the UPnP discovery and logging now
						self.log_upnp_devices_found_processing()

					else:
						# allow a base class to process the command
						self.handle_unknown_plugin_command(command, re_queue_commands_list)

					# complete the de-queuing of the command, allowing the next
					# command in queue to rise to the top
					self.plugin_command_queue.task_done()
					if re_queue_command:
						self.logger.threaddebug("Plugin command queue not yet ready; re-queuing for future execution")
						re_queue_commands_list.append(command)

				# any commands that did not yet execute should be placed back into the queue
				for command_to_requeue in re_queue_commands_list:
					self.plugin_command_queue.put(command_to_requeue)

				# sleep on an empty queue... note that this should not normally be as granular
				# as a device's communications! (value is in seconds)
				self.sleep(empty_queue_thread_sleep_time)

		except self.StopThread:
			# this exception is simply shutting down the thread... there is nothing
			# that we need to process
			pass

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will be called to handle any unknown commands at the plugin level; it
	# can/should be overridden in the plugin implementation (if needed)
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def handle_unknown_plugin_command(self, rp_command, requeue_commands_list):
		pass

	# endregion
	#######################################################################################

	#######################################################################################
	# region Indigo definitions helper functions
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will add a new action to the managed actions of the plugin
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def add_indigo_action(self, indigo_action):
		self.indigo_actions[indigo_action.indigoActionId] = indigo_action

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will add a new device response to the list of responses that the plugin
	# can automatically handle
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def add_device_response_definition(self, device_type_id, response_dfn):
		if not (device_type_id in self.device_response_defns):
			self.device_response_defns[device_type_id] = list()
		self.device_response_defns[device_type_id].append(response_dfn)

	# endregion
	#######################################################################################

	#######################################################################################
	# region Data Validation Functions
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will be called to validate the information entered into the Plugin
	# configuration file
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def validatePrefsConfigUi(self, valuesDict):
		# create an error message dictionary to hold validation issues foundDevice
		error_messages = indigo.Dict()

		# check each defined parameter, if any exist...
		for param in self.plugin_config_params:
			if param.indigo_id in valuesDict:
				# a value is present for this parameter - validate it
				if not param.is_value_valid(valuesDict[param.indigo_id]):
					error_messages[param.indigo_id] = param.invalid_value_message

		# return the validation results...
		if len(error_messages) == 0:
			return True, valuesDict
		else:
			return False, valuesDict, error_messages

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will be called when the user has closed the preference dialog
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def closedPrefsConfigUi(self, valuesDict, userCancelled):
		if not userCancelled:
			try:
				self.debugLevel = int(valuesDict.get(u'debugLevel', DEBUGLEVEL_NONE))
			except:
				self.debugLevel = DEBUGLEVEL_NONE

			# set up the logging level of the INDIGO logging handler to the selected level
			if self.debugLevel == DEBUGLEVEL_LOW:
				self.indigo_log_handler.setLevel(logging.DEBUG)
			elif self.debugLevel == DEBUGLEVEL_HIGH:
				self.indigo_log_handler.setLevel(logging.THREADDEBUG)
			else:
				self.indigo_log_handler.setLevel(logging.INFO)

			self.logger.debug("Plugin preferences updated")
			if self.debugLevel == DEBUGLEVEL_NONE:
				self.logger.info("Debugging disabled")
			else:
				self.logger.info("Debugging enabled... remember to turn off when done!")

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will be called to validate the information entered into the Device
	# configuration GUI from within Indigo (it will only validate registered params)
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def validateDeviceConfigUi(self, valuesDict, device_type_id, devId):
		# create an error message dictionary to hold any validation issues
		# (and their messages) that we find
		error_messages = indigo.Dict()

		# loop through each parameter for this device and validate one-by-one
		if device_type_id in self.managed_dev_params:
			for param in self.managed_dev_params[device_type_id]:
				if param.indigo_id in valuesDict:
					# a parameter value is present, validate it now
					if not param.is_value_valid(valuesDict[param.indigo_id]):
						error_messages[param.indigo_id] = param.invalid_value_message

				elif param.is_required:
					error_messages[param.indigo_id] = param.invalid_value_message

		# return the validation results...
		if len(error_messages) == 0:
			# process any hidden variables that are used to show state information in
			# indigo or as a RPFramework config/storage
			valuesDict["address"] = self.substitute_indigo_values(self.get_gui_config_value(device_type_id, GUI_CONFIG_ADDRESSKEY, ""), None, valuesDict)
			self.logger.threaddebug("Setting address of {devId} to {valuesDict['address']}")

			return self.validateDeviceConfigUiEx(valuesDict, device_type_id, devId)
		else:
			return False, valuesDict, error_messages

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will be called to validate any parameters not known to the plugin (not
	# automatically handled and validated); this will only be called once all known
	# parameters have been validated and it MUST return a valid tuple
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def validateDeviceConfigUiEx(self, valuesDict, deviceTypeId, devId):
		return True, valuesDict

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will validate an action Config UI popup when it is being edited from
	# within the Indigo client; if the action being validated is not a known action then
	# a callback to the plugin implementation will be made
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def validateActionConfigUi(self, valuesDict, typeId, actionId):
		self.logger.threaddebug(f"Call to validate action: {typeId}")
		if typeId in self.indigo_actions:
			action_defn = self.indigo_actions[typeId]
			managed_action_validation = action_defn.validateActionValues(valuesDict)
			if not managed_action_validation[0]:
				self.logger.threaddebug(f"Managed validation failed: {managed_action_validation[1]}{managed_action_validation[2]}")
			return managed_action_validation
		else:
			return self.validateUnRegisteredActionConfigUi(valuesDict, typeId, actionId)

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called to retrieve a dynamic list of elements for an action (or
	# other ConfigUI based) routine
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getConfigDialogMenu(self, filter=u'', valuesDict=None, typeId="", targetId=0):
		# the routine is designed to pass the call along to the device since most of the
		# time this is device-specific (such as inputs)
		self.logger.threaddebug(f"Dynamic menu requested for Device ID: {targetId}")
		if targetId in self.managed_devices:
			return self.managed_devices[targetId].getConfigDialogMenuItems(filter, valuesDict, typeId, targetId)
		else:
			self.logger.debug(f"Call to getConfigDialogMenu for device not managed by this plugin")
			return []

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called to retrieve a dynamic list of devices that are found on the
	# network matching the service given by the filter
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getConfigDialogUPNPDeviceMenu(self, filter=u'', valuesDict=None, typeId=u'', targetId=0):
		self.update_upnp_enumeration_list(typeId)
		return self.parse_upnp_device_list(self.enumerated_devices)

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called whenever the user clicks the "Select" button on a device
	# dialog that asks for selecting from an list of enumerated devices
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def selectUPNPEnumeratedDeviceForUse(self, valuesDict, typeId, devId):
		menu_field_id   = self.get_gui_config_value(typeId, GUI_CONFIG_UPNP_ENUMDEVICESFIELDID, "upnpEnumeratedDevices")
		target_field_id = self.get_gui_config_value(typeId, GUI_CONFIG_UPNP_DEVICESELECTTARGETFIELDID, "httpAddress")
		if valuesDict[menu_field_id] != "":
			# the target field may be just the address or may be broken up into multiple parts, separated
			# by a colon (in which case the menu ID value must match!)
			fields_to_update = target_field_id.split(u':')
			values_selected  = valuesDict[menu_field_id].split(u':')

			field_idx = 0
			for field in fields_to_update:
				valuesDict[field] = values_selected[field_idx]
				field_idx += 1

		return valuesDict

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called to parse out a uPNP search results list in order to create_device_object
	# an indigo-friendly menu; usually will be overridden in plugin descendants
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def parse_upnp_device_list(self, deviceList):
		try:
			menu_items = []
			for network_device in deviceList:
				self.logger.threaddebug(f"Found uPnP Device: {network_device}")
				menu_items.append((network_device.location, network_device.server))
			return menu_items
		except:
			self.logger.warning("Error parsing UPNP devices found on the network")
			return []

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine should be overridden and should validate any actions which are not
	# already defined within the plugin class
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def validateUnRegisteredActionConfigUi(self, valuesDict, typeId, actionId):
		return True, valuesDict

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will validate whether or not an IP address is valid as a IPv4 addr
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def is_ip_v4_valid(self, ip):
		# Make sure a value was entered for the address... an IPv4 should require at least
		# 7 characters (0.0.0.0)
		ip = to_unicode(ip)
		if len(ip) < 7:
			return False

		# separate the IP address into its components... this limits the format for the
		# user input but is using a fairly standard notation so acceptable
		address_parts = ip.split(u'.')
		if len(address_parts) != 4:
			return False

		for part in address_parts:
			try:
				part = int(part)
				if part < 0 or part > 255:
					return False
			except ValueError:
				return False

		# if we make it here, the input should be valid
		return True

	# endregion
	#######################################################################################

	#######################################################################################
	# region Action Execution Routines
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will do the work of processing/executing an action; it is assumed that
	# the plugin developer will only assign the action callback to this routine if it
	# should be handled
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def execute_action(self, pluginAction, indigoActionId="", indigoDeviceId="", paramValues=None):
		# ensure that the actionID specified by the action is a managed action that
		# we can automatically handle
		if pluginAction is not None:
			indigoActionId = pluginAction.pluginTypeId
			indigoDeviceId = pluginAction.deviceId
			paramValues    = pluginAction.props

		# ensure that action and device are both managed... if so they will each appear in
		# the respective member variable dictionaries
		if indigoActionId not in self.indigo_actions:
			self.logger.error(f"Execute action called for non-managed action id: {indigoActionId}")
			return
		if indigoDeviceId not in self.managed_devices:
			self.logger.error(f"Execute action called for non-managed device id: {indigoDeviceId}")
			return

		# if execution made it this far then we have the action & device and can execute
		# that action now...
		self.indigo_actions[indigoActionId].generateActionCommands(self, self.managed_devices[indigoDeviceId], paramValues)

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will toggled the debug setting on all devices managed... it is used to
	# allow setting the debug status w/o restarting the plugin
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def toggle_debug_enabled(self):
		if self.debugLevel == DEBUGLEVEL_NONE:
			self.debugLevel = DEBUGLEVEL_LOW
			self.indigo_log_handler.setLevel(logging.DEBUG)
			self.pluginPrefs["debugLevel"] = DEBUGLEVEL_LOW
			self.logger.info("Debug enabled (on Low) by user")
		else:
			self.debugLevel = DEBUGLEVEL_NONE
			self.indigo_log_handler.setLevel(logging.INFO)
			self.pluginPrefs["debugLevel"] = DEBUGLEVEL_NONE
			self.logger.info("Debug disabled by user")
		self.savePluginPrefs()

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will be called when the user has created a request to log the UPnP
	# debug information to the Indigo log
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def log_upnp_devices_found(self, valuesDict, typeId):
		# perform validation here... only real requirement is to have a "type" selected
		# and this should always be the case...
		errors_dict = indigo.Dict()

		# add a new command to the plugin's command queue for processing on a background
		# thread (required to avoid Indigo timing out the operation!)
		self.plugin_command_queue.put(RPFrameworkCommand.RPFrameworkCommand(RPFrameworkCommand.CMD_DEBUG_LOGUPNPDEVICES, commandPayload=None))
		self.logger.info("Scheduled UPnP Device Search")

		# return to the dialog to allow it to close
		return True, valuesDict, errors_dict

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine processing the logging of the UPnP devices once the plugin spools the
	# command on the background thread
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def log_upnp_devices_found_processing(self):
		try:
			# perform the UPnP search and logging now...
			self.logger.debug("Beginning UPnP Device Search")
			service_target         = "ssdp:all"
			discovery_started      = time.time()
			discovered_device_list = uPnPDiscover(service_target, timeout=6)

			# create an HTML file that contains the details for all the devices found on the network
			self.logger.debug("UPnP Device Search completed... creating output HTML")
			device_html  = '<html><head><title>UPnP Devices Found</title><style type="text/css">html,body { margin: 0px; padding: 0px; width: 100%; height: 100%; }\n.upnpDevice { margin: 10px 0px 8px 5px; border-bottom: solid 1px #505050; }\n.fieldLabel { width: 140px; display: inline-block; }</style></head><body>'
			device_html += "<div style='background-color: #3f51b5; width: 100%; height: 50px; border-bottom: solid 2px black;'><span style='color: #a1c057; font-size: 25px; font-weight: bold; line-height: 49px; padding-left: 3px;'>RogueProeliator's RPFramework UPnP Discovery Report</span></div>"
			device_html += "<div style='border-bottom: solid 2px black; padding: 8px 3px;'><span class='fieldLabel'><b>Requesting Plugin:</b></span>" + self.pluginDisplayName + u"<br /><span class='fieldLabel'><b>Service Query:</b></span>" + service_target + u"<br /><span class='fieldLabel'><b>Date Run:</b></span>" + to_unicode(discovery_started) + "</div>"

			# loop through each device found...
			for device in discovered_device_list:
				device_html += f"<div class='upnpDevice'><span class='fieldLabel'>Location:</span><a href='{device.location}' target='_blank'>{device.location}</a><br /><span class='fieldLabel'>USN:</span>{device.usn}<br /><span class='fieldLabel'>ST:</span>{device.st}<br /><span class='fieldLabel'>Cache Time:</span>{device.cache}s"
				for header in device.allHeaders:
					header_key = to_unicode(header[0])
					if header_key != "location" and header_key != "usn" and header_key != "cache-control" and header_key != "st" and header_key != "ext":
						device_html += f"<br /><span class='fieldLabel'>{header[0]}:</span>{header[1]}"
				device_html += "</div>"

			device_html += "</body></html>"

			# write out the file...
			self.logger.threaddebug("Writing UPnP Device Search HTML to file")
			temp_filename          = self.get_plugin_directory_file_path("tmpUPnPDiscoveryResults.html")
			upnp_results_html_file = open(temp_filename, 'w')
			upnp_results_html_file.write(to_str(device_html))
			upnp_results_html_file.close()

			# launch the file in a browser window via the command line
			call(["open", temp_filename])
			self.logger.info(f"Created UPnP results temporary file at {temp_filename}")
		except:
			self.logger.error("Error generating UPnP report")

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will be called whenever the user has chosen to dump the device details
	# to the event log via the menuitem action
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def dump_device_details_to_log(self, valuesDict, typeId):
		errors_dict     = indigo.Dict()
		devices_to_dump = valuesDict.get("devicesToDump", None)

		if devices_to_dump is None or len(devices_to_dump) == 0:
			errors_dict["devicesToDump"] = "Please select one or more devices"
			return False, valuesDict, errors_dict
		else:
			for device_id in devices_to_dump:
				self.logger.info(f"Dumping details for DeviceID: {device_id}")
				dump_dev = indigo.devices[int(device_id)]
				self.logger.info(to_unicode(dump_dev))
			return True, valuesDict, errors_dict

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine provides the callback for devices based off a Dimmer... since the call
	# comes into the plugin we will pass it off the device now
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def actionControlDimmerRelay(self, action, dev):
		# transform this action into our standard "execute_action" parameters so that the
		# action is processed in a standard way
		indigo_action_id = f"{action.deviceAction}"
		if indigo_action_id == "11":
			indigo_action_id = "StatusRequest"

		indigo_device_id = dev.id
		param_values     = dict()
		param_values["actionValue"] = f"{action.actionValue}"
		self.logger.debug(f"Dimmer Command: ActionId={indigo_action_id}; Device={indigo_device_id}; actionValue={param_values['actionValue']}")

		self.execute_action(None, indigo_action_id, indigo_device_id, param_values)

	# endregion
	#######################################################################################

	#######################################################################################
	# region Helper Routines
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will perform a substitution on a string for all Indigo-values that
	# may be substituted (variables, devices, states, parameters, etc.)
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def substitute_indigo_values(self, input_str, rp_device, action_param_values):
		substituted_string = input_str
		if substituted_string is None:
			substituted_string = ""

		# substitute each parameter value called for in the string; this is done first so that
		# the parameter could call for a substitution
		ap_matcher = re.compile(r'%ap:([a-z\d]+)%', re.IGNORECASE)
		for match in ap_matcher.finditer(substituted_string):
			substituted_string = substituted_string.replace(f"{match.group(0)}", f"{action_param_values[match.group(1)]}")

		# substitute device properties since the substitute method below handles states...
		dp_matcher = re.compile(r'%dp:([a-z\d]+)%', re.IGNORECASE)
		for match in dp_matcher.finditer(substituted_string):
			if type(rp_device.indigoDevice.pluginProps.get(match.group(1), None)) is indigo.List:
				substituted_string = substituted_string.replace(f"{match.group(0)}", "'" + ','.join(rp_device.indigoDevice.pluginProps.get(match.group(1))) + "'")
			else:
				substituted_string = substituted_string.replace(f"{match.group(0)}", f"{rp_device.indigoDevice.pluginProps.get(match.group(1), '')}")

		# handle device states for any where we do not specify a device id
		ds_matcher = re.compile(r'%ds:([a-z\d]+)%', re.IGNORECASE)
		for match in ds_matcher.finditer(substituted_string):
			substituted_string = substituted_string.replace(f"{match.group(0)}", f"{rp_device.indigoDevice.states.get(match.group(1), '')}")

		# handle parent device properties (for child devices)
		if rp_device is not None:
			if self.get_gui_config_value(rp_device.indigoDevice.deviceTypeId, GUI_CONFIG_ISCHILDDEVICEID, "false").lower() == "true":
				parent_device_id = int(rp_device.indigoDevice.pluginProps[self.get_gui_config_value(rp_device.indigoDevice.deviceTypeId, GUI_CONFIG_PARENTDEVICEIDPROPERTYNAME, "")])
				if parent_device_id in self.managed_devices:
					parent_rp_device = self.managed_devices[parent_device_id]
					pdp_matcher = re.compile(r'%pdp:([a-z\d]+)%', re.IGNORECASE)
					for match in pdp_matcher.finditer(substituted_string):
						if type(parent_rp_device.indigoDevice.pluginProps.get(match.group(1), None)) is indigo.List:
							substituted_string = substituted_string.replace(f"{match.group(0)}", "'" + ','.join(parent_rp_device.indigoDevice.pluginProps.get(match.group(1))) + "'")
						else:
							substituted_string = substituted_string.replace(f"{match.group(0)}", f"{parent_rp_device.indigoDevice.pluginProps.get(match.group(1), '')}")

		# handle plugin preferences
		pp_matcher = re.compile(r'%pp:([a-z\d]+)%', re.IGNORECASE)
		for match in pp_matcher.finditer(substituted_string):
			substituted_string = substituted_string.replace(f"{match.group(0)}", f"{self.pluginPrefs.get(match.group(1), u'')}")

		# perform the standard indigo values substitution...
		substituted_string = self.substitute(substituted_string)

		# return the new string to the caller
		return substituted_string

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will set a GUI configuration value given the device type, the key and
	# the value for the device
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def put_gui_config_value(self, device_type_id, config_key, config_value):
		if device_type_id not in self.managed_dev_gui_configs:
			self.managed_dev_gui_configs[device_type_id] = dict()
		self.managed_dev_gui_configs[device_type_id][config_key] = config_value

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will retrieve a GUI config value for a device type and key; it allows
	# passing in a default value in case the value is not found in the settings
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def get_gui_config_value(self, device_type_id, config_key, default_value=""):
		if device_type_id not in self.managed_dev_gui_configs:
			return default_value
		elif config_key in self.managed_dev_gui_configs[device_type_id]:
			return self.managed_dev_gui_configs[device_type_id][config_key]
		else:
			self.logger.threaddebug(f"Returning default GUIConfigValue for {device_type_id}: {config_key}")
			return default_value

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will retrieve the list of device response definitions for the given
	# device type
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def get_device_response_definitions(self, device_type_id):
		if device_type_id in self.device_response_defns:
			return self.device_response_defns[device_type_id]
		else:
			return ()

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will update the enumeratedDevices list of devices from the uPNP
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def update_upnp_enumeration_list(self, device_type_id):
		u_pnp_cache_time = int(self.get_gui_config_value(device_type_id, GUI_CONFIG_UPNP_CACHETIMESEC, "180"))
		if time.time() > self.last_device_enumeration + u_pnp_cache_time or len(self.enumerated_devices) == 0:
			service_id = self.get_gui_config_value(device_type_id, GUI_CONFIG_UPNP_SERVICE, "ssdp:all")
			self.logger.debug(f"Performing uPnP search for: {service_id}")
			discovered_devices = uPnPDiscover(service_id)
			self.logger.debug(f"Found {len(discovered_devices)} devices")

			self.enumerated_devices     = discovered_devices
			self.last_device_enumeration = time.time()

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will get the full path to a file with the given name inside the plugin
	# directory; note this is specifically returning a string, not unicode, to allow
	# use of the IO libraries which require ascii
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def get_plugin_directory_file_path(self, file_name, plugin_name=None):
		if plugin_name is None:
			plugin_name = self.pluginDisplayName.replace(" Plugin", "")
		indigo_base_path = indigo.server.getInstallFolderPath()

		requested_file_path = os.path.join(indigo_base_path, f"Plugins/{plugin_name}.indigoPlugin/Contents/Server Plugin/{file_name}")
		return f"{requested_file_path}"

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called whenever the plugin is updating from an older version, as
	# determined by the plugin property and plugin version number
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def perform_plugin_upgrade_maintenance(self, old_version, new_version):
		if old_version == "":
			self.logger.info(f"Performing first upgrade/run of version {new_version}")
		else:
			self.logger.info(f"Performing upgrade from {old_version} to {new_version}")

		# remove any unwanted directories from the RPFramework
		plugin_base_path = os.getcwd()
		remove_paths = 	[	os.path.join(plugin_base_path, "RPFramework/requests"),
							os.path.join(plugin_base_path, "RPFramework/dataAccess")]
		for removePath in remove_paths:
			try:
				if os.path.isdir(removePath):
					self.logger.debug(f"Removing unused directory tree at {removePath}")
					shutil.rmtree(removePath)
				elif os.path.isfile(removePath):
					os.remove(removePath)
			except:
				self.logger.error(f"Failed to remove path during upgrade: {removePath}")

		# allow the descendant classes to perform their own upgrade options
		self.perform_plugin_upgrade(old_version, new_version)

		# update the version flag within our plugin
		self.pluginPrefs["loadedPluginVersion"] = new_version
		self.savePluginPrefs()
		self.logger.info(f"Completed plugin updating/installation for {new_version}")

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine may be used by plugins to perform any upgrades specific to the plugin;
	# it will be called following the framework's update processing
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def perform_plugin_upgrade(self, old_version, new_version):
		pass

	# endregion
	#######################################################################################
