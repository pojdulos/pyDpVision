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

from .. import AP,Transform
import weakref
from .gLViewer import GLViewer
from .propWidget import PropWidget

class PropViewer(PropWidget):
	def __init__(self, _viewer : GLViewer, parent=None):
		super( PropViewer, self ).__init__( parent )
		AP.loadUi('propViewer.ui', self)
		self.spinOrthoViewSize.setRange(0,180)
		self.rot = _viewer.transform.getEulerAnglesDeg()
		self.tra = _viewer.transform.getTranslation()
		self.obj_ref = weakref.ref(_viewer)

	@staticmethod
	def create(m, parent = 0):
		return PropWidget.build( [ PropViewer(m) ], parent )


	def updateProperties(self):
		viewer : GLViewer = self.obj_ref()
		if viewer is None:
			return

		w = {	self.spinViewRotX, self.spinViewRotY, self.spinViewRotZ, \
	   			self.spinViewTransX, self.spinViewTransY, self.spinViewTransZ, \
				self.bgColorButton, self.radioOrtho, self.spinOrthoViewSize, \
				self.radioPersp, self.spinAngleOfView, self.spinDefaultViewSize }
		
		for i in w: i.blockSignals(True)

		self.updateBgColorButton( viewer._fBgColor )

		self.rot = viewer.transform.getEulerAnglesDeg()
		self.tra = viewer.transform.getTranslation()
		
		self.spinViewRotX.setValue( self.rot[0] )
		self.spinViewRotY.setValue( self.rot[1] )
		self.spinViewRotZ.setValue( self.rot[2] )

		self.spinViewTransX.setValue( self.tra[0] )
		self.spinViewTransY.setValue( self.tra[1] )
		self.spinViewTransZ.setValue( self.tra[2] )

		isOrtho = viewer._projection == GLViewer.Projection.ORTHOGONAL

		self.radioOrtho.setChecked(isOrtho)
		self.spinOrthoViewSize.setValue(viewer._dOrthoViewSize)
		self.spinOrthoViewSize.setEnabled(isOrtho)

		isPersp = not isOrtho

		self.radioPersp.setChecked(isPersp)
		self.spinAngleOfView.setValue(viewer._dViewingAngle)
		self.spinAngleOfView.setEnabled(isPersp)

		self.orthoWidget.setVisible(isOrtho)
		self.perspWidget.setVisible(isPersp)

		self.spinDefaultViewSize.setValue(viewer._dCurrentViewSize)

		self.updateMatrix(viewer.transform)

		for i in w: i.blockSignals(False)

	def	updateMatrix(self, transform:Transform):
		mat	= transform.toNumPy()
		self.matrixTable.blockSignals(True)
		for row in range(4):
			for	col in range(4):
				value = mat[row, col]
				item = self.matrixTable.item(row,	col)
				if	item is None:
					item = QTableWidgetItem()
					self.matrixTable.setItem(row, col, item)
				item.setText(f"{value:.6f}")
		self.matrixTable.blockSignals(False)


	def updateBgColorButton(self, col):
		s = "background-color: rgb(" + str(col.red()) + ", " + str(col.green()) + ", " + str(col.blue()) + ");"
		self.bgColorButton.setStyleSheet(s)

	@pyqtSlot(float)
	def changedRotX(self, d ):
		viewer : GLViewer = self.obj_ref()
		r = d - self.rot[0]
		viewer.transform.rotate(r, [1, 0, 0])
		self.rot[0] = d
		viewer.update()
	
	@pyqtSlot(float)
	def changedRotY(self, d ):
		viewer : GLViewer = self.obj_ref()
		r = d - self.rot[1]
		viewer.transform.rotate(r, [0, 1, 0])
		self.rot[1] = d
		viewer.update()

	@pyqtSlot(float)
	def changedRotZ(self, d ):
		viewer : GLViewer = self.obj_ref()
		r = d - self.rot[2]
		viewer.transform.rotate(r, [0, 0, 1])
		self.rot[2] = d
		viewer.update()

	@pyqtSlot(float)
	def onChangedRotation(self, d):
		viewer : GLViewer = self.obj_ref()
		x, y, z = self.spinViewRotX.value(), self.spinViewRotY.value(), self.spinViewRotZ.value()
		rx, ry, rz = x - self.tra[0], y - self.tra[1], z - self.tra[2]
		
		viewer.transform.rotate(rz, [0, 0, 1])
		viewer.transform.rotate(ry, [0, 1, 0])
		viewer.transform.rotate(rx, [1, 0, 0])

		self.rot = [x, y, z]
		viewer.update()

	@pyqtSlot(float)
	def changedTraXYZ(self, d):
		viewer : GLViewer = self.obj_ref()
		x, y, z = self.spinViewTransX.value(), self.spinViewTransY.value(), self.spinViewTransZ.value()

		tx, ty, tz = x - self.tra[0], y - self.tra[1], z - self.tra[2]
		
		viewer.transform.translate(tx, ty, tz)
		self.tra = [x, y, z]
		viewer.update()

	@pyqtSlot()
	def onBackgroundColorButton(self):
		viewer : GLViewer = self.obj_ref()
		color = QColorDialog.getColor( viewer._fBgColor, self, "Select background color", QColorDialog.DontUseNativeDialog)
		if color.isValid():
			viewer._fBgColor = color
			self.updateBgColorButton( color )
			viewer.update()
	
	@pyqtSlot(int)
	def changedAngle(self, i ):
		viewer : GLViewer = self.obj_ref()
		viewer._dViewingAngle = i
		viewer.recalcView()
		viewer.update()
	
	@pyqtSlot(int)
	def changedOrthoViewSize(self, d):
		viewer : GLViewer = self.obj_ref()
		viewer._dOrthoViewSize = d
		viewer.recalcView()
		viewer.update()

	@pyqtSlot(bool)
	def radioPropToggled(self, t):
		viewer : GLViewer = self.obj_ref()
		if t:
			viewer._projection = GLViewer.Projection.PERSPECTIVE
		else:
			viewer._projection = GLViewer.Projection.ORTHOGONAL
		viewer.recalcView()
		viewer.update()
		self.updateProperties()

	def onClearMatrixButton(self):
		viewer : GLViewer = self.obj_ref()
		viewer.transform.reset()
		AP.mainWin.dock['properties'].updateProperties()
		AP.updateAllViews()

	@pyqtSlot(float)
	def onDefaultViewSizeChanged(self, val):
		"""Zapisuje nową domyślną skalę sceny i od razu przelicza widok."""
		viewer : GLViewer = self.obj_ref()
		if viewer is None:
			return
		viewer._dCurrentViewSize = val
		viewer.setViewScale(val)
		self.updateProperties()

	@pyqtSlot()
	def onResetView(self):
		"""Przywraca kamerę i transformację do stanu domyślnego dla bieżącej skali."""
		viewer : GLViewer = self.obj_ref()
		if viewer is None:
			return
		viewer.resetView()
		self.updateProperties()
