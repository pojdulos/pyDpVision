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
import numpy as np

import weakref

class BaseObject(QObject):
	def __init__(self, parent=None):
		super( BaseObject, self ).__init__( parent )
		# print(self.__class__.__name__+" constructor")
		
		self.parent = parent
		self.label = self.__class__.__name__
		self.description = ""
		self.checked = False
		self.modified = True
		
		self.m_showSelf = True
		self.m_showKids = True
		self.m_showBB = True
				
	def __del__(self):
		self.__parent = None
		# print(self.__class__.__name__+" destructor")

	@property
	def parent(self):
		return self.__parent() if self.__parent is not None else None
	
	@parent.setter
	def parent(self, parent):
		if parent is None:
			self.__parent = None
		elif issubclass(type(parent), BaseObject) and type(parent) is not BaseObject: # BaseObject can not have children
			self.__parent = weakref.ref(parent)
		else:
			raise TypeError("Parent must be a derived class of BaseObject")

	@property
	def label(self):
		return self.__label
	
	@label.setter
	def label(self, _lbl):
		self.__label = _lbl

	@property
	def description(self):
		return self.__descr
	
	@description.setter
	def description(self, _dsc):
		self.__descr = _dsc

	@property
	def checked(self):
		return self.__checked
	
	@checked.setter
	def checked(self, b):
		# print('BaseObject: checked' if b else 'BaseObject: unchecked')
		self.__checked = b

	@property
	def modified(self):
		return self.__modified
	
	@modified.setter
	def modified(self, b):
		self.__modified = b
	
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
			raise TypeError("Argument 'object_type' must be a class type or string")
	
	def on_mouse_move(self, x, y):
		pass

	def children(self):
		return []
	
	def renderSelf(self):
		pass
	
	def renderKids(self):
		pass
	
	def getBB(self):
		return None
	
	def drawBBwireframe(self, _min, _max, _color=(1.0, 1.0, 0.0)):
		gl.glPushMatrix()
		gl.glPushAttrib(gl.GL_ALL_ATTRIB_BITS)

		gl.glDisable(gl.GL_TEXTURE_2D)
		gl.glEnable(gl.GL_COLOR_MATERIAL)
		gl.glColorMaterial(gl.GL_FRONT_AND_BACK, gl.GL_AMBIENT_AND_DIFFUSE)
		
		gl.glColor3fv(_color)
		gl.glBegin(gl.GL_LINES)
		# Bottom face
		gl.glVertex3f(_min[0], _min[1], _min[2])
		gl.glVertex3f(_max[0], _min[1], _min[2])

		gl.glVertex3f(_max[0], _min[1], _min[2])
		gl.glVertex3f(_max[0], _max[1], _min[2])

		gl.glVertex3f(_min[0], _max[1], _min[2])
		gl.glVertex3f(_max[0], _max[1], _min[2])

		gl.glVertex3f(_min[0], _max[1], _min[2])
		gl.glVertex3f(_min[0], _min[1], _min[2])

		# Top face
		gl.glVertex3f(_min[0], _min[1], _max[2])
		gl.glVertex3f(_max[0], _min[1], _max[2])

		gl.glVertex3f(_max[0], _min[1], _max[2])
		gl.glVertex3f(_max[0], _max[1], _max[2])

		gl.glVertex3f(_max[0], _max[1], _max[2])
		gl.glVertex3f(_min[0], _max[1], _max[2])

		gl.glVertex3f(_min[0], _max[1], _max[2])
		gl.glVertex3f(_min[0], _min[1], _max[2])

		# Vertical edges
		gl.glVertex3f(_min[0], _min[1], _min[2])
		gl.glVertex3f(_min[0], _min[1], _max[2])

		gl.glVertex3f(_max[0], _min[1], _min[2])
		gl.glVertex3f(_max[0], _min[1], _max[2])

		gl.glVertex3f(_max[0], _max[1], _min[2])
		gl.glVertex3f(_max[0], _max[1], _max[2])

		gl.glVertex3f(_min[0], _max[1], _min[2])
		gl.glVertex3f(_min[0], _max[1], _max[2])
		gl.glEnd()

		gl.glPopAttrib()
		gl.glPopMatrix()

	def renderBB(self):
		bb = self.getBB()
		if bb is not None:
			_b, _min, _max = bb
			if _b:
				self.drawBBwireframe(_min, _max, _color=(0.0, 1.0, 0.0))

	def render(self):
		gl.glPushMatrix()
		if (self.m_showSelf):
			self.renderSelf()
		if (self.m_showKids):
			self.renderKids()
		if (self.m_showBB):
			self.renderBB()
		gl.glPopMatrix()

	def getGlobalTransformation(self):
		if self.__parent is not None:
			parent = self.__parent()
			if parent is not None:
				return parent.getGlobalTransformation()
		return np.eye(4, dtype=np.float64)
