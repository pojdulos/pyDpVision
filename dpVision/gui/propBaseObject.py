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
import weakref
from .. import AP

class PropBaseObject(PropWidget):
	def __init__(self, _obj, parent=None):
		super( PropBaseObject, self ).__init__( parent )
		AP.loadUi('propBaseObject.ui', self)
		self.obj_ref = weakref.ref(_obj)

	@staticmethod
	def create(m, parent = 0):
		return PropWidget.build( [ PropBaseObject(m) ], parent )

	def updateProperties(self):
		obj = self.obj_ref()
		w = self.get_subwidgets()
		for i in w:	i.blockSignals(True)
		self.selfVisibleCheck.setChecked(obj.getSelfVisibility())
		self.kidsVisibleCheck.setChecked(obj.getKidsVisibility())
		self.labelEdit.setText(obj.label)
		self.descrEdit.setText(obj.description)
		self.selectedCheck.setChecked(obj.checked)
		for i in w:	i.blockSignals(False)

	@pyqtSlot(bool)
	def onChangedKidsVisibility(self, b):
		obj = self.obj_ref()
		obj.setKidsVisibility(b)
		AP.mainWin.dock["workspace"].refreshAll()
		AP.updateAllViews()

	@pyqtSlot(bool)
	def onChangedSelfVisibility(self, b):
		obj = self.obj_ref()
		obj.setSelfVisibility(b)
		AP.mainWin.dock["workspace"].refreshAll()
		AP.updateAllViews()

	@pyqtSlot(bool)
	def onChangedSelection(self, b):
		print('PropBaseObject: checked' if b else 'PropBaseObject: unchecked')
		obj = self.obj_ref()
		if obj is not None:
			obj.checked = b
			self.object_updated.emit(obj)

	@pyqtSlot(str)
	def onChangedLabel(self, s):
		obj = self.obj_ref()
		obj.label = s
		AP.mainWin.dock["workspace"].refreshAll()
		AP.updateAllViews()

	@pyqtSlot()
	def onDescrChanged(self):
		obj = self.obj_ref()
		obj.description = self.descrEdit.toPlainText()


