# -*- coding: utf-8 -*-
"""
Created on Mon Nov 27 12:58:12 2023

@author: pojdulos
"""
from dpVision.Globals import AP
from .Parser import Parser
from .AnnotationSphere import AnnotationSphere
from .Transform import Transform
import numpy as np
import math
import os
from PyQt5.QtGui import *
from PyQt5.QtCore import *


class ParserATMDL(Parser):
	descr = 'ATMDL files'
	load_exts = ['.atmdl']
	#save_exts = ['.atmdl']
	
	@staticmethod	
	def count_lines(path):
		with open(path, 'r') as file:
			return sum(1 for _ in file)

	@staticmethod	
	def load( path ):
		return ParserATMDL().loadATMDL(path)
	
	@staticmethod	
	def save( obj, path ):
		return False
	
	@staticmethod	
	def inPlugin():
		return False
	
	def __init__(self):
		self.atmdlFile = QFile()
		self.buffer = []

	def readWord(self, stream):
		if not len(self.buffer):
			line = stream.readLine()
			if not line:
				return None
			self.buffer = line.split()
		return self.buffer.pop(0)

	def readLine(self, stream):
		if len(self.buffer):
			line = ' '.join(self.buffer)
			self.buffer = []
		else:	
			line = stream.readLine()
		return line

	def skip_comments(self, stream):
		slowo = self.readWord(stream)
		if not slowo:
			return ''
		
		while slowo.strip().startswith('#'):
			print("COMMENT: " + slowo + self.readLine(stream))
			slowo = self.readWord(stream)

		return slowo

	def parseType_string(self, stream):
		return self.readWord(stream)

	def loadShellFile(self, filepath, mainFile, cleanIt=False):
		myPath = filepath

		if not os.path.exists(myPath):
			myPath = os.path.dirname(mainFile)+'/'+myPath
			if not os.path.exists(myPath):
				print('Plik nie istnieje: '+filepath)
				return None

		result = Parser.load(myPath)

		return result #cleanIt?clean_model(result):result;

	def parseObject_shell(self, stream):
		slowo = self.skip_comments(stream)

		print("Rozpoczeto interpretacje obiektu shell")

		if not slowo == '{':
			print("BŁĄD. Oczekiwano znaku { odczytano: "+ slowo)
			return None

		opis = {}
		kids = []

		while not slowo == '}':
			slowo = self.skip_comments(stream)

			if slowo in [ 'label', 'descr', 'file' ]:
				opis[slowo] = self.parseType_string(stream)
			elif slowo == "}":
				print("znaleziono klamre zamykajaca")
			else:
				tmp = self.parseObject(stream, slowo)
				if not tmp is None:
					kids.append(tmp)
				else:
					print("BLAD. Nierozpoznany symbol "+ slowo)
					return None

		obj = None
		if 'file' in opis:
			obj = self.loadShellFile(opis["file"], self.atmdlFile)
			if not obj is None:
				if 'label' in opis:
					obj.setLabel(opis["label"])
				if 'descr' in opis:
					obj.setDescription(opis["descr"])

				for kid in kids:
					self.add_kid(obj, kid)
		print("Zakonczono interpretacje obiektu shell")
		return obj
	
	def parseObject_transformation(self, stream):
		return None
	
	def parseObject_point(self, stream):
		return None

	def parseObject_sphere(self, stream):
		slowo = self.skip_comments(stream)

		if not slowo == '{':
			print("BŁĄD. Oczekiwano znaku { odczytano: "+ slowo)
			return None

		opis = {}
		kids = []

		while not slowo == '}':
			slowo = self.skip_comments(stream)

			if slowo in [ 'label', 'descr' ]:
				opis[slowo] = self.parseType_string(stream)
			elif slowo == "coords":
				opis["coords"] = self.parseType_string(stream)
				#opis["coords"] = parseType_matrix(stream)
			elif slowo == "radius":
				slowo = self.readWord(stream)
				opis["radius"] = slowo
			elif slowo == "color":
				slowo = self.readWord(stream)
				opis["color"] = slowo
			elif slowo == "}":
				print("Poprawnie odczytano sferę")
			else:
				print("BLAD. Nierozpoznany symbol "+ slowo)
				return None

		coords = [0.0, 0.0, 0.0]

		if 'coords' in opis:
			qCoords = opis["coords"].split(",")
			coords = [float(qCoords[0]), float(qCoords[1]), float(qCoords[2])]

		radius = 1.0

		if 'radius' in opis:
			radius = float(opis["radius"])

		obj = AnnotationSphere()
		obj.m_c = coords
		obj.m_r = radius

		if not obj is None:
			obj.m_lats = 32
			obj.m_longs = 32

			if 'color' in opis:
				obj.setColor(txt=opis["color"])
			
			if 'label' in opis:
				obj.setLabel(opis["label"])

			if 'descr' in opis:
				obj.setDescr(opis["descr"])

			return obj
		return None
		
	def parseObject_triangle(self, stream):
		return None
	
	def parseObject_animation(self, stream):
		return None


	def parseObject(self, stream, slowo):
		if slowo in ['shell', 'mesh', 'model']:
			return self.parseObject_shell(stream)
		elif slowo in ['transformation', 'transform', 'trans']:
			return self.parseObject_transformation(stream)
		elif slowo == "point":
			return self.parseObject_point(stream)
		elif slowo == "sphere":
			return self.parseObject_sphere(stream)
		elif slowo == "triangle":
			return self.parseObject_triangle(stream)
		elif slowo in ['animation', 'motion', 'movement']:
			return self.parseObject_animation(stream)
		return None

	def add_kid(self, obj, kid):
		obj.addChild(kid)
		# if kid.hasCategory('Object'):
		# 	obj.addChild(kid)
		# elif kid.hasCategory('Annotation'):
		# 	obj.addAnnotation(kid)

	def loadATMDL(self, path):
		self.atmdlFile.setFileName(path)

		if not self.atmdlFile.open(QIODevice.ReadOnly | QFile.Text):
			print("Can't open file.")
			return None

		stream = QTextStream(self.atmdlFile)
		stream.setCodec("UTF-8")

		root = Transform()

		currentObject = root

		while not stream.atEnd():
			slowo = self.skip_comments(stream)

			tmp = self.parseObject(stream, slowo)
			if not tmp is None:
				self.add_kid(currentObject, tmp)
				pass
			elif not len(slowo.strip()):
				# NEUTRALIZUJE PUSTE ZNAKI NA KONCU PLIKU
				pass
			else:
				print("\033[33mBŁĄD. Nierozpoznany symbol " + slowo + "\033[0m" )
				break

		return root


	