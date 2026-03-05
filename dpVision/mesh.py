# -*- coding: utf-8 -*-
"""
Created on Mon Nov 27 11:53:31 2023

@author: pojdulos
"""
from PyQt5.QtGui import *
from OpenGL.GL import *
import numpy as np
import math
import os

from .pointCloud import PointCloud
from .shaders import load_and_compile_shader

def Face(a,b,c):
	return np.array([a, b, c], dtype=np.uint)

class Mesh(PointCloud):
	class Material:
		def __init__(self):
			self.ambient = [0.2, 0.2, 0.2]
			self.diffuse = [0.6, 0.6, 0.6]
			self.specular = [0.0, 0.0, 0.0]
			self.alpha = 1.0
			self.shinines = 0.0
			self.dTexFileName = ''
			self.dTexture = None

		def hasTexture(self):
			return not self.dTexture is None #and self.m_tindices.shape[0] and self.m_tcoords.shape[0]

	def __init__(self, parent=None):
		super( Mesh, self ).__init__( parent )
		self.m_faces = np.empty((0, 3), dtype=np.uint)
		self.m_fcolors = np.empty((0, 4), dtype=np.ubyte)
		self.m_fnormals = np.empty((0, 3), dtype=np.float32)
		self.m_tcoords = np.empty((0, 2), dtype=np.float32)
		self.m_tindices = np.empty((0, 3), dtype=np.uint)
		self.b_renderTexture = True
		self.b_renderSmooth = True
		self.gl_renderAs = GL_TRIANGLES

		self.t_vbo = None
		self.texture = None
		self.ebo = None
		self.shader_program = None
		self.vBuf = None
		self.cBuf = None
		self.nBuf = None
		self.tBuf = None
		self.materials = {
			'' : Mesh.Material() # default material
		}
		self.currentMaterial = ''

	def addFace(self, face, ti=None):
		self.m_faces = np.vstack([self.m_faces, face])
		if ti is not None and len(ti) == len(face):
			self.m_tindices = np.vstack([self.m_tindices, ti])

	def triangulate(self, vertices):
		triangles = []
		for i in range(1, len(vertices) - 1):
			triangle = [vertices[0], vertices[i], vertices[i + 1]]
			triangles.append(triangle)
		return triangles

	def addFaceX(self, face, ti=None):
		def add_faces(faces, tis=None):
			if tis is not None:
				self.m_faces = np.vstack([self.m_faces] + faces)
				self.m_tindices = np.vstack([self.m_tindices] + tis)
			else:
				self.m_faces = np.vstack([self.m_faces] + faces)

		if ti is not None and len(ti) != len(face):
			raise ValueError("number of texture indices do not match face indices")

		if len(face) > 3:
			new_faces = self.triangulate(face)
			new_tis = self.triangulate(ti) if ti and len(ti) == len(face) else None
			add_faces(new_faces, new_tis)
		else:
			add_faces([face], [ti] if ti and len(ti) == len(face) else None)

	# def addFaceX(self, face, ti=None):
	# 	def add_faces(faces, tis=None):
	# 		last_idx = None
	# 		for f in faces:
	# 			t = tis.pop(0) if tis else None
	# 			last_idx = self.addFace(face=f, ti=t)
	# 		return last_idx

	# 	if ti is not None and len(ti) != len(face):
	# 		raise ValueError("number of texture indices do not match face indices")

	# 	if len(face) > 3:
	# 		new_faces = self.triangulate(face)
	# 		new_tis = self.triangulate(ti) if ti and len(ti) == len(face) else None
	# 		return add_faces(new_faces, new_tis)
	# 	else:
	# 		return add_faces([face], [ti] if ti and len(ti) == len(face) else None)

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

	def calcFN(self):
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
		norms[norms == 0] = 1  # Zapobieganie dzieleniu przez zero
		self.m_fnormals = (cross_products.T / norms).T  # Normalizacja dla każdej normalnej

	def triangleArea(self, pA, pB, pC):
		vAB = np.array(pB) - np.array(pA)
		vAC = np.array(pC) - np.array(pA)
		cross_product = np.cross(vAB, vAC)
		area = 0.5 * np.linalg.norm(cross_product)
		return area

	def calcVN(self, weighted=True):
		# Wyodrębnienie współrzędnych wierzchołków dla każdej ściany
		pA = self.m_vertices[self.m_faces[:, 0]]
		pB = self.m_vertices[self.m_faces[:, 1]]
		pC = self.m_vertices[self.m_faces[:, 2]]

		# # Obliczanie wektorów tworzących ściany
		# vAB = pB - pA
		# vAC = pC - pA

		# # Obliczanie normalnych za pomocą iloczynu wektorowego
		# normals = np.cross(vAB, vAC)

		vAB = self.m_vertices[self.m_faces[:, 1]] - self.m_vertices[self.m_faces[:, 0]]
		vAC = self.m_vertices[self.m_faces[:, 2]] - self.m_vertices[self.m_faces[:, 0]]

		# Debugging shapes
		print("vAB shape:", vAB.shape)
		print("vAC shape:", vAC.shape)

		# Ensure shapes are valid for cross product
		if vAB.shape[-1] not in (2, 3) or vAC.shape[-1] not in (2, 3):
			raise ValueError("vAB and vAC must be 2D or 3D vectors")

		normals = np.cross(vAB, vAC)


		if not weighted:
			normals_lengths = np.linalg.norm(normals, axis=1)
			normals_lengths[normals_lengths == 0] = 1  # Zapobieganie dzieleniu przez zero
			normals = normals / normals_lengths[:, np.newaxis]

		# Inicjalizacja tymczasowej tablicy normalnych
		tmpN = np.zeros((len(self.m_vertices), 3), dtype=np.float32)

		# Sumowanie normalnych dla wierzchołków
		for i in range(3):  # Dla każdego wierzchołka w trójkącie
			np.add.at(tmpN, self.m_faces[:, i], normals)

		# Normalizacja normalnych
		norms = np.linalg.norm(tmpN, axis=1)
		norms[norms == 0] = 1  # Zapobieganie dzieleniu przez zero
		self.m_vnormals = tmpN / norms[:, np.newaxis]


	def renderWithShaders2(self):
		if getattr(self, '_shader_failed', False):
			return
		if self.shader_program is None:
			# Inicjalizacja i konfiguracja shaderów
			
			try:
				vertex_shader = load_and_compile_shader('mesh.vert', GL_VERTEX_SHADER)
				fragment_shader = load_and_compile_shader('mesh.frag', GL_FRAGMENT_SHADER)
			except Exception as e:
				print( e )
				self._shader_failed = True
				return
			
			# Tworzenie programu shaderów
			program = glCreateProgram()
			glAttachShader(program, vertex_shader)
			glAttachShader(program, fragment_shader)
			glLinkProgram(program)
			
			# Sprawdzanie, czy program został powiązany poprawnie
			if not glGetProgramiv(program, GL_LINK_STATUS):
				print(glGetProgramInfoLog(program))
				glDeleteProgram(program)
				self._shader_failed = True
				return
			
			self.shader_program = program
			
			# Usuwanie shaderów (już nie są potrzebne po powiązaniu programu)
			glDeleteShader(vertex_shader)
			glDeleteShader(fragment_shader)

		# Używanie programu shaderów
		glUseProgram(self.shader_program)

		# Porównuję liczbę wierszy w tablicach:
		drawVN = self.m_vnormals.shape[0] == self.m_vertices.shape[0]
		drawFN = self.m_fnormals.shape[0] == self.m_faces.shape[0]
		drawN = drawVN or drawFN
		drawVC = self.m_vcolors.shape[0] == self.m_vertices.shape[0]
		drawFC = self.m_fcolors.shape[0] == self.m_faces.shape[0]
		drawC = drawVC or drawFC
		drawT = self.b_renderTexture \
				and self.materials[self.currentMaterial].hasTexture() \
				and self.m_tindices.shape[0] == self.m_faces.shape[0]

		if self.vBuf is None:
			_vBuf = []
			_cBuf = []
			_nBuf = []
			for idx, f in enumerate(self.m_faces):
				v = [ self.m_vertices[f[0]], self.m_vertices[f[1]], self.m_vertices[f[2]] ]
				_vBuf.append(v)
				if drawVC:
					c = [ self.m_vcolors[f[0]], self.m_vcolors[f[1]], self.m_vcolors[f[2]] ]
					_cBuf.append(c)
				elif drawFC:
					c = [ self.m_fcolors[idx], self.m_fcolors[idx], self.m_fcolors[idx] ]
					_cBuf.append(c)
				if drawVN:
					n = [ self.m_vnormals[f[0]], self.m_vnormals[f[1]], self.m_vnormals[f[2]] ]
					_nBuf.append(n)
				elif drawFN:
					n = [ self.m_fnormals[idx], self.m_fnormals[idx], self.m_fnormals[idx] ]
					_nBuf.append(n)
			self.vBuf = np.array(_vBuf, dtype=np.float32)
			if drawC:
				self.cBuf = np.array(_cBuf, dtype=np.ubyte)
			if drawN:
				self.nBuf = np.array(_nBuf, dtype=np.float32)

		if drawT:
			if self.tBuf is None:		
				_tBuf = []
				for i in self.m_tindices:
					t = [ self.m_tcoords[i[0]], self.m_tcoords[i[1]], self.m_tcoords[i[2]] ]
					_tBuf.append(t)

				self.tBuf = np.array(_tBuf, dtype=np.float32)

		if self.v_vbo is None:
			self.v_vbo = glGenBuffers(1)
		glBindBuffer(GL_ARRAY_BUFFER, self.v_vbo)
		glBufferData(GL_ARRAY_BUFFER, self.vBuf.nbytes, self.vBuf, GL_STATIC_DRAW)

		useVColors_loc = glGetUniformLocation(self.shader_program, "useVColors")
		dC = self.materials[self.currentMaterial].diffuse + [self.materials[self.currentMaterial].alpha]
