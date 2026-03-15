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

	@classmethod
	def regParser(cls):
		if not cls in Parser.parsers:
			print(f"registering parser: {cls.__name__}")
			Parser.parsers.append(cls)
		else:
			print(f"parser: {cls.__name__} already registered")

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
	def get_instance(path):
		for p in tuple(Parser.parsers):
			if p.canLoadExt(path=path):
				if p.is_not_static():
					return p(path)
			elif p.check_by_content(path=path):
				if p.is_not_static():
					return p(path)

		print(f"File format is not supported yet: {path}")
		return None

	@staticmethod	
	def load(path):
		for p in tuple(Parser.parsers):
			if p.canLoadExt(path=path) or p.check_by_content(path=path):
				obj = p.load(path)
				obj.label = os.path.basename(path)
				return obj

		print(f"File format is not supported yet: {path}")
		return None
	
	@staticmethod	
	def save(obj, path):
		fname, fext = os.path.splitext(path)
		fext = fext.lower()
		for p in Parser.parsers:
			if p.canSaveExt(fext):
				return p.save(obj, path)
		return False

	@staticmethod
	def getSaveParsers(obj):
		result = []
		for parser in Parser.parsers:
			if parser.canSaveObject(obj):
				result.append(parser)
		return result

	@staticmethod
	def getSaveExts(obj):
		filters = []
		for parser in Parser.getSaveParsers(obj):
			if len(parser.save_exts):
				patterns = ' '.join([f'*{ext}' for ext in parser.save_exts])
				filters.append(f"{parser.descr} ({patterns})")
		return ';;'.join(filters)
	
	@staticmethod	
	def inPlugin():
		return False
	
	###### CLASS METHODS #####
	@classmethod
	def	is_not_static(cls):
		return False

	@classmethod
	def canLoadExt(cls, path=None):
		if path:
			return path.endswith(tuple(cls.load_exts))
		return False

	@classmethod
	def canSaveExt(cls, ext):
		return ext in cls.save_exts

	@classmethod
	def canSaveObject(cls, obj):
		return False

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
