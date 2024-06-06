# -*- coding: utf-8 -*-
"""
Created on Mon Nov 27 12:58:12 2023

@author: pojdulos
"""
from PyQt5.QtCore import *
import os

class Parser(QObject):
	descr = "Generic parser"
	load_exts = []
	save_exts = []

	parsers = []

	def __init__(self):
		super( Parser, self ).__init__()
		
	@staticmethod
	def regParser( t ):
		if not t in Parser.parsers:
			Parser.parsers.append(t)

	@staticmethod
	def unregParser( t ):
		if t in Parser.parsers:
			Parser.parsers.remove(t)

	@staticmethod
	def getLoadExts():
		ext = "All (*.*)"
		for parser in Parser.parsers:
			ext = parser.loadExts(ext)
		return ext

	@staticmethod	
	def check_by_content(path):
		return False

	@staticmethod	
	def load(path):
		for p in tuple(Parser.parsers):
			if p.canLoadExt(path=path):
				return p.load(path)
			elif p.check_by_content(path=path):
				return p.load(path)

		print(f"File format is not supported yet: {path}")
		return None
	
	@staticmethod	
	def save(obj, path):
		fname, fext = os.path.splitext(path)
		for p in Parser.parsers:
			if p.canSaveExt(fext):
				return p.save(obj, path)
		return False
	
	@staticmethod	
	def inPlugin():
		return False
	
	###### CLASS METHODS #####

	@classmethod
	def canLoadExt(cls, path=None):
		if path:
			return path.endswith(tuple(cls.load_exts))
		return False

	@classmethod
	def canSaveExt(cls, ext):
		return ext in cls.save_exts

	@classmethod
	def loadExts(cls, ext):
		if len(cls.load_exts):
			if len(ext):
				ext = ext + ";;"
			ext = ext + cls.descr + " ("
			for e in cls.load_exts:
				ext = ext + "*" + e + ";"

			ext = ext[:-1] + ')'
		return ext

