import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore

from .frastaBinaryDock import FrastaBinaryDock
from .frastaProfileDock import FrastaProfileDock
from dpVision import GridData64

import logging
logger = logging.getLogger(__name__)

class FrastaController(QtCore.QObject):
	pointSelected = QtCore.pyqtSignal(int, int)

	def __init__(self, parent=None):
		super().__init__(parent)
		self.binary_dock = FrastaBinaryDock()
		self.profile_dock = FrastaProfileDock()

		# sygnały
		self.binary_dock.profileLineChanged.connect(self.on_profileLineChanged)
		self.binary_dock.separationChanged.connect(self.on_binary_separation_valueChanged)

		self.profile_dock.profilePointSelected.connect(self.on_profilePointSelected)
		
		self.pointSelected.connect(self.binary_dock.on_pointSelected)
		
	def set_data(self, distance_map: GridData64, grid1: GridData64=None, grid2: GridData64=None):
		self.binary_dock.set_data(distance_map, grid1, grid2)


	def set_profile(self):
		prof_dist = self.binary_dock.distance_map.m_grid64[self.current_rr, self.current_cc]
		valid = np.isfinite(prof_dist)

		profiles = []
		if self.binary_dock.grid1 is not None and self.binary_dock.grid2 is not None:
			prof1 = self.binary_dock.grid1.m_grid64[self.current_rr, self.current_cc]
			prof2 = self.binary_dock.grid2.m_grid64[self.current_rr, self.current_cc] + self.binary_dock.separation
			valid &= np.isfinite(prof1) & np.isfinite(prof2)
			profiles.append(("Ref", prof1[valid], pg.mkPen('g', width=2)))
			profiles.append(("Adj", prof2[valid], pg.mkPen('b', width=2)))

		# współrzędne w przestrzeni
		xs = self.current_rr * self.binary_dock.distance_map.stepY + self.binary_dock.distance_map.offsetY
		ys = self.current_cc * self.binary_dock.distance_map.stepX + self.binary_dock.distance_map.offsetX

		# zastosowanie maski
		xs, ys = xs[valid], ys[valid]

		# odległości wzdłuż linii
		positions_line = np.hypot(xs - xs[0], ys - ys[0])
		prof_dist = prof_dist[valid]

		assert len(positions_line) == len(prof_dist)

		self.profile_dock.set_profiles(positions_line, profiles, prof_dist,
									separation=self.binary_dock.separation)

	@QtCore.pyqtSlot(tuple)
	def on_profileLineChanged(self, krotka):
		c0, r0, c1, r1 = krotka # to jest już w układzie numpy !

		# length_pix = int(round(np.hypot(r1 - r0, c1 - c0)))
		# rr = np.linspace(r0, r1, num=length_pix+1, dtype=int)
		# cc = np.linspace(c0, c1, num=length_pix+1, dtype=int)
		from skimage.draw import line
		rr, cc = line(r0, c0, r1, c1)

		self.current_rr = rr
		self.current_cc = cc

		self.set_profile()


	def on_profilePointSelected(self, idx:int):
		""" Obsługa kliknięcia punktu na wykresie.
			Zamienia indeks punktu na profilu na współrzedne
			w układzie siatki i emituje sygnał z tymi współrzednymi """
		if self.current_rr is None or self.current_cc is None:
			return
		if idx < 0 or idx >= len(self.current_rr):
			return
		r, c = int(self.current_rr[idx]), int(self.current_cc[idx])
		# logger.debug(f"Wybrano punkt: row={r}, col={c}")
		self.pointSelected.emit(r, c)


	def on_binary_separation_valueChanged(self, v):
		self.set_profile()
