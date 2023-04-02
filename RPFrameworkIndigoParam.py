#! /usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################################
# RPFrameworkIndigoParamDefn by RogueProeliator <adam.d.ashe@gmail.com>
# This class stores the definition of a parameter coming from Indigo - for an action,
# device configuration, plugin configuration, etc. It is used so that the base classes
# may automatically handle parameter functions (such as validation) that normally would
# have to be written into each plugin
#######################################################################################

# region Python Imports
import os
import re
import sys

import urllib.request as urlopen

try:
	import indigo
except:
	pass

from .RPFrameworkUtils import to_str

# endregion


class RPFrameworkIndigoParamDefn(object):

	#######################################################################################
	# region Constants and Configuration Variables
	ParamTypeInteger         = 0
	ParamTypeFloat           = 1
	ParamTypeBoolean         = 2
	ParamTypeString          = 3
	ParamTypeOSDirectoryPath = 4
	ParamTypeIPAddress       = 5
	ParamTypeList            = 6
	ParamTypeOSFilePath      = 7

	# endregion
	#######################################################################################
	
	#######################################################################################
	# region Construction and Destruction Methods
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor allows passing in the data that makes up the definition of the param_type
	# (with the type and ID being the only two required fields
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, indigo_id, param_type, is_required=False, default_value="", min_value=0, max_value=2147483647, validation_expression="", invalid_value_message=""):
		self.indigo_id             = indigo_id
		self.param_type            = param_type
		self.is_required           = is_required
		self.default_value         = default_value
		self.min_value             = min_value
		self.max_value             = max_value
		self.validation_expression = validation_expression
		self.invalid_value_message = invalid_value_message

	# endregion
	#######################################################################################
		
	#######################################################################################
	# region Validation Methods
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will return a boolean indicating if the provided value is valid
	# according to the parameter type and configuration. It is assumed that the proposed
	# value will always be a string!
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def is_value_valid(self, proposed_value):
		# if the value is required but empty then error here
		if proposed_value is None or proposed_value == "":
			return not self.is_required
		
		# now validate that the type is correct...
		if self.param_type == RPFrameworkIndigoParamDefn.ParamTypeInteger:
			try:
				proposed_int_value = int(proposed_value)
				if proposed_int_value < self.min_value or proposed_int_value > self.max_value:
					raise "Param value not in range"
				return True
			except:
				return False
				
		elif self.param_type == RPFrameworkIndigoParamDefn.ParamTypeFloat:
			try:
				proposed_flt_value = float(proposed_value)
				if proposed_flt_value < self.min_value or proposed_flt_value > self.max_value:
					raise "Param value not in range"
				return True
			except:
				return False
				
		elif self.param_type == RPFrameworkIndigoParamDefn.ParamTypeBoolean:
			if type(proposed_value) is bool:
				return True
			else:
				return proposed_value.lower() == "true"
			
		elif self.param_type == RPFrameworkIndigoParamDefn.ParamTypeOSDirectoryPath:
			# validate that the path exists... and that it is a directory
			return os.path.isdir(to_str(proposed_value))
			
		elif self.param_type == RPFrameworkIndigoParamDefn.ParamTypeOSFilePath:
			# validate that the file exists (and that it is a file)
			return os.path.isfile(to_str(proposed_value))
		
		elif self.param_type == RPFrameworkIndigoParamDefn.ParamTypeIPAddress:
			# validate the IP address using IPv4 standards for now...
			return self.is_i_pv4_valid(to_str(proposed_value))
			
		elif self.param_type == RPFrameworkIndigoParamDefn.ParamTypeList:
			# validate that the list contains between the minimum and maximum
			# number of entries
			if len(proposed_value) < self.min_value or len(proposed_value) > self.max_value:
				return False
			else:
				return True
			
		else:
			# default is a string value... so this will need to check against the
			# validation expression, if set, and string length
			if self.validation_expression != "":
				if re.search(self.validation_expression, proposed_value, re.I) is None:
					return False
					
			str_length = len(proposed_value)
			if str_length < self.min_value or str_length > self.max_value:
				return False
				
			# if string processing makes it here then all is good
			return True
			
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will validate whether or not an IP address is valid as a IPv4 addr
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def is_i_pv4_valid(self, ip):
		# make sure a value was entered for the address... an IPv4 should require at least
		# 7 characters (0.0.0.0)
		if len(ip) < 7:
			return False
			
		# separate the IP address into its components... this limits the format for the
		# user input but is using a fairly standard notation so acceptable
		address_parts = ip.split(".")
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
