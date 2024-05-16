from dpVision.Globals import AP
from dpVision.Volumetric import Volumetric
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
		print(image)
		volum.m_volume = sitk.GetArrayFromImage(image)
		
		spacing = image.GetSpacing()
		size = image.GetSize()
		origin = image.GetOrigin()
		# keys = image.GetMetaDataKeys()
		# for key in keys:
		# 	try:
		# 		value = image.GetMetaData(key)
		# 		print(f'{key}: {value}')
		# 	except RuntimeError: # W przypadku braku klucza
		# 		continue

		for idx in range(size[2]):
			gantra = 0.0
			position_image = [origin[0], origin[1], origin[2]+spacing[2]*idx]

			mydict = {
				'ImagePositionPatient': position_image,
				'SliceLocation': position_image[2],
				'PixelSpacing': spacing,
				'SliceThickness': spacing[2],
				'GantryDetectorTilt': gantra
			}
			
			volum.metadata.append(mydict)

		volum.m_minDisplWin = volum.m_min = np.min(volum.m_volume)
		volum.m_maxDisplWin = volum.m_max = np.max(volum.m_volume)
		print(f"wart.min = {volum.m_min}, wart.maks = {volum.m_max}")

		volum.m_minSlice = 0
		volum.m_maxSlice = volum.m_volume.shape[0]-1

		return volum

	@staticmethod	
	def save( obj, path ):
		return False
	
	@staticmethod	
	def inPlugin():
		return False

