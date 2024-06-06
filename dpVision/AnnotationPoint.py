# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 13:15:53 2023

@author: darek
"""

from .annotation import Annotation

import OpenGL.GL as gl
import math

class AnnotationPoint(Annotation):
	def __init__(self, point=[0.0,0.0,0.0], vector=None, parent=None):
		Annotation.__init__(self, parent)
		self.m_point = point
		self.m_vector = vector
		self.m_showVector = not vector is None

	def setPoint(self, point):
		self.m_point = point

	def getPoint(self):
		return self.m_point

	def setVector(self, vector=None, show=True):
		self.m_vector = vector
		self.m_showVector = show and not vector is None

	def getVector(self):
		return self.m_vector

	def showVector(self, show):
		self.m_showVector = show and not self.m_vector is None

	def renderSelf(self):
		gl.glPushMatrix()
		gl.glPushAttrib(gl.GL_ALL_ATTRIB_BITS)
	
		gl.glDisable(gl.GL_TEXTURE_2D)
		gl.glEnable(gl.GL_COLOR_MATERIAL)
	
		gl.glColorMaterial(gl.GL_FRONT_AND_BACK, gl.GL_AMBIENT_AND_DIFFUSE)
	
		gl.glEnable(gl.GL_CULL_FACE)
		gl.glCullFace(gl.GL_FRONT)
	
		gl.glEnable(gl.GL_POINT_SMOOTH)
		gl.glPointSize( 9 )
		
		if self.m_checked:
			gl.glColor4ub(self.m_selcolor.red(),self.m_selcolor.green(),self.m_selcolor.blue(),self.m_selcolor.alpha())
		else:
			gl.glColor4ub(self.m_color.red(),self.m_color.green(),self.m_color.blue(),self.m_color.alpha())

		gl.glTranslatef(self.m_point[0], self.m_point[1], self.m_point[2])
		gl.glBegin(gl.GL_POINTS)

		gl.glVertex3f(0.0, 0.0, 0.0)
		gl.glEnd()
		
		if self.m_showVector and not self.m_vector is None:
			gl.glColor3f(1.0, 1.0, 0.0)
			
			gl.glLineWidth(1.0)
			gl.glBegin(gl.GL_LINES)
			gl.glVertex3f(0.0, 0.0, 0.0)
			gl.glVertex3f(10.0 * self.m_vector[0], 10.0 * self.m_vector[1], 10.0 * self.m_vector[2])
			gl.glEnd()

			gl.glLineWidth(3.0)
			gl.glBegin(gl.GL_LINES)
			gl.glVertex3f(9.6 * self.m_vector[0], 9.6 * self.m_vector[1], 9.6 * self.m_vector[2])
			gl.glVertex3f(9.8 * self.m_vector[0], 9.8 * self.m_vector[1], 9.8 * self.m_vector[2])
			gl.glEnd()

			gl.glLineWidth(5.0)
			gl.glBegin(gl.GL_LINES)
			gl.glVertex3f(9.4 * self.m_vector[0], 9.4 * self.m_vector[1], 9.4 * self.m_vector[2])
			gl.glVertex3f(9.6 * self.m_vector[0], 9.6 * self.m_vector[1], 9.6 * self.m_vector[2])
			gl.glEnd()

		gl.glDisable(gl.GL_POINT_SMOOTH)
			
		gl.glPopAttrib()
		gl.glPopMatrix()
