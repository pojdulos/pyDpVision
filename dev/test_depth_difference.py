#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test czy viewSpaceDepth faktycznie różnicuje meshe"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from dpVision import AP, MainApplication
from dpVision.gui import MainWindow
from dpVision.mesh import Mesh
import numpy as np

print("=== Test viewSpaceDepth w WBOIT ===")

app = AP(sys.argv)
mw = MainWindow(MainApplication())

# Stwórz dwa meshe w BARDZO różnych głębokościach
def create_plane_mesh(center_z, color_rgb, name, alpha=0.5):
    mesh = Mesh() 
    mesh.setName(name)
    
    # Płaszczyzna w płaszczyźnie XY, przesunięta w Z
    size = 50
    vertices = np.array([
        [-size, -size, center_z],
        [ size, -size, center_z],
        [ size,  size, center_z],
        [-size,  size, center_z]
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

# Test 1: Dodaj czerwony Z TYŁU (z = -100), niebieski Z PRZODU (z = -50)
print("\n=== TEST 1: Czerwony z tyłu (z=-100), niebieski z przodu (z=-50) ===")
mesh1 = create_plane_mesh(-100, (1.0, 0.0, 0.0), "Czerwony_tyl", 0.6)
mesh2 = create_plane_mesh(-50, (0.0, 0.0, 1.0), "Niebieski_przod", 0.6)

mw.AP.workspace.addMesh(mesh1)
mw.AP.workspace.addMesh(mesh2)

print(f"Dodano:{mesh1.name()} (czerwony, z=-100 - dalej)")
print(f"  2. {mesh2.name()} (niebieski, z=-50 - bliżej)")
print("\nOczekiwany efekt:")
print("  - Przez niebieski widać czerwony (bliższy ma mniejszą wagę)")
print("  - Przez czerwony widać niebieski")
print("  - NIEZALEŻNIE od kolejności dodawania")

def close_app():
    print("\n=== Aplikacja zamknięta ===")
    mw.close()
    app.quit()

mw.show()
QTimer.singleShot(5000, close_app)

sys.exit(app.exec_())
