# -*- coding: utf-8 -*-
"""
Created on Sun Nov 26 19:51:28 2023

@author: darek
"""

class Sphere:
	def __init__(self):
		self.position = [0.0,0.0,0.0]
		self.radius = 1.0
	
	@property
	def position(self):
		return self._position
	
	@position.setter
	def position(self, position):
		self._position = position

	@property
	def radius(self):
		return self._radius
	
	@radius.setter
	def radius(self, radius):
		self._radius = radius
	