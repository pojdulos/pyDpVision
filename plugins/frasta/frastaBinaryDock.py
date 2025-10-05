import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
from skimage.draw import line
from dpVision import GridData64

import logging
logger = logging.getLogger(__name__)

def create_image_view():
	view = pg.ImageView()
	view.ui.histogram.hide()
	view.ui.roiBtn.hide()
	view.ui.menuBtn.hide()
	return view

def cohen_sutherland_clip(x0, y0, x1, y1, w, h):
	"""Clipping linii do prostokąta 0..w-1, 0..h-1."""
	INSIDE, LEFT, RIGHT, BOTTOM, TOP = 0, 1, 2, 4, 8

	def compute_out_code(x, y):
		code = INSIDE
		if x < 0:       code |= LEFT
		elif x > w-1:   code |= RIGHT
		if y < 0:       code |= BOTTOM
		elif y > h-1:   code |= TOP
		return code

	out_code0 = compute_out_code(x0, y0)
	out_code1 = compute_out_code(x1, y1)
	accept = False

	while True:
		if not (out_code0 | out_code1):
			accept = True
			break
		elif out_code0 & out_code1:
			break
		else:
			out_code_out = out_code0 or out_code1
			if out_code_out & TOP:
				x = x0 + (x1 - x0) * ((h-1 - y0) / (y1 - y0))
				y = h-1
			elif out_code_out & BOTTOM:
				x = x0 + (x1 - x0) * ((0 - y0) / (y1 - y0))
				y = 0
			elif out_code_out & RIGHT:
				y = y0 + (y1 - y0) * ((w-1 - x0) / (x1 - x0))
				x = w-1
			elif out_code_out & LEFT:
				y = y0 + (y1 - y0) * ((0 - x0) / (x1 - x0))
				x = 0

			if out_code_out == out_code0:
				x0, y0 = x, y
				out_code0 = compute_out_code(x0, y0)
			else:
				x1, y1 = x, y
				out_code1 = compute_out_code(x1, y1)

	if accept:
		return int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
	else:
		return None

