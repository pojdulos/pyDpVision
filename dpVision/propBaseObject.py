# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 20:40:37 2023

@author: darek
"""

from abc import ABC, abstractmethod
from PyQt5 import uic
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from .propWidget import PropWidget
from .baseObject import BaseObject

from dpVision.globals import AP

class PropBaseObject(PropWidget):
	def __init__(self, _obj, parent=None):
		super( PropBaseObject, self ).__init__( parent )
		uic.loadUi('dpVision/ui/UiPropBaseObject.ui', self)
		self.obj = _obj

	@staticmethod
	def create(m, parent = 0):
		return PropWidget.build( [ PropBaseObject(m) ], parent )

	def updateProperties(self):
		w = { self.selfVisibleCheck, self.kidsVisibleCheck, self.labelEdit, self.descrEdit }
		for i in w:	i.blockSignals(True)
		self.selfVisibleCheck.setChecked(self.obj.getSelfVisibility())
		self.kidsVisibleCheck.setChecked(self.obj.getKidsVisibility())
		self.labelEdit.setText(self.obj.getLabel())
		self.descrEdit.setText(self.obj.getDescription())
		self.selectedCheck.setChecked(self.obj.isChecked())
		for i in w:	i.blockSignals(False)

	@pyqtSlot(bool)
	def onChangedKidsVisibility(self, b):
		self.obj.setKidsVisibility(b)
		AP.mainWin.dock["workspace"].refreshAll()
		AP.updateAllViews()

	@pyqtSlot(bool)
	def onChangedSelfVisibility(self, b):
		self.obj.setSelfVisibility(b)
		AP.mainWin.dock["workspace"].refreshAll()
		AP.updateAllViews()

	@pyqtSlot(bool)
	def onChangedSelection(self, b):
		pass

	@pyqtSlot(str)
	def onChangedLabel(self, s):
		self.obj.setLabel(s)
		AP.mainWin.dock["workspace"].refreshAll()
		AP.updateAllViews()

	@pyqtSlot()
	def onDescrChanged(self):
		self.obj.setDescription(self.descrEdit.toPlainText())


