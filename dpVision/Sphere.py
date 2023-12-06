# -*- coding: utf-8 -*-
"""
Created on Sun Nov 26 19:51:28 2023

@author: darek
"""

class Sphere:
	def __init__(self):
		self.m_c = [2.0,4.0,2.0]
		self.m_r = 3.0
	
	def setRadius(self, r):
		self.m_r = r
	
	def getRadius(self):
		return self.m_r
	
	def setCenter(self, point):
		self.m_c = point

	def getCenter(self):
		return self.m_c
	
	