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
		if self._parent is not None:
			parent = self._parent()
			if parent is not None:
				return parent.getGlobalTransformation() @ self.matrix
		return self.matrix

	def getHierarchyBBInParentSpace(self):
		bb = self.getHierarchyBB()
		if bb is None:
			return None

		_b, _min, _max = bb
		if not _b or _min is None or _max is None:
			return False, None, None

		corners = np.array([
			[_min[0], _min[1], _min[2], 1.0],
			[_min[0], _min[1], _max[2], 1.0],
			[_min[0], _max[1], _min[2], 1.0],
			[_min[0], _max[1], _max[2], 1.0],
			[_max[0], _min[1], _min[2], 1.0],
			[_max[0], _min[1], _max[2], 1.0],
			[_max[0], _max[1], _min[2], 1.0],
			[_max[0], _max[1], _max[2], 1.0],
		], dtype=np.float64)

		transformed = (self.toNumPy() @ corners.T).T[:, :3]
		return True, transformed.min(axis=0).tolist(), transformed.max(axis=0).tolist()


	# --- budowa macierzy TRS ---
	def updateMatrix(self):
		T = np.eye(4)
		T[:3, 3] = self.m_translation
		S = np.diag([*self.m_scale, 1.0])
		R = np.eye(4)
		R[:3, :3] = self.m_rotation.as_matrix()
		self.matrix = T @ R @ S
		self.invalidate_bb()

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
		# Transformacja stosowana zawsze - rowniez podczas WBOIT pass!
		# Bez tego dzieci nie mialyby poprawnej macierzy modelu.
		from .globals import AP
		if AP.wboit_pass is None and self.m_show_screw:
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
		"""Ustawia rotacje na podstawie kwaternionu w kolejnosci [w, x, y, z]."""
		quat = np.array(quat, dtype=float)
		if np.allclose(quat, 0.0):
			quat = np.array([1, 0, 0, 0], dtype=float)

		norm = np.linalg.norm(quat)
		if norm < 1e-12:  # prawie zero
			quat = np.array([1,0,0,0], dtype=float)
		else:
			quat = quat / norm

		self.m_rotation = Rotation.from_quat([quat[1], quat[2], quat[3], quat[0]])
		self.updateMatrix()


	def getRotation(self):
		# zwraca liste [w, x, y, z]
		x, y, z, w = self.m_rotation.as_quat()
		return [w, x, y, z]

	# --- operacje inkrementalne ---
	def translate(self, dx, dy=None, dz=None):
		"""Dodaje przesuniecie podane jako trzy skalarne wartosci lub jeden wektor XYZ."""
		if dy is None and dz is None:
			vector = np.asarray(dx, dtype=np.float64).reshape(3)
		else:
			vector = np.asarray([dx, dy, dz], dtype=np.float64)

		self.m_translation += vector
		self.updateMatrix()


	def fromEulerAngles(self, roll, pitch, yaw, degrees=True):
		"""
		Ustawia rotacje z katow Eulera.
		:param roll: obrot wokol osi X
		:param pitch: obrot wokol osi Y
		:param yaw: obrot wokol osi Z
		:param degrees: True jesli podajemy katy w stopniach (domyslnie)
		"""
		self.m_rotation = Rotation.from_euler('xyz', [roll, pitch, yaw], degrees=degrees)
		self.updateMatrix()


	def rotate(self, angle, axis, origin=None):
		"""
		Obraca transformacje wokol zadanej osi w ukladzie globalnym.
		:param angle: kat obrotu w stopniach (mozesz zmienic na radiany jesli wolisz)
		:param axis: lista/ndarray [x, y, z] - os obrotu
		:param origin: lista/ndarray [x, y, z], pivot wokol ktorego obracamy
		"""
		# normalizacja osi
		axis = np.asarray(axis, dtype=float)
		axis /= np.linalg.norm(axis)

		# scipy uzywa radianow
		angle_rad = np.radians(angle)

		# nowy obrot jako obiekt Rotation
		R = Rotation.from_rotvec(axis * angle_rad)

		if origin is None:
			# obrot tylko orientacji
			self.m_rotation = R * self.m_rotation
		else:
			origin = np.asarray(origin, dtype=float)

			# przesuniecie do pivotu
			self.m_translation -= origin

			# obrot zarowno rotacji, jak i translacji
			self.m_translation = R.apply(self.m_translation)
			self.m_rotation = R * self.m_rotation

			# powrot z pivotu
			self.m_translation += origin

		self.updateMatrix()

	def rescale_by(self, sx, sy, sz):
		self.m_scale *= [sx, sy, sz]
		self.updateMatrix()

	def reset(self):
		self.m_translation[:] = [0., 0., 0.]
		self.m_rotation = Rotation.identity()
		self.m_scale[:] = [1., 1., 1.]
		self.updateMatrix()

	# --- konwersje ---
	def fromNumPy(self, numpy_array: np.ndarray):
		"""Aktualizuje skladowe transformacji na podstawie macierzy 4x4."""
		M = np.array(numpy_array, dtype=np.float64).reshape((4, 4))
		self.matrix = M

		# --- Translacja ---
		self.m_translation = M[:3, 3]

		# --- Skala (dlugosci wektorow kolumnowych 3x3) ---
		scale_x = np.linalg.norm(M[:3, 0])
		scale_y = np.linalg.norm(M[:3, 1])
		scale_z = np.linalg.norm(M[:3, 2])
		self.m_scale = np.array([scale_x, scale_y, scale_z])

		# --- Rotacja (z macierzy 3x3 z usunieta skala) ---
		Rmat = np.zeros((3, 3))
		if scale_x != 0: Rmat[:, 0] = M[:3, 0] / scale_x
		if scale_y != 0: Rmat[:, 1] = M[:3, 1] / scale_y
		if scale_z != 0: Rmat[:, 2] = M[:3, 2] / scale_z

		self.m_rotation = Rotation.from_matrix(Rmat)
		self.invalidate_bb()

		return self.matrix

	def fromRowMatrixStr(self, matrix_text, separator=","):
		"""Wczytuje macierz 4x4 z tekstu zapisanego wierszami, zachowujac zgodnosc ze starym parserem ATMDL."""
		if matrix_text is None:
			raise ValueError("matrix_text cannot be None")

		if separator == ",":
			values = np.fromstring(matrix_text, dtype=np.float64, sep=",")
		else:
			normalized = matrix_text.replace(separator, " ")
			values = np.fromstring(normalized, dtype=np.float64, sep=" ")

		if values.size != 16:
			raise ValueError(f"Expected 16 matrix values, got {values.size}")

		return self.fromNumPy(values.reshape((4, 4)))

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
					# self.matrix = np.array(values, dtype=np.float64).reshape((4, 4))
					self.fromNumPy(values)
				else:
					raise ValueError("Nieprawidlowa liczba wartosci w schowku")
			except ValueError as e:
				print("Blad konwersji wartosci: ", e)
