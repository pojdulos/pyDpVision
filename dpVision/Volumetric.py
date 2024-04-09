from dpVision.Globals import AP
from .Object import Object
from PyQt5.QtGui import *
from OpenGL.GL import *
import os
import concurrent.futures
from collections import defaultdict
import numpy as np
import pydicom
import time
import pandas as pd

# Zaczątek klasy Volumetric opartej o bibliotekę pyDICOM.
# Pamiętajmy więc, że to prawdopodobnie jeszcze nie działa
# albo działa źle

def convert_to_np_array(key, list):
    return key, np.array(list, dtype=np.float32)

class Volumetric(Object):
	def __init__(self, parent=None):
		super( Volumetric, self ).__init__( parent )
		self.m_dicom_files = []
		self.m_volume = [[[]]]
		self.i = 0
		self.v_vbo = None
	
	def moja_funkcja(self, voksel):
		#print(self.i, voksel)
		#self.i=self.i+1
		przetworzony_voksel = voksel
		return przetworzony_voksel

	def read_as_directory(self, folder_path):
		# Wczytanie wszystkich plików DICOM z folderu
		self.m_dicom_files = [pydicom.dcmread(os.path.join(folder_path, f)) for f in os.listdir(folder_path) if f.endswith('.dcm')]
		# Sortowanie plików DICOM w kolejności
		self.m_dicom_files.sort(key=lambda x: float(x.SliceLocation))
		# Tworzenie wolumetrycznego zestawu danych
		self.m_volume = np.stack([self.moja_funkcja(file.pixel_array) for file in self.m_dicom_files])
		self.m_min = np.min(self.m_volume)
		self.m_max = np.max(self.m_volume)
		
		self.m_displ = defaultdict(list)
		dims = self.m_volume.shape
		step = 4

		indices = np.mgrid[0:dims[0]:step, 0:dims[1]:step, 0:dims[2]:step].reshape(3,-1)
		
		voxel_values = self.m_volume[tuple(indices)]
		voxel_coords = indices.T

		start_time = time.time()
		
		#DRAMATYCZNIE WOLNE (unique działa szybko, ale grupowanie danych po value to koszmar):
		#self.m_displ = {value: voxel_coords[voxel_values == value] for value in np.unique(voxel_values)}
		
		#DUŻO SZYBSZE ALE WBREW MOIM OCZEKIWANIOM RÓWNIEŻ BARDZO WOLNE:		
		# # Tworzenie DataFrame z wartościami i współrzędnymi vokseli
		# df = pd.DataFrame({'values': voxel_values, 'coords': list(map(tuple, voxel_coords))})
		# # Grupowanie DataFrame według wartości vokseli
		# grouped = df.groupby('values')
		# # Tworzenie słownika z grupami
		# self.m_displ = {name: group['coords'].values.tolist() for name, group in grouped}

		#NAJPROSTSZE ALE O DZIWO NAJSZYBSZE:
		for val,coord in zip(voxel_values,voxel_coords):
			#value = float(val - self.m_min) / (self.m_max - self.m_min)
			self.m_displ[val].append(coord)	

		# WSZYSTKO TO DZIALA ZA WOLNO....
		
		end_time = time.time()
		elapsed_time = end_time - start_time
		print(f"Czas wykonania: {elapsed_time} sekund")

	def renderSelf(self):	
		glPushMatrix()
		glPushAttrib(GL_ALL_ATTRIB_BITS)
	
		glEnable(GL_COLOR_MATERIAL)
		glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
	
		glEnable(GL_POINT_SMOOTH)
		glPointSize( 5 )

		if self.v_vbo is None:
			self.v_vbo = glGenBuffers(1)

		glBindBuffer(GL_ARRAY_BUFFER, self.v_vbo)

		# Konfiguracja atrybutów wierzchołka
		glEnableVertexAttribArray(0)  # np. dla pozycji wierzchołka
		glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
				
		for val in self.m_displ:
			if val > 1000:
				value = (val - self.m_min) / (self.m_max - self.m_min)
				glColor3f(value, value, value)

				voxels = np.array(self.m_displ[val],dtype=np.float32)
				#voxels = self.m_displ[val]

				glBufferData(GL_ARRAY_BUFFER, voxels, GL_STATIC_DRAW)
				
				# Renderowanie
				glDrawArrays(GL_POINTS, 0, voxels.shape[0])

		glBindBuffer(GL_ARRAY_BUFFER, 0)

		glDisable(GL_POINT_SMOOTH)
		glDisable(GL_COLOR_MATERIAL)
	
		glPopAttrib()
		glPopMatrix()
