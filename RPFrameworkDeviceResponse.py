#! /usr/bin/env python
# -*- coding: utf-8 -*-
#/////////////////////////////////////////////////////////////////////////////////////////
# RPFrameworkDeviceResponse by RogueProeliator <adam.d.ashe@gmail.com>
# 	Class for all RogueProeliator's "incoming" responses such that they may be
#	automatically processed by base classes
#/////////////////////////////////////////////////////////////////////////////////////////

#/////////////////////////////////////////////////////////////////////////////////////////
#region Python imports
from __future__ import absolute_import
import re

try:
	import indigo
except:
	pass

from .RPFrameworkCommand import RPFrameworkCommand
from .RPFrameworkUtils   import is_string_type
from .RPFrameworkUtils   import to_unicode

#endregion
#/////////////////////////////////////////////////////////////////////////////////////////

#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# RPFrameworkDeviceResponse
#	Class for all RogueProeliator's "incoming" responses such that they may be
#	automatically processed by base classes
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
class RPFrameworkDeviceResponse(object):

	#/////////////////////////////////////////////////////////////////////////////////////////
	#region Constants and Configuration Variables
	RESPONSE_EFFECT_UPDATESTATE  = "updateDeviceState"
	RESPONSE_EFFECT_QUEUECOMMAND = "queueCommand"
	RESPONSE_EFFECT_CALLBACK     = "eventCallback"

	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////////
	
	#/////////////////////////////////////////////////////////////////////////////////////
	#region Construction and Destruction Methods
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor allows passing in the data that makes up the response object
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, responseId, criteriaFormatString, matchExpression, respondToActionId=u''):
		self.responseId           = responseId
		self.criteriaFormatString = criteriaFormatString
		self.respondToActionId    = respondToActionId
		self.matchExpression      = matchExpression
		self.matchResultEffects   = list()

	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////	
	
	#/////////////////////////////////////////////////////////////////////////////////////
	#region Effect Definition Functions
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Allows an outside class to add a new effect to this response object
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def addResponseEffect(self, effect):
		self.matchResultEffects.append(effect)

	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////	
	
	#/////////////////////////////////////////////////////////////////////////////////////
	#region Testing and Execution Functions
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will test the given input to determine if it is a match for the
	# response definition
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def isResponseMatch(self, responseObj, rpCommand, rpDevice, rpPlugin):
		if self.criteriaFormatString is None or self.criteriaFormatString == "" or self.matchExpression is None or self.matchExpression == "":
			# we only need to look at the action...
			if self.respondToActionId == "" or rpCommand.parentAction is None:
				return True
			elif is_string_type(rpCommand.parentAction):
				return self.respondToActionId == rpCommand.parentAction
			else:
				return self.respondToActionId == rpCommand.parentAction.indigoActionId
				
		match_criteria_test = self.substituteCriteriaFormatString(self.criteriaFormatString, responseObj, rpCommand, rpDevice, rpPlugin)
		match_obj           = re.match(self.matchExpression, match_criteria_test, re.I)
		return (match_obj is not None) and (self.respondToActionId == "" or self.respondToActionId == rpCommand.parentAction.indigoActionId)
	
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will generate the criteria to test based upon the response and the
	# response definition criteria
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def substituteCriteriaFormatString(self, formatString, responseObj, rpCommand, rpDevice, rpPlugin):
		substituted_criteria = formatString
		if substituted_criteria is None:
			return ""
		
		# substitute the response/command object values as those are
		# specific to commands
		if rpCommand is not None:
			substituted_criteria = substituted_criteria.replace("%cp:name%", rpCommand.commandName)
			substituted_criteria = substituted_criteria.replace("%cp:payload%", to_unicode(rpCommand.commandPayload))
		
		if is_string_type(responseObj):
			substituted_criteria = substituted_criteria.replace("%cp:response%", responseObj)
		
		# substitute the standard RPFramework substitutions
		substituted_criteria = rpPlugin.substitute_indigo_values(substituted_criteria, rpDevice, None)
		
		#return the result back to the caller
		return substituted_criteria
			
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will execute the effects of the response; it is assuming that it is
	# a match (it will not re-match)
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def executeEffects(self, responseObj, rpCommand, rpDevice, rpPlugin):
		for effect in self.matchResultEffects:
			# first we need to determine if this effect should be executed (based upon a condition; by default all
			# effects will be executed!)
			if effect.updateExecCondition is not None and effect.updateExecCondition != "":
				# this should eval to a boolean value
				if not eval(rpPlugin.substitute_indigo_values(effect.updateExecCondition, rpDevice, dict())):
					rpPlugin.logger.threaddebug(f"Execute condition failed for response, skipping execution for effect: {effect.effectType}")
					continue
		
			# processing for this effect is dependent upon the type
			try:
				if effect.effectType == RPFrameworkDeviceResponse.RESPONSE_EFFECT_UPDATESTATE:
					# this effect should update a device state (param) with a value as formatted
					new_state_value_string = self.substituteCriteriaFormatString(effect.updateValueFormatString, responseObj, rpCommand, rpDevice, rpPlugin)
					if effect.evalUpdateValue:
						new_state_value = eval(new_state_value_string)
					else:
						new_state_value = new_state_value_string
						
					# the effect may have a UI value set... if not leave at an empty string so that
					# we don't attempt to update it
					new_state_ui_value = ""
					if effect.updateValueFormatExString != u"":
						new_state_ui_value_string = self.substituteCriteriaFormatString(effect.updateValueFormatExString, responseObj, rpCommand, rpDevice, rpPlugin)
						if effect.evalUpdateValue:
							new_state_ui_value = eval(new_state_ui_value_string)
						else:
							new_state_ui_value = new_state_ui_value_string
				
					# update the state...
					if new_state_ui_value == "":
						rpPlugin.logger.debug(f"Effect execution: Update state '{effect.updateParam}' to '{new_state_value}'")
						rpDevice.indigoDevice.updateStateOnServer(key=effect.updateParam, value=new_state_value)
					else:
						rpPlugin.logger.debug(f"Effect execution: Update state '{effect.updateParam}' to '{new_state_value}' with UIValue '{new_state_ui_value}'")
						rpDevice.indigoDevice.updateStateOnServer(key=effect.updateParam, value=new_state_value, uiValue=new_state_ui_value)
				
				elif effect.effectType == RPFrameworkDeviceResponse.RESPONSE_EFFECT_QUEUECOMMAND:
					# this effect will enqueue a new command... the updateParam will define the command name
					# and the updateValueFormat will define the new payload
					queue_command_name = self.substituteCriteriaFormatString(effect.updateParam, responseObj, rpCommand, rpDevice, rpPlugin)

					queue_command_payload_str = self.substituteCriteriaFormatString(effect.updateValueFormatString, responseObj, rpCommand, rpDevice, rpPlugin)
					if effect.evalUpdateValue:
						queue_command_payload = eval(queue_command_payload_str)
					else:
						queue_command_payload = queue_command_payload_str
				
					rpPlugin.logger.debug(f"Effect execution: Queuing command {queue_command_name}")
					rpDevice.queueDeviceCommand(RPFrameworkCommand.RPFrameworkCommand(queue_command_name, queue_command_payload))
				
				elif effect.effectType == RPFrameworkDeviceResponse.RESPONSE_EFFECT_CALLBACK:
					# this should kick off a callback to a python call on the device...
					rpPlugin.logger.debug(f"Effect execution: Calling function {effect.updateParam}")
					eval(f"rpDevice.{effect.updateParam}(responseObj, rpCommand)")
			except:
				rpPlugin.logger.exception(f"Error executing effect for device id {rpDevice.indigoDevice.id}")

	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////			
	

#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# RPFrameworkDeviceResponseEffect
#	Class that defines the effects that a match against the device response will enact;
#	these are things such as updating a device state, firing an event, etc.
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
class RPFrameworkDeviceResponseEffect(object):
	
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor allows passing in the data that makes up the response object
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, effectType, updateParam, updateValueFormatString=u'', updateValueFormatExString=u'', evalUpdateValue=False, updateExecCondition=None):
		self.effectType                = effectType
		self.updateParam               = updateParam
		self.updateValueFormatString   = updateValueFormatString
		self.updateValueFormatExString = updateValueFormatExString
		self.evalUpdateValue           = evalUpdateValue
		self.updateExecCondition       = updateExecCondition
		
		