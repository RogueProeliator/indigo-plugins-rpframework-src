#! /usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################################
# RPFrameworkCommand by RogueProeliator <adam.d.ashe@gmail.com>
# Class for all RogueProeliator's commands that request that an action be executed
# on a processing thread.
#######################################################################################


class RPFrameworkCommand(object):

	#######################################################################################
	# region Constants and Configuration Variables
	CMD_INITIALIZE_CONNECTION       = "INITIALIZECONNECTION"
	CMD_TERMINATE_PROCESSING_THREAD = "TERMINATEPROCESSING"
	CMD_PAUSE_PROCESSING            = "PAUSEPROCESSING"
	CMD_DOWNLOAD_UPDATE             = "DOWNLOADUPDATE"

	CMD_UPDATE_DEVICE_STATUS_FULL   = "UPDATEDEVICESTATUS_FULL"
	CMD_UPDATE_DEVICE_STATE         = "UPDATEDEVICESTATE"

	CMD_NETWORKING_WOL_REQUEST      = "SENDWOLREQUEST"
	CMD_DEVICE_RECONNECT            = "RECONNECTDEVICE"

	CMD_DEBUG_LOGUPNPDEVICES        = "LOGUPNPDEVICES"

	# endregion
	#######################################################################################
	
	#######################################################################################
	# region Construction and Destruction Methods
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor allows passing in the data that makes up the command
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, command_name, command_payload=None, post_command_pause=0.0, parent_action=""):
		self.command_name       = command_name
		self.command_payload    = command_payload
		self.post_command_pause = post_command_pause
		self.parent_action      = parent_action
	
	# endregion
	#######################################################################################
		
	#######################################################################################
	# region Utility Methods
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Routine to return a list for the payload, converting a string to a list using the
	# provided delimiter when necessary
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def get_payload_as_list(self, delim="|*|"):
		if isinstance(self.command_payload, str) or isinstance(self.command_payload, bytes):
			return self.command_payload.split(delim)
		else:
			return self.command_payload

	# endregion
	#######################################################################################
