# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 13:15:53 2023

@author: darek
"""

from .annotation import Annotation
from OpenGL.GL import *
import math
import numpy as np

class AnnotationTriangle(Annotation):
	def __init__(self, parent=None,
			  		pA=[0.0,0.0,0.0],
					pB=[0.0,0.0,0.0],
					pC=[0.0,0.0,0.0],
                    color=[0,255,255,128],
                    selcolor=[255,0,0,128]):
		Annotation.__init__(self, parent, color, selcolor)
		self.m_pA = pA
		self.m_pB = pB
		self.m_pC = pC
		self._wboit_vbo = None

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
				return

		glPushMatrix()
		glPushAttrib(GL_ALL_ATTRIB_BITS)

		glDisable(GL_TEXTURE_2D)
		glEnable(GL_COLOR_MATERIAL)

		glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

		glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

		if self.checked:
			glColor4ub(self.m_selcolor.red(),self.m_selcolor.green(),self.m_selcolor.blue(),self.m_selcolor.alpha())
		else:
			glColor4ub(self.m_color.red(),self.m_color.green(),self.m_color.blue(),self.m_color.alpha())

		glBegin(GL_TRIANGLES)
		glVertex3f(self.m_pA[0], self.m_pA[1], self.m_pA[2])
		glVertex3f(self.m_pB[0], self.m_pB[1], self.m_pB[2])
		glVertex3f(self.m_pC[0], self.m_pC[1], self.m_pC[2])
		glEnd()


		glPointSize(5)

		if self.checked:
			glColor4ub(self.m_selcolor.red(),self.m_selcolor.green(),self.m_selcolor.blue(),self.m_selcolor.alpha())
		else:
			glColor4ub(self.m_color.red(),self.m_color.green(),self.m_color.blue(),self.m_color.alpha())

		glEnable(GL_POINT_SMOOTH)
		glBegin(GL_POINTS)
		glVertex3f(self.m_pA[0], self.m_pA[1], self.m_pA[2])
		glVertex3f(self.m_pB[0], self.m_pB[1], self.m_pB[2])
		glVertex3f(self.m_pC[0], self.m_pC[1], self.m_pC[2])
		glEnd()

		glPopAttrib()
		glPopMatrix()

		if self.is_transparent and self.transparent_outline_enabled():
			self.render_outline()

	def render_wboit(self, pass_idx):
		prog = self._prepare_wboit_shader(pass_idx)
		if prog is None:
			return

		vertices = np.array([self.m_pA, self.m_pB, self.m_pC], dtype=np.float32)
		if self._wboit_vbo is None:
			self._wboit_vbo = glGenBuffers(1)
		glBindBuffer(GL_ARRAY_BUFFER, self._wboit_vbo)
		glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_DYNAMIC_DRAW)
		glEnableVertexAttribArray(0)
		glVertexAttribPointer(0, 3, GL_FLOAT, False, 0, None)
		glDrawArrays(GL_TRIANGLES, 0, 3)
		glDisableVertexAttribArray(0)
		glBindBuffer(GL_ARRAY_BUFFER, 0)
		glUseProgram(0)

	def render_outline(self):
		glPushMatrix()
		glPushAttrib(GL_ALL_ATTRIB_BITS)
		glDisable(GL_TEXTURE_2D)
		glDisable(GL_BLEND)
		glEnable(GL_COLOR_MATERIAL)
		glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
		glLineWidth(2.0)
		glColor4f(*self._active_outline_rgba())
		glBegin(GL_LINE_LOOP)
		glVertex3f(self.m_pA[0], self.m_pA[1], self.m_pA[2])
		glVertex3f(self.m_pB[0], self.m_pB[1], self.m_pB[2])
		glVertex3f(self.m_pC[0], self.m_pC[1], self.m_pC[2])
		glEnd()
		glPopAttrib()
		glPopMatrix()
