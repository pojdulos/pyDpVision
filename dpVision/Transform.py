# -*- coding: utf-8 -*-
"""
Created on Fri Nov 24 10:50:11 2023

@author: pojdulos
"""

from PyQt5.QtGui import QMatrix4x4
from OpenGL.GL import *
import numpy as np
import math
from .Object import Object

class Transform(Object):
	def __init__(self, parent=None):
		super( Transform, self ).__init__( parent )
		self.matrix = QMatrix4x4()

	def renderSelf(self):
		glMultMatrixf(self.matrix.data())

	def translate(self, dx, dy, dz):
		self.matrix.translate(dx, dy, dz)

	def rotate(self, angle, x, y, z):
		self.matrix.rotate(angle, x, y, z)

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
