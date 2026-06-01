# -*- coding: utf-8 -*-
"""
Test - czy WBOIT renderowanie jest w ogóle wywoływane?
"""
import sys
from dpVision.mesh import Mesh
from dpVision.workspace import Workspace
import numpy as np

# Monkey patch render_wboit żeby zobaczyć czy jest wywołany
original_render_wboit = Mesh.render_wboit

call_count = [0]

def tracked_render_wboit(self, pass_idx, cull_mode=None):
    call_count[0] += 1
    if call_count[0] <= 4:  # Wypisz pierwsze 4 wywołania
        print(f"  ✓ render_wboit wywołany: pass={pass_idx}, mesh={self.label}")
    return original_render_wboit(self, pass_idx, cull_mode)

Mesh.render_wboit = tracked_render_wboit

def create_quad(x, color):
    vertices = np.array([
        [x, -10, -10], [x, 10, -10],
        [x, 10, 10],   [x, -10, 10]
    ], dtype=np.float32)
    faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.uint)
    mesh = Mesh.create(vertices=vertices.tolist(), faces=faces.tolist())
    mesh.materials[''].diffuse = color
    mesh.materials[''].alpha = 0.5
    return mesh

print("=== Test śledzenia wywołań WBOIT ===\n")

ws = Workspace()
red = create_quad(-5, [1, 0, 0])
red.label = "Red"
blue = create_quad(5, [0, 0, 1])
blue.label = "Blue"

ws.m_data = [red, blue]

print(f"1. Workspace ma {len(ws.m_data)} meshe")
print(f"2. has_transparent() = {ws.has_transparent()}")
print(f"3. Symulacja WBOIT render...\n")

# Symuluj wywołanie jak w gLViewer
try:
    from OpenGL.GL import *
    # Zainicjuj OpenGL context (wymaga okna, ale spróbujmy)
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    from PyQt5.QtOpenGL import QGLWidget
    widget = QGLWidget()
    widget.makeCurrent()
    
    # Symuluj WBOIT passes
    ws.render_transparent_wboit(0)
    ws.render_transparent_wboit(1)
    
    print(f"\n4. Liczba wywołań render_wboit: {call_count[0]}")
    if call_count[0] == 0:
        print("   ❌ BŁĄD: render_wboit NIE jest wywoływany!")
    elif call_count[0] == 4:  # 2 meshe × 2 passes
        print("   ✓ Poprawnie: 2 meshe × 2 passes = 4 wywołania")
    else:
        print(f"   ⚠ Nieoczekiwana liczba wywołań: {call_count[0]}")
        
except Exception as e:
    print(f"\n❌ Nie można zainicjować GL context: {e}")
    print("To normalne - test wymaga okna OpenGL.")
    print("Zamiast tego, uruchom aplikację i sprawdź czy widzisz")
    print("komunikaty 'render_wboit wywołany' w konsoli.")
