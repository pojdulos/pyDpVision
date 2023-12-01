# -*- coding: utf-8 -*-
"""
Created on Mon Nov 27 12:58:12 2023

@author: pojdulos
"""

class Parser:
	m_descr = "Generic parser"
	m_load_exts = []
	m_save_exts = []
	
	@staticmethod	
	def load( path ):
		return None
	
	@staticmethod	
	def save( obj, path ):
		return False
	
	@staticmethod	
	def inPlugin():
		return False
	