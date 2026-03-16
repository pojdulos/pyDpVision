# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 13:15:53 2023

@author: darek
"""

from .annotation import Annotation
from .sphere import Sphere
import math

import numpy as np
import OpenGL.GL as gl

class AnnotationSphere(Annotation, Sphere):
    def __init__(self, parent=None):
        Annotation.__init__(self, parent)
        Sphere.__init__(self)

        # Parametry sfery
        self.m_lats = 32
        self.m_longs = 32

        # VBO
        self.vertex_vbo = None
#        self.color_vbo = None
        self.vertex_data = []
#        self.color_data = []

        # Flaga wskazująca, czy VBO zostało zainicjalizowane
        self._is_initialized = False

    def render_wboit(self, pass_idx):
        if not self._is_initialized:
            self.generateSphereData()
            self.initVBO()

        gl.glPushMatrix()
        gl.glTranslatef(self.position[0], self.position[1], self.position[2])

        prog = self._prepare_wboit_shader(pass_idx)
        if prog is None:
            gl.glPopMatrix()
            return

        gl.glEnableVertexAttribArray(0)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vertex_vbo)
        gl.glVertexAttribPointer(0, 3, gl.GL_FLOAT, False, 0, None)
        for i in range(self.m_lats):
            gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, i * (self.m_longs + 1) * 2, (self.m_longs + 1) * 2)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        gl.glDisableVertexAttribArray(0)
        gl.glUseProgram(0)
        gl.glPopMatrix()

    def generateSphereData(self):
        self.vertex_data.clear()
        for i in range(self.m_lats):
            lat0 = np.pi * (-0.5 + float(i) / self.m_lats)
            z0 = np.sin(lat0)
            zr0 = np.cos(lat0)

            lat1 = np.pi * (-0.5 + float(i + 1) / self.m_lats)
            z1 = np.sin(lat1)
            zr1 = np.cos(lat1)

            for j in range(self.m_longs + 1):
                lng = 2 * np.pi * float(j) / self.m_longs
                x = np.cos(lng)
                y = np.sin(lng)

                # Wierzchołki bez przesunięcia — sfera wokół (0,0,0)
                self.vertex_data.extend([
                    self._radius * x * zr0,
                    self._radius * y * zr0,
                    self._radius * z0
                ])
                self.vertex_data.extend([
                    self._radius * x * zr1,
                    self._radius * y * zr1,
                    self._radius * z1
                ])

    def initVBO(self):
        # Konwertowanie listy na tablicę numpy
        vertex_array = np.array(self.vertex_data, dtype=np.float32)
#        color_array = np.array(self.color_data, dtype=np.float32)

        # Tworzenie VBO dla wierzchołków
        self.vertex_vbo = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vertex_vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, vertex_array.nbytes, vertex_array, gl.GL_STATIC_DRAW)

        # Tworzenie VBO dla kolorów
#        self.color_vbo = gl.glGenBuffers(1)
#        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.color_vbo)
#        gl.glBufferData(gl.GL_ARRAY_BUFFER, color_array.nbytes, color_array, gl.GL_STATIC_DRAW)

        # Flaga inicjalizacji ustawiona na True
        self._is_initialized = True

    def drawSphere(self):
        # Włączenie tablicy wierzchołków
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vertex_vbo)
        gl.glVertexPointer(3, gl.GL_FLOAT, 0, None)

        # Włączenie tablicy kolorów
#        gl.glEnableClientState(gl.GL_COLOR_ARRAY)
#        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.color_vbo)
#        gl.glColorPointer(3, gl.GL_FLOAT, 0, None)

        # Rysowanie sfery jako GL_QUAD_STRIP
        for i in range(self.m_lats):
            gl.glDrawArrays(gl.GL_QUAD_STRIP, i * (self.m_longs + 1) * 2, (self.m_longs + 1) * 2)

        # Wyłączenie tablic
        gl.glDisableClientState(gl.GL_VERTEX_ARRAY)
#        gl.glDisableClientState(gl.GL_COLOR_ARRAY)

    def renderSelf(self):
        from .globals import AP

        if AP.wboit_pass is not None:
            if AP.wboit_pass >= 0:
                if self.is_transparent:
                    self.render_wboit(AP.wboit_pass)
                return
            if self.is_transparent:
                return

        gl.glPushMatrix()
        gl.glPushAttrib(gl.GL_ALL_ATTRIB_BITS)

        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glEnable(gl.GL_COLOR_MATERIAL)
        gl.glColorMaterial(gl.GL_FRONT_AND_BACK, gl.GL_AMBIENT_AND_DIFFUSE)

        gl.glEnable(gl.GL_CULL_FACE)
        gl.glCullFace(gl.GL_FRONT)

        if self.checked:
            gl.glColor4ub(self.m_selcolor.red(), self.m_selcolor.green(), self.m_selcolor.blue(), self.m_selcolor.alpha())
        else:
            gl.glColor4ub(self.m_color.red(), self.m_color.green(), self.m_color.blue(), self.m_color.alpha())

        # --- tutaj kluczowe przesunięcie ---
        gl.glTranslatef(self.position[0], self.position[1], self.position[2])

        if not self._is_initialized:
            self.generateSphereData()
            self.initVBO()

        self.drawSphere()

        gl.glPopAttrib()
        gl.glPopMatrix()
