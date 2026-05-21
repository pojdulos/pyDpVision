
from .. import Parser, AP, Volumetric, SliceMetadata

import numpy as np
from math import *
import os
from contextlib import contextmanager
from PyQt5.QtGui import *
import pydicom


class ParserDICOM(Parser):
	descr = 'DICOM files'
	load_exts = ['.dcm']#,'.dcm.ptl']
	#save_exts = ['.dcm']

	@staticmethod
	@contextmanager
	def _relaxed_pydicom_validation():
		"""Temporarily relax pydicom validation for imperfect clinical exports."""
		prev_mode = pydicom.config.settings.reading_validation_mode
		try:
			pydicom.config.settings.reading_validation_mode = pydicom.config.IGNORE
			with pydicom.config.disable_value_validation():
				yield
		finally:
			pydicom.config.settings.reading_validation_mode = prev_mode

	@staticmethod
	def _get_image_orientation_normal(dcm):
		"""Return the normalized slice normal derived from ImageOrientationPatient."""
		image_orientation = getattr(dcm, 'ImageOrientationPatient', None)
		if image_orientation is None or len(image_orientation) < 6:
			return None

		try:
			row_vector = np.array([float(v) for v in image_orientation[:3]], dtype=np.float64)
			column_vector = np.array([float(v) for v in image_orientation[3:6]], dtype=np.float64)
		except Exception:
			return None

		normal_vector = np.cross(row_vector, column_vector)
		norm = np.linalg.norm(normal_vector)
		if norm <= 0.0:
			return None

		return normal_vector / norm

	@staticmethod
	def _get_image_orientation_axes(dcm):
		"""Return normalized volume X/Y axes derived from ImageOrientationPatient."""
		image_orientation = getattr(dcm, 'ImageOrientationPatient', None)
		if image_orientation is None or len(image_orientation) < 6:
			return None, None

		try:
			axis_x = np.array([float(v) for v in image_orientation[:3]], dtype=np.float64)
			axis_y = np.array([float(v) for v in image_orientation[3:6]], dtype=np.float64)
		except Exception:
			return None, None

		norm_x = np.linalg.norm(axis_x)
		norm_y = np.linalg.norm(axis_y)
		if norm_x <= 0.0 or norm_y <= 0.0:
			return None, None

		return axis_x / norm_x, axis_y / norm_y

	@staticmethod
	def _get_slice_position(dcm, fallback_idx=0.0):
		"""Return the physical slice position in millimeters."""
		image_position = getattr(dcm, 'ImagePositionPatient', None)
		if image_position is not None and len(image_position) >= 3:
			try:
				image_position = np.array([float(v) for v in image_position[:3]], dtype=np.float64)
				normal_vector = ParserDICOM._get_image_orientation_normal(dcm)
				if normal_vector is not None:
					return float(np.dot(image_position, normal_vector))
				return float(image_position[2])
			except Exception:
				pass

		slice_location = getattr(dcm, 'SliceLocation', None)
		if slice_location not in (None, ''):
			try:
				return float(slice_location)
			except Exception:
				pass

		instance_number = getattr(dcm, 'InstanceNumber', None)
		if instance_number not in (None, ''):
			try:
				return float(instance_number)
			except Exception:
				pass

		return float(fallback_idx)

	@staticmethod
	def _slice_sort_key(dcm, fallback_idx=0.0):
		"""Return a stable sort key for ordering slices inside one series."""
		return ParserDICOM._get_slice_position(dcm, fallback_idx)

	@staticmethod
	def _get_slice_thickness(dcm, default_value=1.0):
		"""Return physical slice thickness when it is available in the dataset."""
		for attr_name in ('SliceThickness', 'SpacingBetweenSlices'):
			attr_value = getattr(dcm, attr_name, None)
			if attr_value not in (None, ''):
				try:
					return abs(float(attr_value))
				except Exception:
					pass
		return float(default_value)

	@staticmethod
	def _get_slice_distance(current_dcm, previous_dcm):
		"""Return spacing between neighboring slices in millimeters."""
		if previous_dcm is not None:
			current_position = ParserDICOM._get_slice_position(current_dcm)
			previous_position = ParserDICOM._get_slice_position(previous_dcm)
			slice_distance = abs(current_position - previous_position)
			if slice_distance > 0.0:
				return slice_distance

		return ParserDICOM._get_slice_thickness(current_dcm)
	
	@staticmethod	
	def convert_to_HU(dcm, b=None, m=None):
		"""Convert raw pixel data using DICOM rescale slope and intercept."""
		if b is None: b = float(getattr(dcm, 'RescaleIntercept', 0.0))
		if m is None: m = float(getattr(dcm, 'RescaleSlope', 1.0))
		with ParserDICOM._relaxed_pydicom_validation():
			x = m * dcm.pixel_array + b
		return x
	
	@staticmethod	
	def read_dir(current_dir, current_ext, series_uid=None):
		"""Read one directory of DICOM files and optionally keep only the selected series."""
		dicom_files = []
		for f in os.listdir(current_dir):
			if not current_ext or f.endswith(current_ext):
				try:
					# Keep only files that belong to the selected series when the folder is mixed.
					with ParserDICOM._relaxed_pydicom_validation():
						dicom_file = pydicom.dcmread(os.path.join(current_dir, f), force=True)
					if series_uid is not None and getattr(dicom_file, 'SeriesInstanceUID', None) != series_uid:
						continue
					dicom_files.append(dicom_file)
				except Exception as e:
					# Skip unreadable files instead of aborting the whole import.
					print(f"Plik {f} jest uszkodzony lub nie można go odczytać: {e}")
		return dicom_files

	@staticmethod	
	def load(path):
		"""Load a DICOM series into the internal volumetric structure."""
		volum = Volumetric()

		current_ext = next((ext for ext in ParserDICOM.load_exts if path.endswith(ext)), None)
		current_dir = os.path.dirname(path)
		with ParserDICOM._relaxed_pydicom_validation():
			reference_file = pydicom.dcmread(path, stop_before_pixels=True, force=True)
		
		dicom_files = ParserDICOM.read_dir(
			current_dir,
			current_ext,
			series_uid=getattr(reference_file, 'SeriesInstanceUID', None),
		)

		dicom_files.sort(key=lambda x: ParserDICOM._slice_sort_key(x))
		
		# volum.m_dicom_files = dicom_files
		volum.m_volume = np.stack([ParserDICOM.convert_to_HU(file) for file in dicom_files])
		
		volum.shape = volum.m_volume.shape

		for idx, file in enumerate(dicom_files):
			slice_metadata = SliceMetadata()
			slice_metadata.image_position_patient = [float(x) for x in getattr(file, 'ImagePositionPatient', [0.0, 0.0, idx])]
			raw_pixel_spacing = [float(x) for x in getattr(file, 'PixelSpacing', [1.0, 1.0])]
			slice_metadata.pixel_spacing = raw_pixel_spacing
			
			rows, cols = getattr(file, 'Rows'), getattr(file, 'Columns')
			axis_x, axis_y = ParserDICOM._get_image_orientation_axes(file)
			if axis_x is not None:
				slice_metadata.axis_x = axis_x.tolist()
			if axis_y is not None:
				slice_metadata.axis_y = axis_y.tolist()
			
			slice_metadata.gantry_detector_tilt = float(getattr(file, 'GantryDetectorTilt', 0.0))
			
			# Correct X/Y only when the file likely stores pixel indices instead of millimeters.
			if abs(slice_metadata.image_position_patient[0]) >= cols/2 or abs(slice_metadata.image_position_patient[1]) >= rows/2:
				for i in range(2):
					slice_metadata.image_position_patient[i] = slice_metadata.pixel_spacing[i] * slice_metadata.image_position_patient[i]

			if slice_metadata.gantry_detector_tilt != 0.0:
				slice_tilt_radians = radians(slice_metadata.gantry_detector_tilt)
				dy = slice_metadata.image_position_patient[2] * tan(slice_tilt_radians)
				slice_metadata.image_position_patient[1] = slice_metadata.image_position_patient[1] + dy

			slice_metadata.slice_thickness = ParserDICOM._get_slice_thickness(file)
			slice_metadata.slice_location = ParserDICOM._get_slice_position(file, idx)
			
			if idx > 0:
				slice_metadata.slice_distance = ParserDICOM._get_slice_distance(file, dicom_files[idx-1])
			else:
				slice_metadata.slice_distance = 0.0

			normal_vector = ParserDICOM._get_image_orientation_normal(file)
			if normal_vector is not None:
				slice_metadata.axis_z = normal_vector.tolist()

			column_spacing = raw_pixel_spacing[1] if len(raw_pixel_spacing) > 1 else raw_pixel_spacing[0]
			row_spacing = raw_pixel_spacing[0] if len(raw_pixel_spacing) > 0 else 1.0
			slice_spacing = slice_metadata.slice_distance if slice_metadata.slice_distance > 0.0 else slice_metadata.slice_thickness
			slice_metadata.voxel_spacing = [float(column_spacing), float(row_spacing), float(slice_spacing)]

			# print(f"file {idx}: {slice_metadata}")
			volum.metadata.append(slice_metadata)

		volum.adjustMinMax()

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
