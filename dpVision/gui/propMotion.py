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

from .. import AP

from .propWidget import PropWidget
from .propBaseObject import PropBaseObject
import weakref

class PropMotion(PropWidget):
	def __init__(self, _obj, parent=None):
		super( PropMotion, self ).__init__( parent )
		#uic.loadUi('dpVision/gui/forms/propMotion.ui', self)
		AP.loadUi('propMotion.ui', self)
		self.obj_ref = weakref.ref(_obj)
		self.setTreeView()

	@staticmethod
	def create(m, parent = 0):
		return PropWidget.build( [ PropBaseObject(m), PropMotion(m) ], parent )

	def setTreeView(self):
		obj = self.obj_ref()
		self.treeView.setSelectionBehavior(QAbstractItemView.SelectRows)
		model = QStandardItemModel()
		model.setHorizontalHeaderLabels({ "order", "time", })
		self.treeView.setModel(model)
		self.treeView.setUniformRowHeights(True)

		#self.treeView.setItemDelegate(CSpinBoxDelegate())
		self.treeView.setItemDelegate(QStyledItemDelegate())

		for key in range(obj.size()):
			self.addFrame(model.invisibleRootItem(), key, obj.frame(key))

		self.currentFrameSlider.setMinimum(0)
		self.currentFrameSlider.setMaximum(obj.size()-1)

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
		obj = self.obj_ref()
		self.currentFrameSlider.blockSignals(True)
		self.currentFrameSlider.setValue(obj.currentKey())
		self.currentFrameSlider.blockSignals(False)

		self.updateGroupFrame()
		self.updatePropertiesTree()

	def clearMatrix(self):
		obj = self.obj_ref()
		obj.currentFrame().transform.reset()
		AP.mainWin.dock['properties'].updateProperties()
		AP.updateAllViews()
	
	def copyToClipboard(self):
		obj = self.obj_ref()
		obj.currentFrame().transform.copyToClipboard()

	def pasteFromClipboard(self):
		obj = self.obj_ref()
		obj.currentFrame().transform.pasteFromClipboard()
		AP.mainWin.dock['properties'].updateProperties()
		AP.updateAllViews()

	#QStandardItem*
	def onItemChanged(self, item):
		pass
	
	# QModelIndex&, QModelIndex&
	def onCurrentChanged(self, current, previous):
		obj = self.obj_ref()
		if current.isValid():
			model = self.treeView.model()
			clickedItem = model.itemFromIndex(current)

			key = clickedItem.data(Qt.UserRole)

			self.currentFrameSlider.blockSignals(True)
			self.currentFrameSlider.setValue(key)
			self.currentFrameSlider.blockSignals(False)

			#//qInfo() << "Sequence item clicked. Key=" << key << Qt::endl;
			#//emit(currentObjectChanged(clickedObject->id()));

			obj.setKey(key)

			self.updateGroupFrame()
			AP.updateAllViews()
		else:
			print("item index is invalid")
			#//emit(currentObjectChanged(NO_CURRENT_MODEL));

	# QStandardItem
	def dataChanged(self, item):
		pass

	def onSliderValueChanged(self, val):
		obj = self.obj_ref()
		obj.setKey(val)
		self.updateProperties()
		AP.updateAllViews()

	def onPlayButtonClicked(self):
		obj = self.obj_ref()
		if obj.isPlaying():
			obj.stopPlaying()
		else:
			obj.startPlaying()

	# QModelIndex
	def onTreeViewItemClicked(self, index):
		pass

	def updateGroupFrame(self):
		self.updateMatrix()

	def updateMatrix(self):
		obj = self.obj_ref()
		t = obj.currentFrame().transform
		self.matrixTable.blockSignals(True)
		for row in range(4):
			for col in range(4):
				val = t.matrix[row,col]	
				index = self.matrixTable.model().index(row, col)
				self.matrixTable.model().setData(index, val)
		self.matrixTable.blockSignals(False)

	def updatePropertiesTree(self):
		obj = self.obj_ref()
		model = self.treeView.model()
		index = model.index(obj.currentKey(), 0) # 0 oznacza pierwszą kolumnę

		selectionModel = self.treeView.selectionModel()
		# ui.treeView->blockSignals(true);
		selectionModel.clearSelection()
		selectionModel.select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows);
		# ui.treeView->blockSignals(false);
