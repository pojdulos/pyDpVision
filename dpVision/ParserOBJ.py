# -*- coding: utf-8 -*-
"""
Created on Mon Nov 27 12:58:12 2023

@author: pojdulos
"""
from dpVision.Globals import AP
from .Parser import Parser
from .PointCloud import PointCloud
from .Mesh import Mesh
import numpy as np
import math
import os
from PyQt5.QtGui import *


class ParserOBJ(Parser):
	descr = 'OBJ files'
	load_exts = ['.obj']
	#save_exts = ['.obj']
	
	@staticmethod	
	def parseMtlFile(mesh, path, dirname=""):
		if not os.path.exists(path):
			path = dirname+'/'+path
			print(path)
			if not os.path.exists(path):
				print('Plik MTL nie istnieje')
				return False
		
		mtlFile = open(path, 'r')
		
		if not mtlFile.closed:
			currentmtl  = ''
			for line in mtlFile:
				split = line.split()
				
				#if blank line, skip
				if not len(split):
					continue
				elif split[0][0] == '#':
					continue
				elif split[0] == "newmtl":
					# if '' in mesh.materials:
					# 	del mesh.materials['']
					currentmtl = split[1]
					mesh.materials[currentmtl] = Mesh.Material()
				elif split[0] == "Ka":
					r, g, b = map(float, split[1:4])
					mesh.materials[currentmtl].ambient = [r, g, b]
				elif split[0] == "Kd":
					r, g, b = map(float, split[1:4])
					mesh.materials[currentmtl].diffuse = [r, g, b]
				elif split[0] == "Ks":
					r, g, b = map(float, split[1:4])
					mesh.materials[currentmtl].specular = [r, g, b]
				elif split[0] == "d":
					mesh.materials[currentmtl].alpha = float(split[1])
				elif split[0] == "Tr":
					mesh.materials[currentmtl].alpha = 1 - float(split[1])
				elif split[0] == "illum":
					mesh.materials[currentmtl].shinines = float(split[1])
				elif split[0] == "map_Ka":
					pass
				elif split[0] == "map_Kd":
					mesh.materials[currentmtl].dTexFileName = split[1]
				elif split[0] == "map_Ks":
					pass
				else:
					print(split)
					continue


			mtlFile.close()

	@staticmethod	
	def count_lines(path):
		with open(path, 'r') as file:
			return sum(1 for _ in file)

	@staticmethod	
	def load( path ):
		AP.mainWin.progressIndicator.init(text="Wczytuję plik .obj")
		total_lines = ParserOBJ.count_lines(path)
		step = float(total_lines) / 100.0

		objFile = open(path, 'r')

		mesh = Mesh()
		
		vces = []
		vnorms = []
		vcols = []
		tcrds = []
		f0 = []
		f1 = []
		f2 = []
		b1 = True
		b2 = True

		count = 0
		nxtcnt = step
		for line in objFile:
			count = count+1
			if count >= nxtcnt:
				AP.mainWin.progressIndicator.increase()
				nxtcnt = nxtcnt + step

			split = line.split()
			
			#if blank line, skip
			if not len(split):
				continue

			elif split[0][0] == '#':
				continue
			
			elif split[0] == "v":
				if len(split) >= 4:
					x, y, z = map(float, split[1:4])
					vces.append([x,y,z])
					if len(split) >= 7:
						r,g,b = map(float, split[4:7])
						c = [ round(r*255,0), round(g*255,0), round(b*255,0), 255 ]
						vcols.append(c)
			
			elif split[0] == "vt":
				s, t = map(float, split[1:3])
				tcrds.append([s,t])

			elif split[0] == "vn":
				x, y, z = map(float, split[1:4])
				vnorms.append([x,y,z])
			
			elif split[0] == "f":
				str_values = []
				for part in split[1:]:
					str_values.append( part.split(sep="/") )

				values = [[row[i] for row in str_values] for i in range(len(str_values[0]))]

				f0.append([int(i)-1 for i in values[0]])

				if b1 and len(values)>1:
					try:
						f1.append([int(i)-1 for i in values[1]])
					except ValueError:
						b1 = False
				
				if b2 and len(values)>2:
					try:
						f2.append([int(i)-1 for i in values[2]])
					except ValueError:
						b2 = False
			
			elif split[0] == 'mtllib':
				ParserOBJ.parseMtlFile(mesh, split[1], os.path.dirname(path))

			elif split[0] == 'usemtl':
				if split[1] in mesh.materials:
					mesh.currentMaterial = split[1]
					imgFile = mesh.materials[mesh.currentMaterial].dTexFileName
					if not os.path.exists(imgFile):
						imgFile = os.path.dirname(path)+'/'+imgFile
						if not os.path.exists(imgFile):
							print('Plik tekstury nie istnieje')
							continue
					mesh.materials[mesh.currentMaterial].dTexture = QOpenGLTexture(QImage(imgFile).mirrored())

			else:
				print(split)
				continue

		print( "dodaję wierzcholki "+str(len(vces)) )
		mesh.m_vertices = np.array(vces, dtype=np.float32)

		if len(f0):
			print( "dodaję scianki "+str(len(f0)) )
			mesh.m_faces = np.array(f0, dtype=np.uint)

		if len(vnorms):
			print( "dodaję normalne "+str(len(vnorms)) )
			mesh.m_vnormals = np.array(vnorms, dtype=np.float32)
		else:
			mesh.calcVN()
			print( "obliczam normalne "+str(len(mesh.m_vnormals)) )

		if len(vcols):
			print( "dodaję kolory "+str(len(vcols)) )
			mesh.m_vcolors = np.array(vcols, dtype=np.ubyte)

		if len(tcrds):
			print( "dodaję koordynaty tekstury "+str(len(tcrds)) )
			mesh.m_tcoords = np.array(tcrds, dtype=np.float32)

		if len(f1):
			print( "dodaję indeksy tekstury "+str(len(f1)) )
			mesh.m_tindices = np.array(f1, dtype=np.uint)

# 		mesh.recalcFNormals()
		AP.mainWin.progressIndicator.hide()
		return mesh
	
	@staticmethod	
	def save( obj, path ):
		return False
	
	@staticmethod	
	def inPlugin():
		return False
	