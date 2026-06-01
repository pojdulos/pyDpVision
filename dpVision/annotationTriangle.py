# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 13:15:53 2023

@author: darek
"""

from .annotation import Annotation
from .mesh import Mesh
from OpenGL.GL import *
import numpy as np

class AnnotationTriangle(Annotation):
	def __init__(self, parent=None,
			  		pA=[0.0,0.0,0.0],
					pB=[0.0,0.0,0.0],
					pC=[0.0,0.0,0.0],
                    color=[0,255,255,128],
                    selcolor=[255,0,0,128]):
		Annotation.__init__(self, parent, color, selcolor)
		self._pA = list(pA)
		self._pB = list(pB)
		self._pC = list(pC)
		self._mesh_cache = None
		self._is_initialized = False

	# --- dostęp do wierzchołków z automatyczną invalidacją ---

	@property
	def m_pA(self):
		return self._pA

	@m_pA.setter
	def m_pA(self, value):
		self._pA = list(value)
		self._mark_geometry_dirty()

	@property
	def m_pB(self):
		return self._pB

	@m_pB.setter
	def m_pB(self, value):
		self._pB = list(value)
		self._mark_geometry_dirty()

	@property
	def m_pC(self):
		return self._pC

	@m_pC.setter
	def m_pC(self, value):
		self._pC = list(value)
		self._mark_geometry_dirty()

	# --- cache geometrii ---

	def _mark_geometry_dirty(self):
		self._is_initialized = False
		self._mesh_cache = None

	def _build_mesh_geometry(self):
		mesh = Mesh.create(
			vertices=[list(self._pA), list(self._pB), list(self._pC)],
			faces=[[0, 1, 2]],
		)
		mesh.label = getattr(self, 'label', 'AnnotationTriangle')
		mesh.description = getattr(self, 'description', '')
		mesh.b_renderSmooth = False
		mesh.gl_renderAs = GL_TRIANGLES
		return mesh

	def _ensure_geometry(self):
		if not self._is_initialized:
			self._mesh_cache = self._build_mesh_geometry()
			self._is_initialized = True

	def _sync_mesh_material(self):
		self._ensure_geometry()
		qcolor = self._active_qcolor()
		material = self._mesh_cache.materials[self._mesh_cache.currentMaterial]
		material.diffuse = [qcolor.redF(), qcolor.greenF(), qcolor.blueF()]
		material.alpha = qcolor.alphaF()

	# --- rendering ---

	def render_wboit(self, pass_idx):
		self._sync_mesh_material()
		self._mesh_cache.render_wboit(pass_idx)

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
		self._mesh_cache.renderSelf()

		# Punkty w wierzchołkach
		glPushAttrib(GL_ALL_ATTRIB_BITS)
		glPointSize(5)
		glColor4ub(
			self._active_qcolor().red(),
			self._active_qcolor().green(),
			self._active_qcolor().blue(),
			self._active_qcolor().alpha(),
		)
		glEnable(GL_POINT_SMOOTH)
		glBegin(GL_POINTS)
		glVertex3f(*self._pA)
		glVertex3f(*self._pB)
		glVertex3f(*self._pC)
		glEnd()
		glPopAttrib()

		if self.is_transparent and self.transparent_outline_enabled():
			self.render_outline()

		if self.m_showWireframe:
			self._render_wireframe()

	def render_outline(self):
		self._ensure_geometry()

		glPushMatrix()
		glPushAttrib(GL_ALL_ATTRIB_BITS)
		glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
		glLineWidth(2.0)
		glColor4f(*self._active_outline_rgba())
		self._mesh_cache.renderSelf()
		glPopAttrib()
		glPopMatrix()

	def _render_wireframe(self):
		glPushAttrib(GL_ALL_ATTRIB_BITS)
		glDisable(GL_TEXTURE_2D)
		glDisable(GL_LIGHTING)
		glLineWidth(1.0)
		glColor4f(*self._active_outline_rgba())
		glBegin(GL_LINE_LOOP)
		glVertex3f(*self._pA)
		glVertex3f(*self._pB)
		glVertex3f(*self._pC)
		glEnd()
		glPopAttrib()
