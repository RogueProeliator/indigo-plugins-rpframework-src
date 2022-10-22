#! /usr/bin/env python
# -*- coding: utf-8 -*-
<<<<<<< HEAD

#/////////////////////////////////////////////////////////////////////////////////////////
=======
# /////////////////////////////////////////////////////////////////////////////////////////
# /////////////////////////////////////////////////////////////////////////////////////////
# RPFrameworkPlugin by RogueProeliator <adam.d.ashe@gmail.com>
# 	Base class for all RogueProeliator's plugins for Perceptive Automation's Indigo
#	home automation software.
# /////////////////////////////////////////////////////////////////////////////////////////
# /////////////////////////////////////////////////////////////////////////////////////////

# /////////////////////////////////////////////////////////////////////////////////////////
>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
# region Python Imports
from __future__ import absolute_import
import logging
import os
import queue as Queue
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
#/////////////////////////////////////////////////////////////////////////////////////////

<<<<<<< HEAD
#/////////////////////////////////////////////////////////////////////////////////////////
=======
# /////////////////////////////////////////////////////////////////////////////////////////
>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
# region Constants and configuration variables
GUI_CONFIG_PLUGINSETTINGS                        = u'plugin'
GUI_CONFIG_PLUGIN_COMMANDQUEUEIDLESLEEP          = u'pluginCommandQueueIdleSleep'
GUI_CONFIG_PLUGIN_DEBUG_SHOWUPNPOPTION           = u'showUPnPDebug'
GUI_CONFIG_PLUGIN_DEBUG_UPNPOPTION_SERVICEFILTER = u'UPnPDebugServiceFilter'

GUI_CONFIG_ADDRESSKEY                            = u'deviceAddressFormat'

GUI_CONFIG_UPNP_SERVICE                          = u'deviceUPNPServiceId'
GUI_CONFIG_UPNP_CACHETIMESEC                     = u'deviceUPNPSeachCacheTime'
GUI_CONFIG_UPNP_ENUMDEVICESFIELDID               = u'deviceUPNPDeviceFieldId'
GUI_CONFIG_UPNP_DEVICESELECTTARGETFIELDID        = u'deviceUPNPDeviceSelectedFieldId'

GUI_CONFIG_ISCHILDDEVICEID                       = u'deviceIsChildDevice'
GUI_CONFIG_PARENTDEVICEIDPROPERTYNAME            = u'deviceParentIdProperty'
GUI_CONFIG_CHILDDICTIONARYKEYFORMAT              = u'childDeviceDictionaryKeyFormat'

GUI_CONFIG_RECONNECTIONATTEMPT_LIMIT             = u'reconnectAttemptLimit'
GUI_CONFIG_RECONNECTIONATTEMPT_DELAY             = u'reconnectAttemptDelay'
GUI_CONFIG_RECONNECTIONATTEMPT_SCHEME            = u'reconnectAttemptScheme'
GUI_CONFIG_RECONNECTIONATTEMPT_SCHEME_FIXED      = u'fixed'
GUI_CONFIG_RECONNECTIONATTEMPT_SCHEME_REGRESS    = u'regress'

GUI_CONFIG_DATABASE_CONN_ENABLED                 = u'databaseConnectionEnabled'
GUI_CONFIG_DATABASE_CONN_TYPE                    = u'databaseConnectionType'
GUI_CONFIG_DATABASE_CONN_DBNAME                  = u'databaseConnectionDBName'

DEBUGLEVEL_NONE                                  = 0		# no .debug() logs will be shown in the Indigo log
DEBUGLEVEL_LOW                                   = 1		# show .debug() logs in the Indigo log
DEBUGLEVEL_HIGH                                  = 2		# show .ThreadDebug() log calls in the Indigo log
<<<<<<< HEAD
# endregion
#/////////////////////////////////////////////////////////////////////////////////////////


=======

#endregion
# /////////////////////////////////////////////////////////////////////////////////////////

# /////////////////////////////////////////////////////////////////////////////////////////
# /////////////////////////////////////////////////////////////////////////////////////////
# RPFrameworkPlugin
#	Base class for Indigo plugins that provides standard functionality such as version
#	checking and validation functions
# /////////////////////////////////////////////////////////////////////////////////////////
# /////////////////////////////////////////////////////////////////////////////////////////
>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
class RPFrameworkPlugin(indigo.PluginBase):

	# /////////////////////////////////////////////////////////////////////////////////////
	# region Class construction and destruction methods
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor called once upon plugin class creation; setup the basic functionality
	# common to all plugins based on the framework
<<<<<<< HEAD
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, plugin_id, plugin_display_name, plugin_version, plugin_prefs, managed_device_class_module=None, plugin_supports_upnp=False):
		# flag the plugin as undergoing initialization so that we know the full
		# indigo plugin is not yet available
		self.pluginIsInitializing    = True
		self.pluginSupportsUPNPDebug = plugin_supports_upnp
		
		# call the base class' initialization to begin setup...
		indigo.PluginBase.__init__(self, plugin_id, plugin_display_name, plugin_version, plugin_prefs)
				
		# set up a custom logging format to make it easier to look through (this applies only to the plugin's
		# individual file handler
		logging_format_string = logging.Formatter('%(asctime)s.%(msecs)03d\t%(levelname)-12s\t%(name)s.%(funcName)-25s %(msg)s', datefmt='%Y-%m-%d %H:%M:%S')
		self.plugin_file_handler.setFormatter(logging_format_string)
				
		# determine what the user has set for the debug level; this will determine how we set
		# the python logging to show in the event log
		try:
			self.debugLevel = int(plugin_prefs.get('debugLevel', DEBUGLEVEL_NONE))
=======
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs, daysBetweenUpdateChecks=1, managedDeviceClassModule=None, pluginSupportsUPNP=False):
		# flag the plugin as undergoing initialization so that we know the full
		# indigo plugin is not yet available
		self.pluginIsInitializing    = True
		self.pluginSupportsUPNPDebug = pluginSupportsUPNP

		# call the base class' initialization to begin setup...
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

		# setup a custom logging format to make it easier to look through (this applies only to the plugin's
		# individual file handler
		loggingFormatString = logging.Formatter('%(asctime)s.%(msecs)03d\t%(levelname)-12s\t%(name)s.%(funcName)-25s %(msg)s', datefmt='%Y-%m-%d %H:%M:%S')
		self.plugin_file_handler.setFormatter(loggingFormatString)

		# determine what the user has set for the debug level; this will determine how we set
		# the python logging to show in the event log
		try:
			self.debugLevel = int(pluginPrefs.get("debugLevel", DEBUGLEVEL_NONE))
>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
			if self.debugLevel < 0 or self.debugLevel > 2:
				self.debugLevel = DEBUGLEVEL_NONE
		except:
			self.debugLevel = DEBUGLEVEL_NONE
<<<<<<< HEAD
		
=======

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
		# set up the logging level of the INDIGO logging handler to the selected level
		if self.debugLevel == DEBUGLEVEL_LOW:
			self.indigo_log_handler.setLevel(logging.DEBUG)
		elif self.debugLevel == DEBUGLEVEL_HIGH:
			self.indigo_log_handler.setLevel(logging.THREADDEBUG)
		else:
			self.indigo_log_handler.setLevel(logging.INFO)

		# show the debug message since we are in the middle of initializing the plugin base class
<<<<<<< HEAD
		self.logger.threaddebug('Initializing RPFrameworkPlugin')
		
=======
		self.logger.threaddebug("Initializing RPFrameworkPlugin")

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
		# create the generic device dictionary which will store a reference to each device that
		# is defined in indigo; the ID mapping will map the deviceTypeId to a class name
		self.managedDevices            = dict()
		self.managedDeviceClassModule  = managed_device_class_module
		self.managedDeviceClassMapping = dict()
		self.managedDeviceParams       = dict()
		self.managedDeviceGUIConfigs   = dict()

		# create a list of actions that are known to the base plugin (these will be processed
		# automatically when possible by the base classes alone)
		self.indigoActions             = dict()
		self.deviceResponseDefinitions = dict()

		# the plugin defines the Events processing so that we can handle the update trigger,
		# if it exists
		self.indigoEvents = dict()

		# this list stores a list of enumerated devices for those devices which support
		# enumeration via uPNP
		self.enumeratedDevices     = []
		self.lastDeviceEnumeration = time.time() - 9999

		# create the command queue that will be used at the device level
		self.pluginCommandQueue = Queue.Queue()

		# create plugin-level configuration variables
		self.pluginConfigParams = []

		# parse the RPFramework plugin configuration XML provided for this plugin,
		# if it is present
<<<<<<< HEAD
		self.parseRPFrameworkConfig(plugin_display_name.replace(' Plugin', ''))
		
		# perform any upgrade steps if the plugin is running for the first time after
		# an upgrade
		old_version = plugin_prefs.get('loadedPluginVersion', '')
		if old_version != to_unicode(plugin_version):
			self.performPluginUpgradeMaintenance(old_version, f"{plugin_version}")
		
=======
		self.parseRPFrameworkConfig(pluginDisplayName.replace(" Plugin", ""))

		# perform any upgrade steps if the plugin is running for the first time after
		# an upgrade
		oldPluginVersion = pluginPrefs.get("loadedPluginVersion", "")
		if oldPluginVersion != to_unicode(pluginVersion):
			self.performPluginUpgradeMaintenance(oldPluginVersion, to_unicode(pluginVersion))

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
		# initialization is complete...
		self.pluginIsInitializing = False

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will parse the RPFrameworkConfig.xml file that is present in the
	# plugin's directory, if it is present
