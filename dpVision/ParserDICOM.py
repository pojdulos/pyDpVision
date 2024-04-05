from dpVision.Globals import AP
from dpVision.Volumetric import Volumetric
from .Parser import Parser
import numpy as np
import math
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
	def load( path ):
		volum = Volumetric()
		volum.read_as_directory(os.path.dirname(path))
		return volum

	@staticmethod	
	def save( obj, path ):
		return False
	
	@staticmethod	
	def inPlugin():
		return False

