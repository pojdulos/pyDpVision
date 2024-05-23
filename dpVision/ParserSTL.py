from dpVision.Globals import AP
from .Parser import Parser
from .Mesh import Mesh
import numpy as np
import os
from PyQt5.QtGui import *
import SimpleITK as sitk
from math import *
import struct

def remove_duplicate_vertices(vertices, triangles):
    # Słownik do przechowywania unikalnych wierzchołków i ich nowych indeksów
    unique_vertices = {}
    new_index = 0
    
    # Lista na unikalne wierzchołki
    new_vertices = []
    
    # Przypisanie nowych indeksów do unikalnych wierzchołków
    for i, vertex in enumerate(vertices):
        vertex_tuple = tuple(vertex)
        if vertex_tuple not in unique_vertices:
            unique_vertices[vertex_tuple] = new_index
            new_vertices.append(vertex)
            new_index += 1
    
    # Zaktualizowanie indeksów trójkątów
    new_triangles = []
    for triangle in triangles:
        new_triangle = [unique_vertices[tuple(vertices[idx])] for idx in triangle]
        new_triangles.append(new_triangle)
    
    return new_vertices, new_triangles

class ParserSTL(Parser):
	descr = 'STL files'
	load_exts = ['.stl'] #,'.dcm']
	#save_exts = ['.dcm']

	@staticmethod	
	def loadTextStl( path ):
		mesh = None
		with open(path,'r') as stream:
			print("\n\nParsuję plik: "+path)
			
			# solid szyna_ver0.stl
			header = stream.readline() or None

			vertices = []
			# vnormals = []
			faces = []

			while True:
				line = stream.readline() or None

				if line is None:
					break

				line = line.strip()

				if line.startswith("endsolid"):
					break

				if line.startswith("facet"):
					# facet normal 0.9370570467 0.3490924633 -0.0076513615
					vTxt = line.split()
					nx,ny,nz = map(float, vTxt[2:])
					
					line = stream.readline() or None
					# outer loop  


					face = []

					# vertex    93.3950725187    32.3959506068    -0.3892593974
					line = stream.readline() or None
					vTxt = line.split()

					while vTxt[0] == 'vertex':
						x,y,z = map(float, vTxt[1:])
						vidx = len(vertices)
						vertices.append([x, y, z])
						# vnormals.append([nx, ny, nz])
						face.append(vidx)
						line = stream.readline() or None
						vTxt = line.split()

					faces.append(face)

					line = stream.readline() or None
					# endloop
					
					line = stream.readline() or None
					# endfacet

			# print(f"Przed - liczba wierzchołków: {len(vertices)}, liczba ścianek: {len(faces)}")
			vertices, faces = remove_duplicate_vertices(vertices, faces)
			# print(f"Po    - liczba wierzchołków: {len(vertices)}, liczba ścianek: {len(faces)}")

			mesh = Mesh()
			mesh.m_vertices = np.array(vertices, dtype=np.float32)
			# mesh.m_vnormals = np.array(vnormals, dtype=np.float32)
			mesh.m_faces = np.array(faces, dtype=np.uint)

			mesh.calcVN()
		return mesh

	@staticmethod	
	def loadBinaryStl( path ):
		try:
			with open(path, 'rb') as file:
				print("\n\nParsuję plik: "+path)

				# Odczytujemy pierwsze 80 bajtów
				header = file.read(80)

				ileB = file.read(4)
				lb = struct.unpack('i', ileB)[0]

				vertices = []
				faces = []
				for _ in range(lb):
					t = file.read(50)

					# Pomiń pierwsze 12 bajtów i odczytaj tylko 9 floatów z zakresu od 12 do 47 bajtu
					floats = struct.unpack('9f', t[12:48])
					# Podziel floats na trzy grupy po trzy elementy
					v = [list(floats[i:i+3]) for i in range(0, 9, 3)]
					
					face = []
					for vertex in v:					
						face.append(len(vertices))
						vertices.append(vertex)

					faces.append(face)

				vertices, faces = remove_duplicate_vertices(vertices, faces)

				mesh = Mesh()
				mesh.m_vertices = np.array(vertices, dtype=np.float32)
				mesh.m_faces = np.array(faces, dtype=np.uint)

				mesh.calcVN()
				return mesh
		except Exception as e:
			print(f"Error reading file: {e}")
			return None

	@staticmethod	
	def load( path ):
		mesh = None
		try:
			with open(path, 'rb') as file:
            	# Odczytujemy pierwsze 80 bajtów
				header = file.read(80)
				file.close()
            	# Sprawdzamy, czy nagłówek zaczyna się od "solid"
				if header[:5].decode('ascii', errors='ignore').lower() == 'solid':
					mesh = ParserSTL.loadTextStl(path)
				else:
					mesh = ParserSTL.loadBinaryStl(path)
		except Exception as e:
			print(f"Error reading file: {e}")
			return None

		return mesh

	@staticmethod	
	def save( obj, path ):
		return False
	
	@staticmethod	
	def inPlugin():
		return False
		

