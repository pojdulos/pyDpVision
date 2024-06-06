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

from .globals import AP
from .propWidget import PropWidget
from .propBaseObject import PropBaseObject

class PropMotion(PropWidget):
	def __init__(self, _obj, parent=None):
		super( PropMotion, self ).__init__( parent )
		uic.loadUi('dpVision/ui/UiPropMotion.ui', self)
		self.obj = _obj
		self.setTreeView()

	@staticmethod
	def create(m, parent = 0):
		return PropWidget.build( [ PropBaseObject(m), PropMotion(m) ], parent )

	def setTreeView(self):
		self.treeView.setSelectionBehavior(QAbstractItemView.SelectRows)
		model = QStandardItemModel()
		model.setHorizontalHeaderLabels({ "order", "time", })
		self.treeView.setModel(model)
		self.treeView.setUniformRowHeights(True)

		#self.treeView.setItemDelegate(CSpinBoxDelegate())
		self.treeView.setItemDelegate(QStyledItemDelegate())

		for key in range(self.obj.size()):
			self.addFrame(model.invisibleRootItem(), key, self.obj.frame(key))

		self.currentFrameSlider.setMinimum(0)
		self.currentFrameSlider.setMaximum(self.obj.size()-1)

		self.treeView.selectionModel().currentChanged.connect(self.onCurrentChanged)
		model.itemChanged.connect(self.dataChanged) #(QStandardItem)

	def addFrame(self, parent, frameKey, frameVal):
		if parent:
			leftItem = QStandardItem(str(frameKey))
			leftItem.setAccessibleDescription(str(frameKey))
			leftItem.setData(frameKey, Qt.ItemDataRole.UserRole)
			leftItem.setEditable(False)

			vs = str(frameVal.msec)
			#QString vs = frameVal.t.toString("[","]",",");

			leftItemValue = QStandardItem()
			leftItemValue.setData(vs, Qt.ItemDataRole.DisplayRole)
			leftItemValue.setData(frameVal.msec, Qt.ItemDataRole.EditRole)
			leftItemValue.setData(frameKey, Qt.ItemDataRole.UserRole)

			parent.appendRow([ leftItem, leftItemValue ])

			return leftItem
		return None

	def updateProperties(self):
		self.currentFrameSlider.blockSignals(True)
		self.currentFrameSlider.setValue(self.obj.currentKey())
		self.currentFrameSlider.blockSignals(False)

		self.updateGroupFrame()
		self.updatePropertiesTree()

	def clearMatrix(self):
		self.obj.currentFrame().transform.reset()
		AP.mainWin.dock['properties'].updateProperties()
		AP.updateAllViews()
	
	def copyToClipboard(self):
		self.obj.currentFrame().transform.copyToClipboard()

	def pasteFromClipboard(self):
		self.obj.currentFrame().transform.pasteFromClipboard()
		AP.mainWin.dock['properties'].updateProperties()
		AP.updateAllViews()

	#QStandardItem*
	def onItemChanged(self, item):
		pass
	
	# QModelIndex&, QModelIndex&
	def onCurrentChanged(self, current, previous):
		if current.isValid():
			model = self.treeView.model()
			clickedItem = model.itemFromIndex(current)

			key = clickedItem.data(Qt.UserRole)

			self.currentFrameSlider.blockSignals(True)
			self.currentFrameSlider.setValue(key)
			self.currentFrameSlider.blockSignals(False)

			#//qInfo() << "Sequence item clicked. Key=" << key << Qt::endl;
			#//emit(currentObjectChanged(clickedObject->id()));

			self.obj.setKey(key)

			self.updateGroupFrame()
			AP.updateAllViews()
		else:
			print("item index is invalid")
			#//emit(currentObjectChanged(NO_CURRENT_MODEL));

	# QStandardItem
	def dataChanged(self, item):
		pass

	def onSliderValueChanged(self, val):
		self.obj.setKey(val)
		self.updateProperties()
		AP.updateAllViews()

	def onPlayButtonClicked(self):
		if self.obj.isPlaying():
			self.obj.stopPlaying()
		else:
			self.obj.startPlaying()

	# QModelIndex
	def onTreeViewItemClicked(self, index):
		pass

	def updateGroupFrame(self):
		self.updateMatrix()

	def updateMatrix(self):
		t = self.obj.currentFrame().transform
		self.matrixTable.blockSignals(True)
		for row in range(4):
			for col in range(4):
				val = t.matrix[row,col]	
				index = self.matrixTable.model().index(row, col)
				self.matrixTable.model().setData(index, val)
		self.matrixTable.blockSignals(False)

	def updatePropertiesTree(self):
		model = self.treeView.model()
		index = model.index(self.obj.currentKey(), 0) # 0 oznacza pierwszą kolumnę

		selectionModel = self.treeView.selectionModel()
		# ui.treeView->blockSignals(true);
		selectionModel.clearSelection()
		selectionModel.select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows);
		# ui.treeView->blockSignals(false);
