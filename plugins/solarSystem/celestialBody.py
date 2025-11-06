import numpy as np
from datetime import datetime

REAL_SIZE = True  # używaj rzeczywistych rozmiarów ciał niebieskich
ORBIT_SCALE = 100.0   # im większa wartość, tym planety dalej od Słońca

PLANET_SIZE_SCALE = 80000.0
SUN_SIZE_SCALE = 4000.0
MOON_SIZE_SCALE = 100000.0

# ================== stałe ==================
TWOPI = 2 * np.pi
DEG2RAD = np.pi / 180.0


# ================== funkcje pomocnicze ==================
def kepler_solve(M, e, iters=8):
    """Rozwiązuje równanie Keplera M = E - e*sin(E) dla danej średniej anomalii M."""
    E = M if e < 0.8 else np.pi
    for _ in range(iters):
        E -= (E - e * np.sin(E) - M) / (1 - e * np.cos(E))
    return E



def years_since_j2000(date: datetime) -> float:
    """Zwraca liczbę lat od epoki J2000.0 dla dowolnej daty."""
    J2000 = datetime(2000, 1, 1, 12)
    delta_days = (date - J2000).total_seconds() / 86400.0
    return delta_days / 365.25


# Stała grawitacji Newtona [m³ / (kg·s²)]
G = 6.67430e-11

class CelestialBody:
    """
    Ogólna klasa dla ciał niebieskich (Słońce, planety, księżyce).
    Przechowuje podstawowe dane opisowe i fizyczne.
    """
    def __init__(self, name, color, size, parent=None, **kwargs):
        self.name = name
        self.color = color
        
        if REAL_SIZE:
            self.size = kwargs['radius_AU'] * SUN_SIZE_SCALE
        else:
            self.size = size  # rozmiar wizualny (piksele, nie fizyczny)
        
        self.parent:CelestialBody = parent
        self.children = []

        # Zapisz wszystkie dodatkowe parametry (masa, promień itd.)
        self.params = kwargs
        for k, v in kwargs.items():
            setattr(self, k, v)

        if parent:
            parent.children.append(self)

    def position(self, t):
        """Pozycja w przestrzeni (domyślnie [0,0,0] np. dla Słońca)."""
        return np.zeros(3)

    def visual_position(self, t, position_gain=1.0):
        """
        Zwraca pozycję w jednostkach wizualnych (np. sceny 3D).
        Domyślnie używa funkcji position(t) i przeskalowuje wynik.
        """
        return self.position(t) * position_gain
    

    # ----------------------------------------------------------------
    # === METODY FIZYCZNE ===
    # ----------------------------------------------------------------
    def gravity_surface(self):
        """
        Zwraca przyspieszenie grawitacyjne [m/s²] na powierzchni ciała.
        g = G * M / R²
        M - masa w [kg], R - promień w [m]
        """
        if not hasattr(self, 'mass_kg') or not hasattr(self, 'radius_km'):
            return None  # brak danych
        R = self.radius_km * 1000.0
        return G * self.mass_kg / (R * R)

    def escape_velocity(self):
        """
        Zwraca prędkość ucieczki [m/s] z powierzchni ciała.
        v = sqrt(2 * G * M / R)
        """
        if not hasattr(self, 'mass_kg') or not hasattr(self, 'radius_km'):
            return None
        R = self.radius_km * 1000.0
        return np.sqrt(2 * G * self.mass_kg / R)

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.name}>"


