#! /usr/bin/env python
# -*- coding: utf-8 -*-
#/////////////////////////////////////////////////////////////////////////////////////////
# RPFrameworkCommand by RogueProeliator <adam.d.ashe@gmail.com>
# 	Class for all RogueProeliator's commands that request that an action be executed
#	on a processing thread.
#/////////////////////////////////////////////////////////////////////////////////////////

#/////////////////////////////////////////////////////////////////////////////////////////
#region Python Imports
import sys
#endregion
#/////////////////////////////////////////////////////////////////////////////////////////


#/////////////////////////////////////////////////////////////////////////////////////////
# RPFrameworkCommand
#	Class that allows communication of an action request between the plugin device and
#	its processing thread that is executing the actions/requests/communications
#/////////////////////////////////////////////////////////////////////////////////////////
class RPFrameworkCommand(object):

	#/////////////////////////////////////////////////////////////////////////////////////////
	#region Constants and Configuration Variables
	CMD_INITIALIZE_CONNECTION       = "INITIALIZECONNECTION"
	CMD_TERMINATE_PROCESSING_THREAD = "TERMINATEPROCESSING"
	CMD_PAUSE_PROCESSING            = "PAUSEPROCESSING"
	CMD_DOWNLOAD_UPDATE             = "DOWNLOADUPDATE"

	CMD_UPDATE_DEVICE_STATUS_FULL   = "UPDATEDEVICESTATUS_FULL"
	CMD_UPDATE_DEVICE_STATE         = "UPDATEDEVICESTATE"

	CMD_NETWORKING_WOL_REQUEST      = "SENDWOLREQUEST"
	CMD_DEVICE_RECONNECT            = "RECONNECTDEVICE"

	CMD_DEBUG_LOGUPNPDEVICES        = "LOGUPNPDEVICES"

	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////////
	
	#/////////////////////////////////////////////////////////////////////////////////////
	#region Construction and Destruction Methods
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor allows passing in the data that makes up the command
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, commandName, commandPayload=None, postCommandPause=0.0, parentAction=u''):
		self.commandName      = commandName
		self.commandPayload   = commandPayload
		self.postCommandPause = postCommandPause
		self.parentAction     = parentAction
	
	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////
		
	#/////////////////////////////////////////////////////////////////////////////////////
	#region Utility Methods
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Routine to return a list for the payload, converting a string to a list using the
	# provided delimiter when necessary
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getPayloadAsList(self, delim=u'|*|'):
		if isinstance(self.commandPayload, str) or isinstance(self.commandPayload, bytes):
			return self.commandPayload.split(delim)
		else:
			return self.commandPayload

	#endregion
	#/////////////////////////////////////////////////////////////////////////////////////