<<<<<<< HEAD
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def parseRPFrameworkConfig(self, plugin_name):
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
						rp_plugin_param = self.readIndigoParamNode(pluginParam)
						self.pluginConfigParams.append(rp_plugin_param)
						self.logger.threaddebug(f"Found plugin param: {rp_plugin_param.indigoId}")
				
				# read in any plugin-level guiConfigSettings
				plugin_gui_config_node = plugin_config_node.find("guiConfiguration")
				if plugin_gui_config_node is not None:
					for guiConfigSetting in plugin_gui_config_node:
=======
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def parseRPFrameworkConfig(self, pluginName):
		pluginBasePath = os.getcwd()
		pluginConfigPath = os.path.join(pluginBasePath, "RPFrameworkConfig.xml")

		if os.path.exists(pluginConfigPath):
			self.logger.debug("Beginning processing of RPFrameworkConfig.xml file")
			try:
				# read in the XML using the XML ElementTree implementation/module
				configDom        = xml.etree.ElementTree.parse(pluginConfigPath)
				pluginConfigNode = configDom.getroot().find("pluginConfig")

				# read in any plugin-level parameter definitions
				pluginParamNode = pluginConfigNode.find("pluginParams")
				if pluginParamNode != None:
					for pluginParam in pluginParamNode:
						rpPluginParam = self.readIndigoParamNode(pluginParam)
						self.pluginConfigParams.append(rpPluginParam)
						self.logger.threaddebug(f"Found plugin param: {rpPluginParam.indigoId}")

				# read in any plugin-level guiConfigSettings
				pluginGuiConfigNode = pluginConfigNode.find("guiConfiguration")
				if pluginGuiConfigNode != None:
					for guiConfigSetting in pluginGuiConfigNode:
>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
						self.logger.threaddebug(f"Found plugin setting: {guiConfigSetting.tag} = {guiConfigSetting.text}")
						self.putGUIConfigValue(GUI_CONFIG_PLUGINSETTINGS, guiConfigSetting.tag, guiConfigSetting.text)

				# determine if any device mappings are present
<<<<<<< HEAD
				device_mappings = plugin_config_node.find("deviceMapping")
				if device_mappings is not None:
					for deviceMapping in device_mappings.findall("device"):
						indigo_id  = f"{deviceMapping.get('indigoId')}"
						class_name = f"{deviceMapping.get('className')}"
						self.managedDeviceClassMapping[indigo_id] = class_name
						self.logger.threaddebug(f"Found device mapping; id: {indigo_id} to class: {class_name}")
				else:
					self.logger.threaddebug("No device mappings found")
					
				# read in any device definition information such as device properties for
				# validation and retrieval
				devices_node = plugin_config_node.find("devices")
				if devices_node is not None:
					for device_dfn in devices_node.findall("device"):
						indigo_device_id = to_unicode(device_dfn.get("indigoId"))
						
						# process all the parameters for this device
						device_params_node = device_dfn.find("params")
						if device_params_node is not None:
							params_list = list()
							for device_param in device_params_node.findall("param"):
								rp_dev_param = self.readIndigoParamNode(device_param)
								self.logger.threaddebug(f"Created device parameter for managed device '{indigo_device_id}': {rp_dev_param.indigoId}")
								params_list.append(rp_dev_param)
							self.managedDeviceParams[indigo_device_id] = params_list
							
						# process any GUI configurations -- these are settings that affect how the
						# plugin appears to Indigo users
						gui_config_node = device_dfn.find("guiConfiguration")
						if gui_config_node is not None:
							for guiConfigSetting in gui_config_node:
								self.logger.threaddebug(f"Found device setting: {guiConfigSetting.tag}={guiConfigSetting.text}")
								self.putGUIConfigValue(indigo_device_id, guiConfigSetting.tag, guiConfigSetting.text)
								
						# process any device response definitions... these define what the plugin will do
						# when a response is received from the device (definition is agnostic of type of device,
						# though they may be handled differently in code)
						device_responses_node = device_dfn.find("deviceResponses")
						if device_responses_node is not None:
							for dev_response in device_responses_node.findall("response"):
								response_id            = f"{dev_response.get('id')}"
								response_to_action_id  = f"{dev_response.get('respondToActionId')}"
								criteria_format_string = f"{dev_response.find('criteriaFormatString').text}"
								match_expression       = f"{dev_response.find('matchExpression').text}"
								self.logger.threaddebug(f"Found device response: {response_id}")
									
								# create the object so that effects may be added from child nodes
								dev_response_defn = RPFrameworkDeviceResponse.RPFrameworkDeviceResponse(response_id, criteria_format_string, match_expression, response_to_action_id)
								
								# add in any effects that are defined
								effects_list_node = dev_response.find("effects")
								if effects_list_node is not None:
									for effectDefn in effects_list_node.findall("effect"):
										effect_type         = eval(f"RPFrameworkDeviceResponse.{effectDefn.get('effectType')}")
										effect_update_param = f"{effectDefn.find('updateParam').text}"
										effect_value_format = f"{effectDefn.find('updateValueFormat').text}"
										
										effect_value_format_ex_val  = ""
										effect_value_format_ex_node = effectDefn.find("updateValueExFormat")
										if effect_value_format_ex_node is not None:
											effect_value_format_ex_val = f"{effect_value_format_ex_node.text}"
										
										effect_value_eval_result = to_unicode(effectDefn.get("evalResult")).lower() == "true"
										
										effect_exec_condition      = ""
										effect_exec_condition_node = effectDefn.find("updateExecCondition")
										if effect_exec_condition_node is not None:
											effect_exec_condition = f"{effect_exec_condition_node.text}"
										
										self.logger.threaddebug(f"Found response effect: Type={effect_type}; Param: {effect_update_param}; ValueFormat={effect_value_format}; ValueFormatEx={effect_value_format_ex_val}; Eval={effect_value_eval_result}; Condition={effect_exec_condition}")
										dev_response_defn.addResponseEffect(RPFrameworkDeviceResponse.RPFrameworkDeviceResponseEffect(effect_type, effect_update_param, effect_value_format, effect_value_format_ex_val, effect_value_eval_result, effect_exec_condition))
								
								# add the definition to the plugin's list of response definitions
								self.addDeviceResponseDefinition(indigo_device_id, dev_response_defn)
						
				# attempt to read any actions that will be automatically processed by
				# the framework
				managed_actions = plugin_config_node.find("actions")
				if managed_actions is not None:
					for managedAction in managed_actions.findall("action"):
						indigo_action_id = to_unicode(managedAction.get('indigoId'))
						rp_action = RPFrameworkIndigoActionDfn(indigo_action_id)
						self.logger.threaddebug(f"Found managed action: {indigo_action_id}")
						
						# process/add in the commands for this action
						command_list_node = managedAction.find("commands")
						if command_list_node is not None:
							for command_defn in command_list_node.findall("command"):
								command_name_node          = command_defn.find("commandName")
								command_format_string_node = command_defn.find("commandFormat")
								
								command_execute_condition      = ""
								command_execute_condition_node = command_defn.find("commandExecCondition")
								if command_execute_condition_node is not None:
									command_execute_condition = to_unicode(command_execute_condition_node.text)
								
								command_repeat_count      = ""
								command_repeat_count_node = command_defn.find("commandRepeatCount")
								if command_repeat_count_node is not None:
									command_repeat_count = to_unicode(command_repeat_count_node.text)
									
								command_repeat_delay      = ""
								command_repeat_delay_node = command_defn.find("commandRepeatDelay")
								if command_repeat_delay_node is not None:
									command_repeat_delay = f"{command_repeat_delay_node.text}"
								
								rp_action.addIndigoCommand(to_unicode(command_name_node.text), to_unicode(command_format_string_node.text), command_repeat_count, command_repeat_delay, command_execute_condition)
							
						params_node = managedAction.find("params")
						if params_node is not None:
							self.logger.threaddebug(f"Processing {len(params_node)} params for action")
							for action_param in params_node.findall("param"):
								rp_param = self.readIndigoParamNode(action_param)
								self.logger.threaddebug(f"Created parameter for managed action '{rp_action.indigoActionId}': {rp_param.indigoId}")
								rp_action.addIndigoParameter(rp_param)
						self.addIndigoAction(rp_action)
				self.logger.debug("Successfully completed processing of RPFrameworkConfig.xml file")
			except:
				self.logger.critical(f"Plugin Config: Error reading RPFrameworkConfig.xml file at: {plugin_config_path}")
		else:
			self.logger.warning(f"RPFrameworkConfig.xml not found at {plugin_config_path}, skipping processing")
			
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will read in a parameter definition from the given XML node, returning
	# a RPFrameworkIndigoParam object fully filled in from the node
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def readIndigoParamNode(self, param_node):
		param_indigo_id   = f"{param_node.get('indigoId')}"
		param_type        = eval(f"RPFrameworkIndigoParam.{param_node.get('paramType')}")
		param_is_required = (param_node.get("isRequired").lower() == "true")
		rp_param          = RPFrameworkIndigoParamDefn(param_indigo_id, param_type, isRequired=param_is_required)
		
		min_value_node = param_node.find("minValue")
		if min_value_node is not None:
			min_value_string = min_value_node.text
			if rp_param.paramType == RPFrameworkIndigoParamDefn.ParamTypeFloat:
				rp_param.minValue = float(min_value_string)
			else:
				rp_param.minValue = int(min_value_string)
		
		max_value_node = param_node.find("maxValue")
		if max_value_node is not None:
			max_value_string = max_value_node.text
			if rp_param.paramType == RPFrameworkIndigoParamDefn.ParamTypeFloat:
				rp_param.maxValue = float(max_value_string)
			else:
				rp_param.maxValue = int(max_value_string)
				
		val_expression_node = param_node.find("validationExpression")
		if val_expression_node is not None:
			rp_param.validationExpression = to_unicode(val_expression_node.text)
				
		default_value_node = param_node.find("defaultValue")
		if default_value_node is not None:
			if rp_param.paramType == RPFrameworkIndigoParamDefn.ParamTypeFloat:
				rp_param.defaultValue = float(default_value_node.text)
			elif rp_param.paramType == RPFrameworkIndigoParamDefn.ParamTypeInteger:
				rp_param.defaultValue = int(default_value_node.text)
			elif rp_param.paramType == RPFrameworkIndigoParamDefn.ParamTypeBoolean:
				rp_param.defaultValue = (default_value_node.text.lower() == "true")
			else:
				rp_param.defaultValue = default_value_node.text
				
		invalid_message_node = param_node.find("invalidValueMessage")
		if invalid_message_node is not None:
			rp_param.invalidValueMessage = to_unicode(invalid_message_node.text)
	
		return rp_param
	
