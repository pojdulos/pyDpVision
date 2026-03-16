# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 13:15:53 2023

@author: darek
"""

from .annotation import Annotation
from OpenGL.GL import *
import math
import numpy as np
import numbers
import logging
logger = logging.getLogger(__name__)

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
	def __init__(self, pC=(0.0,0.0,0.0), pN=(0.0,0.0,1.0), size=(10,10), parent=None):
		Annotation.__init__(self, parent)
		self.m_center = pC
		self.normal_vector = pN
		self.setSize(size)
		self._wboit_vbo = None

	@property
	def normal_vector(self):
		return self.m_normal
	
	@normal_vector.setter
	def normal_vector(self, _vec):
		self.m_normal = (0.0, 0.0, 1.0)

		def assign_if_nonzero(vn):
			if vn.length() != 0:
				self.m_normal = tuple(vn)
			else:
				logger.warning("Normal vector cannot be zero size")

		if isinstance(_vec, Vector3d):
			assign_if_nonzero(_vec.normalized())
			return

		if isinstance(_vec, str):
			logger.warning("Normal vector cannot be a string")
			return

		try:
			t = tuple(_vec)
		except TypeError:
			logger.warning(f"Normal vector must be iterable of 3 numbers, got: {type(_vec)}")
			return

		if len(t) != 3:
			logger.warning(f"Normal vector must have exactly 3 components, got {len(t)}")
			return

		assign_if_nonzero(Vector3d(*t).normalized())
	

	def setSize(self, _size):
		if isinstance(_size, numbers.Number):
			# skalar -> kwadrat
			self.m_size = (_size, _size)

		elif isinstance(_size, str):
			# specjalne traktowanie stringów
			print("String:", _size)

		else:
			try:
				t = tuple(_size)
				if len(t) == 1:
					# np. [5] -> (5, 5)
					self.m_size = (t[0], t[0])
				elif len(t) >= 2:
					# bierzemy tylko pierwsze dwie wartości
					self.m_size = (t[0], t[1])
				else:
					raise ValueError("Pusta sekwencja dla rozmiaru!")
			except TypeError:
				raise TypeError(f"Nieobsługiwany typ dla setSize: {type(_size)}")


	def renderSelf(self):
		from .globals import AP
		normal = Vector3d(*self.m_normal)
		center = Vector3d(*self.m_center)
		W, H = self.m_size

		if normal.length() > 0.0:
			normal = normal.normalized()

			# wybierz wektor nie równoległy do normal
			if abs(normal[0]) < 0.9:
				tmp = Vector3d(1, 0, 0)
			else:
				tmp = Vector3d(0, 1, 0)

			# oblicz v1 ortogonalny do normal
			v1 = tmp - normal * tmp.dot(normal)
			if v1.length() < 1e-6:
				# awaryjnie użyj innego wektora
				tmp = Vector3d(0, 0, 1)
				v1 = tmp - normal * tmp.dot(normal)

			v1 = v1.normalized() * (W / 2.0)
			v2 = normal.cross(v1).normalized() * (H / 2.0)

			# rogi prostokąta
			p1 =  v1 + v2
			p2 = -v1 + v2
			p3 = -v1 - v2
			p4 =  v1 - v2

			if AP.wboit_pass is not None:
				if AP.wboit_pass >= 0:
					if self.is_transparent:
						self.render_wboit(AP.wboit_pass, (p1, p2, p3, p4), center)
					return
				if self.is_transparent:
					return

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
			glVertex3f(*p1)
			glVertex3f(*p2)
			glVertex3f(*p3)
			glVertex3f(*p4)
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

	def render_wboit(self, pass_idx, corners, center):
		prog = self._prepare_wboit_shader(pass_idx)
		if prog is None:
			return

		vertices = np.array([
			corners[0] + center,
			corners[1] + center,
			corners[2] + center,
			corners[0] + center,
			corners[2] + center,
			corners[3] + center,
		], dtype=np.float32)

		if self._wboit_vbo is None:
			self._wboit_vbo = glGenBuffers(1)
		glBindBuffer(GL_ARRAY_BUFFER, self._wboit_vbo)
		glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_DYNAMIC_DRAW)
		glEnableVertexAttribArray(0)
		glVertexAttribPointer(0, 3, GL_FLOAT, False, 0, None)
		glDrawArrays(GL_TRIANGLES, 0, 6)
		glDisableVertexAttribArray(0)
		glBindBuffer(GL_ARRAY_BUFFER, 0)
		glUseProgram(0)
