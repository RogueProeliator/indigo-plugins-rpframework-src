#! /usr/bin/env python
# -*- coding: utf-8 -*-
#/////////////////////////////////////////////////////////////////////////////////////////
# RPFrameworkIndigoActionDfn by RogueProeliator <adam.d.ashe@gmail.com>
# 	This class defines an action available to the user/processed by the plugin in a
#	standard manner such that the base classes in the framework are able to process many
#	actions automatically w/o custom writing them for each plugin.
#/////////////////////////////////////////////////////////////////////////////////////////

#/////////////////////////////////////////////////////////////////////////////////////////
#region Python Imports
from __future__ import absolute_import

try:
	import indigo
except:
	pass

from .RPFrameworkCommand import RPFrameworkCommand
from .RPFrameworkUtils   import to_unicode

#endregion
#/////////////////////////////////////////////////////////////////////////////////////////

#/////////////////////////////////////////////////////////////////////////////////////////
# RPFrameworkIndigoParamDefn
#	This class stores the definition of a parameter coming from Indigo - for an action,
#	device configuration, plugin configuration, etc.
#/////////////////////////////////////////////////////////////////////////////////////////
class RPFrameworkIndigoActionDfn(object):
	
	#/////////////////////////////////////////////////////////////////////////////////////
	#region Construction and Destruction Methods
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor allows passing in the data that makes up the definition of the action
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, indigoActionId, commandName = "", commandParamFormatString = "", commandExecuteCount="1", indigoParams=None):
		self.indigoActionId = indigoActionId
		
		self.actionCommands = []
		if commandName != "" and commandParamFormatString != "":
			self.actionCommands.append((commandName, commandParamFormatString, commandExecuteCount, "", ""))
		
		self.indigoParams = indigoParams
		if self.indigoParams is None:
			self.indigoParams = []
	
	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////
	
	#/////////////////////////////////////////////////////////////////////////////////////
	#region Parameter Definition Functions
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Allows an outside class to add a new parameter for this action
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def addIndigoParameter(self, indigoParam):
		self.indigoParams.append(indigoParam)
		
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Allows an outside class to add a new command to be sent for this action. The
	# commands will be sent in the order received
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def addIndigoCommand(self, commandName, commandFormatString, commandExecuteCount="1", commandRepeatDelay="", commandExecuteCondition=""):
		self.actionCommands.append((commandName, commandFormatString, commandExecuteCount, commandRepeatDelay, commandExecuteCondition))

	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////	
		
	#/////////////////////////////////////////////////////////////////////////////////////
	#region Validation routines
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine validates the action against a set of values for the parameters of the
	# action; the return is the same as the validation for Indigo call-backs:
	# 	(True|False, valuesDict, ErrorMessageDict)
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def validateActionValues(self, paramValues):
		error_messages = indigo.Dict()
		
		# loop through each parameter for this action and validate one-by-one
		for param in self.indigoParams:
			if param.indigoId in paramValues:
				# a parameter value is present, validate it now
				if not param.isValueValid(paramValues[param.indigoId]):
					error_messages[param.indigoId] = param.invalidValueMessage
					
			elif param.isRequired:
				error_messages[param.indigoId] = param.invalidValueMessage
				
		# return the validation results...
		if len(error_messages) == 0:
			return True, paramValues
		else:
			return False, paramValues, error_messages

	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////		
			
	#/////////////////////////////////////////////////////////////////////////////////////
	#region Action Execution Routines
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will allow the base plugin to execute the action, generating the
	# command(s) that will be passed to the device's command queue
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def generateActionCommands(self, rpPlugin, rpDevice, paramValues):
		# validate that the values sent in are valid for this action
		validation_results = self.validateActionValues(paramValues)
		if not validation_results[0]:
			rpPlugin.logger.error(f"Invalid values sent for action {self.indigoActionId}; the following errors were found:")
			rpPlugin.logger.error(to_unicode(validation_results[2]))
			return
		
		# determine the list of parameter values based upon the parameter definitions
		# and the values provided (these will be used during substitutions below)
		resolved_values = dict()
		for rpParam in self.indigoParams:
			resolved_values[rpParam.indigoId] = paramValues.get(rpParam.indigoId, rpParam.defaultValue)

		# generate the command for each of the ones defined for this action
		commands_to_queue = []
		for (commandName, commandFormatString, commandExecuteCount, repeatCommandDelay, executeCondition) in self.actionCommands:
			# this command may have an execute condition which could prevent the command
			# from firing...
			if executeCondition is not None and executeCondition != "":
				# this should eval to a boolean value
				if not eval(rpPlugin.substitute_indigo_values(executeCondition, rpDevice, resolved_values)):
					rpPlugin.logger.threaddebug(f"Execute condition failed, skipping execution for command: {commandName}")
					continue
		
			# determine the number of times to execute this command (supports sending the same request
			# multiple times in a row)
			execute_times_str = rpPlugin.substitute_indigo_values(commandExecuteCount, rpDevice, resolved_values)
			if execute_times_str.startswith(u'eval:'):
				execute_times_str = eval(execute_times_str.replace("eval:", ""))
			if execute_times_str is None or execute_times_str == "":
				execute_times_str = "1"
			execute_times = int(execute_times_str)
		
			# create a new command for each of the count requested...
			for i in range(0, execute_times):
				# create the payload based upon the format string provided for the command
				payload = rpPlugin.substitute_indigo_values(commandFormatString, rpDevice, resolved_values)
				if payload.startswith("eval:"):
					payload = eval(payload.replace("eval:", ""))
				
				# determine the delay that should be added after the command (delay between repeats)
				delay_time_str = rpPlugin.substitute_indigo_values(repeatCommandDelay, rpDevice, resolved_values)
				delay_time = 0.0
				if execute_times > 1 and delay_time_str != "":
					delay_time = float(delay_time_str)
			
				# create and add the command to the queue
				commands_to_queue.append(RPFrameworkCommand.RPFrameworkCommand(commandName, commandPayload=payload, postCommandPause=delay_time, parentAction=self))
			
		# if the execution made it here then the list of commands has been successfully built without
		# error and may be queued up on the device
		for commandForDevice in commands_to_queue:
			rpDevice.queueDeviceCommand(commandForDevice)

	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////