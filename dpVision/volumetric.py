import itertools
from math import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from OpenGL.GL import *
import numpy as np
import matplotlib.pyplot as plt
import cv2
import os
import pydicom
from tqdm import tqdm

from .globals import AP
from .object import Object
from .shaders import load_and_compile_shader, compile_shader
from .pointCloud import PointCloud
from .mesh import Mesh

# Zaczątek klasy Volumetric opartej o bibliotekę pyDICOM.
# Pamiętajmy więc, że to prawdopodobnie jeszcze nie działa
# albo działa źle

# def convert_to_np_array(key, list):
#     return key, np.array(list, dtype=np.float32)

class SliceMetadata():
	def __init__(self):
		self.image_position_patient = [0.0,0.0,0.0]
		self.slice_location = 0.0
		self.pixel_spacing = [1.0, 1.0]
		self.slice_thickness = 1.0
		self.slice_distance = 1.0
		self.gantry_detector_tilt = 0.0
	
	def __str__(self):
		txt  = f"SliceMetadata"
		txt += f"( gantry_detector_tilt = {self.gantry_detector_tilt}"
		txt += f", slice_thickness = {self.slice_thickness}"
		txt += f", slice_location = {self.slice_location}"
		txt += f", pixel_spacing = {self.pixel_spacing}"
		txt += f", image_position_patient = {self.image_position_patient} )"
		return txt
	
	def __repr__(self):
		return self.__str__()
	
