# -*- coding: utf-8 -*-
"""
Created on Fri Nov 24 10:50:11 2023

@author: pojdulos
"""

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from .. import AP, Transform

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
			self.addMenu(self.create_move_menu())
			if self.m_obj.hasType('PointCloud') or self.m_obj.hasType('Mesh'):
				self.addSeparator()
				self.addMenu(self.create_point_cloud_menu())
			elif self.m_obj.hasType('Volumetric'):
				self.addSeparator()
				self.addMenu(self.create_volumetric_menu())

		self.addSeparator()
		action = QAction("Refresh tree", self)
		action.triggered.connect(self.refreshTree)
		self.addAction(action)

	def create_point_cloud_menu(self):
		menu = QMenu("point cloud...", self)
		action = QAction("invert normals for vertices", self)
		action.triggered.connect(self.point_cloud_invert_normals)
		menu.addAction(action)
		action = QAction("export as .obj", self)
		action.triggered.connect(self.point_cloud_export_as_obj)
		menu.addAction(action)
		return menu

	def create_volumetric_menu(self):
		menu = QMenu("volumetric...", self)
		action = QAction("create SIFT cloud", self)
		action.triggered.connect(self.volumetric_sift)
		menu.addAction(action)
		action = QAction("marching cube", self)
		action.triggered.connect(self.volumetric_marching_cube)
		menu.addAction(action)
		
		return menu

	def create_move_menu(self):
		menu = QMenu("move to...", self)
		menu.setIcon(QIcon(":/icons/MoveTo.ico"))
		action = QAction("...new model", self)
		action.setData(None)
		action.triggered.connect(self.move_to)
		menu.addAction(action)
		menu.addSeparator()

		for m in AP.mainWin.workspace.m_data:
			if m != self.m_obj and m != self.m_obj.getParent(): 
				if not len(m.children()):
					action = QAction(m.getLabel(), self)
					action.setData(m)
					action.triggered.connect(self.move_to)
					menu.addAction(action)
				else:
					menu.addMenu(self.create_move_submenu(m.getLabel(), m))
		return menu

	def create_move_submenu(self, label, obj):
		menu2 = QMenu(label, self)
		action = QAction(".. here ..", self)
		action.setData(obj)
		action.triggered.connect(self.move_to)
		menu2.addSeparator()

		for m in obj.children():
			if m != self.m_obj and m != self.m_obj.getParent(): 
				if not len(m.children()):
					action = QAction(m.getLabel(), self)
					action.setData(m)
					action.triggered.connect(self.move_to)
					menu2.addAction(action)
				else:
					menu2.addMenu( self.create_move_submenu(m.getLabel(), m) )
		return menu2

	@pyqtSlot()
	def point_cloud_export_as_obj(self):
		fileName = QFileDialog.getSaveFileName( self, "Save File", "", "*.obj")
		
		if fileName[0] != '':
			self.m_obj.export_as_obj(fileName[0])

	@pyqtSlot()
	def point_cloud_invert_normals(self):
		self.m_obj.invert_normals()
		self.m_obj.vBuf = None
		AP.updateAllViews()

	@pyqtSlot()
	def volumetric_sift(self):
		self.m_obj.calculate_sift()

	@pyqtSlot()
	def volumetric_marching_cube(self):
		dlg = QDialog()
		AP.loadUi('dlgMarchingCube.ui', dlg)

		# pmUi.spinBox->setValue( ((CMesh*) AP::WORKSPACE::getCurrentModel()->getChild())->vertices().size() );

		if dlg.exec():
			factor = dlg.spinBox.value()
			close_boundary = dlg.closeBoundaryBox.isChecked()
			self.m_obj.marching_cube(factor=factor, close_boundary=close_boundary)

	@pyqtSlot()
	def refreshTree(self):
		AP.mainWin.dock["workspace"].refreshAll()

	@pyqtSlot()
	def slotCreateEmptyModel(self):
		AP.addObject(Transform(), self.m_obj)

	@pyqtSlot()
	def move_to(self):
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
