# -*- coding: utf-8 -*-
"""
Created on Mon Nov 27 10:05:30 2023

@author: pojdulos
"""

from .object import Object
from PyQt5.QtGui import *
from OpenGL.GL import *
import numpy as np
from enum import IntEnum

from .shaders import create_program


def Vertex(pt=None, x=0.0, y=0.0, z=0.0):
	if pt and isinstance(pt, list) and len(pt) == 3:
		return np.array(pt, dtype=np.float32)
	return np.array([x, y, z], dtype=np.float32)


class RenderMode(IntEnum):
	POINTS = 0
	SPLAT = 1


class PointCloud(Object):
	def __init__(self, parent=None):
		super(PointCloud, self).__init__(parent)
		self.m_vertices = np.empty((0, 3), dtype=np.float32)
		self.m_vcolors = np.empty((0, 4), dtype=np.ubyte)
		self.m_vnormals = np.empty((0, 3), dtype=np.float32)
		self.v_vbo = None
		self.c_vbo = None
		self.n_vbo = None
		self.shader_program = None
		self.splat_shader = None
		self.wboit_splat_shader = None
		self.render_mode = RenderMode.POINTS
		self.point_size = 1.0
		self.splat_scale = 1.0
		self.uniform_color = [0.6, 0.6, 0.6, 1.0]
		self._estimated_spacing = None
		self._cached_local_bb = None

	def addVertex(self, x, y, z):
		self.m_vertices = np.vstack([self.m_vertices, Vertex(x, y, z)])
		self.invalidate_bb()

	def invert_normals(self):
		if self.m_vnormals.shape[0] == self.m_vertices.shape[0]:
			self.m_vnormals = -self.m_vnormals
			return True
		return False

	def getCenterOfWeight(self):
		ctr = [0.0, 0.0, 0.0]
		num_vertices = len(self.m_vertices)
		if num_vertices:
			sums = [sum(dim) for dim in zip(*self.m_vertices)]
			ctr = [total / num_vertices for total in sums]
		return ctr

	def invalidate_bb(self):
		self._cached_local_bb = None
		self._estimated_spacing = None
		super().invalidate_bb()

	def getLocalBB(self):
		if self._cached_local_bb is not None:
			return self._cached_local_bb

		if len(self.m_vertices) == 0:
			self._cached_local_bb = (False, None, None)
			return self._cached_local_bb

		if len(self.m_vertices) > 10000:
			verts_array = np.array(self.m_vertices) if not isinstance(self.m_vertices, np.ndarray) else self.m_vertices
			_min = verts_array.min(axis=0).tolist()
			_max = verts_array.max(axis=0).tolist()
		else:
			_min = [min(dim) for dim in zip(*self.m_vertices)]
			_max = [max(dim) for dim in zip(*self.m_vertices)]

		self._cached_local_bb = (True, _min, _max)
		return self._cached_local_bb

	def _estimate_point_spacing(self):
		if self._estimated_spacing is not None:
			return self._estimated_spacing

		n = len(self.m_vertices)
		if n <= 1:
			self._estimated_spacing = 1.0
			return self._estimated_spacing

		bb = self.getBB()
		if bb is None or not bb[0]:
			self._estimated_spacing = 1.0
			return self._estimated_spacing

		_min = np.asarray(bb[1], dtype=np.float64)
		_max = np.asarray(bb[2], dtype=np.float64)
		extents = np.maximum(_max - _min, 0.0)
		nonzero = extents[extents > 1e-9]

		if len(nonzero) >= 3:
			spacing = float((np.prod(nonzero[:3]) / n) ** (1.0 / 3.0))
		elif len(nonzero) == 2:
			spacing = float((nonzero[0] * nonzero[1] / n) ** 0.5)
		elif len(nonzero) == 1:
			spacing = float(nonzero[0] / max(n - 1, 1))
		else:
			spacing = 1.0

		self._estimated_spacing = max(spacing, 1e-3)
		return self._estimated_spacing

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
		self.vertex_vbo = glGenBuffers(1)
		self.color_vbo = glGenBuffers(1)

		self.shader_program = create_program(
			vertex_shader_name='pointCloud.vert',
			fragment_shader_name='pointCloud.frag'
		)
		self._compile_splat_shader()

		glBindBuffer(GL_ARRAY_BUFFER, self.vertex_vbo)
		glBufferData(GL_ARRAY_BUFFER, self.m_vertices.nbytes, self.m_vertices, GL_DYNAMIC_DRAW)

		colors = np.array(self.m_vcolors, dtype=np.uint8)
		glBindBuffer(GL_ARRAY_BUFFER, self.color_vbo)
		glBufferData(GL_ARRAY_BUFFER, colors.nbytes, colors, GL_STATIC_DRAW)

		glBindBuffer(GL_ARRAY_BUFFER, 0)

	def _compile_splat_shader(self):
		try:
			self.splat_shader = create_program(
				vertex_shader_name='pointCloudSplat.vert',
				fragment_shader_name='pointCloudSplat.frag'
			)
			print('[PointCloud] splat_shader OK', flush=True)
		except Exception as e:
			print(f'[PointCloud] BLAD kompilacji splat_shader: {e}', flush=True)
			self.splat_shader = None

	def _compile_wboit_splat_shader(self):
		try:
			self.wboit_splat_shader = create_program(
				vertex_shader_name='pointCloudSplat.vert',
				fragment_shader_name='wboit_pointCloudSplat.frag'
			)
			print('[PointCloud] wboit_splat_shader OK', flush=True)
		except Exception as e:
			print(f'[PointCloud] BLAD kompilacji wboit_splat_shader: {e}', flush=True)
			self.wboit_splat_shader = None

	def _render_as_points(self):
		use_uniform_color = len(self.m_vcolors) < len(self.m_vertices)

		glUseProgram(self.shader_program)
		glEnable(GL_POINT_SMOOTH)
		glEnable(GL_PROGRAM_POINT_SIZE)
		glPointSize(float(self.point_size))

		glBindBuffer(GL_ARRAY_BUFFER, self.vertex_vbo)
		glEnableVertexAttribArray(0)
		glVertexAttribPointer(0, 3, GL_FLOAT, False, 0, None)

		if not use_uniform_color:
			glBindBuffer(GL_ARRAY_BUFFER, self.color_vbo)
			glEnableVertexAttribArray(1)
			glVertexAttribPointer(1, 4, GL_UNSIGNED_BYTE, True, 0, None)
		else:
			glDisableVertexAttribArray(1)

		modelview = np.array(glGetFloatv(GL_MODELVIEW_MATRIX), dtype=np.float32)
		projection = np.array(glGetFloatv(GL_PROJECTION_MATRIX), dtype=np.float32)

		glUniformMatrix4fv(glGetUniformLocation(self.shader_program, "u_mvp"), 1, GL_FALSE, modelview @ projection)
		glUniform1i(glGetUniformLocation(self.shader_program, "u_use_u_color"), int(use_uniform_color))
		glUniform4f(glGetUniformLocation(self.shader_program, "u_color"), *self.uniform_color)

		glDrawArrays(GL_POINTS, 0, len(self.m_vertices))

		glBindBuffer(GL_ARRAY_BUFFER, 0)
		glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
		glDisableVertexAttribArray(0)
		glDisableVertexAttribArray(1)
		glUseProgram(0)

	def _render_as_splats(self):
		import ctypes

		if self.splat_shader is None:
			self._compile_splat_shader()
		if self.splat_shader is None:
			return

		use_uniform_color = len(self.m_vcolors) < len(self.m_vertices)

		glEnable(GL_PROGRAM_POINT_SIZE)
		glEnable(GL_BLEND)
		glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
		glDepthMask(GL_FALSE)

		glUseProgram(self.splat_shader)

		modelview = np.array(glGetFloatv(GL_MODELVIEW_MATRIX), dtype=np.float32).T
		projection = np.array(glGetFloatv(GL_PROJECTION_MATRIX), dtype=np.float32).T
		mvp = projection @ modelview

		glUniformMatrix4fv(glGetUniformLocation(self.splat_shader, "u_mvp"), 1, GL_FALSE, mvp.T)
		glUniformMatrix4fv(glGetUniformLocation(self.splat_shader, "u_mv"), 1, GL_FALSE, modelview.T)
		glUniformMatrix4fv(glGetUniformLocation(self.splat_shader, "u_projection"), 1, GL_FALSE, projection.T)

		viewport = glGetIntegerv(GL_VIEWPORT)
		glUniform1f(glGetUniformLocation(self.splat_shader, "u_viewport_h"), float(viewport[3]))
		glUniform1f(glGetUniformLocation(self.splat_shader, "u_focal_y"), float(projection[1, 1]))
		glUniform1f(glGetUniformLocation(self.splat_shader, "u_splat_scale"), float(self.splat_scale))
		glUniform1f(glGetUniformLocation(self.splat_shader, "u_point_spacing"), float(self._estimate_point_spacing()))
		glUniform1i(glGetUniformLocation(self.splat_shader, "u_use_u_color"), int(use_uniform_color))
		glUniform4f(glGetUniformLocation(self.splat_shader, "u_color"), *self.uniform_color)

		glBindBuffer(GL_ARRAY_BUFFER, self.vertex_vbo)
		glEnableVertexAttribArray(0)
		glVertexAttribPointer(0, 3, GL_FLOAT, False, 0, None)

		if not use_uniform_color:
			glBindBuffer(GL_ARRAY_BUFFER, self.color_vbo)
			glEnableVertexAttribArray(1)
			glVertexAttribPointer(1, 4, GL_UNSIGNED_BYTE, True, 0, None)
		else:
			glDisableVertexAttribArray(1)

		try:
			glEnable(GL_POINT_SPRITE)
		except Exception:
			pass

		glDrawArrays(GL_POINTS, 0, len(self.m_vertices))

		try:
			glDisable(GL_POINT_SPRITE)
		except Exception:
			pass

		glBindBuffer(GL_ARRAY_BUFFER, 0)
		glDisableVertexAttribArray(0)
		glDisableVertexAttribArray(1)
		glUseProgram(0)
		glDepthMask(GL_TRUE)
		glDisable(GL_BLEND)

	def render_wboit(self, pass_idx):
		import ctypes

		if self.render_mode != RenderMode.SPLAT:
			return
		if self.wboit_splat_shader is None:
			self._compile_wboit_splat_shader()
		if self.wboit_splat_shader is None:
			return

		use_uniform_color = len(self.m_vcolors) < len(self.m_vertices)

		glEnable(GL_PROGRAM_POINT_SIZE)
		glUseProgram(self.wboit_splat_shader)

		modelview = np.array(glGetFloatv(GL_MODELVIEW_MATRIX), dtype=np.float32).T
		projection = np.array(glGetFloatv(GL_PROJECTION_MATRIX), dtype=np.float32).T
		mvp = projection @ modelview

		glUniformMatrix4fv(glGetUniformLocation(self.wboit_splat_shader, "u_mvp"), 1, GL_FALSE, mvp.T)
		glUniformMatrix4fv(glGetUniformLocation(self.wboit_splat_shader, "u_mv"), 1, GL_FALSE, modelview.T)
		glUniformMatrix4fv(glGetUniformLocation(self.wboit_splat_shader, "u_projection"), 1, GL_FALSE, projection.T)

		viewport = glGetIntegerv(GL_VIEWPORT)
		glUniform1f(glGetUniformLocation(self.wboit_splat_shader, "u_viewport_h"), float(viewport[3]))
		glUniform1f(glGetUniformLocation(self.wboit_splat_shader, "u_focal_y"), float(projection[1, 1]))
		glUniform1f(glGetUniformLocation(self.wboit_splat_shader, "u_splat_scale"), float(self.splat_scale))
		glUniform1f(glGetUniformLocation(self.wboit_splat_shader, "u_point_spacing"), float(self._estimate_point_spacing()))
		glUniform1i(glGetUniformLocation(self.wboit_splat_shader, "u_use_u_color"), int(use_uniform_color))
		glUniform4f(glGetUniformLocation(self.wboit_splat_shader, "u_color"), *self.uniform_color)
		glUniform1i(glGetUniformLocation(self.wboit_splat_shader, "u_wboit_pass"), pass_idx)

		glBindBuffer(GL_ARRAY_BUFFER, self.vertex_vbo)
		glEnableVertexAttribArray(0)
		glVertexAttribPointer(0, 3, GL_FLOAT, False, 0, None)

		if not use_uniform_color:
			glBindBuffer(GL_ARRAY_BUFFER, self.color_vbo)
			glEnableVertexAttribArray(1)
			glVertexAttribPointer(1, 4, GL_UNSIGNED_BYTE, True, 0, None)
		else:
			glDisableVertexAttribArray(1)

		try:
			glEnable(GL_POINT_SPRITE)
		except Exception:
			pass

		glDrawArrays(GL_POINTS, 0, len(self.m_vertices))

		try:
			glDisable(GL_POINT_SPRITE)
		except Exception:
			pass

		glBindBuffer(GL_ARRAY_BUFFER, 0)
		glDisableVertexAttribArray(0)
		glDisableVertexAttribArray(1)
		glUseProgram(0)

	@property
	def is_transparent(self):
		return self.render_mode == RenderMode.SPLAT

	def renderSelf(self):
		from .globals import AP

		if self.shader_program is None:
			self.initializeGL()

		if AP.wboit_pass is not None:
			if AP.wboit_pass >= 0:
				if self.is_transparent:
					self.render_wboit(AP.wboit_pass)
				return
			if self.is_transparent:
				return

		if self.render_mode == RenderMode.SPLAT:
			self._render_as_splats()
		else:
			self._render_as_points()

	def export_as_obj(self, obj_file_name='v:/fast_test.obj'):
		objFile = open(obj_file_name, 'w')
		objFile.write(f"# .obj file created with pyDpVision\n\n")
		for pt in self.m_vertices:
			txt = f"v {pt[0]:.6f} {pt[1]:.6f} {pt[2]:.6f}\n"
			objFile.write(txt)
		objFile.close()
