# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 12:16:13 2023

@author: darek
"""

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
#from OpenGL.GL import *
import OpenGL.GL as gl


class BaseObject(QObject):
	def __init__(self, parent=None):
		super( BaseObject, self ).__init__( parent )
		print(self.__class__.__name__+" constructor")
		self.m_parent = parent

		self.m_label = self.__class__.__name__
		self.m_descr = ""
		self.m_showSelf = True
		self.m_showKids = True
		self.m_modified = True
		self.m_checked = False

	def __del__(self):
		print(self.__class__.__name__+" destructor")

	def setLabel(self, _lbl):
		self.m_label = _lbl

	def getLabel(self):
		return self.m_label

	def setDescription(self, _dsc):
		self.m_descr = _dsc

	def getDescription(self):
		return self.m_descr

	def setParent(self, obj):
		self.m_parent = obj

	def getParent(self):
		return self.m_parent

	def setChecked(self, b):
		self.m_checked = b

	def isChecked(self):
		return self.m_checked
		
	def setSelfVisibility(self, b):
		self.m_showSelf = b

	def getSelfVisibility(self):
		return self.m_showSelf

	def setKidsVisibility(self, b):
		self.m_showKids = b

	def getKidsVisibility(self):
		return self.m_showKids

	def hasCategory(self, object_category):
		'''Check if object is instance of subclass of object_category
		'object_category' must be given as type'''

		if not isinstance(object_category, type):
			raise TypeError("Argument 'object_category' must be a class type")
		return issubclass(type(self), object_category)

	def hasType(self, object_type):
		'''Check if object is instance of object_type
		'object_type' could be given as string or type'''

		if isinstance(object_type, str):
			return self.__class__.__name__ == object_type
		elif isinstance(object_type, type):
			return type(self) is object_type
		else:
			raise TypeError("Argument 'object_type' must be a class type")
	
	def on_mouse_move(self, x, y):
		#
		pass

	def children(self):
		return []
	
	def renderSelf(self):
		pass
	
	def renderKids(self):
		pass
	
	def render(self):
		gl.glPushMatrix()
		if (self.m_showSelf):
			self.renderSelf()
		if (self.m_showKids):
			self.renderKids()
		gl.glPopMatrix()

	def getGlobalTransformation(self):
		return self.m_parent.getGlobalTransformation() if self.m_parent else QMatrix4x4()

