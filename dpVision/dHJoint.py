import math
from operator import ior
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

    def __init__(self, angle_unit='deg', theta=0.0, d=0.0, a=0.0, alpha=0.0,
                joint_type='revolute', theta_variable=True, d_variable=False,
                parent=None, name=None):

        self.alpha_limits = None
        self.theta_limits = None
        self.a_limits = None
        self.d_limits = None

        self.angle_unit = angle_unit if angle_unit in ('deg','rad') else 'deg'
        self.length_unit = "mm" # {"type":"string"},
        self.convention = "classical" # {"type":"string","enum":["classical","modified"]}
        self.scheme = "urdf-like" # {"type":"string","enum":["joints-only","urdf-like"]}
        
        # przechowuj wewnętrznie w radianach
        self.theta = math.radians(theta) if self.angle_unit == 'deg' else float(theta)
        self.d = float(d)
        self.a = float(a)
        self.alpha = math.radians(alpha) if self.angle_unit == 'deg' else float(alpha)

        if joint_type and joint_type in ('revolute','prismatic','fixed'):
            self.joint_type = joint_type
            self.theta_variable = (joint_type=='revolute')
            self.d_variable = (joint_type=='prismatic') 
        else:
            self.theta_variable = bool(theta_variable) if theta_variable is not None else True
            self.d_variable = bool(d_variable) if d_variable is not None else False
            self.joint_type = 'revolute' if self.theta_variable else 'prismatic' if self.d_variable else 'fixed'

        self.view_as_vector = True  # czy renderować joint jako wektor (linia od origin do pozycji jointu)

        # dopiero tutaj, bo Transform.__init__ wywoła self.updateMatrix()
        # z tej klasy więc musimy mieć najpierw ustawione parametry DH
        super().__init__(matrix=None, parent=parent)

        if name is not None:
            try:
                self.label = name
            except Exception:
                pass

        # ustaw macierz lokalną zgodnie z DH
        #self.updateMatrix()
        # niepotrzebne bo konstruktor Transform wywołał updateMatrix()

    def create(self, type='revolute'):
        joint = DHJoint( joint_type = type if type in ('revolute','prismatic','fixed') else 'revolute' )
        return joint

    def set_type(self, type='revolute'):
        self.joint_type = type if type in ('revolute','prismatic','fixed') else 'revolute'
        self.d_variable = (self.joint_type == 'prismatic')
        self.theta_variable = (self.joint_type == 'revolute')

    def addChild(self, d):
        from dpVision.dHModel import DHLink
        if d is None or not isinstance(d, DHLink):
            print("DHJoint: only DHLink instances can be added as children.")
            return False
        
        # Joint może mieć tylko jedno dziecko (link)
        # if len(self.m_data) > 0:
        #     print("DHJoint: can have only one child link. Remove existing child first.")
        #     return False
        
        return super(DHJoint, self).addChild(d)

    # nadpisujemy updateMatrix tak, by ustawić macierz zgodnie z DH
    def updateMatrix(self):
        # classical DH: Rz(theta) * Tz(d) * Tx(a) * Rx(alpha)
        M = Rz_mat_rad(self.theta) @ Tz_mat(self.d) @ Tx_mat(self.a) @ Rx_mat_rad(self.alpha)
        # korzystamy z fromNumPy, aby w Transform poprawnie rozbić translację/rotację/skale
        # fromNumPy ustawi self.matrix, self.m_translation, self.m_rotation, self.m_scale
        self.fromNumPy(M)

        m0 = np.eye(4, dtype=np.float64)
        m1 = self.toNumPy()
        if self._parent is not None:
            parent = self._parent()
            if parent is not None:
                m0 = parent.getGlobalTransformation()
                m1 = m0 @ self.toNumPy()
        p0 = m0[:3, 3]
        p1 = m1[:3, 3]

        self.description = f"begin: [{p0[0]:.2f}, {p0[1]:.2f}, {p0[2]:.2f}]\n end: [{p1[0]:.2f}, {p1[1]:.2f}, {p1[2]:.2f}]"
        # print(self.description)

    def renderAxes(self):
        gl.glPushAttrib(gl.GL_ALL_ATTRIB_BITS)
        gl.glDisable(gl.GL_LIGHTING)

        asize = 7.0  # długość osi

        a0XYZ = np.array([
            [0.0, 0.0, 0.0, 1.0],       # punkt origin
            [asize, 0.0, 0.0, 1.0],     # oś X
            [0.0, asize, 0.0, 1.0],     # oś Y
            [0.0, 0.0, asize, 1.0],     # oś Z 
        ], dtype=np.float32)
        
        a0XYZ = a0XYZ @ self.matrix.T
        a0, aX, aY, aZ = a0XYZ[:, :3]

        gl.glEnable(gl.GL_LINE_SMOOTH)
        gl.glLineWidth(1.0)
        gl.glBegin(gl.GL_LINES)
        gl.glColor4ub(255, 0, 0, 255)
        gl.glVertex3f(*a0); gl.glVertex3f(*aX)
        gl.glColor4ub(0, 255, 0, 255)
        gl.glVertex3f(*a0); gl.glVertex3f(*aY)
        gl.glColor4ub(0, 0, 255, 255)
        gl.glVertex3f(*a0); gl.glVertex3f(*aZ)
        gl.glEnd()
        gl.glDisable(gl.GL_LINE_SMOOTH)

        gl.glPopAttrib()


    def renderArm(self):
        gl.glPushAttrib(gl.GL_ALL_ATTRIB_BITS)
        gl.glDisable(gl.GL_LIGHTING)

        p0 = [0.0, 0.0, 0.0]
        p1 = None
        p2 = np.array(self.matrix[:3, 3], dtype=np.float32)
        c2 = [0,0,255,255]      # zasadniczy segment
        c1 = [128,128,128,255]  # offset od poprzedniego jointu
        c0 = [255,255,0,255]    # kropka w węźle

        if not self.view_as_vector:
            if self.joint_type == 'revolute':
                p1 = [0.0, 0.0, p2[2]]
            elif self.joint_type == 'prismatic':
                p1 = [p2[0], 0.0, 0.0]
        
        if self.joint_type == 'fixed':
            c2 = c1

        
        gl.glEnable(gl.GL_LINE_SMOOTH)
        gl.glLineWidth(3.0)
        gl.glBegin(gl.GL_LINES)
        if p1:
            gl.glColor4ub(*c1)
            gl.glVertex3f(*p0); gl.glVertex3f(*p1)
            gl.glColor4ub(*c2)
            gl.glVertex3f(*p1); gl.glVertex3f(*p2)
        else:
            gl.glColor4ub(*c2)
            gl.glVertex3f(*p0); gl.glVertex3f(*p2)
        gl.glEnd()
        gl.glDisable(gl.GL_LINE_SMOOTH)

        # punkt w (0,0,0)
        
        gl.glEnable(gl.GL_POINT_SMOOTH)
        gl.glPointSize(9)
        gl.glBegin(gl.GL_POINTS)
        gl.glColor4ub(*c0)
        gl.glVertex3f(*p0)
        gl.glEnd()
        gl.glDisable(gl.GL_POINT_SMOOTH)

        gl.glPopAttrib()

    def renderSelf(self):
        self.renderArm()
        self.renderAxes()
        Transform.renderSelf(self)

    # settery/utility
    def set_theta_deg(self, val_deg):
        val = max( self.theta_limits[0], min( self.theta_limits[1], float(val_deg) ) ) if self.theta_limits else float(val_deg)
        self.theta = math.radians(float(val))
        self.updateMatrix()

    def set_theta_rad(self, val_rad):
        val = max( math.radians(self.theta_limits[0]), min( math.radians(self.theta_limits[1]), float(val_rad) ) ) if self.theta_limits else float(val_rad)
        self.theta = float(val)
        self.updateMatrix()

    def set_d(self, val):
        self.d = max( self.d_limits[0], min( self.d_limits[1], float(val) ) ) if self.d_limits else float(val)
        self.updateMatrix()

    def set_a(self, val):
        self.a = max( self.a_limits[0], min( self.a_limits[1], float(val) ) ) if self.a_limits else float(val)
        self.updateMatrix()

    def set_alpha_deg(self, val_deg):
        val = max( self.alpha_limits[0], min( self.alpha_limits[1], float(val_deg) ) ) if self.alpha_limits else float(val_deg) 
        self.alpha = math.radians(float(val))
        self.updateMatrix()

    def set_alpha_rad(self, val_rad):
        val = max( math.radians(self.alpha_limits[0]), min( math.radians(self.alpha_limits[1]), float(val_rad) ) ) if self.alpha_limits else float(val_rad) 
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

    def to_dict(self, angle_unit='deg', urdf_like=True):
        limits = self.theta_limits if self.joint_type=='revolute' else self.d_limits if self.joint_type=='prismatic' else None

        joint = {
            'name': self.label if self.label else '',
            'type': self.joint_type,
        }
        
        if urdf_like:
            joint['parent'] = self.parent.label if self.parent else None
            joint['child'] = self.children()[0].label if self.children() else None
        else:
            joint['parent_joint'] = self.parent.parent.label if self.parent and self.parent.parent else None

        dh_params = self.to_dh_row(degrees=(angle_unit=='deg'))
        joint.update(dh_params)

        if limits:
            joint['limits'] = limits

        return joint
    
    def subtree_to_dict(self, angle_unit='deg'):
        jd = [ self.to_dict(angle_unit=angle_unit) ]
        for child in self.children():
            if isinstance(child, DHJoint):
                jd.extend( child.subtree_to_dict(angle_unit=angle_unit) )
        return jd
    
    def subtree_to_json(self, angle_unit='deg'):
        import json
        jd = self.subtree_to_dict(angle_unit=angle_unit)
        return json.dumps(jd, indent=4)
    
    def export_subtree(self, filename):
        import json
        joints = self.subtree_to_dict(angle_unit='deg')
        meta = {
            'angle_unit': 'deg',
            'convention': 'classical',
            'length_unit': 'mm',
            'version': '1.0'
        }
        jd = {'meta': meta, 'joints': joints}
        
        with open(filename, 'w') as f:
            json.dump(jd, f, indent=4)

    @classmethod
    def from_dict(cls, jd, joints_dict=None, angle_unit='deg'):
        joint = DHJoint(
            joint_type=jd.get('type','revolute'),
            angle_unit=angle_unit,
            theta=jd.get('theta',0.0),
            d=jd.get('d',0.0),
            a=jd.get('a',0.0),
            alpha=jd.get('alpha',0.0),
            name=jd.get('name',None)
        )

        limits = jd.get('limits', None)
        if limits:
            if joint.joint_type=='revolute':
                joint.theta_limits = limits
            elif joint.joint_type=='prismatic':
                joint.d_limits = limits

        if joints_dict is not None:
            joints_dict[joint.label] = joint

        return joint    
    