=======
				deviceMappings = pluginConfigNode.find("deviceMapping")
				if deviceMappings is not None:
					for deviceMapping in deviceMappings.findall("device"):
						indigoId  = to_unicode(deviceMapping.get("indigoId"))
						className = to_unicode(deviceMapping.get("className"))
						self.managedDeviceClassMapping[indigoId] = className
						self.logger.threaddebug(f"Found device mapping; id: {indigoId} to class: {className}")
				else:
					self.logger.threaddebug("No device mappings found")

				# read in any device definition information such as device properties for
				# validation and retrieval
				devicesNode = pluginConfigNode.find("devices")
				if devicesNode is not None:
					for deviceDfn in devicesNode.findall("device"):
						indigoDeviceId = to_unicode(deviceDfn.get("indigoId"))

						# process all the parameters for this device
						deviceParamsNode = deviceDfn.find("params")
						if deviceParamsNode != None:
							paramsList = list()
							for deviceParam in deviceParamsNode.findall("param"):
								rpDevParam = self.readIndigoParamNode(deviceParam)
								self.logger.threaddebug(f"Created device parameter for managed device '{indigoDeviceId}': {rpDevParam.indigoId}")
								paramsList.append(rpDevParam)
							self.managedDeviceParams[indigoDeviceId] = paramsList

						# process any GUI configurations -- these are settings that affect how the
						# plugin appears to Indigo users
						guiConfigNode = deviceDfn.find("guiConfiguration")
						if guiConfigNode is not None:
							for guiConfigSetting in guiConfigNode:
								self.logger.threaddebug(f"Found device setting: {guiConfigSetting.tag}={guiConfigSetting.text}")
								self.putGUIConfigValue(indigoDeviceId, guiConfigSetting.tag, guiConfigSetting.text)

						# process any device response definitions... these define what the plugin will do
						# when a response is received from the device (definition is agnostic of type of device,
						# though they may be handled differently in code)
						deviceResponsesNode = deviceDfn.find("deviceResponses")
						if deviceResponsesNode is not None:
							for devResponse in deviceResponsesNode.findall("response"):
								responseId           = to_unicode(devResponse.get("id"))
								responseToActionId   = to_unicode(devResponse.get("respondToActionId"))
								criteriaFormatString = to_unicode(devResponse.find("criteriaFormatString").text)
								matchExpression      = to_unicode(devResponse.find("matchExpression").text)
								self.logger.threaddebug(f"Found device response: {responseId}")

								# create the object so that effects may be added from child nodes
								devResponseDefn = RPFrameworkDeviceResponse(responseId, criteriaFormatString, matchExpression, responseToActionId)

								# add in any effects that are defined
								effectsListNode = devResponse.find("effects")
								if effectsListNode is not None:
									for effectDefn in effectsListNode.findall("effect"):
										effectType        = eval(f"RPFrameworkDeviceResponse.{effectDefn.get('effectType')}")
										effectUpdateParam = to_unicode(effectDefn.find("updateParam").text)
										effectValueFormat = to_unicode(effectDefn.find("updateValueFormat").text)

										effectValueFormatExVal = u''
										effectValueFormatExNode = effectDefn.find("updateValueExFormat")
										if effectValueFormatExNode is not None:
											effectValueFormatExVal = to_unicode(effectValueFormatExNode.text)

										effectValueEvalResult = to_unicode(effectDefn.get("evalResult")).lower() == "true"

										effectExecCondition = u''
										effectExecConditionNode = effectDefn.find("updateExecCondition")
										if effectExecConditionNode is not None:
											effectExecCondition = to_unicode(effectExecConditionNode.text)

										self.logger.threaddebug(f"Found response effect: Type={effectType}; Param: {effectUpdateParam}; ValueFormat={effectValueFormat}; ValueFormatEx={effectValueFormatExVal}; Eval={effectValueEvalResult}; Condition={effectExecCondition}")
										devResponseDefn.addResponseEffect(RPFrameworkDeviceResponseEffect(effectType, effectUpdateParam, effectValueFormat, effectValueFormatExVal, effectValueEvalResult, effectExecCondition))

								# add the definition to the plugin's list of response definitions
								self.addDeviceResponseDefinition(indigoDeviceId, devResponseDefn)

				# attempt to read any actions that will be automatically processed by
				# the framework
				managedActions = pluginConfigNode.find("actions")
				if managedActions is not None:
					for managedAction in managedActions.findall("action"):
						indigoActionId = to_unicode(managedAction.get("indigoId"))
						rpAction = RPFrameworkIndigoActionDfn(indigoActionId)
						self.logger.threaddebug(f"Found managed action: {indigoActionId}")

						# process/add in the commands for this action
						commandListNode = managedAction.find("commands")
						if commandListNode is not None:
							for commandDefn in commandListNode.findall("command"):
								commandNameNode         = commandDefn.find("commandName")
								commandFormatStringNode = commandDefn.find("commandFormat")

								commandExecuteCondition     = ""
								commandExecuteConditionNode = commandDefn.find("commandExecCondition")
								if commandExecuteConditionNode is not None:
									commandExecuteCondition = to_unicode(commandExecuteConditionNode.text)

								commandRepeatCount = ""
								commandRepeatCountNode = commandDefn.find("commandRepeatCount")
								if commandRepeatCountNode is not None:
									commandRepeatCount = to_unicode(commandRepeatCountNode.text)

								commandRepeatDelay = ""
								commandRepeatDelayNode = commandDefn.find("commandRepeatDelay")
								if commandRepeatDelayNode is not None:
									commandRepeatDelay = to_unicode(commandRepeatDelayNode.text)

								rpAction.addIndigoCommand(to_unicode(commandNameNode.text), to_unicode(commandFormatStringNode.text), commandRepeatCount, commandRepeatDelay, commandExecuteCondition)

						paramsNode = managedAction.find("params")
						if paramsNode is not None:
							self.logger.threaddebug(f"Processing {len(paramsNode)} params for action")
							for actionParam in paramsNode.findall("param"):
								rpParam = self.readIndigoParamNode(actionParam)
								self.logger.threaddebug(f"Created parameter for managed action '{rpAction.indigoActionId}': {rpParam.indigoId}")
								rpAction.addIndigoParameter(rpParam)
						self.addIndigoAction(rpAction)
				self.logger.debug("Successfully completed processing of RPFrameworkConfig.xml file")
			except Exception as err:
				self.logger.error(f"Plugin Config: Error reading RPFrameworkConfig.xml file at: {pluginConfigPath}\n{err}")
		else:
			self.logger.warning(f"RPFrameworkConfig.xml not found at {pluginConfigPath}, skipping processing")

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will read in a parameter definition from the given XML node, returning
	# a RPFrameworkIndigoParam object fully filled in from the node
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def readIndigoParamNode(self, paramNode):
		paramIndigoId   = to_unicode(paramNode.get("indigoId"))
		paramType       = eval(f"RPFrameworkIndigoParamDefn.{paramNode.get('paramType')}")
		paramIsRequired = (paramNode.get("isRequired").lower() == "true")
		rpParam         = RPFrameworkIndigoParamDefn(paramIndigoId, paramType, isRequired=paramIsRequired)

		minValueNode = paramNode.find("minValue")
		if minValueNode is not None:
			minValueString = minValueNode.text
			if rpParam.paramType == RPFrameworkIndigoParamDefn.ParamTypeFloat:
				rpParam.minValue = float(minValueString)
			else:
				rpParam.minValue = int(minValueString)

		maxValueNode = paramNode.find("maxValue")
		if maxValueNode is not None:
			maxValueString = maxValueNode.text
			if rpParam.paramType == RPFrameworkIndigoParamDefn.ParamTypeFloat:
				rpParam.maxValue = float(maxValueString)
			else:
				rpParam.maxValue = int(maxValueString)

		validationExpressionNode = paramNode.find("validationExpression")
		if validationExpressionNode is not None:
			rpParam.validationExpression = to_unicode(validationExpressionNode.text)

		defaultValueNode = paramNode.find("defaultValue")
		if defaultValueNode is not None:
			if rpParam.paramType == RPFrameworkIndigoParamDefn.ParamTypeFloat:
				rpParam.defaultValue = float(defaultValueNode.text)
			elif rpParam.paramType == RPFrameworkIndigoParamDefn.ParamTypeInteger:
				rpParam.defaultValue = int(defaultValueNode.text)
			elif rpParam.paramType == RPFrameworkIndigoParamDefn.ParamTypeBoolean:
				rpParam.defaultValue = (defaultValueNode.text.lower() == "true")
			else:
				rpParam.defaultValue = defaultValueNode.text

		invalidMessageNode = paramNode.find("invalidValueMessage")
		if invalidMessageNode is not None:
			rpParam.invalidValueMessage = to_unicode(invalidMessageNode.text)

		return rpParam

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
	#endregion
	# /////////////////////////////////////////////////////////////////////////////////////

	# /////////////////////////////////////////////////////////////////////////////////////
	# region Indigo control methods
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# startup is called by Indigo whenever the plugin is first starting up (by a restart
	# of Indigo server or the plugin or an update
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def startup(self):
		pass

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# shutdown is called by Indigo whenever the entire plugin is being shut down from
	# being disabled, during an update process or if the server is being shut down
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def shutdown(self):
		pass

	#endregion
	# /////////////////////////////////////////////////////////////////////////////////////

	# /////////////////////////////////////////////////////////////////////////////////////
	# region Indigo device life-cycle call-back routines
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called whenever the plugin should be connecting / communicating with
	# the physical device... here is where we will begin tracking the device as well
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def deviceStartComm(self, dev):
		self.logger.debug(f"Entering deviceStartComm for {dev.name}; ID={dev.id}")
