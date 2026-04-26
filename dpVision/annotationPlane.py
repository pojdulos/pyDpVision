# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 13:15:53 2023

@author: darek
"""

from .annotation import Annotation
from OpenGL.GL import *
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
	def __init__(self, parent=None, pC=(0.0,0.0,0.0), pN=(0.0,0.0,1.0), size=(10,10),
                    color=[0,255,255,128],
                    selcolor=[255,0,0,128]):
		Annotation.__init__(self, parent, color, selcolor)
		self.m_center = pC
		self._corners = None   # (4, 3) float32, relative to center
		self._vbo = None
		self._is_initialized = False
		self.m_grid_u = 4
		self.m_grid_v = 4
		self.normal_vector = pN
		self.setSize(size)

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
			self._mark_geometry_dirty()
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
		self._mark_geometry_dirty()
	

	def setSize(self, _size):
		if isinstance(_size, numbers.Number):
			self.m_size = (_size, _size)

		elif isinstance(_size, str):
			print("String:", _size)

		else:
			try:
				t = tuple(_size)
				if len(t) == 1:
					self.m_size = (t[0], t[0])
				elif len(t) >= 2:
					self.m_size = (t[0], t[1])
				else:
					raise ValueError("Pusta sekwencja dla rozmiaru!")
			except TypeError:
				raise TypeError(f"Nieobsługiwany typ dla setSize: {type(_size)}")
		self._mark_geometry_dirty()

	# --- cache geometrii ---

	def _mark_geometry_dirty(self):
		self._is_initialized = False
		self._corners = None

	def _build_corners(self):
		"""Oblicza 4 rogi plastra w układzie lokalnym (względem centrum)."""
		normal = np.asarray(self.m_normal, dtype=np.float64)
		norm = np.linalg.norm(normal)
		if norm < 1e-6:
			normal = np.array([0.0, 0.0, 1.0])
		else:
			normal = normal / norm

		W, H = self.m_size

		if abs(normal[0]) < 0.9:
			tmp = np.array([1.0, 0.0, 0.0])
		else:
			tmp = np.array([0.0, 1.0, 0.0])

		v1 = tmp - np.dot(tmp, normal) * normal
		if np.linalg.norm(v1) < 1e-6:
			tmp = np.array([0.0, 0.0, 1.0])
			v1 = tmp - np.dot(tmp, normal) * normal
		v1 = v1 / np.linalg.norm(v1) * (W / 2.0)
		v2_raw = np.cross(normal, v1)
		v2 = v2_raw / np.linalg.norm(v2_raw) * (H / 2.0)

		# kolejność zgodna z GL_QUADS: obejście CCW
		return np.array([
			 v1 + v2,
			-v1 + v2,
			-v1 - v2,
			 v1 - v2,
		], dtype=np.float32)

	def _ensure_geometry(self):
		if not self._is_initialized:
			self._corners = self._build_corners()
			self._is_initialized = True

	def _upload_vbo(self, verts):
		"""Ładuje/aktualizuje VBO z tablicą wierzchołków (4×3 float32)."""
		if self._vbo is None:
			self._vbo = glGenBuffers(1)
		glBindBuffer(GL_ARRAY_BUFFER, self._vbo)
		glBufferData(GL_ARRAY_BUFFER, verts.nbytes, verts, GL_DYNAMIC_DRAW)

	def _render_normal_line(self):
		"""Rysuje żółtą linię wzdłuż wektora normalnego (przestrzeń lokalna)."""
		normal = np.asarray(self.m_normal, dtype=np.float64)
		if np.linalg.norm(normal) < 1e-6:
			return
		glLineWidth(1)
		glColor3f(1.0, 1.0, 0.0)
		glBegin(GL_LINES)
		glVertex3f(0.0, 0.0, 0.0)
		glVertex3f(*(5.0 * normal))
		glEnd()

	# --- rendering ---

	def _render_wireframe(self):
		self._ensure_geometry()
		v1 = (self._corners[0] - self._corners[1]) / 2.0
		v2 = (self._corners[0] - self._corners[3]) / 2.0

		glPushMatrix()
		glPushAttrib(GL_ALL_ATTRIB_BITS)
		glDisable(GL_TEXTURE_2D)
		glDisable(GL_LIGHTING)
		glLineWidth(1.0)
		glColor4f(*self._active_outline_rgba())
		glTranslatef(self.m_center[0], self.m_center[1], self.m_center[2])

		nu, nv = self.m_grid_u, self.m_grid_v
		glBegin(GL_LINES)
		for i in range(nu + 1):
			t = i / nu * 2.0 - 1.0
			start = t * v1 - v2
			end   = t * v1 + v2
			glVertex3f(*start); glVertex3f(*end)
		for j in range(nv + 1):
			t = j / nv * 2.0 - 1.0
			start = -v1 + t * v2
			end   =  v1 + t * v2
			glVertex3f(*start); glVertex3f(*end)
		glEnd()

		glPopAttrib()
		glPopMatrix()

	def render_wboit(self, pass_idx):
		self._ensure_geometry()
		center = np.asarray(self.m_center, dtype=np.float32)
		verts = self._corners + center   # (4, 3) — absolutne pozycje

		prog = self._prepare_wboit_shader(pass_idx)
		if prog is None:
			return

		self._upload_vbo(verts)
		glEnableVertexAttribArray(0)
		glVertexAttribPointer(0, 3, GL_FLOAT, False, 0, None)
		glDrawArrays(GL_QUADS, 0, 4)
		glDisableVertexAttribArray(0)
		glBindBuffer(GL_ARRAY_BUFFER, 0)
		glUseProgram(0)

	def renderSelf(self):
		from .globals import AP

		if AP.wboit_pass is not None:
			if AP.wboit_pass >= 0:
				if self.is_transparent:
					self.render_wboit(AP.wboit_pass)
				return
			if self.is_transparent:
				if self.transparent_outline_enabled():
					self.render_outline()
				if self.m_showWireframe:
					self._render_wireframe()

		glPushMatrix()
		glPushAttrib(GL_ALL_ATTRIB_BITS)

		glDisable(GL_TEXTURE_2D)
		glEnable(GL_COLOR_MATERIAL)
		glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

		qcolor = self._active_qcolor()
		glColor4ub(qcolor.red(), qcolor.green(), qcolor.blue(), qcolor.alpha())

		glTranslatef(self.m_center[0], self.m_center[1], self.m_center[2])

		glBegin(GL_QUADS)
		for p in self._corners:
			glVertex3f(*p)
		glEnd()

		self._render_normal_line()

		glPopAttrib()
		glPopMatrix()

		if self.is_transparent and self.transparent_outline_enabled():
			self.render_outline()

		if self.m_showWireframe:
			self._render_wireframe()

	def render_outline(self):
		self._ensure_geometry()

		glPushMatrix()
		glPushAttrib(GL_ALL_ATTRIB_BITS)
		glDisable(GL_TEXTURE_2D)
		glDisable(GL_BLEND)
		glLineWidth(2.0)
		glColor4f(*self._active_outline_rgba())
		glTranslatef(self.m_center[0], self.m_center[1], self.m_center[2])

		glBegin(GL_LINE_LOOP)
		for p in self._corners:
			glVertex3f(*p)
		glEnd()

		glPopAttrib()
		glPopMatrix()
