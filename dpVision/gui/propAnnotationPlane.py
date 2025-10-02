# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 20:40:37 2023

@author: darek
"""

from abc import ABC, abstractmethod
from PyQt5 import uic
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from .propBaseObject import PropBaseObject
from .propAnnotation import PropAnnotation
from .propWidget import PropWidget
import weakref
from .. import AnnotationPlane, AP
from .multiSpinBox import MultiSpinBox

import logging
logger = logging.getLogger(__name__)

class PropAnnotationPlane(PropWidget):
	def __init__(self, _obj:AnnotationPlane, parent=None):
		super( PropAnnotationPlane, self ).__init__( parent )
		if _obj is None:
			logger.warning("Building properties window for object=None")
		self.obj_ref = weakref.ref(_obj)
		self.buildUI()

	def buildUI(self):
		layout = QFormLayout(self)

		self._centroid = MultiSpinBox(count=3, labels=("X: ","Y: ", "Z: "))
		self._centroid.setStyleSheet("border:none")

		self._normal = MultiSpinBox(count=3, labels=("X: ","Y: ", "Z: "))
		self._normal.setRange(-1.0, 1.0)
		self._normal.setStyleSheet("border:none")

		self._size = MultiSpinBox(count=2, labels=("W: ","H: "))

		layout.addRow("center", self._centroid)
		layout.addRow("normal", self._normal)
		layout.addRow("size", self._size)
		self.setLayout(layout)

		self._centroid.valueChanged.connect(self.on_centroid_valueChanged)
		self._normal.valueChanged.connect(self.on_normal_valueChanged)
		self._size.valueChanged.connect(self.on_size_valueChanged)


	@staticmethod
	def create(m:AnnotationPlane, parent = 0):
		return PropWidget.build( [ 
				PropAnnotationPlane(m),
				PropAnnotation(m),
				PropBaseObject(m),
			], parent )

	def updateProperties(self):
		obj:AnnotationPlane = self.obj_ref()
		if obj is None:
			return

		w = self.get_subwidgets()
		for i in w:	i.blockSignals(True)

		self._centroid.setValue(obj.m_center)
		self._normal.setValue(obj.m_normal)
		self._size.setValue(obj.m_size)

		for i in w:	i.blockSignals(False)
		self.update()

	@pyqtSlot(tuple)
	def on_size_valueChanged(self, vals):
		obj = self.obj_ref()
		if obj is None:
			return
		obj.m_size = vals
		AP.updateAllViews()

	@pyqtSlot(tuple)
	def on_centroid_valueChanged(self, vals):
		obj = self.obj_ref()
		if obj is None:
			return
		obj.m_center = vals
		AP.updateAllViews()

	@pyqtSlot(tuple)
	def on_normal_valueChanged(self, vals):
		obj = self.obj_ref()
		if obj is None:
			return
		obj.normal_vector = vals
		AP.updateAllViews()

