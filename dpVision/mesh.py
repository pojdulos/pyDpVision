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
			self.dTexImage = None
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
		self.vao = None
		self.shader_program = None
		self.uniform_locs = {}  # Cache dla uniform locations
		self.wboit_shader = None
		self.wboit_uniform_locs = {}
		self.vBuf = None
		self.iBuf = None
		self.cBuf = None
		self.nBuf = None
		self.tBuf = None
		self._gpu_uploaded = False
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

		# Ensure shapes are valid for cross product
		if vAB.shape[-1] not in (2, 3) or vAC.shape[-1] not in (2, 3):
			raise ValueError("vAB and vAC must be 2D or 3D vectors")

		normals = np.cross(vAB, vAC)


		if not weighted:
			normals_lengths = np.linalg.norm(normals, axis=1)
			normals_lengths[normals_lengths == 0] = 1  # Zapobieganie dzieleniu przez zero
			normals = normals / normals_lengths[:, np.newaxis]

		# Sumowanie normalnych dla wierzchołków — bincount zamiast np.add.at
		nv = len(self.m_vertices)
		faces_flat = self.m_faces.ravel()          # (3*nf,)
		normals_rep = np.repeat(normals, 3, axis=0)  # (3*nf, 3)
		tmpN = np.empty((nv, 3), dtype=np.float64)
		for d in range(3):
			tmpN[:, d] = np.bincount(faces_flat, weights=normals_rep[:, d], minlength=nv)

		# Normalizacja normalnych
		norms = np.linalg.norm(tmpN, axis=1)
		norms[norms == 0] = 1  # Zapobieganie dzieleniu przez zero
		self.m_vnormals = (tmpN / norms[:, np.newaxis]).astype(np.float32)


	def renderWithShaders2(self):
		if getattr(self, '_shader_failed', False):
			return
			
		# Usuń flagę blokady - problem był w tym że nie pozwalała na normalne renderowanie
		# Zamiast tego OpenGL kolejkuje komendy więc nie ma problemu z "współbieżnością"
		
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
			
			# Cache uniform locations (wywoływane tylko raz, nie w każdej klatce!)
			self.uniform_locs = {
				'useVColors': glGetUniformLocation(program, "useVColors"),
				'myColor': glGetUniformLocation(program, "myColor"),
				'useVNormals': glGetUniformLocation(program, "useVNormals"),
				'useTexture': glGetUniformLocation(program, "useTexture"),
				'texture1': glGetUniformLocation(program, "texture1"),
				'useFlatShading': glGetUniformLocation(program, "useFlatShading"),
				'model': glGetUniformLocation(program, "model"),
				'view': glGetUniformLocation(program, "view"),
				'projection': glGetUniformLocation(program, "projection")
			}
			
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
			# Sprawdzamy czy trzeba duplikować wierzchołki (gdy atrybuty mają różne indeksy)
			needDuplication = drawFC or drawFN or (drawT and not np.array_equal(self.m_tindices, self.m_faces))
			
			if needDuplication:
				# Duplikujemy wierzchołki - każdy trójkąt ma osobne kopie wierzchołków
				f = self.m_faces
				self.vBuf = self.m_vertices[f].reshape(-1, 3).astype(np.float32)  # (nf*3, 3)
				self.iBuf = np.arange(len(self.vBuf), dtype=np.uint32)  # (nf*3,) sekwencyjne indeksy
				
				if drawVC:
					self.cBuf = self.m_vcolors[f].reshape(-1, 4).astype(np.ubyte)
				elif drawFC:
					self.cBuf = np.repeat(self.m_fcolors, 3, axis=0).astype(np.ubyte)
					
				if drawVN:
					self.nBuf = self.m_vnormals[f].reshape(-1, 3).astype(np.float32)
				elif drawFN:
					self.nBuf = np.repeat(self.m_fnormals, 3, axis=0).astype(np.float32)
			else:
				# Używamy indeksowania - wysyłamy tylko unikalne wierzchołki
				self.vBuf = self.m_vertices.astype(np.float32)  # (nv, 3)
				self.iBuf = self.m_faces.astype(np.uint32).ravel()  # (nf*3,) flat array indeksów
				
				if drawVC:
					self.cBuf = self.m_vcolors.astype(np.ubyte)
				if drawVN:
					self.nBuf = self.m_vnormals.astype(np.float32)

		if drawT:
			if self.tBuf is None:
				# Tekstury - używamy m_tindices (które mogą być różne od m_faces w OBJ)
				self.tBuf = self.m_tcoords[self.m_tindices].reshape(-1, 2).astype(np.float32)

		# Wgraj dane do GPU tylko raz (nie przy każdej klatce)
		if not self._gpu_uploaded:
			# Tworzenie VAO - przechowuje cały stan vertex attributes
			if self.vao is None:
				self.vao = glGenVertexArrays(1)
			glBindVertexArray(self.vao)
			
			if self.v_vbo is None:
				self.v_vbo = glGenBuffers(1)
			glBindBuffer(GL_ARRAY_BUFFER, self.v_vbo)
			glBufferData(GL_ARRAY_BUFFER, self.vBuf.nbytes, self.vBuf, GL_STATIC_DRAW)
			glVertexAttribPointer(0, 3, GL_FLOAT, False, 0, None)
			glEnableVertexAttribArray(0)
			
			# Element Buffer Object dla indeksów
			if self.ebo is None:
				self.ebo = glGenBuffers(1)
			glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
			glBufferData(GL_ELEMENT_ARRAY_BUFFER, self.iBuf.nbytes, self.iBuf, GL_STATIC_DRAW)

			if drawC:
				if self.c_vbo is None:
					self.c_vbo = glGenBuffers(1)
				glBindBuffer(GL_ARRAY_BUFFER, self.c_vbo)
				glBufferData(GL_ARRAY_BUFFER, self.cBuf.nbytes, self.cBuf, GL_STATIC_DRAW)
				glVertexAttribPointer(1, 4, GL_UNSIGNED_BYTE, True, 0, None)
				glEnableVertexAttribArray(1)

			if drawN:
				if self.n_vbo is None:
					self.n_vbo = glGenBuffers(1)
				glBindBuffer(GL_ARRAY_BUFFER, self.n_vbo)
				glBufferData(GL_ARRAY_BUFFER, self.nBuf.nbytes, self.nBuf, GL_STATIC_DRAW)
				glVertexAttribPointer(2, 3, GL_FLOAT, True, 0, None)
				glEnableVertexAttribArray(2)

			glBindVertexArray(0)  # Unbind VAO
			self._gpu_uploaded = True
		
		# Tekstury mogą być ładowane dynamicznie, więc upload osobno
		if drawT and self.t_vbo is None:
			glBindVertexArray(self.vao)
			self.t_vbo = glGenBuffers(1)
			glBindBuffer(GL_ARRAY_BUFFER, self.t_vbo)
			glBufferData(GL_ARRAY_BUFFER, self.tBuf.nbytes, self.tBuf, GL_STATIC_DRAW)
			glVertexAttribPointer(3, 2, GL_FLOAT, False, 0, None)
			glEnableVertexAttribArray(3)
			glBindVertexArray(0)
		
		# Używamy cache'owanych uniform locations zamiast glGetUniformLocation w każdej klatce
		dC = self.materials[self.currentMaterial].diffuse + [self.materials[self.currentMaterial].alpha]
		glUniform4f(self.uniform_locs['myColor'], dC[0], dC[1], dC[2], dC[3])
		glUniform1i(self.uniform_locs['useVColors'], 1 if drawC else 0)
		glUniform1i(self.uniform_locs['useVNormals'], 1 if drawN else 0)
		
		if drawT:
			glActiveTexture(GL_TEXTURE0)
			glBindTexture(GL_TEXTURE_2D, self.materials[self.currentMaterial].dTexture.textureId())
			glUniform1i(self.uniform_locs['texture1'], 0)
			glUniform1i(self.uniform_locs['useTexture'], 1)
		else:
			glUniform1i(self.uniform_locs['useTexture'], 0)

		glUniform1i(self.uniform_locs['useFlatShading'], 0 if self.b_renderSmooth else 1)

		# Bindujemy VAO - automatycznie ustawia wszystkie vertex attributes
		glBindVertexArray(self.vao)
		
		# Pobierz macierze z OpenGL (konieczne dla poprawnego wyświetlania)
		model = np.empty((4,4), dtype=np.float32)
		projection = np.empty((4,4), dtype=np.float32)
		view = np.identity(4, dtype=np.float32)
		
		glGetFloatv(GL_MODELVIEW_MATRIX, model)
		glGetFloatv(GL_PROJECTION_MATRIX, projection)
		
		# Używamy cache'owanych uniform locations
		glUniformMatrix4fv(self.uniform_locs['model'], 1, GL_FALSE, model)
		glUniformMatrix4fv(self.uniform_locs['view'], 1, GL_FALSE, view)
		glUniformMatrix4fv(self.uniform_locs['projection'], 1, GL_FALSE, projection)

		# Używamy glDrawElements zamiast glDrawArrays - renderuje tylko unikalne wierzchołki
		glDrawElements(GL_TRIANGLES, len(self.iBuf), GL_UNSIGNED_INT, None)

		# Unbind VAO
		glBindVertexArray(0)

		glUseProgram(0) # Wyłączenie programu shaderów
		
		# Podstawowe statystyki (pierwszy frame)
		if not hasattr(self, '_frame_count'):
			self._frame_count = 0
			print(f"\n=== MESH RENDERING STARTED ===")
			print(f"Triangles: {len(self.iBuf)//3:,}, Unique Vertices: {len(self.vBuf):,}")
			print(f"Memory: Vertices={self.vBuf.nbytes/1024/1024:.1f}MB, Indices={self.iBuf.nbytes/1024/1024:.1f}MB")
		
		self._frame_count += 1


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

	@property
	def is_transparent(self):
		alpha = self.materials[self.currentMaterial].alpha
		result = alpha < 0.999
		# Debug: print tylko gdy się zmienia
		if not hasattr(self, '_last_is_transparent') or self._last_is_transparent != result:
			print(f"[MESH] '{self.label}' is_transparent changed: {getattr(self, '_last_is_transparent', None)} -> {result} (alpha={alpha:.3f})")
			self._last_is_transparent = result
		return result

	def _compile_wboit_shader(self):
		"""Kompiluje shader WBOIT dla tego mesha."""
		print(f"[WBOIT] Kompilowanie WBOIT shader...")
		try:
			vs = load_and_compile_shader('mesh.vert', GL_VERTEX_SHADER)
			fs = load_and_compile_shader('wboit_mesh.frag', GL_FRAGMENT_SHADER)
			prog = glCreateProgram()
			glAttachShader(prog, vs)
			glAttachShader(prog, fs)
			glLinkProgram(prog)
			if not glGetProgramiv(prog, GL_LINK_STATUS):
				print(glGetProgramInfoLog(prog))
				glDeleteProgram(prog)
				return
			glDeleteShader(vs)
			glDeleteShader(fs)
			
			# USUŃ stary shader jeśli istnieje
			if self.wboit_shader is not None:
				glDeleteProgram(self.wboit_shader)
				
			self.wboit_shader = prog
			self.wboit_uniform_locs = {
				'model':          glGetUniformLocation(prog, 'model'),
				'view':           glGetUniformLocation(prog, 'view'),
				'projection':     glGetUniformLocation(prog, 'projection'),
				'myColor':        glGetUniformLocation(prog, 'myColor'),
				'useVColors':     glGetUniformLocation(prog, 'useVColors'),
				'useVNormals':    glGetUniformLocation(prog, 'useVNormals'),
				'useTexture':     glGetUniformLocation(prog, 'useTexture'),
				'useFlatShading': glGetUniformLocation(prog, 'useFlatShading'),
				'texture1':       glGetUniformLocation(prog, 'texture1'),
				'u_wboit_pass':   glGetUniformLocation(prog, 'u_wboit_pass'),
				'u_cameraPos':    glGetUniformLocation(prog, 'u_cameraPos'),
			}
			print(f"[WBOIT] Shader skompilowany: program={prog}")
		except Exception as e:
			print(f"WBOIT mesh shader error: {e}")
			self._shader_failed = True

	def render_wboit(self, pass_idx, cull_mode=None, camera_pos=None):
		"""WBOIT rendering – tylko dla przezroczystych mesha (is_transparent=True).
		Wywoływane gdy AP.wboit_pass >= 0.
		"""
		# Renderujemy wyłącznie przezroczyste meshe – nieprzezroczyste są obsługiwane
		# w normalnym opaque pass z poprawnym depth testem.
		if not self.is_transparent:
			return
		
		if not len(self.m_faces):
			return
		
		if getattr(self, '_shader_failed', False):
			return
		if self.wboit_shader is None:
			self._compile_wboit_shader()
		if self.wboit_shader is None:
			return
		# Ensure geometry is uploaded to GPU (may not have happened if mesh is always transparent)
		if not self._gpu_uploaded:
			glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE)
			glDepthMask(GL_FALSE)
			self.renderWithShaders2()
			glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)
			# Przywróć WBOIT state - renderWithShaders2() może zmieniać GL state
			glDepthMask(GL_FALSE)
		if self.vao is None:
			return

		# Workspace ustawia stan OpenGL - mesh tylko używa
		glUseProgram(self.wboit_shader)
		glUniform1i(self.wboit_uniform_locs['u_wboit_pass'], pass_idx)

		mat = self.materials[self.currentMaterial]
		dC  = mat.diffuse + [mat.alpha]
		glUniform4f(self.wboit_uniform_locs['myColor'], *dC)

		drawC = self.cBuf is not None
		drawN = self.nBuf is not None
		drawT = (self.b_renderTexture and mat.hasTexture()
		         and self.m_tindices.shape[0] == self.m_faces.shape[0])

		glUniform1i(self.wboit_uniform_locs['useVColors'],    1 if drawC else 0)
		glUniform1i(self.wboit_uniform_locs['useVNormals'],   1 if drawN else 0)
		glUniform1i(self.wboit_uniform_locs['useFlatShading'], 0 if self.b_renderSmooth else 1)

		if drawT:
			glActiveTexture(GL_TEXTURE0)
			glBindTexture(GL_TEXTURE_2D, mat.dTexture.textureId())
			glUniform1i(self.wboit_uniform_locs['texture1'],  0)
			glUniform1i(self.wboit_uniform_locs['useTexture'], 1)
		else:
			glUniform1i(self.wboit_uniform_locs['useTexture'], 0)

		model      = np.empty((4, 4), dtype=np.float32)
		projection = np.empty((4, 4), dtype=np.float32)
		view       = np.identity(4,   dtype=np.float32)
		glGetFloatv(GL_MODELVIEW_MATRIX,  model)
		glGetFloatv(GL_PROJECTION_MATRIX, projection)
		glUniformMatrix4fv(self.wboit_uniform_locs['model'],      1, GL_FALSE, model)
		glUniformMatrix4fv(self.wboit_uniform_locs['view'],       1, GL_FALSE, view)
		glUniformMatrix4fv(self.wboit_uniform_locs['projection'], 1, GL_FALSE, projection)
		
		# Przekaż pozycję kamery do weight function
		if camera_pos is not None:
			glUniform3f(self.wboit_uniform_locs['u_cameraPos'], *camera_pos)
		else:
			# Fallback - użyj (0, 0, 200) jako domyślna pozycja kamery
			glUniform3f(self.wboit_uniform_locs['u_cameraPos'], 0.0, 0.0, 200.0)

		glBindVertexArray(self.vao)
		
		# Workspace ustawia culling - mesh tylko rysuje
		# (Nie robimy tutaj włączania/wyłączania culling ani dwóch draw calls)
		glDrawElements(GL_TRIANGLES, len(self.iBuf), GL_UNSIGNED_INT, None)
		
		glBindVertexArray(0)
		glUseProgram(0)

	def renderSelf(self):
		from .globals import AP
		
		if AP.wboit_pass is not None:
			if AP.wboit_pass >= 0:
				# WBOIT passes (0=accum, 1=reveal): tylko przezroczyste meshe przez WBOIT shader.
				# Nieprzezroczyste są już wyrenderowane w opaque pass – pomijamy je tutaj.
				if self.is_transparent:
					self.render_wboit(AP.wboit_pass)
				return
			else:
				# AP.wboit_pass == -1: opaque-only pass.
				# Pomijamy przezroczyste – zostaną wyrenderowane przez WBOIT.
				if self.is_transparent:
					return
				# Nieprzezroczyste: przepadaj do normalnego renderowania poniżej.
		
		# Normalne renderowanie
		if not len(self.m_faces):
			PointCloud.renderSelf(self)
		else:
			glEnable(GL_COLOR_MATERIAL)
			glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

			if self.gl_renderAs == 0:
				glPolygonMode(GL_FRONT, GL_POINT)
				glPolygonMode(GL_BACK, GL_POINT)
			elif self.gl_renderAs == 1:
				glPolygonMode(GL_FRONT, GL_LINE)
				glPolygonMode(GL_BACK, GL_LINE)
			else:
				glPolygonMode(GL_FRONT, GL_FILL)
				glPolygonMode(GL_BACK, GL_FILL)

			if self.is_transparent:
				# Dwuprzebiegowy render dla przezroczystych zamkniętych siatek:
				# 1. tylne ścianki (back faces) – rysowane pierwsze (dalej od kamery)
				# 2. przednie ścianki (front faces) – rysowane drugie (bliżej kamery)
				# Gwarantuje poprawny back-to-front bez sortowania trójkątów.
				glEnable(GL_CULL_FACE)
				glCullFace(GL_FRONT)
				self.renderWithShaders2()
				glCullFace(GL_BACK)
				self.renderWithShaders2()
				glDisable(GL_CULL_FACE)
			else:
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

	def to_grid25D(self, **kwargs):
		from .conversion import mesh_to_grid25D
		return mesh_to_grid25D(self, **kwargs)

	def info(self):
		return f"Mesh: {len(self.m_vertices)} vertices, {len(self.m_faces)} faces"
	
