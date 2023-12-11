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
import math

from dpVision.Globals import AP
from .Object import Object

class Transform(Object):
	def __init__(self, matrix = None, parent=None):
		super( Transform, self ).__init__( parent )
		self.matrix = matrix if matrix is not None else QMatrix4x4()

	def renderSelf(self):
		glMultMatrixf(self.matrix.data())

	def translate(self, dx, dy, dz):
		self.matrix.translate(dx, dy, dz)

	def rotate(self, angle, axis, origin=None):
		if origin:
			self.matrix.translate(-origin[0], -origin[1], -origin[2])
		self.matrix.rotate(angle, axis[0], axis[1], axis[2])
		if origin:
			self.matrix.translate(origin[0], origin[1], origin[2])

	def scale(self, sx, sy, sz):
		self.matrix.scale(sx, sy, sz)

	def reset(self):
		self.matrix.setToIdentity()

	def get_matrix(self):
		return self.matrix
    
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
		return [self.matrix[0, 3], self.matrix[1, 3], self.matrix[2, 3]]

	def getScale(self):
		scaleX = math.sqrt(self.matrix[0, 0]**2 + self.matrix[0, 1]**2 + self.matrix[0, 2]**2)
		scaleY = math.sqrt(self.matrix[1, 0]**2 + self.matrix[1, 1]**2 + self.matrix[1, 2]**2)
		scaleZ = math.sqrt(self.matrix[2, 0]**2 + self.matrix[2, 1]**2 + self.matrix[2, 2]**2)
		return [scaleX, scaleY, scaleZ]

	def getEulerAnglesDeg(self):
		# Zakładamy, że m11 = row 0, col 0; m12 = row 0, col 1; itd.
		m11, m12, m13 = self.matrix[0, 0], self.matrix[0, 1], self.matrix[0, 2]
		m21, m22, m23 = self.matrix[1, 0], self.matrix[1, 1], self.matrix[1, 2]
		m31, m32, m33 = self.matrix[2, 0], self.matrix[2, 1], self.matrix[2, 2]
	
	    # Wyliczenie kątów Eulera z macierzy rotacji
		if m13 < 1:
			if m13 > -1:
				thetaY = math.asin(m13)
				thetaX = math.atan2(-m23, m33)
				thetaZ = math.atan2(-m12, m11)
			else:  # m13 == -1
				thetaY = -math.pi / 2
				thetaX = -math.atan2(m21, m22)
				thetaZ = 0
		else:  # m13 == 1
			thetaY = math.pi / 2
			thetaX = math.atan2(m21, m22)
			thetaZ = 0
	
		return [math.degrees(thetaX), math.degrees(thetaY), math.degrees(thetaZ)]

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
		return self.matrix if self.m_parent is None else self.matrix * self.m_parent.getGlobalTransformation()

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
