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

class PropAnnotationPoint(PropWidget):
	def __init__(self, _obj, parent=None):
		super( PropAnnotationPoint, self ).__init__( parent )
		#uic.loadUi('dpVision/gui/forms/propAnnotationPoint.ui', self)
		AP.loadUi('propAnnotationPoint.ui', self)
		self.obj_ref = weakref.ref(_obj)

	@staticmethod
	def create(m, parent = 0):
		return PropWidget.build( [ PropBaseObject(m), PropAnnotation(m), PropAnnotationPoint(m) ], parent )


	def updateProperties(self):
		obj = self.obj_ref()
		if obj is None:
			return

		w = [ self.pointX, self.pointY, self.pointZ, self.vecX, self.vecY, self.vecZ, self.showVec ]
		for i in w:
			i.blockSignals(True)

		ctr = obj.m_point
		self.pointX.setValue(ctr[0])
		self.pointY.setValue(ctr[1])
		self.pointZ.setValue(ctr[2])
		
		vec = obj.m_vector if obj.m_vector is not None else [0.0,0.0,1.0]
		self.vecX.setValue(vec[0])
		self.vecY.setValue(vec[1])
		self.vecZ.setValue(vec[2])
		
		self.vecX.setEnabled(obj.m_showVector)
		self.vecY.setEnabled(obj.m_showVector)
		self.vecZ.setEnabled(obj.m_showVector)
		self.showVec.setChecked(obj.m_showVector)

		for i in w:
			i.blockSignals(False)

	@pyqtSlot(float)
	def onPointX(self, x):
		obj = self.obj_ref()
		obj.m_point[0] = x
		AP.updateAllViews()

	@pyqtSlot(float)
	def onPointY(self, y):
		obj = self.obj_ref()
		obj.m_point[1] = y
		AP.updateAllViews()

	@pyqtSlot(float)
	def onPointZ(self, z):
		obj = self.obj_ref()
		obj.m_point[2] = z
		AP.updateAllViews()

	@pyqtSlot(float)
	def onVecX(self, x):
		obj = self.obj_ref()
		obj.m_vector[0] = x
		AP.updateAllViews()

	@pyqtSlot(float)
	def onVecY(self, y):
		obj = self.obj_ref()
		obj.m_vector[1] = y
		AP.updateAllViews()

	@pyqtSlot(float)
	def onVecZ(self, z):
		obj = self.obj_ref()
		obj.m_vector[2] = z
		AP.updateAllViews()

	@pyqtSlot(bool)
	def onShowVec(self, b):
		obj = self.obj_ref()
		obj.m_showVector = b

		self.vecX.setEnabled(obj.m_showVector)
		self.vecY.setEnabled(obj.m_showVector)
		self.vecZ.setEnabled(obj.m_showVector)

		AP.updateAllViews()
