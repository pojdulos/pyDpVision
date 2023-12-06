# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 12:31:41 2023

@author: darek
"""

from PyQt5.QtCore import QObject
import OpenGL.GL as gl

class Workspace(QObject):
	def __init__(self):
		super( Workspace, self ).__init__()
		self.m_data = []
		self.m_checked = []
		self.m_currentObject = None
		
	def render(self):
		for obj in self.m_data:
			gl.glPushMatrix()
	
			if not obj is None:
				obj.render()
			
			gl.glPopMatrix()
	
