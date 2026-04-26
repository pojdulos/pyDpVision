# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 13:15:53 2023

@author: darek
"""

from .annotation import Annotation
from .sphere import Sphere
from .mesh import Mesh

import numpy as np
import OpenGL.GL as gl

class AnnotationSphere(Annotation, Sphere):
    def __init__(self, parent=None,
                    position=[0.0, 0.0, 0.0],
                    radius=1.0,
                    color=[0,255,255,128],
                    selcolor=[255,0,0,128]):

        Annotation.__init__(self, parent, color, selcolor)
        Sphere.__init__(self, position, radius)

        self.m_lats = 32
        self.m_longs = 32

        self._mesh_cache = None
        self._is_initialized = False

    # --- nadpisanie setterów Sphere aby invalidować geometrię ---

    @Sphere.radius.setter
    def radius(self, value):
        Sphere.radius.fset(self, value)
        self._mark_geometry_dirty()

    # --- cache geometrii ---

    def _mark_geometry_dirty(self):
        self._is_initialized = False
        self._mesh_cache = None

    def _build_mesh_geometry(self):
        vertices = []
        faces = []

        for i in range(self.m_lats + 1):
            lat = np.pi * (-0.5 + float(i) / self.m_lats)
            z = np.sin(lat) * self._radius
            zr = np.cos(lat) * self._radius

            for j in range(self.m_longs):
                lng = 2.0 * np.pi * float(j) / self.m_longs
                x = np.cos(lng) * zr
                y = np.sin(lng) * zr
                vertices.append([x, y, z])

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
        mesh.label = getattr(self, 'label', 'AnnotationSphere')
        mesh.description = getattr(self, 'description', '')
        mesh.b_renderSmooth = True
        mesh.gl_renderAs = gl.GL_TRIANGLES
        return mesh

    def _ensure_geometry(self):
        if not self._is_initialized:
            self._mesh_cache = self._build_mesh_geometry()
            self._is_initialized = True

    def _sync_mesh_material(self):
        self._ensure_geometry()
        qcolor = self._active_qcolor()
        material = self._mesh_cache.materials[self._mesh_cache.currentMaterial]
        material.diffuse = [qcolor.redF(), qcolor.greenF(), qcolor.blueF()]
        material.alpha = qcolor.alphaF()

    # --- rendering ---

    def _render_wireframe(self):
        n_lat = 8
        n_lon = 8
        n_seg = 64
        r = self._radius

        gl.glPushMatrix()
        gl.glPushAttrib(gl.GL_ALL_ATTRIB_BITS)
        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glDisable(gl.GL_LIGHTING)
        gl.glLineWidth(1.0)
        gl.glColor4f(*self._active_outline_rgba())
        gl.glTranslatef(self.position[0], self.position[1], self.position[2])

        for i in range(1, n_lat + 1):
            lat = np.pi * (-0.5 + float(i) / (n_lat + 1))
            z = r * np.sin(lat)
            rz = r * np.cos(lat)
            gl.glBegin(gl.GL_LINE_LOOP)
            for j in range(n_seg):
                lng = 2.0 * np.pi * j / n_seg
                gl.glVertex3f(rz * np.cos(lng), rz * np.sin(lng), z)
            gl.glEnd()

        for i in range(n_lon):
            lng = 2.0 * np.pi * i / n_lon
            gl.glBegin(gl.GL_LINE_STRIP)
            for j in range(n_seg + 1):
                lat = np.pi * (-0.5 + float(j) / n_seg)
                z = r * np.sin(lat)
                rz = r * np.cos(lat)
                gl.glVertex3f(rz * np.cos(lng), rz * np.sin(lng), z)
            gl.glEnd()

        gl.glPopAttrib()
        gl.glPopMatrix()

    def render_wboit(self, pass_idx):
        self._sync_mesh_material()
        gl.glPushMatrix()
        gl.glTranslatef(self.position[0], self.position[1], self.position[2])
        self._mesh_cache.render_wboit(pass_idx)
        gl.glPopMatrix()

    def renderSelf(self):
        from .globals import AP

        if AP.wboit_pass is not None:
            if AP.wboit_pass >= 0:
                if self.is_transparent:
                    self.render_wboit(AP.wboit_pass)
                return
            if self.is_transparent:
                if self.transparent_outline_enabled():
                    self.render_outline()
                if self.m_showWireframe:
                    self._render_wireframe()
                return

        self._sync_mesh_material()

        gl.glPushMatrix()
        gl.glTranslatef(self.position[0], self.position[1], self.position[2])
        self._mesh_cache.renderSelf()
        gl.glPopMatrix()

        if self.is_transparent and self.transparent_outline_enabled():
            self.render_outline()

        if self.m_showWireframe:
            self._render_wireframe()

    def render_outline(self):
        self._ensure_geometry()

        gl.glPushMatrix()
        gl.glPushAttrib(gl.GL_ALL_ATTRIB_BITS)
        gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_LINE)
        gl.glLineWidth(1.5)
        gl.glColor4f(*self._active_outline_rgba())
        gl.glTranslatef(self.position[0], self.position[1], self.position[2])
        self._mesh_cache.renderSelf()
        gl.glPopAttrib()
        gl.glPopMatrix()
