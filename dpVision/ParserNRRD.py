from dpVision.Globals import AP
from dpVision.Volumetric import Volumetric, SliceMetadata
from .Parser import Parser
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
			# print(f"file {idx}: {slice_metadata}")
			volum.metadata.append(slice_metadata)

		volum.m_min = np.min(volum.m_volume)
		volum.m_max = np.max(volum.m_volume)
		# print(f"wart.min = {volum.m_min}, wart.maks = {volum.m_max}")
		volum.m_minDisplWin = volum.m_min
		volum.m_maxDisplWin = volum.m_max

		volum.m_minSlice = 0
		volum.m_maxSlice = size[2]-1

		for filter in volum.m_filters:
			filter[1] = volum.m_minDisplWin
			filter[2] = volum.m_maxDisplWin

		return volum

	@staticmethod	
	def save( obj, path ):
		return False
	
	@staticmethod	
	def inPlugin():
		return False

