from dpVision.Globals import AP
from dpVision.Transform import Transform
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

def read_line(stream):
    while True:
        line = stream.readline()
        if line == '':  # Koniec pliku
            return None
        if line.strip():  # Linia z treścią
            return line.strip().split()
        # Jeśli linia jest pusta, pętla kontynuuje, aby pominąć pustą linię

class Solid:
	def __init__(self):
		self.header = None
		self.vertices = []
		self.faces = []

class ParserSTL(Parser):
	descr = 'STL files'
	load_exts = ['.stl']
	#save_exts = ['.stl']

	def __init__(self):
		self.solids = []

	def end_procedure(self):
		meshes = []
		for solid in self.solids:
			header = solid.header
			vertices, faces = remove_duplicate_vertices(solid.vertices, solid.faces)

			mesh = Mesh()

			if header:
				if len(header)>2:
					descr = ' '.join(header[1:])
					mesh.setDescription(descr)
					mesh.setLabel(os.path.basename(path))
				elif len(header)>1:
					mesh.setLabel(header[1])
				else:
					mesh.setLabel(os.path.basename(path))

			mesh.m_vertices = np.array(vertices, dtype=np.float32)
			mesh.m_faces = np.array(faces, dtype=np.uint)

			mesh.calcVN()
			meshes.append(mesh)

		if len(meshes) > 1:
			return meshes
		elif len(meshes) > 0:	
			return mesh
		return None

	def error(self, message):
		print(message)
		return self.end_procedure()

	def loadTextStl( self, path ):
		with open(path,'r') as stream:
			print("\n\nParsuję plik: "+path)
			
			header = read_line(stream) # solid szyna_ver0.stl
			if header is None:
				return self.error("'solid' expected, but end of file detected")

			while header[0] == 'solid':
				solid = Solid()
				solid.header = header

				while True: # while (not 'endsolid') or 'facet normal'
					line = read_line(stream) # facet normal nx ny nz
					if line is None:
						return self.error(f"'endsolid' or 'facet normal nx ny nz' expected, but found end of file")
					elif line[0] == "endsolid":
						self.solids.append(solid)
						header = read_line(stream) # solid szyna_ver0.stl
						if header is None:
							return self.error("End of file detected (it is not error)")
						break

					elif not (line[0] == 'facet' and line[1] == 'normal' ):
						return self.error(f"'endsolid' or 'facet normal nx ny nz' expected, but found: {line}")
					else:
						line = read_line(stream) # outer loop
						if line is None:
							return self.error(f"'outer loop' expected, but found end of file")
						elif line[0] != 'outer' or line[1] != 'loop':
							return self.error(f"'outer loop' expected, but found: {line}")
						else:
							vTxt = read_line(stream)
							if vTxt is None:
								return self.error(f"'vertex x y z' expected, but found end of file")
							elif vTxt[0] != 'vertex':
								return self.error(f"'vertex x y z' expected, but found: {line}")
							else:
								face = []
								while vTxt[0] == 'vertex':
									x,y,z = map(float, vTxt[1:])
									vidx = len(solid.vertices)
									solid.vertices.append([x, y, z])
									# vnormals.append([nx, ny, nz])
									face.append(vidx)
									vTxt = read_line(stream)
									if vTxt is None:
										return self.error(f"'vertex x y z' or 'endloop' expected, but found end of file")
								solid.faces.append(face)

								# in vTxt should now be 'endloop'
								if vTxt[0] != 'endloop':
									return self.error(f"'endloop' expected, but found: {line}")
								else:
									line = read_line(stream) # endfacet
									if line is None:
										return self.error(f"'endfacet' expected, but found end of file")
									elif line[0] != 'endfacet':
										return self.error(f"'endfacet' expected, but found: {line}")
		return self.end_procedure()


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

				if header:
					header = header.decode('ascii', errors='ignore').strip().split()
					if len(header)>2:
						descr = ' '.join(header[1:])
						mesh.setDescription(descr)
						mesh.setLabel(os.path.basename(path))
					elif len(header)>1:
						mesh.setLabel(header[1])
					else:
						mesh.setLabel(os.path.basename(path))

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
					mesh = ParserSTL().loadTextStl(path)
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
		

