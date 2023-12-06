# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 20:40:37 2023

@author: darek
"""

from abc import ABC, abstractmethod
from PyQt5 import uic

from dpVision.PropWidget import PropWidget
from dpVision.PropBaseObject import PropBaseObject

class PropMotion(PropWidget):
	def __init__(self, _obj, parent=None):
		super( PropMotion, self ).__init__( parent )
		uic.loadUi('dpVision/ui/UiPropMotion.ui', self)
		self.obj = _obj

	@staticmethod
	def create(m, parent = 0):
		return PropWidget.build( [ PropBaseObject(m), PropMotion(m) ], parent )

	def updateProperties(self):
		obj = self.obj


	def clearMatrix(self):
		pass

	def copyToClipboard(self):
		pass

	def pasteFromClipboard(self):
		pass

	#QStandardItem*
	def onItemChanged(self, item):
		pass
	
	# QModelIndex&, QModelIndex&
	def onCurrentChanged(self, current, previous):
		pass

	# QStandardItem
	def dataChanged(self, item):
		pass

	def onSliderValueChanged(self, val):
		pass

	def onPlayButtonClicked(self):
		if self.obj.isPlaying():
			self.obj.stopPlaying()
		else:
			self.obj.startPlaying()

	# QModelIndex
	def onTreeViewItemClicked(self, index):
		pass

	def updateGroupFrame(self):
		pass

	def updateMatrix(self):
		pass

	def updatePropertiesTree(self):
		pass