class Volumetric(Object):
	def __init__(self, parent=None):
		super( Volumetric, self ).__init__( parent )
		self.m_dicom_files = []
		self.m_volume = [[[]]]
		self.i = 0
		self.v_vbo = None
		self.shader_program = None
		self.m_minDisplWin = 0.0
		self.m_maxDisplWin = 1.0
		self.m_fastDraw = True
		self.m_renderBoxes = False
		self.metadata : list[SliceMetadata] = []
		self.m_minSlice = 0
		self.m_maxSlice = 0
		self.m_minRow = 0
		self.m_maxRow = 0
		self.m_minColumn = 0
		self.m_maxColumn = 0
		self.m_filters = [
			[0,  -100,   799],
			[0, -9999, 99999],
			[0, -9999, 99999],
			[0, -9999,  4000],
			[0, -9999, 99999],
			[0, -9999, 99999],
			[0,   800,  4095]]
		
		self.m_fcolors = [
			[1.0, 0.0, 0.0],
			[0.0, 1.0, 0.0],
			[0.0, 0.0, 1.0],
			[1.0, 1.0, 0.0],
			[0.0, 1.0, 1.0],
			[1.0, 0.0, 1.0],
			[1.0, 1.0, 1.0]]

		self.m_shape = (0,0,0)
	
	@property
	def shape(self):
		return self.m_shape
	
	@shape.setter
	def shape(self, _shape):
		self.m_shape = _shape
		

	def test_gauss(self):
		from scipy.ndimage import gaussian_filter
		#volume = np.array(trójwymiarowa_lista)  # zamień 'trójwymiarowa_lista' na swoją listę
		
		sigma = 3  # Parametr sigma kontroluje stopień rozmycia
		self.m_volume = gaussian_filter(self.m_volume, sigma=sigma)

	def aply_window(self, x, c, w, ymin=0.0, ymax=1.0):
		'''	windowing C.11.2.1.2.1 Default LINEAR Function
			c - window center, w - window width
			ymin, ymax - destination data intensity range
		'''
		y = np.zeros_like(x)
		y[x <= (c - 0.5 - (w - 1) / 2)] = ymin
		y[x > (c - 0.5 + (w - 1) / 2)] = ymax
		y[(x > (c - 0.5 - (w - 1) / 2)) & (x <= (c - 0.5 + (w - 1) / 2))] = \
			((x[(x > (c - 0.5 - (w - 1) / 2)) & (x <= (c - 0.5 + (w - 1) / 2))] - (c - 0.5)) / (w - 1) + 0.5) * (
					ymax - ymin) + ymin
		return y

	def show_histogram(self):
		data = np.array(self.m_volume).flatten()

		#data = data.clip(lower=data.quantile(0.1), upper=data.quantile(0.9))
		#data = data.clip(lower=0, upper=4096)
		
		biny = np.round(np.arange(0, 1.01, 0.01),2)

		# wygeneruj histogram i zapisz wyniki
		counts, bins = np.histogram(data, bins=biny)

		# wypisz krawędzie binów i częstości
		for i in range(len(bins)-1):
			print(f"Bin: ({bins[i]}, {bins[i+1]}), Częstość: {counts[i]}")

		plt.hist(bins[:-1], bins, weights=counts)

		plt.title('Histogram')
		plt.xlabel('Wartości')
		plt.ylabel('Częstotliwość')
		plt.grid(axis='y', alpha=0.5)
		plt.show()


	def on_mouse_move(self, dx, dy):
		self.m_minDisplWin = self.m_minDisplWin + dx
		self.m_minDisplWin = self.m_minDisplWin + dy
		if self.m_minDisplWin < self.m_min:
			self.m_minDisplWin = self.m_min

		self.m_maxDisplWin = self.m_maxDisplWin - dx
		self.m_maxDisplWin = self.m_maxDisplWin + dy
		if self.m_maxDisplWin > self.m_max:
			self.m_maxDisplWin = self.m_max

		AP.updateProperties()
		AP.updateAllViews()
		#print(f"dx={dx}, dy={dy}")

	def remove_shader_program(self):
		glDeleteProgram(self.shader_program)
		self.shader_program = None

	def create_program(self):
		# Inicjalizacja i konfiguracja shaderów
		geom_filename = 'volumetric_box.geom' if self.m_renderBoxes else 'volumetric.geom'
		try:
			vertex_shader = load_and_compile_shader('volumetric.vert', GL_VERTEX_SHADER)
			geometry_shader = load_and_compile_shader(geom_filename, GL_GEOMETRY_SHADER)
			fragment_shader = load_and_compile_shader('volumetric.frag', GL_FRAGMENT_SHADER)
		except Exception as e:
			print( e )
			return
		
		# Tworzenie programu shaderów
		self.shader_program = glCreateProgram()
		
		glAttachShader(self.shader_program, vertex_shader)
		glAttachShader(self.shader_program, geometry_shader)
		glAttachShader(self.shader_program, fragment_shader)
		
		glLinkProgram(self.shader_program)
		
		# Sprawdzanie, czy program został powiązany poprawnie
		if not glGetProgramiv(self.shader_program, GL_LINK_STATUS):
			info = glGetProgramInfoLog(self.shader_program)
			if isinstance(info, bytes):
				info = info.decode('utf-8')
			print(f"Shader program link failed:\n{info}")
			glDeleteProgram(self.shader_program)
			self.shader_program = None
			return
		
		# Usuwanie shaderów (już nie są potrzebne po powiązaniu programu)
		glDeleteShader(vertex_shader)
		glDeleteShader(geometry_shader)
		glDeleteShader(fragment_shader)


	def renderSelf(self):
		glEnable(GL_PROGRAM_POINT_SIZE)
		if self.shader_program is None:
			self.create_program()

		# Używanie programu shaderów
		glUseProgram(self.shader_program)

		if self.v_vbo is None:
			self.v_vbo = glGenBuffers(1)

		glBindBuffer(GL_ARRAY_BUFFER, self.v_vbo)
		
		# Konfiguracja atrybutów wierzchołka
		glEnableVertexAttribArray(0)  # np. dla pozycji wierzchołka
		glVertexAttribPointer(0, 1, GL_FLOAT, GL_FALSE, 0, None)

		modelview = np.array(glGetFloatv(GL_MODELVIEW_MATRIX), dtype=np.float32)
		modelview_loc = glGetUniformLocation(self.shader_program, "modelviewMatrix")
		glUniformMatrix4fv(modelview_loc, 1, GL_FALSE, modelview)

		projection = np.array(glGetFloatv(GL_PROJECTION_MATRIX), dtype=np.float32)
		projection_loc = glGetUniformLocation(self.shader_program, "projectionMatrix")
		glUniformMatrix4fv(projection_loc, 1, GL_FALSE, projection)

		minColor_loc = glGetUniformLocation(self.shader_program, "minColor")
		glUniform1f( minColor_loc, self.m_minDisplWin )

		maxColor_loc = glGetUniformLocation(self.shader_program, "maxColor")
		glUniform1f( maxColor_loc, self.m_maxDisplWin )

		f_loc = glGetUniformLocation(self.shader_program, "f")
		glUniform3fv(f_loc, 7, self.m_filters)

		fcolors_loc = glGetUniformLocation(self.shader_program, "fcolors")
		glUniform3fv(fcolors_loc, 7, self.m_fcolors)

		if not self.m_fastDraw and not AP.mouse_key_pressed:
			factor = 1
		elif len(self.m_volume) < 1536:
			factor = 4
		else:
			factor = 8

		factor_loc = glGetUniformLocation(self.shader_program, "factor")
		glUniform1i( factor_loc, factor )
		
		first_slice = factor*int(self.m_minSlice/factor)
		first_row = factor*int(self.m_minRow/factor)
		first_column = factor*int(self.m_minColumn/factor)

		# subvolume = self.m_volume[
		# 	first_slice:self.m_maxSlice+1:factor,
		# 	first_row:self.m_maxRow+1:factor,
		# 	first_column:self.m_maxColumn+1:factor
		# 	]

		subvolume = [slice[first_row:self.m_maxRow+1:factor,first_column:self.m_maxColumn+1:factor] for slice in self.m_volume[first_slice:self.m_maxSlice+1:factor]]
