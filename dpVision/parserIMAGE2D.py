from .globals import AP
from .image import Image
from .parser import Parser
from PyQt5.QtGui import *

class ParserIMAGE2D(Parser):
	descr = '2D Image files'
	load_exts = ['.png','.jpg','.bmp']
	#save_exts = ['.dcm']
 
	@staticmethod	
	def load( path ):
		img = Image(path = path)
		return img

	@staticmethod	
	def save( obj, path ):
		return False
	
	@staticmethod	
	def inPlugin():
		return False

