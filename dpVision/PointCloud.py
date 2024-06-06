# -*- coding: utf-8 -*-
"""
Created on Mon Nov 27 10:05:30 2023

@author: pojdulos
"""

from .object import Object
from PyQt5.QtGui import *
from OpenGL.GL import *
import numpy as np


def Vertex(x,y,z):
	return np.array([x, y, z], dtype=np.float32)


class PointCloud(Object):
	def __init__(self, parent=None):
		super( PointCloud, self ).__init__( parent )
		self.m_vertices = np.empty((0, 3), dtype=np.float32)
		self.m_vcolors = np.empty((0, 4), dtype=np.ubyte)
		self.m_vnormals = np.empty((0, 3), dtype=np.float32)
		self.v_vbo = None
		self.c_vbo = None
		self.n_vbo = None
		
	def addVertex(self, x, y, z):
		self.m_vertices = np.vstack([self.m_vertices, Vertex(x, y, z)])
	
	# def getCenterOfWeight(self):
	# 	ctr = [0., 0., 0.]
	# 	if len(self.m_vertices)>0:
	# 		for v in self.m_vertices:
	# 			ctr[0] += v[0]
	# 			ctr[1] += v[1]
	# 			ctr[2] += v[2]

	# 		ctr[0] /= len(self.m_vertices)
	# 		ctr[1] /= len(self.m_vertices)
	# 		ctr[2] /= len(self.m_vertices)
	# 	return ctr

	def getCenterOfWeight(self):
		ctr = [0., 0., 0.]
		num_vertices = len(self.m_vertices)
		if num_vertices:
			sums = [sum(dim) for dim in zip(*self.m_vertices)]
			ctr = [total / num_vertices for total in sums]
		return ctr

	def getBB(self):
		_b, _min, _max = Object.getBB()  # Pobieranie BB z klasy nadrzędnej
		if _b:  # Jeśli BB istnieje w klasie nadrzędnej
			if len(self.m_vertices) > 0:  # Sprawdzenie, czy są wierzchołki w aktualnej klasie
				_min = [min(dim) for dim in zip(_min, *self.m_vertices)]
				_max = [max(dim) for dim in zip(_max, *self.m_vertices)]
		else:  # Jeśli BB nie istnieje w klasie nadrzędnej
			if len(self.m_vertices) > 0:  # Sprawdzenie, czy są wierzchołki w aktualnej klasie
				_min = [min(dim) for dim in zip(*self.m_vertices)]
				_max = [max(dim) for dim in zip(*self.m_vertices)]
			_b = True  # Zaktualizowanie flagi _b
		return _b, _min, _max

	def getCenterOfBB(self):
		ctr = [0., 0., 0.]
		num_vertices = len(self.m_vertices)
		if num_vertices:
			_min = [min(dim) for dim in zip(*self.m_vertices)]
			_max = [max(dim) for dim in zip(*self.m_vertices)]
			ctr = [(m1 + m2) / 2 for m1, m2 in zip(_min, _max)]
		return ctr

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