#		subvolume = np.array(subvolume, dtype=np.float32)

		# small_shape = subvolume.shape
		small_shape = (len(subvolume), subvolume[0].shape[0], subvolume[0].shape[1])
		
		sizeX_loc = glGetUniformLocation(self.shader_program, "sizeX")
		glUniform1i( sizeX_loc, small_shape[2] )

		sizeY_loc = glGetUniformLocation(self.shader_program, "sizeY")
		glUniform1i( sizeY_loc, small_shape[1] )

		for idx_in_subvolume in range(small_shape[0]):
			true_index_of_slice = first_slice + idx_in_subvolume * factor
			
			colors = np.array(subvolume[idx_in_subvolume], dtype=np.float32).flatten()

			glBufferData(GL_ARRAY_BUFFER, colors.nbytes, colors, GL_STATIC_DRAW)
		
			metadata = self.metadata[true_index_of_slice]

			imagePosition = [
				metadata.image_position_patient[0] + metadata.pixel_spacing[0] * float(first_column),
				metadata.image_position_patient[1] + metadata.pixel_spacing[1] * float(first_row),
				metadata.image_position_patient[2]
			]
			
			voxel_size = [
				metadata.pixel_spacing[0],
				metadata.pixel_spacing[1],
				metadata.slice_thickness
			]

			imagePosition_loc = glGetUniformLocation(self.shader_program, "imagePosition")
			glUniform3fv( imagePosition_loc, 1, imagePosition )
			
			voxelSize_loc = glGetUniformLocation(self.shader_program, "voxelSize")
			glUniform3fv( voxelSize_loc, 1, voxel_size )

			glDrawArrays(GL_POINTS, 0, colors.shape[0])

		glBindBuffer(GL_ARRAY_BUFFER, 0)
		glUseProgram(0) # Wyłączenie programu shaderów
		glDisable(GL_PROGRAM_POINT_SIZE)


	# Domyślne ustawienie parametrów dla algorytmu SIFT
	# nfeatures - Liczba kluczowych punktów do zachowania. Domyślnie 0, co oznacza, że nie ma limitu.
	# nOctaveLayers - Liczba warstw w każdej oktawie. Domyślnie 3
	# contrastThreshold - Próg eliminacji kluczowych punktów o niskim kontraście. Domyślnie 0.04
	# edgeThreshold - Próg eliminacji kluczowych punktów na krawędziach. Domyślnie 10
	# sigma - Początkowa sigma dla Gaussowskiego rozmycia. Domyślnie 1.6
	def sift_cloud(self, nfeatures = 0, nOctaveLayers = 3, contrastThreshold = 0.04, edgeThreshold = 10, sigma = 1.6, factor=1):
		vertices = []

		for idx_of_slice in range(self.m_minSlice, self.m_maxSlice+1):
			image = self.m_volume[idx_of_slice][self.m_minRow:self.m_maxRow+1, self.m_minColumn:self.m_maxColumn+1]

			pixel_spacing = list( self.metadata[idx_of_slice].pixel_spacing )
			
			position = [
				self.metadata[idx_of_slice].image_position_patient[0] + pixel_spacing[0] * float(self.m_minColumn),
				self.metadata[idx_of_slice].image_position_patient[1] + pixel_spacing[1] * float(self.m_minRow),
				self.metadata[idx_of_slice].image_position_patient[2]
			]

			# position = self.metadata[idx_of_slice].image_position_patient

			print(f"slice {idx_of_slice}: position = {position}")
			

			# if gauss:
			# 	image = gaussian_filter(image, sigma=gauss)

			image = [ [min(max(self.m_minDisplWin,i),self.m_maxDisplWin) for i in row] for row in image]

			# Normalizuj dane obrazu do zakresu 0-255
			obraz = cv2.normalize(np.array(image), None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)


			# Domyślne ustawienie parametrów dla algorytmu SIFT
			
			# Liczba kluczowych punktów do zachowania. Domyślnie 0, co oznacza, że nie ma limitu.
			nfeatures = 0
			
			# Liczba warstw w każdej oktawie. Domyślnie 3
			nOctaveLayers = 5
			
			# Próg eliminacji kluczowych punktów o niskim kontraście. Domyślnie 0.04
			contrastThreshold = 0.05
			
			# Próg eliminacji kluczowych punktów na krawędziach. Domyślnie 10
			edgeThreshold = 10
			
			# Początkowa sigma dla Gaussowskiego rozmycia. Domyślnie 1.6
			sigma = 0.4

			# Tworzenie obiektu SIFT z ustawionymi parametrami
			sift = cv2.SIFT_create(	nfeatures=nfeatures, nOctaveLayers=nOctaveLayers, 
			 						contrastThreshold=contrastThreshold, edgeThreshold=edgeThreshold, sigma=sigma)

			# Znajdź punkty kluczowe i deskryptory za pomocą SIFT
			keypoints, descriptors = sift.detectAndCompute(obraz, None)

			# orb = cv2.ORB_create()
			# keypoints, descriptors = orb.detectAndCompute(obraz, None)

			for key in keypoints:
				point = [
							float(position[0]) + pixel_spacing[0] * key.pt[0],
							float(position[1]) + pixel_spacing[1] * key.pt[1],
							float(position[2])
				]
				
				vertices.append(np.array(point, dtype=np.float32))

		cloud = PointCloud()
		cloud.m_vertices = np.array(vertices, dtype=np.float32)
		return cloud

	def marching_cube(self, factor=1, close_boundary=True, sigma_unit=0.8, min_volume=50):

		import mcubes
		import numpy as np
		from scipy.ndimage import gaussian_filter, map_coordinates
		from scipy import ndimage as ndi

		# ------------------------------------------------------------
		# 1. ROI extraction (bez subsamplingu)
		# ------------------------------------------------------------

		first_slice = factor * int(self.m_minSlice / factor)
		first_row = factor * int(self.m_minRow / factor)
		first_column = factor * int(self.m_minColumn / factor)

		image = [
			slice[first_row:self.m_maxRow+1, first_column:self.m_maxColumn+1]
			for slice in self.m_volume[first_slice:self.m_maxSlice+1]
		]

		image = np.array(image, dtype=np.float32)

		# ------------------------------------------------------------
		# 2. Gaussian smoothing (anti-aliasing)
		# ------------------------------------------------------------

		px = self.metadata[1].pixel_spacing[0]
		py = self.metadata[1].pixel_spacing[1]
		pz = self.metadata[1].slice_distance

		sigma_mm = sigma_unit * ( 0.5 * (px + py) )

		sigma = (
			sigma_mm / pz,
			sigma_mm / py,
			sigma_mm / px,
		)

		image = gaussian_filter(image, sigma=sigma)

		# ------------------------------------------------------------
		# 3. Subsampling (factor)
		# ------------------------------------------------------------

		if factor > 1:
			image = image[::factor, ::factor, ::factor]

		# ------------------------------------------------------------
		# 4. Gradient computation
		# ------------------------------------------------------------

		gz, gy, gx = np.gradient(image)
		grad = np.sqrt(gx*gx + gy*gy + gz*gz)

		g = grad.ravel()
		v = image.ravel()

		# ------------------------------------------------------------
		# 5. Automatic threshold estimation
		# ------------------------------------------------------------

		g_thr = np.percentile(g, 95)

		mask_grad = (g >= g_thr) & (v > 150) & (v < 6000)

		if np.sum(mask_grad) < 100:
			threshold_init = 300
		else:
			threshold_init = np.percentile(v[mask_grad], 30)

		threshold_init *= 1.05

		print("threshold_init:", threshold_init)

		# ------------------------------------------------------------
		# 6. Binary segmentation
		# ------------------------------------------------------------

		mask_bone = image > threshold_init

		structure = ndi.generate_binary_structure(3,1)

		mask_bone = ndi.binary_opening(mask_bone, structure=structure, iterations=1)
		mask_bone = ndi.binary_closing(mask_bone, structure=structure, iterations=2)

		labels, n = ndi.label(mask_bone)
		sizes = ndi.sum(mask_bone, labels, index=np.arange(1, n+1))

		voxel_volume = px * py * pz
		sizes_mm3 = sizes * voxel_volume

		keep = np.zeros(n + 1, dtype=bool)
		keep[1:][sizes_mm3 >= min_volume] = True

		mask_clean = keep[labels]

		image_clean = image.copy()
		image_clean[~mask_clean] = image.min()

		# ------------------------------------------------------------
		# 7. Marching cubes
		# ------------------------------------------------------------

		if close_boundary:
			image_mc = np.pad(image_clean, 1, mode='constant')
		else:
			image_mc = image_clean

		points, faces = mcubes.marching_cubes(image_mc, threshold_init)

		offset = 1 if close_boundary else 0

		# ------------------------------------------------------------
		# 8. Gradient confidence on surface
		# ------------------------------------------------------------

		coords = np.vstack([
			points[:,0] - offset,
			points[:,1] - offset,
			points[:,2] - offset
		])

		grad_values = map_coordinates(grad, coords, order=1, mode='nearest')

		print("Gradient on surface:")
		print("min:", grad_values.min())
		print("max:", grad_values.max())
		print("mean:", grad_values.mean())

		for p in [1,5,10,50,90,95,99]:
			print(f"p{p}:", np.percentile(grad_values, p))

		# ------------------------------------------------------------
		# 9. Transform vertices to world coordinates
		# ------------------------------------------------------------

		origin = [
			self.metadata[first_slice].image_position_patient[0] + px * float(first_column),
			self.metadata[first_slice].image_position_patient[1] + py * float(first_row),
			self.metadata[first_slice].image_position_patient[2]
		]

		if first_slice > 0:
			slice_distance = (
				self.metadata[first_slice].image_position_patient[2] -
				self.metadata[first_slice-1].image_position_patient[2]
			)
		else:
			slice_distance = (
				self.metadata[first_slice+1].image_position_patient[2] -
				self.metadata[first_slice].image_position_patient[2]
			)

		gantra = self.metadata[0].gantry_detector_tilt

		if close_boundary:
			origin[0] -= px * factor
			origin[1] -= py * factor
			origin[2] -= slice_distance * factor

		scale = [px*factor, py*factor, slice_distance*factor]

		vertices = []

		for p in points:

			vx = [
				p[2] * scale[0],
				p[1] * scale[1],
				p[0] * scale[2]
			]

			if gantra != 0.0:
				vx[1] += vx[2] * tan(gantra)

			vx = [vx[i] + origin[i] for i in range(3)]

			vertices.append(vx)

		mesh = Mesh.create(vertices=vertices, faces=faces, invert_normals=True)
		AP.addObject(mesh, self)
		
	def adjustMinMax(self, calc_color=True, winMin=None, winMax=None, min_slice=None, max_slice=None, min_row=None, max_row=None, min_column=None, max_column=None):
		if calc_color:
			self.m_min = np.min(self.m_volume[0])
			self.m_max = np.max(self.m_volume[0])
			for i in tqdm(range(len(self.m_volume)), desc='Processing'):
				self.m_min = min(self.m_min, np.min(self.m_volume[i]))
				self.m_max = max(self.m_max, np.max(self.m_volume[i]))
		self.m_minDisplWin = winMin if winMin else self.m_min
		self.m_maxDisplWin = winMax if winMax else self.m_max
		self.m_minSlice = min_slice if min_slice else 0
		self.m_maxSlice = max_slice if max_slice else self.shape[0]-1
		self.m_minRow = min_row if min_row else 0
		self.m_maxRow = max_row if max_row else self.shape[1]-1
		self.m_minColumn = min_column if min_column else 0
		self.m_maxColumn = max_column if max_column else self.shape[2]-1

	def adjustMinMaxColor(self, color):
		self.m_min = min(self.m_min, color)
		self.m_max = max(self.m_max, color)
		self.m_minDisplWin = self.m_min
		self.m_maxDisplWin = self.m_max

	@staticmethod
	def create(layers=256, rows=256, columns=256):
		volum = Volumetric()
		volum.m_volume = [] #np.zeros((layers, rows, columns), dtype=np.float32)

		for i in tqdm(range(layers), desc=f"creating volume ({layers}, {rows}, {columns})..."):
			try:
				subarray = np.zeros((rows,columns), dtype='float32')
			except MemoryError:
				print("\nBRAK PAMIĘCI !!!")
				return None
			# subarray[:,:] = i
			volum.m_volume.append(subarray)

		volum.shape = (layers, rows, columns)

		for l in range(layers):
			mdata = SliceMetadata()
			mdata.image_position_patient[2] = float(l)
			volum.metadata.append(mdata)

		volum.m_min, volum.m_max = 0., 0.
		volum.adjustMinMax(calc_color=False)

		for filter in volum.m_filters:
			filter[1] = max(filter[1], volum.m_minDisplWin)
			filter[2] = min(filter[2], volum.m_maxDisplWin)
		return volum
	
	def drawBox(self, origin=[0,0,0], size=[10,10,10], color=1000.):
		layers, rows, cols = self.shape
		for z in tqdm(range(size[0]), desc=f"drawing volumetric box: origin = {origin}, size = {size}..."):
			for y in range(size[1]):
				for x in range(size[2]):
					if (col := origin[2] + x) < cols and (row := origin[1] + y) < rows and (layer := origin[0] + z) < layers:
						self.m_volume[layer][row, col] = color
		self.adjustMinMaxColor(color)

	def drawSphere(self, origin=[0,0,0], radius=1, color=1000.):
		origin_z, origin_y, origin_x = origin
		z_min = max(0, origin_z - radius)
		z_max = min(self.shape[0], origin_z + radius + 1)
		y_min = max(0, origin_y - radius)
		y_max = min(self.shape[1], origin_y + radius + 1)
		x_min = max(0, origin_x - radius)
		x_max = min(self.shape[2], origin_x + radius + 1)

		# Przygotowanie danych wejściowych
		radius_squared = radius**2

		# Tworzenie siatki współrzędnych
		z = np.arange(z_min, z_max)
		y = np.arange(y_min, y_max)
		x = np.arange(x_min, x_max)
		zv, yv, xv = np.meshgrid(z, y, x, indexing='ij')

		# Obliczanie maski dla sfer
		mask = (xv - origin_x)**2 + (yv - origin_y)**2 + (zv - origin_z)**2 <= radius_squared

		# Rysowanie sfery
		for z_idx in tqdm(range(z_min,z_max), desc=f"drawing volumetric sphere: origin = {origin}, radius = {radius}..."):
			slice_mask = mask[z_idx - z_min,:,:]

			shifted_mask = np.zeros_like(self.m_volume[z_idx], dtype=bool)
			shifted_mask[y_min:y_min+slice_mask.shape[0], x_min:x_min+slice_mask.shape[1]] = slice_mask

			self.m_volume[z_idx][shifted_mask] = color			
		self.adjustMinMaxColor(color)


	# def drawEllipsoid(self, origin=[0,0,0], radii=[1,1,1], color=1000.):
	# 	origin_z, origin_y, origin_x = origin
	# 	radius_z, radius_y, radius_x = radii
	# 	for z in range(self.shape[0]):
	# 		for y in range(self.shape[1]):
	# 			for x in range(self.shape[2]):
	# 				if ((x - origin_x) / radius_x) ** 2 + ((y - origin_y) / radius_y) ** 2 + ((z - origin_z) / radius_z) ** 2 <= 1:
	# 					self.m_volume[z, y, x] = color
	# 	# self.m_volume.flush()
	# 	self.adjustMinMax()

	def drawCylinder(self, origin=[0,0,0], radius=1, height=1, axis='z', color=1000.):
		origin_z, origin_y, origin_x = origin
		#radius = float(radius)
		height = int(height)
		
		if axis == 'z':
			for z in range(origin_z - height // 2, origin_z + height // 2 + 1):
				for y in range(origin_y - radius, origin_y + radius + 1):
					for x in range(origin_x - radius, origin_x + radius + 1):
						if ((y - origin_y) ** 2 + (x - origin_x) ** 2 <= radius ** 2):
							self.m_volume[z][y, x] = color
		elif axis == 'y':
			for z in range(origin_z - radius, origin_z + radius + 1):
				for y in range(origin_y - height // 2, origin_y + height // 2 + 1):
					for x in range(origin_x - radius, origin_x + radius + 1):
						if ((z - origin_z) ** 2 + (x - origin_x) ** 2 <= radius ** 2):
							self.m_volume[z][y, x] = color
		elif axis == 'x':
			for z in range(origin_z - radius, origin_z + radius + 1):
				for y in range(origin_y - radius, origin_y + radius + 1):
					for x in range(origin_x - height // 2, origin_x + height // 2 + 1):
						if ((z - origin_z) ** 2 + (y - origin_y) ** 2 <= radius ** 2):
							self.m_volume[z][y, x] = color
		else:
			raise ValueError("Axis must be one of 'x', 'y', or 'z'.")
		# self.m_volume.flush()
		self.adjustMinMaxColor(color)

	def set_pixel_size(self, image_x=1.0, image_y=1.0, slice_thickness=1.0):
		for n,mdata in enumerate(self.metadata):
			mdata.pixel_spacing = [image_x, image_y]
			mdata.slice_thickness = slice_thickness
			mdata.slice_distance = slice_thickness
			mdata.slice_location = slice_thickness*n
			mdata.image_position_patient[2] = slice_thickness*n

	def set_position(self, x=0.0, y=0.0, z=0.0):
		for n,mdata in enumerate(self.metadata):
			mdata.image_position_patient[0] = x
			mdata.image_position_patient[1] = y
			mdata.image_position_patient[2] = z + mdata.slice_distance*n
			mdata.slice_location = mdata.image_position_patient[2]

	# def export(self, dir="v:/test/", file_base="image_", ext=".png"):
	# 	from PIL import Image
	# 	import os
	# 	for i,layer in enumerate(self.m_volume):
	# 		# stwórz obraz
	# 		img = Image.fromarray(layer.astype(np.uint8))

	# 		# Utwórz nazwę pliku zgodnie z formatem "file_base_numer.ext"
	# 		filename = os.path.join(dir, f"{file_base}{i:03}{ext}")

	# 		# Zapisz obraz na dysku
	# 		img.save(filename)			

	def export(self, dir="v:/test/", file_base="image_", ext=".dcm"):
		if not os.path.exists(dir):
			os.makedirs(dir)

		for i, layer in enumerate(self.m_volume):
			# Tworzenie obiektu DICOM
			ds = pydicom.FileDataset(os.path.join(dir, f"{file_base}{i:03}{ext}"), {}, file_meta=None, preamble=b"\0" * 128)
			
			# Ustawienie podstawowych atrybutów DICOM
			ds.PatientName = "Anonymous"
			ds.PatientID = "123456"
			ds.Modality = "MR"
			ds.SeriesDescription = "generated with pyDpVision software"
			ds.Rows, ds.Columns = layer.shape
			ds.PixelSpacing = self.metadata[i].pixel_spacing
			ds.BitsAllocated = 16  # Ustawiamy na 16 bitów
			ds.BitsStored = 16
			ds.HighBit = 15
			ds.PixelRepresentation = 1  # Ustawiamy na wartość ze znakiem (signed)
			
			# Przykładowe dodatkowe atrybuty DICOM
			ds.ImagePositionPatient = self.metadata[i].image_position_patient
			ds.RescaleIntercept = -1000.0  # Jeśli potrzebne, ustawienie interceptu
			ds.RescaleSlope = 1.0  # Jeśli potrzebne, ustawienie nachylenia
			ds.SliceThickness = self.metadata[i].slice_thickness
			ds.SliceLocation = self.metadata[i].slice_location

			ds.SamplesPerPixel = 1
			ds.PhotometricInterpretation = 'MONOCHROME2'
			
			ds.file_meta.TransferSyntaxUID = pydicom.uid.ImplicitVRLittleEndian 
			
			# Konwersja warstwy na format DICOM
			# Zakładając, że warstwa jest typu int lub float, możesz ją rzutować na int16
			image = layer.astype(np.int16)
			ds.PixelData = image.tobytes()

			# Zapisanie pliku DICOM
			ds.save_as(os.path.join(dir, f"{file_base}{i:03}{ext}"))
