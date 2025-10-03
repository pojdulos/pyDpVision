import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore

from .frastaBinaryDock import FrastaBinaryDock
from .frastaProfileDock import FrastaProfileDock
from dpVision import GridData64

import logging
logger = logging.getLogger(__name__)

class FrastaController(QtCore.QObject):
	pointSelected = QtCore.pyqtSignal(int, int, float)

	def __init__(self, parent=None):
		super().__init__(parent)
		self.binary_dock = FrastaBinaryDock()
		self.profile_dock = FrastaProfileDock()

		# sygnały
		self.binary_dock.profileLineChanged.connect(self.on_profileLineChanged)
		self.profile_dock.pointClicked.connect(self.on_profile_point_clicked)
		
		self.pointSelected.connect(self.binary_dock.on_profile_point_selected)

	def set_data(self, distance_map: GridData64, grid1: GridData64=None, grid2: GridData64=None):
		self.binary_dock.set_data(distance_map, grid1, grid2)

	@QtCore.pyqtSlot(tuple)
	def on_profileLineChanged(self, krotka):
		c0, r0, c1, r1 = krotka # to jest już w układzie numpy !

		# length_pix = int(round(np.hypot(r1 - r0, c1 - c0)))
		# rr = np.linspace(r0, r1, num=length_pix+1, dtype=int)
		# cc = np.linspace(c0, c1, num=length_pix+1, dtype=int)
		from skimage.draw import line
		rr, cc = line(r0, c0, r1, c1)

		# rr, cc = np.linspace(r0, r1, num=200, dtype=int), np.linspace(c0, c1, num=200, dtype=int)

		self.current_rr = rr
		self.current_cc = cc

		prof_dist = self.binary_dock.distance_map.m_grid64[rr, cc]
		valid = np.isfinite(prof_dist)
		profiles = []
		if self.binary_dock.grid1 is not None and self.binary_dock.grid2 is not None:
			prof1 = self.binary_dock.grid1.m_grid64[rr, cc]
			prof2 = self.binary_dock.grid2.m_grid64[rr, cc] + self.binary_dock.separation
			valid &= np.isfinite(prof1) & np.isfinite(prof2)
			profiles.append(("Ref", prof1[valid], pg.mkPen('g', width=2)))
			profiles.append(("Adj", prof2[valid], pg.mkPen('b', width=2)))

		# positions_line = np.arange(len(rr))[valid] * self.binary_dock.distance_map.stepX
		xs = rr * self.binary_dock.distance_map.stepY + self.binary_dock.distance_map.offsetY
		ys = cc * self.binary_dock.distance_map.stepX + self.binary_dock.distance_map.offsetX
		# odległości wzdłuż linii
		positions_line = np.hypot(xs - xs[0], ys - ys[0])

		prof_dist = prof_dist[valid]
		self.profile_dock.set_profiles(positions_line, profiles, prof_dist)



	def on_profile_point_clicked(self, idx:int):
		"""Obsługa kliknięcia punktu na wykresie."""
		if self.current_rr is None or self.current_cc is None:
			return

		if idx < 0 or idx >= len(self.current_rr):
			return

		# numpy indices
		r, c = int(self.current_rr[idx]), int(self.current_cc[idx])

		# wartość z mapy odległości (albo Ref/Adj jak wolisz)
		val = float(self.binary_dock.distance_map.m_grid64[r, c])

		# emit spójnych współrzędnych w numpy
		self.pointSelected.emit(r, c, val)

		logger.debug(f"Wybrano punkt: row={r}, col={c}, val={val:.2f}")
