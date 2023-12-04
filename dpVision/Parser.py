# -*- coding: utf-8 -*-
"""
Created on Mon Nov 27 12:58:12 2023

@author: pojdulos
"""
import os

class Parser:
	descr = "Generic parser"
	load_exts = []
	save_exts = []

	parsers = []

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
	def getExtByFileContent(path):
		from PyQt5.QtCore import QFile, QIODevice
		ext = ""
		plik = QFile(path)
		if plik.open(QIODevice.ReadOnly):
			plik.seek(0x80)
			dcm = plik.read(4)
			if dcm.startswith("DICM"):
				ext = ".dcm"
			plik.close()
		return ext

	@staticmethod	
	def load(path):
		fname, fext = os.path.splitext(path)
		if not len(fext):
			fext = Parser.getExtByFileContent(path)
		for p in Parser.parsers:
			if p.canLoadExt(fext):
				return p.load(path)
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
	def canLoadExt(cls, ext):
		return ext in cls.load_exts

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

