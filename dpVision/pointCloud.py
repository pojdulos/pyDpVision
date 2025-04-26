# -*- coding: utf-8 -*-
"""
Created on Mon Nov 27 10:05:30 2023

@author: pojdulos
"""

from .object import Object
from PyQt5.QtGui import *
from OpenGL.GL import *
import numpy as np
from .shaders import create_program

def Vertex(pt=None, x=0., y=0., z=0.):
	if pt and isinstance(pt, list) and len(pt)==3:
		return np.array(pt, dtype=np.float32)
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
	
	def invert_normals(self):
		if self.m_vnormals.shape[0] == self.m_vertices.shape[0]:
			self.m_vnormals = -self.m_vnormals
			return True	
		return False
	
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
		
	def initializeGL(self):
		# --- przygotuj VBO na punkty (wierzchołki + kolory) ---
		self.vertex_vbo = glGenBuffers(1)
		self.color_vbo = glGenBuffers(1)

		self.shader_program = create_program(vertex_shader_name='pointCloud.vert', fragment_shader_name='pointCloud.frag')

		# vertices = np.array(self.m_projected_vertices, dtype=np.float32)
		glBindBuffer(GL_ARRAY_BUFFER, self.vertex_vbo)
		glBufferData(GL_ARRAY_BUFFER, self.m_vertices.nbytes, self.m_vertices, GL_DYNAMIC_DRAW)

		colors = np.array(self.m_vcolors, dtype=np.uint8)
		glBindBuffer(GL_ARRAY_BUFFER, self.color_vbo)
		glBufferData(GL_ARRAY_BUFFER, colors.nbytes, colors, GL_STATIC_DRAW)
			
		glBindBuffer(GL_ARRAY_BUFFER, 0)

		# if self.m_edges:
		# 	self.edge_vbo = glGenBuffers(1)
		# 	edge_indices = np.array(self.m_edges, dtype=np.uint32).flatten()

		# 	glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.edge_vbo)
		# 	glBufferData(GL_ELEMENT_ARRAY_BUFFER, edge_indices.nbytes, edge_indices, GL_DYNAMIC_DRAW)

		# 	glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

	def renderSelf(self):
		if not hasattr(self, "shader_program") or self.shader_program is None:
			self.initializeGL()
		
		# if self.buf_changed:
		# 	self.update_vertex_buffer()
		# 	self.buf_changed = False

		use_uniform_color = len(self.m_vcolors) < len(self.m_vertices)

		# Używaj własnego shader program (przypuśćmy self.shaderProgram)
		glUseProgram(self.shader_program)

		# --- Punkty ---
		glEnable(GL_POINT_SMOOTH)
		glEnable(GL_PROGRAM_POINT_SIZE)
		glPointSize(1)

		glBindBuffer(GL_ARRAY_BUFFER, self.vertex_vbo)
		glEnableVertexAttribArray(0)  # a_position
		glVertexAttribPointer(0, 3, GL_FLOAT, False, 0, None)

		if not use_uniform_color:
			glBindBuffer(GL_ARRAY_BUFFER, self.color_vbo)
			glEnableVertexAttribArray(1)
			glVertexAttribPointer(1, 4, GL_UNSIGNED_BYTE, True, 0, None)
		else:
			# wyłączam a_color!
			glDisableVertexAttribArray(1)

		modelview = np.array(glGetFloatv(GL_MODELVIEW_MATRIX), dtype=np.float32)
		projection = np.array(glGetFloatv(GL_PROJECTION_MATRIX), dtype=np.float32)

		mvp_loc = glGetUniformLocation(self.shader_program, "u_mvp")
		glUniformMatrix4fv(mvp_loc, 1, GL_FALSE, modelview @ projection)

		u_use_u_color_loc = glGetUniformLocation(self.shader_program, "u_use_u_color")
		glUniform1i(u_use_u_color_loc, int(use_uniform_color))			

		u_color_loc = glGetUniformLocation(self.shader_program, "u_color")
		glUniform4f(u_color_loc, 0.6, 0.6, 0.6, 1.0)			

		# print("Drawing", len(self.m_projected_vertices), "points")
		glDrawArrays(GL_POINTS, 0, len(self.m_vertices))

		# --- Krawędzie ---
		# if self.m_edges and len(self.m_edges):
		# 	glLineWidth(2.0)
		# 	glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.edge_vbo)
		# 	glDrawElements(GL_LINES, len(self.m_edges)*2, GL_UNSIGNED_INT, None)

		# Clean up
		glBindBuffer(GL_ARRAY_BUFFER, 0)
		glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
		glDisableVertexAttribArray(0)
		glDisableVertexAttribArray(1)

		glUseProgram(0)





	def export_as_obj(self, obj_file_name='v:/fast_test.obj'):
		objFile = open(obj_file_name, 'w')
		objFile.write(f"# .obj file created with pyDpVision\n\n")
		for pt in self.m_vertices:
			txt = f"v {pt[0]:.6f} {pt[1]:.6f} {pt[2]:.6f}\n"
			objFile.write(txt)
		objFile.close()
