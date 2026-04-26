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
import weakref
from .. import AP

class PropAnnotation(PropWidget):
	def __init__(self, _obj, parent=None):
		super( PropAnnotation, self ).__init__( parent )
		AP.loadUi('propAnnotation.ui', self)
		self.obj_ref = weakref.ref(_obj)
		self.wireframeCheck.stateChanged.connect(self.wireframeToggled)

	@staticmethod
	def create(m, parent = 0):
		return PropWidget.build( [ PropBaseObject(m), PropAnnotation(m) ], parent )


	def updateProperties(self):
		obj = self.obj_ref()
		self.updateColorButton(obj.getColor())
		self.updateSelColorButton(obj.getSelColor())
		self.wireframeCheck.blockSignals(True)
		self.wireframeCheck.setChecked(obj.m_showWireframe)
		self.wireframeCheck.blockSignals(False)

	def updateColorButton(self, col):
		s = "background-color: rgb(" + str(col.red()) + ", " + str(col.green()) + ", " + str(col.blue()) + ");"
		self.colorButton.setStyleSheet(s)

	def updateSelColorButton(self, col):
		s = "background-color: rgb(" + str(col.red()) + ", " + str(col.green()) + ", " + str(col.blue()) + ");"
		self.selcolorButton.setStyleSheet(s)

	def	colorButtonPressed(self):
		obj = self.obj_ref()
		color = QColorDialog.getColor( obj.getColor(), self, "Select color", QColorDialog.ShowAlphaChannel | QColorDialog.DontUseNativeDialog)
		if color.isValid():
			obj.m_color = color
			self.updateColorButton( color )
			AP.mainWin.update()

	def selcolorButtonPressed(self):
		obj = self.obj_ref()
		color = QColorDialog.getColor( obj.getSelColor(), self, "Select color", QColorDialog.ShowAlphaChannel | QColorDialog.DontUseNativeDialog)
		if color.isValid():
			obj.m_selcolor = color
			self.updateSelColorButton( color )
			AP.mainWin.update()

	@pyqtSlot(int)
	def wireframeToggled(self, state):
		obj = self.obj_ref()
		if obj is None:
			return
		obj.showWireframe(bool(state))
		AP.updateAllViews()

