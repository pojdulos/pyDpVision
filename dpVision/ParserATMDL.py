# -*- coding: utf-8 -*-
"""
Created on Mon Nov 27 12:58:12 2023

@author: pojdulos
"""
from dpVision.AnnotationPoint import AnnotationPoint
from dpVision.AnnotationTriangle import AnnotationTriangle
from dpVision.Motion import Motion
from .Parser import Parser
from .AnnotationSphere import AnnotationSphere
from .Transform import Transform
import os
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import re

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
		self.atmdlFile = ''

	def readChar(self, stream):
		return stream.read(1) or None
	def readWord(self, stream):
		znak = self.readChar(stream)
		while znak and znak.isspace():
			znak = self.readChar(stream)

		if znak is None:
			return None, None
			
		# jestem pewien, że znak nie jest None ani nie jest spacją
		# dlatego pętla wykona sie co najmniej raz
		slowo = '' 
		while znak and not znak.isspace():
			slowo = slowo + znak
			znak = self.readChar(stream)
			
		return slowo, znak
	def readLine(self, stream):
		return stream.readline() or None
	def skip_comments(self, stream):
		slowo, znak = self.readWord(stream)

		if slowo is None:
			return None
		
		while slowo.startswith('#'):
			komentarz = 'Komentarz: ' + slowo
			if znak:
				if znak not in ['\n','\r']:
					reszta_linii = self.readLine(stream) or ''
					komentarz += znak + reszta_linii
				else:
					komentarz += znak
				slowo, znak = self.readWord(stream)
				print(komentarz)
			else:
				print(komentarz)
				return None
		return slowo
	def parseType_string(self, stream):
		def readQuotedString(stream, slowo, znak):
			if slowo.endswith('"'):
				return slowo[1:-1]
			
			while znak:
				if znak in ['\n', '\r']:
					print("UWAGA: Napotkano koniec linii bez zamknięcia cudzysłowu")
					return slowo[1:]

				if znak == '"':
					print("Poprawnie domknięto cudzysłów")
					return slowo[1:]

				slowo = slowo + znak
				znak = self.readChar(stream) # None gdy koniec pliku

			if znak is None:
				print("Osiągnięto koniec pliku podczas parsowania ciągu")
				return slowo[1:]

		def readBracedString(stream, slowo, znak):
			if slowo.endswith('}'):
				return slowo[1:-1]
			
			while znak:
				if znak == '}':
					print("Poprawnie domknięto klamry")
					return slowo[1:]

				slowo = slowo + znak
				znak = self.readChar(stream) # None gdy koniec pliku

			if znak is None:
				print("Osiągnięto koniec pliku podczas parsowania ciągu")
				return slowo[1:]


		# slowo lub znak mogą przyjąć wartość None gdy koniec pliku
		slowo, znak = self.readWord(stream)

		if slowo is None:
			print("Osiągnięto koniec pliku podczas parsowania ciągu")
			return None

		if znak is None:
			print("Osiągnięto koniec pliku podczas parsowania ciągu")
			return slowo

		if slowo.startswith('"'):
			return readQuotedString(stream, slowo, znak)
		
		elif slowo.startswith('{'):
			return readBracedString(stream, slowo, znak)

		return slowo
	def parseType_matrix(self, stream):
		tekst, znak = self.readWord(stream)
		if tekst is None:
			print("Osiągnięto koniec pliku podczas parsowania macierzy")
			return None

		if znak is None:
			print("Osiągnięto koniec pliku podczas parsowania macierzy")
			return tekst

		if tekst.startswith('['):
			znaki = [tekst]
			while znak:
				if znak == ']':
					print("Poprawnie domknięto nawiasy")
					znaki.append(znak)
					break
				else:	
					znaki.append(znak)
					znak = self.readChar(stream)

			if znak is None:
				print("BŁĄD: Oczekiwano zamknięcia nawiasu, ale osiągnięto koniec pliku podczas parsowania macierzy")
				tekst = ''.join(znaki)
				tekst = tekst[1:]

			tekst = ''.join(znaki)
			tekst = tekst[1:-1]

		tekst = re.sub(r"[\s,;]+", ",", tekst).strip(',')

		print("Odczytano macierz: [" + tekst +"]")
		return tekst

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

		if slowo is None:
			print("Osiągnięto koniec pliku podczas parsowania obiektu 'shell'")
			return None

		print("Rozpoczeto parsowanie obiektu 'shell'")

		if not slowo == '{':
			print("BŁĄD. Oczekiwano znaku { odczytano: "+ slowo)
			return None

		opis = {}
		kids = []

		while not slowo == '}':
			slowo = self.skip_comments(stream)

			if slowo is None:
				print("Osiągnięto koniec pliku podczas parsowania obiektu 'shell'")
				return None

			elif slowo in [ 'label', 'descr', 'file' ]:
				result = self.parseType_string(stream)
				if result:
					opis[slowo] = result
			elif slowo == "}":
				print("Znaleziono klamre zamykajacą obiekt 'shell'")
			else:
				tmp = self.parseObject(stream, slowo)
				if not tmp is None:
					kids.append(tmp)
				else:
					print("BLAD. W czasie parsowania obiektu 'shell' znaleziono nierozpoznany symbol: "+ slowo)
					return None

		obj = None
		if 'file' in opis:
			obj = self.loadShellFile(opis["file"], self.atmdlFile)
			if obj is not None:
				if 'label' in opis:
					obj.setLabel(opis["label"])
				if 'descr' in opis:
					obj.setDescription(opis["descr"])

				for kid in kids:
					self.add_kid(obj, kid)
				
				print("Zakonczono parsowanie obiektu 'shell'")
		return obj
	
	def parseObject_transformation(self, stream):
		slowo = self.skip_comments(stream)

		if slowo is None:
			print("Osiągnięto koniec pliku podczas parsowania obiektu 'transformation'")
			return None

		elif slowo != "{":
			print("BŁĄD. Oczekiwano znaku { odczytano: "+slowo )
			return None

		opis = {}
		kids = []

		frameTransformation = Transform()
		isTransformDefined = False

		while slowo != "}":
			slowo = self.skip_comments(stream)

			if slowo is None:
				print("Osiągnięto koniec pliku podczas parsowania obiektu 'transformation'")
				return None
			elif slowo == "}":
				print("Znaleziono klamrę zamykająca obiekt 'transformation'")
			elif slowo in {'label', 'descr'}:
				tekst = self.parseType_string(stream)
				if tekst:
					opis[slowo] = tekst
			elif slowo == "matrix":
				tekst = self.parseType_matrix(stream)
				if tekst:
					opis["matrix"] = tekst
			elif slowo == "rotation":
				tR = self.parseProperty_rotation(stream)
				frameTransformation.matrix = tR.matrix * frameTransformation.matrix
				isTransformDefined = True
			elif slowo == "translation":
				tT = self.parseProperty_translation(stream)
				frameTransformation.matrix = tT.matrix * frameTransformation.matrix
				isTransformDefined = True
			else:
				tmp = self.parseObject(stream, slowo)
				if tmp:
					kids.append(tmp)
				else:
					print("BŁĄD. Nierozpoznany symbol "+ slowo)
					#return None


		obj = Transform()
		if obj is not None:
			if 'label' in opis:
				obj.setLabel(opis["label"])
			
			if 'descr' in opis:
				obj.setDescription(opis["descr"])

			if 'matrix' in opis:
				frameTransformation.fromRowMatrixStr(opis["matrix"], ",")
				isTransformDefined = True

			if isTransformDefined:
				obj.matrix = frameTransformation.matrix

			for kid in kids:
				self.add_kid(obj, kid)
		return obj

	def parseObject_point(self, stream):
		slowo = self.skip_comments(stream)

		if slowo is None:
			print("Osiągnięto koniec pliku podczas parsowania obiektu 'point'")
			return None

		if not slowo == '{':
			print("BŁĄD. Oczekiwano znaku { odczytano: "+ slowo)
			return None

		opis = {}
		kids = []

		while not slowo == '}':
			slowo = self.skip_comments(stream)

			if slowo is None:
				print("Osiągnięto koniec pliku podczas parsowania obiektu 'point'")
				return None
			elif slowo == "}":
				print("Znaleziono klamrę zamykającą obiekt 'point'")
			elif slowo in [ 'label', 'descr' ]:
				tekst = self.parseType_string(stream)
				if tekst:
					opis[slowo] = tekst
			elif slowo == "coords":
				tekst = self.parseType_matrix(stream)
				if tekst:
					opis["coords"] = tekst
			elif slowo in {'vector', 'normal'}:
				tekst = self.parseType_matrix(stream)
				if tekst:
					opis['normal'] = tekst
			elif slowo == "color":
				slowo, _ = self.readWord(stream)
				if slowo:
					if slowo[0] != '#':
						slowo = '#'+slowo
					opis["color"] = slowo
			else:
				print("BLAD1. Nierozpoznany symbol "+ slowo)
				return None

		if 'coords' in opis:
			qCoords = opis["coords"].split(",")
			coords = [float(qCoords[0]), float(qCoords[1]), float(qCoords[2])]

		obj = AnnotationPoint()

		if obj:
			obj.setPoint(coords)
			if 'normal' in opis:
				qNorm = opis['normal'].split(",")
				normal = [float(qNorm[0]), float(qNorm[1]), float(qNorm[2])]
				obj.setVector(normal)

			if 'color' in opis:
				obj.setColor(txt=opis["color"])
			
			if 'label' in opis:
				obj.setLabel(opis["label"])

			if 'descr' in opis:
				obj.setDescr(opis["descr"])

			return obj
		return None

	def parseObject_sphere(self, stream):
		slowo = self.skip_comments(stream)

		if slowo is None:
			print("Osiągnięto koniec pliku podczas parsowania obiektu 'sphere'")
			return None

		if not slowo == '{':
			print("BŁĄD. Oczekiwano znaku { odczytano: "+ slowo)
			return None

		opis = {}
		kids = []

		while not slowo == '}':
			slowo = self.skip_comments(stream)

			if slowo is None:
				print("Osiągnięto koniec pliku podczas parsowania obiektu 'sphere'")
				return None
			elif slowo == "}":
				print("Znaleziono klamrę zamykającą obiekt 'sphere'")
			elif slowo in [ 'label', 'descr' ]:
				tekst = self.parseType_string(stream)
				if tekst:
					opis[slowo] = tekst
			elif slowo == "coords":
				tekst = self.parseType_matrix(stream)
				if tekst:
					opis["coords"] = tekst
			elif slowo == "radius":
				slowo, _ = self.readWord(stream)
				if slowo:
					opis["radius"] = slowo
			elif slowo == "color":
				slowo, _ = self.readWord(stream)
				if slowo:
					if slowo[0] != '#':
						slowo = '#'+slowo
					opis["color"] = slowo
			else:
				print("BLAD1. Nierozpoznany symbol "+ slowo)
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
		slowo = self.skip_comments(stream)

		if slowo is None:
			print("Osiągnięto koniec pliku podczas parsowania obiektu 'triangle'")
			return None

		if not slowo == '{':
			print("BŁĄD. Oczekiwano znaku { odczytano: "+ slowo)
			return None

		opis = {}
		kids = []

		while not slowo == '}':
			slowo = self.skip_comments(stream)

			if slowo is None:
				print("Osiągnięto koniec pliku podczas parsowania obiektu 'triangle'")
				return None
			elif slowo == "}":
				print("Znaleziono klamrę zamykającą obiekt 'triangle'")
			elif slowo in [ 'label', 'descr' ]:
				tekst = self.parseType_string(stream)
				if tekst:
					opis[slowo] = tekst
			elif slowo in {'coordsA', 'coordsB', 'coordsC' }:
				tekst = self.parseType_matrix(stream)
				if tekst:
					opis[slowo] = tekst
			elif slowo == "color":
				slowo, _ = self.readWord(stream)
				if slowo:
					if slowo[0] != '#':
						slowo = '#'+slowo
					opis["color"] = slowo
			else:
				print("BLAD1. Nierozpoznany symbol "+ slowo)
				return None

		if 'coordsA' in opis and 'coordsB' in opis and 'coordsC' in opis:
			qCoordsA = opis["coordsA"].split(",")
			qCoordsB = opis["coordsB"].split(",")
			qCoordsC = opis["coordsC"].split(",")
			
			vA = [float(qCoordsA[0]), float(qCoordsA[1]), float(qCoordsA[2])]
			vB = [float(qCoordsB[0]), float(qCoordsB[1]), float(qCoordsB[2])]
			vC = [float(qCoordsC[0]), float(qCoordsC[1]), float(qCoordsC[2])]

		obj = AnnotationTriangle(vA, vB, vC)
		if obj:
			if 'color' in opis:
				obj.setColor(txt=opis["color"])
			if 'label' in opis:
				obj.setLabel(opis["label"])
			if 'descr' in opis:
				obj.setDescr(opis["descr"])
			return obj
		return None
	
	def parseProperty_frame(self, stream):
		slowo = self.skip_comments(stream)

		if slowo is None:
			print("Osiągnięto koniec pliku podczas parsowania właściwości 'frame'")
			return Motion.FrameVal()

		elif slowo != "{":
			print("BŁĄD. Oczekiwano znaku { odczytano: "+slowo )
			return Motion.FrameVal()

		opis = {}

		frameTransformation = Transform()
		isTransformDefined = False

		while slowo != "}":
			slowo = self.skip_comments(stream)

			if slowo is None:
				print("Osiągnięto koniec pliku podczas parsowania włąściwości 'frame'")
				return None
			elif slowo == "}":
				print("Znaleziono klamrę zamykająca właściwość 'frame'")
			elif slowo in {'label', 'descr'}:
				tekst = self.parseType_string(stream)
				if tekst:
					opis[slowo] = tekst
			elif slowo == "matrix":
				tekst = self.parseType_matrix(stream)
				if tekst:
					opis["matrix"] = tekst
			elif slowo == "rotation":
				tR = self.parseProperty_rotation(stream)
				frameTransformation.matrix = tR.matrix * frameTransformation.matrix
				isTransformDefined = True
			elif slowo == "translation":
				tT = self.parseProperty_translation(stream)
				frameTransformation.matrix = tT.matrix * frameTransformation.matrix
				isTransformDefined = True
			elif slowo == "order":
				slowo, _ = self.readWord(stream)
				if slowo:
					opis["order"] = slowo
			elif slowo in { "delay",  "time" }:
				slowo, _ = self.readWord(stream)
				if slowo:
					opis["time"] = slowo
			else:
				print("BŁĄD. Nierozpoznany symbol "+ slowo)

		if 'matrix' in opis:
			frameTransformation.fromRowMatrixStr(opis["matrix"], ",")
			isTransformDefined = True

		if isTransformDefined:
			timeS = float(opis["time"]) if 'time' in opis else 1.0
			msec = int(timeS * 1000.0)

			return Motion.FrameVal(msec, frameTransformation)

		return Motion.FrameVal()

	def parseProperty_sequence(self, stream):
		slowo = self.skip_comments(stream)

		if slowo is None:
			print("Osiągnięto koniec pliku podczas parsowania właściwości 'sequence'")
			return []

		elif slowo != "{":
			print("BŁĄD. Oczekiwano znaku { odczytano: "+slowo )
			return []

		seq = []
		count = 0

		while slowo != "}":
			slowo = self.skip_comments(stream)

			if slowo is None:
				print("Osiągnięto koniec pliku podczas parsowania włąściwości 'sequence'")
				return None
			elif slowo == "}":
				print("Znaleziono klamrę zamykająca właściwość 'sequence'")
			elif slowo == "frame":
				frame = self.parseProperty_frame(stream)
				seq.append( frame )
			# elif slowo == "frameset":
			# 	frameset = self.parseProperty_frameset(stream)
			# 	seq += frameset
			else:
				print("BŁĄD. Nierozpoznany symbol "+ slowo)

		return seq

	def parseObject_animation(self, stream):
		slowo = self.skip_comments(stream)

		if slowo is None:
			print("Osiągnięto koniec pliku podczas parsowania obiektu 'animation'")
			return None

		elif slowo != "{":
			print("BŁĄD. Oczekiwano znaku { odczytano: "+slowo )
			return None

		opis = {}
		kids = []

		seq = []

		while slowo != "}":
			slowo = self.skip_comments(stream)

			if slowo is None:
				print("Osiągnięto koniec pliku podczas parsowania obiektu 'transformation'")
				return None
			elif slowo == "}":
				print("Znaleziono klamrę zamykająca obiekt 'transformation'")
			elif slowo in {'label', 'descr'}:
				tekst = self.parseType_string(stream)
				if tekst:
					opis[slowo] = tekst
			elif slowo in { "sequence", "sequention"}:
				seq = self.parseProperty_sequence(stream)
			else:
				tmp = self.parseObject(stream, slowo)
				if tmp:
					kids.append(tmp)
				else:
					print("BŁĄD. Nierozpoznany symbol "+ slowo)

		obj = Motion(seq)
		if obj:
			if 'label' in opis:
				obj.setLabel(opis["label"])
			if 'descr' in opis:
				obj.setDescription(opis["descr"])
			for kid in kids:
				self.add_kid(obj, kid)
		return obj

	def parseProperty_rotation(self, stream):
		slowo = self.skip_comments(stream)

		if slowo is None:
			print("Osiągnięto koniec pliku podczas parsowania właściwości 'rotation'")
			return None

		if slowo != "{":
			print("BŁĄD. Oczekiwano znaku { odczytano: "+ slowo)
			return Transform()

		opis = {}
		kids = []

		while slowo != "}":
			slowo = self.skip_comments(stream)

			if slowo is None:
				print("Osiągnięto koniec pliku podczas parsowania właściwości 'rotation'")
				return Transform()
			elif slowo == "}":
				print("Znaleziono klamrę zamykajacą właściwość 'rotation'")
			elif slowo in {'axis', 'origin'}:
				tekst = self.parseType_matrix(stream)
				if tekst:
					opis[slowo] = tekst
			elif slowo == "angle":
				slowo, _ = self.readWord(stream)
				if slowo:
					opis["angle"] = slowo
			else:
				print("BŁĄD. Nierozpoznany symbol "+ slowo)
				return Transform()

		t = Transform()
		if 'axis' in opis and 'angle' in opis:
			axisList = opis['axis'].split(',')
			axis = [ float(axisList[0]), float(axisList[1]), float(axisList[2]) ]

			angle = float(opis['angle'])

			origin = None
			if 'origin' in opis:
				originList = opis['origin'].split(',')
				origin = [ float(originList[0]), float(originList[1]), float(originList[2]) ]
			t.rotate(angle, axis, origin)
		return t

	def parseProperty_translation(self, stream):
		slowo =	self.parseType_matrix(stream)

		t = Transform()

		if slowo:
			axisList = slowo.split(',')
			axis = [ float(axisList[0]), float(axisList[1]), float(axisList[2]) ]
			t.translate(axis)

		return t
	
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
		with open(path,'r') as stream:
			self.atmdlFile = path
			root = Transform()

			while True:
				slowo = self.skip_comments(stream)
				if slowo:
					tmp = self.parseObject(stream, slowo)
					if tmp:
						self.add_kid(root, tmp)
					else:
						print("\033[33mNierozpoznany symbol: " + slowo + "\033[0m" )
				else:
					print("\033[31mKONIEC PLIKU\033[0m")
					break
			

			return root


	