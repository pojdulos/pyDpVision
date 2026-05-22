# -*- coding: utf-8 -*-
"""Property panel for the `VirtualXRay` scene object."""

from __future__ import annotations

import weakref

import numpy as np
from PyQt5.QtCore import Qt, QEventLoop, pyqtSlot
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import (
	QApplication,
	QCheckBox,
	QComboBox,
	QFormLayout,
	QGroupBox,
	QHBoxLayout,
	QLabel,
	QMessageBox,
		QProgressBar,
	QPushButton,
	QSpinBox,
	QTabWidget,
	QVBoxLayout,
	QWidget,
	QDoubleSpinBox,
)

from .. import AP, Image, VirtualXRay, normalize_projection_to_uint8
from .multiSpinBox import MultiSpinBox
from .propBaseObject import PropBaseObject
from .propWidget import PropWidget


class PropVirtualXRay(PropWidget):
	"""Edit basic source and detector parameters of one `VirtualXRay` scene node."""

	def __init__(self, _obj: VirtualXRay, parent=None):
		"""Build the property editor widgets and bind them to the provided scene object."""
		super().__init__(parent)
		self.obj_ref = weakref.ref(_obj)
		self._setup_ui()
		self._connect_signals()

	def _setup_ui(self):
		"""Create the full property form for detector, source and sampling parameters."""
		layout = QVBoxLayout(self)

		self.tabs = QTabWidget()
		layout.addWidget(self.tabs)

		self.sceneTab = QWidget()
		self.sceneTabLayout = QVBoxLayout(self.sceneTab)

		self.sceneGroup = QGroupBox("Scene")
		scene_layout = QFormLayout(self.sceneGroup)
		self.volumesLabel = QLabel("-")
		self.modeCombo = QComboBox()
		self.modeCombo.addItems(["cone", "parallel"])
		scene_layout.addRow("Volumes:", self.volumesLabel)
		scene_layout.addRow("Mode:", self.modeCombo)
		self.sceneTabLayout.addWidget(self.sceneGroup)
		self.sceneTabLayout.addStretch(1)
		self.tabs.addTab(self.sceneTab, "Scene")

		self.detectorTab = QWidget()
		self.detectorTabLayout = QVBoxLayout(self.detectorTab)

		self.detectorGroup = QGroupBox("Detector")
		detector_layout = QFormLayout(self.detectorGroup)
		self.detectorCenterSpin = MultiSpinBox(3, labels=("X", "Y", "Z"))
		self.detectorNormalSpin = MultiSpinBox(3, labels=("X", "Y", "Z"))
		self.detectorUpSpin = MultiSpinBox(3, labels=("X", "Y", "Z"))
		self.detectorPixelSizeSpin = MultiSpinBox(2, labels=("U", "V"))
		self.detectorShapeWidget = QWidget()
		detector_shape_layout = QHBoxLayout(self.detectorShapeWidget)
		detector_shape_layout.setContentsMargins(0, 0, 0, 0)
		self.detectorHeightSpin = QSpinBox()
		self.detectorWidthSpin = QSpinBox()
		for spin in (self.detectorHeightSpin, self.detectorWidthSpin):
			spin.setRange(1, 8192)
		detector_shape_layout.addWidget(QLabel("H"))
		detector_shape_layout.addWidget(self.detectorHeightSpin)
		detector_shape_layout.addWidget(QLabel("W"))
		detector_shape_layout.addWidget(self.detectorWidthSpin)
		detector_layout.addRow("Center [mm]:", self.detectorCenterSpin)
		detector_layout.addRow("Normal:", self.detectorNormalSpin)
		detector_layout.addRow("Up:", self.detectorUpSpin)
		detector_layout.addRow("Pixel size [mm]:", self.detectorPixelSizeSpin)
		detector_layout.addRow("Shape [px]:", self.detectorShapeWidget)
		self.detectorTabLayout.addWidget(self.detectorGroup)
		self.detectorTabLayout.addStretch(1)
		self.tabs.addTab(self.detectorTab, "Detector")

		self.sourceTab = QWidget()
		self.sourceTabLayout = QVBoxLayout(self.sourceTab)

		self.sourceGroup = QGroupBox("Source")
		source_layout = QFormLayout(self.sourceGroup)
		self.sourcePositionSpin = MultiSpinBox(3, labels=("X", "Y", "Z"))
		self.rayDirectionSpin = MultiSpinBox(3, labels=("X", "Y", "Z"))
		source_layout.addRow("Position [mm]:", self.sourcePositionSpin)
		source_layout.addRow("Direction:", self.rayDirectionSpin)
		self.sourceTabLayout.addWidget(self.sourceGroup)
		self.sourceTabLayout.addStretch(1)
		self.tabs.addTab(self.sourceTab, "Source")

		self.samplingTab = QWidget()
		self.samplingTabLayout = QVBoxLayout(self.samplingTab)

		self.samplingGroup = QGroupBox("Sampling")
		sampling_layout = QFormLayout(self.samplingGroup)
		self.stepSpin = QDoubleSpinBox()
		self.stepSpin.setRange(0.01, 50.0)
		self.stepSpin.setDecimals(3)
		self.stepSpin.setSingleStep(0.1)
		self.qualityCombo = QComboBox()
		self.qualityCombo.addItems(["draft", "normal", "high"])
		sampling_layout.addRow("Step [mm]:", self.stepSpin)
		sampling_layout.addRow("Quality:", self.qualityCombo)
		self.samplingTabLayout.addWidget(self.samplingGroup)
		self.samplingTabLayout.addStretch(1)
		self.tabs.addTab(self.samplingTab, "Sampling")

		self.physicsTab = QWidget()
		self.physicsTabLayout = QVBoxLayout(self.physicsTab)

		self.physicsGroup = QGroupBox("Physics")
		physics_layout = QFormLayout(self.physicsGroup)
		self.physicsMaterialWindowCenterSpin = QDoubleSpinBox()
		self.physicsMaterialWindowCenterSpin.setRange(-1e6, 1e6)
		self.physicsMaterialWindowCenterSpin.setDecimals(3)
		self.physicsMaterialWindowCenterSpin.setSingleStep(1.0)
		self.physicsMaterialWindowWidthSpin = QDoubleSpinBox()
		self.physicsMaterialWindowWidthSpin.setRange(0.0, 1e6)
		self.physicsMaterialWindowWidthSpin.setDecimals(3)
		self.physicsMaterialWindowWidthSpin.setSingleStep(1.0)
		self.physicsMaterialWindowModeCombo = QComboBox()
		self.physicsMaterialWindowModeCombo.addItems(["hard", "linear", "sigmoid"])
		self.physicsMaterialWindowSoftnessSpin = QDoubleSpinBox()
		self.physicsMaterialWindowSoftnessSpin.setRange(0.0, 1e6)
		self.physicsMaterialWindowSoftnessSpin.setDecimals(3)
		self.physicsMaterialWindowSoftnessSpin.setSingleStep(1.0)
		physics_layout.addRow("Material center [HU]:", self.physicsMaterialWindowCenterSpin)
		physics_layout.addRow("Material width [HU]:", self.physicsMaterialWindowWidthSpin)
		physics_layout.addRow("Window mode:", self.physicsMaterialWindowModeCombo)
		physics_layout.addRow("Softness [HU]:", self.physicsMaterialWindowSoftnessSpin)
		self.physicsTabLayout.addWidget(self.physicsGroup)
		self.physicsTabLayout.addStretch(1)
		self.tabs.addTab(self.physicsTab, "Physics")

		self.presentationTab = QWidget()
		self.presentationTabLayout = QVBoxLayout(self.presentationTab)

		self.presentationGroup = QGroupBox("Presentation")
		presentation_layout = QFormLayout(self.presentationGroup)
		self.presentationModeCombo = QComboBox()
		self.presentationModeCombo.addItems(["digital", "film", "raw"])
		self.presentationInvertCheck = QCheckBox("Invert")
		self.presentationGammaSpin = QDoubleSpinBox()
		self.presentationGammaSpin.setRange(0.05, 10.0)
		self.presentationGammaSpin.setDecimals(3)
		self.presentationGammaSpin.setSingleStep(0.05)
		self.presentationContrastSpin = QDoubleSpinBox()
		self.presentationContrastSpin.setRange(0.05, 10.0)
		self.presentationContrastSpin.setDecimals(3)
		self.presentationContrastSpin.setSingleStep(0.05)
		self.presentationPercentileSpin = QDoubleSpinBox()
		self.presentationPercentileSpin.setRange(50.0, 100.0)
		self.presentationPercentileSpin.setDecimals(2)
		self.presentationPercentileSpin.setSingleStep(0.1)
		self.presentationWindowCenterSpin = QDoubleSpinBox()
		self.presentationWindowCenterSpin.setRange(-1e6, 1e6)
		self.presentationWindowCenterSpin.setDecimals(3)
		self.presentationWindowCenterSpin.setSingleStep(0.1)
		self.presentationWindowWidthSpin = QDoubleSpinBox()
		self.presentationWindowWidthSpin.setRange(0.0, 1e6)
		self.presentationWindowWidthSpin.setDecimals(3)
		self.presentationWindowWidthSpin.setSingleStep(0.1)
		presentation_layout.addRow("Mode:", self.presentationModeCombo)
		presentation_layout.addRow("", self.presentationInvertCheck)
		presentation_layout.addRow("Gamma:", self.presentationGammaSpin)
		presentation_layout.addRow("Contrast:", self.presentationContrastSpin)
		presentation_layout.addRow("Robust [%]:", self.presentationPercentileSpin)
		presentation_layout.addRow("Window center:", self.presentationWindowCenterSpin)
		presentation_layout.addRow("Window width:", self.presentationWindowWidthSpin)
		self.presentationTabLayout.addWidget(self.presentationGroup)
		self.presentationTabLayout.addStretch(1)
		self.tabs.addTab(self.presentationTab, "Presentation")

		self.advancedTab = QWidget()
		self.advancedTabLayout = QVBoxLayout(self.advancedTab)

		self.advancedPhysicsGroup = QGroupBox("Advanced Physics")
		advanced_physics_layout = QFormLayout(self.advancedPhysicsGroup)
		self.physicsMuAirSpin = QDoubleSpinBox()
		self.physicsMuAirSpin.setRange(-1e6, 1e6)
		self.physicsMuAirSpin.setDecimals(6)
		self.physicsMuAirSpin.setSingleStep(0.001)
		self.physicsMuWaterSpin = QDoubleSpinBox()
		self.physicsMuWaterSpin.setRange(-1e6, 1e6)
		self.physicsMuWaterSpin.setDecimals(6)
		self.physicsMuWaterSpin.setSingleStep(0.001)
		self.physicsHounsfieldAirSpin = QDoubleSpinBox()
		self.physicsHounsfieldAirSpin.setRange(-1e6, 1e6)
		self.physicsHounsfieldAirSpin.setDecimals(3)
		self.physicsHounsfieldAirSpin.setSingleStep(1.0)
		self.physicsAttenuationScaleSpin = QDoubleSpinBox()
		self.physicsAttenuationScaleSpin.setRange(0.0, 1e6)
		self.physicsAttenuationScaleSpin.setDecimals(6)
		self.physicsAttenuationScaleSpin.setSingleStep(0.01)
		self.physicsOutputModeCombo = QComboBox()
		self.physicsOutputModeCombo.addItems(["integral", "intensity"])
		self.physicsIntensityFloorSpin = QDoubleSpinBox()
		self.physicsIntensityFloorSpin.setRange(0.0, 1e6)
		self.physicsIntensityFloorSpin.setDecimals(6)
		self.physicsIntensityFloorSpin.setSingleStep(0.001)
		advanced_physics_layout.addRow("mu_air:", self.physicsMuAirSpin)
		advanced_physics_layout.addRow("mu_water:", self.physicsMuWaterSpin)
		advanced_physics_layout.addRow("hounsfield_air:", self.physicsHounsfieldAirSpin)
		advanced_physics_layout.addRow("attenuation_scale:", self.physicsAttenuationScaleSpin)
		advanced_physics_layout.addRow("output_mode:", self.physicsOutputModeCombo)
		advanced_physics_layout.addRow("intensity_floor:", self.physicsIntensityFloorSpin)
		self.advancedTabLayout.addWidget(self.advancedPhysicsGroup)

		self.advancedSourceGroup = QGroupBox("Advanced Source")
		advanced_source_layout = QFormLayout(self.advancedSourceGroup)
		self.sourceInterpolationCombo = QComboBox()
		self.sourceInterpolationCombo.addItems(["nearest", "linear", "cubic"])
		self.sourceUseFillValueCheck = QCheckBox("Use explicit fill value")
		self.sourceFillValueSpin = QDoubleSpinBox()
		self.sourceFillValueSpin.setRange(-1e9, 1e9)
		self.sourceFillValueSpin.setDecimals(3)
		self.sourceFillValueSpin.setSingleStep(1.0)
		advanced_source_layout.addRow("interpolation:", self.sourceInterpolationCombo)
		advanced_source_layout.addRow("", self.sourceUseFillValueCheck)
		advanced_source_layout.addRow("fill_value:", self.sourceFillValueSpin)
		self.advancedTabLayout.addWidget(self.advancedSourceGroup)
		self.advancedTabLayout.addStretch(1)
		self.tabs.addTab(self.advancedTab, "Advanced")

		self.runTab = QWidget()
		self.runTabLayout = QVBoxLayout(self.runTab)

		self.actionsWidget = QWidget()
		actions_layout = QHBoxLayout(self.actionsWidget)
		actions_layout.setContentsMargins(0, 0, 0, 0)
		self.refreshButton = QPushButton("Refresh")
		self.runSimulationButton = QPushButton("Run Simulation")
		self.updateDisplayButton = QPushButton("Update display")
		self.updateDisplayButton.setEnabled(False)
		self.renderInfoLabel = QLabel("")
		actions_layout.addWidget(self.refreshButton)
		actions_layout.addWidget(self.runSimulationButton)
		actions_layout.addWidget(self.updateDisplayButton)
		self.runTabLayout.addWidget(self.actionsWidget)
		self.progressBar = QProgressBar()
		self.progressBar.setRange(0, 100)
		self.progressBar.setValue(0)
		self.progressBar.setVisible(False)
		self.runTabLayout.addWidget(self.progressBar)
		self.runTabLayout.addWidget(self.renderInfoLabel)
		self.runTabLayout.addStretch(1)
		self.tabs.addTab(self.runTab, "Run")

		layout.addStretch(1)

	def _connect_signals(self):
		"""Connect all editor widgets to their slots."""
		self.modeCombo.currentTextChanged.connect(self.on_mode_changed)
		self.detectorCenterSpin.valueChanged.connect(self.on_detector_center_changed)
		self.detectorNormalSpin.valueChanged.connect(self.on_detector_normal_changed)
		self.detectorUpSpin.valueChanged.connect(self.on_detector_up_changed)
		self.detectorPixelSizeSpin.valueChanged.connect(self.on_detector_pixel_size_changed)
		self.detectorHeightSpin.valueChanged.connect(self.on_detector_shape_changed)
		self.detectorWidthSpin.valueChanged.connect(self.on_detector_shape_changed)
		self.sourcePositionSpin.valueChanged.connect(self.on_source_position_changed)
		self.rayDirectionSpin.valueChanged.connect(self.on_ray_direction_changed)
		self.stepSpin.valueChanged.connect(self.on_step_changed)
		self.qualityCombo.currentTextChanged.connect(self.on_quality_changed)
		self.physicsMaterialWindowCenterSpin.valueChanged.connect(self.on_physics_material_window_changed)
		self.physicsMaterialWindowWidthSpin.valueChanged.connect(self.on_physics_material_window_changed)
		self.physicsMaterialWindowModeCombo.currentTextChanged.connect(self.on_physics_material_window_mode_changed)
		self.physicsMaterialWindowSoftnessSpin.valueChanged.connect(self.on_physics_material_window_softness_changed)
		self.presentationModeCombo.currentTextChanged.connect(self.on_presentation_mode_changed)
		self.presentationInvertCheck.toggled.connect(self.on_presentation_invert_changed)
		self.presentationGammaSpin.valueChanged.connect(self.on_presentation_gamma_changed)
		self.presentationContrastSpin.valueChanged.connect(self.on_presentation_contrast_changed)
		self.presentationPercentileSpin.valueChanged.connect(self.on_presentation_percentile_changed)
		self.presentationWindowCenterSpin.valueChanged.connect(self.on_presentation_window_changed)
		self.presentationWindowWidthSpin.valueChanged.connect(self.on_presentation_window_changed)
		self.physicsMuAirSpin.valueChanged.connect(self.on_advanced_physics_changed)
		self.physicsMuWaterSpin.valueChanged.connect(self.on_advanced_physics_changed)
		self.physicsHounsfieldAirSpin.valueChanged.connect(self.on_advanced_physics_changed)
		self.physicsAttenuationScaleSpin.valueChanged.connect(self.on_advanced_physics_changed)
		self.physicsOutputModeCombo.currentTextChanged.connect(self.on_advanced_physics_changed)
		self.physicsIntensityFloorSpin.valueChanged.connect(self.on_advanced_physics_changed)
		self.sourceInterpolationCombo.currentTextChanged.connect(self.on_advanced_source_changed)
		self.sourceUseFillValueCheck.toggled.connect(self.on_advanced_source_changed)
		self.sourceFillValueSpin.valueChanged.connect(self.on_advanced_source_changed)
		self.refreshButton.clicked.connect(self.on_refresh_requested)
		self.runSimulationButton.clicked.connect(self.on_run_simulation)
		self.updateDisplayButton.clicked.connect(self.on_update_display)

	@staticmethod
	def create(m, parent=0):
		"""Build the combined base-object and VirtualXRay property panel."""
		return PropWidget.build([PropVirtualXRay(m), PropBaseObject(m)], parent)

	def blockAll(self, b):
		"""Block or unblock signals for all editable widgets in this panel."""
		for widget in (
			self.modeCombo,
			self.detectorCenterSpin,
			self.detectorNormalSpin,
			self.detectorUpSpin,
			self.detectorPixelSizeSpin,
			self.detectorHeightSpin,
			self.detectorWidthSpin,
			self.sourcePositionSpin,
			self.rayDirectionSpin,
			self.stepSpin,
			self.qualityCombo,
			self.physicsMaterialWindowCenterSpin,
			self.physicsMaterialWindowWidthSpin,
			self.physicsMaterialWindowModeCombo,
			self.physicsMaterialWindowSoftnessSpin,
			self.presentationModeCombo,
			self.presentationInvertCheck,
			self.presentationGammaSpin,
			self.presentationContrastSpin,
			self.presentationPercentileSpin,
			self.presentationWindowCenterSpin,
			self.presentationWindowWidthSpin,
			self.physicsMuAirSpin,
			self.physicsMuWaterSpin,
			self.physicsHounsfieldAirSpin,
			self.physicsAttenuationScaleSpin,
			self.physicsOutputModeCombo,
			self.physicsIntensityFloorSpin,
			self.sourceInterpolationCombo,
			self.sourceUseFillValueCheck,
			self.sourceFillValueSpin,
		):
			widget.blockSignals(b)

	def _update_mode_visibility(self, obj: VirtualXRay):
		"""Enable either the point-source editor or the parallel-ray editor based on the current mode."""
		is_cone = str(obj.projection_mode).lower() == "cone"
		self.sourcePositionSpin.setEnabled(is_cone)
		self.rayDirectionSpin.setEnabled(not is_cone)

	def _update_presentation_visibility(self, obj: VirtualXRay):
		"""Enable only presentation controls relevant to the selected display mode."""
		mode = str(obj.presentation_mode).lower()
		is_raw = mode == "raw"
		is_digital = mode == "digital"
		self.presentationInvertCheck.setEnabled(not is_raw)
		self.presentationGammaSpin.setEnabled(not is_raw)
		self.presentationContrastSpin.setEnabled(not is_raw)
		self.presentationPercentileSpin.setEnabled(not is_raw)
		self.presentationWindowCenterSpin.setEnabled(is_digital)
		self.presentationWindowWidthSpin.setEnabled(is_digital)

	def _update_physics_visibility(self, obj: VirtualXRay):
		"""Enable only physics controls relevant to the selected material window mode."""
		width_enabled = obj.physics_material_window_width is not None and float(obj.physics_material_window_width) > 0.0
		mode = str(obj.physics_material_window_mode).lower()
		self.physicsMaterialWindowModeCombo.setEnabled(width_enabled)
		self.physicsMaterialWindowSoftnessSpin.setEnabled(width_enabled and mode in {"linear", "sigmoid"})
		self.physicsIntensityFloorSpin.setEnabled(str(obj.physics_output_mode).lower() == "intensity")

	def _update_advanced_source_visibility(self, obj: VirtualXRay):
		"""Enable explicit source fill value only when that override is active."""
		self.sourceFillValueSpin.setEnabled(obj.source_fill_value is not None)

	def updateProperties(self):
		"""Synchronize widget values with the current state of the bound VirtualXRay object."""
		obj = self.obj_ref()
		if obj is None:
			return
		self.blockAll(True)
		self.modeCombo.setCurrentText(str(obj.projection_mode))
		self.detectorCenterSpin.setValue(obj.detector_center_ref)
		self.detectorNormalSpin.setValue(obj.detector_normal_ref)
		self.detectorUpSpin.setValue(obj.detector_up_ref)
		self.detectorPixelSizeSpin.setValue(obj.detector_pixel_size_mm)
		self.detectorHeightSpin.setValue(int(obj.detector_shape_hw[0]))
		self.detectorWidthSpin.setValue(int(obj.detector_shape_hw[1]))
		self.sourcePositionSpin.setValue(obj.source_position_ref)
		self.rayDirectionSpin.setValue(obj.ray_direction_ref)
		self.stepSpin.setValue(float(obj.step_mm))
		self.qualityCombo.setCurrentText(str(obj.quality_profile_name))
		self.physicsMaterialWindowCenterSpin.setValue(0.0 if obj.physics_material_window_center is None else float(obj.physics_material_window_center))
		self.physicsMaterialWindowWidthSpin.setValue(0.0 if obj.physics_material_window_width is None else float(obj.physics_material_window_width))
		self.physicsMaterialWindowModeCombo.setCurrentText(str(obj.physics_material_window_mode))
		self.physicsMaterialWindowSoftnessSpin.setValue(float(obj.physics_material_window_softness))
		self.presentationModeCombo.setCurrentText(str(obj.presentation_mode))
		self.presentationInvertCheck.setChecked(bool(obj.presentation_invert))
		self.presentationGammaSpin.setValue(float(obj.presentation_gamma))
		self.presentationContrastSpin.setValue(float(obj.presentation_contrast))
		self.presentationPercentileSpin.setValue(float(obj.presentation_robust_percentile))
		self.presentationWindowCenterSpin.setValue(0.0 if obj.presentation_window_center is None else float(obj.presentation_window_center))
		self.presentationWindowWidthSpin.setValue(0.0 if obj.presentation_window_width is None else float(obj.presentation_window_width))
		self.physicsMuAirSpin.setValue(float(obj.physics_mu_air))
		self.physicsMuWaterSpin.setValue(float(obj.physics_mu_water))
		self.physicsHounsfieldAirSpin.setValue(float(obj.physics_hounsfield_air))
		self.physicsAttenuationScaleSpin.setValue(float(obj.physics_attenuation_scale))
		self.physicsOutputModeCombo.setCurrentText(str(obj.physics_output_mode))
		self.physicsIntensityFloorSpin.setValue(float(obj.physics_intensity_floor))
		self.sourceInterpolationCombo.setCurrentText(str(obj.source_interpolation))
		self.sourceUseFillValueCheck.setChecked(obj.source_fill_value is not None)
		self.sourceFillValueSpin.setValue(0.0 if obj.source_fill_value is None else float(obj.source_fill_value))
		self.volumesLabel.setText(str(len(obj.collect_volumetrics())))
		self.renderInfoLabel.setText(obj.info())
		self.updateDisplayButton.setEnabled(obj.last_raw_projection is not None)
		self._update_mode_visibility(obj)
		self._update_physics_visibility(obj)
		self._update_advanced_source_visibility(obj)
		self._update_presentation_visibility(obj)
		self.blockAll(False)

	def _after_change(self, obj: VirtualXRay):
		"""Refresh dependent state after changing one property."""
		obj.invalidate_bb()
		self.updateProperties()
		AP.mainWin.dock["workspace"].refreshAll()
		AP.updateAllViews()

	@pyqtSlot(str)
	def on_mode_changed(self, mode):
		"""Switch between cone-beam and parallel-beam geometry editing."""
		obj = self.obj_ref()
		if obj is None:
			return
		obj.projection_mode = str(mode).lower()
		self._after_change(obj)

	@pyqtSlot(tuple)
	def on_detector_center_changed(self, values):
		"""Store the detector center in the local X-ray reference frame."""
		obj = self.obj_ref()
		obj.detector_center_ref = np.asarray(values, dtype=np.float32)
		self._after_change(obj)

	@pyqtSlot(tuple)
	def on_detector_normal_changed(self, values):
		"""Store the detector normal vector in the local X-ray reference frame."""
		obj = self.obj_ref()
		obj.detector_normal_ref = np.asarray(values, dtype=np.float32)
		self._after_change(obj)

	@pyqtSlot(tuple)
	def on_detector_up_changed(self, values):
		"""Store the detector up vector in the local X-ray reference frame."""
		obj = self.obj_ref()
		obj.detector_up_ref = np.asarray(values, dtype=np.float32)
		self._after_change(obj)

	@pyqtSlot(tuple)
	def on_detector_pixel_size_changed(self, values):
		"""Store detector pixel pitch along the local detector axes."""
		obj = self.obj_ref()
		obj.detector_pixel_size_mm = [max(1e-4, float(values[0])), max(1e-4, float(values[1]))]
		self._after_change(obj)

	@pyqtSlot(int)
	def on_detector_shape_changed(self, _value):
		"""Store detector raster size in pixels."""
		obj = self.obj_ref()
		obj.detector_shape_hw = [int(self.detectorHeightSpin.value()), int(self.detectorWidthSpin.value())]
		self._after_change(obj)

	@pyqtSlot(tuple)
	def on_source_position_changed(self, values):
		"""Store point-source position in the local X-ray reference frame."""
		obj = self.obj_ref()
		obj.source_position_ref = np.asarray(values, dtype=np.float32)
		self._after_change(obj)

	@pyqtSlot(tuple)
	def on_ray_direction_changed(self, values):
		"""Store parallel-ray direction in the local X-ray reference frame."""
		obj = self.obj_ref()
		obj.ray_direction_ref = np.asarray(values, dtype=np.float32)
		self._after_change(obj)

	@pyqtSlot(float)
	def on_step_changed(self, value):
		"""Store the ray-marching integration step in millimeters."""
		obj = self.obj_ref()
		obj.step_mm = max(0.01, float(value))
		self._after_change(obj)

	@pyqtSlot(str)
	def on_quality_changed(self, value):
		"""Store the currently selected quality preset name."""
		obj = self.obj_ref()
		obj.quality_profile_name = str(value)
		self._after_change(obj)

	@pyqtSlot()
	def on_physics_material_window_changed(self):
		"""Store an optional HU window applied before attenuation integration."""
		obj = self.obj_ref()
		center = float(self.physicsMaterialWindowCenterSpin.value())
		width = float(self.physicsMaterialWindowWidthSpin.value())
		obj.physics_material_window_center = center if width > 0.0 else None
		obj.physics_material_window_width = width if width > 0.0 else None
		self._after_change(obj)

	@pyqtSlot(str)
	def on_physics_material_window_mode_changed(self, value):
		"""Store the material-window weighting mode used before attenuation integration."""
		obj = self.obj_ref()
		obj.physics_material_window_mode = str(value)
		self._after_change(obj)

	@pyqtSlot(float)
	def on_physics_material_window_softness_changed(self, value):
		"""Store the transition softness used by non-binary material window modes."""
		obj = self.obj_ref()
		obj.physics_material_window_softness = max(0.0, float(value))
		self._after_change(obj)

	@pyqtSlot(str)
	def on_presentation_mode_changed(self, value):
		"""Store the currently selected presentation mode."""
		obj = self.obj_ref()
		obj.presentation_mode = str(value)
		self._after_change(obj)

	@pyqtSlot(bool)
	def on_presentation_invert_changed(self, value):
		"""Store the inversion state of the presentation model."""
		obj = self.obj_ref()
		obj.presentation_invert = bool(value)
		self._after_change(obj)

	@pyqtSlot(float)
	def on_presentation_gamma_changed(self, value):
		"""Store the gamma applied by the presentation model."""
		obj = self.obj_ref()
		obj.presentation_gamma = max(0.05, float(value))
		self._after_change(obj)

	@pyqtSlot(float)
	def on_presentation_contrast_changed(self, value):
		"""Store the contrast applied by the presentation model."""
		obj = self.obj_ref()
		obj.presentation_contrast = max(0.05, float(value))
		self._after_change(obj)

	@pyqtSlot(float)
	def on_presentation_percentile_changed(self, value):
		"""Store the robust percentile used by film-like and digital presentation."""
		obj = self.obj_ref()
		obj.presentation_robust_percentile = min(100.0, max(50.0, float(value)))
		self._after_change(obj)

	@pyqtSlot()
	def on_presentation_window_changed(self):
		"""Store optional digital-radiography window center and width."""
		obj = self.obj_ref()
		center = float(self.presentationWindowCenterSpin.value())
		width = float(self.presentationWindowWidthSpin.value())
		obj.presentation_window_center = center if width > 0.0 else None
		obj.presentation_window_width = width if width > 0.0 else None
		self._after_change(obj)

	@pyqtSlot()
	def on_refresh_requested(self):
		"""Refresh the volume count and textual scene summary."""
		obj = self.obj_ref()
		self.renderInfoLabel.setText(obj.info())
		self.volumesLabel.setText(str(len(obj.collect_volumetrics())))

	@pyqtSlot()
	def on_advanced_physics_changed(self):
		"""Store lower-level physics parameters exposed for quick backend testing."""
		obj = self.obj_ref()
		obj.physics_mu_air = float(self.physicsMuAirSpin.value())
		obj.physics_mu_water = float(self.physicsMuWaterSpin.value())
		obj.physics_hounsfield_air = float(self.physicsHounsfieldAirSpin.value())
		obj.physics_attenuation_scale = float(self.physicsAttenuationScaleSpin.value())
		obj.physics_output_mode = str(self.physicsOutputModeCombo.currentText())
		obj.physics_intensity_floor = float(self.physicsIntensityFloorSpin.value())
		self._after_change(obj)

	@pyqtSlot()
	def on_advanced_source_changed(self):
		"""Store lower-level source sampling parameters exposed for quick backend testing."""
		obj = self.obj_ref()
		obj.source_interpolation = str(self.sourceInterpolationCombo.currentText())
		obj.source_fill_value = float(self.sourceFillValueSpin.value()) if self.sourceUseFillValueCheck.isChecked() else None
		self._after_change(obj)

	@pyqtSlot()
	def _display_image_array(self, obj, display_image):
		"""Convert a float display image to uint8, wrap in QImage and add to workspace."""
		mode = str(obj.presentation_mode).lower()
		if mode == "raw":
			image_u8 = normalize_projection_to_uint8(
				display_image,
				robust_percentile=float(obj.presentation_robust_percentile),
				invert=False,
			)
		else:
			image_u8 = normalize_projection_to_uint8(
				display_image,
				fixed_range=(0.0, 1.0),
				invert=False,
			)
		height, width = image_u8.shape
		qimage = QImage(
			image_u8.data,
			width,
			height,
			image_u8.strides[0],
			QImage.Format_Grayscale8,
		).copy()
		image_obj = Image(image=qimage)
		image_obj.label = f"{obj.label}_projection"
		AP.addObject(image_obj)

	def on_run_simulation(self):
		"""Run one X-ray projection, cache the raw result and insert the display image into the workspace."""
		obj = self.obj_ref()
		if obj is None:
			return

		self.progressBar.setValue(0)
		self.progressBar.setVisible(True)
		self.runSimulationButton.setEnabled(False)

		# Zamroź viewery GL przed processEvents — renderowanie Image przez glTexImage2D
		# poza normalnym cyklem paintGL powoduje crash przy drugiej symulacji.
		gl_viewers = AP.mainWin.allGLViewers()
		for v in gl_viewers:
			v.setUpdatesEnabled(False)

		QApplication.processEvents()  # odmaluj pasek przed startem blokującego obliczenia

		def _on_progress(fraction):
			self.progressBar.setValue(int(fraction * 100))
			QApplication.processEvents(QEventLoop.ExcludeUserInputEvents)

		QApplication.setOverrideCursor(Qt.WaitCursor)
		try:
			try:
				_, stats = obj.project_and_cache(return_stats=True, progress_callback=_on_progress)
				display_image = obj.apply_presentation()
			except Exception as exc:
				QMessageBox.critical(self, "Simulation error", str(exc))
				return
			self._display_image_array(obj, display_image)
			self.updateDisplayButton.setEnabled(True)
			self.renderInfoLabel.setText(
				f"{stats.elapsed_seconds:.2f}s, traced={stats.traced_pixels}, avgS={stats.average_samples_per_traced_pixel:.1f}"
			)
		finally:
			QApplication.restoreOverrideCursor()
			for v in gl_viewers:
				v.setUpdatesEnabled(True)
			AP.updateAllViews()
			self.progressBar.setVisible(False)
			self.runSimulationButton.setEnabled(True)

	def on_update_display(self):
		"""Re-apply the current presentation model to the cached raw projection without re-projecting."""
		obj = self.obj_ref()
		if obj is None:
			return
		display_image = obj.apply_presentation()
		if display_image is None:
			return
		self._display_image_array(obj, display_image)
