import math
import numpy as np
from scipy.spatial.transform import Rotation
from .transform import Transform

def Rz_mat_rad(theta_rad):
    c = math.cos(theta_rad); s = math.sin(theta_rad)
    M = np.eye(4, dtype=np.float64)
    M[:3,:3] = np.array([[c, -s, 0.],
                         [s,  c, 0.],
                         [0., 0., 1.]])
    return M

def Rx_mat_rad(alpha_rad):
    c = math.cos(alpha_rad); s = math.sin(alpha_rad)
    M = np.eye(4, dtype=np.float64)
    M[:3,:3] = np.array([[1., 0.,  0.],
                         [0., c, -s],
                         [0., s,  c]])
    return M

def Tz_mat(d):
    M = np.eye(4, dtype=np.float64)
    M[2,3] = d
    return M

def Tx_mat(a):
    M = np.eye(4, dtype=np.float64)
    M[0,3] = a
    return M

class DHJoint(Transform):
    """
    Joint opisany parametrami DH (classical):
      local = Rz(theta) @ Tz(d) @ Tx(a) @ Rx(alpha)

    Domyślnie theta i d mogą być zmienne (sterowane).
    """

    def __init__(self, theta_deg=0.0, d=0.0, a=0.0, alpha_deg=0.0,
                 theta_variable=True, d_variable=False,
                 parent=None, name=None):
        # zainicjuj Transform bez macierzy; Transform.__init__ ustawi identity
        super().__init__(matrix=None, parent=parent)

        # przechowuj wewnętrznie w radianach
        self.theta = math.radians(theta_deg)
        self.d = float(d)
        self.a = float(a)
        self.alpha = math.radians(alpha_deg)

        self.theta_variable = bool(theta_variable)
        self.d_variable = bool(d_variable)

        if name is not None:
            try:
                self.name = name
            except Exception:
                pass

        # ustaw macierz lokalną zgodnie z DH
        self.updateMatrix()

    # nadpisujemy updateMatrix tak, by ustawić macierz zgodnie z DH
    def updateMatrix(self):
        # classical DH: Rz(theta) * Tz(d) * Tx(a) * Rx(alpha)
        M = Rz_mat_rad(self.theta) @ Tz_mat(self.d) @ Tx_mat(self.a) @ Rx_mat_rad(self.alpha)
        # korzystamy z fromNumPy, aby w Transform poprawnie rozbić translację/rotację/skale
        # fromNumPy ustawi self.matrix, self.m_translation, self.m_rotation, self.m_scale
        self.fromNumPy(M)
        # nie wywołujemy Transform.updateMatrix(), bo tam budowane jest T*R*S z pól TRS (a my mamy już macierz)
        # jeśli chcesz wymusić odświeżenie potomków, możesz (w zależności od Object/scene) wysłać sygnał lub nie

    # settery/utility
    def set_theta_deg(self, val_deg):
        self.theta = math.radians(float(val_deg))
        self.updateMatrix()

    def set_theta_rad(self, val_rad):
        self.theta = float(val_rad)
        self.updateMatrix()

    def set_d(self, val):
        self.d = float(val)
        self.updateMatrix()

    def set_a(self, val):
        self.a = float(val)
        self.updateMatrix()

    def set_alpha_deg(self, val_deg):
        self.alpha = math.radians(float(val_deg))
        self.updateMatrix()

    def set_alpha_rad(self, val_rad):
        self.alpha = float(val_rad)
        self.updateMatrix()

    def get_theta_deg(self):
        return math.degrees(self.theta)

    def get_alpha_deg(self):
        return math.degrees(self.alpha)

    def to_dh_row(self, degrees=True):
        """Zwraca słownik z parametrami DH."""
        if degrees:
            return {'theta': self.get_theta_deg(), 'd': self.d, 'a': self.a, 'alpha': self.get_alpha_deg()}
        else:
            return {'theta': self.theta, 'd': self.d, 'a': self.a, 'alpha': self.alpha}

    def set_from_dh_row(self, row, degrees=True):
        """Ustawia parametry z wiersza DH (słownika)."""
        if degrees:
            self.theta = math.radians(float(row.get('theta', math.degrees(self.theta))))
            self.alpha = math.radians(float(row.get('alpha', math.degrees(self.alpha))))
        else:
            self.theta = float(row.get('theta', self.theta))
            self.alpha = float(row.get('alpha', self.alpha))
        self.d = float(row.get('d', self.d))
        self.a = float(row.get('a', self.a))
        self.updateMatrix()

    # pomocnicze - punkt origin i oś Z jointu w układzie świata
    def origin_world(self):
        G = self.getGlobalTransformation()
        return G[:3, 3].copy()

    def z_axis_world(self):
        G = self.getGlobalTransformation()
        return G[:3, :3] @ np.array([0., 0., 1.])

    # konwersja do formatu fixed_offset + axis (przydatne do URDF / integracji)
    def to_fixed_offset_and_axis(self):
        """
        Zwraca (fixed_offset, axis) - fixed_offset (4x4) = Tz(d) @ Tx(a) @ Rx(alpha)
        axis = local Z = [0,0,1] (w lokalnej ramce)
        i q = theta (zmienna)
        """
        fixed = Tz_mat(self.d) @ Tx_mat(self.a) @ Rx_mat_rad(self.alpha)
        axis = np.array([0., 0., 1.])
        return fixed, axis

