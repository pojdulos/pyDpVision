import sys
import os
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
from skimage.draw import line
from PyQt5.QtCore import QPointF
from math import atan, degrees
import numpy as np
#import h5py
from scipy.ndimage import gaussian_filter
from sklearn.linear_model import LinearRegression

#from .grid3DViewer import show_3d_viewer
from .helpers import remove_relative_offset, remove_relative_tilt
from dpVision import GridData64

import logging
logger = logging.getLogger(__name__)

def create_image_view():
    view = pg.ImageView()
    view.ui.histogram.hide()
    view.ui.roiBtn.hide()
    view.ui.menuBtn.hide()
    return view

class FrastaViewer(QtWidgets.QMainWindow):
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setWindowTitle("FRASTA analysis")
		self.setGeometry(100, 100, 1000, 600)

		# --- dane ---
		self.distance_map = None
		self.grid1 = None
		self.grid2 = None

		self.binary_contact = None
		self.pixel_um = QPointF(1.0, 1.0)
		self.separation = 0.0

		# --- widżety ---
		central = QtWidgets.QWidget(); self.setCentralWidget(central)
		main_layout = QtWidgets.QHBoxLayout(central)
		layout = QtWidgets.QVBoxLayout()

		# wykres profilu
		self.plot_widget = pg.PlotWidget()
		main_layout.addWidget(self.plot_widget, 2)
		main_layout.addLayout(layout)

		# widok obrazu
		self.image_view = create_image_view()
		self.image_view.setMinimumWidth(400)
		layout.addWidget(self.image_view, 3)
		self.image_view.getView().sigRangeChanged.connect(self.on_range_changed)

		# separation spinbox
		sep_layout = QtWidgets.QHBoxLayout()
		self.spinbox_separation = QtWidgets.QDoubleSpinBox()
		self.spinbox_separation.setRange(-5000, 5000)
		self.spinbox_separation.setDecimals(2)
		self.spinbox_separation.setValue(self.separation)
		self.spinbox_separation.valueChanged.connect(self.update_plot)
		sep_layout.addWidget(QtWidgets.QLabel("Separation [µm]:"))
		sep_layout.addWidget(self.spinbox_separation)
		layout.addLayout(sep_layout)

		# window size dla fit lines
		self.spinbox_window_mm = QtWidgets.QDoubleSpinBox()
		self.spinbox_window_mm.setRange(0.001, 5.0)
		self.spinbox_window_mm.setValue(0.5)
		self.spinbox_window_mm.setSingleStep(0.001)
		self.spinbox_window_mm.setDecimals(3)
		self.spinbox_window_mm.valueChanged.connect(self.update_profile_from_roi)

		self.checkbox_snap = QtWidgets.QCheckBox("Snap to plot")
		self.checkbox_snap.setChecked(True)

		win_layout = QtWidgets.QHBoxLayout()
		win_layout.addWidget(QtWidgets.QLabel("Window size [mm]:"))
		win_layout.addWidget(self.spinbox_window_mm)
		win_layout.addWidget(self.checkbox_snap)
		layout.addLayout(win_layout)

		# ROI linia
		self.line_roi = None
		# self.image_view.getView().mousePressEvent = self.on_image_click

		# status bar
		self.progress_bar = QtWidgets.QProgressBar()
		self.progress_bar.setVisible(False)
		self.statusBar().addPermanentWidget(self.progress_bar)

		# stan
		self.rr, self.cc = None, None
		self.positions_line = None
		self.reference_profile = None  # = profile mapy odległości
		self.cursor_lines = []
		self.annotations = []
		self.image_marker = None
		self.saved_points = []
		self.saved_point_markers = []
		self.mytest = []

		# sygnały myszy
		self.plot_widget.scene().sigMouseMoved.connect(self.on_mouse_move)
		self.plot_widget.scene().sigMouseClicked.connect(self.on_plot_click)

	# --- API ---

	def set_data(self, distance_map: GridData64, grid1: GridData64 = None, grid2: GridData64 = None):
		"""Ustaw dane do wyświetlania. Siatki są opcjonalne."""
		self.distance_map = distance_map
		self.grid1 = grid1
		self.grid2 = grid2

		h = self.distance_map.m_grid64.shape[0]
		w = self.distance_map.m_grid64.shape[1]
		if self.grid1 is not None:
			self.grid1.m_grid64 = self.grid1.m_grid64[:h, :w]
		if self.grid2 is not None:
			self.grid2.m_grid64 = self.grid2.m_grid64[:h, :w]

		self.x1, self.y1 = 0, 0
		self.x2, self.y2 = w - 1, h - 1

		self.redraw_roi()
		self.update_plot()


	# --- logika ---
	def update_plot(self):
		"""Odśwież widok binarny na podstawie separacji."""
		self.separation = self.spinbox_separation.value()
		dist = self.distance_map.m_grid64
		valid = np.isfinite(dist)
		binary_contact = (dist > self.separation) & valid

		# self.image_view.setImage(np.fliplr(binary_contact.T.astype(np.uint8)), autoRange=False, autoLevels=True)
		arr = binary_contact.astype(np.uint8)
		arr = arr.T[:, ::-1]   # transpozycja + odwrócenie w pionie
		self.image_view.setImage(arr, autoRange=False, autoLevels=True)

		self.binary_contact = binary_contact
		self.update_profile_from_roi()
		self.update_volume_info()


	# --- ROI i profile ---
	def on_image_click(self, event):
		pos = event.scenePos()
		vb = self.image_view.getView()
		mouse_point = vb.mapSceneToView(pos)
		x, y = int(round(mouse_point.x())), int(round(mouse_point.y()))
		if self.line_roi is None:
			self.x1, self.y1 = x, y
			self.x2, self.y2 = x, y
			self.redraw_roi()
		else:
			self.x2, self.y2 = x, y
			self.redraw_roi()
			self.update_profile_from_roi()

	def update_roi_markers(self):
		# Usuń stare markery (jeśli są)
		if hasattr(self, "roi_endpoint_markers"):
			for m in self.roi_endpoint_markers:
				self.image_view.getView().removeItem(m)
		self.roi_endpoint_markers = []
		if hasattr(self, "roi_endpoint_labels"):
			for t in self.roi_endpoint_labels:
				self.image_view.getView().removeItem(t)
		self.roi_endpoint_labels = []
		
		# Pobierz BIEŻĄCE pozycje końców ROI w układzie obrazka!
		handle0 = self.line_roi.getHandles()[0]
		handle1 = self.line_roi.getHandles()[1]
		pt0 = self.line_roi.mapToParent(handle0.pos())
		pt1 = self.line_roi.mapToParent(handle1.pos())
		x1, y1 = pt0.x(), pt0.y()
		x2, y2 = pt1.x(), pt1.y()

		# Dodaj markery
		marker1 = pg.ScatterPlotItem([x1], [y1], size=18, pen=pg.mkPen('g', width=3), brush=pg.mkBrush(0,255,0,100), symbol='o')
		marker2 = pg.ScatterPlotItem([x2], [y2], size=18, pen=pg.mkPen('r', width=3), brush=pg.mkBrush(255,0,0,100), symbol='x')
		self.image_view.getView().addItem(marker1)
		self.image_view.getView().addItem(marker2)
		self.roi_endpoint_markers = [marker1, marker2]
		
		# Opcjonalnie: etykiety z numerkami
		label1 = pg.TextItem("1", color='g', anchor=(0.5, 1.5))
		label1.setPos(x1, y1)
		label2 = pg.TextItem("2", color='r', anchor=(0.5, 1.5))
		label2.setPos(x2, y2)
		self.image_view.getView().addItem(label1)
		self.image_view.getView().addItem(label2)
		self.roi_endpoint_labels = [label1, label2]

	def redraw_roi(self):
		if self.line_roi is not None:
			try:
				self.image_view.getView().removeItem(self.line_roi)
			except Exception:
				pass

		# używamy współrzędnych widoku, nie numpy
		self.line_roi = pg.LineROI(
			[self.x1, self.y1],
			[self.x2, self.y2],
			pen=pg.mkPen('r', width=2),
			width=1
		)
		self.line_roi.handles[2]['type'] = 'center'
		self.line_roi.sigRegionChanged.connect(self.update_profile_from_roi)
		self.line_roi.sigRegionChanged.connect(self.update_roi_markers)

		self.image_view.getView().addItem(self.line_roi)
		self.line_roi.setZValue(10)

		self.update_roi_markers()


	def clamp_roi_to_image(self):
		if self.line_roi is None: 
			return
		h, w = self.distance_map.m_grid64.shape
		x_max = h - 1
		y_max = w - 1

		handles = self.line_roi.getHandles()
		pt1 = self.line_roi.mapToParent(handles[0].pos())
		pt2 = self.line_roi.mapToParent(handles[1].pos())

		self.x1 = float(np.clip(pt1.x(), 0, x_max))
		self.y1 = float(np.clip(pt1.y(), 0, y_max))
		self.x2 = float(np.clip(pt2.x(), 0, x_max))
		self.y2 = float(np.clip(pt2.y(), 0, y_max))


	def get_roi_coords(self):
		if self.line_roi is None:
			return None, None
		handles = self.line_roi.getHandles()
		pt0 = self.line_roi.mapToParent(handles[0].pos())
		pt1 = self.line_roi.mapToParent(handles[1].pos())

		r0, c0 = self.view_to_numpy(pt0.x(), pt0.y())
		r1, c1 = self.view_to_numpy(pt1.x(), pt1.y())
		return (r0, c0), (r1, c1)

	def update_profile_from_roi(self):
		self.clamp_roi_to_image()
		if self.line_roi is None: 
			return

		p1, p2 = self.get_roi_coords()  # używa view_to_numpy()
		if p1 is None or p2 is None:
			return

		r0, c0 = p1
		r1, c1 = p2
		rr, cc = line(r0, c0, r1, c1)

		h, w = self.distance_map.m_grid64.shape
		rr = np.clip(rr, 0, h-1)
		cc = np.clip(cc, 0, w-1)

		# profil odległości
		prof_dist = self.distance_map.m_grid64[rr, cc]
		valid = np.isfinite(prof_dist)

		profiles = []
		if self.grid1 is not None and self.grid2 is not None:
			prof1 = self.grid1.m_grid64[rr, cc]
			prof2 = self.grid2.m_grid64[rr, cc] + self.separation
			valid &= np.isfinite(prof1) & np.isfinite(prof2)
			profiles.append(("Ref", prof1[valid], pg.mkPen('g', width=2)))
			profiles.append(("Adj", prof2[valid], pg.mkPen('b', width=2)))

		positions_line = np.arange(len(rr))[valid] * (self.distance_map.stepX / 1000.0)
		prof_dist = prof_dist[valid]

		self.plot_widget.clear()
		for name, prof, pen in profiles:
			self.plot_widget.plot(positions_line, prof, pen=pen, name=name)
		#self.plot_widget.plot(positions_line, prof_dist, pen=pg.mkPen('r', width=2), name="Dist")

		# zapamiętaj
		self.positions_line   = positions_line
		self.reference_profile = profiles[0][1] if profiles else None
		self.adjusted_profile  = profiles[1][1] if profiles else None
		#self.distance_profile  = prof_dist
		self.rr = rr[valid]
		self.cc = cc[valid]


	# --- obsługa myszy i adnotacje ---
	def on_mouse_move(self, pos):
		if not self.plot_widget.sceneBoundingRect().contains(pos): return
		mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
		x_pos = mouse_point.x()
		self._clear_cursor_and_annotations()
		self._draw_cursor_line(x_pos)
		if self.positions_line is not None and len(self.positions_line) > 0:
			if self.positions_line[0] <= x_pos <= self.positions_line[-1]:
				idx = np.argmin(np.abs(self.positions_line - x_pos))
				self._update_image_marker(idx)
				self._draw_annotations_and_fit_lines(x_pos, idx)
			else:
				self._clear_marker()

	def on_plot_click(self, event):
		if event.modifiers() == QtCore.Qt.ControlModifier:
			self._handle_ctrl_click(event)

	def _handle_ctrl_click(self, event):
		pos = event.scenePos()
		if not self.plot_widget.sceneBoundingRect().contains(pos): return
		mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
		x_pos = mouse_point.x()
		if not (self.positions_line[0] <= x_pos <= self.positions_line[-1]): return
		idx = np.argmin(np.abs(self.positions_line - x_pos))
		self._save_profile_point(idx)

	def _save_profile_point(self, idx):
		x_img, y_img = self.numpy_to_view(self.rr[idx], self.cc[idx])
		val = self.reference_profile[idx]
		pos_mm = self.positions_line[idx]
		self.saved_points.append({
			'profile_idx': idx,
			'x_img': int(x_img), 'y_img': int(y_img),
			'x_pos_mm': float(pos_mm), 'val_um': float(val),
		})
		marker = pg.ScatterPlotItem([x_img], [y_img], size=12,
									pen=pg.mkPen('g', width=2),
									brush=pg.mkBrush(0,255,255,120), symbol='+')
		self.image_view.getView().addItem(marker)
		self.saved_point_markers.append(marker)
		logger.debug("Saved point:", self.saved_points[-1])

	# --- fit lines i kąty (na jednej krzywej) ---
	def _draw_annotations_and_fit_lines(self, x_pos, idx):
		val = self.reference_profile[idx]
		window_mm = self.spinbox_window_mm.value()
		pixel_size_mm = self.pixel_um.x() / 1000.0
		window_size = max(1, int(round(window_mm / pixel_size_mm)))
		start = max(0, idx - window_size)
		end = min(len(self.positions_line), idx + window_size + 1)

		slope, angle, reg = self._fit_profile(self.positions_line[start:end],
											self.reference_profile[start:end])

		# adnotacja wartości i kąta
		self._draw_diff_and_angle_text(val, angle)

		# fit line
		self._draw_fit_line(x_pos, slope, reg, idx, window_mm)

	def _fit_profile(self, x, y):
		x_fit = x.reshape(-1, 1)
		y_fit = y.reshape(-1, 1) / 1000.0  # mm
		reg = LinearRegression().fit(x_fit, y_fit)
		slope = reg.coef_[0][0]
		angle = degrees(atan(slope))
		return slope, angle, reg

	def _draw_diff_and_angle_text(self, val, angle):
		vb = self.plot_widget.getPlotItem().vb
		x_min, x_max = vb.viewRange()[0]
		y_min, y_max = vb.viewRange()[1]
		text1 = pg.TextItem(f"dist: {val:.1f} µm", color='r', anchor=(0, 1))
		text1.setPos(x_min+0.02*(x_max-x_min), y_max-0.05*(y_max-y_min))
		self.plot_widget.addItem(text1); self.annotations.append(text1)
		text2 = pg.TextItem(f"Angle: {angle:.1f}°", color='y', anchor=(0, 1))
		text2.setPos(x_min+0.02*(x_max-x_min), y_max-0.2*(y_max-y_min))
		self.plot_widget.addItem(text2); self.annotations.append(text2)

	def _draw_fit_line(self, x_pos, slope, reg, idx, window_mm):
		vb = self.plot_widget.getPlotItem().vb
		line_half_width_mm = window_mm / 2.0
		x0, x1 = x_pos - line_half_width_mm, x_pos + line_half_width_mm
		if self.checkbox_snap.isChecked():
			y_at_cursor = self.reference_profile[idx] / 1000.0
			b = y_at_cursor - slope * x_pos
		else:
			b = reg.intercept_[0]
		y0, y1 = slope * x0 + b, slope * x1 + b
		for item in self.mytest: vb.removeItem(item)
		self.mytest.clear()
		line = pg.PlotDataItem([x0, x1], [y0*1000, y1*1000],
							pen=pg.mkPen('y', width=2))
		vb.addItem(line, ignoreBounds=True)
		self.annotations.append(line); self.mytest.append(line)

	# --- helpers ---
	def _clear_cursor_and_annotations(self):
		for item in self.cursor_lines + self.annotations:
			self.plot_widget.removeItem(item)
		self.cursor_lines.clear(); self.annotations.clear()

	def _draw_cursor_line(self, x_pos):
		vline = pg.InfiniteLine(pos=x_pos, angle=90,
								pen=pg.mkPen('r', width=1,
											style=QtCore.Qt.DashLine))
		self.plot_widget.addItem(vline); self.cursor_lines.append(vline)

	def _shape_np(self):
		h, w = self.distance_map.m_grid64.shape
		return h, w

	def view_to_numpy(self, x_view, y_view):
		h, w = self._shape_np()  # h = rows, w = cols w oryginalnym numpy
		col = int(round(x_view))           # pozioma
		row = h - 1 - int(round(y_view))   # pionowa odwrócona
		row = int(np.clip(row, 0, h-1))
		col = int(np.clip(col, 0, w-1))
		return row, col

	def numpy_to_view(self, row, col):
		h, w = self._shape_np()
		x_view = float(col)
		y_view = float(h - 1 - row)
		return x_view, y_view

	def _update_image_marker(self, idx):
		if self.rr is None or self.cc is None or idx < 0 or idx >= len(self.rr):
			return
		r, c = self.rr[idx], self.cc[idx]
		x_view, y_view = self.numpy_to_view(r, c)

		view = self.image_view.getView()
		if self.image_marker:
			view.removeItem(self.image_marker)
		self.image_marker = pg.ScatterPlotItem([x_view], [y_view],
											size=14,
											pen=pg.mkPen('m', width=2),
											brush=pg.mkBrush(255,0,255,100))
		view.addItem(self.image_marker)



	def _clear_marker(self):
		view = self.image_view.getView()
		if self.image_marker:
			view.removeItem(self.image_marker); self.image_marker = None


	def resize_image_view(self, shape):
		h, w = shape; aspect = w/h; base = 500
		if aspect >= 1: w,h = base,int(base/aspect)
		else: h,w = base,int(base*aspect)
		self.image_view.setFixedSize(w,h)


	def on_range_changed(self, viewbox, ranges):
		self.update_volume_info()

	def update_volume_info(self):
		if self.binary_contact is None: return
		x_min, x_max, y_min, y_max = self.get_viewbox_ranges_int(shape=self.binary_contact.shape)
		px_um, py_um = self.pixel_um.x(), self.pixel_um.y()
		pixel_area_um2 = px_um * py_um
		fragment = self.binary_contact[y_min:y_max+1, x_min:x_max+1]
		white_count = np.count_nonzero(fragment)
		white_area_um2 = pixel_area_um2 * white_count
		white_area_mm2 = white_area_um2 * 1e-6
		diff = self.distance_map.m_grid64[y_min:y_max+1, x_min:x_max+1] - self.separation
		diff_masked = np.where(fragment, diff, 0)
		volume_um3 = np.abs(np.sum(diff_masked)) * pixel_area_um2
		volume_mm3 = volume_um3 * 1e-9
		self.statusBar().showMessage(
			f"Białe pola: {white_count}, area: {white_area_um2:.2f}µm² ({white_area_mm2:.4f}mm²), "
			f"volume: {volume_um3:.2f}µm³ ({volume_mm3:.4f}mm³)"
		)

	def get_viewbox_ranges_int(self, shape=None, overflow=False):
		vb = self.image_view.getView()
		(x0, x1), (y0, y1) = vb.viewRange()

		# Rogi w układzie widoku
		corners_view = [
			(x0, y0),
			(x0, y1),
			(x1, y0),
			(x1, y1)
		]

		# Przekształć do indeksów numpy
		coords_np = [self.view_to_numpy(x, y) for (x, y) in corners_view]
		rows = [r for r, c in coords_np]
		cols = [c for r, c in coords_np]

		r_min, r_max = min(rows), max(rows)
		c_min, c_max = min(cols), max(cols)

		# Przytnij do wymiarów siatki
		if shape is not None:
			h, w = shape
			r_min = max(0, r_min); r_max = min(h-1, r_max)
			c_min = max(0, c_min); c_max = min(w-1, c_max)

		return c_min, c_max, r_min, r_max  # x_min, x_max, y_min, y_max w logice numpy
