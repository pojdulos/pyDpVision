# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 20:40:37 2023

@author: darek
"""

from abc import ABC, abstractmethod
from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import *

from dpVision.PropWidget import PropWidget
from dpVision.PropBaseObject import PropBaseObject
from dpVision.PropAnnotation import PropAnnotation
from dpVision.AnnotationPoint import AnnotationPoint
from dpVision.Globals import AP

class PropAnnotationPoint(PropWidget):
	def __init__(self, _obj, parent=None):
		super( PropAnnotationPoint, self ).__init__( parent )
		uic.loadUi('dpVision/ui/UiPropAnnotationPoint.ui', self)
		self.obj = _obj

	@staticmethod
	def create(m, parent = 0):
		return PropWidget.build( [ PropBaseObject(m), PropAnnotation(m), PropAnnotationPoint(m) ], parent )


	def updateProperties(self):
		if self.obj is None:
			return

		w = [ self.pointX, self.pointY, self.pointZ, self.vecX, self.vecY, self.vecZ, self.showVec ]
		for i in w:
			i.blockSignals(True)

		ctr = self.obj.m_point
		self.pointX.setValue(ctr[0])
		self.pointY.setValue(ctr[1])
		self.pointZ.setValue(ctr[2])
		
		vec = self.obj.m_vector
		self.vecX.setValue(vec[0])
		self.vecY.setValue(vec[1])
		self.vecZ.setValue(vec[2])
		
		self.showVec.setChecked(self.obj.m_showVector)

		for i in w:
			i.blockSignals(False)

	@pyqtSlot(float)
	def onPointX(self, x):
		self.obj.m_point[0] = x
		AP.updateAllViews()

	@pyqtSlot(float)
	def onPointY(self, y):
		self.obj.m_point[1] = y
		AP.updateAllViews()

	@pyqtSlot(float)
	def onPointZ(self, z):
		self.obj.m_point[2] = z
		AP.updateAllViews()

	@pyqtSlot(float)
	def onVecX(self, x):
		self.obj.m_vector[0] = x
		AP.updateAllViews()

	@pyqtSlot(float)
	def onVecY(self, y):
		self.obj.m_vector[1] = y
		AP.updateAllViews()

	@pyqtSlot(float)
	def onVecZ(self, z):
		self.obj.m_vector[2] = z
		AP.updateAllViews()

	@pyqtSlot(bool)
	def onShowVec(self, b):
		self.obj.m_showVector = b
		AP.updateAllViews()
