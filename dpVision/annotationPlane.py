# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 13:15:53 2023

@author: darek
"""

from .annotation import Annotation
from OpenGL.GL import *
import math
import numpy as np

class Vector3d(np.ndarray):
	"""Prosta klasa wektorowa bazująca na NumPy."""
	def __new__(cls, x, y, z):
		obj = np.asarray([x, y, z], dtype=float).view(cls)
		return obj

	def length(self):
		return np.linalg.norm(self)

	def normalized(self):
		norm = self.length()
		return self / norm if norm != 0 else self

	def cross(self, other):
		return Vector3d(*np.cross(self, other))

	def __neg__(self):
		return Vector3d(*(-self.view(np.ndarray)))

	def __mul__(self, scalar):
		return Vector3d(*((self.view(np.ndarray)) * scalar))

class AnnotationPlane(Annotation):
	def __init__(self, pC=[0.0,0.0,0.0], pN=[0.0,0.0,1.0], size=10, parent=None):
		Annotation.__init__(self, parent)
		self.m_center = pC
		self.m_normal = pN
		self.m_size = size


	def renderSelf(self):
		normal = Vector3d(*self.m_normal)
		center = Vector3d(*self.m_center)
		size = self.m_size

		if normal.length() > 0.0:
			# Startowe wartości
			x, y, z = 1.0, 1.0, 1.0

			# Wyznaczanie jednego z kierunków zależnie od normalnej
			if normal[2] != 0.0:
				z = (normal[0] + normal[1]) / -normal[2]
			elif normal[1] != 0.0:
				y = (normal[0] + normal[2]) / -normal[1]
			else:
				x = (normal[1] + normal[2]) / -normal[0]

			v1 = Vector3d(x, y, z).normalized() * size
			v2 = v1.cross(normal).normalized() * size
			v3 = -v1
			v4 = -v2

			glPushMatrix()
			glPushAttrib(GL_ALL_ATTRIB_BITS)

			glDisable(GL_TEXTURE_2D)
			glEnable(GL_COLOR_MATERIAL)
			glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

			glPointSize(9)

			if self.checked:
				glColor4ub(self.m_selcolor.red(), self.m_selcolor.green(), self.m_selcolor.blue(), self.m_selcolor.alpha())
			else:
				glColor4ub(self.m_color.red(), self.m_color.green(), self.m_color.blue(), self.m_color.alpha())

			glTranslatef(center[0], center[1], center[2])

			# Rysowanie kwadratu
			glBegin(GL_QUADS)
			glVertex3f(*v1)
			glVertex3f(*v2)
			glVertex3f(*v3)
			glVertex3f(*v4)
			glEnd()

			# Wektor normalny jako linia
			if normal.length() != 0.0:
				glLineWidth(1)
				glColor3f(1.0, 1.0, 0.0)
				glBegin(GL_LINES)
				glVertex3f(*(5 * normal))
				glVertex3f(0.0, 0.0, 0.0)
				glEnd()

			glPopAttrib()
			glPopMatrix()
