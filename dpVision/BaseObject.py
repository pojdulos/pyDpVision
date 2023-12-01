# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 12:16:13 2023

@author: darek
"""

from PyQt5.QtCore import QObject

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

	def hasCategory(self, cat):
		if not isinstance(cat, type):
			raise TypeError("Argument 'cat' must be a class type")
		return issubclass(type(self), cat)

	def hasType(self, typ):
		if not isinstance(typ, type):
			raise TypeError("Argument 'typ' must be a class type")
		return type(self) is typ

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