<<<<<<< HEAD
		
		# create the plugin device object and add it to the managed list
		new_device_object             = self.createDeviceObject(dev)
		self.managedDevices[dev.id] = new_device_object
		new_device_object.initiateCommunications()
		
		# this object may be a child object... if it is then we need to see if its
		# parent has already been created (and if so add it to that parent)
		is_child_device_type = self.getGUIConfigValue(dev.deviceTypeId, GUI_CONFIG_ISCHILDDEVICEID, "false").lower() == "true"
		if is_child_device_type:
			self.logger.threaddebug("Device is child object, attempting to find parent")
			parent_device_id = int(dev.pluginProps[self.getGUIConfigValue(dev.deviceTypeId, GUI_CONFIG_PARENTDEVICEIDPROPERTYNAME, "")])
			self.logger.threaddebug(f"Found parent ID of device {dev.id}: {parent_device_id}")
			if parent_device_id in self.managedDevices:
				self.logger.threaddebug("Parent object found, adding this child device now")
				self.managedDevices[parent_device_id].addChildDevice(new_device_object)
				
		# this object could be a parent object whose children have already been created; we need to add those children
		# to this parent object now
		for found_device_id in self.managedDevices:
			found_device = self.managedDevices[found_device_id]
			if self.getGUIConfigValue(found_device.indigoDevice.deviceTypeId, GUI_CONFIG_ISCHILDDEVICEID, "false").lower() == "true" and int(found_device.indigoDevice.pluginProps[self.getGUIConfigValue(found_device.indigoDevice.deviceTypeId, GUI_CONFIG_PARENTDEVICEIDPROPERTYNAME, "")]) == dev.id:
				self.logger.threaddebug(f"Found previously-created child object for parent; child ID: {found_device.indigoDevice.id}")
				new_device_object.addChildDevice(found_device)

		self.logger.debug(f"Exiting deviceStartComm for {dev.name}")
		
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
=======

		# create the plugin device object and add it to the managed list
		newDeviceObject             = self.createDeviceObject(dev)
		self.managedDevices[dev.id] = newDeviceObject
		newDeviceObject.initiateCommunications()

		# this object may be a child object... if it is then we need to see if its
		# parent has already been created (and if so add it to that parent)
		isChildDeviceType = self.getGUIConfigValue(dev.deviceTypeId, GUI_CONFIG_ISCHILDDEVICEID, "false").lower() == "true"
		if isChildDeviceType == True:
			self.logger.threaddebug("Device is child object, attempting to find parent")
			parentDeviceId = int(dev.pluginProps[self.getGUIConfigValue(dev.deviceTypeId, GUI_CONFIG_PARENTDEVICEIDPROPERTYNAME, "")])
			self.logger.threaddebug(f"Found parent ID of device {dev.id}: {parentDeviceId}")
			if parentDeviceId in self.managedDevices:
				self.logger.threaddebug("Parent object found, adding this child device now")
				self.managedDevices[parentDeviceId].addChildDevice(newDeviceObject)

		# this object could be a parent object whose children have already been created; we need to add those children
		# to this parent object now
		for foundDeviceId in self.managedDevices:
			foundDevice = self.managedDevices[foundDeviceId]
			if self.getGUIConfigValue(foundDevice.indigoDevice.deviceTypeId, GUI_CONFIG_ISCHILDDEVICEID, "false").lower() == "true" and int(foundDevice.indigoDevice.pluginProps[self.getGUIConfigValue(foundDevice.indigoDevice.deviceTypeId, GUI_CONFIG_PARENTDEVICEIDPROPERTYNAME, "")]) == dev.id:
				self.logger.threaddebug(f"Found previously-created child object for parent; child ID: {foundDevice.indigoDevice.id}")
				newDeviceObject.addChildDevice(foundDevice)

		self.logger.debug(f"Exiting deviceStartComm for {dev.name}")

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
	# This routine must be implemented in ancestor classes in order to return the device
	# object that is to be created/managed
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def createUnManagedDeviceObject(self, device):
		raise "createUnManagedDeviceObject not implemented"
<<<<<<< HEAD

	def createDeviceObject(self, device):
		if self.managedDeviceClassModule is not None and device.deviceTypeId in self.managedDeviceClassMapping:
			device_class = getattr(self.managedDeviceClassModule, self.managedDeviceClassMapping[device.deviceTypeId])
			return device_class(self, device)
=======
	def createDeviceObject(self, device):
		if not (self.managedDeviceClassModule is None) and device.deviceTypeId in self.managedDeviceClassMapping:
			deviceClass = getattr(self.managedDeviceClassModule, self.managedDeviceClassMapping[device.deviceTypeId])
			return deviceClass(self, device)
>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
		else:
			return self.createUnManagedDeviceObject(device)

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called whenever the plugin should cease communicating with the
	# hardware, breaking the connection
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def deviceStopComm(self, dev):
		self.logger.debug(f"Entering deviceStopComm for {dev.name}; ID={dev.id}")
<<<<<<< HEAD
		
=======

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
		# dequeue any pending reconnection attempts...

		# first remove the device from the parent if this is a child device...
<<<<<<< HEAD
		is_child_device_type = self.getGUIConfigValue(dev.deviceTypeId, GUI_CONFIG_ISCHILDDEVICEID, "false").lower() == "true"
		if is_child_device_type:
			self.logger.threaddebug("Device is child object, attempting to remove from parent...")
			parent_device_id = int(dev.pluginProps[self.getGUIConfigValue(dev.deviceTypeId, GUI_CONFIG_PARENTDEVICEIDPROPERTYNAME, "")])
			if parent_device_id in self.managedDevices:
				self.logger.threaddebug(f"Removing device from parent ID: {parent_device_id}")
				self.managedDevices[parent_device_id].removeChildDevice(self.managedDevices[dev.id])
		
		# remove the primary managed object
		self.managedDevices[dev.id].terminateCommunications()
		del self.managedDevices[dev.id]			
		
		self.logger.debug(f"Exiting deviceStopComm for {dev.name}")
		
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
=======
		isChildDeviceType = self.getGUIConfigValue(dev.deviceTypeId, GUI_CONFIG_ISCHILDDEVICEID, "false").lower() == "true"
		if isChildDeviceType == True:
			self.logger.threaddebug("Device is child object, attempting to remove from parent...")
			parentDeviceId = int(dev.pluginProps[self.getGUIConfigValue(dev.deviceTypeId, GUI_CONFIG_PARENTDEVICEIDPROPERTYNAME, "")])
			if parentDeviceId in self.managedDevices:
				self.logger.threaddebug(f"Removing device from parent ID: {parentDeviceId}")
				self.managedDevices[parentDeviceId].removeChildDevice(self.managedDevices[dev.id])

		# remove the primary managed object
		self.managedDevices[dev.id].terminateCommunications()
		del self.managedDevices[dev.id]

		self.logger.debug(f"Exiting deviceStopComm for {dev.name}")

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
	# This routine is called whenever the server is defining an event / trigger setup
	# by the user
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def triggerStartProcessing(self, trigger):
		self.logger.threaddebug(f"Registering trigger: {trigger.id}")
<<<<<<< HEAD
		
		# if the descendent class does not handle the trigger then we process it by
		# storing it against the trigger type
		if not self.registerCustomTrigger(trigger):
			trigger_type = trigger.pluginTypeId
			if trigger_type not in self.indigoEvents:
				self.indigoEvents[trigger_type] = dict()
			self.indigoEvents[trigger_type][trigger.id] = trigger
			
		self.logger.debug(f"Registered trigger: {trigger.id}")
		
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
=======

		# if the descendent class does not handle the trigger then we process it by
		# storing it against the trigger type
		if self.registerCustomTrigger(trigger) == False:
			triggerType = trigger.pluginTypeId
			if not (triggerType in self.indigoEvents):
				self.indigoEvents[triggerType] = dict()
			self.indigoEvents[triggerType][trigger.id] = trigger

		self.logger.debug(f"Registered trigger: {trigger.id}")

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
	# This routine gives descendant plugins the chance to process the event
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def registerCustomTrigger(self, trigger):
		return False

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called whenever the server is un-registering a trigger
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def triggerStopProcessing(self, trigger):
		self.logger.threaddebug(f"Stopping trigger: {trigger.id}")
