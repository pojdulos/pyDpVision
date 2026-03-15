# -*- coding: utf-8 -*-
"""
Test dwóch przecinających się przezroczystych mesh'ów z WBOIT
"""
import sys
from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtWidgets import QApplication
from dpVision import AP, MainApplication
from dpVision.gui import MainWindow
from dpVision.mesh import Mesh
import numpy as np


def create_cube(center, size, color, alpha):
    """Tworzy sześcian o zadanym środku, rozmiarze, kolorze i przezroczystości."""
    cx, cy, cz = center
    s = size / 2.0
    
    vertices = np.array([
        [cx-s, cy-s, cz-s], [cx+s, cy-s, cz-s], [cx+s, cy+s, cz-s], [cx-s, cy+s, cz-s],
        [cx-s, cy-s, cz+s], [cx+s, cy-s, cz+s], [cx+s, cy+s, cz+s], [cx-s, cy+s, cz+s]
    ], dtype=np.float32)
    
    faces = np.array([
        [0, 1, 2], [0, 2, 3],  # przód
        [4, 6, 5], [4, 7, 6],  # tył
        [0, 4, 5], [0, 5, 1],  # dół
        [2, 6, 7], [2, 7, 3],  # góra
        [0, 3, 7], [0, 7, 4],  # lewo
        [1, 5, 6], [1, 6, 2]   # prawo
    ], dtype=np.uint)
    
    mesh = Mesh.create(vertices=vertices.tolist(), faces=faces.tolist())
    mesh.materials[''].diffuse = color
    mesh.materials[''].alpha = alpha
    
    return mesh


def main():
    print("=== Test dwóch przecinających się przezroczystych mesh'ów ===\n")
    
    # Inicjalizacja aplikacji
    MainApplication.setOrganizationName('IITiS PAN')
    MainApplication.setOrganizationDomain("iitis.pl")
    MainApplication.setApplicationName("dpVision")
    
    AP.mainApp = MainApplication(sys.argv)
    AP.settings = QSettings()
    AP.mainWin = MainWindow()
    
    workspace = AP.mainWin.workspace
    
    # Utwórz dwa przecinające się sześciany
    print("1. Tworzenie pierwszego sześcianu (czerwony, lewo)...")
    mesh1 = create_cube(
        center=[-5, 0, 0],
        size=15,
        color=[0.9, 0.2, 0.2],  # czerwony
        alpha=0.5
    )
    mesh1.label = "Cube 1 (Red)"
    #workspace.m_data.append(mesh1)
    AP.addObject(mesh1)  # Dodaj do workspace (jeśli potrzebne)
    print(f"   - {mesh1.info()}")
    print(f"   - Alpha: {mesh1.materials[''].alpha}, is_transparent: {mesh1.is_transparent}")
    
    print("\n2. Tworzenie drugiego sześcianu (niebieski, prawo)...")
    mesh2 = create_cube(
        center=[5, 0, 0],
        size=15,
        color=[0.2, 0.2, 0.9],  # niebieski
        alpha=0.5
    )
    mesh2.label = "Cube 2 (Blue)"
    # workspace.m_data.append(mesh2)
    AP.addObject(mesh2)  # Dodaj do workspace (jeśli potrzebne)
    print(f"   - {mesh2.info()}")
    print(f"   - Alpha: {mesh2.materials[''].alpha}, is_transparent: {mesh2.is_transparent}")
    
    # Sprawdź czy są wykryte jako przezroczyste
    print(f"\n3. workspace.has_transparent(): {workspace.has_transparent()}")
    
    # Info o WBOIT
    print("\n4. Informacje o WBOIT:")
    print("   - Oba meshe mają dwuprzebiegowe renderowanie (back+front faces)")
    print("   - WBOIT akumuluje wszystkie fragmenty niezależnie od kolejności")
    print("   - Powinno być widoczne:")
    print("     ✓ Przez czerwony mesh widać niebieski mesh")
    print("     ✓ Przez niebieski mesh widać czerwony mesh")
    print("     ✓ W miejscu przecięcia widać mieszankę kolorów")
    
    # Pokaż okno
    print("\n5. Uruchamianie aplikacji GUI...")
    print("   Sprawdź wizualnie czy:")
    print("   - Oba meshe są przezroczyste")
    print("   - Widać przez nie nawzajem (w obie strony)")
    print("   - Brak problemów z zasłanianiem\n")
    
    AP.mainWin.showMaximized()
    AP.updateAllViews()
    return AP.mainApp.exec_()


if __name__ == '__main__':
    sys.exit(main())
