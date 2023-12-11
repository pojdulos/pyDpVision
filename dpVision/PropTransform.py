# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
import re
from PyQt5 import uic
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from dpVision.Globals import AP

from dpVision.PropWidget import PropWidget
from dpVision.PropBaseObject import PropBaseObject
from dpVision.Transform import Transform

class PropTransform(PropWidget):
	def __init__(self, _obj, parent=None):
		super( PropTransform, self ).__init__( parent )
		uic.loadUi('dpVision/ui/UiPropTransform.ui', self)
		
		self.treeView.setVisible(False)
		self.resize(self.layout().sizeHint())

		self.m_trans = _obj

	@staticmethod
	def create(m, parent = 0):
		return PropWidget.build( [ PropBaseObject(m), PropTransform(m) ], parent )

	def updateProperties(self):
		if self.m_trans is None:
			return
		self.updateMatrix()

	def updateMatrix(self):
		self.matrixTable.blockSignals(True)
		for row in range(4):
			for col in range(4):
				index = self.matrixTable.model().index(row,col)
				value = self.m_trans.matrix[row,col]
				self.matrixTable.model().setData(index, value)
		self.matrixTable.blockSignals(False)

	def changedEul(self,double):
		pass
	
	def changedTra(self,double):
		pass

	def changedSca(self,double):
		pass
		
	def changedQua(self,double):
		pass
	
	def clearMatrix(self):
		self.m_trans.reset()
		AP.mainWin.dock['properties'].updateProperties()
		AP.updateAllViews()
	
	def copyToClipboard(self):
		self.m_trans.copyToClipboard()

	def pasteFromClipboard(self):
		self.m_trans.pasteFromClipboard()
		AP.mainWin.dock['properties'].updateProperties()
		AP.updateAllViews()

	def onRotButton(self):
		pass

	def onScaleCheck(self,i):
		pass