<<<<<<< HEAD
		
		# if the descendent class does not handle the unregistration then we process it by
		# removing it from the dictionary
		if not self.registerCustomTrigger(trigger):
			trigger_type = trigger.pluginTypeId
			if trigger_type in self.indigoEvents:
				if trigger.id in self.indigoEvents[trigger_type]:
					del self.indigoEvents[trigger_type][trigger.id]
		
		self.logger.debug(f"Stopped trigger: {trigger.id}")
		
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
=======

		# if the descendent class does not handle the de-registration then we process it by
		# removing it from the dictionary
		if self.registerCustomTrigger(trigger) == False:
			triggerType = trigger.pluginTypeId
			if triggerType in self.indigoEvents:
				if trigger.id in self.indigoEvents[triggerType]:
					del self.indigoEvents[triggerType][trigger.id]

		self.logger.debug(f"Stopped trigger: {trigger.id}")

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
	# This routine gives descendant plugins the chance to unregister the event
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def unRegisterCustomTrigger(self, trigger):
		return False

	# endregion
	# /////////////////////////////////////////////////////////////////////////////////////

	# /////////////////////////////////////////////////////////////////////////////////////
	# region Asynchronous processing routines
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will run the concurrent processing thread used at the plugin (not
	# device) level - such things as update checks and device reconnections
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def runConcurrentThread(self):
		try:
			# read in any configuration values necessary...
<<<<<<< HEAD
			empty_queue_thread_sleep_time = float(self.getGUIConfigValue(GUI_CONFIG_PLUGINSETTINGS, GUI_CONFIG_PLUGIN_COMMANDQUEUEIDLESLEEP, "20"))
			
=======
			emptyQueueThreadSleepTime = float(self.getGUIConfigValue(GUI_CONFIG_PLUGINSETTINGS, GUI_CONFIG_PLUGIN_COMMANDQUEUEIDLESLEEP, u'20'))

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
			while True:
				# process pending commands now...
				re_queue_commands_list = list()
				while not self.pluginCommandQueue.empty():
<<<<<<< HEAD
					len_queue = self.pluginCommandQueue.qsize()
					self.logger.threaddebug(f"Plugin Command queue has {len_queue} command(s) waiting")
					
=======
					lenQueue = self.pluginCommandQueue.qsize()
					self.logger.threaddebug(u'Plugin Command queue has {0} command(s) waiting'.format(lenQueue))

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
					# the command name will identify what action should be taken...
					re_queue_command = False
					command = self.pluginCommandQueue.get()
					if command.commandName == RPFrameworkCommand.CMD_DEVICE_RECONNECT:
						# the command payload will be in the form of a tuple:
						#	(DeviceID, DeviceInstanceIdentifier, ReconnectTime)
						#	ReconnectTime is the datetime where the next reconnection attempt should occur
						time_now = time.time()
						if time_now > command.commandPayload[2]:
							if command.commandPayload[0] in self.managedDevices:
								if self.managedDevices[command.commandPayload[0]].deviceInstanceIdentifier == command.commandPayload[1]:
									self.logger.debug(f"Attempting reconnection to device {command.commandPayload[0]}")
									self.managedDevices[command.commandPayload[0]].initiateCommunications()
								else:
									self.logger.threaddebug(f"Ignoring reconnection command for device {command.commandPayload[0]}; new instance detected")
							else:
								self.logger.debug(f"Ignoring reconnection command for device {command.commandPayload[0]}; device not created")
						else:
<<<<<<< HEAD
							re_queue_command = True
					
=======
							reQueueCommand = True

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
					elif command.commandName == RPFrameworkCommand.CMD_DEBUG_LOGUPNPDEVICES:
						# kick off the UPnP discovery and logging now
						self.logUPnPDevicesFoundProcessing()

					else:
						# allow a base class to process the command
<<<<<<< HEAD
						self.handleUnknownPluginCommand(command, re_queue_commands_list)
					
					# complete the de-queuing of the command, allowing the next
					# command in queue to rise to the top
					self.pluginCommandQueue.task_done()
					if re_queue_command:
						self.logger.threaddebug("Plugin command queue not yet ready; re-queuing for future execution")
						re_queue_commands_list.append(command)
							
				# any commands that did not yet execute should be placed back into the queue
				for command_to_requeue in re_queue_commands_list:
					self.pluginCommandQueue.put(command_to_requeue)
				
				# sleep on an empty queue... note that this should not normally be as granular
				# as a device's communications! (value is in seconds)
				self.sleep(empty_queue_thread_sleep_time)
				
=======
						self.handleUnknownPluginCommand(command, reQueueCommandsList)

					# complete the dequeuing of the command, allowing the next
					# command in queue to rise to the top
					self.pluginCommandQueue.task_done()
					if reQueueCommand == True:
						self.logger.threaddebug(u'Plugin command queue not yet ready; requeuing for future execution')
						reQueueCommandsList.append(command)

				# any commands that did not yet execute should be placed back into the queue
				for commandToRequeue in reQueueCommandsList:
					self.pluginCommandQueue.put(commandToRequeue)

				# sleep on an empty queue... note that this should not normally be as granular
				# as a device's communications! (value is in seconds)
				self.sleep(emptyQueueThreadSleepTime)

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
		except self.StopThread:
			# this exception is simply shutting down the thread... there is nothing
			# that we need to process
			pass

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will be called to handle any unknown commands at the plugin level; it
	# can/should be overridden in the plugin implementation (if needed)
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def handleUnknownPluginCommand(self, rpCommand, reQueueCommandsList):
		pass

	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////

	#/////////////////////////////////////////////////////////////////////////////////////
	#region Indigo definitions helper functions
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will add a new action to the managed actions of the plugin
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def addIndigoAction(self, indigoAction):
		self.indigoActions[indigoAction.indigoActionId] = indigoAction

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will add a new device response to the list of responses that the plugin
	# can automatically handle
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def addDeviceResponseDefinition(self, deviceTypeId, responseDfn):
		if not (deviceTypeId in self.deviceResponseDefinitions):
			self.deviceResponseDefinitions[deviceTypeId] = list()
		self.deviceResponseDefinitions[deviceTypeId].append(responseDfn)

	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////

	#/////////////////////////////////////////////////////////////////////////////////////
	#region Data Validation Functions
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will be called to validate the information entered into the Plugin
	# configuration file
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def validatePrefsConfigUi(self, valuesDict):
		# create an error message dictionary to hold validation issues foundDevice
<<<<<<< HEAD
		error_messages = indigo.Dict()
		
=======
		errorMessages = indigo.Dict()

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
		# check each defined parameter, if any exist...
		for param in self.pluginConfigParams:
			if param.indigoId in valuesDict:
				# a value is present for this parameter - validate it
<<<<<<< HEAD
				if not param.isValueValid(valuesDict[param.indigoId]):
					error_messages[param.indigoId] = param.invalidValueMessage
					
=======
				if param.isValueValid(valuesDict[param.indigoId]) == False:
					errorMessages[param.indigoId] = param.invalidValueMessage

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
		# return the validation results...
		if len(error_messages) == 0:
			return True, valuesDict
		else:
<<<<<<< HEAD
			return False, valuesDict, error_messages
	
=======
			return (False, valuesDict, errorMessages)

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will be called when the user has closed the preference dialog
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def closedPrefsConfigUi(self, valuesDict, userCancelled):
		if not userCancelled:
			try:
				self.debugLevel = int(valuesDict.get(u'debugLevel', DEBUGLEVEL_NONE))
			except:
				self.debugLevel = DEBUGLEVEL_NONE
<<<<<<< HEAD
				
			# set up the logging level of the INDIGO logging handler to the selected level
=======

			# setup the logging level of the INDIGO logging handler to the selected level
>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
			if self.debugLevel == DEBUGLEVEL_LOW:
				self.indigo_log_handler.setLevel(logging.DEBUG)
			elif self.debugLevel == DEBUGLEVEL_HIGH:
				self.indigo_log_handler.setLevel(logging.THREADDEBUG)
			else:
				self.indigo_log_handler.setLevel(logging.INFO)
<<<<<<< HEAD
			
			self.logger.debug("Plugin preferences updated")
=======

			self.logger.debug(u'Plugin preferences updated')
>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
			if self.debugLevel == DEBUGLEVEL_NONE:
				self.logger.info("Debugging disabled")
			else:
<<<<<<< HEAD
				self.logger.info("Debugging enabled... remember to turn off when done!")
			
=======
				self.logger.info(u'Debugging enabled... remember to turn off when done!')

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called in order to get the initial values for the menu actions
	# defined in MenuItems.xml. The default (as per the base) just returns a values and
	# error dictionary, both blank
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getMenuActionConfigUiValues(self, menuId):
<<<<<<< HEAD
		values_dict    = indigo.Dict()
		error_msg_dict = indigo.Dict()
		
		if menuId == "checkForUpdateImmediate":
			# we need to run the update during the launch and then show the results to the
			# user... watch for failures and do not let this go on (must time out) since
			# the dialog could get killed
			update_available              = self.checkVersionNow()
			values_dict["currentVersion"] = f"{self.pluginVersion}"
			values_dict["latestVersion"]  = self.latestReleaseFound
			
=======
		valuesDict = indigo.Dict()
		errorMsgDict = indigo.Dict()

		if menuId == u'checkForUpdateImmediate':
			# we need to run the update during the launch and then show the results to the
			# user... watch for failures and do not let this go on (must time out) since
			# the dialog could get killed
			updateAvailable              = self.checkVersionNow()
			valuesDict["currentVersion"] = to_unicode(self.pluginVersion)
			valuesDict["latestVersion"]  = self.latestReleaseFound

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
			# give the user a "better" message about the current status
			if self.latestReleaseFound == "":
				values_dict["versionCheckResults"] = "3"
			elif update_available:
				values_dict["versionCheckResults"] = "1"
			else:
<<<<<<< HEAD
				values_dict["versionCheckResults"] = "2"
		
		return values_dict, error_msg_dict
		
=======
				valuesDict["versionCheckResults"] = u'2'

		return (valuesDict, errorMsgDict)

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will be called to validate the information entered into the Device
	# configuration GUI from within Indigo (it will only validate registered params)
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def validateDeviceConfigUi(self, valuesDict, deviceTypeId, devId):
		# create an error message dictionary to hold any validation issues
<<<<<<< HEAD
		# (and their messages) that we find	
		error_messages = indigo.Dict()
		
=======
		# (and their messages) that we find
		errorMessages = indigo.Dict()

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
		# loop through each parameter for this device and validate one-by-one
		if deviceTypeId in self.managedDeviceParams:
			for param in self.managedDeviceParams[deviceTypeId]:
				if param.indigoId in valuesDict:
					# a parameter value is present, validate it now
<<<<<<< HEAD
					if not param.isValueValid(valuesDict[param.indigoId]):
						error_messages[param.indigoId] = param.invalidValueMessage
					
				elif param.isRequired:
					error_messages[param.indigoId] = param.invalidValueMessage
				
=======
					if param.isValueValid(valuesDict[param.indigoId]) == False:
						errorMessages[param.indigoId] = param.invalidValueMessage

				elif param.isRequired == True:
					errorMessages[param.indigoId] = param.invalidValueMessage

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
		# return the validation results...
		if len(error_messages) == 0:
			# process any hidden variables that are used to show state information in
			# indigo or as a RPFramework config/storage
<<<<<<< HEAD
			valuesDict["address"] = self.substituteIndigoValues(self.getGUIConfigValue(deviceTypeId, GUI_CONFIG_ADDRESSKEY, ""), None, valuesDict)
			self.logger.threaddebug(f"Setting address of {devId} to {valuesDict['address']}")
			
			return self.validateDeviceConfigUiEx(valuesDict, deviceTypeId, devId)
		else:
			return False, valuesDict, error_messages
	
=======
			valuesDict["address"] = self.substituteIndigoValues(self.getGUIConfigValue(deviceTypeId, GUI_CONFIG_ADDRESSKEY, u''), None, valuesDict)
			self.logger.threaddebug(u'Setting address of {0} to {1}'.format(devId, valuesDict["address"]))

			return self.validateDeviceConfigUiEx(valuesDict, deviceTypeId, devId)
		else:
			return (False, valuesDict, errorMessages)

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will be called to validate any parameters not known to the plugin (not
	# automatically handled and validated); this will only be called once all known
	# parameters have been validated and it MUST return a valid tuple
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def validateDeviceConfigUiEx(self, valuesDict, deviceTypeId, devId):
<<<<<<< HEAD
		return True, valuesDict
	
=======
		return (True, valuesDict)

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will validate an action Config UI popup when it is being edited from
	# within the Indigo client; if the action being validated is not a known action then
	# a callback to the plugin implementation will be made
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
<<<<<<< HEAD
	def validateActionConfigUi(self, valuesDict, typeId, actionId):	
		self.logger.threaddebug(f"Call to validate action: {typeId}")
=======
	def validateActionConfigUi(self, valuesDict, typeId, actionId):
		self.logger.threaddebug(u'Call to validate action: {0}'.format(typeId))
>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
		if typeId in self.indigoActions:
			action_defn = self.indigoActions[typeId]
			managed_action_validation = action_defn.validateActionValues(valuesDict)
			if not managed_action_validation[0]:
				self.logger.threaddebug(f"Managed validation failed: {managed_action_validation[1]}{managed_action_validation[2]}")
			return managed_action_validation
		else:
			return self.validateUnRegisteredActionConfigUi(valuesDict, typeId, actionId)

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called to retrieve a dynamic list of elements for an action (or
	# other ConfigUI based) routine
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getConfigDialogMenu(self, filter=u'', valuesDict=None, typeId="", targetId=0):
		# the routine is designed to pass the call along to the device since most of the
		# time this is device-specific (such as inputs)
		self.logger.threaddebug(f"Dynamic menu requested for Device ID: {targetId}")
		if targetId in self.managedDevices:
			return self.managedDevices[targetId].getConfigDialogMenuItems(filter, valuesDict, typeId, targetId)
		else:
			self.logger.debug("Call to getConfigDialogMenu for device not managed by this plugin")
			return []

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called to retrieve a dynamic list of devices that are found on the
	# network matching the service given by the filter
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getConfigDialogUPNPDeviceMenu(self, filter=u'', valuesDict=None, typeId=u'', targetId=0):
		self.updateUPNPEnumerationList(typeId)
		return self.parseUPNPDeviceList(self.enumeratedDevices)

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called whenever the user clicks the "Select" button on a device
	# dialog that asks for selecting from an list of enumerated devices
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def selectUPNPEnumeratedDeviceForUse(self, valuesDict, typeId, devId):
		menu_field_id   = self.getGUIConfigValue(typeId, GUI_CONFIG_UPNP_ENUMDEVICESFIELDID, "upnpEnumeratedDevices")
		target_field_id = self.getGUIConfigValue(typeId, GUI_CONFIG_UPNP_DEVICESELECTTARGETFIELDID, "httpAddress")
		if valuesDict[menu_field_id] != u'':
			# the target field may be just the address or may be broken up into multiple parts, separated
			# by a colon (in which case the menu ID value must match!)
<<<<<<< HEAD
			fields_to_update = target_field_id.split(':')
			values_selected  = valuesDict[menu_field_id].split(':')
			
			field_idx = 0
			for field in fields_to_update:
				valuesDict[field] = values_selected[field_idx]
				field_idx += 1
				
=======
			fieldsToUpdate = targetFieldId.split(u':')
			valuesSelected = valuesDict[menuFieldId].split(u':')

			fieldIdx = 0
			for field in fieldsToUpdate:
				valuesDict[field] = valuesSelected[fieldIdx]
				fieldIdx += 1

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
		return valuesDict

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called to parse out a uPNP search results list in order to createDeviceObject
	# an indigo-friendly menu; usually will be overridden in plugin descendants
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def parseUPNPDeviceList(self, deviceList):
		try:
			menu_items = []
			for networkDevice in deviceList:
				self.logger.threaddebug(f"Found uPnP Device: {networkDevice}")
				menu_items.append((networkDevice.location, networkDevice.server))
			return menu_items
		except:
			self.logger.warning(u'Error parsing UPNP devices found on the network')
			return []

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine should be overridden and should validate any actions which are not
	# already defined within the plugin class
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def validateUnRegisteredActionConfigUi(self, valuesDict, typeId, actionId):
<<<<<<< HEAD
		return True, valuesDict
	
=======
		return (True, valuesDict)

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will validate whether or not an IP address is valid as a IPv4 addr
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def isIPv4Valid(self, ip):
		# Make sure a value was entered for the address... an IPv4 should require at least
		# 7 characters (0.0.0.0)
		ip = to_unicode(ip)
		if len(ip) < 7:
			return False

		# separate the IP address into its components... this limits the format for the
		# user input but is using a fairly standard notation so acceptable
<<<<<<< HEAD
		address_parts = ip.split(u'.')
		if len(address_parts) != 4:
			return False
				
		for part in address_parts:
=======
		addressParts = ip.split(u'.')
		if len(addressParts) != 4:
			return False

		for part in addressParts:
>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
			try:
				part = int(part)
				if part < 0 or part > 255:
					return False
			except ValueError:
				return False

		# if we make it here, the input should be valid
		return True

	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////

	#/////////////////////////////////////////////////////////////////////////////////////
	#region Action Execution Routines
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will do the work of processing/executing an action; it is assumed that
	# the plugin developer will only assign the action callback to this routine if it
	# should be handled
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def executeAction(self, pluginAction, indigoActionId=u'', indigoDeviceId=u'', paramValues=None):
		# ensure that the actionID specified by the action is a managed action that
		# we can automatically handle
		if pluginAction is not None:
			indigoActionId = pluginAction.pluginTypeId
			indigoDeviceId = pluginAction.deviceId
			paramValues    = pluginAction.props

		# ensure that action and device are both managed... if so they will each appear in
		# the respective member variable dictionaries
		if indigoActionId not in self.indigoActions:
			self.logger.error(f"Execute action called for non-managed action id: {indigoActionId}")
			return
		if indigoDeviceId not in self.managedDevices:
			self.logger.error(f"Execute action called for non-managed device id: {indigoDeviceId}")
			return

		# if execution made it this far then we have the action & device and can execute
		# that action now...
		self.indigoActions[indigoActionId].generateActionCommands(self, self.managedDevices[indigoDeviceId], paramValues)

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will toggled the debug setting on all devices managed... it is used to
	# allow setting the debug status w/o restarting the plugin
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def toggleDebugEnabled(self):
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

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will be called when the user has created a request to log the UPnP
	# debug information to the Indigo log
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def logUPnPDevicesFound(self, valuesDict, typeId):
		# perform validation here... only real requirement is to have a "type" selected
		# and this should always be the case...
<<<<<<< HEAD
		errors_dict = indigo.Dict()
		
=======
		errorsDict = indigo.Dict()

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
		# add a new command to the plugin's command queue for processing on a background
		# thread (required to avoid Indigo timing out the operation!)
		self.pluginCommandQueue.put(RPFrameworkCommand.RPFrameworkCommand(RPFrameworkCommand.CMD_DEBUG_LOGUPNPDEVICES, commandPayload=None))
		self.logger.info(u'Scheduled UPnP Device Search')
<<<<<<< HEAD
		
		# return to the dialog to allow it to close
		return True, valuesDict, errors_dict
	
=======

		# return back to the dialog to allow it to close
		return (True, valuesDict, errorsDict)

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine processing the logging of the UPnP devices once the plugin spools the
	# command on the background thread
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def logUPnPDevicesFoundProcessing(self):
		try:
			# perform the UPnP search and logging now...
<<<<<<< HEAD
			self.logger.debug("Beginning UPnP Device Search")
			service_target         = "ssdp:all"
			discovery_started      = time.time()
			discovered_device_list = uPnPDiscover(service_target, timeout=6)
			
			# create an HTML file that contains the details for all of the devices found on the network
			self.logger.debug(u'UPnP Device Search completed... creating output HTML')
			device_html  = u'<html><head><title>UPnP Devices Found</title><style type="text/css">html,body { margin: 0px; padding: 0px; width: 100%; height: 100%; }\n.upnpDevice { margin: 10px 0px 8px 5px; border-bottom: solid 1px #505050; }\n.fieldLabel { width: 140px; display: inline-block; }</style></head><body>'
			device_html += u"<div style='background-color: #3f51b5; width: 100%; height: 50px; border-bottom: solid 2px black;'><span style='color: #a1c057; font-size: 25px; font-weight: bold; line-height: 49px; padding-left: 3px;'>RogueProeliator's RPFramework UPnP Discovery Report</span></div>"
			device_html += u"<div style='border-bottom: solid 2px black; padding: 8px 3px;'><span class='fieldLabel'><b>Requesting Plugin:</b></span>" + self.pluginDisplayName + u"<br /><span class='fieldLabel'><b>Service Query:</b></span>" + service_target + u"<br /><span class='fieldLabel'><b>Date Run:</b></span>" + to_unicode(discovery_started) + "</div>"
		
=======
			self.logger.debug(u'Beginning UPnP Device Search')
			serviceTarget        = u'ssdp:all'
			discoveryStarted     = time.time()
			discoveredDeviceList = uPnPDiscover(serviceTarget, timeout=6)

			# create an HTML file that contains the details for all of the devices found on the network
			self.logger.debug(u'UPnP Device Search completed... creating output HTML')
			deviceHtml  = u'<html><head><title>UPnP Devices Found</title><style type="text/css">html,body { margin: 0px; padding: 0px; width: 100%; height: 100%; }\n.upnpDevice { margin: 10px 0px 8px 5px; border-bottom: solid 1px #505050; }\n.fieldLabel { width: 140px; display: inline-block; }</style></head><body>'
			deviceHtml += u"<div style='background-color: #3f51b5; width: 100%; height: 50px; border-bottom: solid 2px black;'><span style='color: #a1c057; font-size: 25px; font-weight: bold; line-height: 49px; padding-left: 3px;'>RogueProeliator's RPFramework UPnP Discovery Report</span></div>"
			deviceHtml += u"<div style='border-bottom: solid 2px black; padding: 8px 3px;'><span class='fieldLabel'><b>Requesting Plugin:</b></span>" + self.pluginDisplayName + u"<br /><span class='fieldLabel'><b>Service Query:</b></span>" + serviceTarget + u"<br /><span class='fieldLabel'><b>Date Run:</b></span>" + to_unicode(discoveryStarted) + "</div>"

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
			# loop through each device found...
			for device in discovered_device_list:
				device_html += u"<div class='upnpDevice'><span class='fieldLabel'>Location:</span><a href='" + to_unicode(device.location) + u"' target='_blank'>" + to_unicode(device.location) + u"</a><br /><span class='fieldLabel'>USN:</span>" + to_unicode(device.usn) + u"<br /><span class='fieldLabel'>ST:</span>" + to_unicode(device.st) + u"<br /><span class='fieldLabel'>Cache Time:</span>" + to_unicode(device.cache) + u"s"
				for header in device.allHeaders:
<<<<<<< HEAD
					header_key = to_unicode(header[0])
					if header_key != u'location' and header_key != u'usn' and header_key != u'cache-control' and header_key != u'st' and header_key != u'ext':
						device_html += u"<br /><span class='fieldLabel'>" + to_unicode(header[0]) + u":</span>" + to_unicode(header[1])
				device_html += u"</div>"
		
			device_html += u"</body></html>"
		
			# write out the file...
			self.logger.threaddebug("Writing UPnP Device Search HTML to file")
			temp_filename          = self.getPluginDirectoryFilePath("tmpUPnPDiscoveryResults.html")
			upnp_results_html_file = open(temp_filename, 'w')
			upnp_results_html_file.write(to_str(device_html))
			upnp_results_html_file.close()
		
=======
					headerKey = to_unicode(header[0])
					if headerKey != u'location' and headerKey != u'usn' and headerKey != u'cache-control' and headerKey != u'st' and headerKey != u'ext':
						deviceHtml += u"<br /><span class='fieldLabel'>" + to_unicode(header[0]) + u":</span>" + to_unicode(header[1])
				deviceHtml += u"</div>"

			deviceHtml += u"</body></html>"

			# write out the file...
			self.logger.threaddebug(u"Writing UPnP Device Search HTML to file")
			tempFilename        = self.getPluginDirectoryFilePath("tmpUPnPDiscoveryResults.html")
			upnpResultsHtmlFile = open(tempFilename, 'w')
			upnpResultsHtmlFile.write(to_str(deviceHtml))
			upnpResultsHtmlFile.close()

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
			# launch the file in a browser window via the command line
			call(["open", temp_filename])
			self.logger.info(f"Created UPnP results temporary file at {temp_filename}")
		except:
<<<<<<< HEAD
			self.logger.error("Error generating UPnP report")
	
=======
			self.logger.error(u'Error generating UPnP report')

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will be called whenever the user has chosen to dump the device details
	# to the event log via the menuitem action
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def dumpDeviceDetailsToLog(self, valuesDict, typeId):
<<<<<<< HEAD
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
		
=======
		errorsDict    = indigo.Dict()
		devicesToDump = valuesDict.get(u'devicesToDump', None)

		if devicesToDump is None or len(devicesToDump) == 0:
			errorsDict[u'devicesToDump'] = u'Please select one or more devices'
			return (False, valuesDict, errorsDict)
		else:
			for deviceId in devicesToDump:
				self.logger.info(u'Dumping details for DeviceID: {0}'.format(deviceId))
				dumpDev = indigo.devices[int(deviceId)]
				self.logger.info(to_unicode(dumpDev))
			return (True, valuesDict, errorsDict)

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine provides the callback for devices based off a Dimmer... since the call
	# comes into the plugin we will pass it off the device now
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def actionControlDimmerRelay(self, action, dev):
		# transform this action into our standard "executeAction" parameters so that the
		# action is processed in a standard way
<<<<<<< HEAD
		indigo_action_id = to_unicode(action.deviceAction)
		if indigo_action_id == "11":
			indigo_action_id = "StatusRequest"
		
		indigo_device_id = dev.id
		param_values = dict()
		param_values["actionValue"] = to_unicode(action.actionValue)
		self.logger.debug(f"Dimmer Command: ActionId={indigo_action_id}; Device={indigo_device_id}; actionValue={param_values['actionValue']}")
		
		self.executeAction(None, indigo_action_id, indigo_device_id, param_values)
		
=======
		indigoActionId = to_unicode(action.deviceAction)
		if indigoActionId == u'11':
			indigoActionId = u'StatusRequest'

		indigoDeviceId = dev.id
		paramValues = dict()
		paramValues["actionValue"] = to_unicode(action.actionValue)
		self.logger.debug(u'Dimmer Command: ActionId={0}; Device={1}; actionValue={2}'.format(indigoActionId, indigoDeviceId, paramValues["actionValue"]))

		self.executeAction(None, indigoActionId, indigoDeviceId, paramValues)

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////

	#/////////////////////////////////////////////////////////////////////////////////////
	#region Helper Routines
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will perform a substitution on a string for all Indigo-values that
	# may be substituted (variables, devices, states, parameters, etc.)
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def substituteIndigoValues(self, input, rpDevice, actionParamValues):
<<<<<<< HEAD
		substituted_string = input
		if substituted_string is None:
			substituted_string = ""
		
		# substitute each parameter value called for in the string; this is done first so that
		# the parameter could call for a substitution
		ap_matcher = re.compile(r'%ap:([a-z\d]+)%', re.IGNORECASE)
		for match in ap_matcher.finditer(substituted_string):
			substituted_string = substituted_string.replace(to_unicode(match.group(0)), to_unicode(actionParamValues[match.group(1)]))
			
=======
		substitutedString = input
		if substitutedString is None:
			substitutedString = u''

		# substitute each parameter value called for in the string; this is done first so that
		# the parameter could call for a substitution
		apMatcher = re.compile(r'%ap:([a-z\d]+)%', re.IGNORECASE)
		for match in apMatcher.finditer(substitutedString):
			substitutedString = substitutedString.replace(to_unicode(match.group(0)), to_unicode(actionParamValues[match.group(1)]))

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
		# substitute device properties since the substitute method below handles states...
		dp_matcher = re.compile(r'%dp:([a-z\d]+)%', re.IGNORECASE)
		for match in dp_matcher.finditer(substituted_string):
			if type(rpDevice.indigoDevice.pluginProps.get(match.group(1), None)) is indigo.List:
				substituted_string = substituted_string.replace(to_unicode(match.group(0)), "'" + ','.join(rpDevice.indigoDevice.pluginProps.get(match.group(1))) + "'")
			else:
<<<<<<< HEAD
				substituted_string = substituted_string.replace(to_unicode(match.group(0)), to_unicode(rpDevice.indigoDevice.pluginProps.get(match.group(1), "")))
			
		# handle device states for any where we do not specify a device id
		ds_matcher = re.compile(r'%ds:([a-z\d]+)%', re.IGNORECASE)
		for match in ds_matcher.finditer(substituted_string):
			substituted_string = substituted_string.replace(to_unicode(match.group(0)), to_unicode(rpDevice.indigoDevice.states.get(match.group(1), u'')))
			
=======
				substitutedString = substitutedString.replace(to_unicode(match.group(0)), to_unicode(rpDevice.indigoDevice.pluginProps.get(match.group(1), u'')))

		# handle device states for any where we do not specify a device id
		dsMatcher = re.compile(r'%ds:([a-z\d]+)%', re.IGNORECASE)
		for match in dsMatcher.finditer(substitutedString):
			substitutedString = substitutedString.replace(to_unicode(match.group(0)), to_unicode(rpDevice.indigoDevice.states.get(match.group(1), u'')))

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
		# handle parent device properties (for child devices)
		if rpDevice is not None:
			if self.getGUIConfigValue(rpDevice.indigoDevice.deviceTypeId, GUI_CONFIG_ISCHILDDEVICEID, "false").lower() == "true":
				parent_device_id = int(rpDevice.indigoDevice.pluginProps[self.getGUIConfigValue(rpDevice.indigoDevice.deviceTypeId, GUI_CONFIG_PARENTDEVICEIDPROPERTYNAME, "")])
				if parent_device_id in self.managedDevices:
					parent_rp_device = self.managedDevices[parent_device_id]
					pdp_matcher = re.compile(r'%pdp:([a-z\d]+)%', re.IGNORECASE)
					for match in pdp_matcher.finditer(substituted_string):
						if type(parent_rp_device.indigoDevice.pluginProps.get(match.group(1), None)) is indigo.List:
							substituted_string = substituted_string.replace(to_unicode(match.group(0)), "'" + ','.join(parent_rp_device.indigoDevice.pluginProps.get(match.group(1))) + "'")
						else:
<<<<<<< HEAD
							substituted_string = substituted_string.replace(to_unicode(match.group(0)), to_unicode(parent_rp_device.indigoDevice.pluginProps.get(match.group(1), "")))
			
		# handle plugin preferences
		pp_matcher = re.compile(r'%pp:([a-z\d]+)%', re.IGNORECASE)
		for match in pp_matcher.finditer(substituted_string):
			substituted_string = substituted_string.replace(to_unicode(match.group(0)), to_unicode(self.pluginPrefs.get(match.group(1), "")))
			
		# perform the standard indigo values substitution...
		substituted_string = self.substitute(substituted_string)
		
		# return the new string to the caller
		return substituted_string
		
=======
							substitutedString = substitutedString.replace(to_unicode(match.group(0)), to_unicode(parentRPDevice.indigoDevice.pluginProps.get(match.group(1), u'')))

		# handle plugin preferences
		ppMatcher = re.compile(r'%pp:([a-z\d]+)%', re.IGNORECASE)
		for match in ppMatcher.finditer(substitutedString):
			substitutedString = substitutedString.replace(to_unicode(match.group(0)), to_unicode(self.pluginPrefs.get(match.group(1), u'')))

		# perform the standard indigo values substitution...
		substitutedString = self.substitute(substitutedString)

		# return the new string to the caller
		return substitutedString

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will set a GUI configuration value given the device type, the key and
	# the value for the device
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def putGUIConfigValue(self, deviceTypeId, configKey, configValue):
		if deviceTypeId not in self.managedDeviceGUIConfigs:
			self.managedDeviceGUIConfigs[deviceTypeId] = dict()
		self.managedDeviceGUIConfigs[deviceTypeId][configKey] = configValue

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will retrieve a GUI config value for a device type and key; it allows
	# passing in a default value in case the value is not found in the settings
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getGUIConfigValue(self, deviceTypeId, configKey, defaultValue=u''):
		if deviceTypeId not in self.managedDeviceGUIConfigs:
			return defaultValue
		elif configKey in self.managedDeviceGUIConfigs[deviceTypeId]:
			return self.managedDeviceGUIConfigs[deviceTypeId][configKey]
		else:
			self.logger.threaddebug(f"Returning default GUIConfigValue for {deviceTypeId}: {configKey}")
			return defaultValue

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will retrieve the list of device response definitions for the given
	# device type
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getDeviceResponseDefinitions(self, deviceTypeId):
		if deviceTypeId in self.deviceResponseDefinitions:
			return self.deviceResponseDefinitions[deviceTypeId]
		else:
			return ()

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will update the enumeratedDevices list of devices from the uPNP
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def updateUPNPEnumerationList(self, deviceTypeId):
<<<<<<< HEAD
		u_pnp_cache_time = int(self.getGUIConfigValue(deviceTypeId, GUI_CONFIG_UPNP_CACHETIMESEC, u'180'))
		if time.time() > self.lastDeviceEnumeration + u_pnp_cache_time or len(self.enumeratedDevices) == 0:
			service_id = self.getGUIConfigValue(deviceTypeId, GUI_CONFIG_UPNP_SERVICE, u'ssdp:all')
			self.logger.debug(f"Performing uPnP search for: {service_id}")
			discovered_devices = uPnPDiscover(service_id)
			self.logger.debug(f"Found {len(discovered_devices)} devices")
			
			self.enumeratedDevices     = discovered_devices
=======
		uPNPCacheTime = int(self.getGUIConfigValue(deviceTypeId, GUI_CONFIG_UPNP_CACHETIMESEC, u'180'))
		if time.time() > self.lastDeviceEnumeration + uPNPCacheTime or len(self.enumeratedDevices) == 0:
			serviceId = self.getGUIConfigValue(deviceTypeId, GUI_CONFIG_UPNP_SERVICE, u'ssdp:all')
			self.logger.debug(u'Performing uPnP search for: {0}'.format(serviceId))
			discoveredDevices = uPnPDiscover(serviceId)
			self.logger.debug(u'Found {0} devices'.format(len(discoveredDevices)))

			self.enumeratedDevices     = discoveredDevices
>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
			self.lastDeviceEnumeration = time.time()

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will get the full path to a file with the given name inside the plugin
	# directory; note this is specifically returning a string, not unicode, to allow
	# use of the IO libraries which require ascii
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getPluginDirectoryFilePath(self, fileName, pluginName = None):
		if pluginName is None:
			pluginName = self.pluginDisplayName.replace(' Plugin', '')
<<<<<<< HEAD
		indigo_base_path = indigo.server.getInstallFolderPath()
		
		requested_file_path = os.path.join(indigo_base_path, f"Plugins/{pluginName}.indigoPlugin/Contents/Server Plugin/{fileName}")
		return to_str(requested_file_path)
			
=======
		indigoBasePath = indigo.server.getInstallFolderPath()

		requestedFilePath = os.path.join(indigoBasePath, "Plugins/{0}.indigoPlugin/Contents/Server Plugin/{1}".format(pluginName, fileName))
		return to_str(requestedFilePath)

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called whenever the plugin is updating from an older version, as
	# determined by the plugin property and plugin version number
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def performPluginUpgradeMaintenance(self, oldVersion, newVersion):
		if oldVersion == "":
			self.logger.info(f"Performing first upgrade/run of version {newVersion}")
		else:
<<<<<<< HEAD
			self.logger.info(f"Performing upgrade from {oldVersion} to {newVersion}")
			
=======
			self.logger.info(u'Performing upgrade from {0} to {1}'.format(oldVersion, newVersion))

>>>>>>> 8bed37c927ff71608202bf8d5d539d06d0410327
		# remove any unwanted directories from the RPFramework
		plugin_base_path = os.getcwd()
		remove_paths = 	[	os.path.join(plugin_base_path, "RPFramework/requests"),
							os.path.join(plugin_base_path, "RPFramework/dataAccess")]
		for remove_path in remove_paths:
			try:
				if os.path.isdir(remove_path):
					self.logger.debug(f"Removing unused directory tree at {remove_path}")
					shutil.rmtree(remove_path)
				elif os.path.isfile(remove_path):
					os.remove(remove_path)
			except:
				self.logger.error(f"Failed to remove path during upgrade: {remove_path}")


		# allow the descendant classes to perform their own upgrade options
		self.performPluginUpgrade(oldVersion, newVersion)

		# update the version flag within our plugin
		self.pluginPrefs['loadedPluginVersion'] = newVersion
		self.savePluginPrefs()
		self.logger.info(u'Completed plugin updating/installation for {0}'.format(newVersion))

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine may be used by plugins to perform any upgrades specific to the plugin;
	# it will be called following the framework's update processing
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def performPluginUpgrade(self, oldVersion, newVersion):
		pass

	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////
