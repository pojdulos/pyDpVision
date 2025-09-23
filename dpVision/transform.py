import re
import numpy as np
from scipy.spatial.transform import Rotation
from OpenGL.GL import *
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QClipboard

from .globals import AP
from .object import Object
from .k3RigidToScrew import *


class Transform(Object):
	def __init__(self, matrix=None, parent=None):
		super().__init__(parent)

		self.m_translation = np.zeros(3, dtype=np.float64)
		self.m_rotation = Rotation.identity()
		self.m_scale = np.ones(3, dtype=np.float64)
		self.m_lock_scale = True
		
		self.m_origin = np.zeros(3, dtype=np.float64)
		self.m_show_screw = False

		self.matrix = np.eye(4, dtype=np.float64)
		if matrix is not None:
			self.fromNumPy(matrix)
		else:
			self.updateMatrix()

	def getGlobalTransformation(self):
		if self.__parent is not None:
			parent = self.__parent()
			if parent is not None:
				return parent.getGlobalTransformation() @ self.matrix
		return self.matrix


	def getBB(self):
		# 1. Najpierw zbieramy BB dzieci
		_b, _min, _max = Object.getBB(self)

		if not _b:  # jeśli dzieci nie mają BB
			return False, None, None

		# 2. Generujemy 8 narożników AABB
		corners = [
			[_min[0], _min[1], _min[2], 1.0],
			[_min[0], _min[1], _max[2], 1.0],
			[_min[0], _max[1], _min[2], 1.0],
			[_min[0], _max[1], _max[2], 1.0],
			[_max[0], _min[1], _min[2], 1.0],
			[_max[0], _min[1], _max[2], 1.0],
			[_max[0], _max[1], _min[2], 1.0],
			[_max[0], _max[1], _max[2], 1.0],
		]
		corners = np.array(corners, dtype=np.float64)

		# 3. Przekształcamy wszystkie narożniki macierzą transformacji
		mat = self.toNumPy()
		transformed = (mat @ corners.T).T[:, :3]  # bierzemy tylko XYZ

		# 4. Wyznaczamy nowe min/max
		bb_min = transformed.min(axis=0).tolist()
		bb_max = transformed.max(axis=0).tolist()

		return True, bb_min, bb_max


	# --- budowa macierzy TRS ---
	def updateMatrix(self):
		T = np.eye(4)
		T[:3, 3] = self.m_translation
		S = np.diag([*self.m_scale, 1.0])
		R = np.eye(4)
		R[:3, :3] = self.m_rotation.as_matrix()
		self.matrix = T @ R @ S

	def invertedMatrix(self):
		return np.linalg.inv(self.matrix)

	def invertedRotationMatrix(self):
		return np.linalg.inv(self.m_rotation.as_matrix())

	@staticmethod
	def fromTo(m0, m1):
		return m0 @ np.linalg.inv(m1)

	# --- rendering ---
	def renderScrew(self, r=1., g=1., b=0.):
		V, alpha, D, t = K3RigidToScrew(self.matrix)
		P = K3Projection([0., 0., 0.], D, V)
		A = np.vstack([P - 50 * V, P, P + 50 * V])

		glPushMatrix()
		glPushAttrib(GL_ALL_ATTRIB_BITS)

		glDisable(GL_TEXTURE_2D)
		glEnable(GL_COLOR_MATERIAL)
		glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
		glColor3f(r, g, b)

		glLineWidth(3.0)
		glBegin(GL_LINES)
		glVertex3f(*A[0]); glVertex3f(*A[2])
		glEnd()

		glLineWidth(1.0)
		glBegin(GL_LINES)
		glVertex3f(0., 0., 0.); glVertex3f(*A[1])
		glEnd()

		glPopAttrib()
		glPopMatrix()

	def renderSelf(self):
		if self.m_show_screw:
			self.renderScrew()
		glMultMatrixf(self.matrix.astype(np.float32).T)

	# --- settery/gettery TRS ---
	def setTranslation(self, tx, ty, tz):
		self.m_translation[:] = [tx, ty, tz]
		self.updateMatrix()

	def getTranslation(self):
		return self.m_translation.tolist()

	def setScale(self, sx, sy, sz):
		self.m_scale[:] = [sx, sy, sz]
		self.updateMatrix()

	def getScale(self):
		return self.m_scale.tolist()

	def setRotation(self, quat):
		quat = np.array(quat, dtype=float)
		if np.allclose(quat, 0.0):
			quat = np.array([1, 0, 0, 0], dtype=float)
		quat /= np.linalg.norm(quat)
		self.m_rotation = Rotation.from_quat([quat[1], quat[2], quat[3], quat[0]])
		self.updateMatrix()


	def getRotation(self):
		# zwraca listę [w, x, y, z]
		x, y, z, w = self.m_rotation.as_quat()
		return [w, x, y, z]

	# --- operacje inkrementalne ---
	def translate(self, dx, dy, dz):
		self.m_translation += [dx, dy, dz]
		self.updateMatrix()



	def rotate(self, angle, axis, origin=None):
		"""
		Obraca transformację wokół zadanej osi w układzie globalnym.
		:param angle: kąt obrotu w stopniach (możesz zmienić na radiany jeśli wolisz)
		:param axis: lista/ndarray [x, y, z] – oś obrotu
		:param origin: lista/ndarray [x, y, z], pivot wokół którego obracamy
		"""
		# normalizacja osi
		axis = np.asarray(axis, dtype=float)
		axis /= np.linalg.norm(axis)

		# scipy używa radianów
		angle_rad = np.radians(angle)

		# nowy obrót jako obiekt Rotation
		R = Rotation.from_rotvec(axis * angle_rad)

		if origin is None:
			# obrót tylko orientacji
			self.m_rotation = R * self.m_rotation
		else:
			origin = np.asarray(origin, dtype=float)

			# przesunięcie do pivotu
			self.m_translation -= origin

			# obrót zarówno rotacji, jak i translacji
			self.m_translation = R.apply(self.m_translation)
			self.m_rotation = R * self.m_rotation

			# powrót z pivotu
			self.m_translation += origin

		self.updateMatrix()

	def scale(self, sx, sy, sz):
		self.m_scale *= [sx, sy, sz]
		self.updateMatrix()

	def reset(self):
		self.m_translation[:] = [0., 0., 0.]
		self.m_rotation = Rotation.identity()
		self.m_scale[:] = [1., 1., 1.]
		self.updateMatrix()

	# --- konwersje ---
	def fromNumPy(self, numpy_array):
		self.matrix = np.array(numpy_array, dtype=np.float64).reshape((4, 4))
		return self.matrix

	def toNumPy(self):
		return self.matrix.copy()

	def rotationMatrix(self):
		return self.m_rotation.as_matrix()

	def toGLMatrix(self):
		return self.matrix.astype(np.float32).T.flatten()

	def getEulerAnglesDeg(self):
		return self.m_rotation.as_euler('xyz', degrees=True).tolist()

	# --- clipboard ---
	def copyToClipboard(self):
		vals = self.matrix.flatten()
		text = ' '.join(map(str, vals))
		QApplication.clipboard().setText(text, QClipboard.Clipboard)

	def pasteFromClipboard(self):
		text = QApplication.clipboard().text(QClipboard.Clipboard)
		if text:
			pieces = re.split(r"\s+", text)
			try:
				values = [float(i) for i in pieces]
				if len(values) == 16:
					self.matrix = np.array(values, dtype=np.float64).reshape((4, 4))
				else:
					raise ValueError("Nieprawidłowa liczba wartości w schowku")
			except ValueError as e:
				print("Błąd konwersji wartości: ", e)

