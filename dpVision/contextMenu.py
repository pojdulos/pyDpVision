# -*- coding: utf-8 -*-
"""
Created on Fri Nov 24 10:50:11 2023

@author: pojdulos
"""

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from .transform import Transform
from .globals import AP

class ContextMenu(QMenu):
	def __init__(self, obj=None, parent=None):
		super( ContextMenu, self ).__init__( parent )
		self.m_obj = obj

		if self.m_obj is None:
			action = QAction("Create empty model", self)
			action.triggered.connect(self.slotCreateEmptyModel)
			self.addAction(action)

			self.addSeparator()
			self.addMenu(AP.mainWin.menuWorkspace)
			self.addMenu(AP.mainWin.menuCamera)
		else:
			action = QAction("Create empty submodel", self)
			action.triggered.connect(self.slotCreateEmptyModel)
			self.addAction(action)
			self.addSeparator()
			self.addMenu(self.createMoveMenu())

		self.addSeparator()
		action = QAction("Refresh tree", self)
		action.triggered.connect(self.refreshTree)
		self.addAction(action)


	def createMoveMenu(self):
		menu = QMenu("move to...", self)
		menu.setIcon(QIcon(":/icons/MoveTo.ico"))
		action = QAction("...new model", self)
		action.setData(None)
		action.triggered.connect(self.moveTo)
		menu.addAction(action)
		menu.addSeparator()

		for m in AP.mainWin.workspace.m_data:
			if m != self.m_obj and m != self.m_obj.getParent(): 
				if not len(m.children()):
					action = QAction(m.getLabel(), self)
					action.setData(m)
					action.triggered.connect(self.moveTo)
					menu.addAction(action)
				else:
					menu.addMenu(self.createMoveSubMenu(m.getLabel(), m))
		return menu

	def createMoveSubMenu(self, label, obj):
		menu2 = QMenu(label, self)
		action = QAction(".. here ..", self)
		action.setData(obj)
		action.triggered.connect(self.moveTo)
		menu2.addSeparator()

		for m in obj.children():
			if m != self.m_obj and m != self.m_obj.getParent(): 
				if not len(m.children()):
					action = QAction(m.getLabel(), self)
					action.setData(m)
					action.triggered.connect(self.moveTo)
					menu2.addAction(action)
				else:
					menu2.addMenu( self.createMoveSubMenu(m.getLabel(), m) )
		return menu2


	@pyqtSlot()
	def refreshTree(self):
		AP.mainWin.dock["workspace"].refreshAll()

	@pyqtSlot()
	def slotCreateEmptyModel(self):
		AP.addObject(Transform(), self.m_obj)

	@pyqtSlot()
	def moveTo(self):
		if self.m_obj is None: return
		
		action = self.sender()
		newParent = action.data()
		oldParent = self.m_obj.getParent()

		_m0 = oldParent.getGlobalTransformation() if oldParent else QMatrix4x4()
		_m1 = newParent.getGlobalTransformation() if newParent else QMatrix4x4()

		newModel = Transform()
		newModel.matrix = Transform.fromTo(m0 = _m0, m1 = _m1)

		AP.addObject(child=newModel, parent=newParent)
		AP.addObject(child=self.m_obj, parent=newModel)
		AP.removeObject(child=self.m_obj, parent=oldParent)

		AP.updateAllViews()
