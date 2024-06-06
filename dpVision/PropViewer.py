# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 20:40:37 2023

@author: darek
"""

from abc import ABC, abstractmethod
from PyQt5 import uic
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QVector3D

from .gLViewer import GLViewer
from .propWidget import PropWidget
from .globals import AP

class PropViewer(PropWidget):
	def __init__(self, _viewer, parent=None):
		super( PropViewer, self ).__init__( parent )
		uic.loadUi('dpVision/ui/UiPropViewer.ui', self)
		self.viewer = _viewer
		self.rot = self.viewer.transform.getEulerAnglesDeg()
		self.tra = self.viewer.transform.getTranslation()

	@staticmethod
	def create(m, parent = 0):
		return PropWidget.build( [ PropViewer(m) ], parent )


	def updateProperties(self):
		if self.viewer is None:
			return

		w = {	self.spinViewRotX, self.spinViewRotY, self.spinViewRotZ, \
	   			self.spinViewTransX, self.spinViewTransY, self.spinViewTransZ, \
				self.bgColorButton, self.radioOrtho, self.spinOrthoViewSize, \
				self.radioPersp, self.spinAngleOfView }
		
		for i in w: i.blockSignals(True)

		self.updateBgColorButton( self.viewer._fBgColor )

		self.rot = self.viewer.transform.getEulerAnglesDeg()
		self.tra = self.viewer.transform.getTranslation()
		
		self.spinViewRotX.setValue( self.rot[0] )
		self.spinViewRotY.setValue( self.rot[1] )
		self.spinViewRotZ.setValue( self.rot[2] )

		self.spinViewTransX.setValue( self.tra[0] )
		self.spinViewTransY.setValue( self.tra[1] )
		self.spinViewTransZ.setValue( self.tra[2] )

		isOrtho = self.viewer._projection == GLViewer.Projection.ORTHOGONAL

		self.radioOrtho.setChecked(isOrtho)
		self.spinOrthoViewSize.setValue(self.viewer._dOrthoViewSize)
		self.spinOrthoViewSize.setEnabled(isOrtho)

		isPersp = not isOrtho

		self.radioPersp.setChecked(isPersp)
		self.spinAngleOfView.setValue(self.viewer._dViewingAngle)
		self.spinAngleOfView.setEnabled(isPersp)

		self.orthoWidget.setVisible(isOrtho)
		self.perspWidget.setVisible(isPersp)

		self.updateMatrix()

		for i in w: i.blockSignals(False)

	def updateMatrix(self):
		self.matrixTable.blockSignals(True)
		for row in range(4):
			for col in range(4):
				index = self.matrixTable.model().index(row,col)
				value = self.viewer.transform.matrix[row,col]
				self.matrixTable.model().setData(index, round(value,6))
		self.matrixTable.blockSignals(False)

	def updateBgColorButton(self, col):
		s = "background-color: rgb(" + str(col.red()) + ", " + str(col.green()) + ", " + str(col.blue()) + ");"
		self.bgColorButton.setStyleSheet(s)

	@pyqtSlot(float)
	def changedRotX(self, d ):
		r = d - self.rot[0]
		self.viewer.transform.rotate(r, [1, 0, 0])
		self.rot[0] = d
		self.viewer.update()
	
	@pyqtSlot(float)
	def changedRotY(self, d ):
		r = d - self.rot[1]
		self.viewer.transform.rotate(r, [0, 1, 0])
		self.rot[1] = d
		self.viewer.update()

	@pyqtSlot(float)
	def changedRotZ(self, d ):
		r = d - self.rot[2]
		self.viewer.transform.rotate(r, [0, 0, 1])
		self.rot[2] = d
		self.viewer.update()

	@pyqtSlot(float)
	def onChangedRotation(self, d):
		x, y, z = self.spinViewRotX.value(), self.spinViewRotY.value(), self.spinViewRotZ.value()
		rx, ry, rz = x - self.tra[0], y - self.tra[1], z - self.tra[2]
		
		self.viewer.transform.rotate(rz, [0, 0, 1])
		self.viewer.transform.rotate(ry, [0, 1, 0])
		self.viewer.transform.rotate(rx, [1, 0, 0])

		self.rot = [x, y, z]
		self.viewer.update()

	@pyqtSlot(float)
	def changedTraXYZ(self, d):
		x, y, z = self.spinViewTransX.value(), self.spinViewTransY.value(), self.spinViewTransZ.value()

		tx, ty, tz = x - self.tra[0], y - self.tra[1], z - self.tra[2]
		
		self.viewer.transform.translate(tx, ty, tz)
		self.tra = [x, y, z]
		self.viewer.update()

	@pyqtSlot()
	def onBackgroundColorButton(self):
		color = QColorDialog.getColor( self.viewer._fBgColor, self, "Select background color", QColorDialog.DontUseNativeDialog)
		if color.isValid():
			self.viewer._fBgColor = color
			self.updateBgColorButton( color )
			self.viewer.update()
	
	@pyqtSlot(int)
	def changedAngle(self, i ):
		self.viewer._dViewingAngle = i
		self.viewer.recalcView()
		self.viewer.update()
	
	@pyqtSlot(int)
	def changedOrthoViewSize(self, d):
		self.viewer._dOrthoViewSize = d
		self.viewer.recalcView()
		self.viewer.update()

	@pyqtSlot(bool)
	def radioPropToggled(self, t):
		if t:
			self.viewer._projection = GLViewer.Projection.PERSPECTIVE
		else:
			self.viewer._projection = GLViewer.Projection.ORTHOGONAL
		self.viewer.recalcView()
		self.viewer.update()
		self.updateProperties()

	def onClearMatrixButton(self):
		self.viewer.transform.reset()
		AP.mainWin.dock['properties'].updateProperties()
		AP.updateAllViews()
