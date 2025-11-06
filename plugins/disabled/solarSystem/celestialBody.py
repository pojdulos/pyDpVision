import numpy as np
from datetime import datetime

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


# class Planet(CelestialBody):
#     """
#     Planeta w układzie heliocentrycznym — dziedziczy dane fizyczne
#     i dodaje model Keplerowski ruchu orbitalnego.
#     """
#     def __init__(self, name, color, size, a, e, p, inc, argPeri,
#                  meanAnomaly0=0.0, Omega=0.0, epoch=2000.0,
#                  moons=None, parent=None, **kwargs):
#         super().__init__(name, color, size, parent,
#                          a=a, e=e, p=p, inc=inc, argPeri=argPeri,
#                          meanAnomaly0=meanAnomaly0, Omega=Omega,
#                          epoch=epoch, **kwargs)

#         self.a = a        # półoś wielka [AU]
#         self.e = e        # mimośród orbity
#         self.p = p        # okres orbitalny [lata ziemskie]
#         self.inc = inc    # inklinacja [°]
#         self.argPeri = argPeri
#         self.meanAnomaly0 = meanAnomaly0
#         self.Omega = Omega
#         self.epoch = epoch

#         # Księżyce (jeśli są)
#         self.moons = []
#         if moons:
#             for m in moons:
#                 self.moons.append(Moon(parent=self, **m))

#     def position(self, t):
#         """
#         Oblicza pozycję planety względem Słońca w AU.
#         Wykorzystuje równanie Keplera M = E - e*sin(E).
#         """
#         n = 2 * np.pi / self.p             # średni ruch [rad/rok]
#         M = (t - (self.epoch - 2000.0)) * n + np.deg2rad(self.meanAnomaly0)
#         E = M
#         for _ in range(6):                 # iteracyjne rozwiązanie Keplera
#             E -= (E - self.e * np.sin(E) - M) / (1 - self.e * np.cos(E))
#         a, e = self.a, self.e
#         b = a * np.sqrt(1 - e * e)
#         x_local = a * np.cos(E) - a * e
#         y_local = b * np.sin(E)
#         pos = rotate_z_x(np.array([x_local, y_local, 0]),
#                          self.argPeri, self.inc, self.Omega)
#         center = np.zeros(3) if not self.parent else self.parent.position(t)
#         return center + pos

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
            for m in moons:
                self.moons.append(Moon(parent=self, **m))

    def position(self, t):
        """
        Oblicza pozycję planety względem Słońca w AU.
        """
        n = 2 * np.pi / self.p
        M = (t - (self.epoch - 2000.0)) * n + np.deg2rad(self.meanAnomaly0)
        E = M
        for _ in range(6):  # iteracyjne rozwiązanie Keplera
            E -= (E - self.e * np.sin(E) - M) / (1 - self.e * np.cos(E))

        a, e = self.a, self.e
        b = a * np.sqrt(1 - e * e)
        x_local = a * np.cos(E) - (a * e if True else 0)
        y_local = b * np.sin(E)
        pos = rotate_z_x(np.array([x_local, y_local, 0]),
                         self.argPeri, self.inc, self.Omega)
        center = np.zeros(3) if not self.parent else self.parent.position(t)
        return center + pos

    def visual_position(self, t, position_gain=1.0):
        """
        Pozycja planety w scenie wizualnej (heliocentryczna).
        Planety nie mają dodatkowego powiększenia.
        """
        pos = self.position(t)
        return pos * position_gain
    
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
            pts.append(p_rot)
        return np.array(pts)


class Moon(CelestialBody):
    """
    Księżyc orbitujący wokół planety.
    """
    def __init__(self, name, color, size, d, p, parent, **kwargs):
        super().__init__(name, color, size, parent, d=d, p=p, **kwargs)
        self.d = d  # średnia odległość od planety [AU]
        self.p = p  # okres orbitalny [lata]

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
        Pozycja księżyca względem planety [AU].
        Obrót odbywa się tylko w lokalnym układzie planety,
        bez przenoszenia jej orientacji heliocentrycznej.
        """
        M = (t / self.p) * 2 * np.pi
        x = self.d * np.cos(M)
        y = self.d * np.sin(M)
        return np.array([x, y, 0])

    def visual_position(self, t, position_gain=1.0, moon_orbit_gain = 100.0):
        """
        Pozycja wizualna księżyca względem sceny.
        Używa pozycji planety w układzie heliocentrycznym
        + lokalnej orbity księżyca wokół planety.
        """
        planet_pos = self.parent.position(t)
        rel = self.position_relative(t)

        return (planet_pos + rel * moon_orbit_gain) * position_gain
    