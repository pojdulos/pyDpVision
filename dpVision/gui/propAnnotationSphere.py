# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 20:40:37 2023

@author: darek
"""

from abc import ABC, abstractmethod
from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import *

from .propWidget import PropWidget
from .propBaseObject import PropBaseObject
from .propAnnotation import PropAnnotation
import weakref
from .. import AP

class PropAnnotationSphere(PropWidget):
	def __init__(self, _obj, parent=None):
		super( PropAnnotationSphere, self ).__init__( parent )
		#uic.loadUi('dpVision/gui/forms/propAnnotationSphere.ui', self)
		AP.loadUi('propAnnotationSphere.ui', self)
		self.obj_ref = weakref.ref(_obj)

	@staticmethod
	def create(m, parent = 0):
		return PropWidget.build( [ PropBaseObject(m), PropAnnotation(m), PropAnnotationSphere(m) ], parent )

	def updateProperties(self):
		obj = self.obj_ref()
		if obj is None:
			return

		w = [ self.ctrX, self.ctrY, self.ctrZ, self.radius ]
		for i in w:
			i.blockSignals(True)

		ctr = obj.position
		self.ctrX.setValue(ctr[0])
		self.ctrY.setValue(ctr[1])
		self.ctrZ.setValue(ctr[2])
		self.radius.setValue(obj.radius)

		for i in w:
			i.blockSignals(False)

	@pyqtSlot(float)
	def changedCtrX(self, x):
		obj = self.obj_ref()
		ctr = obj.position
		ctr[0] = x
		obj.position = ctr
		AP.updateAllViews()

	@pyqtSlot(float)
	def changedCtrY(self, y):
		obj = self.obj_ref()
		ctr = obj.position
		ctr[1] = y
		obj.position = ctr
		AP.updateAllViews()

	@pyqtSlot(float)
	def changedCtrZ(self, z):
		obj = self.obj_ref()
		ctr = obj.position
		ctr[2] = z
		obj.position = ctr
		AP.updateAllViews()

	@pyqtSlot(float)
	def changedRadius(self, r):
		obj = self.obj_ref()
		obj.radius = r
		obj._is_initialized = False
		AP.updateAllViews()
