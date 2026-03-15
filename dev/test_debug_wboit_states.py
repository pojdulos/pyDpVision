#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Debug: sprawdź stany GL podczas WBOIT rendering"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from dpVision import AP, MainApplication
from dpVision.gui import MainWindow
from dpVision.mesh import Mesh
import numpy as np
from OpenGL.GL import *

print("=== Debug WBOIT States ===")

app = AP(sys.argv)
mw = MainWindow(MainApplication())

# Stwórz dwa proste meshe (płaszczyzny)
def create_plane_mesh(center_x, color_rgb, alpha=0.5):
    mesh = Mesh()
    mesh.setName(f"Plane_{center_x}")
    
    # Płaszczyzna w płaszczyźnie YZ, przesunięta w X
    size = 50
    vertices = np.array([
        [center_x, -size, -size],
        [center_x,  size, -size],
        [center_x,  size,  size],
        [center_x, -size,  size]
    ], dtype=np.float32)
    
    faces = np.array([
        [0, 1, 2],
        [0, 2, 3]
    ], dtype=np.uint32)
    
    mesh.m_vertices = vertices
    mesh.m_faces = faces
    mesh.calcNormals()
    
    # Ustaw kolor i przezroczystość
    mat = mesh.materials['']
    mat.diffuse = list(color_rgb)
    mat.alpha = alpha
    mesh.currentMaterial = ''
    
    return mesh

# Dodaj dwa meshe w różnej kolejności
mesh1 = create_plane_mesh(-10, (1.0, 0.0, 0.0), 0.5)  # Czerwony z tyłu
mesh2 = create_plane_mesh(10, (0.0, 0.0, 1.0), 0.5)   # Niebieski z przodu

mw.AP.workspace.addMesh(mesh1)
mw.AP.workspace.addMesh(mesh2)

print(f"Dodano meshe:")
print(f"  1. {mesh1.name()} (czerwony, x=-10)")
print(f"  2. {mesh2.name()} (niebieski, x=10)")

# Stwórz monkey-patch do sprawdzania stanów GL
original_render_wboit = Mesh.render_wboit

def debug_render_wboit(self, pass_idx, cull_mode=None):
    mesh_name = self.name()
    
    # Sprawdź stany GL PRZED renderowaniem
    depth_test = glIsEnabled(GL_DEPTH_TEST)
    depth_func = glGetIntegerv(GL_DEPTH_FUNC)
    depth_writemask = glGetBooleanv(GL_DEPTH_WRITEMASK)
    blend_enabled = glIsEnabled(GL_BLEND)
    blend_src = glGetIntegerv(GL_BLEND_SRC_RGB)
    blend_dst = glGetIntegerv(GL_BLEND_DST_RGB)
    cull_enabled = glIsEnabled(GL_CULL_FACE)
    
    print(f"\n[Pass {pass_idx}] Mesh: {mesh_name}")
    print(f"  Depth Test: {depth_test}, Func: {depth_func:#x}, WriteMask: {depth_writemask}")
    print(f"  Blend: {blend_enabled}, Src: {blend_src:#x}, Dst: {blend_dst:#x}")
    print(f"  Cull Face: {cull_enabled}")
    
    # Wywołaj oryginalną metodę
    original_render_wboit(self, pass_idx, cull_mode)

# Zastosuj monkey-patch
Mesh.render_wboit = debug_render_wboit

def close_app():
    print("\n=== Test zakończony ===")
    mw.close()
    app.quit()

mw.show()
QTimer.singleShot(3000, close_app)  # Zamknij po 3 sekundach

sys.exit(app.exec_())
