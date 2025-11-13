import math
import numpy as np
from scipy.spatial.transform import Rotation
from OpenGL import GL as gl
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

        self.alpha_limits = [-180.0, 180.0]  # domyślne ograniczenia kątów w stopniach
        self.theta_limits = [-180.0, 180.0]  # domyślne ograniczenia kątów w stopniach
        self.a_limits = [0.0, 100.0]         # domyślne ograniczenia długości w jednostkach
        self.d_limits = [0.0, 100.0]         # domyślne ograniczenia długości w jednostkach

        # przechowuj wewnętrznie w radianach
        self.theta = math.radians(theta_deg)
        self.d = float(d)
        self.a = float(a)
        self.alpha = math.radians(alpha_deg)

        self.theta_variable = bool(theta_variable)
        self.d_variable = bool(d_variable)

        # zainicjuj Transform bez macierzy; Transform.__init__ ustawi identity
        super().__init__(matrix=None, parent=parent)

        if name is not None:
            try:
                self.name = name
                self.label = name
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

    def renderAxes(self):
        gl.glPushMatrix()
        gl.glPushAttrib(gl.GL_ALL_ATTRIB_BITS)

        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glEnable(gl.GL_COLOR_MATERIAL)
        gl.glColorMaterial(gl.GL_FRONT_AND_BACK, gl.GL_AMBIENT_AND_DIFFUSE)

        # OBLICZ p2 - przekształcony punkt (wyciągamy translację)
        # jeśli self.matrix jest 4x4 i translacja jest w ostatniej kolumnie:
        a0 = np.array(self.matrix[:3, 3], dtype=np.float32)

        asize = 5.0  # długość osi

        aX = np.array([asize, 0.0, 0.0, 1.0], dtype=np.float32)
        aX = aX @ self.matrix.T

        aY = np.array([0.0, asize, 0.0, 1.0], dtype=np.float32)
        aY = aY @ self.matrix.T

        aZ = np.array([0.0, 0.0, asize, 1.0], dtype=np.float32)
        aZ = aZ @ self.matrix.T

        gl.glEnable(gl.GL_LINE_SMOOTH)
        gl.glLineWidth(1.0)
        gl.glColor4ub(255, 0, 0, 255)
        gl.glBegin(gl.GL_LINES)
        gl.glVertex3f(float(a0[0]), float(a0[1]), float(a0[2]))
        gl.glVertex3f(float(aX[0]), float(aX[1]), float(aX[2]))
        # gl.glEnd()
        gl.glColor4ub(0, 255, 0, 255)
        # gl.glBegin(gl.GL_LINES)
        gl.glVertex3f(float(a0[0]), float(a0[1]), float(a0[2]))
        gl.glVertex3f(float(aY[0]), float(aY[1]), float(aY[2]))
        # gl.glEnd()
        gl.glColor4ub(0, 0, 255, 255)
        # gl.glBegin(gl.GL_LINES)
        gl.glVertex3f(float(a0[0]), float(a0[1]), float(a0[2]))
        gl.glVertex3f(float(aZ[0]), float(aZ[1]), float(aZ[2]))
        gl.glEnd()
        gl.glDisable(gl.GL_LINE_SMOOTH)

        gl.glPopAttrib()
        gl.glPopMatrix()


    def renderArm(self):
        gl.glPushMatrix()
        gl.glPushAttrib(gl.GL_ALL_ATTRIB_BITS)

        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glEnable(gl.GL_COLOR_MATERIAL)
        gl.glColorMaterial(gl.GL_FRONT_AND_BACK, gl.GL_AMBIENT_AND_DIFFUSE)

        # OBLICZ p2 - przekształcony punkt (wyciągamy translację)
        # jeśli self.matrix jest 4x4 i translacja jest w ostatniej kolumnie:
        p2 = np.array(self.matrix[:3, 3], dtype=np.float32)

        # alternatywnie:
        # v = np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)
        # p2_h = v @ self.matrix.T   # p2_h ma 4 elementy
        # p2 = p2_h[:3]

        gl.glColor4ub(255, 0, 0, 255)
        gl.glEnable(gl.GL_LINE_SMOOTH)
        gl.glLineWidth(3.0)
        gl.glBegin(gl.GL_LINES)
        gl.glVertex3f(0.0, 0.0, 0.0)
        gl.glVertex3f(float(p2[0]), float(p2[1]), float(p2[2]))
        gl.glEnd()
        gl.glDisable(gl.GL_LINE_SMOOTH)

        # punkt w (0,0,0)
        gl.glColor4ub(255, 255, 0, 255)
        gl.glEnable(gl.GL_POINT_SMOOTH)
        gl.glPointSize(9)
        gl.glBegin(gl.GL_POINTS)
        gl.glVertex3f(0.0, 0.0, 0.0)
        gl.glEnd()
        gl.glDisable(gl.GL_POINT_SMOOTH)

        gl.glPopAttrib()
        gl.glPopMatrix()

    def renderSelf(self):
        self.renderArm()                    # <- !!! wywołanie z nawiasami
        self.renderAxes()
        Transform.renderSelf(self)

    # settery/utility
    def set_theta_deg(self, val_deg):
        val = max( self.theta_limits[0], min( self.theta_limits[1], float(val_deg) ) )
        self.theta = math.radians(float(val))
        self.updateMatrix()

    def set_theta_rad(self, val_rad):
        val = max( math.radians(self.theta_limits[0]), min( math.radians(self.theta_limits[1]), float(val_rad) ) )
        self.theta = float(val)
        self.updateMatrix()

    def set_d(self, val):
        self.d = max( self.d_limits[0], min( self.d_limits[1], float(val) ) )
        self.updateMatrix()

    def set_a(self, val):
        self.a = max( self.a_limits[0], min( self.a_limits[1], float(val) ) )
        self.updateMatrix()

    def set_alpha_deg(self, val_deg):
        val = max( self.alpha_limits[0], min( self.alpha_limits[1], float(val_deg) ) )
        self.alpha = math.radians(float(val))
        self.updateMatrix()

    def set_alpha_rad(self, val_rad):
        val = max( math.radians(self.alpha_limits[0]), min( math.radians(self.alpha_limits[1]), float(val_rad) ) )
        self.alpha = float(val)
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

