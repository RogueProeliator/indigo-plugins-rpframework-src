#! /usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################################
# RPFrameworkThread by RogueProeliator <adam.d.ashe@gmail.com>
# Class for all RogueProeliator's device threads; supports cancellation via raising an
# exception in the thread
#######################################################################################

# region Python Imports
import ctypes
import inspect
import threading
# endregion


def _async_raise(tid, exctype):
	if not inspect.isclass(exctype):
		raise TypeError("Only types can be raised (not instances)")
	res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), ctypes.py_object(exctype))
	if res == 0:
		raise ValueError("Invalid thread ID")
	elif res != 1:
		# if it returns a number greater than one, you're in trouble, 
		# and you should call it again with exc=NULL to revert the effect
		ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, 0)
		raise SystemError("PyThreadState_SetAsyncExc failed")


#######################################################################################
# RPFrameworkThread
# Base threading class used to launch extra processing threads by plugins and devices
#######################################################################################
class RPFrameworkThread(threading.Thread):

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine returns the ID of the thread, which should be unique to all threads
	# in this package
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def _get_my_tid(self):
		if not self.is_alive():
			raise threading.ThreadError("The thread is not active")

		# check to see if we have the ID already retrieved/cached
		if hasattr(self, "_thread_id"):
			return self._thread_id

		# the id is not yet cached to the class... attempt to find it now in the list
		# of active threads
		for t in threading.enumerate():
			if t is self:
				self._thread_id = t.ident
				return t.ident

		# we could not find the thread's ID
		raise AssertionError("Could not determine the thread's id")

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine raises an exception of the given type within the thread's context
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def raise_exc(self, exctype):
		_async_raise(self._get_my_tid(), exctype)

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine may be called in order to terminate the thread
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def terminateThread(self):
		self.raise_exc(SystemExit)
