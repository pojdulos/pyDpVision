# -*- coding: utf-8 -*-
"""
Created on Thu Apr 16 12:00:00 2026

@author: Codex
"""

from .annotation import Annotation
from .mesh import Mesh

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

        self._mesh_cache = None
        self._is_initialized = False

        self._position = [0.0, 0.0, 0.0]
        self._radii = [1.0, 1.0, 1.0]
        self._axes = np.eye(3, dtype=np.float64)
        self.m_showAxes = False

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
        self._mesh_cache = None

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

    def _build_mesh_geometry(self):
        """Buduje triangulowana siatke elipsoidy z lokalnymi normalnymi wierzcholkow."""
        vertices = []
        faces = []

        for i in range(self.m_lats + 1):
            lat = np.pi * (-0.5 + float(i) / self.m_lats)
            z = np.sin(lat)
            zr = np.cos(lat)

            for j in range(self.m_longs):
                lng = 2.0 * np.pi * float(j) / self.m_longs
                x = np.cos(lng)
                y = np.sin(lng)
                point = self._local_point_from_unit_sphere((x * zr, y * zr, z))
                vertices.append(point.tolist())

        def vertex_index(lat_idx, long_idx):
            return lat_idx * self.m_longs + (long_idx % self.m_longs)

        for i in range(self.m_lats):
            for j in range(self.m_longs):
                i0 = vertex_index(i, j)
                i1 = vertex_index(i + 1, j)
                i2 = vertex_index(i + 1, j + 1)
                i3 = vertex_index(i, j + 1)

                if i != 0:
                    faces.append([i0, i1, i3])
                if i != self.m_lats - 1:
                    faces.append([i1, i2, i3])

        mesh = Mesh.create(vertices=vertices, faces=faces)
        mesh.label = getattr(self, "label", "AnnotationElipsoide")
        mesh.description = getattr(self, "description", "")
        mesh.b_renderSmooth = True
        mesh.gl_renderAs = gl.GL_TRIANGLES
        return mesh

    def _ensure_geometry(self):
        """Buduje siatke elipsoidy tylko wtedy, gdy dane sa nieaktualne."""
        if not self._is_initialized:
            self._mesh_cache = self._build_mesh_geometry()
            self._is_initialized = True

    def _sync_mesh_material(self):
        """Synchronizuje kolor adnotacji z materialem pomocniczego mesha."""
        self._ensure_geometry()

        qcolor = self._active_qcolor()
        material = self._mesh_cache.materials[self._mesh_cache.currentMaterial]
        material.diffuse = [qcolor.redF(), qcolor.greenF(), qcolor.blueF()]
        material.alpha = qcolor.alphaF()

    def showAxes(self, show=True):
        """Wlacza lub wylacza rysowanie osi lokalnych."""
        self.m_showAxes = bool(show)

    def _render_axes(self):
        """Rysuje lokalne osie elipsoidy w kolorach RGB."""
        if not self.m_showAxes:
            return

        radii = np.asarray(self._radii, dtype=np.float64)
        axis_vectors = [
            self._axes[:, 0] * radii[0],
            self._axes[:, 1] * radii[1],
            self._axes[:, 2] * radii[2],
        ]
        axis_colors = [
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
        ]

        gl.glPushAttrib(gl.GL_ALL_ATTRIB_BITS)
        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glDisable(gl.GL_BLEND)
        gl.glDisable(gl.GL_LIGHTING)
        gl.glLineWidth(2.0)

        for axis_vector, axis_color in zip(axis_vectors, axis_colors):
            gl.glColor3f(*axis_color)
            gl.glBegin(gl.GL_LINES)
            gl.glVertex3f(0.0, 0.0, 0.0)
            gl.glVertex3f(*axis_vector.tolist())
            gl.glEnd()

            gl.glLineWidth(4.0)
            gl.glBegin(gl.GL_LINES)
            gl.glVertex3f(*(axis_vector * 0.88).tolist())
            gl.glVertex3f(*(axis_vector * 0.98).tolist())
            gl.glEnd()
            gl.glLineWidth(2.0)

        gl.glPopAttrib()

    def _render_wireframe(self):
        """Rysuje szkielet elipsoidy jako siatke krawedzi lat/lon."""
        n_lat = 8
        n_lon = 8
        n_seg = 64

        gl.glPushMatrix()
        gl.glPushAttrib(gl.GL_ALL_ATTRIB_BITS)
        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glDisable(gl.GL_LIGHTING)
        gl.glLineWidth(1.0)
        gl.glColor4f(*self._active_outline_rgba())
        gl.glTranslatef(self.position[0], self.position[1], self.position[2])

        for i in range(1, n_lat + 1):
            lat = np.pi * (-0.5 + float(i) / (n_lat + 1))
            z = np.sin(lat)
            zr = np.cos(lat)
            gl.glBegin(gl.GL_LINE_LOOP)
            for j in range(n_seg):
                lng = 2.0 * np.pi * j / n_seg
                p = self._local_point_from_unit_sphere((np.cos(lng) * zr, np.sin(lng) * zr, z))
                gl.glVertex3f(*p)
            gl.glEnd()

        for i in range(n_lon):
            lng = 2.0 * np.pi * i / n_lon
            gl.glBegin(gl.GL_LINE_STRIP)
            for j in range(n_seg + 1):
                lat = np.pi * (-0.5 + float(j) / n_seg)
                p = self._local_point_from_unit_sphere((np.cos(lng) * np.cos(lat), np.sin(lng) * np.cos(lat), np.sin(lat)))
                gl.glVertex3f(*p)
            gl.glEnd()

        gl.glPopAttrib()
        gl.glPopMatrix()

    def render_wboit(self, pass_idx):
        """Renderuje elipsoide przez pipeline mesha z normalnymi wierzcholkow."""
        self._sync_mesh_material()
        gl.glPushMatrix()
        gl.glTranslatef(self.position[0], self.position[1], self.position[2])
        self._mesh_cache.render_wboit(pass_idx)
        gl.glPopMatrix()

    def renderSelf(self):
        """Renderuje elipsoide przez pipeline siatki z gladkim cieniowaniem."""
        from .globals import AP

        if AP.wboit_pass is not None:
            if AP.wboit_pass >= 0:
                if self.is_transparent:
                    self.render_wboit(AP.wboit_pass)
                return
            if self.is_transparent:
                if self.transparent_outline_enabled():
                    self.render_outline()
                gl.glPushMatrix()
                gl.glTranslatef(self.position[0], self.position[1], self.position[2])
                self._render_axes()
                gl.glPopMatrix()
                if self.m_showWireframe:
                    self._render_wireframe()
                return

        self._sync_mesh_material()

        gl.glPushMatrix()
        gl.glTranslatef(self.position[0], self.position[1], self.position[2])
        self._mesh_cache.renderSelf()
        self._render_axes()
        gl.glPopMatrix()

        if self.m_showWireframe:
            self._render_wireframe()

    def render_outline(self):
        """Rysuje obrys elipsoidy wykorzystujac ten sam mesh co render wypelnienia."""
        self._sync_mesh_material()

        gl.glPushMatrix()
        gl.glPushAttrib(gl.GL_ALL_ATTRIB_BITS)

        gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_LINE)
        gl.glLineWidth(1.5)
        gl.glColor4f(*self._active_outline_rgba())
        gl.glTranslatef(self.position[0], self.position[1], self.position[2])
        self._mesh_cache.renderSelf()
        gl.glPopAttrib()
        gl.glPopMatrix()
