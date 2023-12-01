# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 20:40:37 2023

@author: darek
"""

from abc import ABC, abstractmethod
from PyQt5 import uic

from dpVision.PropWidget import PropWidget
from dpVision.BaseObject import BaseObject

class PropBaseObject(PropWidget):
	def __init__(self, _obj, parent=None):
		super( PropBaseObject, self ).__init__( parent )
		uic.loadUi('dpVision/ui/UiPropBaseObject.ui', self)
		self.obj = _obj
		# self.rot = self.viewer.transform.getEulerAnglesDeg()
		# self.tra = self.viewer.transform.getTranslation()
		# self.sca = self.viewer.transform.getScale()

	@staticmethod
	def create(m, parent = 0):
		return PropWidget.build( [ PropBaseObject(m) ], parent )


	def updateProperties(self):
		obj = self.obj
		# if not view is None:
		# 	self.rot = view.transform.getEulerAnglesDeg()
		# 	self.tra = view.transform.getTranslation()
		# 	self.sca = view.transform.getScale()
			
		# 	self.spinViewRotX.blockSignals(True)
		# 	self.spinViewRotX.setValue( self.rot[0] )
		# 	self.spinViewRotX.blockSignals(False)
	
		# 	self.spinViewRotY.blockSignals(True)
		# 	self.spinViewRotY.setValue( self.rot[1] )
		# 	self.spinViewRotY.blockSignals(False)
	
		# 	self.spinViewRotZ.blockSignals(True)
		# 	self.spinViewRotZ.setValue( self.rot[2] )
		# 	self.spinViewRotZ.blockSignals(False)
	
		# 	self.spinViewTransX.blockSignals(True);
		# 	self.spinViewTransX.setValue( self.tra[0] );
		# 	self.spinViewTransX.blockSignals(False);
	
		# 	self.spinViewTransY.blockSignals(True);
		# 	self.spinViewTransY.setValue( self.tra[1] );
		# 	self.spinViewTransY.blockSignals(False);
	
		# 	self.spinViewTransZ.blockSignals(True);
		# 	self.spinViewTransZ.setValue( self.tra[2] );
		# 	self.spinViewTransZ.blockSignals(False);
	
		# 	self.spinViewScale.blockSignals(True);
		# 	self.spinViewScale.setValue( self.sca[0] ); #UWAGA !!! @@@
		# 	self.spinViewScale.blockSignals(False);
	
		# 	self.spinBG.blockSignals(True);
		# 	self.spinBG.setValue(view._fBgColor.redF());
		# 	self.spinBG.blockSignals(False);
	
		# 	isOrtho = view._projection == GLViewer.Projection.ORTHOGONAL
	
		# 	self.radioOrtho.blockSignals(True);
		# 	self.radioOrtho.setChecked(isOrtho);
		# 	self.radioOrtho.blockSignals(False);
	
		# 	self.spinOrthoViewSize.blockSignals(True);
		# 	self.spinOrthoViewSize.setValue(view._dOrthoViewSize);
		# 	self.spinOrthoViewSize.blockSignals(False);
	
		# 	self.spinOrthoViewSize.setEnabled(isOrtho);
	
		# 	isPersp = not isOrtho
	
		# 	self.radioPersp.blockSignals(True);
		# 	self.radioPersp.setChecked(isPersp);
		# 	self.radioPersp.blockSignals(False);
	
		# 	self.spinAngleOfView.blockSignals(True);
		# 	self.spinAngleOfView.setValue(view._dViewingAngle);
		# 	self.spinAngleOfView.blockSignals(False);
	
		# 	self.spinAngleOfView.setEnabled(isPersp);

	def changedKidsVisibility(self, b):
		pass

	def changedVisibility(self, i):
		pass

	def changedSelection(self, i):
		pass

	def changedLabel(self, s):
		pass

	def onDescrChanged(self):
		pass

