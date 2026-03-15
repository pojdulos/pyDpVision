#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test z wymuszeniem rekompilacji shaderów WBOIT"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from dpVision import AP, MainApplication
from dpVision.gui import MainWindow
from dpVision.mesh import Mesh
import numpy as np

print("=== Test WBOIT z wymuszeniem rekompilacji shaderów ===")

app = AP(sys.argv)
mw = MainWindow(MainApplication())

def create_plane_mesh(center_x, color_rgb, name, alpha=0.6):
    mesh = Mesh()
    mesh.setName(name)
    
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
    
    mat = mesh.materials['']
    mat.diffuse = list(color_rgb)
    mat.alpha = alpha
    mesh.currentMaterial = ''
    
    return mesh

# Dodaj meshe
mesh1 = create_plane_mesh(-20, (1.0, 0.0, 0.0), "Czerwony", 0.6)
mesh2 = create_plane_mesh(20, (0.0, 0.0, 1.0), "Niebieski", 0.6)

mw.AP.workspace.addMesh(mesh1)
mw.AP.workspace.addMesh(mesh2)

print(f"\nDodano:")
print(f"  1. {mesh1.name()} (czerwony, x=-20)")
print(f"  2. {mesh2.name()} (niebieski, x=20)")

def force_recompile_shaders():
    """Wymuś rekompilację wszystkich shaderów WBOIT"""
    print("\n=== WYMUSZAM REKOMPILACJĘ SHADERÓW WBOIT ===")
    for obj in mw.AP.workspace.m_data:
        if obj is not None and hasattr(obj, 'force_recompile_wboit_shader'):
            print(f"Rekompilacja shadera dla: {obj.name()}")
            obj.force_recompile_wboit_shader()
    print("=== REKOMPILACJA ZAKOŃCZONA ===\n")
    
    # Odśwież widok
    mw.glViewer.update()

# Wymuś rekompilację po 1 sekundzie (po załadowaniu meshów)
QTimer.singleShot(1000, force_recompile_shaders)

def close_app():
    print("\n=== Zamykam aplikację ===")
    mw.close()
    app.quit()

mw.show()
QTimer.singleShot(6000, close_app)

sys.exit(app.exec_())
