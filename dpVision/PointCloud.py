# -*- coding: utf-8 -*-
"""
Created on Mon Nov 27 10:05:30 2023

@author: pojdulos
"""

from .Object import Object
from PyQt5.QtGui import *
from OpenGL.GL import *
import numpy as np


def Vertex(x,y,z):
	return np.array([x, y, z], dtype=np.float32)


class PointCloud(Object):
	def __init__(self, parent=None):
		super( PointCloud, self ).__init__( parent )
		self.m_vertices = np.empty((0, 3), dtype=np.float32)
		self.m_vnormals = np.empty((0, 3), dtype=np.float32)
		self.m_vcolors = np.empty((0, 4), dtype=np.ubyte)
		self.v_vbo = None
		self.n_vbo = None
		self.c_vbo = None
		
	def addVertex(self, x, y, z):
		self.m_vertices = np.vstack([self.m_vertices, Vertex(x, y, z)])
		
	def test(self):
		self.m_vertices = np.vstack([self.m_vertices, Vertex(10, 10, 1)])
		self.m_vcolors = np.vstack([self.m_vcolors, [255, 255, 0, 255]])
		
		self.m_vertices = np.vstack([self.m_vertices, Vertex(10, -10, 1)])
		self.m_vcolors = np.vstack([self.m_vcolors, [255, 0, 0, 255]])
		
		self.m_vertices = np.vstack([self.m_vertices, Vertex(-10, -10, 1)])
		self.m_vcolors = np.vstack([self.m_vcolors, [0, 255, 0, 255]])
		
		self.m_vertices = np.vstack([self.m_vertices, Vertex(-10, 10, 1)])
		self.m_vcolors = np.vstack([self.m_vcolors, [0, 0, 255, 255]])
		
		return self
		
	def renderSelf2(self):
		glPushMatrix();
		glPushAttrib(GL_ALL_ATTRIB_BITS);
	
		glEnable(GL_COLOR_MATERIAL);
	
		glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE);
	
		glEnable(GL_POINT_SMOOTH)
		glPointSize( 1 )
		
		glBegin(GL_POINTS)
		for i in range(len(self.m_vertices)):
			v = self.m_vertices[i]
			#c = self.m_vcolors[i]
			#glColor4ub(c[0], c[1], c[2], c[3])
			glVertex3f(v[0], v[1], v[2]);
		glEnd()
	
		glDisable(GL_COLOR_MATERIAL);
	
		glPopAttrib();
		glPopMatrix();
	
	def renderSelf(self):
		glPushMatrix();
		glPushAttrib(GL_ALL_ATTRIB_BITS);
	
		glEnable(GL_COLOR_MATERIAL);
		glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE);
	
		glEnable(GL_POINT_SMOOTH)
		glPointSize( 1 )
		
		# Tworzenie VBO
		if self.v_vbo is None:
			self.v_vbo = glGenBuffers(1)
			
		glBindBuffer(GL_ARRAY_BUFFER, self.v_vbo)
		glBufferData(GL_ARRAY_BUFFER, self.m_vertices, GL_STATIC_DRAW)
		
		# Konfiguracja atrybutów wierzchołka
		glEnableVertexAttribArray(0)  # np. dla pozycji wierzchołka
		glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
		
		# Renderowanie
		glDrawArrays(GL_POINTS, 0, len(self.m_vertices))

		glBindBuffer(GL_ARRAY_BUFFER, 0)
	
		glDisable(GL_POINT_SMOOTH)
		glDisable(GL_COLOR_MATERIAL);
	
		glPopAttrib();
		glPopMatrix();

