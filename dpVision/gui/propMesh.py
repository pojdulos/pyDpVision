# -*- coding: utf-8 -*-
"""Property panel for mesh objects, including per-object X-ray source tuning."""

from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import (
	QCheckBox,
	QColorDialog,
	QComboBox,
	QDoubleSpinBox,
	QFormLayout,
	QGroupBox,
	QLayout,
	QSizePolicy,
	QVBoxLayout,
	QWidget,
)
from PyQt5.QtGui import QColor

from .. import AP, ensure_xray_source_config
from .propWidget import PropWidget
from .propBaseObject import PropBaseObject
import weakref


class PropMesh(PropWidget):
	"""Edit mesh appearance and per-object X-ray source settings."""

	def __init__(self, _obj, parent=None):
		"""Create the mesh property panel and append X-ray controls to the loaded UI."""
		super(PropMesh, self).__init__(parent)
		AP.loadUi('propMesh.ui', self)
		self.obj_ref = weakref.ref(_obj)
		ensure_xray_source_config(_obj)
		self._relax_ui_constraints()
		self._build_xray_group()
		self._connect_xray_signals()

	@staticmethod
	def create(m, parent=0):
		"""Build the full mesh property panel for the selected object."""
		return PropWidget.build([PropBaseObject(m), PropMesh(m)], parent)

	def _relax_ui_constraints(self):
		"""Remove fixed-size limits inherited from the legacy `.ui` definition."""
		for widget in (self, getattr(self, "mesh", None), getattr(self, "info", None)):
			if widget is None:
				continue
			widget.setMinimumSize(0, 0)
			widget.setMaximumSize(16777215, 16777215)
			widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

		root_layout = self.layout()
		if isinstance(root_layout, QLayout):
			self._main_container = QWidget(self)
			self._main_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
			self._main_layout = QVBoxLayout(self._main_container)
			self._main_layout.setContentsMargins(0, 0, 0, 0)
			self._main_layout.setSpacing(6)
			root_layout.removeWidget(self.mesh)
			self.mesh.setParent(self._main_container)
			self._main_layout.addWidget(self.mesh)
			root_layout.addWidget(self._main_container)

	def _build_xray_group(self):
		"""Append one readable X-ray configuration group below the existing mesh controls."""
		self.xrayGroup = QGroupBox("XRay Source")
		self.xrayLayout = QFormLayout(self.xrayGroup)
		self.xrayLayout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
		self.xrayLayout.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
		self.xrayLayout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
		self.xrayEnabledCheck = QCheckBox("Enabled in VirtualXRay")
		self.xrayModeCombo = QComboBox()
		self.xrayModeCombo.addItems(["solid", "shell"])
		self.xrayScalarValueSpin = QDoubleSpinBox()
		self.xrayScalarValueSpin.setRange(-1e6, 1e6)
		self.xrayScalarValueSpin.setDecimals(3)
		self.xrayScalarValueSpin.setSingleStep(10.0)
		self.xrayShellThicknessSpin = QDoubleSpinBox()
		self.xrayShellThicknessSpin.setRange(0.001, 1e6)
		self.xrayShellThicknessSpin.setDecimals(3)
		self.xrayShellThicknessSpin.setSingleStep(0.1)
		self.xrayScalarScaleSpin = QDoubleSpinBox()
		self.xrayScalarScaleSpin.setRange(-1e3, 1e3)
		self.xrayScalarScaleSpin.setDecimals(6)
		self.xrayScalarScaleSpin.setSingleStep(0.05)
		self.xrayScalarBiasSpin = QDoubleSpinBox()
		self.xrayScalarBiasSpin.setRange(-1e6, 1e6)
		self.xrayScalarBiasSpin.setDecimals(3)
		self.xrayScalarBiasSpin.setSingleStep(10.0)
		self.xrayAttenuationSpin = QDoubleSpinBox()
		self.xrayAttenuationSpin.setRange(0.0, 1e6)
		self.xrayAttenuationSpin.setDecimals(6)
		self.xrayAttenuationSpin.setSingleStep(0.05)

		self.xrayLayout.addRow("", self.xrayEnabledCheck)
		self.xrayLayout.addRow("Mode:", self.xrayModeCombo)
		self.xrayLayout.addRow("Scalar value:", self.xrayScalarValueSpin)
		self.xrayLayout.addRow("Shell [mm]:", self.xrayShellThicknessSpin)
		self.xrayLayout.addRow("Scalar scale:", self.xrayScalarScaleSpin)
		self.xrayLayout.addRow("Scalar bias:", self.xrayScalarBiasSpin)
		self.xrayLayout.addRow("Attenuation x:", self.xrayAttenuationSpin)

		main_layout = getattr(self, "_main_layout", None)
		if isinstance(main_layout, QLayout):
			main_layout.addWidget(self.xrayGroup)

	def _connect_xray_signals(self):
		"""Connect X-ray tuning widgets to the underlying mesh object."""
		self.xrayEnabledCheck.toggled.connect(self.on_xray_changed)
		self.xrayModeCombo.currentTextChanged.connect(self.on_xray_changed)
		self.xrayScalarValueSpin.valueChanged.connect(self.on_xray_changed)
		self.xrayShellThicknessSpin.valueChanged.connect(self.on_xray_changed)
		self.xrayScalarScaleSpin.valueChanged.connect(self.on_xray_changed)
		self.xrayScalarBiasSpin.valueChanged.connect(self.on_xray_changed)
		self.xrayAttenuationSpin.valueChanged.connect(self.on_xray_changed)

	def _block_xray_signals(self, blocked):
		"""Block or unblock signals from the X-ray widgets during refresh."""
		for widget in (
			self.xrayEnabledCheck,
			self.xrayModeCombo,
			self.xrayScalarValueSpin,
			self.xrayShellThicknessSpin,
			self.xrayScalarScaleSpin,
			self.xrayScalarBiasSpin,
			self.xrayAttenuationSpin,
		):
			widget.blockSignals(blocked)

	def _update_xray_visibility(self, obj):
		"""Enable only controls relevant to the current X-ray mesh mode."""
		enabled = bool(obj.xray_source_enabled)
		is_shell = str(obj.xray_mesh_mode).lower() == "shell"
		self.xrayModeCombo.setEnabled(enabled)
		self.xrayScalarValueSpin.setEnabled(enabled)
		self.xrayShellThicknessSpin.setEnabled(enabled and is_shell)
		self.xrayScalarScaleSpin.setEnabled(enabled)
		self.xrayScalarBiasSpin.setEnabled(enabled)
		self.xrayAttenuationSpin.setEnabled(enabled)

	def updateProperties(self):
		"""Refresh the panel from the current mesh state."""
		obj = self.obj_ref()
		ensure_xray_source_config(obj)
		col = obj.materials[obj.currentMaterial].diffuse + [obj.materials[obj.currentMaterial].alpha]
		qc = QColor()
		qc.setRgbF(col[0], col[1], col[2], col[3])
		self.updateDefaultColorButton(qc)

		self._block_xray_signals(True)
		self.xrayEnabledCheck.setChecked(bool(obj.xray_source_enabled))
		self.xrayModeCombo.setCurrentText(str(obj.xray_mesh_mode))
		self.xrayScalarValueSpin.setValue(float(obj.xray_mesh_scalar_value))
		self.xrayShellThicknessSpin.setValue(float(obj.xray_mesh_shell_thickness_mm))
		self.xrayScalarScaleSpin.setValue(float(obj.xray_scalar_scale))
		self.xrayScalarBiasSpin.setValue(float(obj.xray_scalar_bias))
		self.xrayAttenuationSpin.setValue(float(obj.xray_attenuation_multiplier))
		self._update_xray_visibility(obj)
		self._block_xray_signals(False)

	def updateDefaultColorButton(self, col):
		"""Refresh the button preview for the mesh diffuse colour."""
		s = "background-color: rgb(" + str(col.red()) + ", " + str(col.green()) + ", " + str(col.blue()) + ");"
		self.bgColorButton.setStyleSheet(s)

	@pyqtSlot()
	def on_default_color_button(self):
		"""Open one colour picker and store the selected mesh material colour."""
		obj = self.obj_ref()
		col = obj.materials[obj.currentMaterial].diffuse + [obj.materials[obj.currentMaterial].alpha]
		qc = QColor()
		qc.setRgbF(col[0], col[1], col[2], col[3])
		color = QColorDialog.getColor(qc, self, "Select color", options=QColorDialog.ShowAlphaChannel | QColorDialog.DontUseNativeDialog)
		if color.isValid():
			obj.materials[obj.currentMaterial].diffuse = [color.redF(), color.greenF(), color.blueF()]
			obj.materials[obj.currentMaterial].alpha = color.alphaF()
			self.updateDefaultColorButton(color)
			AP.updateAllViews()

	@pyqtSlot()
	def on_xray_changed(self):
		"""Store the mesh-specific X-ray source settings directly on the selected object."""
		obj = self.obj_ref()
		ensure_xray_source_config(obj)
		obj.xray_source_enabled = bool(self.xrayEnabledCheck.isChecked())
		obj.xray_mesh_mode = str(self.xrayModeCombo.currentText()).lower()
		obj.xray_mesh_scalar_value = float(self.xrayScalarValueSpin.value())
		obj.xray_mesh_shell_thickness_mm = max(1e-4, float(self.xrayShellThicknessSpin.value()))
		obj.xray_scalar_scale = float(self.xrayScalarScaleSpin.value())
		obj.xray_scalar_bias = float(self.xrayScalarBiasSpin.value())
		obj.xray_attenuation_multiplier = max(0.0, float(self.xrayAttenuationSpin.value()))
		self._update_xray_visibility(obj)
		AP.updateProperties()
		AP.updateAllViews()
