from .Object import Object
from PyQt5.QtGui import *
from OpenGL.GL import *
import os
import numpy as np
import pydicom

# Zaczątek klasy Volumetric opartej o bibliotekę pyDICOM.
# Pamiętajmy więc, że to prawdopodobnie jeszcze nie działa
# albo działa źle

class Volumetric(Object):
	def __init__(self, parent=None):
		super( Volumetric, self ).__init__( parent )
		self.m_dicom_files = []
		self.m_volume = [[[]]]
		self.i = 0
	
	def moja_funkcja(self, voksel):
		print(self.i, voksel)
		self.i=self.i+1
		przetworzony_voksel = voksel
		return przetworzony_voksel

	def read_as_directory(self, folder_path):
		# Wczytanie wszystkich plików DICOM z folderu
		self.m_dicom_files = [pydicom.dcmread(os.path.join(folder_path, f)) for f in os.listdir(folder_path) if f.endswith('.dcm')]
		# Sortowanie plików DICOM w kolejności
		self.m_dicom_files.sort(key=lambda x: float(x.SliceLocation))
		# Tworzenie wolumetrycznego zestawu danych
		self.m_volume = np.stack([self.moja_funkcja(file.pixel_array) for file in self.m_dicom_files])
		
		# WSZYSTKO TO DZIALA ZA WOLNO....
		# from collections import defaultdict
		# # Inicjalizacja pustego słownika
		# voxel_dict = defaultdict(list)
		# # Iteracja przez każdy voksel w wolumenie
		# for i in range(self.m_volume.shape[0]):
		# 	for j in range(self.m_volume.shape[1]):
		# 		for k in range(self.m_volume.shape[2]):
		# 			# Dodanie współrzędnych do odpowiedniej listy w słowniku
		# 			voxel_dict[self.m_volume[i, j, k]].append((i, j, k))
		# 			print(i, j, k)

		# # Tworzenie unikalnych wartości i indeksów
		# values, indices = np.unique(self.m_volume, return_inverse=True)
		# # Tworzenie pustego słownika
		# voxel_dict = {value: [] for value in values}
		# # Wypełnianie słownika
		# indices = indices.reshape(self.m_volume.shape)
		# for value in values:
		# 	voxel_dict[value] = np.argwhere(indices == value).tolist()


	def renderSelf(self):	
		# SZUKAM EFEKTYWNEJ METODY RENDEROWANIA WOLUMENU
		# NIESTETY PYTHON TU BARDZO USTEPUJE C++
		pass
