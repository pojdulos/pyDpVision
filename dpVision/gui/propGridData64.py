# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 20:40:37 2023

@author: darek
"""

from abc import ABC, abstractmethod
from PyQt5 import uic
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from .propBaseObject import PropBaseObject
from .propWidget import PropWidget
import weakref
from .. import GridData64, AP
from .multiSpinBox import MultiSpinBox
import numpy as np

import logging
logger = logging.getLogger(__name__)

class PropGridData64(PropWidget):
	def __init__(self, _obj:GridData64, parent=None):
		super( PropGridData64, self ).__init__( parent )
		if _obj is None:
			logger.warning("Building properties window for object=None")
		self.obj_ref = weakref.ref(_obj)
		self.buildUI()

	def buildUI(self):
		layout = QFormLayout(self)
		self.grid_steps = MultiSpinBox(count=2, labels=("X: ","Y: "))
		#self.grid_steps.setFlat(True)
		self.grid_steps.setStyleSheet("border:none")
		self.use_colormap = QCheckBox()
		self.colormap_range = MultiSpinBox(count=2, labels=("min: ","max: "))
		self.uniform_color = MultiSpinBox(count=3, labels=("R=","G=","B="))
		self.uniform_color.setStyleSheet("border:none")
		self.use_mesh = QCheckBox()

		self.z_filter = QDoubleSpinBox()
		self.z_filter.setValue(0.0)

		layout.addRow("grid steps [um]:", self.grid_steps)
		layout.addRow("use colormap", self.use_colormap)
		layout.addRow("colormap range", self.colormap_range)
		layout.addRow("uniform color", self.uniform_color)
		layout.addRow("draw as surface", self.use_mesh)
		layout.addRow("Z filter", self.z_filter)
		self.setLayout(layout)

		self.grid_steps.valueChanged.connect(self.on_grid_steps_valueChanged)
		self.use_colormap.toggled.connect(self.on_use_colormap_toggled)
		self.colormap_range.valueChanged.connect(self.on_colormap_range_valueChanged)
		self.uniform_color.valueChanged.connect(self.on_uniform_color_valueChanged)
		self.use_mesh.toggled.connect(self.on_use_mesh_toggled)
		self.z_filter.valueChanged.connect(self.on_z_filter_valueChanged)


	@staticmethod
	def create(m:GridData64, parent = 0):
		return PropWidget.build( [ 
				PropGridData64(m),
				PropBaseObject(m),
			], parent )

	def updateProperties(self):
		obj:GridData64 = self.obj_ref()
		if obj is None:
			return

		w = self.get_subwidgets()
		for i in w:	i.blockSignals(True)

		self.grid_steps.setValue((obj.stepX, obj.stepY))
		self.use_colormap.setChecked(not obj.use_uniform_color)
		self.colormap_range.setValue(obj.get_colormap_range())
		self.colormap_range.setEnabled(not obj.use_uniform_color)
		self.uniform_color.setValue(obj.uniform_color)
		self.uniform_color.setEnabled(obj.use_uniform_color)
		self.use_mesh.setChecked(obj.use_mesh)
		self.z_filter.setValue(obj.z_filter)

		for i in w:	i.blockSignals(False)
		self.update()

	@pyqtSlot(bool)
	def on_use_colormap_toggled(self, b):
		obj = self.obj_ref()
		if obj is None:
			return

		obj.use_uniform_color = not b
		self.uniform_color.setEnabled(obj.use_uniform_color)
		self.colormap_range.setEnabled(not obj.use_uniform_color)

		AP.updateAllViews()

	@pyqtSlot(tuple)
	def on_colormap_range_valueChanged(self, vals):
		obj = self.obj_ref()
		if obj is None:
			return
		obj.m_minZ, obj.m_maxZ = vals
		AP.updateAllViews()

	@pyqtSlot(tuple)
	def on_grid_steps_valueChanged(self, vals):
		obj = self.obj_ref()
		if obj is None:
			return
		obj.stepX, obj.stepY = vals
		AP.updateAllViews()

	@pyqtSlot(tuple)
	def on_uniform_color_valueChanged(self, vals):
		obj = self.obj_ref()
		if obj is None:
			return
		obj.uniform_color = vals
		AP.updateAllViews()

	@pyqtSlot(bool)
	def on_use_mesh_toggled(self, b):
		obj = self.obj_ref()
		if obj is None:
			return

		obj.set_display_mode(use_mesh = b)

		AP.updateAllViews()

	@pyqtSlot(float)
	def on_z_filter_valueChanged(self, v):
		obj = self.obj_ref()
		if obj is None:
			return
		obj.z_filter = v
		AP.updateAllViews()

	# def on_plane_changed(self, plane, idx, val):
	# 	obj = self.obj_ref()

	# 	val2 = obj.m_rplanes[plane][(idx+1)%2]

	# 	if (idx==1 and val <= val2) or (idx==0 and val >= val2):
	# 		return

	# 	obj.m_rplanes[plane][idx] = val

	# 	obj.projectTo3D()
		
	# 	AP.mainWin.dock["workspace"].refreshAll()
	# 	AP.updateAllViews()

	# def on_gain_changed(self, cur_idx, cur_val):
	# 	obj = self.obj_ref()
	# 	obj.m_gains[cur_idx] = cur_val

	# 	obj.projectTo3D()
		
	# 	AP.mainWin.dock["workspace"].refreshAll()
	# 	AP.updateAllViews()

	# def on_index_changed(self, cur_idx, cur_val):
	# 	obj = self.obj_ref()

	# 	for i in range (4):
	# 		if i != cur_idx and obj.m_real_dims[i] == cur_val:
	# 			obj.m_real_dims[i] = obj.m_real_dims[cur_idx]
	# 			break

	# 	obj.m_real_dims[cur_idx] = cur_val
		
	# 	obj.projectTo3D()

	# 	self.updateProperties()				

	# 	AP.mainWin.dock["workspace"].refreshAll()
	# 	AP.updateAllViews()