#		dC = [1.0, 0.5, 0.5, 0.8]
		loc = glGetUniformLocation(self.shader_program, "myColor")
		glUniform4f(loc, dC[0], dC[1], dC[2], dC[3] )
		if drawC:
			if self.c_vbo is None:
				self.c_vbo = glGenBuffers(1)
			glBindBuffer(GL_ARRAY_BUFFER, self.c_vbo)
			glBufferData(GL_ARRAY_BUFFER, self.cBuf.nbytes, self.cBuf, GL_STATIC_DRAW)
			glUniform1i(useVColors_loc, 1)
		else:
			glUniform1i(useVColors_loc, 0)
		
		useVNormals_loc = glGetUniformLocation(self.shader_program, "useVNormals")
		if drawN:
			if self.n_vbo is None:
				self.n_vbo = glGenBuffers(1)
			glBindBuffer(GL_ARRAY_BUFFER, self.n_vbo)
			glBufferData(GL_ARRAY_BUFFER, self.nBuf.nbytes, self.nBuf, GL_STATIC_DRAW)
			glUniform1i(useVNormals_loc, 1)
		else:
			glUniform1i(useVNormals_loc, 0)

		useTexture_loc = glGetUniformLocation(self.shader_program, "useTexture")
		if drawT:
			glActiveTexture(GL_TEXTURE0)
			glBindTexture(GL_TEXTURE_2D, self.materials[self.currentMaterial].dTexture.textureId())
			glUniform1i(glGetUniformLocation(self.shader_program, "texture1"), 0)

			if self.t_vbo is None:
				self.t_vbo = glGenBuffers(1)
			glBindBuffer(GL_ARRAY_BUFFER, self.t_vbo)
			glBufferData(GL_ARRAY_BUFFER, self.tBuf.nbytes, self.tBuf, GL_STATIC_DRAW)
			glUniform1i(useTexture_loc, 1)
		else:
			glUniform1i(useTexture_loc, 0)

		###############

		useFlatShading_loc = glGetUniformLocation(self.shader_program, "useFlatShading")
		if self.b_renderSmooth:
			glUniform1i(useFlatShading_loc, 0)
		else:
			glUniform1i(useFlatShading_loc, 1)


		glBindBuffer(GL_ARRAY_BUFFER, self.v_vbo)
		glVertexAttribPointer(0, 3, GL_FLOAT, False, 0, None)
		glEnableVertexAttribArray(0)

		if drawC:
			glBindBuffer(GL_ARRAY_BUFFER, self.c_vbo)
			glVertexAttribPointer(1, 4, GL_UNSIGNED_BYTE, True, 0, None)
			glEnableVertexAttribArray(1)

		if drawN:
			glBindBuffer(GL_ARRAY_BUFFER, self.n_vbo)
			glVertexAttribPointer(2, 3, GL_FLOAT, True, 0, None)
			glEnableVertexAttribArray(2)

		if drawT:
			glBindBuffer(GL_ARRAY_BUFFER, self.t_vbo)
			glVertexAttribPointer(3, 2, GL_FLOAT, False, 0, None)
			glEnableVertexAttribArray(3)

		###############

		model_loc = glGetUniformLocation(self.shader_program, "model")
		view_loc = glGetUniformLocation(self.shader_program, "view")
		projection_loc = glGetUniformLocation(self.shader_program, "projection")
		
		model = np.array([[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]], dtype=np.float32)
		projection = np.array([[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]], dtype=np.float32)
		view = np.array([[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]], dtype=np.float32)

		glGetFloatv(GL_MODELVIEW_MATRIX, model)
		glGetFloatv(GL_PROJECTION_MATRIX, projection)
		
		glUniformMatrix4fv(model_loc, 1, GL_FALSE, model)
		glUniformMatrix4fv(view_loc, 1, GL_FALSE, view)
		glUniformMatrix4fv(projection_loc, 1, GL_FALSE, projection)

		glDrawArrays(GL_TRIANGLES, 0, len(self.vBuf) * 3)

		glBindBuffer(GL_ARRAY_BUFFER, 0)

		glDisableVertexAttribArray(0)
		if drawC:
			glDisableVertexAttribArray(1)
		if drawN:
			glDisableVertexAttribArray(2)
		if drawT:
			glDisableVertexAttribArray(3)

		glUseProgram(0) # Wyłączenie programu shaderów


	# def renderWithShaders(self):
	# 	if self.shader_program is None:
	# 		# Inicjalizacja i konfiguracja shaderów
	# 		vertex_shader = compile_shader(Mesh_vertex_shader_code, GL_VERTEX_SHADER)
	# 		fragment_shader = compile_shader(Mesh_fragment_shader_code, GL_FRAGMENT_SHADER)
			
	# 		# Tworzenie programu shaderów
	# 		self.shader_program = glCreateProgram()
	# 		glAttachShader(self.shader_program, vertex_shader)
	# 		glAttachShader(self.shader_program, fragment_shader)
	# 		glLinkProgram(self.shader_program)
			
	# 		# Sprawdzanie, czy program został powiązany poprawnie
	# 		if not glGetProgramiv(self.shader_program, GL_LINK_STATUS):
	# 			print(glGetProgramInfoLog(self.shader_program))
	# 			raise Exception("Error linking shaders")
			
	# 		# Usuwanie shaderów (już nie są potrzebne po powiązaniu programu)
	# 		glDeleteShader(vertex_shader)
	# 		glDeleteShader(fragment_shader)

	# 	# Używanie programu shaderów
	# 	glUseProgram(self.shader_program)

	# 	drawN = self.m_vnormals.shape[0] == self.m_vertices.shape[0]
	# 	drawC = self.m_vcolors.shape[0] == self.m_vertices.shape[0]

	# 	# Przygotowanie VBOs i EBO
	# 	if self.vbo is None:
	# 		self.vbo = glGenBuffers(1)
	# 	glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
	# 	glBufferData(GL_ARRAY_BUFFER, self.m_vertices.nbytes, self.m_vertices, GL_STATIC_DRAW)

	# 	if drawC:		
	# 		if self.cvbo is None:
	# 			self.cvbo = glGenBuffers(1)
	# 		glBindBuffer(GL_ARRAY_BUFFER, self.cvbo)
	# 		glBufferData(GL_ARRAY_BUFFER, self.m_vcolors.nbytes, self.m_vcolors, GL_STATIC_DRAW)
			
	# 	if drawN:
	# 		if self.nvbo is None:
	# 			self.nvbo = glGenBuffers(1)
	# 		glBindBuffer(GL_ARRAY_BUFFER, self.nvbo)
	# 		glBufferData(GL_ARRAY_BUFFER, self.m_vnormals.nbytes, self.m_vnormals, GL_STATIC_DRAW)


	# 	if self.ebo is None:
	# 		self.ebo = glGenBuffers(1)
	# 	glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
	# 	glBufferData(GL_ELEMENT_ARRAY_BUFFER, self.m_faces.nbytes, self.m_faces, GL_STATIC_DRAW)


	# 	# Konfiguracja atrybutów wierzchołków
	# 	glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
	# 	glVertexAttribPointer(0, 3, GL_FLOAT, False, 0, None)
	# 	glEnableVertexAttribArray(0)

	# 	useVColors_loc = glGetUniformLocation(self.shader_program, "useVColors")
	# 	if drawC:
	# 		glBindBuffer(GL_ARRAY_BUFFER, self.cvbo)
	# 		glVertexAttribPointer(1, 4, GL_UNSIGNED_BYTE, True, 0, None)
	# 		glEnableVertexAttribArray(1)
	# 		glUniform1i(useVColors_loc, 1)
	# 	else:
	# 		glUniform1i(useVColors_loc, 0)

	# 	useVNormals_loc = glGetUniformLocation(self.shader_program, "useVNormals")
	# 	if drawN:
	# 		glBindBuffer(GL_ARRAY_BUFFER, self.nvbo)
	# 		glVertexAttribPointer(2, 3, GL_FLOAT, True, 0, None)
	# 		glEnableVertexAttribArray(2)
	# 		glUniform1i(useVNormals_loc, 1)
	# 	else:
	# 		glUniform1i(useVNormals_loc, 0)

	# 	useTexture_loc = glGetUniformLocation(self.shader_program, "useTexture")
	# 	glUniform1i(useTexture_loc, 0)

	# 	model_loc = glGetUniformLocation(self.shader_program, "model")
	# 	view_loc = glGetUniformLocation(self.shader_program, "view")
	# 	projection_loc = glGetUniformLocation(self.shader_program, "projection")
		
	# 	model = np.array((4,4),dtype=np.float32)
	# 	projection = np.array((4,4),dtype=np.float32)
		
	# 	glGetFloatv(GL_MODELVIEW_MATRIX, model)
	# 	glGetFloatv(GL_PROJECTION_MATRIX, projection)
		
	# 	view = np.array([[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]], dtype=np.float32)
		
	# 	glUniformMatrix4fv(model_loc, 1, GL_FALSE, model)
	# 	glUniformMatrix4fv(view_loc, 1, GL_FALSE, view)
	# 	glUniformMatrix4fv(projection_loc, 1, GL_FALSE, projection)

		
	# 	# Renderowanie
	# 	glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
	# 	glDrawElements(GL_TRIANGLES, len(self.m_faces) * 3, GL_UNSIGNED_INT, None)
		
	# 	# Oczyszczanie
	# 	glBindBuffer(GL_ARRAY_BUFFER, 0)
	# 	glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
		
	# 	glDisableVertexAttribArray(0)
	# 	if drawC:
	# 		glDisableVertexAttribArray(1)
	# 	if drawN:
	# 		glDisableVertexAttribArray(2)

	# 	glUseProgram(0) # Wyłączenie programu shaderów

	def renderSelf(self):
		if not len(self.m_faces):
			PointCloud.renderSelf(self)
		else:	
			glEnable(GL_COLOR_MATERIAL)
			glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

			if self.gl_renderAs == 0:
				glPolygonMode(GL_FRONT, GL_POINT)
				glPolygonMode(GL_BACK, GL_POINT)
				#glEnable(GL_POINT_SMOOTH)
				#glPointSize(1)
			elif self.gl_renderAs == 1:
				glPolygonMode(GL_FRONT, GL_LINE)
				glPolygonMode(GL_BACK, GL_LINE)
			else:
				glPolygonMode(GL_FRONT, GL_FILL)
				glPolygonMode(GL_BACK, GL_FILL)

			self.renderWithShaders2()

			glDisable(GL_COLOR_MATERIAL)



	def invert_normals(self):
		for i in range(self.m_faces.shape[0]):
			tmp = self.m_faces[i][0]
			self.m_faces[i][0] = self.m_faces[i][2]
			self.m_faces[i][2] = tmp
		self.calcVN()


	def export_as_obj(self, obj_file_name='v:/fast_test.obj'):
		objFile = open(obj_file_name, 'w')
		objFile.write(f"# .obj file created with pyDpVision\n\n")
		for pt in self.m_vertices:
			txt = f"v {pt[0]:.6f} {pt[1]:.6f} {pt[2]:.6f}\n"
			objFile.write(txt)
		objFile.write(f"# {self.m_vertices.shape[0]} vertices, 0 vertices normals\n\n")

		for tr in self.m_faces:
			txt = f"f {tr[0]+1} {tr[1]+1} {tr[2]+1}\n"
			objFile.write(txt)
		objFile.write(f"# {self.m_faces.shape[0]} faces, 0 coords texture\n\n")

		objFile.close()

	@staticmethod
	def create(vertices = [], faces = [], invert_normals = False):
		mesh = Mesh()
		mesh.m_vertices = np.array(vertices, dtype=np.float32)
		mesh.m_faces =  np.array(faces, dtype=np.uint)
		#mesh.m_vcolors = np.zeros((len(vertices), 4), dtype=np.ubyte)
		#mesh.m_vcolors[:] = [255,255,0,255]

		if invert_normals:
			mesh.invert_normals()
		else:
			mesh.calcVN()
		
		return mesh
