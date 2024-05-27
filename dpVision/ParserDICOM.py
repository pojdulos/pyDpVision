from dpVision.Globals import AP
from dpVision.Volumetric import Volumetric, SliceMetadata
from .Parser import Parser
import numpy as np
from math import *
import os
from PyQt5.QtGui import *
import pydicom

# Zaczątek parsera plików DICOM na bazie biblioteki pyDICOM.
# Pamiętajmy wiec, podobnie jak w przypadku klasy Volumetric,
# że to jeszcze nie ma prawa działać

class ParserDICOM(Parser):
	descr = 'DICOM files'
	load_exts = ['.dcm']
	#save_exts = ['.dcm']

	@staticmethod	
	def convert_to_HU(dcm, b=None, m=None):
		print(dcm)
		if b is None: b = float(getattr(dcm, 'RescaleIntercept', 0.0))
		if m is None: m = float(getattr(dcm, 'RescaleSlope', 1.0))
		x = m * dcm.pixel_array + b
		return x
	
	@staticmethod	
	def load( path ):
		volum = Volumetric()

		dicom_files = [pydicom.dcmread(os.path.join(os.path.dirname(path), f)) for f in os.listdir(os.path.dirname(path)) if f.endswith('.dcm')]
		dicom_files.sort(key=lambda x: float(getattr(x, 'SliceLocation', float(getattr(x, 'ImagePositionPatient')[2]))))
		volum.m_volume = np.stack([ParserDICOM.convert_to_HU(file) for file in dicom_files])
		
		for idx, file in enumerate(dicom_files):
			slice_metadata = SliceMetadata()
			slice_metadata.image_position_patient = getattr(file, 'ImagePositionPatient', [0.0, 0.0, idx])
			slice_metadata.pixel_spacing = getattr(file, 'PixelSpacing', [1.0, 1.0])
			
			rows, cols = getattr(file, 'Rows'), getattr(file, 'Columns')
			
			slice_metadata.gantry_detector_tilt = float(getattr(file, 'GantryDetectorTilt', 0.0))
			
			# korekcja polozenia w X i Y jesli zostało podane w pikselach zamiast milimetrach
			if abs(slice_metadata.image_position_patient[0]) >= cols/2 or abs(slice_metadata.image_position_patient[1]) >= rows/2:
				for i in range(2):
					slice_metadata.image_position_patient[i] = slice_metadata.pixel_spacing[i] * slice_metadata.image_position_patient[i]

			# korekcja polozenia w X i Y jesli nie zostało ustawione
			# elif position_image[0] == 0 and position_image[1] == 0:
			# 	for i in range(2):
			# 		position_image[0] = - pixel_spacing[0] * cols/2
			# 		position_image[1] = - pixel_spacing[1] * rows/2


			if slice_metadata.gantry_detector_tilt != 0.0:
				dy = slice_metadata.image_position_patient[2] * tan(slice_metadata.gantry_detector_tilt)
				slice_metadata.image_position_patient[1] = slice_metadata.image_position_patient[1] + dy

			slice_metadata.slice_thickness = getattr(file, 'SliceThickness', 1.0)
			slice_metadata.slice_location = getattr(file, 'SliceLocation', idx)
			
			# print(f"file {idx}: {slice_metadata}")
			volum.metadata.append(slice_metadata)

		volum.m_min = np.min(volum.m_volume)
		volum.m_max = np.max(volum.m_volume)
		# print(f"wart.min = {volum.m_min}, wart.maks = {volum.m_max}")
		volum.m_minDisplWin = volum.m_min
		volum.m_maxDisplWin = volum.m_max

		volum.m_minSlice = 0
		volum.m_maxSlice = volum.m_volume.shape[0]-1

		for filter in volum.m_filters:
			filter[1] = max(filter[1], volum.m_minDisplWin)
			filter[2] = min(filter[2], volum.m_maxDisplWin)

		# self.show_histogram()
		return volum

	@staticmethod	
	def save( obj, path ):
		return False
	
	@staticmethod	
	def inPlugin():
		return False

