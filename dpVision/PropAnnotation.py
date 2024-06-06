# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 20:40:37 2023

@author: darek
"""

from abc import ABC, abstractmethod
from PyQt5 import uic
from PyQt5.QtWidgets import *

from .propWidget import PropWidget
from .propBaseObject import PropBaseObject
from .annotation import Annotation
from .globals import AP

class PropAnnotation(PropWidget):
	def __init__(self, _obj, parent=None):
		super( PropAnnotation, self ).__init__( parent )
		uic.loadUi('dpVision/ui/UiPropAnnotation.ui', self)
		self.obj = _obj

	@staticmethod
	def create(m, parent = 0):
		return PropWidget.build( [ PropBaseObject(m), PropAnnotation(m) ], parent )


	def updateProperties(self):
		self.updateColorButton(self.obj.getColor())
		self.updateSelColorButton(self.obj.getSelColor())

	def updateColorButton(self, col):
		s = "background-color: rgb(" + str(col.red()) + ", " + str(col.green()) + ", " + str(col.blue()) + ");"
		self.colorButton.setStyleSheet(s)

	def updateSelColorButton(self, col):
		s = "background-color: rgb(" + str(col.red()) + ", " + str(col.green()) + ", " + str(col.blue()) + ");"
		self.selcolorButton.setStyleSheet(s)

	def	colorButtonPressed(self):
		color = QColorDialog.getColor( self.obj.getColor(), self, "Select color", QColorDialog.ShowAlphaChannel | QColorDialog.DontUseNativeDialog)
		if color.isValid():
			self.obj.m_color = color
			self.updateColorButton( color )
			AP.mainWin.update()

	def selcolorButtonPressed(self):
		color = QColorDialog.getColor( self.obj.getSelColor(), self, "Select color", QColorDialog.ShowAlphaChannel | QColorDialog.DontUseNativeDialog)
		if color.isValid():
			self.obj.m_selcolor = color
			self.updateSelColorButton( color )
			AP.mainWin.update()

