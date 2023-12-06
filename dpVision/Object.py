# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 13:15:53 2023

@author: darek
"""

from .BaseObject import BaseObject

class Object(BaseObject):
	def __init__(self, parent=None):
		super( Object, self ).__init__( parent )
		self.m_data = []

	def children(self):
		return self.m_data

	def addChild(self, d):
		if d is None or not issubclass(type(d), BaseObject):
			return False

		d.setParent( self )
		self.m_data.append( d )

		return True

	def removeChild(self, child=None):
		if child is None and len(self.m_data):
			self.m_data.remove(self.m_data[0])
		elif child in self.m_data:
			self.m_data.remove(child)

	def renderKids(self):
		for child in self.m_data:
			child.render()
			
	
	