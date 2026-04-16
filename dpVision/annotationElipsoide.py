# -*- coding: utf-8 -*-
"""
Created on Thu Apr 16 12:00:00 2026

@author: Codex
"""

from .annotation import Annotation

import numpy as np
import OpenGL.GL as gl


class AnnotationElipsoide(Annotation):
    """Renderuje elipsoide zorientowana trzema wektorami kierunkowymi osi lokalnych."""

    def __init__(
        self,
        parent=None,
        position=(0.0, 0.0, 0.0),
        radii=(1.0, 1.0, 1.0),
        axis_x=(1.0, 0.0, 0.0),
        axis_y=(0.0, 1.0, 0.0),
        axis_z=(0.0, 0.0, 1.0),
        color=[0, 255, 255, 128],
        selcolor=[255, 0, 0, 128],
    ):
        """Inicjalizuje elipsoide z centrum, polosiami i kierunkami lokalnych osi."""
        Annotation.__init__(self, parent, color, selcolor)

        self.m_lats = 32
        self.m_longs = 32

        self.vertex_vbo = None
        self.vertex_data = []
        self._is_initialized = False

        self._position = [0.0, 0.0, 0.0]
        self._radii = [1.0, 1.0, 1.0]
        self._axes = np.eye(3, dtype=np.float64)

        self.position = position
        self.setRadii(radii)
        self.setAxes(axis_x=axis_x, axis_y=axis_y, axis_z=axis_z)

    @staticmethod
    def _as_vec3(values, fallback):
        """Konwertuje dowolna sekwencje na liste trzech liczb zmiennoprzecinkowych."""
        try:
            vec = np.asarray(values, dtype=np.float64).reshape(3)
        except Exception:
            vec = np.asarray(fallback, dtype=np.float64).reshape(3)
        return vec

    @staticmethod
    def _normalize(vec, fallback):
        """Normalizuje wektor, a dla zera zwraca zdefiniowany fallback."""
        arr = np.asarray(vec, dtype=np.float64).reshape(3)
        norm = np.linalg.norm(arr)
        if norm <= 1e-12:
            return np.asarray(fallback, dtype=np.float64).reshape(3)
        return arr / norm

    def _mark_geometry_dirty(self):
        """Oznacza geometrię jako wymagajaca przebudowy po zmianie parametrow."""
        self._is_initialized = False
        self.vertex_data = []

    @property
    def position(self):
        """Zwraca srodek elipsoidy."""
        return self._position

    @position.setter
    def position(self, position):
        """Ustawia srodek elipsoidy."""
        self._position = self._as_vec3(position, (0.0, 0.0, 0.0)).tolist()
        self._mark_geometry_dirty()

    @property
    def radii(self):
        """Zwraca dlugosci polosi elipsoidy."""
        return self._radii

    def setRadii(self, radii):
        """Ustawia dlugosci polosi elipsoidy, wymuszajac wartosci dodatnie."""
        radii_vec = np.abs(self._as_vec3(radii, (1.0, 1.0, 1.0)))
        radii_vec[radii_vec <= 1e-12] = 1e-12
        self._radii = radii_vec.tolist()
        self._mark_geometry_dirty()

    def getRadii(self):
        """Zwraca dlugosci polosi elipsoidy."""
        return list(self._radii)

    @property
    def axis_x(self):
        """Zwraca kierunek pierwszej osi lokalnej."""
        return self._axes[:, 0].tolist()

    @property
    def axis_y(self):
        """Zwraca kierunek drugiej osi lokalnej."""
        return self._axes[:, 1].tolist()

    @property
    def axis_z(self):
        """Zwraca kierunek trzeciej osi lokalnej."""
        return self._axes[:, 2].tolist()

    def getAxes(self):
        """Zwraca trojke ortonormalnych osi lokalnych elipsoidy."""
        return [self.axis_x, self.axis_y, self.axis_z]

    def setAxes(self, axis_x=None, axis_y=None, axis_z=None):
        """Ustawia orientacje elipsoidy na podstawie wektorow kierunkowych osi."""
        default_x = np.array((1.0, 0.0, 0.0), dtype=np.float64)
        default_y = np.array((0.0, 1.0, 0.0), dtype=np.float64)
        default_z = np.array((0.0, 0.0, 1.0), dtype=np.float64)

        x_vec = self._normalize(axis_x if axis_x is not None else self.axis_x, default_x)

        if axis_y is not None:
            y_seed = self._as_vec3(axis_y, default_y)
        elif axis_z is not None:
            z_seed = self._normalize(axis_z, default_z)
            y_seed = np.cross(z_seed, x_vec)
        else:
            y_seed = np.cross(default_z, x_vec)
            if np.linalg.norm(y_seed) <= 1e-12:
                y_seed = np.cross(default_y, x_vec)

        y_vec = y_seed - np.dot(y_seed, x_vec) * x_vec
        if np.linalg.norm(y_vec) <= 1e-12:
            fallback = np.cross(default_y, x_vec)
            if np.linalg.norm(fallback) <= 1e-12:
                fallback = np.cross(default_z, x_vec)
            y_vec = fallback
        y_vec = self._normalize(y_vec, default_y)

        z_vec = np.cross(x_vec, y_vec)
        if np.linalg.norm(z_vec) <= 1e-12:
            z_vec = default_z.copy()
        z_vec = self._normalize(z_vec, default_z)

        if axis_z is not None and np.dot(z_vec, self._normalize(axis_z, default_z)) < 0.0:
            y_vec = -y_vec
            z_vec = -z_vec

        self._axes = np.column_stack((x_vec, y_vec, z_vec))
        self._mark_geometry_dirty()

    def _local_point_from_unit_sphere(self, unit_point):
        """Mapuje punkt sfery jednostkowej do lokalnej geometrii elipsoidy."""
        scaled = np.asarray(unit_point, dtype=np.float64) * np.asarray(self._radii, dtype=np.float64)
        return self._axes @ scaled

    def generateElipsoideData(self):
        """Generuje liste wierzcholkow elipsoidy jako zorientowane paski trojkatow."""
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

                p0 = self._local_point_from_unit_sphere((x * zr0, y * zr0, z0))
                p1 = self._local_point_from_unit_sphere((x * zr1, y * zr1, z1))

                self.vertex_data.extend(p0.tolist())
                self.vertex_data.extend(p1.tolist())

    def initVBO(self):
        """Tworzy lub aktualizuje bufor OpenGL z geometrią elipsoidy."""
        vertex_array = np.array(self.vertex_data, dtype=np.float32)

        if self.vertex_vbo is None:
            self.vertex_vbo = gl.glGenBuffers(1)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vertex_vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, vertex_array.nbytes, vertex_array, gl.GL_STATIC_DRAW)

        self._is_initialized = True

    def _ensure_geometry(self):
        """Buduje geometrię i VBO tylko wtedy, gdy dane są nieaktualne."""
        if not self._is_initialized:
            self.generateElipsoideData()
            self.initVBO()

    def drawElipsoide(self):
        """Rysuje elipsoide przy pomocy wczesniej zbudowanego VBO."""
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vertex_vbo)
        gl.glVertexPointer(3, gl.GL_FLOAT, 0, None)

        for i in range(self.m_lats):
            gl.glDrawArrays(gl.GL_QUAD_STRIP, i * (self.m_longs + 1) * 2, (self.m_longs + 1) * 2)

        gl.glDisableClientState(gl.GL_VERTEX_ARRAY)

    def render_wboit(self, pass_idx):
        """Renderuje elipsoide w trybie WBOIT."""
        self._ensure_geometry()

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

    def renderSelf(self):
        """Renderuje pelna elipsoide w klasycznym pipeline OpenGL."""
        from .globals import AP

        if AP.wboit_pass is not None:
            if AP.wboit_pass >= 0:
                if self.is_transparent:
                    self.render_wboit(AP.wboit_pass)
                return
            if self.is_transparent:
                if self.transparent_outline_enabled():
                    self.render_outline()
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

        gl.glTranslatef(self.position[0], self.position[1], self.position[2])
        self._ensure_geometry()
        self.drawElipsoide()

        gl.glPopAttrib()
        gl.glPopMatrix()

        if self.is_transparent and self.transparent_outline_enabled():
            self.render_outline()

    def render_outline(self):
        """Rysuje obrys elipsoidy dla przezroczystych adnotacji."""
        self._ensure_geometry()

        gl.glPushMatrix()
        gl.glPushAttrib(gl.GL_ALL_ATTRIB_BITS)
        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glDisable(gl.GL_BLEND)
        gl.glEnable(gl.GL_COLOR_MATERIAL)
        gl.glColorMaterial(gl.GL_FRONT_AND_BACK, gl.GL_AMBIENT_AND_DIFFUSE)
        gl.glEnable(gl.GL_CULL_FACE)
        gl.glCullFace(gl.GL_BACK)
        gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_LINE)
        gl.glLineWidth(1.5)
        gl.glColor4f(*self._active_outline_rgba())
        gl.glTranslatef(self.position[0], self.position[1], self.position[2])
        self.drawElipsoide()
        gl.glPopAttrib()
        gl.glPopMatrix()
