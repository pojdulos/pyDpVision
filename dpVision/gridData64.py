# -*- coding: utf-8 -*-
"""
@author: pojdulos
"""

from .object import Object
from .surface import Surface
from PyQt5.QtGui import *
from OpenGL.GL import *
import numpy as np
from .shaders import create_program
from .colormaps import make_colormap


class GridData64(Object):
	"""
	Siatka danych wysokościowych z renderingiem OpenGL.

	Używa kompozycji z Surface (dane + maska/ROI) zamiast wielokrotnego
	dziedziczenia (PyQt5 QObject nie daje się łączyć z Surface przez MRO).
	Wszystkie atrybuty i metody Surface dostępne przez delegację.
	"""

	def __init__(self, grid, stepX=1.0, stepY=1.0, offsetX=None, offsetY=None, parent=None,
				 unit="mm", metadata=None, mask=None):
		Object.__init__(self, parent)

		_grid = np.asarray(grid, dtype=np.float64)
		_offsetX = -stepX * _grid.shape[1] / 2 if offsetX is None else offsetX
		_offsetY = -stepY * _grid.shape[0] / 2 if offsetY is None else offsetY

		self._surface = Surface(
			height=_grid,
			dx=stepX,
			dy=stepY,
			x0=_offsetX,
			y0=_offsetY,
			mask=mask,
			unit=unit,
			metadata=metadata,
		)

		self.use_uniform_color = True
		self.uniform_color = [0.6, 0.6, 0.6]
		self.use_mesh = False
		self.z_filter = 0.0
		self._colormap_name = 'skala'

		self.shader_program = None
		self.tex = None
		self.palette_tex = None

	# ------------------------------------------------------------------
	# Delegacja do Surface  (duck typing — GridData64 działa jak Surface)
	# ------------------------------------------------------------------

	def __getattr__(self, name):
		# Wywoływane tylko gdy normalne wyszukiwanie zawiedzie.
		# Deleguje do _surface, udostępniając całe API Surface (copy, crop,
		# crop_to_mask, xi, yi, length, width, shape, nx, ny, ...).
		try:
			surface = object.__getattribute__(self, '_surface')
			return getattr(surface, name)
		except AttributeError:
			raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

	# Kluczowe atrybuty Surface wystawione jawnie przez property
	# (potrzebne settery, bo __getattr__ nie obsługuje przypisania)

	@property
	def height(self):
		return self._surface.height

	@height.setter
	def height(self, value):
		self._surface.height = np.asarray(value, dtype=np.float64)
		self.invalidate_bb()

	@property
	def dx(self):
		return self._surface.dx

	@dx.setter
	def dx(self, value):
		self._surface.dx = value
		self._surface.__dict__.pop('xi', None)
		self.invalidate_bb()

	@property
	def dy(self):
		return self._surface.dy

	@dy.setter
	def dy(self, value):
		self._surface.dy = value
		self._surface.__dict__.pop('yi', None)
		self.invalidate_bb()

	@property
	def x0(self):
		return self._surface.x0

	@x0.setter
	def x0(self, value):
		self._surface.x0 = value
		self._surface.__dict__.pop('xi', None)
		self.invalidate_bb()

	@property
	def y0(self):
		return self._surface.y0

	@y0.setter
	def y0(self, value):
		self._surface.y0 = value
		self._surface.__dict__.pop('yi', None)
		self.invalidate_bb()

	@property
	def mask(self):
		return self._surface.mask

	@mask.setter
	def mask(self, value):
		self._surface.mask = value

	@property
	def vmin(self):
		return self._surface.vmin

	@vmin.setter
	def vmin(self, value):
		self._surface.vmin = value

	@property
	def vmax(self):
		return self._surface.vmax

	@vmax.setter
	def vmax(self, value):
		self._surface.vmax = value

	@property
	def unit(self):
		return self._surface.unit

	@unit.setter
	def unit(self, value):
		self._surface.unit = value

	@property
	def metadata(self):
		return self._surface.metadata

	@metadata.setter
	def metadata(self, value):
		self._surface.metadata = value

	# ------------------------------------------------------------------
	# Backward-compatible aliases
	# ------------------------------------------------------------------

	@property
	def m_grid64(self):
		return self._surface.height

	@m_grid64.setter
	def m_grid64(self, value):
		self.height = value  # przez height setter → invalidate_bb()

	@property
	def stepX(self):
		return self._surface.dx

	@stepX.setter
	def stepX(self, value):
		self.dx = value

	@property
	def stepY(self):
		return self._surface.dy

	@stepY.setter
	def stepY(self, value):
		self.dy = value

	@property
	def offsetX(self):
		return self._surface.x0

	@offsetX.setter
	def offsetX(self, value):
		self.x0 = value

	@property
	def offsetY(self):
		return self._surface.y0

	@offsetY.setter
	def offsetY(self, value):
		self.y0 = value

	@property
	def h(self):
		return self._surface.ny

	@property
	def w(self):
		return self._surface.nx

	# ------------------------------------------------------------------
	# Classmethod: buduj GridData64 z obiektu Surface
	# ------------------------------------------------------------------

	@classmethod
	def from_surface(cls, surface, parent=None):
		"""Utwórz GridData64 z obiektu Surface (np. wynik ROI/filtra z efs)."""
		height = surface.height.copy()
		height[~surface.mask] = np.nan
		obj = cls(
			height,
			stepX=surface.dx,
			stepY=surface.dy,
			offsetX=surface.x0,
			offsetY=surface.y0,
			parent=parent,
			unit=getattr(surface, 'unit', 'mm'),
			metadata=dict(getattr(surface, 'metadata', {})),
			mask=surface.mask.copy(),
		)
		if surface.vmin is not None:
			obj.vmin = surface.vmin
		if surface.vmax is not None:
			obj.vmax = surface.vmax
		return obj

	# ------------------------------------------------------------------

	def upload_palette_to_gpu(self):
		"""Tworzy/aktualizuje 256×1 teksturę RGB z aktualną paletą kolorów."""
		colors = make_colormap(self._colormap_name)  # (256, 3) float32
		rgba = np.concatenate(
			[colors, np.ones((len(colors), 1), dtype=np.float32)], axis=1
		)  # (256, 4)
		if self.palette_tex is None:
			self.palette_tex = glGenTextures(1)
		glBindTexture(GL_TEXTURE_2D, self.palette_tex)
		glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA32F,
					 len(colors), 1, 0,
					 GL_RGBA, GL_FLOAT, rgba)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
		glBindTexture(GL_TEXTURE_2D, 0)

	def set_colormap(self, name):
		"""Ustawia colormapy dla wizualizacji wysokości.
		name: str ('jet','rainbow','hot','cool','gray','terrain')
		      lub tablica (N,3) float z własnymi kolorami.
		"""
		self._colormap_name = name
		if self.palette_tex is not None:
			self.upload_palette_to_gpu()

	def upload_to_gpu(self):
		"""Tworzy/aktualizuje teksturę RG32F w GPU (Z + maska)."""
		safe_grid = np.nan_to_num(
			self.height,
			nan=0.0, posinf=0.0, neginf=0.0
		).astype(np.float32)
		# używamy self.mask z Surface (może być zmodyfikowana przez ROI)
		mask_f32 = self.mask.astype(np.float32)

		data_rg = np.stack((safe_grid, mask_f32), axis=-1)

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

		self.upload_palette_to_gpu()

	def get_colormap_range(self):
		if self.vmin is None or self.vmax is None:
			z_values = self.height[np.isfinite(self.height)]
			self.vmin = float(np.min(z_values))
			self.vmax = float(np.max(z_values))
		return (self.vmin, self.vmax)
	
	def renderSelf(self):
		if self.shader_program is None:
			self.initializeGL()

		glUseProgram(self.shader_program)

		# --- Uniformy: macierz MVP ---
		# Surface przechowuje dane w µm; tu konwertujemy µm→mm (1e-3).
		# Viewer już zastosował gl.glScalef(mm→viewer_unit) przed wywołaniem render(),
		# więc modelview zawiera tę skalę — dlatego MVP automatycznie daje poprawne wsp.
		modelview = np.array(glGetFloatv(GL_MODELVIEW_MATRIX), dtype=np.float32).T
		projection = np.array(glGetFloatv(GL_PROJECTION_MATRIX), dtype=np.float32).T
		scale = np.diag([1e-3, 1e-3, 1e-3, 1.0]).astype(np.float32)  # µm → mm
		mvp = projection @ modelview @ scale

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

		# --- Paleta kolorów (unit 1) ---
		glActiveTexture(GL_TEXTURE1)
		glBindTexture(GL_TEXTURE_2D, self.palette_tex)
		glUniform1i(glGetUniformLocation(self.shader_program, "u_palette"), 1)
		glActiveTexture(GL_TEXTURE0)

		# tryb koloru
		
		glUniform1i(glGetUniformLocation(self.shader_program, "u_useUniformColor"), int(self.use_uniform_color))
		if self.use_uniform_color:
			glUniform3fv(glGetUniformLocation(self.shader_program, "u_uniformColor"), 1, self.uniform_color)

		# min/max Z dla colormapy
		minZ, maxZ = self.get_colormap_range()
		glUniform1f(glGetUniformLocation(self.shader_program, "u_minZ"), minZ)
		glUniform1f(glGetUniformLocation(self.shader_program, "u_maxZ"), maxZ)

		# --- Rysowanie ---
		if self.use_mesh:
			glDrawArrays(GL_POINTS, 0, (self.h - 1) * (self.w - 1))
		else:
			glDrawArrays(GL_POINTS, 0, self.h * self.w)

		# --- Clean up ---
		glActiveTexture(GL_TEXTURE1)
		glBindTexture(GL_TEXTURE_2D, 0)
		glActiveTexture(GL_TEXTURE0)
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
		self.height = np.asarray(new_grid, dtype=np.float64)
		self.mask = np.isfinite(self.height)
		if stepX is not None:
			self.dx = stepX
			self.__dict__.pop('xi', None)
		if stepY is not None:
			self.dy = stepY
			self.__dict__.pop('yi', None)
		self.vmin = None
		self.vmax = None
		self.upload_to_gpu()
		self.invalidate_bb()  # propaguj do rodziców

	def getBB(self):
		_b, _min1, _max1 = Object.getBB(self)  # BB dzieci w hierarchii sceny
		if self.height.size == 0:
			return _b, _min1, _max1

		# Surface przechowuje w µm; BB zawsze w mm (canonical world unit).
		s = 1e-3
		_min = [
			self.x0 * s,
			self.y0 * s,
			np.nanmin(self.height) * s
		]
		_max = [
			(self.x0 + self.dx * self.nx) * s,
			(self.y0 + self.dy * self.ny) * s,
			np.nanmax(self.height) * s
		]
		if _b:
			_min = [min(a, b) for a, b in zip(_min1, _min)]
			_max = [max(a, b) for a, b in zip(_max1, _max)]
		return True, _min, _max

	def to_mesh(self):
		from .conversion import grid_to_mesh
		return grid_to_mesh(self)

	def info(self):
		return f"GridData64: shape={self.height.shape}, stepX={self.stepX}, stepY={self.stepY}, offsetX={self.offsetX}, offsetY={self.offsetY}"