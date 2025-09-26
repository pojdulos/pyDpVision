# -*- coding: utf-8 -*-
"""
@author: pojdulos
"""

from .object import Object
from PyQt5.QtGui import *
from OpenGL.GL import *
import numpy as np
from .shaders import create_program


class GridData64(Object):
	def __init__(self, grid, stepX=1.0, stepY=1.0, parent=None):
		super(GridData64, self).__init__(parent)
		# oryginalny grid w float64 do obliczeń
		self.m_grid64 = grid.astype(np.float64)
		self.stepX = stepX
		self.stepY = stepY
		self.offsetY = -stepY*self.m_grid64.shape[0]/2
		self.offsetX = -stepX*self.m_grid64.shape[1]/2
		self.use_uniform_color = True
		self.uniform_color = [0.6,0.6,0.6]
		self.use_mesh = False
		
		# GPU tekstura tworzona później
		self.shader_program = None
		self.tex = None

	@property
	def h(self):
		return self.m_grid64.shape[0]

	@property
	def w(self):
		return self.m_grid64.shape[1]

	def upload_to_gpu(self):
		"""Tworzy/aktualizuje teksturę RG32F w GPU (Z + maska)."""
		safe_grid = np.nan_to_num(
			self.m_grid64,
			nan=0.0, posinf=0.0, neginf=0.0
		).astype(np.float32)
		mask = np.isfinite(self.m_grid64).astype(np.float32)

		data_rg = np.stack((safe_grid, mask), axis=-1)

		if self.tex is None:
			self.tex = glGenTextures(1)
		glBindTexture(GL_TEXTURE_2D, self.tex)
		glTexImage2D(GL_TEXTURE_2D, 0, GL_RG32F,
					 self.w, self.h, 0,
					 GL_RG, GL_FLOAT, data_rg)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
		glBindTexture(GL_TEXTURE_2D, 0)

	def initializeGL(self):
		# upload pierwszej wersji danych
		self.upload_to_gpu()

		# --- shadery ---
		if self.use_mesh:
			self.shader_program = create_program(
				vertex_shader_name='gridDataAsMesh.vert',
				fragment_shader_name='gridDataAsMesh.frag',
				geometry_shader_name='gridDataAsMesh.geom' )
		else:
			self.shader_program = create_program(
				vertex_shader_name='gridDataAsCloud.vert',
				fragment_shader_name='gridDataAsCloud.frag' )
			 
	def renderSelf(self):
		if self.shader_program is None:
			self.initializeGL()

		glUseProgram(self.shader_program)

		# --- Uniformy: macierz MVP ---
		modelview = np.array(glGetFloatv(GL_MODELVIEW_MATRIX), dtype=np.float32).T
		projection = np.array(glGetFloatv(GL_PROJECTION_MATRIX), dtype=np.float32).T
		mvp = projection @ modelview

		mvp_loc = glGetUniformLocation(self.shader_program, "u_mvp")
		glUniformMatrix4fv(mvp_loc, 1, GL_FALSE, mvp.T)

		# --- Uniformy: kroki siatki + rozmiar grida ---
		glUniform1f(glGetUniformLocation(self.shader_program, "u_stepX"), self.stepX)
		glUniform1f(glGetUniformLocation(self.shader_program, "u_stepY"), self.stepY)
		glUniform1f(glGetUniformLocation(self.shader_program, "u_offsetX"), self.offsetX)
		glUniform1f(glGetUniformLocation(self.shader_program, "u_offsetY"), self.offsetY)
		glUniform1i(glGetUniformLocation(self.shader_program, "u_width"), self.w)
		glUniform1i(glGetUniformLocation(self.shader_program, "u_height"), self.h)

		# --- Tekstura RG (wysokość + maska) ---
		glActiveTexture(GL_TEXTURE0)
		glBindTexture(GL_TEXTURE_2D, self.tex)
		glUniform1i(glGetUniformLocation(self.shader_program, "u_gridTex"), 0)

		# tryb koloru
		
		glUniform1i(glGetUniformLocation(self.shader_program, "u_useUniformColor"), int(self.use_uniform_color))
		if self.use_uniform_color:
			glUniform3fv(glGetUniformLocation(self.shader_program, "u_uniformColor"), 1, self.uniform_color)

		# min/max Z dla colormapy
		z_values = self.m_grid64[np.isfinite(self.m_grid64)]
		minZ, maxZ = float(np.min(z_values)), float(np.max(z_values))
		glUniform1f(glGetUniformLocation(self.shader_program, "u_minZ"), minZ)
		glUniform1f(glGetUniformLocation(self.shader_program, "u_maxZ"), maxZ)

		# --- Rysowanie ---
		if self.use_mesh:
			glDrawArrays(GL_POINTS, 0, (self.h - 1) * (self.w - 1))
		else:
			glDrawArrays(GL_POINTS, 0, self.h * self.w)

		# --- Clean up ---
		glBindTexture(GL_TEXTURE_2D, 0)
		glUseProgram(0)

	def set_display_mode(self, use_mesh: bool):
		if self.use_mesh != use_mesh:
			self.use_mesh = use_mesh
			# wymuszenie rekonstrukcji shaderów
			if self.shader_program is not None:
				glDeleteProgram(self.shader_program)
			self.shader_program = None

	def update_grid(self, new_grid: np.ndarray, stepX=None, stepY=None):
		self.m_grid64 = new_grid.astype(np.float64)
		#self.h, self.w = self.m_grid64.shape
		if stepX is not None: self.stepX = stepX
		if stepY is not None: self.stepY = stepY
		self.upload_to_gpu()

	def getBB(self):
		_b, _min1, _max1 = Object.getBB(self)  # Pobieranie BB z klasy nadrzędnej
		if self.m_grid64.size == 0:
			return _b, _min1, _max1
		
		_min = [
			self.offsetX,
		  	self.offsetY,
			np.nanmin(self.m_grid64)
		]
		
		_max = [
			self.offsetX+self.stepX*self.m_grid64.shape[1],
			self.offsetY+self.stepY*self.m_grid64.shape[0],
			np.nanmax(self.m_grid64)
		]
		
		if _b:
			_min = [min(a, b) for a, b in zip(_min1, _min)]
			_max = [max(a, b) for a, b in zip(_max1, _max)]
		return True, _min, _max
