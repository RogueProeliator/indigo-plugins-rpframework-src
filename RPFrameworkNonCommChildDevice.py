#! /usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################################
# RPFrameworkNonCommChildDevice by RogueProeliator <adam.d.ashe@gmail.com>
# Base class for all RogueProeliator's devices which do not actively communicate but
# rather function to pass commands along to a parent device; examples would be zones
# indigo a multi-room audio system or zones in an alarm panel
#######################################################################################

# region Python imports
from __future__ import absolute_import

try:
	import indigo
except:
	pass

from .RPFrameworkDevice  import RPFrameworkDevice
from .RPFrameworkPlugin import GUI_CONFIG_PARENTDEVICEIDPROPERTYNAME
# endregion


class RPFrameworkNonCommChildDevice(RPFrameworkDevice):

	#######################################################################################
	# region Construction and Destruction Methods
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor called once upon plugin class receiving a command to start device
	# communication. The plugin will call other commands when needed, simply zero out the
	# member variables
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, plugin, device):
		super().__init__(plugin, device)

	# endregion
	#######################################################################################

	#######################################################################################
	# region Disabled communications functions
	def initiate_communications(self):
		super(RPFrameworkNonCommChildDevice, self).initiate_communications(initialize_connect=False)
		
	def terminate_communications(self):
		pass

	# endregion
	#######################################################################################

	#######################################################################################
	# region Queue and Command Processing Methods
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Add new command to queue of the PARENT object... this must be obtained from the
	# plugin...
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def queue_device_command(self, command):
		parent_device_id = int(self.indigoDevice.pluginProps[self.host_plugin.get_gui_config_value(self.indigoDevice.deviceTypeId, GUI_CONFIG_PARENTDEVICEIDPROPERTYNAME, "")])
		if parent_device_id in self.host_plugin.managed_devices:
			self.host_plugin.managed_devices[parent_device_id].queue_device_command(command)

	# endregion
	#######################################################################################
		