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
from .shaders import create_program
#from numba import njit, prange
#import cupy as cp
import time

import ctypes
#import cupy.cuda.runtime as cuda_runtime
#import pycuda.gl as cudagl
#import pycuda.driver as cuda


# @njit(parallel=True)
# def update_projection_numba(vertices, rotation_matrix, real_dims, gains, d, blend):
# 	N = vertices.shape[0]
# 	rotated = vertices @ rotation_matrix.T

# 	x = rotated[:, real_dims[0]] * gains[0]
# 	y = rotated[:, real_dims[1]] * gains[1]
# 	z = rotated[:, real_dims[2]] * gains[2]

# 	if real_dims[3] >= 0:
# 		w = rotated[:, real_dims[3]] * gains[3]
# 	else:
# 		w = np.zeros(N, dtype=np.float32)

# 	result = np.empty((N, 3), dtype=np.float32)

# 	for i in prange(N):
# 		factor = d / max(d - w[i], 1e-3)
# 		px = x[i] * factor
# 		py = y[i] * factor
# 		pz = z[i] * factor

# 		result[i, 0] = x[i] * (1 - blend) + px * blend
# 		result[i, 1] = y[i] * (1 - blend) + py * blend
# 		result[i, 2] = z[i] * (1 - blend) + pz * blend

