# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 13:15:53 2023

@author: darek
"""

from PyQt5.QtGui import *
from .BaseObject import BaseObject

class Annotation(BaseObject):
	def __init__(self, parent=None):
		super( Annotation, self ).__init__( parent )
		self.m_color = QColor(0,0,255,102)
		self.m_selcolor = QColor(255,0,0,102)

	def setColor(self, txt=None, r=255, g=255, b=255, a=255):
		if not hex is None:
			self.m_color = QColor(txt)
		else:
			self.m_color = QColor(r, g, b, a)

	def getColor(self):
		return self.m_color
	
	def setSelColor(self, r, g, b, a=255):
		self.m_selcolor = QColor(r, g, b, a)

	def getSelColor(self):
		return self.m_selcolor
	