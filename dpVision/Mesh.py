# -*- coding: utf-8 -*-
"""
Created on Mon Nov 27 11:53:31 2023

@author: pojdulos
"""
from PyQt5.QtGui import *
from OpenGL.GL import *
import numpy as np
import math


from dpVision.PointCloud import PointCloud
from dpVision.Shaders import Mesh_vertex_shader_code, Mesh_fragment_shader_code, compile_shader


def Face(a,b,c):
	return np.array([a, b, c], dtype=np.uint)

class Mesh(PointCloud):
	def __init__(self, parent=None):
		super( Mesh, self ).__init__( parent )
		self.m_faces = np.empty((0, 3), dtype=np.uint)
		self.m_fnormals = np.empty((0, 3), dtype=np.float32)
		self.ebo = None
		self.shader_program = None

	def addFace(self, a, b, c):
		self.m_faces = np.vstack([self.m_faces, Face(a, b, c)])

	def addFaceX(self, dane):
		a, b, c = dane[0], dane[1], dane[2]
		lastIDX = self.addFace(a, b, c) #, col);
		for i in range(3, len(dane)):
			b = c
			c = dane[i]
			lastIDX = self.addFace(a, b, c) #, col);
		return lastIDX;

	@staticmethod
	def getNormal(v0, v1, v2):
		# wektor f.A->f.B
		v01 = v1 - v0
	
		# wektor f.A->f.C
		v02 = v2 - v0
	
		# iloczyn wektorowy
		cross_product = np.cross(v01, v02)
	
		# Normalizacja
		norm = np.linalg.norm(cross_product)
		vn = cross_product / norm if norm != 0 else cross_product
	
		return vn


	def test(self):
		self.addVertex(-5.0, -5.0, 0.0)
		self.addVertex(-5.0, 5.0, 0.0)
		self.addVertex(5.0, 5.0, 0.0)
		self.addVertex(5.0, -5.0, 0.0)

		self.addFace(0, 1, 2)
		self.addFace(2, 3, 0)
		
		return self

	@staticmethod
	def test2():
		phi = (1.0 + math.sqrt(5.0)) / 2.0
	
		vertices = [ [1, 1, 1],
			[1, 1, -1],
			[1, -1, 1],
			[1, -1, -1],
			[-1, 1, 1],
			[-1, 1, -1],
			[-1, -1, 1],
			[-1, -1, -1],
			[0, 1 / phi, phi],
			[0, 1 / phi, -phi],
			[0, -1 / phi, phi],
			[0, -1 / phi, -phi],
			[1 / phi, phi, 0],
			[1 / phi, -phi, 0],
			[-1 / phi, phi, 0],
			[-1 / phi, -phi, 0],
			[phi, 0, 1 / phi],
			[phi, 0, -1 / phi],
			[-phi, 0, 1 / phi],
			[-phi, 0, -1 / phi]]
	
		faces5 = [ [0, 12, 14, 4,8 ],
			[0, 16, 17, 1, 12 ],
			[0, 8, 10, 2,16 ],
			[1,9,5,14,12],
			[1,17,3,11,9],
			[2,13,3,17,16],
			[2,10,6,15,13],
			[3,13,15,7,11],
			[4,18,6,10,8],
			[4,14,5,19,18],
			[5,9,11,7,19],
			[6,18,19,7,15] ]
	
		mesh = Mesh()
	
		# Dodawanie wierzchołków
		for i in range(20):
			mesh.addVertex(vertices[i][0], vertices[i][1], vertices[i][2])
	
		# Dodawanie ścian
		for i in range(12):
			mesh.addFaceX([faces5[i][0], faces5[i][1], faces5[i][2], faces5[i][3], faces5[i][4]])

		return mesh

	def recalcFNormals(self):
		# Krok 1: Ekstrakcja współrzędnych wierzchołków
		v0_indices = self.m_faces[:, 0]
		v1_indices = self.m_faces[:, 1]
		v2_indices = self.m_faces[:, 2]
		
		v0 = self.m_vertices[v0_indices]
		v1 = self.m_vertices[v1_indices]
		v2 = self.m_vertices[v2_indices]
		
		# Krok 2: Obliczanie wektorów krawędziowych
		v01 = v1 - v0
		v02 = v2 - v0
		
		# Krok 3: Iloczyn wektorowy i normalizacja
		cross_products = np.cross(v01, v02)
		norms = np.linalg.norm(cross_products, axis=1)
		self.m_fnormals = (cross_products.T / norms).T  # Normalizacja dla każdej normalnej
		
		# Zapobieganie dzieleniu przez zero
		self.m_fnormals[np.isnan(self.m_fnormals)] = 0

	def setDefaultColor(self):
		glMaterialfv(GL_FRONT, GL_AMBIENT, [0.2, 0.2, 0.2, 1.0] )
		glMaterialfv(GL_FRONT, GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0] )
		glMaterialfv(GL_FRONT, GL_SPECULAR, [0.0, 0.0, 0.0, 1.0] )
		glMaterialfv(GL_FRONT, GL_EMISSION, [0.0, 0.0, 0.0, 1.0] )
		glMaterialf(GL_FRONT, GL_SHININESS, 0.0 )
		
	def renderOldStyle(self):
		if not len(self.m_faces):
			PointCloud.renderSelf(self)
		else:	
			glPushMatrix();
			glPushAttrib(GL_ALL_ATTRIB_BITS);
		
			glEnable(GL_COLOR_MATERIAL);
			self.setDefaultColor()

			glEnable(GL_POINT_SMOOTH)
			#glPointSize( 5 )
			
			glPolygonMode(GL_FRONT, GL_FILL)
			glPolygonMode(GL_BACK, GL_LINE)
			
			hasFN = len(self.m_fnormals) == len(self.m_faces)
			hasVN = len(self.m_vnormals) == len(self.m_vertices)
			hasVC = len(self.m_vcolors) == len(self.m_vertices)
			
			glShadeModel(GL_SMOOTH)
			
			glBegin(GL_TRIANGLES)
			for i in range(len(self.m_faces)):
				f = self.m_faces[i]
				v0, v1, v2 = self.m_vertices[f[0]], self.m_vertices[f[1]], self.m_vertices[f[2]]
				if hasVN:
					n0, n1, n2 = self.m_vnormals[f[0]], self.m_vnormals[f[1]], self.m_vnormals[f[2]]
					glNormal3f(n0[0], n0[1], n0[2])
				if hasVC:
					c0, c1, c2 = self.m_vcolors[f[0]], self.m_vcolors[f[1]], self.m_vcolors[f[2]]
					glColor4ub(c0[0], c0[1], c0[2], c0[3])
				glVertex3f(v0[0], v0[1], v0[2])
				if hasVN:
					glNormal3f(n1[0], n1[1], n1[2])
				if hasVC:
					glColor4ub(c1[0], c1[1], c1[2], c1[3])
				glVertex3f(v1[0], v1[1], v1[2])
				if hasVN:
					glNormal3f(n2[0], n2[1], n2[2])
				if hasVC:
					glColor4ub(c2[0], c2[1], c2[2], c2[3])
				glVertex3f(v2[0], v2[1], v2[2])
			glEnd()
		
			glDisable(GL_COLOR_MATERIAL);
		
			glPopAttrib();
			glPopMatrix();



	def renderWithShaders(self):
		if not len(self.m_faces):
			PointCloud.renderSelf(self)
		else:	
			if self.shader_program is None:
				# Inicjalizacja i konfiguracja shaderów
				vertex_shader = compile_shader(Mesh_vertex_shader_code, GL_VERTEX_SHADER)
				fragment_shader = compile_shader(Mesh_fragment_shader_code, GL_FRAGMENT_SHADER)
				
				# Tworzenie programu shaderów
				self.shader_program = glCreateProgram()
				glAttachShader(self.shader_program, vertex_shader)
				glAttachShader(self.shader_program, fragment_shader)
				glLinkProgram(self.shader_program)
				
				# Sprawdzanie, czy program został powiązany poprawnie
				if not glGetProgramiv(self.shader_program, GL_LINK_STATUS):
					print(glGetProgramInfoLog(self.shader_program))
					raise Exception("Error linking shaders")
				
				# Usuwanie shaderów (już nie są potrzebne po powiązaniu programu)
				glDeleteShader(vertex_shader)
				glDeleteShader(fragment_shader)

			# Używanie programu shaderów
			glUseProgram(self.shader_program)
				
			# Przygotowanie VBOs i EBO
			if self.vbo is None:
				self.vbo = glGenBuffers(1)
			glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
			glBufferData(GL_ARRAY_BUFFER, self.m_vertices.nbytes, self.m_vertices, GL_STATIC_DRAW)
			
			if self.cvbo is None:
				self.cvbo = glGenBuffers(1)
			glBindBuffer(GL_ARRAY_BUFFER, self.cvbo)

			if self.m_vcolors.shape[0] == self.m_vertices.shape[0]:
				colors = self.m_vcolors
			else:
				colors = np.array((len(self.m_vertices),4), dtype=np.ubyte)
			glBufferData(GL_ARRAY_BUFFER, colors.nbytes, colors, GL_STATIC_DRAW)
				
			if self.nvbo is None:
				self.nvbo = glGenBuffers(1)
			glBindBuffer(GL_ARRAY_BUFFER, self.nvbo)
			
			if self.m_vnormals.shape[0] == self.m_vertices.shape[0]:
				normals = self.m_vnormals
			else:
				normals = np.array((len(self.m_vertices),3), dtype=np.float32)
			glBufferData(GL_ARRAY_BUFFER, normals.nbytes, normals, GL_STATIC_DRAW)
			
			if self.ebo is None:
				self.ebo = glGenBuffers(1)
			glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
			glBufferData(GL_ELEMENT_ARRAY_BUFFER, self.m_faces.nbytes, self.m_faces, GL_STATIC_DRAW)
			
			# Konfiguracja atrybutów wierzchołków
			glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
			glVertexAttribPointer(0, 3, GL_FLOAT, False, 0, None)
			glEnableVertexAttribArray(0)

			glBindBuffer(GL_ARRAY_BUFFER, self.cvbo)
			glVertexAttribPointer(1, 4, GL_UNSIGNED_BYTE, True, 0, None)
			glEnableVertexAttribArray(1)

			glBindBuffer(GL_ARRAY_BUFFER, self.nvbo)
			glVertexAttribPointer(2, 3, GL_FLOAT, True, 0, None)
			glEnableVertexAttribArray(2)

			model_loc = glGetUniformLocation(self.shader_program, "model")
			view_loc = glGetUniformLocation(self.shader_program, "view")
			projection_loc = glGetUniformLocation(self.shader_program, "projection")
			
			model = np.array((4,4),dtype=np.float32)
			projection = np.array((4,4),dtype=np.float32)
			
			glGetFloatv(GL_MODELVIEW_MATRIX, model)
			glGetFloatv(GL_PROJECTION_MATRIX, projection)
			
			view = np.array([[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]], dtype=np.float32)
			
			glUniformMatrix4fv(model_loc, 1, GL_FALSE, model)
			glUniformMatrix4fv(view_loc, 1, GL_FALSE, view)
			glUniformMatrix4fv(projection_loc, 1, GL_FALSE, projection)

			useVColors_loc = glGetUniformLocation(self.shader_program, "useVColors")
			if self.m_vcolors.shape[0] == self.m_vertices.shape[0]:
				glUniform1i(useVColors_loc, 1)
			else:
				glUniform1i(useVColors_loc, 0)
			
			useVNormals_loc = glGetUniformLocation(self.shader_program, "useVNormals")
			if self.m_vnormals.shape[0] == self.m_vertices.shape[0]:
				glUniform1i(useVNormals_loc, 1)
			else:
				glUniform1i(useVNormals_loc, 0)
			
			# Renderowanie
			glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
			glDrawElements(GL_TRIANGLES, len(self.m_faces) * 3, GL_UNSIGNED_INT, None)
			
			# Oczyszczanie
			glBindBuffer(GL_ARRAY_BUFFER, 0)
			glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
			
			glDisableVertexAttribArray(0)
			glDisableVertexAttribArray(1)
			glDisableVertexAttribArray(2)
			
			glUseProgram(0) # Wyłączenie programu shaderów

	def renderSelf(self):
		glEnable(GL_COLOR_MATERIAL)
		glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
		glShadeModel(GL_SMOOTH)
		#self.renderOldStyle()
		self.renderWithShaders()
		glDisable(GL_COLOR_MATERIAL)
		

