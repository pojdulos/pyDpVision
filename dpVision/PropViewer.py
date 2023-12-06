# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 20:40:37 2023

@author: darek
"""

from abc import ABC, abstractmethod
from PyQt5 import uic
from PyQt5.QtCore import QRegularExpression
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PyQt5.QtGui import QVector3D
from .GLViewer import GLViewer
from .PropWidget import PropWidget

class PropViewer(PropWidget):
	def __init__(self, _viewer, parent=None):
		super( PropViewer, self ).__init__( parent )
		uic.loadUi('dpVision/ui/UiPropViewer.ui', self)
		self.viewer = _viewer
		self.rot = self.viewer.transform.getEulerAnglesDeg()
		self.tra = self.viewer.transform.getTranslation()
		self.sca = self.viewer.transform.getScale()

	@staticmethod
	def create(m, parent = 0):
		return PropWidget.build( [ PropViewer(m) ], parent )


	def updateProperties(self):
		view = self.viewer
		if not view is None:
			self.rot = view.transform.getEulerAnglesDeg()
			self.tra = view.transform.getTranslation()
			self.sca = view.transform.getScale()
			
			self.spinViewRotX.blockSignals(True)
			self.spinViewRotX.setValue( self.rot[0] )
			self.spinViewRotX.blockSignals(False)
	
			self.spinViewRotY.blockSignals(True)
			self.spinViewRotY.setValue( self.rot[1] )
			self.spinViewRotY.blockSignals(False)
	
			self.spinViewRotZ.blockSignals(True)
			self.spinViewRotZ.setValue( self.rot[2] )
			self.spinViewRotZ.blockSignals(False)
	
			self.spinViewTransX.blockSignals(True);
			self.spinViewTransX.setValue( self.tra[0] );
			self.spinViewTransX.blockSignals(False);
	
			self.spinViewTransY.blockSignals(True);
			self.spinViewTransY.setValue( self.tra[1] );
			self.spinViewTransY.blockSignals(False);
	
			self.spinViewTransZ.blockSignals(True);
			self.spinViewTransZ.setValue( self.tra[2] );
			self.spinViewTransZ.blockSignals(False);
	
			self.spinViewScale.blockSignals(True);
			self.spinViewScale.setValue( self.sca[0] ); #UWAGA !!! @@@
			self.spinViewScale.blockSignals(False);
	
			self.spinBG.blockSignals(True);
			self.spinBG.setValue(view._fBgColor.redF());
			self.spinBG.blockSignals(False);
	
			isOrtho = view._projection == GLViewer.Projection.ORTHOGONAL
	
			self.radioOrtho.blockSignals(True);
			self.radioOrtho.setChecked(isOrtho);
			self.radioOrtho.blockSignals(False);
	
			self.spinOrthoViewSize.blockSignals(True);
			self.spinOrthoViewSize.setValue(view._dOrthoViewSize);
			self.spinOrthoViewSize.blockSignals(False);
	
			self.spinOrthoViewSize.setEnabled(isOrtho);
	
			isPersp = not isOrtho
	
			self.radioPersp.blockSignals(True);
			self.radioPersp.setChecked(isPersp);
			self.radioPersp.blockSignals(False);
	
			self.spinAngleOfView.blockSignals(True);
			self.spinAngleOfView.setValue(view._dViewingAngle);
			self.spinAngleOfView.blockSignals(False);
	
			self.spinAngleOfView.setEnabled(isPersp);


	def rotXeditingFinished(self):
		pass
	
	def changedRotX(self, d ):
		r = d - self.rot[0]
		self.viewer.transform.rotate(r, 1, 0, 0)
		self.rot[0] = d
		self.viewer.update()

	
	def changedRotY(self, d ):
		r = d - self.rot[1]
		self.viewer.transform.rotate(r, 0, 1, 0)
		self.rot[1] = d
		self.viewer.update()

	def changedRotZ(self, d ):
		r = d - self.rot[2]
		self.viewer.transform.rotate(r, 0, 0, 1)
		self.rot[2] = d
		self.viewer.update()
	
	def changedTraXYZ(self, d):
		x, y, z = self.spinViewTransX.value(), self.spinViewTransY.value(), self.spinViewTransZ.value()

		tx, ty, tz = x - self.tra[0], y - self.tra[1], z - self.tra[2]
		
		self.viewer.transform.translate(tx, ty, tz)
		self.tra = [x, y, z]
		self.viewer.update()


# 	void changedScale( double );
	def changedBGcolor(self, d ):
		pass
	
	def changedAngle(self, i ):
		pass
	
	def changedOrthoViewSize(self, d):
		pass

	def radioPropToggled(self, t):
		if t:
			self.viewer._projection = GLViewer.Projection.PERSPECTIVE
		else:
			self.viewer._projection = GLViewer.Projection.ORTHOGONAL
		self.viewer.update()
