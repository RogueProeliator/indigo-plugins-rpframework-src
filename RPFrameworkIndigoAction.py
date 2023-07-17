#! /usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################################
# RPFrameworkIndigoActionDfn by RogueProeliator <adam.d.ashe@gmail.com>
# This class defines an action available to the user/processed by the plugin in a
# standard manner such that the base classes in the framework are able to process many
# actions automatically w/o custom writing them for each plugin.
#######################################################################################

# region Python Imports
from __future__ import absolute_import
try:
	import indigo
except:
	pass
from .RPFrameworkCommand import RPFrameworkCommand
from .RPFrameworkUtils   import to_unicode

# endregion


class RPFrameworkIndigoActionDfn(object):
	
	#######################################################################################
	# region Construction and Destruction Methods
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor allows passing in the data that makes up the definition of the action
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, indigo_action_id, command_name="", command_param_format_string="", command_execute_count="1", indigo_params=None):
		self.indigoActionId = indigo_action_id
		
		self.actionCommands = []
		if command_name != "" and command_param_format_string != "":
			self.actionCommands.append((command_name, command_param_format_string, command_execute_count, "", ""))
		
		self.indigo_params = indigo_params
		if self.indigo_params is None:
			self.indigo_params = []
	
	# endregion
	#######################################################################################
	
	#######################################################################################
	# region Parameter Definition Functions
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Allows an outside class to add a new parameter for this action
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def add_indigo_parameter(self, indigo_param):
		self.indigo_params.append(indigo_param)
		
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Allows an outside class to add a new command to be sent for this action. The
	# commands will be sent in the order received
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def add_indigo_command(self, command_name, command_format_string, command_execute_count="1", commandRepeatDelay="", command_execute_condition=""):
		self.actionCommands.append((command_name, command_format_string, command_execute_count, commandRepeatDelay, command_execute_condition))

	# endregion
	#######################################################################################
		
	#######################################################################################
	# region Validation routines
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine validates the action against a set of values for the parameters of the
	# action; the return is the same as the validation for Indigo call-backs:
	# 	(True|False, valuesDict, ErrorMessageDict)
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def validate_action_values(self, param_values):
		error_messages = indigo.Dict()
		
		# loop through each parameter for this action and validate one-by-one
		for param in self.indigo_params:
			if param.indigo_id in param_values:
				# a parameter value is present, validate it now
				if not param.is_value_valid(param_values[param.indigo_id]):
					error_messages[param.indigo_id] = param.invalid_value_message
					
			elif param.is_required:
				error_messages[param.indigo_id] = param.invalid_value_message
				
		# return the validation results...
		if len(error_messages) == 0:
			return True, param_values
		else:
			return False, param_values, error_messages

	# endregion
	#######################################################################################
			
	#######################################################################################
	# region Action Execution Routines
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will allow the base plugin to execute the action, generating the
	# command(s) that will be passed to the device's command queue
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def generate_action_commands(self, rp_plugin, rp_device, param_values):
		# validate that the values sent in are valid for this action
		validation_results = self.validate_action_values(param_values)
		if not validation_results[0]:
			rp_plugin.logger.error(f"Invalid values sent for action {self.indigoActionId}; the following errors were found:")
			rp_plugin.logger.error(to_unicode(validation_results[2]))
			return
		
		# determine the list of parameter values based upon the parameter definitions
		# and the values provided (these will be used during substitutions below)
		resolved_values = dict()
		for rp_param in self.indigo_params:
			resolved_values[rp_param.indigo_id] = param_values.get(rp_param.indigo_id, rp_param.default_value)

		# generate the command for each of the ones defined for this action
		commands_to_queue = []
		for (commandName, commandFormatString, commandExecuteCount, repeatCommandDelay, executeCondition) in self.actionCommands:
			# this command may have an execute condition which could prevent the command
			# from firing...
			if executeCondition is not None and executeCondition != "":
				# this should eval to a boolean value
				if not eval(rp_plugin.substitute_indigo_values(executeCondition, rp_device, resolved_values)):
					rp_plugin.logger.threaddebug(f"Execute condition failed, skipping execution for command: {commandName}")
					continue
		
			# determine the number of times to execute this command (supports sending the same request
			# multiple times in a row)
			execute_times_str = rp_plugin.substitute_indigo_values(commandExecuteCount, rp_device, resolved_values)
			if execute_times_str.startswith(u'eval:'):
				execute_times_str = eval(execute_times_str.replace("eval:", ""))
			if execute_times_str is None or execute_times_str == "":
				execute_times_str = "1"
			execute_times = int(execute_times_str)
		
			# create a new command for each of the count requested...
			for i in range(0, execute_times):
				# create the payload based upon the format string provided for the command
				payload = rp_plugin.substitute_indigo_values(commandFormatString, rp_device, resolved_values)
				if payload.startswith("eval:"):
					payload = eval(payload.replace("eval:", ""))
				
				# determine the delay that should be added after the command (delay between repeats)
				delay_time_str = rp_plugin.substitute_indigo_values(repeatCommandDelay, rp_device, resolved_values)
				delay_time = 0.0
				if execute_times > 1 and delay_time_str != "":
					delay_time = float(delay_time_str)
			
				# create and add the command to the queue
				commands_to_queue.append(RPFrameworkCommand(commandName, command_payload=payload, post_command_pause=delay_time, parent_action=self))
			
		# if the execution made it here then the list of commands has been successfully built without
		# error and may be queued up on the device
		for commandForDevice in commands_to_queue:
			rp_device.queue_device_command(commandForDevice)

	# endregion
	#######################################################################################
