# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 13:15:53 2023

@author: darek
"""

from .annotation import Annotation
from OpenGL.GL import *
import math

class AnnotationTriangle(Annotation):
	def __init__(self, pA=[0.0,0.0,0.0], pB=[0.0,0.0,0.0],pC=[0.0,0.0,0.0], parent=None):
		Annotation.__init__(self, parent)
		self.m_pA = pA
		self.m_pB = pB
		self.m_pC = pC

	def renderSelf(self):
		glPushMatrix()
		glPushAttrib(GL_ALL_ATTRIB_BITS)

		glDisable(GL_TEXTURE_2D)
		glEnable(GL_COLOR_MATERIAL)

		glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

		glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

		if self.m_checked:
			glColor4ub(self.m_selcolor.red(),self.m_selcolor.green(),self.m_selcolor.blue(),self.m_selcolor.alpha())
		else:
			glColor4ub(self.m_color.red(),self.m_color.green(),self.m_color.blue(),self.m_color.alpha())

		glBegin(GL_TRIANGLES)
		glVertex3f(self.m_pA[0], self.m_pA[1], self.m_pA[2])
		glVertex3f(self.m_pB[0], self.m_pB[1], self.m_pB[2])
		glVertex3f(self.m_pC[0], self.m_pC[1], self.m_pC[2])
		glEnd()


		glPointSize(5)

		if self.m_checked:
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
