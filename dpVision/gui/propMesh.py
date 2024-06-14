# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 20:40:37 2023

@author: darek
"""

from abc import ABC, abstractmethod
from PyQt5 import uic
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from .. import AP
from .propWidget import PropWidget
from .propBaseObject import PropBaseObject


class PropMesh(PropWidget):
	def __init__(self, _obj, parent=None):
		super( PropMesh, self ).__init__( parent )
		#uic.loadUi('dpVision/gui/forms/propMesh.ui', self)
		AP.loadUi('propMesh.ui', self)
		self.obj = _obj

	@staticmethod
	def create(m, parent = 0):
		return PropWidget.build( [ PropBaseObject(m), PropMesh(m) ], parent )


	def updateProperties(self):
		obj = self.obj
		col = obj.materials[obj.currentMaterial].diffuse + [obj.materials[obj.currentMaterial].alpha]
		qc = QColor()
		qc.setRgbF(col[0],col[1],col[2],col[3])
		self.updateDefaultColorButton( qc )

	def updateDefaultColorButton(self, col):
		s = "background-color: rgb(" + str(col.red()) + ", " + str(col.green()) + ", " + str(col.blue()) + ");"
		self.bgColorButton.setStyleSheet(s)

	@pyqtSlot()
	def on_default_color_button(self):
		col = self.obj.materials[self.obj.currentMaterial].diffuse + [self.obj.materials[self.obj.currentMaterial].alpha]
		qc = QColor()
		qc.setRgbF(col[0],col[1],col[2],col[3])
		color = QColorDialog.getColor( qc, self, "Select color", options=QColorDialog.ShowAlphaChannel | QColorDialog.DontUseNativeDialog)
		if color.isValid():
			self.obj.materials[self.obj.currentMaterial].diffuse = [ color.redF(), color.greenF(), color.blueF() ]
			self.obj.materials[self.obj.currentMaterial].alpha = color.alphaF()
			self.updateDefaultColorButton( color )
			AP.updateAllViews()

