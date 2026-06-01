# -*- coding: utf-8 -*-
"""Tri-planar volumetric preview with synchronized crosshair navigation."""

from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
	QApplication,
	QCheckBox,
	QComboBox,
	QDialog,
	QDoubleSpinBox,
	QGridLayout,
	QGroupBox,
	QHBoxLayout,
	QLabel,
	QPushButton,
	QScrollArea,
	QSlider,
	QSpinBox,
	QVBoxLayout,
	QWidget,
)


class SliceViewLabel(QLabel):
	"""Display one slice preview and emit image-space click coordinates."""

	planeClicked = pyqtSignal(str, int, int)

	def __init__(self, plane, parent=None):
		super(SliceViewLabel, self).__init__(parent)
		self.plane = plane
		self.source_width = 0
		self.source_height = 0
		self.setAlignment(Qt.AlignCenter)
		self.setMouseTracking(True)

	def set_source_size(self, width, height):
		"""Store the original image size for click-to-voxel mapping."""
		self.source_width = int(width)
		self.source_height = int(height)

	def mousePressEvent(self, event):
		"""Translate a click on the scaled pixmap into image coordinates."""
		if event.button() != Qt.LeftButton:
			super(SliceViewLabel, self).mousePressEvent(event)
			return

		if self.source_width <= 0 or self.source_height <= 0:
			return

		label_width = max(1, self.width())
		label_height = max(1, self.height())
		x_ratio = min(max(event.x() / label_width, 0.0), 0.999999)
		y_ratio = min(max(event.y() / label_height, 0.0), 0.999999)

		image_x = min(int(x_ratio * self.source_width), self.source_width - 1)
		image_y = min(int(y_ratio * self.source_height), self.source_height - 1)
		self.planeClicked.emit(self.plane, image_x, image_y)


