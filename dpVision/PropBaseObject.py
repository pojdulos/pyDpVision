# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 20:40:37 2023

@author: darek
"""

from abc import ABC, abstractmethod
from PyQt5 import uic
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from dpVision.PropWidget import PropWidget
from dpVision.BaseObject import BaseObject

from dpVision.Globals import AP

class PropBaseObject(PropWidget):
	def __init__(self, _obj, parent=None):
		super( PropBaseObject, self ).__init__( parent )
		uic.loadUi('dpVision/ui/UiPropBaseObject.ui', self)
		self.obj = _obj

	@staticmethod
	def create(m, parent = 0):
		return PropWidget.build( [ PropBaseObject(m) ], parent )


	def updateProperties(self):
		obj = self.obj

	#@pyqtSlot(bool)
	def changedKidsVisibility(self, b):
		self.obj.setKidsVisibility(b)
		AP.updateAllViews()

	#@pyqtSlot(int)
	def changedVisibility(self, b):
		self.obj.setSelfVisibility(b)
		AP.updateAllViews()

	def changedSelection(self, i):
		pass

	def changedLabel(self, s):
		self.obj.setLabel(s)
		AP.updateAllViews()
		#AP.mainWin.UI::DOCK::WORKSPACE::setItemLabelById(obj->id(), s.toStdWString());

	def onDescrChanged(self):
		self.obj.setDescription(self.descrEdit.toPlainText())


