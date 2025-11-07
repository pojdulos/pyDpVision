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
	def __init__(self, parent, name, color, size, d, p,
				 phase_deg=0.0, incl_eq_deg=0.0, node_eq_deg=0.0,
				 radius_km=None, mass_kg=None, **kwargs):

		kwargs.setdefault('body_type', 'moon')

		super().__init__(name=name, color=color, size=size, parent=parent,
						 radius_km=radius_km, mass_kg=mass_kg, **kwargs)

		# parametry orbity
		self.d = d              # średnia odległość [AU]
		self.p = p              # okres orbitalny [lata]
		self.phase_deg   = phase_deg
		self.incl_eq_deg = incl_eq_deg
		self.node_eq_deg = node_eq_deg


	def position_relative(self, t):
		M = (t / self.p) * 2 * np.pi + np.deg2rad(self.phase_deg)

		e = getattr(self, 'eccentricity', 0.0)
		a = self.d

		E = M
		for _ in range(5):
			E = M + e * np.sin(E)

		x = a * (np.cos(E) - e)
		y = a * np.sqrt(1 - e*e) * np.sin(E)
		local = np.array([x, y, 0.0])

		if abs(self.incl_eq_deg) > 1e-9 or abs(self.node_eq_deg) > 1e-9:
			local = rotate_z(local, self.node_eq_deg)
			local = rotate_x(local, self.incl_eq_deg)

		dOmega_dt = -19.3549 / 18.6
		node_prec = dOmega_dt * t
		local = rotate_z(local, node_prec)

		spin_node = getattr(self.parent, 'spin_node_deg', 0.0)
		obliq     = getattr(self.parent, 'obliquity_deg', 0.0)
		local = rotate_z(local, spin_node)
		local = rotate_x(local, obliq)

		return local

	def position_visual_relative2(self, t):
		rel = self.position_relative(t)

		base = ORBIT_SCALE if REAL_SIZE else 1.0
		rel_display = rel * base

		# --- NEW: uwzględnij pierścienie (jeśli są) ---
		planet_surface = self.parent.visual_radius()
		ring_outer = getattr(self.parent, "ring_outer_visual", None)

		if ring_outer is not None:
			safe_radius = max(planet_surface, ring_outer)
		else:
			safe_radius = planet_surface

		safe_radius *= 1.05  # odrobinka powietrza, ale bez odrywania od planety

		r = np.linalg.norm(rel_display)
		if r < safe_radius and r > 0:
			rel_display = rel_display * (safe_radius / r)

		return rel_display

	def position_visual_relative(self, t):
		# 1) fizyczna orbita względem planety (AU)
		rel = self.position_relative(t)

		# 2) bazowa konwersja AU → scena
		base = ORBIT_SCALE if REAL_SIZE else 1.0
		rel_visual = rel * base

		# 3) Wyznacz promień bezpieczeństwa = planeta + pierścienie + księżyc
		planet_R = self.parent.visual_radius()
		moon_R   = self.visual_radius()
		ring_R   = getattr(self.parent, "ring_outer_visual", 0.0) or 0.0

		safe_radius = max(planet_R + moon_R, ring_R + moon_R)

		# 4) Jeśli ta planeta ma wiele księżyców → znajdź minimalną orbitę
		d_min = getattr(self.parent, 'moon_min_d', None)
		if d_min is None or d_min <= 0:
			return rel_visual

		d_min_visual = d_min * base

		# 5) Jeśli najbliższy księżyc byłby za blisko → oblicz skalowanie
		# Skala musi wynosić 1.0 gdy księżyc jest wystarczająco daleko
		scale = max(1.0, safe_radius / d_min_visual)

		# 6) Płynnie podnosimy do ALPHA → lepsza kontrola wyglądu
		ALPHAS = {
			"Ziemia":1.1,
			"Mars":1.1, 
			"Jowisz":1.1, 
			"Saturn":1.1,
			"Uran":1.1,
			"Neptun":1.1,
			"Pluton":1.1
		}
		
		alpha = ALPHAS.get(self.parent.name, 1.0)

		scale = scale ** alpha

		return rel_visual * scale
	

	def visual_position(self, t):
		return self.parent.visual_position(t) + self.position_visual_relative(t)

	def orbit_points_visual(self, n_points=200, t=0.0):
		"""
		Zwraca punkty orbity księżyca w jednostkach sceny,
		ale *względem planety*, gotowe do dodania jako dziecko Transform planety.
		"""
		pts = []
		for k in range(n_points):
			tt = t + (k / n_points) * self.p    # przebieg orbity
			rel = self.position_visual_relative(tt)
			pts.append(rel)
		return np.array(pts)