# 	return result



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
		self.m_edges = None
		self.shader_program = None
		self.m_current_ix = 30
		self.m_current_iy = 30
		# self.m_real_dims = [0, 1, 2, 3]
		self.m_real_dims = [i if i<self.m_dimensions else None for i in range(4)]
		self.m_gains = [1.0, 1.0, 1.0, 1.0]
		self.m_rplanes = [[0, self.m_dimensions-1],[1, self.m_dimensions-1]]
		self.v_vbo = None
		self.c_vbo = None
		self.n_vbo = None
		self.buf_changed = False

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

	# def update_vertex_buffer(self):
	# 	if hasattr(self, "vertex_vbo") and self.vertex_vbo:
	# 		glBindBuffer(GL_ARRAY_BUFFER, self.vertex_vbo)
	# 		glBufferSubData(GL_ARRAY_BUFFER, 0, self.m_projected_vertices.nbytes, self.m_projected_vertices)
	# 		glBindBuffer(GL_ARRAY_BUFFER, 0)
	def update_vertex_buffer(self):
		if hasattr(self, "vertex_vbo") and self.vertex_vbo:
			glBindBuffer(GL_ARRAY_BUFFER, self.vertex_vbo)

			# ptr = glMapBuffer(GL_ARRAY_BUFFER, GL_WRITE_ONLY)
			ptr = glMapBufferRange(GL_ARRAY_BUFFER, 0, self.m_projected_vertices.nbytes,
                       GL_MAP_WRITE_BIT | GL_MAP_INVALIDATE_BUFFER_BIT)

			if ptr:
				from ctypes import memmove, c_void_p
				memmove(c_void_p(ptr), self.m_projected_vertices.ctypes.data, self.m_projected_vertices.nbytes)
				glUnmapBuffer(GL_ARRAY_BUFFER)

			glBindBuffer(GL_ARRAY_BUFFER, 0)

	def initializeGL(self):
		# --- przygotuj VBO na punkty (wierzchołki + kolory) ---
		self.vertex_vbo = glGenBuffers(1)
		self.color_vbo = glGenBuffers(1)

		#  self.register_vbo_with_cuda()

		self.shader_program = create_program(vertex_shader_name='nDimCloud.vert', fragment_shader_name='nDimCloud.frag')

		# vertices = np.array(self.m_projected_vertices, dtype=np.float32)
		glBindBuffer(GL_ARRAY_BUFFER, self.vertex_vbo)
		glBufferData(GL_ARRAY_BUFFER, self.m_projected_vertices.nbytes, self.m_projected_vertices, GL_DYNAMIC_DRAW)

		colors = np.array(self.m_vcolors, dtype=np.uint8)
		glBindBuffer(GL_ARRAY_BUFFER, self.color_vbo)
		glBufferData(GL_ARRAY_BUFFER, colors.nbytes, colors, GL_STATIC_DRAW)
			
		glBindBuffer(GL_ARRAY_BUFFER, 0)

		if self.m_edges:
			self.edge_vbo = glGenBuffers(1)
			edge_indices = np.array(self.m_edges, dtype=np.uint32).flatten()

			glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.edge_vbo)
			glBufferData(GL_ELEMENT_ARRAY_BUFFER, edge_indices.nbytes, edge_indices, GL_DYNAMIC_DRAW)

			glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

	def renderSelf(self):
		if self.shader_program is None:
			self.initializeGL()
		
		# if self.buf_changed:
		# 	self.update_vertex_buffer()
		# 	self.buf_changed = False

		use_uniform_color = len(self.m_vcolors) < len(self.m_projected_vertices)

		# Używaj własnego shader program (przypuśćmy self.shaderProgram)
		glUseProgram(self.shader_program)

		# --- Punkty ---
		glEnable(GL_POINT_SMOOTH)
		glEnable(GL_PROGRAM_POINT_SIZE)
		glPointSize(7)

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
		glUniform4f(u_color_loc, 0.5, 0.5, 0.5, 1.0)			

		# print("Drawing", len(self.m_projected_vertices), "points")
		glDrawArrays(GL_POINTS, 0, len(self.m_projected_vertices))

		# --- Krawędzie ---
		if self.m_edges and len(self.m_edges):
			glLineWidth(2.0)
			glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.edge_vbo)
			glDrawElements(GL_LINES, len(self.m_edges)*2, GL_UNSIGNED_INT, None)

		# Clean up
		glBindBuffer(GL_ARRAY_BUFFER, 0)
		glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
		glDisableVertexAttribArray(0)
		glDisableVertexAttribArray(1)

		glUseProgram(0)


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


	# def update_projection(self, rotation_matrix, d=50.0, blend=0.5):
		
	# 	self.m_projected_vertices = np.array([
	# 		self.project_nd_to_3d(np.dot(rotation_matrix, np.array(v)), d, blend)
	# 		for v in self.m_vertices
	# 	], dtype=np.float32)

	# 	self.update_vertex_buffer()

	def update_projection_fast(self, rotation_matrix, d=50.0, blend=0.5):
		# Obrót całej chmury punktów naraz
		rotated = self.m_vertices @ rotation_matrix.T  # shape: (N, D)

		# Wydzielenie x, y, z (i opcjonalnie w)
		x = rotated[:, self.m_real_dims[0]] * self.m_gains[0]
		y = rotated[:, self.m_real_dims[1]] * self.m_gains[1]
		z = rotated[:, self.m_real_dims[2]] * self.m_gains[2]

		if self.m_real_dims[3] is not None:
			w = rotated[:, self.m_real_dims[3]] * self.m_gains[3]
			factor = d / np.maximum(d - w, 1e-3)

			px = x * factor
			py = y * factor
			pz = z * factor

			x = x * (1 - blend) + px * blend
			y = y * (1 - blend) + py * blend
			z = z * (1 - blend) + pz * blend

		self.m_projected_vertices = np.stack((x, y, z), axis=-1).astype(np.float32)

		self.update_vertex_buffer()


	def rotation_matrix_nd(self, plane, theta):
		"""
		Zwraca macierz obrotu w wymiarze `dim`,
		obracającą o kąt `theta` w płaszczyźnie (i, j).
		"""
		i, j = plane
		assert 0 <= i < j < self.m_dimensions, "Nieprawidłowe indeksy osi"

		R = np.identity(self.m_dimensions, dtype=np.float32)

		cos_t = np.cos(theta)
		sin_t = np.sin(theta)

		R[i, i] = cos_t
		R[j, j] = cos_t
		R[i, j] = -sin_t
		R[j, i] = sin_t

		return R





	def update_projection(self, rotation_matrix, d=50.0, blend=0.5):
		real_dims = np.array([
			self.m_real_dims[0],
			self.m_real_dims[1],
			self.m_real_dims[2],
			self.m_real_dims[3] if self.m_real_dims[3] is not None else -1
		], dtype=np.int32)
		gains = np.array(self.m_gains, dtype=np.float32)

		self.m_projected_vertices = update_projection_numba(
			self.m_vertices,
			rotation_matrix,
			real_dims,
			gains,
			d,
			blend
		)

		self.update_vertex_buffer()


	# def register_vbo_with_cuda(self):
	# 	if not hasattr(self, 'cuda_vbo_resource') or self.cuda_vbo_resource is None:
	# 		self.cuda_vbo_resource = cudagl.RegisteredBuffer(int(self.vertex_vbo), cuda.graphics_map_flags.WRITE_DISCARD)

	# def update_vertex_buffer_gpu(self, result_gpu):
	# 	if not hasattr(self, 'cuda_vbo_resource') or self.cuda_vbo_resource is None:
	# 		raise RuntimeError("CUDA resource not registered!")

	# 	size_in_bytes = result_gpu.nbytes

	# 	# Mapowanie zasobu
	# 	mapped_buf = self.cuda_vbo_resource.map()

	# 	try:
	# 		vbo_ptr, vbo_size = mapped_buf.device_ptr_and_size()
	# 		src_ptr = result_gpu.data.ptr

	# 		cuda.memcpy_dtod(vbo_ptr, src_ptr, size_in_bytes)

	# 	finally:
	# 		mapped_buf.unmap()

	def update_vertex_buffer_gpu(self, result_gpu):
		if hasattr(self, "vertex_vbo") and self.vertex_vbo:
			glBindBuffer(GL_ARRAY_BUFFER, self.vertex_vbo)

			size_in_bytes = result_gpu.nbytes

			# Mapujemy bufor OpenGL do wskaźnika w pamięci GPU
			ptr = glMapBufferRange(GL_ARRAY_BUFFER, 0, size_in_bytes,
								GL_MAP_WRITE_BIT | GL_MAP_INVALIDATE_BUFFER_BIT)

			if not ptr:
				raise RuntimeError("Failed to map OpenGL buffer")

			# Wskaźnik do mapped OpenGL buffer
			dst_ptr = ctypes.c_void_p(ptr)

			# Pobieramy wskaźnik źródłowy do CuPy array
			src_ptr = result_gpu.data.ptr

			# Kopiujemy pamięć GPU → GPU (cudaMemcpyDeviceToDevice)
			# cp.cuda.runtime.memcpy(dst_ptr.value, src_ptr, size_in_bytes, cp.cuda.runtime.memcpyDeviceToDevice)
			cp.cuda.runtime.memcpy(dst_ptr.value, src_ptr, size_in_bytes, cp.cuda.runtime.memcpyDeviceToHost)

			# Odmapuj bufor
			glUnmapBuffer(GL_ARRAY_BUFFER)

			glBindBuffer(GL_ARRAY_BUFFER, 0)



	# def update_projection_cupy(self, rotation_matrix, d=50.0, blend=0.5):
	# 	# start = time.perf_counter()

	# 	# Konwertujemy dane do tablicy CuPy
	# 	vertices_gpu = cp.asarray(self.m_vertices)  # automatyczne przerzucenie na GPU
	# 	rotation_gpu = cp.asarray(rotation_matrix)

	# 	# print("convertion time", time.perf_counter() - start)
	# 	# start = time.perf_counter()

	# 	# Obrót
	# 	rotated = vertices_gpu @ rotation_gpu.T

	# 	# print("rotation time", time.perf_counter() - start)
	# 	# start = time.perf_counter()

	# 	# Wydzielenie potrzebnych osi
	# 	x = rotated[:, self.m_real_dims[0]] * self.m_gains[0]
	# 	y = rotated[:, self.m_real_dims[1]] * self.m_gains[1]
	# 	z = rotated[:, self.m_real_dims[2]] * self.m_gains[2]

	# 	if self.m_real_dims[3] is not None:
	# 		w = rotated[:, self.m_real_dims[3]] * self.m_gains[3]
	# 	else:
	# 		w = cp.zeros_like(x)

	# 	factor = d / cp.maximum(d - w, 1e-3)
	# 	px = x * factor
	# 	py = y * factor
	# 	pz = z * factor

	# 	x_out = x * (1 - blend) + px * blend
	# 	y_out = y * (1 - blend) + py * blend
	# 	z_out = z * (1 - blend) + pz * blend

	# 	result_gpu = cp.stack((x_out, y_out, z_out), axis=-1)

	# 	# print("another operations time", time.perf_counter() - start)
	# 	# start = time.perf_counter()


	# 	# Ściągamy dane z powrotem z GPU do CPU
	# 	self.m_projected_vertices = cp.asnumpy(result_gpu) # .astype(np.float32)
	# 	# self.update_vertex_buffer_gpu(result_gpu)

	# 	# print("copy to buffer time", time.perf_counter() - start)
	# 	# start = time.perf_counter()

	# 	self.update_vertex_buffer()
	# 	# self.buf_changed = True
	
	# 	# print("update buffer time", time.perf_counter() - start)

# wyniki:
# convertion time 0.06809849999990547
# rotation time 0.14803959999699146
# another operations time 0.040373099996941164
# copy to buffer time 3.089999518124387e-05


	def projectTo3D(self, total = 360):
		thetaX = 2 * np.pi * self.m_current_ix / total
		Rx = self.rotation_matrix_nd(self.m_rplanes[0], thetaX)
		
		thetaY = 2 * np.pi * self.m_current_iy / total
		Ry = self.rotation_matrix_nd(self.m_rplanes[1], thetaY)
		
		R = Ry @ Rx

		self.update_projection_fast(R, d=50)
		#self.update_projection_cupy(R, d=50)


	def on_mouse_move(self, dx, dy):
		total = 360

		if dx:
			self.m_current_ix += ( 3 if dx<0 else -3 ) % total
		
		if dy:
			self.m_current_iy += ( 3 if dy>0 else -3 ) % total
		
		self.projectTo3D(total)

		AP.updateProperties()
		AP.updateAllViews()