class DialogVolumetricPreview(QDialog):
	"""Display synchronized XY, YZ and ZX views of a volumetric object."""

	def __init__(self, volumetric, parent=None):
		super(DialogVolumetricPreview, self).__init__(parent)
		self.volumetric = volumetric
		self._images_by_plane = {}
		self._view_widgets = {}
		self._axis_controls = {}
		self._view_positions = {}

		self.setAttribute(Qt.WA_DeleteOnClose, True)
		self.setWindowTitle(f"Volumetric Preview: {getattr(volumetric, 'label', 'Volumetric')}")
		self.resize(1400, 950)

		self._build_ui()
		self._sync_window_controls()
		self._sync_axis_ranges(reset_to_center=True)
		self._update_layout_mode()
		self.refresh_previews()

	def _build_ui(self):
		"""Create controls, axis widgets and three synchronized view panels."""
		main_layout = QVBoxLayout(self)

		toolbar_layout = QGridLayout()
		main_layout.addLayout(toolbar_layout)

		self.rtg_check = QCheckBox("RTG all")
		self.rtg_check.toggled.connect(self.on_rtg_all_toggled)
		toolbar_layout.addWidget(self.rtg_check, 0, 0)

		self.rtg_mode_combo = QComboBox()
		self.rtg_mode_combo.addItems(["mean", "sum", "max", "xray"])
		self.rtg_mode_combo.setCurrentText("xray")
		self.rtg_mode_combo.currentTextChanged.connect(self.refresh_previews)
		toolbar_layout.addWidget(QLabel("RTG mode"), 0, 1)
		toolbar_layout.addWidget(self.rtg_mode_combo, 0, 2)

		self.xray_gain_spin = QDoubleSpinBox()
		self.xray_gain_spin.setRange(0.001, 5.0)
		self.xray_gain_spin.setDecimals(3)
		self.xray_gain_spin.setSingleStep(0.01)
		self.xray_gain_spin.setValue(0.25)
		self.xray_gain_spin.valueChanged.connect(self.refresh_previews)
		toolbar_layout.addWidget(QLabel("Xray gain"), 0, 3)
		toolbar_layout.addWidget(self.xray_gain_spin, 0, 4)

		self.xray_gamma_spin = QDoubleSpinBox()
		self.xray_gamma_spin.setRange(0.2, 4.0)
		self.xray_gamma_spin.setDecimals(2)
		self.xray_gamma_spin.setSingleStep(0.1)
		self.xray_gamma_spin.setValue(1.4)
		self.xray_gamma_spin.valueChanged.connect(self.refresh_previews)
		toolbar_layout.addWidget(QLabel("Xray gamma"), 0, 5)
		toolbar_layout.addWidget(self.xray_gamma_spin, 0, 6)

		self.displ_window_check = QCheckBox("Display window")
		self.displ_window_check.setChecked(True)
		self.displ_window_check.toggled.connect(self.refresh_previews)
		toolbar_layout.addWidget(self.displ_window_check, 0, 7, 1, 2)

		self.invert_check = QCheckBox("Invert")
		self.invert_check.toggled.connect(self.refresh_previews)
		toolbar_layout.addWidget(self.invert_check, 0, 9)

		self.fit_check = QCheckBox("Fit to panels")
		self.fit_check.setChecked(True)
		self.fit_check.toggled.connect(self.refresh_previews)
		toolbar_layout.addWidget(self.fit_check, 0, 10, 1, 2)

		self.zoom_spin = QDoubleSpinBox()
		self.zoom_spin.setRange(0.1, 8.0)
		self.zoom_spin.setSingleStep(0.1)
		self.zoom_spin.setValue(1.0)
		self.zoom_spin.valueChanged.connect(self.refresh_previews)
		toolbar_layout.addWidget(QLabel("Zoom"), 0, 12)
		toolbar_layout.addWidget(self.zoom_spin, 0, 13)

		reset_button = QPushButton("Reset center")
		reset_button.clicked.connect(self.on_reset_center_clicked)
		toolbar_layout.addWidget(reset_button, 0, 14)

		self.win_min_spin = QDoubleSpinBox()
		self.win_min_spin.setDecimals(3)
		self.win_min_spin.valueChanged.connect(self.on_window_min_changed)
		toolbar_layout.addWidget(QLabel("Win min"), 1, 0)
		toolbar_layout.addWidget(self.win_min_spin, 1, 1)

		self.win_max_spin = QDoubleSpinBox()
		self.win_max_spin.setDecimals(3)
		self.win_max_spin.valueChanged.connect(self.on_window_max_changed)
		toolbar_layout.addWidget(QLabel("Win max"), 1, 2)
		toolbar_layout.addWidget(self.win_max_spin, 1, 3)

		self.slab_thickness_spin = QDoubleSpinBox()
		self.slab_thickness_spin.setRange(0.0, 500.0)
		self.slab_thickness_spin.setDecimals(3)
		self.slab_thickness_spin.setSingleStep(0.5)
		self.slab_thickness_spin.setValue(0.0)
		self.slab_thickness_spin.valueChanged.connect(self.refresh_previews)
		toolbar_layout.addWidget(QLabel("Slab mm"), 1, 4)
		toolbar_layout.addWidget(self.slab_thickness_spin, 1, 5)

		self.slab_samples_spin = QSpinBox()
		self.slab_samples_spin.setRange(1, 256)
		self.slab_samples_spin.setValue(1)
		self.slab_samples_spin.valueChanged.connect(self.refresh_previews)
		toolbar_layout.addWidget(QLabel("Samples"), 1, 6)
		toolbar_layout.addWidget(self.slab_samples_spin, 1, 7)

		self.slab_mode_combo = QComboBox()
		self.slab_mode_combo.addItems(["center", "mean", "max", "min"])
		self.slab_mode_combo.setCurrentText("center")
		self.slab_mode_combo.currentTextChanged.connect(self.refresh_previews)
		toolbar_layout.addWidget(QLabel("Slab mode"), 1, 8)
		toolbar_layout.addWidget(self.slab_mode_combo, 1, 9)

		self.position_label = QLabel("")
		toolbar_layout.addWidget(self.position_label, 3, 0, 1, 13)

		self.oblique_yaw_spin = QDoubleSpinBox()
		self.oblique_yaw_spin.setRange(-180.0, 180.0)
		self.oblique_yaw_spin.setSingleStep(1.0)
		self.oblique_yaw_spin.setValue(0.0)
		self.oblique_yaw_spin.valueChanged.connect(self.refresh_previews)
		toolbar_layout.addWidget(QLabel("Yaw"), 2, 0)
		toolbar_layout.addWidget(self.oblique_yaw_spin, 2, 1)
		self.oblique_yaw_axis_combo = QComboBox()
		self.oblique_yaw_axis_combo.addItems(["X", "Y", "Z"])
		self.oblique_yaw_axis_combo.setCurrentText("Y")
		self.oblique_yaw_axis_combo.currentTextChanged.connect(self.refresh_previews)
		toolbar_layout.addWidget(QLabel("Yaw axis"), 2, 2)
		toolbar_layout.addWidget(self.oblique_yaw_axis_combo, 2, 3)

		self.oblique_pitch_spin = QDoubleSpinBox()
		self.oblique_pitch_spin.setRange(-89.0, 89.0)
		self.oblique_pitch_spin.setSingleStep(1.0)
		self.oblique_pitch_spin.setValue(0.0)
		self.oblique_pitch_spin.valueChanged.connect(self.refresh_previews)
		toolbar_layout.addWidget(QLabel("Pitch"), 2, 4)
		toolbar_layout.addWidget(self.oblique_pitch_spin, 2, 5)
		self.oblique_pitch_axis_combo = QComboBox()
		self.oblique_pitch_axis_combo.addItems(["X", "Y", "Z"])
		self.oblique_pitch_axis_combo.setCurrentText("X")
		self.oblique_pitch_axis_combo.currentTextChanged.connect(self.refresh_previews)
		toolbar_layout.addWidget(QLabel("Pitch axis"), 2, 6)
		toolbar_layout.addWidget(self.oblique_pitch_axis_combo, 2, 7)

		reset_oblique_button = QPushButton("Reset oblique")
		reset_oblique_button.clicked.connect(self.on_reset_oblique_clicked)
		toolbar_layout.addWidget(reset_oblique_button, 2, 8)

		self.show_oblique_check = QCheckBox("Show oblique")
		self.show_oblique_check.setChecked(False)
		self.show_oblique_check.toggled.connect(self.on_show_oblique_toggled)
		toolbar_layout.addWidget(self.show_oblique_check, 2, 9)

		axis_layout = QGridLayout()
		main_layout.addLayout(axis_layout)
		self._add_axis_controls(axis_layout, axis_name="X", row=0)
		self._add_axis_controls(axis_layout, axis_name="Y", row=1)
		self._add_axis_controls(axis_layout, axis_name="Z", row=2)

		self.views_layout = QGridLayout()
		main_layout.addLayout(self.views_layout, stretch=1)

		self._add_view_panel(self.views_layout, plane="XY", row=0, column=0)
		self._add_view_panel(self.views_layout, plane="YZ", row=0, column=1)
		self._add_view_panel(self.views_layout, plane="ZX", row=1, column=0)
		self._add_view_panel(self.views_layout, plane="OBLIQUE", row=1, column=1, clickable=False)

		self.views_layout.setRowStretch(0, 1)
		self.views_layout.setRowStretch(1, 1)
		self.views_layout.setColumnStretch(0, 1)
		self.views_layout.setColumnStretch(1, 1)

	def _add_axis_controls(self, layout, axis_name, row):
		"""Create synchronized slider and spin controls for one axis."""
		layout.addWidget(QLabel(axis_name), row, 0)

		slider = QSlider(Qt.Horizontal)
		slider.setTracking(True)
		slider.valueChanged.connect(lambda value, name=axis_name: self.on_axis_slider_changed(name, value))
		layout.addWidget(slider, row, 1)

		spin = QSpinBox()
		spin.valueChanged.connect(lambda value, name=axis_name: self.on_axis_spin_changed(name, value))
		layout.addWidget(spin, row, 2)

		self._axis_controls[axis_name] = {
			"slider": slider,
			"spin": spin,
		}

	def _add_view_panel(self, layout, plane, row, column, clickable=True):
		"""Create one scrollable image panel for the selected plane."""
		group = QGroupBox(plane)
		group_layout = QVBoxLayout(group)
		header_layout = QHBoxLayout()

		label = SliceViewLabel(plane)
		if clickable:
			label.planeClicked.connect(self.on_plane_clicked)

		rtg_checkbox = QCheckBox("RTG")
		rtg_checkbox.toggled.connect(self.refresh_previews)
		header_layout.addWidget(rtg_checkbox)

		full_checkbox = QCheckBox("Full")
		full_checkbox.toggled.connect(lambda enabled, p=plane: self.on_full_view_toggled(p, enabled))
		header_layout.addWidget(full_checkbox)
		header_layout.addStretch(1)
		group_layout.addLayout(header_layout)

		scroll_area = QScrollArea()
		scroll_area.setWidgetResizable(True)

		container = QWidget()
		container_layout = QVBoxLayout(container)
		container_layout.setContentsMargins(0, 0, 0, 0)
		container_layout.addWidget(label, alignment=Qt.AlignCenter)
		scroll_area.setWidget(container)

		group_layout.addWidget(scroll_area)
		layout.addWidget(group, row, column)
		self._view_positions[plane] = (row, column)

		self._view_widgets[plane] = {
			"group": group,
			"label": label,
			"full_checkbox": full_checkbox,
			"rtg_checkbox": rtg_checkbox,
			"scroll": scroll_area,
		}

	def _sync_window_controls(self):
		"""Initialize windowing controls from the current volumetric state."""
		vmin = float(self.volumetric.m_min)
		vmax = float(self.volumetric.m_max)

		self.win_min_spin.blockSignals(True)
		self.win_max_spin.blockSignals(True)
		self.win_min_spin.setRange(vmin, vmax)
		self.win_max_spin.setRange(vmin, vmax)
		self.win_min_spin.setValue(float(self.volumetric.m_minDisplWin))
		self.win_max_spin.setValue(float(self.volumetric.m_maxDisplWin))
		self.win_min_spin.blockSignals(False)
		self.win_max_spin.blockSignals(False)

	def _sync_axis_ranges(self, reset_to_center=False):
		"""Initialize or update the available X/Y/Z ranges from the volume shape."""
		layers, rows, columns = self.volumetric.shape
		ranges = {
			"X": max(0, int(columns) - 1),
			"Y": max(0, int(rows) - 1),
			"Z": max(0, int(layers) - 1),
		}

		for axis_name, maximum in ranges.items():
			slider = self._axis_controls[axis_name]["slider"]
			spin = self._axis_controls[axis_name]["spin"]

			slider.blockSignals(True)
			spin.blockSignals(True)
			slider.setRange(0, maximum)
			spin.setRange(0, maximum)
			if reset_to_center:
				center_value = maximum // 2
				slider.setValue(center_value)
				spin.setValue(center_value)
			else:
				current_value = min(spin.value(), maximum)
				slider.setValue(current_value)
				spin.setValue(current_value)
			slider.blockSignals(False)
			spin.blockSignals(False)

	def _get_axis_value(self, axis_name):
		"""Return the current integer value for one navigation axis."""
		return int(self._axis_controls[axis_name]["spin"].value())

	def _set_axis_value(self, axis_name, value):
		"""Update one axis without creating slider-spin feedback loops."""
		controls = self._axis_controls[axis_name]
		slider = controls["slider"]
		spin = controls["spin"]
		clamped_value = max(spin.minimum(), min(int(value), spin.maximum()))

		slider.blockSignals(True)
		spin.blockSignals(True)
		slider.setValue(clamped_value)
		spin.setValue(clamped_value)
		slider.blockSignals(False)
		spin.blockSignals(False)

	def _plane_rtg_enabled(self, plane):
		"""Return True when the selected panel should use projection mode."""
		return bool(self._view_widgets[plane]["rtg_checkbox"].isChecked())

	def _is_plane_enabled(self, plane):
		"""Return True when the panel should participate in layout and refresh."""
		return plane != "OBLIQUE" or self.show_oblique_check.isChecked()

	def _update_layout_mode(self):
		"""Rebuild the grid so one `Full` panel can span the whole preview area."""
		active_plane = None
		for plane in ("XY", "YZ", "ZX", "OBLIQUE"):
			if not self._is_plane_enabled(plane):
				continue
			if self._view_widgets[plane]["full_checkbox"].isChecked():
				active_plane = plane
				break

		while self.views_layout.count() > 0:
			item = self.views_layout.takeAt(0)
			widget = item.widget()
			if widget is not None:
				widget.setParent(None)

		if active_plane is None:
			for plane in ("XY", "YZ", "ZX", "OBLIQUE"):
				if not self._is_plane_enabled(plane):
					self._view_widgets[plane]["group"].setVisible(False)
					continue
				row, column = self._view_positions[plane]
				group = self._view_widgets[plane]["group"]
				self.views_layout.addWidget(group, row, column)
				group.setVisible(True)
			return

		active_group = self._view_widgets[active_plane]["group"]
		self.views_layout.addWidget(active_group, 0, 0, 2, 2)
		active_group.setVisible(True)
		for plane in ("XY", "YZ", "ZX", "OBLIQUE"):
			group = self._view_widgets[plane]["group"]
			if plane != active_plane:
				group.setVisible(False)

	def _visible_planes(self):
		"""Return the planes that are currently visible and worth recomputing."""
		visible_planes = [
			plane
			for plane in ("XY", "YZ", "ZX", "OBLIQUE")
			if self._is_plane_enabled(plane) and self._view_widgets[plane]["group"].isVisible()
		]
		if visible_planes:
			return visible_planes

		return [
			plane
			for plane in ("XY", "YZ", "ZX", "OBLIQUE")
			if self._is_plane_enabled(plane)
		]

	def _update_position_label(self):
		"""Show the current shared crosshair position in voxel coordinates."""
		x_value = self._get_axis_value("X")
		y_value = self._get_axis_value("Y")
		z_value = self._get_axis_value("Z")
		yaw_value = self.oblique_yaw_spin.value()
		pitch_value = self.oblique_pitch_spin.value()
		yaw_axis = self.oblique_yaw_axis_combo.currentText()
		pitch_axis = self.oblique_pitch_axis_combo.currentText()
		slab_mm = self.slab_thickness_spin.value()
		slab_mode = self.slab_mode_combo.currentText()
		slab_samples = self.slab_samples_spin.value()
		rtg_mode = self.rtg_mode_combo.currentText()
		xray_gain = self.xray_gain_spin.value()
		xray_gamma = self.xray_gamma_spin.value()
		rtg_planes = ",".join([
			plane
			for plane in ("XY", "YZ", "ZX", "OBLIQUE")
			if self._is_plane_enabled(plane) and self._plane_rtg_enabled(plane)
		]) or "-"
		self.position_label.setText(
			f"Crosshair: X={x_value}  Y={y_value}  Z={z_value}  |  Oblique yaw={yaw_value:.1f}@{yaw_axis} pitch={pitch_value:.1f}@{pitch_axis}  |  Slab {slab_mm:.1f} mm {slab_mode} x{slab_samples}  |  RTG {rtg_mode} gain={xray_gain:.3f} gamma={xray_gamma:.2f} [{rtg_planes}]"
		)

	def _get_plane_image(self, plane):
		"""Fetch the current preview QImage for one anatomical plane."""
		use_display_window = self.displ_window_check.isChecked()
		invert = self.invert_check.isChecked()
		rtg = self._plane_rtg_enabled(plane)
		rtg_mode = self.rtg_mode_combo.currentText()
		xray_gain = self.xray_gain_spin.value()
		xray_gamma = self.xray_gamma_spin.value()
		slab_thickness_mm = self.slab_thickness_spin.value()
		slab_samples = self.slab_samples_spin.value()
		slab_mode = self.slab_mode_combo.currentText()
		if plane == "OBLIQUE":
			center_xyz = [
				self._get_axis_value("X"),
				self._get_axis_value("Y"),
				self._get_axis_value("Z"),
			]
			effective_slab_mm = slab_thickness_mm
			effective_samples = slab_samples
			effective_mode = slab_mode
			if rtg:
				_origin, _basis, spacing = self.volumetric.get_volume_geometry()
				diag_mm = float(max(spacing) * max(self.volumetric.shape))
				effective_slab_mm = slab_thickness_mm if slab_thickness_mm > 0.0 else diag_mm
				effective_samples = max(slab_samples, 32)
				effective_mode = rtg_mode
			return self.volumetric.get_oblique_preview_qimage(
				center_xyz=center_xyz,
				yaw_degrees=self.oblique_yaw_spin.value(),
				pitch_degrees=self.oblique_pitch_spin.value(),
				yaw_axis=self.oblique_yaw_axis_combo.currentText(),
				pitch_axis=self.oblique_pitch_axis_combo.currentText(),
				use_display_window=use_display_window,
				invert=invert,
				slab_thickness_mm=effective_slab_mm,
				slab_samples=effective_samples,
				slab_mode=effective_mode,
				xray_gain=xray_gain,
				xray_gamma=xray_gamma,
			)
		index_map = {
			"XY": self._get_axis_value("Z"),
			"YZ": self._get_axis_value("X"),
			"ZX": self._get_axis_value("Y"),
		}
		if (slab_thickness_mm > 0.0 or slab_samples > 1) and not rtg:
			image = self.volumetric.get_slice_array_slab(
				index=index_map[plane],
				plane=plane,
				slab_thickness_mm=slab_thickness_mm,
				slab_samples=slab_samples,
				slab_mode=slab_mode,
				use_display_window=use_display_window,
				xray_gain=xray_gain,
			)
			buffer = self.volumetric.normalize_slice_to_uint8(
				image=image,
				use_display_window=use_display_window,
				invert=invert,
			)
			height, width = buffer.shape
			return QImage(buffer.data, width, height, buffer.strides[0], QImage.Format_Grayscale8).copy()

		return self.volumetric.get_preview_qimage(
			index=index_map[plane],
			plane=plane,
			use_display_window=use_display_window,
			invert=invert,
			rtg=rtg,
			projection_mode=rtg_mode,
			xray_gain=xray_gain,
			xray_gamma=xray_gamma,
		)

	def _get_crosshair_coords(self, plane, image_width, image_height):
		"""Map the shared X/Y/Z position into one plane's image coordinates."""
		if plane == "OBLIQUE":
			return image_width // 2, image_height // 2

		x_value = self._get_axis_value("X")
		y_value = self._get_axis_value("Y")
		z_value = self._get_axis_value("Z")

		if plane == "YZ":
			return (
				max(0, min(z_value, image_width - 1)),
				max(0, min(y_value, image_height - 1)),
			)
		if plane == "ZX":
			return (
				max(0, min(x_value, image_width - 1)),
				max(0, min(z_value, image_height - 1)),
			)
		return (
			max(0, min(x_value, image_width - 1)),
			max(0, min(y_value, image_height - 1)),
		)

	def _scaled_pixmap_with_crosshair(self, plane, qimage, target_size):
		"""Scale a plane preview and draw the shared crosshair on top of it."""
		pixmap = QPixmap.fromImage(qimage)
		scaled = pixmap.scaled(
			target_size,
			Qt.KeepAspectRatio,
			Qt.SmoothTransformation,
		)

		source_width = max(1, qimage.width())
		source_height = max(1, qimage.height())
		target_width = max(1, scaled.width())
		target_height = max(1, scaled.height())
		cross_x, cross_y = self._get_crosshair_coords(plane, source_width, source_height)

		draw_x = int(round(cross_x * (target_width - 1) / max(1, source_width - 1)))
		draw_y = int(round(cross_y * (target_height - 1) / max(1, source_height - 1)))

		painter = QPainter(scaled)
		painter.setRenderHint(QPainter.Antialiasing, False)

		pen_primary = QPen(QColor(255, 64, 64))
		pen_primary.setWidth(1)
		painter.setPen(pen_primary)
		painter.drawLine(draw_x, 0, draw_x, target_height - 1)
		painter.drawLine(0, draw_y, target_width - 1, draw_y)

		pen_secondary = QPen(QColor(64, 255, 255))
		pen_secondary.setWidth(1)
		painter.setPen(pen_secondary)
		painter.drawEllipse(draw_x - 3, draw_y - 3, 6, 6)
		painter.end()

		return scaled

	def _update_view_widget(self, plane):
		"""Refresh one panel from the current crosshair position."""
		qimage = self._get_plane_image(plane)
		self._images_by_plane[plane] = qimage

		label = self._view_widgets[plane]["label"]
		scroll_area = self._view_widgets[plane]["scroll"]
		label.set_source_size(qimage.width(), qimage.height())

		if self.fit_check.isChecked():
			target_size = scroll_area.viewport().size()
		else:
			scale = float(self.zoom_spin.value())
			source_size = QPixmap.fromImage(qimage).size()
			target_size = source_size.scaled(
				max(1, int(round(source_size.width() * scale))),
				max(1, int(round(source_size.height() * scale))),
				Qt.KeepAspectRatio,
			)

		scaled = self._scaled_pixmap_with_crosshair(plane, qimage, target_size)
		label.setPixmap(scaled)
		label.resize(scaled.size())

		mode = "RTG" if self._plane_rtg_enabled(plane) else "Slice"
		self._view_widgets[plane]["group"].setTitle(f"{plane}  {mode}  {qimage.width()}x{qimage.height()}")

	def resizeEvent(self, event):
		"""Refresh panels when the dialog changes size in fit mode."""
		super(DialogVolumetricPreview, self).resizeEvent(event)
		if self.fit_check.isChecked():
			self.refresh_previews()

	@pyqtSlot()
	def refresh_previews(self):
		"""Rebuild all three orthogonal previews and redraw crosshairs."""
		self._update_xray_controls()
		self._update_layout_mode()
		visible_planes = self._visible_planes()
		QApplication.setOverrideCursor(Qt.WaitCursor)
		try:
			self._update_position_label()
			for plane in visible_planes:
				self._update_view_widget(plane)
		finally:
			QApplication.restoreOverrideCursor()

	def _update_xray_controls(self):
		"""Enable Xray-specific controls only when they are relevant."""
		is_any_rtg_enabled = any(
			self._is_plane_enabled(plane) and self._plane_rtg_enabled(plane)
			for plane in ("XY", "YZ", "ZX", "OBLIQUE")
		)
		is_xray_mode = is_any_rtg_enabled and self.rtg_mode_combo.currentText() == "xray"
		self.xray_gain_spin.setEnabled(is_xray_mode)
		self.xray_gamma_spin.setEnabled(is_xray_mode)

	@pyqtSlot(str, bool)
	def on_full_view_toggled(self, plane, enabled):
		"""Switch between quad view and one selected full-size panel."""
		if enabled:
			for other_plane in ("XY", "YZ", "ZX", "OBLIQUE"):
				if other_plane == plane:
					continue
				checkbox = self._view_widgets[other_plane]["full_checkbox"]
				checkbox.blockSignals(True)
				checkbox.setChecked(False)
				checkbox.blockSignals(False)
		self.refresh_previews()

	@pyqtSlot(bool)
	def on_show_oblique_toggled(self, enabled):
		"""Show or hide the heavy OBLIQUE panel to save recomputation time."""
		if not enabled:
			for key in ("full_checkbox", "rtg_checkbox"):
				checkbox = self._view_widgets["OBLIQUE"][key]
				checkbox.blockSignals(True)
				checkbox.setChecked(False)
				checkbox.blockSignals(False)
		self.refresh_previews()

	@pyqtSlot(str, int, int)
	def on_plane_clicked(self, plane, image_x, image_y):
		"""Move the shared crosshair to the clicked voxel in one plane."""
		if plane == "YZ":
			self._set_axis_value("Z", image_x)
			self._set_axis_value("Y", image_y)
		elif plane == "ZX":
			self._set_axis_value("X", image_x)
			self._set_axis_value("Z", image_y)
		else:
			self._set_axis_value("X", image_x)
			self._set_axis_value("Y", image_y)

		self.refresh_previews()

	@pyqtSlot(bool)
	def on_rtg_all_toggled(self, enabled):
		"""Toggle RTG for every panel at once as a convenience shortcut."""
		for plane in ("XY", "YZ", "ZX", "OBLIQUE"):
			if not self._is_plane_enabled(plane):
				continue
			checkbox = self._view_widgets[plane]["rtg_checkbox"]
			checkbox.blockSignals(True)
			checkbox.setChecked(enabled)
			checkbox.blockSignals(False)
		self.refresh_previews()

	@pyqtSlot(str, int)
	def on_axis_slider_changed(self, axis_name, value):
		"""Synchronize a slider move into the paired spin box."""
		spin = self._axis_controls[axis_name]["spin"]
		spin.blockSignals(True)
		spin.setValue(value)
		spin.blockSignals(False)
		self.refresh_previews()

	@pyqtSlot(str, int)
	def on_axis_spin_changed(self, axis_name, value):
		"""Synchronize a spin-box edit into the paired slider."""
		slider = self._axis_controls[axis_name]["slider"]
		slider.blockSignals(True)
		slider.setValue(value)
		slider.blockSignals(False)
		self.refresh_previews()

	@pyqtSlot()
	def on_reset_center_clicked(self):
		"""Reset the crosshair to the center of the current volume."""
		self._sync_axis_ranges(reset_to_center=True)
		self.refresh_previews()

	@pyqtSlot()
	def on_reset_oblique_clicked(self):
		"""Reset oblique rotation back to the axial orientation."""
		self.oblique_yaw_spin.blockSignals(True)
		self.oblique_pitch_spin.blockSignals(True)
		self.oblique_yaw_axis_combo.blockSignals(True)
		self.oblique_pitch_axis_combo.blockSignals(True)
		self.oblique_yaw_spin.setValue(0.0)
		self.oblique_pitch_spin.setValue(0.0)
		self.oblique_yaw_axis_combo.setCurrentText("Y")
		self.oblique_pitch_axis_combo.setCurrentText("X")
		self.oblique_yaw_spin.blockSignals(False)
		self.oblique_pitch_spin.blockSignals(False)
		self.oblique_yaw_axis_combo.blockSignals(False)
		self.oblique_pitch_axis_combo.blockSignals(False)
		self.refresh_previews()

	@pyqtSlot(float)
	def on_window_min_changed(self, value):
		"""Clamp and propagate the lower display window bound."""
		if value > self.win_max_spin.value():
			value = self.win_max_spin.value()
			self.win_min_spin.blockSignals(True)
			self.win_min_spin.setValue(value)
			self.win_min_spin.blockSignals(False)

		self.volumetric.m_minDisplWin = float(value)
		self.win_max_spin.setMinimum(float(value))
		self.refresh_previews()

	@pyqtSlot(float)
	def on_window_max_changed(self, value):
		"""Clamp and propagate the upper display window bound."""
		if value < self.win_min_spin.value():
			value = self.win_min_spin.value()
			self.win_max_spin.blockSignals(True)
			self.win_max_spin.setValue(value)
			self.win_max_spin.blockSignals(False)

		self.volumetric.m_maxDisplWin = float(value)
		self.win_min_spin.setMaximum(float(value))
		self.refresh_previews()
