# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 13:15:53 2023

@author: darek
"""

from PyQt5.QtGui import *
from .baseObject import BaseObject
from .object import Object
from OpenGL.GL import *
from .shaders import create_program
import numpy as np

class Annotation(BaseObject):
	TRANSPARENT_OUTLINE_ENABLED = True

	def __init__(self, parent=None, color=[0,255,255,128], selcolor=[255,0,0,128]):
		super( Annotation, self ).__init__( parent )
		r, g, b, a = color
		self.m_color = QColor(r, g, b, a)
		r, g, b, a = selcolor
		self.m_selcolor = QColor(r, g, b, a)
		self._wboit_shader = None
		self.m_showWireframe = False

	def setColor(self, name=None, r=0, g=0, b=255, a=102):
		if name:
			kolor = QColor(name)
			if kolor.isValid():
				self.m_color = kolor
				return
		if r and g and b:
			kolor = QColor(r, g, b, a)
			if kolor.isValid():
				self.m_color = kolor
		return

	def getColor(self):
		return self.m_color
	
	def setSelColor(self, name=None, r=255, g=0, b=0, a=102):
		if name:
			kolor = QColor(name)
			if kolor.isValid():
				self.m_selcolor = kolor
				return
		if r and g and b:
			kolor = QColor(r, g, b, a)
			if kolor.isValid():
				self.m_selcolor = kolor
		return

	def getSelColor(self):
		return self.m_selcolor

	def _active_qcolor(self):
		return self.m_selcolor if self.checked else self.m_color

	def _active_rgba(self):
		col = self._active_qcolor()
		return (
			col.redF(),
			col.greenF(),
			col.blueF(),
			col.alphaF(),
		)

	def _active_outline_rgba(self):
		col = self._active_qcolor()
		return (
			col.redF(),
			col.greenF(),
			col.blueF(),
			1.0,
		)

	@classmethod
	def transparent_outline_enabled(cls):
		return bool(cls.TRANSPARENT_OUTLINE_ENABLED)

	@property
	def is_transparent(self):
		return self._active_qcolor().alphaF() < 0.999

	def _compile_wboit_shader(self):
		if self._wboit_shader is not None:
			return self._wboit_shader
		try:
			self._wboit_shader = create_program(
				vertex_shader_name='annotation_wboit.vert',
				fragment_shader_name='annotation_wboit.frag'
			)
		except Exception as e:
			print(f'[Annotation] WBOIT shader error: {e}')
			self._wboit_shader = None
		return self._wboit_shader

	def _prepare_wboit_shader(self, pass_idx):
		prog = self._compile_wboit_shader()
		if prog is None:
			return None

		glUseProgram(prog)
		model = np.empty((4, 4), dtype=np.float32)
		projection = np.empty((4, 4), dtype=np.float32)
		view = np.identity(4, dtype=np.float32)
		glGetFloatv(GL_MODELVIEW_MATRIX, model)
		glGetFloatv(GL_PROJECTION_MATRIX, projection)

		glUniformMatrix4fv(glGetUniformLocation(prog, "model"), 1, GL_FALSE, model)
		glUniformMatrix4fv(glGetUniformLocation(prog, "view"), 1, GL_FALSE, view)
		glUniformMatrix4fv(glGetUniformLocation(prog, "projection"), 1, GL_FALSE, projection)
		glUniform4f(glGetUniformLocation(prog, "u_color"), *self._active_rgba())
		glUniform1i(glGetUniformLocation(prog, "u_wboit_pass"), pass_idx)
		return prog

	def showWireframe(self, show=True):
		self.m_showWireframe = bool(show)

	def _render_wireframe(self):
		pass
	
