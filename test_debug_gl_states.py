# -*- coding: utf-8 -*-
"""
Debug - sprawdzenie czy depth test jest naprawdę wyłączony podczas WBOIT
"""
import sys
from PyQt5.QtCore import QSettings
from dpVision import AP, MainApplication
from dpVision.gui import MainWindow
from dpVision.mesh import Mesh
from OpenGL.GL import *
import numpy as np


def check_gl_state(label):
    """Sprawdź i wyświetl aktualne stany OpenGL."""
    depth_test = glIsEnabled(GL_DEPTH_TEST)
    depth_func = glGetIntegerv(GL_DEPTH_FUNC)
    depth_mask = glGetBooleanv(GL_DEPTH_WRITEMASK)
    blend = glIsEnabled(GL_BLEND)
    blend_src = glGetIntegerv(GL_BLEND_SRC)
    blend_dst = glGetIntegerv(GL_BLEND_DST)
    cull_face = glIsEnabled(GL_CULL_FACE)
    cull_mode = glGetIntegerv(GL_CULL_FACE_MODE) if cull_face else None
    
    print(f"\n=== GL State: {label} ===")
    print(f"  Depth Test: {depth_test}")
    print(f"  Depth Func: {depth_func} (GL_LEQUAL={GL_LEQUAL})")
    print(f"  Depth Mask: {depth_mask}")
    print(f"  Blend: {blend}")
    print(f"  Blend Src: {blend_src}, Dst: {blend_dst}")
    print(f"  Cull Face: {cull_face}")
    if cull_mode:
        print(f"  Cull Mode: {cull_mode} (GL_FRONT={GL_FRONT}, GL_BACK={GL_BACK})")


def create_plane(x, color):
    vertices = np.array([
        [x, -15, -15], [x, 15, -15],
        [x, 15, 15],   [x, -15, 15]
    ], dtype=np.float32)
    
    faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.uint)
    
    mesh = Mesh.create(vertices=vertices.tolist(), faces=faces.tolist())
    mesh.materials[''].diffuse = color
    mesh.materials[''].alpha = 0.6
    
    return mesh


def main():
    MainApplication.setOrganizationName('IITiS PAN')
    MainApplication.setOrganizationDomain("iitis.pl")
    MainApplication.setApplicationName("dpVision")
    
    AP.mainApp = MainApplication(sys.argv)
    AP.settings = QSettings()
    AP.mainWin = MainWindow()
    
    # Dwa meshe
    red = create_plane(-8, [1, 0, 0])
    red.label = "Red"
    blue = create_plane(8, [0, 0, 1])
    blue.label = "Blue"
    
    AP.mainWin.workspace.m_data = [red, blue]
    
    print("=== Debug WBOIT - sprawdzanie stanów GL ===")
    print("\nDodano dwa przecinające się meshe:")
    print("  - Czerwony (x=-8)")
    print("  - Niebieski (x=8)")
    print("\nUruchamianie aplikacji...")
    print("Po pierwszej klatce sprawdź output w konsoli.")
    print("\nJeśli zobaczysz 'Depth Test: True' w WBOIT passes,")
    print("to znaczy że depth test jest błędnie włączony!\n")
    
    AP.mainWin.showMaximized()
    return AP.mainApp.exec_()


if __name__ == '__main__':
    sys.exit(main())
