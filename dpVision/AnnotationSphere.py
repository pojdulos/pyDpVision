# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 13:15:53 2023

@author: darek
"""

from .annotation import Annotation
from .sphere import Sphere
import OpenGL.GL as gl
import math

class AnnotationSphere(Annotation,Sphere):
	def __init__(self, parent=None):
		# super( AnnotationSphere, self ).__init__( parent )
		Annotation.__init__(self, parent)
		Sphere.__init__(self)  
		self.m_lats = 32
		self.m_longs = 32

	def drawSphere(self):
		gl.glTranslatef(self.m_c[0], self.m_c[1], self.m_c[2])
		for i in range(self.m_lats+1):
			lat0 = math.pi * (-0.5 + float(i - 1) / self.m_lats)
			z0 = math.sin(lat0)
			zr0 = math.cos(lat0)
	
			lat1 = math.pi * (-0.5 + float(i) / self.m_lats)
			z1 = math.sin(lat1)
			zr1 = math.cos(lat1)
	
			gl.glBegin(gl.GL_QUAD_STRIP)
			for j in range (self.m_longs+1):
				lng = 2 * math.pi * float(j - 1) / self.m_longs
				x = math.cos(lng)
				y = math.sin(lng)
	
				gl.glNormal3f(x * zr0, y * zr0, z0);
				gl.glVertex3f(self.m_r * x * zr0, self.m_r * y * zr0, self.m_r * z0);
				gl.glNormal3f(x * zr1, y * zr1, z1);
				gl.glVertex3f(self.m_r * x * zr1, self.m_r * y * zr1, self.m_r * z1);
			gl.glEnd()
	
	def renderSelf(self):
		gl.glPushMatrix();
		gl.glPushAttrib(gl.GL_ALL_ATTRIB_BITS);
	
		gl.glDisable(gl.GL_TEXTURE_2D);
		gl.glEnable(gl.GL_COLOR_MATERIAL);
	
		gl.glColorMaterial(gl.GL_FRONT_AND_BACK, gl.GL_AMBIENT_AND_DIFFUSE);
	
		gl.glEnable(gl.GL_CULL_FACE);
		gl.glCullFace(gl.GL_FRONT);
	
# 		//drawAxes();
	
		if self.m_checked:
			gl.glColor4ub(self.m_selcolor.red(),self.m_selcolor.green(),self.m_selcolor.blue(),self.m_selcolor.alpha())
		else:
			gl.glColor4ub(self.m_color.red(),self.m_color.green(),self.m_color.blue(),self.m_color.alpha())

		self.drawSphere();
	
		gl.glPopAttrib();
		gl.glPopMatrix();
