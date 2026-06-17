# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 13:15:53 2023

@author: darek
"""

from .annotation import Annotation
import OpenGL.GL as gl
import math

class AnnotationPath(Annotation):
	def __init__(self, points=[], parent=None):
		Annotation.__init__(self, parent)
		self.m_width = 1.0
		self.m_points = points

	def addPoint(self, point):
		self.m_points.append(point)

	def renderSelf(self):
		gl.glPushMatrix()
		gl.glPushAttrib(gl.GL_ALL_ATTRIB_BITS)
	
		gl.glDisable(gl.GL_TEXTURE_2D)
		gl.glPolygonMode(gl.GL_FRONT, gl.GL_LINE)
		gl.glPolygonMode(gl.GL_BACK, gl.GL_LINE)

		gl.glEnable(gl.GL_COLOR_MATERIAL)
		gl.glColorMaterial(gl.GL_FRONT_AND_BACK, gl.GL_AMBIENT_AND_DIFFUSE)
	
		if self.checked:
			gl.glColor4ub(self.m_selcolor.red(),self.m_selcolor.green(),self.m_selcolor.blue(),self.m_selcolor.alpha())
		else:
			gl.glColor4ub(self.m_color.red(),self.m_color.green(),self.m_color.blue(),self.m_color.alpha())

		gl.glLineWidth(self.m_width)

		gl.glBegin(gl.GL_LINE_STRIP)

		for point in self.m_points:
			gl.glVertex3fv(point)
		
		gl.glEnd()
		
		gl.glDisable(gl.GL_COLOR_MATERIAL)
			
		gl.glPopAttrib()
		gl.glPopMatrix()
