from .celestialBody import MOON_SIZE_SCALE, ORBIT_SCALE, REAL_SIZE, CelestialBody
import numpy as np

def rotate_z(vec, angle_deg):
	a = np.deg2rad(angle_deg)
	ca, sa = np.cos(a), np.sin(a)
	x, y, z = vec
	return np.array([ca*x - sa*y, sa*x + ca*y, z])

def rotate_x(vec, angle_deg):
	a = np.deg2rad(angle_deg)
	ca, sa = np.cos(a), np.sin(a)
	x, y, z = vec
	return np.array([x, ca*y - sa*z, sa*y + ca*z])

class Moon(CelestialBody):
	"""
	Księżyc orbitujący wokół planety.
	"""
	def __init__(self, parent, name, color, size, d, p,
				phase_deg=0.0, incl_eq_deg=0.0, node_eq_deg=0.0,
				radius_km=None, mass_kg=None, **kwargs):
		"""
		d           - średnia odległość od planety [AU]
		p           - okres orbitalny (w latach)
		phase_deg   - przesunięcie fazowe orbity (żeby księżyce nie nakładały się)
		incl_eq_deg - nachylenie orbity względem równika planety
		node_eq_deg - orientacja orbity względem równika planety
		"""
		super().__init__(name=name, color=color, size=size, parent=parent,
						radius_km=radius_km, mass_kg=mass_kg, **kwargs)

		if REAL_SIZE:
			self.size = kwargs['radius_AU'] * MOON_SIZE_SCALE
			if self.name in ("Phobos", "Deimos"):
				self.size*=100.0  # tymczasowy hack dla Marsjanskich księżyców
		else:
			self.size = size  # rozmiar wizualny (piksele, nie fizyczny)

		self.d = d
		self.p = p

		self.phase_deg   = phase_deg
		self.incl_eq_deg = incl_eq_deg
		self.node_eq_deg = node_eq_deg

	def position(self, t):
		"""Pozycja księżyca względem Słońca."""
		M = (t / self.p) * 2 * np.pi
		x_local = self.d * np.cos(M)
		y_local = self.d * np.sin(M)
		pos = np.array([x_local, y_local, 0])
		#return self.parent.position(t) + pos
		return pos


	def position_relative(self, t):
		"""
		Pozycja księżyca względem planety [AU], w płaszczyźnie równika planety,
		zorientowanej jak na J2000: najpierw definiujemy orbitę w układzie
		równikowym planety (node_eq, incl_eq), a potem osadzamy tę płaszczyznę
		w ekliptyce obrotami: spin_node_deg (wokół Z), obliquity_deg (wokół X).
		"""
		# 1) Orbita kołowa w lokalnym XY (początkowo w płaszczyźnie równika)
		M = (t / self.p) * 2 * np.pi + np.deg2rad(self.phase_deg)
		
		#local = np.array([self.d * np.cos(M), self.d * np.sin(M), 0.0])
		e = getattr(self, 'eccentricity', 0.0)   # new parameter
		a = self.d                                # semimajor axis [AU]

		# Rozwiąż równanie Keplera (M = E - e*sin(E))
		E = M
		for _ in range(5):
			E = M + e * np.sin(E)

		x = a * (np.cos(E) - e)
		y = a * np.sqrt(1 - e*e) * np.sin(E)
		local = np.array([x, y, 0.0])

		# 2) Własne nachylenie orbity względem równika planety (opcjonalne)
		if abs(self.incl_eq_deg) > 1e-9 or abs(self.node_eq_deg) > 1e-9:
			local = rotate_z(local, self.node_eq_deg)
			local = rotate_x(local, self.incl_eq_deg)

		# 🔥 3) Precesja węzłów orbity księżyca (18.6 lat)
		# Współczynnik:
		# węzeł orbity Księżyca cofa się ~19.3549° w ciągu 18.6 lat
		# czyli ~ -1.04° na rok
		dOmega_dt = -19.3549 / 18.6  # stopni/rok
		node_prec = dOmega_dt * t     # zależność od epoki (t = lata od J2000)
		local = rotate_z(local, node_prec)

		# 4) Osadzenie równika planety w ekliptyce:
		spin_node = getattr(self.parent, 'spin_node_deg', 0.0)
		obliq     = getattr(self.parent, 'obliquity_deg', 0.0)
		local = rotate_z(local, spin_node)
		local = rotate_x(local, obliq)

		return local
	
	def position_visual_relative(self, t):
		"""
		Wizualna pozycja księżyca względem planety,
		wykorzystuje rozmiar wizualny planety, a nie radius_AU,
		dzięki czemu księżyc jest zawsze 'nad powierzchnią' planety.
		"""
		# 1) fizyczna orbita w AU
		rel = self.position_relative(t)

		# 2) przeskalowanie odległości orbit do sceny
		if REAL_SIZE:
			rel_display = rel * ORBIT_SCALE
		else:
			rel_display = rel.copy()

		# 3) obliczamy bezpieczną odległość na podstawie
		#    TEGO SAMEGO rozmiaru, którego używamy do rysowania planety
		planet_visual_radius = self.parent.size
		safe_offset = planet_visual_radius * 2.0  # 1.3–2.0 działa świetnie

		# aktualny dystans księżyca
		r = np.linalg.norm(rel_display)

		# jeśli księżyc „wpada” do planety → odsuwamy go
		if r < safe_offset:
			if r > 0:
				rel_display = rel_display * (safe_offset / r)

		return rel_display


	def visual_position(self, t):
		planet_pos_au = self.parent.position(t)
		moon_rel_au = self.position_relative(t)

		pos_au = planet_pos_au + moon_rel_au

		if REAL_SIZE:
			return pos_au * ORBIT_SCALE
		else:
			return pos_au
