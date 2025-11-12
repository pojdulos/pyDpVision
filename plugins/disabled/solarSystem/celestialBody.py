import numpy as np
from datetime import datetime

REAL_SIZE = True
# mnożniki z wymiarów w AU na jednostki sceny
ORBIT_SCALE = 250.0 #100.0
SUN_SIZE_SCALE = 10000.0
PLANET_SIZE_SCALE = 80000.0
MOON_SIZE_SCALE = 100000.0

TWOPI = 2 * np.pi
DEG2RAD = np.pi / 180.0
G = 6.67430e-11


def kepler_solve(M, e, iters=8):
    E = M if e < 0.8 else np.pi
    for _ in range(iters):
        E -= (E - e*np.sin(E) - M) / (1 - e*np.cos(E))
    return E


def years_since_j2000(date: datetime) -> float:
    J2000 = datetime(2000, 1, 1, 12)
    delta_days = (date - J2000).total_seconds() / 86400.0
    return delta_days / 365.25


class CelestialBody:
    def __init__(self, name, color, size, parent=None, body_type='planet', **kwargs):
        self.name : str = name
        self.color : str = color
        self.size : float = size
        self.body_type : str = body_type
        self.parent : CelestialBody = parent
        self.children : list[CelestialBody] = []

        for k, v in kwargs.items():
            setattr(self, k, v)

        if parent:
            parent.children.append(self)

    def position(self, t):
        return np.zeros(3)

    def visual_radius(self):
        if not REAL_SIZE:
            return self.size

        r_au = getattr(self, 'radius_AU', None)
        if r_au is None:
            return self.size

        if self.body_type == 'sun':
            scale = SUN_SIZE_SCALE
        elif self.body_type == 'moon':
            scale = MOON_SIZE_SCALE
        else:
            scale = PLANET_SIZE_SCALE

        return max(r_au * scale, 0.3) # żeby nie zniknęło całkiem

    def visual_position(self, t):
        pos_au = self.position(t)
        return pos_au * ORBIT_SCALE if REAL_SIZE else pos_au

    def gravity_surface(self):
        if not hasattr(self, 'mass_kg') or not hasattr(self, 'radius_km'):
            return None
        R = self.radius_km * 1000.0
        return G * self.mass_kg / (R*R)

    def escape_velocity(self):
        if not hasattr(self, 'mass_kg') or not hasattr(self, 'radius_km'):
            return None
        R = self.radius_km * 1000.0
        return np.sqrt(2 * G * self.mass_kg / R)

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.name}>"
