#! /usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################################
# RPFrameworkIndigoMock by RogueProeliator <adam.d.ashe@gmail.com>
# Mocking class used for unit testing
#######################################################################################

class RPFrameworkIndigoMock(object):
    
    # internal class
    class PluginBase(object):
        def __init__(self, plugin_id ='', plugin_display_name ='', plugin_version = (1, 0, 0), plugin_prefs = None):
            pass