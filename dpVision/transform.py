# -*- coding: utf-8 -*-
"""
Created on Fri Nov 24 10:50:11 2023

@author: pojdulos
"""

import re
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from OpenGL.GL import *
import numpy as np
from scipy.spatial.transform import Rotation
import math

from .globals import AP
from .object import Object
from .k3RigidToScrew import *

class Transform(Object):
	def __init__(self, matrix = None, parent=None):
		super( Transform, self ).__init__( parent )
		self.matrix = matrix if matrix is not None else QMatrix4x4()
		self.m_origin = [0., 0., 0.]
		self.m_show_screw = False

	def renderScrew(self, r=1., g=1., b=0.):
		V, alpha, D, t = K3RigidToScrew(self.toNumPy())
		print('V =',V, 'alpha =',np.degrees(alpha), 'D =',D, 't =',t)
		P = K3Projection([0.,0.,0.], D, V)
		print('nz=',P)
		A = np.vstack([ P - 50 * V, P, P + 50 * V ])
		print('q =', self.toQuaternion())
		glPushMatrix()
		glPushAttrib(GL_ALL_ATTRIB_BITS)

		glDisable(GL_TEXTURE_2D)
		glEnable(GL_COLOR_MATERIAL)

		glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

		glColor3f(r, g, b)

		glLineWidth(3.0)
		glBegin(GL_LINES)
		glVertex3f(A[0,0], A[0,1], A[0,2])
		glVertex3f(A[2,0], A[2,1], A[2,2])
		glEnd()
		glLineWidth(1.0)
		glBegin(GL_LINES)
		glVertex3f(0., 0., 0.)
		glVertex3f(A[1,0], A[1,1], A[1,2])
		glEnd()

		glPopAttrib()
		glPopMatrix()

	def renderSelf(self):
		if self.m_show_screw:
			self.renderScrew()
		glMultMatrixf(self.matrix.data())

	def translate(self, dx, dy, dz):
		self.matrix.translate(dx, dy, dz)

	def set_origin(self, origin=[0., 0., 0.]):
		self.m_origin = origin

	def rotate2(self, angle, axis):
		if self.m_origin:
			self.matrix.translate(self.m_origin[0], self.m_origin[1], self.m_origin[2])
		self.matrix.rotate(angle, axis[0], axis[1], axis[2])
		if self.m_origin:
			self.matrix.translate(-self.m_origin[0], -self.m_origin[1], -self.m_origin[2])

	def rotate(self, angle, axis, origin=None):
		if origin:
			self.matrix.translate(origin[0], origin[1], origin[2])
		self.matrix.rotate(angle, axis[0], axis[1], axis[2])
		if origin:
			self.matrix.translate(-origin[0], -origin[1], -origin[2])

	def reset(self):
		self.matrix.setToIdentity()

	def get_matrix(self):
		return self.matrix
    
	def fromNumPy(self, numpy_array):
		self.matrix = QMatrix4x4( 	numpy_array[0, 0], numpy_array[0, 1], numpy_array[0, 2], numpy_array[0, 3],
                      				numpy_array[1, 0], numpy_array[1, 1], numpy_array[1, 2], numpy_array[1, 3],
                      				numpy_array[2, 0], numpy_array[2, 1], numpy_array[2, 2], numpy_array[2, 3],
                      				numpy_array[3, 0], numpy_array[3, 1], numpy_array[3, 2], numpy_array[3, 3] )
		
	def toNumPy(self):
		return np.array( [
			[self.matrix[0,0], self.matrix[0,1], self.matrix[0,2], self.matrix[0,3]],
			[self.matrix[1,0], self.matrix[1,1], self.matrix[1,2], self.matrix[1,3]],
			[self.matrix[2,0], self.matrix[2,1], self.matrix[2,2], self.matrix[2,3]],
			[self.matrix[3,0], self.matrix[3,1], self.matrix[3,2], self.matrix[3,3]]] )

	def invertedMatrix(self):
		return np.linalg.inv(self.toNumPy())


	def rotationMatrix(self):
		return np.array( [
			[self.matrix[0,0], self.matrix[0,1], self.matrix[0,2]],
			[self.matrix[1,0], self.matrix[1,1], self.matrix[1,2]],
			[self.matrix[2,0], self.matrix[2,1], self.matrix[2,2]]] )
	
	def toGLMatrix(self):
		return self.matrix.data()

	def invertedRotationMatrix(self):
		return np.linalg.inv(self.rotationMatrix())

	def getTranslation(self):
		return [self.matrix.column(3).x(),
				self.matrix.column(3).y(),
				self.matrix.column(3).z()]

	# def setTranslation(self, tx, ty, tz):
	# 	self.matrix.setColumn(3, [tx, ty, tz, 1.0])

	# def setTranslation(self, tx, ty, tz):
	# 	old = self.getTranslation()
	# 	self.translate(tx - old[0], ty - old[1], tz - old[2])


	def setTranslation(self, tx, ty, tz):
		# --- 1. Pobierz kolumny bazowe (zawierają rotację i skalę) ---
		col0 = self.matrix.column(0).toVector3D()
		col1 = self.matrix.column(1).toVector3D()
		col2 = self.matrix.column(2).toVector3D()

		# --- 2. Oblicz skale i normalizuj ---
		scx = col0.length()
		scy = col1.length()
		scz = col2.length()

		if scx != 0: col0 /= scx
		if scy != 0: col1 /= scy
		if scz != 0: col2 /= scz

		# --- 3. Złóż nową macierz ---
		new_matrix = QMatrix4x4()
		new_matrix.setColumn(0, QVector4D(col0.x()*scx, col0.y()*scx, col0.z()*scx, 0))
		new_matrix.setColumn(1, QVector4D(col1.x()*scy, col1.y()*scy, col1.z()*scy, 0))
		new_matrix.setColumn(2, QVector4D(col2.x()*scz, col2.y()*scz, col2.z()*scz, 0))
		new_matrix.setColumn(3, QVector4D(tx, ty, tz, 1.0))

		self.matrix = new_matrix



	# def getScale(self):
	# 	scaleX = math.sqrt(self.matrix[0, 0]**2 + self.matrix[0, 1]**2 + self.matrix[0, 2]**2)
	# 	scaleY = math.sqrt(self.matrix[1, 0]**2 + self.matrix[1, 1]**2 + self.matrix[1, 2]**2)
	# 	scaleZ = math.sqrt(self.matrix[2, 0]**2 + self.matrix[2, 1]**2 + self.matrix[2, 2]**2)
	# 	return [scaleX, scaleY, scaleZ]

	# def getScale(self):
	# 	scale_x = (self.matrix.row(0).toVector3D()).length()
	# 	scale_y = (self.matrix.row(1).toVector3D()).length()
	# 	scale_z = (self.matrix.row(2).toVector3D()).length()
	# 	return [scale_x, scale_y, scale_z]

	# def getScale(self):
	# 	return [self.matrix.row(i).toVector3D().length() for i in range(3)]

	def getScale(self):
		return [
			self.matrix.column(0).toVector3D().length(),
			self.matrix.column(1).toVector3D().length(),
			self.matrix.column(2).toVector3D().length(),
		]

	def scale(self, sx, sy, sz):
		self.matrix.scale(sx, sy, sz)

	def setScale(self, sx, sy, sz):
		sc = self.getScale()
		dsx, dsy, dsz = sx / sc[0], sy / sc[1], sz / sc[2]
		self.matrix.scale(dsx, dsy, dsz)

	# def _setScale(matrix: QMatrix4x4, sx: float, sy: float, sz: float):
	# 	# 1. pobierz kolumny bazowe (X, Y, Z)
	# 	col0 = QVector3D(matrix.column(0).toVector3D())
	# 	col1 = QVector3D(matrix.column(1).toVector3D())
	# 	col2 = QVector3D(matrix.column(2).toVector3D())

	# 	# 2. oblicz bieżące skale
	# 	scx = col0.length()
	# 	scy = col1.length()
	# 	scz = col2.length()

	# 	# 3. normalizuj kolumny (zostaje czysta rotacja)
	# 	if scx != 0: col0 /= scx
	# 	if scy != 0: col1 /= scy
	# 	if scz != 0: col2 /= scz

	# 	# 4. przemnoż przez nowe skale
	# 	col0 *= sx
	# 	col1 *= sy
	# 	col2 *= sz

	# 	# 5. wpisz kolumny z powrotem do macierzy
	# 	for i in range(3):
	# 		matrix.setColumn(i, [col0[i], col1[i], col2[i], matrix.column(i).w()])

	# 	return matrix

	# def setScale(self, sx, sy, sz):
	# 	self.matrix = Transform._setScale(self.matrix, sx, sy, sz)

	def fromEulerAngles(self, roll, pitch, yaw):
		m = Rotation.from_euler('xyz', [roll, pitch, yaw], degrees=True).as_matrix()
		for i in range(3):
			for j in range(3):
				self.matrix[i,j] = m[i,j]

	def getEulerAnglesDeg(self):
		euler_angles = Rotation.from_matrix(self.rotationMatrix()).as_euler('xyz', degrees=True)
		return euler_angles

	def toQuaternion(self):
		x, y, z, w = Rotation.from_matrix(self.rotationMatrix()).as_quat()
		quaternion = [w, x, y, z]
		return quaternion
	
	# def getEulerAnglesDeg(self):
	# 	# Zakładamy, że m11 = row 0, col 0; m12 = row 0, col 1; itd.
	# 	m11, m12, m13 = self.matrix[0, 0], self.matrix[0, 1], self.matrix[0, 2]
	# 	m21, m22, m23 = self.matrix[1, 0], self.matrix[1, 1], self.matrix[1, 2]
	# 	m31, m32, m33 = self.matrix[2, 0], self.matrix[2, 1], self.matrix[2, 2]
	
	#     # Wyliczenie kątów Eulera z macierzy rotacji
	# 	if m13 < 1:
	# 		if m13 > -1:
	# 			thetaY = math.asin(m13)
	# 			thetaX = math.atan2(-m23, m33)
	# 			thetaZ = math.atan2(-m12, m11)
	# 		else:  # m13 == -1
	# 			thetaY = -math.pi / 2
	# 			thetaX = -math.atan2(m21, m22)
	# 			thetaZ = 0
	# 	else:  # m13 == 1
	# 		thetaY = math.pi / 2
	# 		thetaX = math.atan2(m21, m22)
	# 		thetaZ = 0
	
	# 	return [math.degrees(thetaX), math.degrees(thetaY), math.degrees(thetaZ)]

	# def toQuaternion(self):
	# 	# Pobierz elementy macierzy rotacji
	# 	m = self.matrix.copyDataTo()
	# 	m11, m12, m13, _, m21, m22, m23, _, m31, m32, m33, _, _, _, _, _, = m

	# 	# Oblicz współczynniki kwaternionu
	# 	w = (m11 + m22 + m33 + 1.0) / 4.0
	# 	x = (m11 - m22 - m33 + 1.0) / 4.0
	# 	y = (-m11 + m22 - m33 + 1.0) / 4.0
	# 	z = (-m11 - m22 + m33 + 1.0) / 4.0

	# 	# Zabezpieczenie przed niedokładnościami obliczeń
	# 	if w < 0.0:
	# 		w = 0.0
	# 	if x < 0.0:
	# 		x = 0.0
	# 	if y < 0.0:
	# 		y = 0.0
	# 	if z < 0.0:
	# 		z = 0.0

	# 	# Oblicz pierwiastki kwadratowe
	# 	w = pow(w, 0.5)
	# 	x = pow(x, 0.5)
	# 	y = pow(y, 0.5)
	# 	z = pow(z, 0.5)

	# 	# Wybierz największy współczynnik
	# 	max_value = max(w, x, y, z)
	# 	if max_value == w:
	# 		w *= 1.0
	# 		x *= 1.0 if m32 - m23 > 0 else -1.0
	# 		y *= 1.0 if m13 - m31 > 0 else -1.0
	# 		z *= 1.0 if m21 - m12 > 0 else -1.0
	# 	elif max_value == x:
	# 		w *= 1.0 if m32 - m23 > 0 else -1.0
	# 		x *= 1.0
	# 		y *= 1.0 if m21 + m12 > 0 else -1.0
	# 		z *= 1.0 if m13 + m31 > 0 else -1.0
	# 	elif max_value == y:
	# 		w *= 1.0 if m13 - m31 > 0 else -1.0
	# 		x *= 1.0 if m21 + m12 > 0 else -1.0
	# 		y *= 1.0
	# 		z *= 1.0 if m32 + m23 > 0 else -1.0
	# 	elif max_value == z:
	# 		w *= 1.0 if m21 - m12 > 0 else -1.0
	# 		x *= 1.0 if m13 + m31 > 0 else -1.0
	# 		y *= 1.0 if m32 + m23 > 0 else -1.0
	# 		z *= 1.0

	# 	# Utwórz kwaternion
	# 	quaternion = [w, x, y, z]
	# 	return quaternion


	def fromRowMatrixStr(self, text, separator):
		if text is not None:
			pieces = text.split(separator)

			if len(pieces) >= 16:
				tmpMatrix = []

				ok = False
				for row in range(4):
					for col in range(4):
						self.matrix[row,col] = float(pieces[ row * 4 + col])


	def getGlobalTransformation(self):
		return self.matrix if self.__parent is None else self.matrix * self.__parent.getGlobalTransformation()

	@staticmethod
	def fromTo(m0 = QMatrix4x4(), m1 = QMatrix4x4()):
		m1i, b = m1.inverted()
		return m0 * m1i if b else QMatrix4x4()

	def copyToClipboard(self):
		vals = []
		for row in range(4):
			for col in range(4):
				vals.append( str(self.matrix[row, col]) )
		text = ' '.join(vals)
		QApplication.clipboard().setText(text, QClipboard.Clipboard)

	def pasteFromClipboard(self):
		def listToMatrix4x4(values):
			matrix = QMatrix4x4()
			for row in range(4):
				for col in range(4):
					matrix[row, col] = values[row * 4 + col]
			return matrix
		
		text = QApplication.clipboard().text(QClipboard.Clipboard)
		if text:
			pieces = re.split(r"\s+", text)
			try:
				values = [float(i) for i in pieces]
				if len(values) == 16:
					tmpMatrix = listToMatrix4x4(values)
					self.matrix = tmpMatrix
				else:
					raise ValueError("Nieprawidłowa liczba wartości w schowku")
			except ValueError as e:
				print("Błąd konwersji wartości: ", e)
