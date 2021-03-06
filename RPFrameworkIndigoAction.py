#! /usr/bin/env python
# -*- coding: utf-8 -*-
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# RPFrameworkIndigoActionDfn by RogueProeliator <adam.d.ashe@gmail.com>
# 	This class defines an action available to the user/processed by the plugin in a
#	standard manner such that the base classes in the framework are able to process many
#	actions automatically w/o custom writing them for each plugin.
#/////////////////////////////////////////////////////////////////////////////////////////
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
#/////////////////////////////////////////////////////////////////////////////////////////
# RPFrameworkIndigoParamDefn
#	This class stores the definition of a parameter coming from Indigo - for an action,
#	device configuration, plugin configuration, etc.
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
class RPFrameworkIndigoActionDfn(object):
	
	#/////////////////////////////////////////////////////////////////////////////////////
	#region Construction and Destruction Methods
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor allows passing in the data that makes up the definition of the action
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, indigoActionId, commandName = u'', commandParamFormatString = u'', commandExecuteCount=u'1', indigoParams=None):
		self.indigoActionId = indigoActionId
		
		self.actionCommands = []
		if commandName != u'' and commandParamFormatString != u'':
			self.actionCommands.append((commandName, commandParamFormatString, commandExecuteCount, u'', u''))
		
		self.indigoParams = indigoParams
		if self.indigoParams == None:
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
	def addIndigoCommand(self, commandName, commandFormatString, commandExecuteCount=u'1', commandRepeatDelay=u'', commandExecuteCondition=u''):
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
		errorMessages = indigo.Dict()
		
		# loop through each parameter for this action and validate one-by-one
		for param in self.indigoParams:
			if param.indigoId in paramValues:
				# a parameter value is present, validate it now
				if param.isValueValid(paramValues[param.indigoId]) == False:
					errorMessages[param.indigoId] = param.invalidValueMessage
					
			elif param.isRequired == True:
				errorMessages[param.indigoId] = param.invalidValueMessage
				
		# return the validation results...
		if len(errorMessages) == 0:
			return (True, paramValues)
		else:
			return (False, paramValues, errorMessages)

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
		validationResults = self.validateActionValues(paramValues)
		if validationResults[0] == False:
			rpPlugin.logger.error(u'Invalid values sent for action {0}; the following errors were found:'.format(self.indigoActionId))
			rpPlugin.logger.error(to_unicode(validationResults[2]))
			return
		
		# determine the list of parameter values based upon the parameter definitions
		# and the values provided (these will be used during substitutions below)
		resolvedValues = dict()
		for rpParam in self.indigoParams:
			resolvedValues[rpParam.indigoId] = paramValues.get(rpParam.indigoId, rpParam.defaultValue)

		# generate the command for each of the ones defined for this action
		commandsToQueue = []
		for (commandName, commandFormatString, commandExecuteCount, repeatCommandDelay, executeCondition) in self.actionCommands:
			# this command may have an execute condition which could prevent the command
			# from firing...
			if executeCondition != None and executeCondition != u'':
				# this should eval to a boolean value
				if eval(rpPlugin.substituteIndigoValues(executeCondition, rpDevice, resolvedValues)) == False:
					rpPlugin.logger.threaddebug(u'Execute condition failed, skipping execution for command: {0}'.format(commandName))
					continue
		
			# determine the number of times to execute this command (supports sending the same request
			# multiple times in a row)
			executeTimesStr = rpPlugin.substituteIndigoValues(commandExecuteCount, rpDevice, resolvedValues)
			if executeTimesStr.startswith(u'eval:'):
				executeTimesStr = eval(executeTimesStr.replace(u'eval:', u''))
			if executeTimesStr == None or executeTimesStr == u'':
				executeTimesStr = u'1'
			executeTimes = int(executeTimesStr)
		
			# create a new command for each of the count requested...
			for i in range(0,executeTimes):
				# create the payload based upon the format string provided for the command
				payload = rpPlugin.substituteIndigoValues(commandFormatString, rpDevice, resolvedValues)
				if payload.startswith(u'eval:'):
					payload = eval(payload.replace(u'eval:', u''))
				
				# determine the delay that should be added after the command (delay between repeats)
				delayTimeStr = rpPlugin.substituteIndigoValues(repeatCommandDelay, rpDevice, resolvedValues)
				delayTime = 0.0
				if executeTimes > 1 and delayTimeStr != u'':
					delayTime = float(delayTimeStr)
			
				# create and add the command to the queue
				commandsToQueue.append(RPFrameworkCommand.RPFrameworkCommand(commandName, commandPayload=payload, postCommandPause=delayTime, parentAction=self))
			
		# if the execution made it here then the list of commands has been successfully built without
		# error and may be queued up on the device
		for commandForDevice in commandsToQueue:
			rpDevice.queueDeviceCommand(commandForDevice)

	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////