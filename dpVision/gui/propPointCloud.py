# -*- coding: utf-8 -*-
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QComboBox, QDoubleSpinBox, QFormLayout, QLabel

from .propBaseObject import PropBaseObject
from .propWidget import PropWidget
from .. import AP
from ..pointCloud import RenderMode
import weakref


_MODES = [
	("Points", RenderMode.POINTS),
	("Gaussian splat", RenderMode.SPLAT),
]


class PropPointCloud(PropWidget):
	def __init__(self, _obj, parent=None):
		super().__init__(parent)
		self.obj_ref = weakref.ref(_obj)
		self.buildUI()

	def buildUI(self):
		layout = QFormLayout(self)

		self.mode_combo = QComboBox()
		for label, _ in _MODES:
			self.mode_combo.addItem(label)
		layout.addRow("render mode", self.mode_combo)

		self.point_size = QDoubleSpinBox()
		self.point_size.setRange(1.0, 20.0)
		self.point_size.setSingleStep(1.0)
		self.point_size.setDecimals(1)
		layout.addRow("point size", self.point_size)

		self.splat_scale = QDoubleSpinBox()
		self.splat_scale.setRange(0.1, 20.0)
		self.splat_scale.setSingleStep(0.1)
		self.splat_scale.setDecimals(2)
		layout.addRow("splat scale", self.splat_scale)

		self.lbl_points = QLabel()
		self.lbl_spacing = QLabel()
		layout.addRow("points", self.lbl_points)
		layout.addRow("spacing est.", self.lbl_spacing)

		self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
		self.point_size.valueChanged.connect(self.on_point_size_changed)
		self.splat_scale.valueChanged.connect(self.on_splat_scale_changed)

	@staticmethod
	def create(m, parent=0):
		return PropWidget.build([
			PropPointCloud(m),
			PropBaseObject(m),
		], parent)

	def updateProperties(self):
		obj = self.obj_ref()
		if obj is None:
			return

		for w in self.get_subwidgets():
			w.blockSignals(True)

		mode_idx = 0
		for i, (_, mode) in enumerate(_MODES):
			if mode == obj.render_mode:
				mode_idx = i
				break
		self.mode_combo.setCurrentIndex(mode_idx)
		self.point_size.setValue(float(obj.point_size))
		self.splat_scale.setValue(float(obj.splat_scale))
		self.splat_scale.setEnabled(obj.render_mode == RenderMode.SPLAT)
		self.lbl_points.setText(f"{len(obj.m_vertices):,}")
		self.lbl_spacing.setText(f"{obj._estimate_point_spacing():.4f}")

		for w in self.get_subwidgets():
			w.blockSignals(False)

	@pyqtSlot(int)
	def on_mode_changed(self, idx):
		obj = self.obj_ref()
		if obj is None or idx < 0 or idx >= len(_MODES):
			return
		obj.render_mode = _MODES[idx][1]
		self.splat_scale.setEnabled(obj.render_mode == RenderMode.SPLAT)
		AP.updateAllViews()

	@pyqtSlot(float)
	def on_point_size_changed(self, val):
		obj = self.obj_ref()
		if obj is None:
			return
		obj.point_size = val
		AP.updateAllViews()

	@pyqtSlot(float)
	def on_splat_scale_changed(self, val):
		obj = self.obj_ref()
		if obj is None:
			return
		obj.splat_scale = val
		AP.updateAllViews()
