import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
from math import atan, degrees
from sklearn.linear_model import LinearRegression

import logging
logger = logging.getLogger(__name__)

class FrastaProfileDock(QtWidgets.QDockWidget):
	pointClicked = QtCore.pyqtSignal(int)  # (col, row, value)

	def __init__(self, parent=None):
		super().__init__(parent)
		self.setWindowTitle("FRASTA Profile")
		self.setFloating(True)

		central = QtWidgets.QWidget()
		self.setWidget(central)
		layout = QtWidgets.QVBoxLayout(central)

		self.plot_widget = pg.PlotWidget()
		layout.addWidget(self.plot_widget)

		# window size dla fit lines
		self.spinbox_window_um = QtWidgets.QDoubleSpinBox()
		self.spinbox_window_um.setRange(1, 5000)
		self.spinbox_window_um.setValue(500)
		self.spinbox_window_um.setSingleStep(1)
		self.spinbox_window_um.setDecimals(0)
		self.checkbox_snap = QtWidgets.QCheckBox("Snap to plot")
		self.checkbox_snap.setChecked(True)

		win_layout = QtWidgets.QHBoxLayout()
		win_layout.addWidget(QtWidgets.QLabel("Window size [µm]:"))
		win_layout.addWidget(self.spinbox_window_um)
		win_layout.addWidget(self.checkbox_snap)
		layout.addLayout(win_layout)

		self.positions_line = None
		self.reference_profile = None
		self.adjusted_profile = None
		self.distance_profile = None
		self.fit_lines = []
		self.h_line = None
		self.cursor_lines = []
		self.annotations = []
		self.saved_points = []

		self.plot_widget.scene().sigMouseMoved.connect(self.on_mouse_move)
		self.plot_widget.scene().sigMouseClicked.connect(self.on_plot_click)

	def set_profiles(self, positions, profiles, dist):
		self.plot_widget.clear()
		for name, prof, pen in profiles:
			self.plot_widget.plot(positions, prof, pen=pen, name=name)
		self.plot_widget.plot(positions, dist, pen=pg.mkPen('r', width=2), name="Dist")

		self.positions_line = positions
		self.reference_profile = profiles[0][1] if profiles else None
		self.adjusted_profile = profiles[1][1] if len(profiles) > 1 else None
		self.distance_profile = dist

	def on_mouse_move(self, pos):
		if not self.plot_widget.sceneBoundingRect().contains(pos):
			return
		mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
		x_pos = mouse_point.x()
		y_pos = mouse_point.y()

		self._clear_cursor_and_annotations()

		if self.positions_line is not None and len(self.positions_line) > 0:
			if self.positions_line[0] <= x_pos <= self.positions_line[-1]:
				self._draw_cursor_line(x_pos, angle=90, color='r')
				self._draw_cursor_line(y_pos, angle=0, color='b')
				idx = np.argmin(np.abs(self.positions_line - x_pos))
				self._draw_annotations_and_fit_lines(x_pos, idx)

	def on_plot_click(self, event):
		if event.modifiers() == QtCore.Qt.ControlModifier:
			pos = event.scenePos()
			if not self.plot_widget.sceneBoundingRect().contains(pos): return
			mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
			x_pos = mouse_point.x()
			if not (self.positions_line[0] <= x_pos <= self.positions_line[-1]): return
			idx = np.argmin(np.abs(self.positions_line - x_pos))
			self._save_profile_point(idx)

	def _save_profile_point(self, idx):
		val = self.reference_profile[idx] if self.reference_profile is not None else None
		self.pointClicked.emit(idx)

	def _clear_cursor_and_annotations(self):
		for item in self.cursor_lines + self.annotations:
			self.plot_widget.removeItem(item)
		self.cursor_lines.clear(); self.annotations.clear()

	def _clear_fit_lines(self):
		for item in self.fit_lines:
			self.plot_widget.removeItem(item)
		self.fit_lines.clear()

	def _draw_cursor_line(self, pos, angle=90, color='r'):
		line = pg.InfiniteLine(
			angle=angle,
			pen=pg.mkPen(color, width=1, style=QtCore.Qt.DashLine)
		)
		self.plot_widget.addItem(line)
		line.setPos(pos)
		self.cursor_lines.append(line)

	def _fit_profile(self, x_um, y_um):
		X = x_um.reshape(-1, 1)
		Y = y_um.reshape(-1, 1)
		reg = LinearRegression().fit(X, Y)
		slope = reg.coef_[0][0]
		angle = degrees(atan(slope))
		return slope, angle, reg

	def _draw_fit_line(self, x_pos_um, slope, reg, idx, window_um, color='y'):
		vb = self.plot_widget.getPlotItem().vb
		half = window_um / 2.0
		x0, x1 = x_pos_um - half, x_pos_um + half

		if self.checkbox_snap.isChecked():
			y_at_cursor_um = self.reference_profile[idx]
			b = y_at_cursor_um - slope * x_pos_um
		else:
			b = reg.intercept_[0]

		y0_um = slope * x0 + b
		y1_um = slope * x1 + b

		line = pg.PlotDataItem([x0, x1], [y0_um, y1_um],
							pen=pg.mkPen(color, width=2))
		self.plot_widget.addItem(line)
		self.fit_lines.append(line)

	def _draw_annotations_and_fit_lines(self, x_pos, idx):
		self._clear_fit_lines()

		window_um = self.spinbox_window_um.value()
		step_um = self.positions_line[1] - self.positions_line[0]
		window_size = max(1, int(round(window_um / step_um)))

		start = max(0, idx - window_size)
		end = min(len(self.positions_line), idx + window_size + 1)

		vb = self.plot_widget.getPlotItem().vb
		x_min, x_max = vb.viewRange()[0]
		y_min, y_max = vb.viewRange()[1]
		offset_y = 0.05 * (y_max - y_min)
		y_text = y_max - offset_y

		if self.reference_profile is not None and self.adjusted_profile is not None:
			slope_ref, angle_ref, reg_ref = self._fit_profile(self.positions_line[start:end],
															self.reference_profile[start:end])
			slope_adj, angle_adj, reg_adj = self._fit_profile(self.positions_line[start:end],
															self.adjusted_profile[start:end])
			val_ref = float(self.reference_profile[idx])
			val_adj = float(self.adjusted_profile[idx])
			dh = val_ref - val_adj
			dtheta = angle_adj - angle_ref

			self._draw_fit_line(x_pos, slope_ref, reg_ref, idx, window_um, color='g')
			self._draw_fit_line(x_pos, slope_adj, reg_adj, idx, window_um, color='b')

			t_ref = pg.TextItem(f"Ref: {val_ref:.1f} µm, {angle_ref:.1f}°", color='g', anchor=(0, 1))
			t_adj = pg.TextItem(f"Adj: {val_adj:.1f} µm, {angle_adj:.1f}°", color='b', anchor=(0, 1))
			t_diff = pg.TextItem(f"Δh: {dh:.1f} µm   Δθ: {dtheta:.1f}°", color='y', anchor=(0, 1))
			for t in (t_ref, t_adj, t_diff):
				t.setPos(x_min + 0.02*(x_max - x_min), y_text)
				self.plot_widget.addItem(t); self.annotations.append(t)
				y_text -= offset_y

