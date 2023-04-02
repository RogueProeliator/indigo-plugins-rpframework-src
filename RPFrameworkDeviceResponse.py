#! /usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################################
# RPFrameworkDeviceResponse by RogueProeliator <adam.d.ashe@gmail.com>
# Class for all RogueProeliator's "incoming" responses such that they may be
# automatically processed by base classes
#######################################################################################

# region Python imports
from __future__ import absolute_import
import re

try:
	import indigo
except:
	pass

from .RPFrameworkCommand import RPFrameworkCommand
from .RPFrameworkUtils   import is_string_type
from .RPFrameworkUtils   import to_unicode
# endregion


class RPFrameworkDeviceResponse(object):

	#######################################################################################
	# region Constants and Configuration Variables
	RESPONSE_EFFECT_UPDATESTATE  = "updateDeviceState"
	RESPONSE_EFFECT_QUEUECOMMAND = "queueCommand"
	RESPONSE_EFFECT_CALLBACK     = "eventCallback"

	# endregion
	#######################################################################################
	
	#######################################################################################
	# region Construction and Destruction Methods
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor allows passing in the data that makes up the response object
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, response_id, criteria_format_string, match_expression, respond_to_action_id=""):
		self.response_id            = response_id
		self.criteria_format_string = criteria_format_string
		self.respond_to_action_id   = respond_to_action_id
		self.match_expression       = match_expression
		self.match_result_effects   = list()

	# endregion
	#######################################################################################
	
	#######################################################################################
	# region Effect Definition Functions
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Allows an outside class to add a new effect to this response object
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def add_response_effect(self, effect):
		self.match_result_effects.append(effect)

	# endregion
	#######################################################################################

	#######################################################################################
	# region Testing and Execution Functions
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will test the given input to determine if it is a match for the
	# response definition
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def is_response_match(self, response_obj, rp_command, rp_device, rp_plugin):
		if self.criteria_format_string is None or self.criteria_format_string == "" or self.match_expression is None or self.match_expression == "":
			# we only need to look at the action...
			if self.respond_to_action_id == "" or rp_command.parent_action is None:
				return True
			elif is_string_type(rp_command.parent_action):
				return self.respond_to_action_id == rp_command.parent_action
			else:
				return self.respond_to_action_id == rp_command.parent_action.indigoActionId
				
		match_criteria_test = self.substitute_criteria_format_string(self.criteria_format_string, response_obj, rp_command, rp_device, rp_plugin)
		match_obj           = re.match(self.match_expression, match_criteria_test, re.I)
		return (match_obj is not None) and (self.respond_to_action_id == "" or self.respond_to_action_id == rp_command.parent_action.indigoActionId)
	
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will generate the criteria to test based upon the response and the
	# response definition criteria
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def substitute_criteria_format_string(self, format_string, response_obj, rp_command, rp_device, rp_plugin):
		substituted_criteria = format_string
		if substituted_criteria is None:
			return ""
		
		# substitute the response/command object values as those are
		# specific to commands
		if rp_command is not None:
			substituted_criteria = substituted_criteria.replace("%cp:name%", rp_command.command_name)
			substituted_criteria = substituted_criteria.replace("%cp:payload%", to_unicode(rp_command.command_payload))
		
		if is_string_type(response_obj):
			substituted_criteria = substituted_criteria.replace("%cp:response%", response_obj)
		
		# substitute the standard RPFramework substitutions
		substituted_criteria = rp_plugin.substitute_indigo_values(substituted_criteria, rp_device, None)
		
		# return the result back to the caller
		return substituted_criteria
			
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will execute the effects of the response; it is assuming that it is
	# a match (it will not re-match)
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def execute_effects(self, response_obj, rp_command, rp_device, rp_plugin):
		for effect in self.match_result_effects:
			# first we need to determine if this effect should be executed (based upon a condition; by default all
			# effects will be executed!)
			if effect.update_exec_condition is not None and effect.update_exec_condition != "":
				# this should eval to a boolean value
				if not eval(rp_plugin.substitute_indigo_values(effect.update_exec_condition, rp_device, dict())):
					rp_plugin.logger.threaddebug(f"Execute condition failed for response, skipping execution for effect: {effect.effect_type}")
					continue
		
			# processing for this effect is dependent upon the type
			try:
				if effect.effect_type == RPFrameworkDeviceResponse.RESPONSE_EFFECT_UPDATESTATE:
					# this effect should update a device state (param) with a value as formatted
					new_state_value_string = self.substitute_criteria_format_string(effect.update_value_format_string, response_obj, rp_command, rp_device, rp_plugin)
					if effect.eval_update_value:
						new_state_value = eval(new_state_value_string)
					else:
						new_state_value = new_state_value_string
						
					# the effect may have a UI value set... if not leave at an empty string so that
					# we don't attempt to update it
					new_state_ui_value = ""
					if effect.update_value_format_ex_string != u"":
						new_state_ui_value_string = self.substitute_criteria_format_string(effect.update_value_format_ex_string, response_obj, rp_command, rp_device, rp_plugin)
						if effect.eval_update_value:
							new_state_ui_value = eval(new_state_ui_value_string)
						else:
							new_state_ui_value = new_state_ui_value_string
				
					# update the state...
					if new_state_ui_value == "":
						rp_plugin.logger.debug(f"Effect execution: Update state '{effect.update_param}' to '{new_state_value}'")
						rp_device.indigoDevice.updateStateOnServer(key=effect.update_param, value=new_state_value)
					else:
						rp_plugin.logger.debug(f"Effect execution: Update state '{effect.update_param}' to '{new_state_value}' with UIValue '{new_state_ui_value}'")
						rp_device.indigoDevice.updateStateOnServer(key=effect.update_param, value=new_state_value, uiValue=new_state_ui_value)
				
				elif effect.effect_type == RPFrameworkDeviceResponse.RESPONSE_EFFECT_QUEUECOMMAND:
					# this effect will enqueue a new command... the update_param will define the command name
					# and the updateValueFormat will define the new payload
					queue_command_name = self.substitute_criteria_format_string(effect.update_param, response_obj, rp_command, rp_device, rp_plugin)

					queue_command_payload_str = self.substitute_criteria_format_string(effect.update_value_format_string, response_obj, rp_command, rp_device, rp_plugin)
					if effect.eval_update_value:
						queue_command_payload = eval(queue_command_payload_str)
					else:
						queue_command_payload = queue_command_payload_str
				
					rp_plugin.logger.debug(f"Effect execution: Queuing command {queue_command_name}")
					rp_device.queue_device_command(RPFrameworkCommand(queue_command_name, queue_command_payload))
				
				elif effect.effect_type == RPFrameworkDeviceResponse.RESPONSE_EFFECT_CALLBACK:
					# this should kick off a callback to a python call on the device...
					rp_plugin.logger.debug(f"Effect execution: Calling function {effect.update_param}")
					eval(f"rpDevice.{effect.update_param}(responseObj, rpCommand)")
			except:
				rp_plugin.logger.exception(f"Error executing effect for device id {rp_device.indigoDevice.id}")

	# endregion
	#######################################################################################
	

class RPFrameworkDeviceResponseEffect(object):
	
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor allows passing in the data that makes up the response object
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, effect_type, update_param, update_value_format_string="", update_value_format_ex_string="", eval_update_value=False, update_exec_condition=None):
		self.effect_type                   = effect_type
		self.update_param                  = update_param
		self.update_value_format_string    = update_value_format_string
		self.update_value_format_ex_string = update_value_format_ex_string
		self.eval_update_value             = eval_update_value
		self.update_exec_condition         = update_exec_condition
		
		