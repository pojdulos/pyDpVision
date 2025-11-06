from .celestialBody import PLANET_SIZE_SCALE, CelestialBody, REAL_SIZE, ORBIT_SCALE, DEG2RAD
from .moon import Moon
import numpy as np

def rotate_z_x(vec, arg_peri_deg, inc_deg, Omega_deg=0.0):
	"""Rotacja 3D: Rz(Omega) * Rx(inc) * Rz(argPeri)."""
	Ω = Omega_deg * DEG2RAD
	ω = arg_peri_deg * DEG2RAD
	i = inc_deg * DEG2RAD

	cO, sO = np.cos(Ω), np.sin(Ω)
	cI, sI = np.cos(i), np.sin(i)
	cW, sW = np.cos(ω), np.sin(ω)

	R = np.array([
		[cO*cW - sO*sW*cI, -cO*sW - sO*cW*cI, sO*sI],
		[sO*cW + cO*sW*cI, -sO*sW + cO*cW*cI, -cO*sI],
		[sW*sI, cW*sI, cI]
	])

	return R @ vec


class Planet(CelestialBody):
	"""
	Planeta w układzie heliocentrycznym — dziedziczy dane fizyczne
	i dodaje model Keplerowski ruchu orbitalnego.
	"""
	def __init__(self, name, color, size, a, e, p, inc, argPeri,
				meanAnomaly0=0.0, Omega=0.0, epoch=2000.0,
				moons=None, parent=None, **kwargs):
		super().__init__(name, color, size, parent,
						a=a, e=e, p=p, inc=inc, argPeri=argPeri,
						meanAnomaly0=meanAnomaly0, Omega=Omega,
						epoch=epoch, **kwargs)

		if REAL_SIZE:
			self.size = kwargs['radius_AU'] * PLANET_SIZE_SCALE
		else:
			self.size = size  # rozmiar wizualny (piksele, nie fizyczny)


		self.a = a        # półoś wielka [AU]
		self.e = e        # mimośród
		self.p = p        # okres orbitalny [lata]
		self.inc = inc    # inklinacja [°]
		self.argPeri = argPeri
		self.meanAnomaly0 = meanAnomaly0
		self.Omega = Omega
		self.epoch = epoch

		self.moons = []
		if moons:
			for i, m in enumerate(moons):
				m.setdefault('phase_deg', i * (360.0 / max(1, len(moons))))
				self.moons.append(Moon(parent=self, **m))

	def position(self, t):
		"""
		Zwraca fizyczną pozycję planety w AU względem Słońca.
		Bez skalowania wizualnego.
		"""
		n = 2 * np.pi / self.p
		M = (t - (self.epoch - 2000.0)) * n + np.deg2rad(self.meanAnomaly0)

		# Kepler
		E = M
		for _ in range(6):
			E -= (E - self.e*np.sin(E) - M) / (1 - self.e*np.cos(E))

		a = self.a
		b = a * np.sqrt(1 - self.e*self.e)

		x_local = a * np.cos(E) - a*self.e
		y_local = b * np.sin(E)

		pos = rotate_z_x(np.array([x_local, y_local, 0]),
						self.argPeri, self.inc, self.Omega)

		center = np.zeros(3) if self.parent is None else self.parent.position(t)
		return center + pos  # <- zawsze AU

	def visual_position(self, t):
		"""
		Pozycja planety w jednostkach sceny (skalowana).
		"""
		pos_au = self.position(t)

		if REAL_SIZE:
			return pos_au * ORBIT_SCALE  # duże rozciągnięcie orbit
		else:
			return pos_au  # 1:1 (przydatne do testów)
	
	# --------------------------------------------------------
	#  🔵 Nowa metoda: generowanie punktów orbity
	# --------------------------------------------------------
	def orbit_points(self, n_points=200, centered=True):
		"""
		Generuje listę punktów (x, y, z) [AU] opisujących orbitę planety.

		Parameters
		----------
		n_points : int
			liczba punktów na elipsie (domyślnie 200)
		centered : bool
			True  – elipsa z ogniskiem w (0,0,0) → fizyczna orbita względem Słońca
			False – elipsa centrowana geometrycznie → wizualne rysowanie

		Returns
		-------
		np.ndarray : tablica kształtu (n_points, 3)
		"""
		a, e = self.a, self.e
		b = a * np.sqrt(1 - e * e)
		E_vals = np.linspace(0, 2*np.pi, n_points)
		focus_offset = a * e if centered else 0.0

		pts = []
		for E in E_vals:
			x = a * np.cos(E) - focus_offset
			y = b * np.sin(E)
			z = 0
			p_rot = rotate_z_x(np.array([x, y, z]),
							self.argPeri, self.inc, self.Omega)

			if REAL_SIZE:
				p_rot *= ORBIT_SCALE

			pts.append(p_rot)
		return np.array(pts)
