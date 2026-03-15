# -*- coding: utf-8 -*-
"""
Created on Mon Nov 27 12:58:12 2023

@author: pojdulos
"""

from .. import Parser, AP, PointCloud, Mesh

import numpy as np
import math
import os
import shutil
from PyQt5.QtGui import *


class ParserOBJ(Parser):
	descr = 'OBJ files'
	load_exts = ['.obj']
	save_exts = ['.obj']

	@staticmethod
	def _iter_exportable_nodes(node):
		if node is None:
			return
		if isinstance(node, Mesh):
			yield node
		elif isinstance(node, PointCloud):
			yield node
		for child in node.children():
			yield from ParserOBJ._iter_exportable_nodes(child)

	@staticmethod
	def _transform_vertices(vertices, matrix):
		if len(vertices) == 0:
			return np.empty((0, 3), dtype=np.float32)
		verts = np.asarray(vertices, dtype=np.float64)
		verts_h = np.hstack([verts, np.ones((len(verts), 1), dtype=np.float64)])
		return (verts_h @ matrix.T)[:, :3].astype(np.float32)

	@staticmethod
	def _transform_normals(normals, matrix):
		if len(normals) == 0:
			return np.empty((0, 3), dtype=np.float32)
		linear = np.asarray(matrix, dtype=np.float64)[:3, :3]
		try:
			normals_t = np.asarray(normals, dtype=np.float64) @ np.linalg.inv(linear)
		except np.linalg.LinAlgError:
			normals_t = np.asarray(normals, dtype=np.float64)
		norms = np.linalg.norm(normals_t, axis=1, keepdims=True)
		norms[norms == 0] = 1.0
		return (normals_t / norms).astype(np.float32)

	@staticmethod
	def _sanitize_name(text, fallback):
		value = str(text).replace('\n', ' ').strip()
		value = ''.join(ch if ch.isalnum() or ch in '._-' else '_' for ch in value)
		return value or fallback

	@staticmethod
	def _copy_texture_if_needed(src_path, dst_dir, used_names):
		if not src_path:
			return None
		src_path = os.path.normpath(src_path)
		if not os.path.isfile(src_path):
			return None

		base_name = os.path.basename(src_path)
		name, ext = os.path.splitext(base_name)
		candidate = base_name
		counter = 1
		while candidate.lower() in used_names:
			candidate = f"{name}_{counter}{ext}"
			counter += 1

		dst_path = os.path.join(dst_dir, candidate)
		if os.path.normcase(os.path.abspath(src_path)) != os.path.normcase(os.path.abspath(dst_path)):
			shutil.copy2(src_path, dst_path)
		used_names.add(candidate.lower())
		return candidate

	@staticmethod
	def _collect_material_export(node, obj_dir, used_texture_names):
		if not isinstance(node, Mesh):
			return None

		material_name = getattr(node, 'currentMaterial', '') or ''
		material = node.materials.get(material_name)
		if material is None:
			return None

		export_name = ParserOBJ._sanitize_name(
			f"{getattr(node, 'label', 'mesh')}_{material_name or 'material'}",
			"material"
		)
		texture_name = None
		texture_path = getattr(material, 'dTexFileName', '')
		if texture_path:
			texture_name = ParserOBJ._copy_texture_if_needed(texture_path, obj_dir, used_texture_names)

		return {
			'name': export_name,
			'ambient': list(material.ambient),
			'diffuse': list(material.diffuse),
			'specular': list(material.specular),
			'alpha': float(material.alpha),
			'illum': int(material.shinines),
			'texture': texture_name,
		}

	@staticmethod
	def _write_mtl_file(mtl_path, materials):
		with open(mtl_path, 'w', encoding='utf-8', newline='\n') as mtl_file:
			mtl_file.write("# .mtl file created with pyDpVision\n\n")
			for material in materials:
				mtl_file.write(f"newmtl {material['name']}\n")
				mtl_file.write(f"Ka {material['ambient'][0]:.6f} {material['ambient'][1]:.6f} {material['ambient'][2]:.6f}\n")
				mtl_file.write(f"Kd {material['diffuse'][0]:.6f} {material['diffuse'][1]:.6f} {material['diffuse'][2]:.6f}\n")
				mtl_file.write(f"Ks {material['specular'][0]:.6f} {material['specular'][1]:.6f} {material['specular'][2]:.6f}\n")
				mtl_file.write(f"d {material['alpha']:.6f}\n")
				mtl_file.write(f"illum {material['illum']}\n")
				if material['texture']:
					mtl_file.write(f"map_Kd {material['texture']}\n")
				mtl_file.write("\n")

	@classmethod
	def canSaveObject(cls, obj):
		return any(True for _ in cls._iter_exportable_nodes(obj))
	
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
		def dodaj_scianki(_f0, _f1=None, f2=None):
			if len(_f0):
				print( "dodajÄ™ scianki "+str(len(_f0)) )
				f0 = [mesh.triangulate(f) if len(f) > 3 else [f] for f in _f0]
				f0 = [item for sublist in f0 for item in sublist]
				mesh.m_faces = np.array(f0, dtype=np.uint)

				if _f1 is not None:
					f1 = [mesh.triangulate(t) if len(t) > 3 else [t] for t in _f1]
					f1 = [item for sublist in f1 for item in sublist]
					mesh.m_tindices = np.array(f1, dtype=np.uint)
		

		AP.mainWin.progressIndicator.init(text="WczytujÄ™ plik .obj")
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

		print( "dodajÄ™ wierzcholki "+str(len(vces)) )
		mesh.m_vertices = np.array(vces, dtype=np.float32)

		dodaj_scianki(f0, f1)

		if len(vnorms):
			print( "dodajÄ™ normalne "+str(len(vnorms)) )
			mesh.m_vnormals = np.array(vnorms, dtype=np.float32)
		else:
			mesh.calcVN()
			print( "obliczam normalne "+str(len(mesh.m_vnormals)) )

		if len(vcols):
			print( "dodajÄ™ kolory "+str(len(vcols)) )
			mesh.m_vcolors = np.array(vcols, dtype=np.ubyte)

		if len(tcrds):
			print( "dodajÄ™ koordynaty tekstury "+str(len(tcrds)) )
			mesh.m_tcoords = np.array(tcrds, dtype=np.float32)

		AP.mainWin.progressIndicator.hide()
		return mesh
	
	@staticmethod	
	def save( obj, path ):
		nodes = list(ParserOBJ._iter_exportable_nodes(obj))
		if not nodes:
			print("ParserOBJ.save: brak siatek lub chmur punktow do zapisu")
			return False

		try:
			obj_dir = os.path.dirname(os.path.abspath(path)) or os.getcwd()
			obj_base_name = os.path.splitext(os.path.basename(path))[0]
			mtl_name = obj_base_name + '.mtl'
			mtl_path = os.path.join(obj_dir, mtl_name)
			used_texture_names = set()
			materials = []
			node_material_names = {}

			for node in nodes:
				material_export = ParserOBJ._collect_material_export(node, obj_dir, used_texture_names)
				if material_export is None:
					continue
				base_name = material_export['name']
				unique_name = base_name
				counter = 1
				existing_names = {m['name'] for m in materials}
				while unique_name in existing_names:
					unique_name = f"{base_name}_{counter}"
					counter += 1
				material_export['name'] = unique_name
				materials.append(material_export)
				node_material_names[id(node)] = unique_name

			with open(path, 'w', encoding='utf-8', newline='\n') as obj_file:
				obj_file.write("# .obj file created with pyDpVision\n\n")
				if len(materials):
					obj_file.write(f"mtllib {mtl_name}\n\n")

				vertex_offset = 1
				texcoord_offset = 1
				normal_offset = 1

				for idx, node in enumerate(nodes, start=1):
					matrix = np.asarray(node.getGlobalTransformation(), dtype=np.float64)
					vertices = ParserOBJ._transform_vertices(node.m_vertices, matrix)
					if len(vertices) == 0:
						continue

					label = getattr(node, 'label', f'object_{idx}')
					safe_label = ParserOBJ._sanitize_name(label, f'object_{idx}')
					obj_file.write(f"o {safe_label}\n")

					has_colors = getattr(node, 'm_vcolors', np.empty((0, 4))).shape[0] == len(vertices)
					if has_colors:
						colors = np.asarray(node.m_vcolors, dtype=np.float32)[:, :3] / 255.0
					for i, pt in enumerate(vertices):
						if has_colors:
							r, g, b = colors[i]
							obj_file.write(f"v {pt[0]:.6f} {pt[1]:.6f} {pt[2]:.6f} {r:.6f} {g:.6f} {b:.6f}\n")
						else:
							obj_file.write(f"v {pt[0]:.6f} {pt[1]:.6f} {pt[2]:.6f}\n")

					has_normals = getattr(node, 'm_vnormals', np.empty((0, 3))).shape[0] == len(vertices)
					if has_normals:
						normals = ParserOBJ._transform_normals(node.m_vnormals, matrix)
						for vn in normals:
							obj_file.write(f"vn {vn[0]:.6f} {vn[1]:.6f} {vn[2]:.6f}\n")

					has_texcoords = (
						isinstance(node, Mesh)
						and getattr(node, 'm_tcoords', np.empty((0, 2))).shape[0] > 0
						and getattr(node, 'm_tindices', np.empty((0, 3))).shape == getattr(node, 'm_faces', np.empty((0, 3))).shape
					)
					if has_texcoords:
						texcoords = np.asarray(node.m_tcoords, dtype=np.float32)
						for vt in texcoords:
							obj_file.write(f"vt {vt[0]:.6f} {vt[1]:.6f}\n")

					if isinstance(node, Mesh) and len(node.m_faces):
						material_name = node_material_names.get(id(node))
						if material_name:
							obj_file.write(f"usemtl {material_name}\n")
						faces = np.asarray(node.m_faces, dtype=np.int64) + vertex_offset
						if has_texcoords:
							tex_faces = np.asarray(node.m_tindices, dtype=np.int64) + texcoord_offset
						if has_normals:
							norm_faces = np.asarray(node.m_faces, dtype=np.int64) + normal_offset
							if has_texcoords:
								for face, tface, nface in zip(faces, tex_faces, norm_faces):
									obj_file.write(
										f"f {face[0]}/{tface[0]}/{nface[0]} {face[1]}/{tface[1]}/{nface[1]} {face[2]}/{tface[2]}/{nface[2]}\n"
									)
							else:
								for face, nface in zip(faces, norm_faces):
									obj_file.write(
										f"f {face[0]}//{nface[0]} {face[1]}//{nface[1]} {face[2]}//{nface[2]}\n"
									)
						else:
							if has_texcoords:
								for face, tface in zip(faces, tex_faces):
									obj_file.write(f"f {face[0]}/{tface[0]} {face[1]}/{tface[1]} {face[2]}/{tface[2]}\n")
							else:
								for face in faces:
									obj_file.write(f"f {face[0]} {face[1]} {face[2]}\n")
					else:
						for point_idx in range(vertex_offset, vertex_offset + len(vertices)):
							obj_file.write(f"p {point_idx}\n")

					obj_file.write("\n")
					vertex_offset += len(vertices)
					if has_texcoords:
						texcoord_offset += len(node.m_tcoords)
					if has_normals:
						normal_offset += len(vertices)

			if len(materials):
				ParserOBJ._write_mtl_file(mtl_path, materials)

			return True
		except Exception as e:
			print(f"ParserOBJ.save: blad zapisu OBJ: {e}")
			return False
	
	@staticmethod	
	def inPlugin():
		return False

ParserOBJ.regParser()
