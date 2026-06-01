# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 12:31:41 2023

@author: darek
"""

from PyQt5.QtCore import QObject
import OpenGL.GL as gl
import numpy as np

class Workspace(QObject):
	def __init__(self):
		super( Workspace, self ).__init__()
		self.m_data = []
		self.m_checked = []
		self.m_currentObject = None

	def _get_all_objects_recursive(self):
		"""Zbiera wszystkie obiekty z hierarchii workspace rekurencyjnie (włącznie z children)."""
		def collect(obj, result):
			result.append(obj)
			for child in obj.children():
				collect(child, result)
		
		all_objects = []
		for obj in self.m_data:
			if obj is not None:
				collect(obj, all_objects)
		return all_objects

	def has_transparent(self):
		"""Sprawdza czy w hierarchii są jakiekolwiek przezroczyste obiekty (rekurencyjnie)."""
		all_objects = self._get_all_objects_recursive()
		result = any(obj.is_transparent for obj in all_objects)
		return result
		
	def render(self, opaque_only=False, camera_pos=None, view_dir=None):
		"""Two-pass render:
		Pass 1 – obiekty nieprzezroczyste (depth write ON),
		Pass 2 – obiekty przezroczyste posortowane back-to-front (depth write OFF).
		Gdy opaque_only=True renderuje tylko nieprzezroczyste (WBOIT przebiegi obsługuje gLViewer).
		"""
		from .globals import AP

		if opaque_only:
			# Ustawiamy flagę -1: każdy Mesh sam pominie siebie jeśli jest transparent.
			# Nie musimy tu nic dzielić - meshe w głębi hierarchii (np. wewnątrz Transform)
			# same sprawdzają AP.wboit_pass i decydują czy się renderować.
			AP.wboit_pass = -1
			try:
				for obj in self.m_data:
					if obj is None:
						continue
					gl.glPushMatrix()
					obj.render()
					gl.glPopMatrix()
			finally:
				AP.wboit_pass = None
			return

		# Normalny render (bez WBOIT): two-pass z sortowaniem przezroczystych
		opaque = []
		transparent = []
		for obj in self.m_data:
			if obj is None:
				continue
			if obj.is_transparent:
				transparent.append(obj)
			else:
				opaque.append(obj)

		for obj in opaque:
			gl.glPushMatrix()
			obj.render()
			gl.glPopMatrix()

		if not transparent:
			return

		# Sortowanie back-to-front względem osi widoku
		if camera_pos is not None and view_dir is not None:
			cp = np.array(camera_pos, dtype=np.float64)
			vd = np.array(view_dir, dtype=np.float64)
			vd_norm = vd / (np.linalg.norm(vd) + 1e-9)
			def _depth(obj):
				try:
					mp = np.array(obj.getMidpoint(), dtype=np.float64)
					return float(np.dot(mp - cp, vd_norm))
				except Exception:
					return 0.0
			transparent.sort(key=_depth, reverse=True)

		gl.glDepthMask(gl.GL_FALSE)
		for obj in transparent:
			gl.glPushMatrix()
			obj.render()
			gl.glPopMatrix()
		gl.glDepthMask(gl.GL_TRUE)

	def render_transparent_wboit(self, pass_idx, camera_pos=None, view_dir=None):
		"""Renderuje całą scenę w trybie WBOIT (również obiekty opaque)."""
		from .globals import AP
		AP.wboit_pass = pass_idx
		try:
			for obj in self.m_data:
				gl.glPushMatrix()
				obj.render()
				gl.glPopMatrix()
		finally:
			AP.wboit_pass = None

