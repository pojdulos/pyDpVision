# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 13:15:53 2023

@author: darek
"""

from PyQt5.QtGui import *
from .baseObject import BaseObject

class Annotation(BaseObject):
	def __init__(self, parent=None):
		super( Annotation, self ).__init__( parent )
		self.m_color = QColor(0,0,255,102)
		self.m_selcolor = QColor(255,0,0,102)

	def setColor(self, name=None, r=0, g=0, b=255, a=102):
		if name:
			kolor = QColor(name)
			if kolor.isValid():
				self.m_color = kolor
				return
		if r and g and b:
			kolor = QColor(r, g, b, a)
			if kolor.isValid():
				self.m_color = kolor
		return

	def getColor(self):
		return self.m_color
	
	def setSelColor(self, name=None, r=255, g=0, b=0, a=102):
		if name:
			kolor = QColor(name)
			if kolor.isValid():
				self.m_selcolor = kolor
				return
		if r and g and b:
			kolor = QColor(r, g, b, a)
			if kolor.isValid():
				self.m_selcolor = kolor
		return

	def getSelColor(self):
		return self.m_selcolor
	