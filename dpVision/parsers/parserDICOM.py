
from .. import Parser, AP, Volumetric, SliceMetadata

import numpy as np
from math import *
import os
from PyQt5.QtGui import *
import pydicom


class ParserDICOM(Parser):
	descr = 'DICOM files'
	load_exts = ['.dcm']#,'.dcm.ptl']
	#save_exts = ['.dcm']

	@staticmethod	
	def convert_to_HU(dcm, b=None, m=None):
		print(dcm.file_meta)
		# dcm.file_meta.TransferSyntaxUID = pydicom.uid.ImplicitVRLittleEndian 
		if b is None: b = float(getattr(dcm, 'RescaleIntercept', 0.0))
		if m is None: m = float(getattr(dcm, 'RescaleSlope', 1.0))
		x = m * dcm.pixel_array + b
		return x
	
	@staticmethod	
	def read_dir( current_dir, current_ext ):
		dicom_files = []
		for f in os.listdir(current_dir):
			if not current_ext or f.endswith(current_ext):
				try:
					# Próba odczytania pliku DICOM
					#dicom_file = pydicom.dcmread(os.path.join(current_dir, f))
					dicom_file = pydicom.read_file(os.path.join(current_dir, f), force=True)
					dicom_files.append(dicom_file)
				except Exception as e:
					# Jeśli wystąpi błąd, plik zostanie pominięty
					print(f"Plik {f} jest uszkodzony lub nie można go odczytać: {e}")
		return dicom_files

	@staticmethod	
	def load( path ):
		volum = Volumetric()

		current_ext = next((ext for ext in ParserDICOM.load_exts if path.endswith(ext)), None)
		current_dir = os.path.dirname(path)
		
		# dicom_files = [pydicom.dcmread(os.path.join(current_dir, f)) for f in os.listdir(current_dir) if f.endswith(current_ext)]
		dicom_files = ParserDICOM.read_dir(current_dir, current_ext)

		dicom_files.sort(key=lambda x: float(getattr(x, 'SliceLocation', float(getattr(x, 'ImagePositionPatient')[2]))))
		
		# volum.m_dicom_files = dicom_files
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
			
			if idx > 0:
				slice_metadata.slice_distance = slice_metadata.slice_location - volum.metadata[idx-1].slice_location
			else:
				slice_metadata.slice_distance = 0.0

			# print(f"file {idx}: {slice_metadata}")
			volum.metadata.append(slice_metadata)

		volum.adjustMinMax()

		volum.m_minSlice = 0
		volum.m_maxSlice = volum.m_volume.shape[0]-1

		for filter in volum.m_filters:
			filter[1] = max(filter[1], volum.m_minDisplWin)
			filter[2] = min(filter[2], volum.m_maxDisplWin)

		# self.show_histogram()
		# volum.test_gauss()
		
		return volum

	@staticmethod	
	def save( obj, path ):
		return False
	
	@staticmethod	
	def inPlugin():
		return False

	@staticmethod	
	def check_by_content(path):
		from PyQt5.QtCore import QFile, QIODevice
		plik = QFile(path)
		if plik.open(QIODevice.ReadOnly):
			plik.seek(0x80)
			dcm = plik.read(4)
			if dcm.decode('ascii', errors='ignore').upper().startswith("DICM"):
				plik.close()
				return True
		return False

ParserDICOM.regParser()
