# -*- coding: utf-8 -*-
"""
Created on Mon Nov 27 10:05:30 2023

@author: pojdulos
"""

from .object import Object
from PyQt5.QtGui import *
from OpenGL.GL import *
import numpy as np



# def Vertex(pt=None):
# 	if pt and isinstance(pt, list) and len(pt)==self.m_dimensions:
# 		return np.array(pt, dtype=np.float32)
# 	return np.array([x, y, z], dtype=np.float32)

# Macierz obrotu wokół płaszczyzny xw
def rotation_matrix_xw(theta):
    return np.array([
        [np.cos(theta), 0, 0, -np.sin(theta)],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [np.sin(theta), 0, 0, np.cos(theta)]
    ])

# Funkcja rzutowania perspektywicznego
def project_to_3d_perspective(vertex_4d, d):
    x, y, z, w = vertex_4d
    factor = d / (d - w)  # klasyczna perspektywa (punkt w oddali → mniejsze)
    return np.array([x * factor, y * factor, z * factor])



class NDimCloud(Object):
	def __init__(self, dim=3, parent=None):
		super( NDimCloud, self ).__init__( parent )
		self.m_dimensions = dim
		self.m_vertices = np.empty((0, self.m_dimensions), dtype=np.float32)
		self.m_projected_vertices = np.empty((0, 3), dtype=np.float32)
		self.m_vcolors = np.empty((0, 4), dtype=np.ubyte)
		# self.m_vnormals = np.empty((0, self.m_dimensions), dtype=np.float32)
		# self.m_edges = generate_edges(self.m_vertices)
		self.v_vbo = None
		self.c_vbo = None
		self.n_vbo = None
		

	def compute_edges(self):
		self.m_edges = []
		for i in range(len(self.m_vertices)):
			for j in range(i + 1, len(self.m_vertices)):
				if np.sum(self.m_vertices[i] != self.m_vertices[j]) == 1:
					self.m_edges.append((i, j))
	
	def addVertex(self, pt):
		if pt and isinstance(pt, list) and len(pt)==self.m_dimensions:
			self.m_vertices = np.vstack([self.m_vertices, np.array(pt, dtype=np.float32)])
	
	# def invert_normals(self):
	# 	if self.m_vnormals.shape[0] == self.m_vertices.shape[0]:
	# 		self.m_vnormals = -self.m_vnormals
	# 		return True	
	# 	return False
	
	def getCenterOfWeight(self):
		if not self.m_vertices:
			return [0.0 for _ in range(self.m_dimensions)]  # lub po prostu pustą listę []

		num_vertices = len(self.m_vertices)
		dim_sums = [sum(dim) for dim in zip(*self.m_vertices)]
		return [s / num_vertices for s in dim_sums]

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
		if not self.m_vertices:
			return [0.0 for _ in range(self.m_dimensions)]

		dims = list(zip(*self.m_vertices))
		return [(min(d) + max(d)) / 2 for d in dims]

	def projectTo3D(self):
			# Przykład: rzutowanie pierwszych 3 wymiarów (ortogonalne)
			self.m_projected_vertices = np.array([
				vertex[:3] if len(vertex) >= 3 else vertex + [0]*(3 - len(vertex))
				for vertex in self.m_vertices
			])

	# Funkcja rzutowania perspektywicznego
	def project_to_3d_perspective(self, vertex_4d, d):
		x, y, z, w = vertex_4d
		epsilon = 1e-5
		denom = d - w
		if abs(denom) < epsilon:
			denom = epsilon if denom >= 0 else -epsilon
		factor = d / denom
		return np.array([x * factor, y * factor, z * factor])
	
	def update_projection(self, rotation_matrix, d=2.0):
		# obrót + rzutowanie perspektywiczne
		self.m_projected_vertices = [
			self.project_to_3d_perspective(np.dot(rotation_matrix, np.array(v)), d)
			for v in self.m_vertices
		]


	# def renderSelf(self):
	# 	glPushMatrix()
	# 	glPushAttrib(GL_ALL_ATTRIB_BITS)
	
	# 	glEnable(GL_COLOR_MATERIAL)
	
	# 	glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
	
	# 	glEnable(GL_POINT_SMOOTH)
	# 	glPointSize( 3 )
		
	# 	glBegin(GL_POINTS)
	# 	for i in range(len(self.m_vertices)):
	# 		v = self.m_projected_vertices[i]
	# 		#c = self.m_vcolors[i]
	# 		#glColor4ub(c[0], c[1], c[2], c[3])
	# 		glVertex3f(v[0], v[1], v[2])
	# 	glEnd()
	
	# 	glDisable(GL_COLOR_MATERIAL)
	
	# 	glPopAttrib()
	# 	glPopMatrix()

	def renderSelf(self):
		glPushMatrix()
		glPushAttrib(GL_ALL_ATTRIB_BITS)

		glEnable(GL_COLOR_MATERIAL)
		glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

		glEnable(GL_POINT_SMOOTH)
		glPointSize(3)

		# --- PUNKTY ---
		# glBegin(GL_POINTS)
		# for v in self.m_projected_vertices:
		# 	glVertex3f(v[0], v[1], v[2])
		# glEnd()

		# --- KRAWĘDZIE ---
		glColor3f(0.6, 0.6, 0.6)  # szary kolor linii
		glLineWidth(1.0)
		glBegin(GL_LINES)
		for i, j in self.m_edges:
			vi = self.m_projected_vertices[i]
			vj = self.m_projected_vertices[j]
			glVertex3f(vi[0], vi[1], vi[2])
			glVertex3f(vj[0], vj[1], vj[2])
		glEnd()

		glDisable(GL_COLOR_MATERIAL)
		glPopAttrib()
		glPopMatrix()

	def export_as_obj(self, obj_file_name='v:/fast_test.obj'):
		objFile = open(obj_file_name, 'w')
		objFile.write(f"# .obj file created with pyDpVision\n\n")
		for pt in self.m_vertices:
			txt = f"v {pt[0]:.6f} {pt[1]:.6f} {pt[2]:.6f}\n"
			objFile.write(txt)
		objFile.close()
