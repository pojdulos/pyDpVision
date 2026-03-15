# -*- coding: utf-8 -*-
"""
Created on Fri Nov 24 10:50:11 2023

@author: pojdulos
"""

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from dpVision.volumetric import Volumetric

from .dialogSiftParameters import DialogSiftParameters
from .dialogVolumetricMetadata import DialogVolumetricMetadata
from .taskManager import FunctionTaskRunner

import numpy as np

from .. import AP, Transform, PointCloud

class ContextMenu(QMenu):
	def __init__(self, obj=None, parent=None):
		super( ContextMenu, self ).__init__( parent )
		self.m_obj = obj

		action = QAction("Create plane", self)
		action.triggered.connect(self.slot_create_plane)
		self.addAction(action)

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
			if self.m_obj.hasType('GridData64'):
				self.addSeparator()
				self.addMenu(self.create_grid_menu())
			elif self.m_obj.hasType('PointCloud') or self.m_obj.hasType('Mesh'):
				self.addSeparator()
				self.addMenu(self.create_point_cloud_menu())
			elif self.m_obj.hasType('Volumetric'):
				self.addSeparator()
				self.addMenu(self.create_volumetric_menu())
			elif self.m_obj.hasType('DHJoint'):
				self.addSeparator()
				self.addMenu(self.create_dhjoint_menu())
			elif self.m_obj.hasType('DHModel'):
				self.addSeparator()
				self.addMenu(self.create_dhmodel_menu())

		self.addSeparator()
		action = QAction("Refresh tree", self)
		action.triggered.connect(self.refreshTree)
		self.addAction(action)

	def create_dhmodel_menu(self):
		menu = QMenu("dh model...", self)
		action = QAction("export subtree", self)
		action.triggered.connect(self.export_DHModel)
		menu.addAction(action)
		return menu

	def create_dhjoint_menu(self):
		menu = QMenu("dh joint...", self)
		action = QAction("export subtree", self)
		action.triggered.connect(self.export_subtree)
		menu.addAction(action)
		action = QAction("view as vector", self)
		action.triggered.connect(
			lambda: (
				setattr(self.m_obj, 'view_as_vector', True), 
				AP.updateAllViews(), 
				AP.updateProperties()
			)
		)
		menu.addAction(action)
		action = QAction("view as arm", self)
		action.triggered.connect(
			lambda: (
				setattr(self.m_obj, 'view_as_vector', False),
				AP.updateAllViews(), 
				AP.updateProperties()
			)
		)
		menu.addAction(action)
		menu.addSeparator()
		set_menu = QMenu("set as...", self)
		menu.addMenu(set_menu)
		action = QAction("revolute", self)
		action.triggered.connect(
			lambda: (
				self.m_obj.set_type(type='R'), 
				AP.updateAllViews(), 
				AP.updateProperties()
			))
		set_menu.addAction(action)
		action = QAction("prismatic", self)
		action.triggered.connect(
			lambda: (
				self.m_obj.set_type(type='P'), 
				AP.updateAllViews(), 
				AP.updateProperties()
			))
		set_menu.addAction(action)
		action = QAction("fixed", self)
		action.triggered.connect(
			lambda: (
				self.m_obj.set_type(type='F'), 
				AP.updateAllViews(), 
				AP.updateProperties()
			))
		set_menu.addAction(action)

		add_menu = QMenu("add segment...", self)
		menu.addMenu(add_menu)
		action = QAction("revolute", self)
		action.triggered.connect(
			lambda: 
				self.dhjoint_add_segment(type='R')
			)
		add_menu.addAction(action)
		action = QAction("prismatic", self)
		action.triggered.connect(
			lambda: 
				self.dhjoint_add_segment(type='P')
			)
		add_menu.addAction(action)
		action = QAction("fixed", self)
		action.triggered.connect(
			lambda: 
				self.dhjoint_add_segment(type='F')
			)
		add_menu.addAction(action)
		return menu

	def export_subtree(self):
		fileName = QFileDialog.getSaveFileName( self, "Save File", "", "*.json")
		
		if fileName[0] != '':
			self.m_obj.export_subtree(fileName[0])

	def export_DHModel(self):
		fileName = QFileDialog.getSaveFileName( self, "Save File", "", "*.json")
		dict = self.m_obj.subtree_to_dict()
		with open(fileName[0], 'w') as f:
			import json
			json.dump(dict, f, indent=4)

	def create_grid_menu(self):
		menu = QMenu("grid...", self)
		action = QAction("convert to mesh", self)
		action.triggered.connect(self.grid_convert_to_mesh)
		menu.addAction(action)
		return menu

	def create_point_cloud_menu(self):
		menu = QMenu("point cloud...", self)
		action = QAction("invert normals for vertices", self)
		action.triggered.connect(self.point_cloud_invert_normals)
		menu.addAction(action)
		action = QAction("export as .obj", self)
		action.triggered.connect(self.point_cloud_export_as_obj)
		menu.addAction(action)
		if self.m_obj.hasType('Mesh'):
			menu.addSeparator()
			action = QAction("convert to point cloud", self)
			action.triggered.connect(self.mesh_convert_to_point_cloud)
			menu.addAction(action)
			action = QAction("convert to grid 2.5D", self)
			action.triggered.connect(self.mesh_convert_to_grid)
			menu.addAction(action)
		return menu

	def create_volumetric_menu(self):
		menu = QMenu("volumetric...", self)
		action = QAction("set metadata", self)
		action.triggered.connect(self.volumetric_set_metadata)
		menu.addAction(action)
		menu.addSeparator()
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
			if m != self.m_obj and m != self.m_obj.parent: 
				if not len(m.children()):
					action = QAction(m.label, self)
					action.setData(m)
					action.triggered.connect(self.move_to)
					menu.addAction(action)
				else:
					menu.addMenu(self.create_move_submenu(m.label, m))
		return menu

	def create_move_submenu(self, label, obj):
		menu2 = QMenu(label, self)
		action = QAction(".. here ..", self)
		action.setData(obj)
		action.triggered.connect(self.move_to)
		menu2.addSeparator()

		for m in obj.children():
			if m != self.m_obj and m != self.m_obj.parent: 
				if not len(m.children()):
					action = QAction(m.label, self)
					action.setData(m)
					action.triggered.connect(self.move_to)
					menu2.addAction(action)
				else:
					menu2.addMenu( self.create_move_submenu(m.label, m) )
		return menu2

	@pyqtSlot()
	def dhjoint_add_segment(self, type='R'):
		child = self.m_obj.create(type=type)
		AP.addObject( child, self.m_obj )
		AP.updateAllViews()

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
	def volumetric_set_metadata(self):
		dlg = DialogVolumetricMetadata(self.m_obj)
		if dlg.exec():
			print("OK")
			AP.updateAllViews()

	@pyqtSlot()
	def volumetric_sift(self):
		nfeatures=0
		nOctaveLayers=3
		contrastThreshold=0.04
		edgeThreshold=10.0
		sigma=1.6
		factor=1

		dlg = DialogSiftParameters(
			nfeatures=nfeatures, 
			nOctaveLayers=nOctaveLayers, 
			contrastThreshold=contrastThreshold, 
			edgeThreshold=edgeThreshold, 
			sigma=sigma, 
			factor=factor )

		if dlg.exec():
			nfeatures, nOctaveLayers, contrastThreshold, edgeThreshold, sigma, factor = dlg.get_fields()

			cloud = self.m_obj.sift_cloud(
				nfeatures=nfeatures, 
				nOctaveLayers=nOctaveLayers, 
				contrastThreshold=contrastThreshold, 
				edgeThreshold=edgeThreshold, 
				sigma=sigma, 
				factor=factor )

			AP.addObject(cloud, self.m_obj)
			AP.updateAllViews()

	@pyqtSlot()
	def volumetric_marching_cube(self):
		vol : Volumetric = self.m_obj
		
		dlg = QDialog()
		AP.loadUi('dlgMarchingCube.ui', dlg)

		dlg.factor_spin.setValue(1)

		dlg.thresh_auto_radio.setChecked(True)

		spin : QDoubleSpinBox = dlg.thresh_spin
		spin.setMinimum(vol.m_volume.min())
		spin.setMaximum(vol.m_volume.max())
		spin.setValue(vol.m_minDisplWin)

		dlg.sigma_auto_radio.setChecked(True)
		dlg.sigma_spin.setValue(0.0) # auto

		if dlg.exec():
			factor    = dlg.factor_spin.value()
			sigma     = None if dlg.sigma_auto_radio.isChecked() else dlg.sigma_spin.value()
			threshold = None if dlg.thresh_auto_radio.isChecked() else vol.m_minDisplWin if dlg.thresh_displ_radio.isChecked() else dlg.thresh_spin.value()
			close_boundary = dlg.closeBoundaryBox.isChecked()

			denoise_3d = dlg.denoise3dBox.isChecked()
			kwargs = dict(factor=factor, sigma_mm=sigma, threshold=threshold,
			              close_boundary=close_boundary, denoise_3d=denoise_3d)

			runner = FunctionTaskRunner(
				vol.marching_cube_compute,
				label=f"Marching Cube: {getattr(vol, 'label', 'Volumetric')}",
				kind="compute",
				progress_text="Obliczam marching cubes...",
				inject_progress=True,
				**kwargs,
			)

			def handle_success(result):
				from dpVision.mesh import Mesh
				vertices, faces = result
				mesh = Mesh.create(vertices=vertices, faces=faces, invert_normals=True)
				AP.addObject(mesh, vol)

			def handle_error(error):
				QMessageBox.critical(None, "Marching Cube – błąd", str(error))

			AP.mainWin.taskManager.start_runner(
				runner,
				on_success=handle_success,
				on_error=handle_error,
				kind="compute",
				label=f"Marching Cube: {getattr(vol, 'label', 'Volumetric')}",
			)

	@pyqtSlot()
	def refreshTree(self):
		AP.mainWin.dock["workspace"].refreshAll()

	@pyqtSlot()
	def mesh_convert_to_grid(self):
		grid = self.m_obj.to_grid25D()
		if grid is None:
			QMessageBox.warning(None, "Convert to grid", "Nie można przekonwertować — dane nie tworzą regularnego gridu 2.5D.")
			return
		parent = self.m_obj.parent
		AP.addObject(grid, parent)
		AP.updateAllViews()
		AP.updateProperties()

	@pyqtSlot()
	def mesh_convert_to_point_cloud(self):
		pc = PointCloud()
		pc.label = f"{self.m_obj.label}_cloud"
		pc.m_vertices = np.array(self.m_obj.m_vertices, dtype=np.float32, copy=True)
		if getattr(self.m_obj, 'm_vcolors', np.empty((0, 4))).shape[0] == len(pc.m_vertices):
			pc.m_vcolors = np.array(self.m_obj.m_vcolors, dtype=np.ubyte, copy=True)
		if getattr(self.m_obj, 'm_vnormals', np.empty((0, 3))).shape[0] == len(pc.m_vertices):
			pc.m_vnormals = np.array(self.m_obj.m_vnormals, dtype=np.float32, copy=True)
		parent = self.m_obj.parent
		AP.addObject(pc, parent)
		AP.updateAllViews()
		AP.updateProperties()

	@pyqtSlot()
	def grid_convert_to_mesh(self):
		mesh = self.m_obj.to_mesh()
		if mesh is None:
			QMessageBox.warning(None, "Convert to mesh", "Nie można przekonwertować gridu do siatki.")
			return
		parent = self.m_obj.parent
		AP.addObject(mesh, parent)
		AP.updateAllViews()
		AP.updateProperties()

	@pyqtSlot()
	def slotCreateEmptyModel(self):
		AP.addObject(Transform(), self.m_obj)

	@pyqtSlot()
	def slot_create_plane(self):
		from .. import AnnotationPlane
		AP.addObject(AnnotationPlane(), self.m_obj)

	@pyqtSlot()
	def move_to(self):
		if self.m_obj is None: return
		
		action = self.sender()
		newParent = action.data()
		oldParent = self.m_obj.parent

		_m0 = oldParent.getGlobalTransformation() if oldParent else np.eye(4, dtype=np.float64)
		_m1 = newParent.getGlobalTransformation() if newParent else np.eye(4, dtype=np.float64)

		newModel = Transform()
		newModel.matrix = Transform.fromTo(m0 = _m0, m1 = _m1)

		AP.addObject(child=newModel, parent=newParent)
		AP.addObject(child=self.m_obj, parent=newModel)
		AP.removeObject(child=self.m_obj, parent=oldParent)

		AP.updateAllViews()

	@pyqtSlot()
	def copy_to(self):
		if self.m_obj is None: return
		
		action = self.sender()
		newParent = action.data()
		oldParent = self.m_obj.parent

		_m0 = oldParent.getGlobalTransformation() if oldParent else QMatrix4x4()
		_m1 = newParent.getGlobalTransformation() if newParent else QMatrix4x4()

		newModel = Transform()
		newModel.matrix = Transform.fromTo(m0 = _m0, m1 = _m1)

		AP.addObject(child=newModel, parent=newParent)
		AP.addObject(child=self.m_obj, parent=newModel)
		AP.removeObject(child=self.m_obj, parent=oldParent)

		AP.updateAllViews()
