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

	def has_transparent(self):
		return any(obj is not None and obj.is_transparent for obj in self.m_data)
		
	def render(self, opaque_only=False, camera_pos=None, view_dir=None):
		"""Two-pass render:
		Pass 1 – obiekty nieprzezroczyste (depth write ON),
		Pass 2 – obiekty przezroczyste posortowane back-to-front (depth write OFF).
		Gdy opaque_only=True renderuje tylko pass 1 (WBOIT przebiegi obsługuje gLViewer).
		"""
		opaque = []
		transparent = []
		for obj in self.m_data:
			if obj is None:
				continue
			if obj.is_transparent:
				transparent.append(obj)
			else:
				opaque.append(obj)

		# --- Pass 1: nieprzezroczyste ---
		for obj in opaque:
			gl.glPushMatrix()
			obj.render()
			gl.glPopMatrix()

		if opaque_only or not transparent:
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
			transparent.sort(key=_depth, reverse=True)  # dalsze pierwsze

		# --- Pass 2: przezroczyste ---
		# Depth write OFF: przezroczyste nie mogą zasłaniać ani siebie nawzajem
		# ani obiektów nieprzezroczystych w buforze głębokości.
		# Depth test ON: przezroczyste nadal są zasłaniane przez nieprzezroczyste
		# obiekty które są przed nimi.
		gl.glDepthMask(gl.GL_FALSE)
		for obj in transparent:
			gl.glPushMatrix()
			obj.render()
			gl.glPopMatrix()
		gl.glDepthMask(gl.GL_TRUE)

	def render_transparent_wboit(self, pass_idx, camera_pos=None, view_dir=None):
		"""Wywołuje render_wboit(pass_idx) na wszystkich przezroczystych obiektach.
		Stan GL (blend, depthMask, DrawBuffers) jest ustawiany przez gLViewer przed wywołaniem.
		"""
		for obj in self.m_data:
			if obj is not None and obj.is_transparent:
				gl.glPushMatrix()
				obj.render_wboit(pass_idx)
				gl.glPopMatrix()

