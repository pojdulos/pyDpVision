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
		self.locked = False

		self.m_showSelf = True
		self.m_showKids = True
		self.m_showBB = True
				
	def __del__(self):
		self._parent = None
		# print(self.__class__.__name__+" destructor")

	@property
	def parent(self):
		return self._parent() if self._parent is not None else None
	
	@parent.setter
	def parent(self, parent):
		if parent is None:
			self._parent = None
		elif issubclass(type(parent), BaseObject) and type(parent) is not BaseObject: # BaseObject can not have children
			self._parent = weakref.ref(parent)
		else:
			raise TypeError("Parent must be a derived class of BaseObject")

	@property
	def label(self):
		return self._label
	
	@label.setter
	def label(self, _lbl):
		self._label = _lbl

	@property
	def description(self):
		return self._descr
	
	@description.setter
	def description(self, _dsc):
		self._descr = _dsc

	@property
	def checked(self):
		return self._checked
	
	@checked.setter
	def checked(self, b):
		self._checked = b

	@property
	def locked(self):
		return self._locked
	
	@locked.setter 
	def locked(self, b:bool):
		self._locked = b

	@property
	def modified(self):
		return self._modified
	
	@modified.setter
	def modified(self, b):
		self._modified = b
	
	def move_to(self, target=None, in_place=False):
		newParent = target
		oldParent = self.parent

		if oldParent:
			oldParent.removeChild(self)
		if newParent:
			newParent.addChild(self)

		# if in_place:
		# 	_m0 = oldParent.getGlobalTransformation() if oldParent else np.eye(4, dtype=np.float64)
		# 	_m1 = newParent.getGlobalTransformation() if newParent else np.eye(4, dtype=np.float64)
		# 	newModel = Transform()
		# 	newModel.matrix = Transform.fromTo(m0 = _m0, m1 = _m1)
		# 	newParent.addChild(newModel)
		# AP.addObject(child=self.m_obj, parent=newModel)
		# AP.removeObject(child=self.m_obj, parent=oldParent)
		# AP.updateAllViews()

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
		# Podczas WBOIT pass (0 lub 1) pomijamy inne obiekty niż Mesh i Transform.
		# Przy AP.wboit_pass = -1 (opaque-only pass) lub None (normalny render) działamy normalnie.
		# (Mesh nadpisuje tę metodę; Transform nadpisuje żeby zawsze aplikować macierz)
		from .globals import AP
		if AP.wboit_pass is not None and AP.wboit_pass >= 0:
			return

	@property
	def is_transparent(self):
		"""Zwraca True jeśli obiekt rysuje się z przezroczystością (wymaga pass 2)."""
		return False

	def renderKids(self):
		pass
	
	def getLocalBB(self):
		return None

	def getHierarchyBB(self):
		return self.getLocalBB()

	def getHierarchyBBInParentSpace(self):
		return self.getHierarchyBB()

	def getBB(self):
		# return self.getHierarchyBB()
		return self.getLocalBB()
	
	def invalidate_bb(self):
		"""Unieważnia cache BB tego węzła i wszystkich przodków."""
		# BaseObject nie ma _dirty/_cached_bb — implementacja pełna jest w Object.
		# Tutaj tylko propagujemy w górę.
		p = self.parent
		if p is not None:
			p.invalidate_bb()
	def drawBBwireframe(self, _min, _max, _color=(1.0, 1.0, 0.0)):
		gl.glPushMatrix()
		# BB jest w mm; viewer już zastosował gl.glScalef(mm→viewer) przed workspace.render().
		# Tutaj żadnego dodatkowego skalowania.
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
			if _b and _min is not None and _max is not None:
				self.drawBBwireframe(_min, _max, _color=(0.0, 1.0, 0.0))

	def render(self):
		gl.glPushMatrix()
		if (self.m_showSelf):
			self.renderSelf()
		if (self.m_showKids):
			self.renderKids()
#		if self.m_showSelf and self.m_showBB:
#			self.renderBB()
		gl.glPopMatrix()

	def getGlobalTransformation(self):
		if self._parent is not None:
			parent = self._parent()
			if parent is not None:
				return parent.getGlobalTransformation()
		return np.eye(4, dtype=np.float64)

	def info(self):
		return f"BaseObject: Info() should be implemented in derived class"
