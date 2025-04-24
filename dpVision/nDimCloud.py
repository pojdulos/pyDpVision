# -*- coding: utf-8 -*-
"""
Created on Mon Nov 27 10:05:30 2023

@author: pojdulos
"""

from dpVision import AP
from .object import Object
from PyQt5.QtGui import *
from OpenGL.GL import *
import numpy as np
import itertools



class NDimCloud(Object):
	def __init__(self, headers=None, dims=None, parent=None):
		super( NDimCloud, self ).__init__( parent )
		
		if headers is None:
			self.m_dimensions = 3 if dims is None else dims
			self.m_headers = [f"unnamed_{i}" for i in range(self.m_dimensions)]
		else:
			self.m_dimensions = len(headers)
			self.m_headers = headers
		
		self.m_vertices = np.empty((0, self.m_dimensions), dtype=np.float32)
		self.m_projected_vertices = np.empty((0, 3), dtype=np.float32)
		self.m_vcolors = np.empty((0, 4), dtype=np.ubyte)
		# self.m_vnormals = np.empty((0, self.m_dimensions), dtype=np.float32)
		# self.m_edges = generate_edges(self.m_vertices)
		self.m_edges = None
		self.m_current_ix = 30
		self.m_current_iy = 30
		self.m_real_dims = [0, 1, 2, 3]
		self.m_gains = [1.0, 1.0, 1.0, 1.0]
		self.v_vbo = None
		self.c_vbo = None
		self.n_vbo = None
		

	def compute_edges(self):
		self.m_edges = []
		for i in range(len(self.m_vertices)):
			for j in range(i + 1, len(self.m_vertices)):
				diff = np.abs(self.m_vertices[i] - self.m_vertices[j])
				num_different = np.sum(diff > 1e-3)
				if num_different == 1 and np.any(np.isclose(diff, 20.0)):
					self.m_edges.append((i, j))

	# tu jest [x,y,z,...]	
	def addVertex(self, pt):
		if pt and isinstance(pt, list) and len(pt)==self.m_dimensions:
			self.m_vertices = np.vstack([self.m_vertices, np.array(pt, dtype=np.float32)])

	# tu jest [[x,y,z,...],[x,y,z,...],...]
	def addVertices(self, pts):
		if pts and isinstance(pts, list) and len(pts) and len(pts[0])==self.m_dimensions:
			self.m_vertices = np.vstack([self.m_vertices, np.array(pts, dtype=np.float32)])


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


	def project_nd_to_3d(self, vertex_nd, d=50, blend=0.5):
		x, y, z = vertex_nd[ self.m_real_dims[0]]*self.m_gains[0], vertex_nd[self.m_real_dims[1]]*self.m_gains[1], vertex_nd[self.m_real_dims[2]]*self.m_gains[2]
		if self.m_real_dims[3] is not None:
			w = vertex_nd[self.m_real_dims[3]]*self.m_gains[3]
			factor = d / max(d - w, 1e-3)
			px, py, pz = x * factor, y * factor, z * factor
			return np.array([
				x * (1 - blend) + px * blend,
				y * (1 - blend) + py * blend,
				z * (1 - blend) + pz * blend
			], dtype=np.float32)
		else:
			return np.array([x, y, z], dtype=np.float32)


	def update_projection(self, rotation_matrix, d=50.0, blend=0.5):
		self.m_projected_vertices = [
			self.project_nd_to_3d(np.dot(rotation_matrix, np.array(v)), d, blend)
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
		glPointSize(7)

		# --- PUNKTY ---
		# glColor3f(1.0, 0.0, 0.0)
		glBegin(GL_POINTS)
		for i,v in enumerate(self.m_projected_vertices):
			if len(self.m_vcolors) > i:
				glColor3ub(self.m_vcolors[i][0], self.m_vcolors[i][1], self.m_vcolors[i][2])
			glVertex3f(v[0], v[1], v[2])
		glEnd()

		if self.m_edges and len(self.m_edges):
			# --- KRAWĘDZIE ---
			# glColor3f(0.6, 0.6, 0.6)  # szary kolor linii
			glLineWidth(2.0)
			glBegin(GL_LINES)
			for i, j in self.m_edges:
				vi = self.m_projected_vertices[i]
				vj = self.m_projected_vertices[j]
				
				if len(self.m_vcolors) > i:
					glColor3ub(self.m_vcolors[i][0], self.m_vcolors[i][1], self.m_vcolors[i][2])
				glVertex3f(vi[0], vi[1], vi[2])
				
				if len(self.m_vcolors) > j:
					glColor3ub(self.m_vcolors[j][0], self.m_vcolors[j][1], self.m_vcolors[j][2])
				glVertex3f(vj[0], vj[1], vj[2])
			glEnd()

		glDisable(GL_COLOR_MATERIAL)
		glPopAttrib()
		glPopMatrix()

	# def export_as_obj(self, obj_file_name='v:/fast_test.obj'):
	# 	objFile = open(obj_file_name, 'w')
	# 	objFile.write(f"# .obj file created with pyDpVision\n\n")
	# 	for pt in self.m_vertices:
	# 		txt = f"v {pt[0]:.6f} {pt[1]:.6f} {pt[2]:.6f}\n"
	# 		objFile.write(txt)
	# 	objFile.close()

	@staticmethod
	def hypercube(dim=4, size=1.0):
		def compute_edges(vertices):
			edges = []
			for i in range(len(vertices)):
				for j in range(i + 1, len(vertices)):
					diff = np.abs(vertices[i] - vertices[j])
					num_different = np.sum(diff > 1e-3)
					if num_different == 1 and np.any(np.isclose(diff, 20.0)):
						edges.append((i, j))
			return edges

		coords = list(itertools.product([-1, 1], repeat=dim))

		cld = NDimCloud(dims=dim)
		cld.m_vertices = np.array(coords, dtype=np.float32) * size
		cld.m_edges = compute_edges(cld.m_vertices)
		return cld

	def rotation_matrix_nd(self, i, j, theta):
		"""
		Zwraca macierz obrotu w wymiarze `dim`,
		obracającą o kąt `theta` w płaszczyźnie (i, j).
		"""
		assert 0 <= i < j < self.m_dimensions, "Nieprawidłowe indeksy osi"

		R = np.identity(self.m_dimensions, dtype=np.float32)

		cos_t = np.cos(theta)
		sin_t = np.sin(theta)

		R[i, i] = cos_t
		R[j, j] = cos_t
		R[i, j] = -sin_t
		R[j, i] = sin_t

		return R

	# def set_rotation(self, i, axes, total):
	# 	theta = 2 * np.pi * i / total
	# 	R = self.rotation_matrix_nd(axes[0], axes[1], theta)
	# 	self.update_projection(R, d=50)


	def projectTo3D(self, total = 360):
		thetaX = 2 * np.pi * self.m_current_ix / total
		Rx = self.rotation_matrix_nd(0, 3, thetaX)
		
		thetaY = 2 * np.pi * self.m_current_iy / total
		Ry = self.rotation_matrix_nd(1, 3, thetaY)
		
		R = Ry @ Rx

		self.update_projection(R, d=50)


	def on_mouse_move(self, dx, dy):
		total = 360

		if dx:
			self.m_current_ix += ( 3 if dx<0 else -3 ) % total
		
		if dy:
			self.m_current_iy += ( 3 if dy>0 else -3 ) % total
		
		self.projectTo3D(total)

		AP.updateProperties()
		AP.updateAllViews()