class FrastaBinaryDock(QtWidgets.QDockWidget):
	profileLineChanged = QtCore.pyqtSignal(tuple)  # (c0, r0, c1, r1)
	quickMessage = QtCore.pyqtSignal(str)
	separationChanged = QtCore.pyqtSignal(int)

	def __init__(self, parent=None):
		super().__init__(parent)
		self.setWindowTitle("FRASTA Binary")
		self.setFloating(True)

		self.distance_map: GridData64 = None
		self.grid1: GridData64 = None
		self.grid2: GridData64 = None
		self.binary_contact = None
		self.pixel_um = QtCore.QPointF(1.0, 1.0)

		central = QtWidgets.QWidget()
		self.setWidget(central)
		layout = QtWidgets.QVBoxLayout(central)

		self.image_view = create_image_view()
		self.image_view.setMinimumWidth(400)
		layout.addWidget(self.image_view, 3)
		self.image_view.getView().sigRangeChanged.connect(self.on_range_changed)

		sep_layout = QtWidgets.QHBoxLayout()
		self._spinbox_separation = QtWidgets.QSpinBox()
		self._spinbox_separation.setRange(-5000, 5000)
		self._spinbox_separation.setValue(0)
		self._spinbox_separation.valueChanged.connect(self.update_plot)
		sep_layout.addWidget(QtWidgets.QLabel("Separation [µm]:"))
		sep_layout.addWidget(self._spinbox_separation)
		layout.addLayout(sep_layout)

		self.line_roi = None
		self.rr, self.cc = None, None
		self.saved_point_markers = []

	# property separation
	@property
	def separation(self):
		return self._spinbox_separation.value()

	@separation.setter
	def separation(self, _sep):
		self._spinbox_separation.setValue(_sep)

	def view_to_numpy(self, x_view, y_view, clip_to_shape=True):
		h, w = self._shape_np()  # h = rows, w = cols w oryginalnym numpy
		col = int(round(x_view))           # pozioma
		row = h - 1 - int(round(y_view))   # pionowa odwrócona
		if clip_to_shape:
			row = int(np.clip(row, 0, h-1))
			col = int(np.clip(col, 0, w-1))
		return row, col

	def _shape_np(self):
		h, w = self.distance_map.m_grid64.shape
		return h, w

	def numpy_to_view(self, row, col):
		h, w = self._shape_np()
		x_view = float(col)
		y_view = float(h - 1 - row)
		return x_view, y_view

	def get_roi_coords(self):
		if self.line_roi is None:
			return None, None
		handles = self.line_roi.getHandles()
		pt0 = self.line_roi.mapToParent(handles[0].pos())
		pt1 = self.line_roi.mapToParent(handles[1].pos())

		r0, c0 = self.view_to_numpy(pt0.x(), pt0.y(), clip_to_shape=False)
		r1, c1 = self.view_to_numpy(pt1.x(), pt1.y(), clip_to_shape=False)

		h, w = self.distance_map.m_grid64.shape
		clipped = cohen_sutherland_clip(c0, r0, c1, r1, w, h)
		if clipped is None:
			return None, None
		c0c, r0c, c1c, r1c = clipped
		return (r0c, c0c, r1c, c1c)

	def set_data(self, distance_map: GridData64, grid1: GridData64 = None, grid2: GridData64 = None):
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

	def update_plot(self):
		dist = self.distance_map.m_grid64
		valid = np.isfinite(dist)
		binary_contact = (dist > self.separation) & valid

		arr = binary_contact.astype(np.uint8)
		arr = arr.T[:, ::-1]
		self.image_view.setImage(arr, autoRange=False, autoLevels=True)

		self.binary_contact = binary_contact
		self.update_volume_info()
		self.separationChanged.emit(self.separation)

	def redraw_roi(self):
		if self.line_roi is not None:
			try:
				self.image_view.getView().removeItem(self.line_roi)
			except Exception:
				pass

		self.line_roi = pg.LineROI(
			[self.x1, self.y1],
			[self.x2, self.y2],
			pen=pg.mkPen('r', width=2),
			width=1
		)
		self.line_roi.handles[2]['type'] = 'center'
		self.line_roi.sigRegionChanged.connect(self._emit_profile_line)
		self._emit_profile_line()

		self.image_view.getView().addItem(self.line_roi)
		self.line_roi.setZValue(10)

	def _emit_profile_line(self):
		if self.line_roi is None:
			return
		
		r0, c0, r1, c1 = self.get_roi_coords()
		self.profileLineChanged.emit((c0, r0, c1, r1))

	def on_range_changed(self, viewbox, ranges):
		self.update_volume_info()

	def update_volume_info(self):
		if self.binary_contact is None:
			return

		# --- pobierz widoczny zakres z ViewBox ---
		vb = self.image_view.getView()
		(x0, x1), (y0, y1) = vb.viewRange()

		# współrzędne w widoku → współrzędne numpy
		r0, c0 = self.view_to_numpy(x0, y0)
		r1, c1 = self.view_to_numpy(x1, y1)

		# upewnij się, że min/max są poprawnie uporządkowane
		r_min, r_max = sorted((r0, r1))
		c_min, c_max = sorted((c0, c1))

		# przytnij do wymiarów
		h, w = self.binary_contact.shape
		r_min = np.clip(r_min, 0, h - 1)
		r_max = np.clip(r_max, 0, h - 1)
		c_min = np.clip(c_min, 0, w - 1)
		c_max = np.clip(c_max, 0, w - 1)

		# --- obliczenia jak wcześniej ---
		px_um, py_um = self.pixel_um.x(), self.pixel_um.y()
		pixel_area_um2 = px_um * py_um

		fragment = self.binary_contact[r_min:r_max+1, c_min:c_max+1]
		white_count = np.count_nonzero(fragment)
		white_area_um2 = pixel_area_um2 * white_count
		white_area_mm2 = white_area_um2 * 1e-6

		diff = self.distance_map.m_grid64[r_min:r_max+1, c_min:c_max+1] - self.separation
		diff_masked = np.where(fragment, diff, 0)
		volume_um3 = np.abs(np.sum(diff_masked)) * pixel_area_um2
		volume_mm3 = volume_um3 * 1e-9

		msg = (f"Białe pola: {white_count}, area: {white_area_um2:.2f}µm² ({white_area_mm2:.4f}mm²), "
			f"volume: {volume_um3:.2f}µm³ ({volume_mm3:.4f}mm³)")
		self.quickMessage.emit(msg)

	def clear_point_markers(self):
		for m in getattr(self, "saved_point_markers", []):
			self.image_view.getView().removeItem(m)
		self.saved_point_markers = []


	def on_profile_point_selected(self, row, col, val):
		x_img, y_img = self.numpy_to_view(row, col)
		marker = pg.ScatterPlotItem([x_img], [y_img], size=12,
									pen=pg.mkPen('g', width=2),
									brush=pg.mkBrush(0,255,255,120), symbol='+')
		self.image_view.getView().addItem(marker)
		self.saved_point_markers.append(marker)
		# opcjonalnie etykiety:
		# text = pg.TextItem(f"{val:.1f} µm", color='k', anchor=(0, 1.5))
		# text.setPos(x_img, y_img)
		# self.image_view.getView().addItem(text)
		# self.saved_point_markers.append(text)
