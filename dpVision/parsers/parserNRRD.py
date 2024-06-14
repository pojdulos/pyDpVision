
from .. import Parser, AP, Volumetric, SliceMetadata

import numpy as np
import os
from PyQt5.QtGui import *
import SimpleITK as sitk
from math import *

class ParserNRRD(Parser):
	descr = 'NRRD datasets'
	load_exts = ['.nrrd'] #,'.dcm']
	#save_exts = ['.dcm']
 
	@staticmethod	
	def load( path ):
		volum = Volumetric()
		image = sitk.ReadImage(path)
		# print(image)
		volum.m_volume = sitk.GetArrayFromImage(image)
		
		origin = image.GetOrigin()
		size = image.GetSize()
		spacing = image.GetSpacing()

		for idx in range(size[2]):
			slice_metadata = SliceMetadata()
			slice_metadata.gantry_detector_tilt = 0.0
			slice_metadata.slice_location = origin[2]+spacing[2]*idx
			slice_metadata.image_position_patient = [origin[0], origin[1], origin[2]+spacing[2]*idx]
			slice_metadata.pixel_spacing = spacing
			slice_metadata.slice_thickness = spacing[2]

			if idx > 0:
				slice_metadata.slice_distance = slice_metadata.slice_location - volum.metadata[idx-1].slice_location
			else:
				slice_metadata.slice_distance = 0.0

			# print(f"file {idx}: {slice_metadata}")
			volum.metadata.append(slice_metadata)

		volum.adjustMinMax()

		for filter in volum.m_filters:
			filter[1] = max(filter[1], volum.m_minDisplWin)
			filter[2] = min(filter[2], volum.m_maxDisplWin)

		return volum

	@staticmethod	
	def save( obj, path ):
		return False
	
	@staticmethod	
	def inPlugin():
		return False

ParserNRRD.regParser()