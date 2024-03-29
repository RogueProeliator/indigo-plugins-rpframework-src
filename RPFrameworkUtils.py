#! /usr/bin/env python
# -*- coding: utf-8 -*-
#/////////////////////////////////////////////////////////////////////////////////////////
# RPFrameworkUtils by RogueProeliator <adam.d.ashe@gmail.com>
# 	Non-class utility functions for use across the framework
#/////////////////////////////////////////////////////////////////////////////////////////

#/////////////////////////////////////////////////////////////////////////////////////////
#region Python Imports
import sys
#endregion
#/////////////////////////////////////////////////////////////////////////////////////////


#/////////////////////////////////////////////////////////////////////////////////////////
# Data Type Conversions
#/////////////////////////////////////////////////////////////////////////////////////////
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# This routine ensures that the given string is a unicode string (if it is a string based
# variable), encoding to unicode if necessary
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
def to_unicode(obj, encoding="utf-8"):
	if obj is None:
		return ""

	if isinstance(obj, str):
		return obj
	elif isinstance(obj, bytes):
		return str(obj, encoding)
	return str(obj)


#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# This routine ensures that the given string is a string object (not unicode), converting
# as necessary
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
def to_str(obj, encoding="utf-8"):
	if obj is None:
		return ""

	if isinstance(obj, str):
		return obj.encode(encoding)
	elif isinstance(obj, bytes):
		return obj
	return bytes(obj)


#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# Returns a boolean indicating if the given object is a string-type
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
def is_string_type(obj):
	return isinstance(obj, str)
