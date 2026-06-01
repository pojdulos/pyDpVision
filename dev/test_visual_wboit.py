# -*- coding: utf-8 -*-
"""
Quick visual test - dwa kolorowe płaskie kwadraty przecinające się w środku
"""
import sys
from PyQt5.QtCore import QSettings
from dpVision import AP, MainApplication
from dpVision.gui import MainWindow
from dpVision.mesh import Mesh
import numpy as np


def create_plane(center_x, size, color, alpha, label):
    """Tworzy płaszczyznę YZ (prostopadłą do osi X)."""
    s = size / 2
    vertices = np.array([
        [center_x, -s, -s],
        [center_x,  s, -s],
        [center_x,  s,  s],
        [center_x, -s,  s],
    ], dtype=np.float32)
    
    faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.uint)
    
    mesh = Mesh.create(vertices=vertices.tolist(), faces=faces.tolist())
    mesh.label = label
    mesh.materials[''].diffuse = color
    mesh.materials[''].alpha = alpha
    
    return mesh


def main():
    MainApplication.setOrganizationName('IITiS PAN')
    MainApplication.setOrganizationDomain("iitis.pl")
    MainApplication.setApplicationName("dpVision")
    
    AP.mainApp = MainApplication(sys.argv)
    AP.settings = QSettings()
    AP.mainWin = MainWindow()
    
    # Czerwona płaszczyzna z lewej (x=-10)
    red = create_plane(-10, 40, [1.0, 0.0, 0.0], 0.6, "Red Plane")
    AP.mainWin.workspace.m_data.append(red)
    
    # Niebieska płaszczyzna z prawej (x=10)
    blue = create_plane(10, 40, [0.0, 0.0, 1.0], 0.6, "Blue Plane")
    AP.mainWin.workspace.m_data.append(blue)
    
    print("=== Visual Test WBOIT ===")
    print("Czerwona płaszczyzna: x=-10")
    print("Niebieska płaszczyzna: x=10")
    print("\nOczekiwany rezultat:")
    print("✓ Przez czerwoną widać niebieską")
    print("✓ Przez niebieską widać czerwoną")
    print("✓ Widoczna mieszanka kolorów (fiolet) w środku")
    print("✓ NIEZALEŻNIE od kolejności dodawania\n")
    
    AP.mainWin.showMaximized()
    return AP.mainApp.exec_()


if __name__ == '__main__':
    sys.exit(main())
