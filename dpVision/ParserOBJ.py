# -*- coding: utf-8 -*-
"""
Created on Mon Nov 27 12:58:12 2023

@author: pojdulos
"""

from .Parser import Parser
from .PointCloud import PointCloud
from .Mesh import Mesh
import numpy as np
import math

class ParserOBJ(Parser):
	m_descr = "OBJ files"
	m_load_exts = ["obj"]
	#m_save_exts = ["obj"]
	
	@staticmethod	
	def load( path ):
		objFile = open(path, 'r')

		mesh = Mesh()
		
		vces = []
		vnorms = []
		fces = []
		vcols = []
		
		for line in objFile:
			split = line.split()
			
			#if blank line, skip
			if not len(split):
				continue

			elif split[0][0] == '#':
				print('komentarz: ',split)
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
				continue

			elif split[0] == "vn":
				x, y, z = map(float, split[1:4])
				vnorms.append([x,y,z])
			
			elif split[0] == "f":
				#print(split)
				f = []
				for part in split[1:]:
					p = part.split(sep="/")
					n = int(p[0])-1
					f.append( n )
					#print(f)
				
				#mesh.addFace(f[0], f[1], f[2])
				fces.append(f)
			
			else:
				print(split)
				continue

		print( "dodaję wierzcholki "+str(len(vces)) )
		mesh.m_vertices = np.array(vces, dtype=np.float32)

		if len(vnorms):
			print( "dodaję normalne "+str(len(vnorms)) )
			mesh.m_vnormals = np.array(vnorms, dtype=np.float32)

		if len(vcols):
			print( "dodaję kolory "+str(len(vcols)) )
			mesh.m_vcolors = np.array(vcols, dtype=np.ubyte)
			
		if len(fces):
			print( "dodaję scianki "+str(len(fces)) )
			mesh.m_faces = np.array(fces, dtype=np.uint)

# 		mesh.recalcFNormals()
		return mesh
	
	@staticmethod	
	def save( obj, path ):
		return False
	
	@staticmethod	
	def inPlugin():
		return False
	