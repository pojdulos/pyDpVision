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
from .annotationSphere import AnnotationSphere
from .globals import AP

class PropAnnotationSphere(PropWidget):
	def __init__(self, _obj, parent=None):
		super( PropAnnotationSphere, self ).__init__( parent )
		uic.loadUi('dpVision/ui/UiPropAnnotationSphere.ui', self)
		self.obj = _obj

	@staticmethod
	def create(m, parent = 0):
		return PropWidget.build( [ PropBaseObject(m), PropAnnotation(m), PropAnnotationSphere(m) ], parent )

	def updateProperties(self):
		if self.obj is None:
			return

		w = [ self.ctrX, self.ctrY, self.ctrZ, self.radius ]
		for i in w:
			i.blockSignals(True)

		ctr = self.obj.getCenter()
		self.ctrX.setValue(ctr[0])
		self.ctrY.setValue(ctr[1])
		self.ctrZ.setValue(ctr[2])
		self.radius.setValue(self.obj.getRadius())

		for i in w:
			i.blockSignals(False)

	@pyqtSlot(float)
	def changedCtrX(self, x):
		ctr = self.obj.getCenter()
		ctr[0] = x
		self.obj.setCenter(ctr)
		AP.updateAllViews()

	@pyqtSlot(float)
	def changedCtrY(self, y):
		ctr = self.obj.getCenter()
		ctr[1] = y
		self.obj.setCenter(ctr)
		AP.updateAllViews()

	@pyqtSlot(float)
	def changedCtrZ(self, z):
		ctr = self.obj.getCenter()
		ctr[2] = z
		self.obj.setCenter(ctr)
		AP.updateAllViews()

	@pyqtSlot(float)
	def changedRadius(self, r):
		self.obj.setRadius(r)
		AP.updateAllViews()
