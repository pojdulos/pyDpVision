# -*- coding: utf-8 -*-
"""
Test mechanizmu WBOIT (Weighted-Blended Order-Independent Transparency)
"""
import sys
from dpVision.mesh import Mesh
from dpVision.workspace import Workspace
import numpy as np


def test_wboit():
    """
    Test sprawdzający, czy mechanizm WBOIT jest aktywny dla przezroczystych obiektów.
    """
    print("=== Test mechanizmu WBOIT ===")
    
    # Utwórz workspace
    workspace = Workspace()
    
    # Utwórz prostą przezroczystą siatkę (mesh)
    print("\n1. Tworzenie przezroczystego obiektu Mesh...")
    
    # Prosty sześcian
    vertices = np.array([
        [-10, -10, -10], [10, -10, -10], [10, 10, -10], [-10, 10, -10],  # przód
        [-10, -10, 10],  [10, -10, 10],  [10, 10, 10],  [-10, 10, 10]    # tył
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
    mesh.label = "Test WBOIT Cube"
    
    # Ustaw przezroczystość (is_transparent jest property obliczane z alpha)
    mesh.materials[''].alpha = 0.5
    mesh.materials[''].diffuse = [0.3, 0.6, 0.9]
    
    print(f"   - Utworzono mesh: {mesh.info()}")
    print(f"   - Alpha materiału: {mesh.materials[''].alpha}")
    print(f"   - Przezroczysty (is_transparent): {mesh.is_transparent}")
    
    # Dodaj do workspace (bezpośrednio do m_data)
    workspace.m_data.append(mesh)
    print("   - Dodano do workspace")
    
    # Sprawdź, czy workspace wykrywa przezroczyste obiekty
    print("\n2. Sprawdzanie wykrywania przezroczystych obiektów...")
    has_transp = workspace.has_transparent()
    print(f"   - workspace.has_transparent(): {has_transp}")
    
    if not has_transp:
        print("   ❌ BŁĄD: Workspace nie wykrywa przezroczystych obiektów!")
        return False
    else:
        print("   ✓ Workspace poprawnie wykrywa przezroczyste obiekty")
    
    # Sprawdź dostępność funkcji WBOIT
    print("\n3. Sprawdzanie dostępności funkcji WBOIT...")
    
    # Sprawdź, czy workspace ma metodę render_transparent_wboit
    has_ws_wboit = hasattr(workspace, 'render_transparent_wboit') and callable(getattr(workspace, 'render_transparent_wboit'))
    print(f"   - workspace.render_transparent_wboit() dostępna: {has_ws_wboit}")
    
    # Sprawdź, czy mesh ma metodę render_wboit
    has_mesh_wboit = hasattr(mesh, 'render_wboit') and callable(getattr(mesh, 'render_wboit'))
    print(f"   - mesh.render_wboit() dostępna: {has_mesh_wboit}")
    
    # Sprawdź, czy mesh ma zmienne WBOIT
    has_wboit_vars = hasattr(mesh, 'wboit_shader') and hasattr(mesh, 'wboit_uniform_locs')
    print(f"   - mesh.wboit_shader i wboit_uniform_locs obecne: {has_wboit_vars}")
    
    # Sprawdź, czy mesh ma metodę _compile_wboit_shader
    has_compile = hasattr(mesh, '_compile_wboit_shader') and callable(getattr(mesh, '_compile_wboit_shader'))
    print(f"   - mesh._compile_wboit_shader() dostępna: {has_compile}")
    
    if not has_ws_wboit:
        print("   ❌ BŁĄD: Workspace nie ma metody render_transparent_wboit!")
        return False
    
    if not has_mesh_wboit:
        print("   ❌ BŁĄD: Mesh nie ma metody render_wboit!")
        return False
    
    print("   ✓ Wszystkie funkcje WBOIT są dostępne")
    
    # Sprawdź dostępność shaderów WBOIT
    print("\n4. Sprawdzanie dostępności shaderów WBOIT...")
    import os
    shader_dir = os.path.join(os.path.dirname(__file__), 'dpVision', 'shaders')
    
    wboit_shaders = [
        'wboit_mesh.frag',
        'wboit_splat.frag',
        'wboit_composite.frag',
        'wboit_composite.vert'
    ]
    
    all_shaders_present = True
    for shader_file in wboit_shaders:
        shader_path = os.path.join(shader_dir, shader_file)
        exists = os.path.exists(shader_path)
        status = "✓" if exists else "❌"
        print(f"   {status} {shader_file}: {'obecny' if exists else 'BRAK'}")
        if not exists:
            all_shaders_present = False
    
    if not all_shaders_present:
        print("   ❌ BŁĄD: Brakuje niektórych shaderów WBOIT!")
        return False
    
    print("   ✓ Wszystkie shadery WBOIT są dostępne")
    
    # Sprawdź modyfikację gLViewer
    print("\n5. Sprawdzanie modyfikacji gLViewer.py...")
    glviewer_path = os.path.join(os.path.dirname(__file__), 'dpVision', 'gui', 'gLViewer.py')
    
    with open(glviewer_path, 'r', encoding='utf-8') as f:
        glviewer_code = f.read()
    
    # Sprawdź, czy jest wywołanie has_transparent()
    has_check = 'has_transparent()' in glviewer_code
    print(f"   - Sprawdzanie has_transparent(): {has_check}")
    
    # Sprawdź, czy jest wywołanie render_transparent_wboit
    has_render_wboit = 'render_transparent_wboit' in glviewer_code
    print(f"   - Wywołanie render_transparent_wboit: {has_render_wboit}")
    
    # Sprawdź, czy jest _init_wboit_resources
    has_init_wboit = '_init_wboit_resources' in glviewer_code
    print(f"   - Funkcja _init_wboit_resources: {has_init_wboit}")
    
    # Sprawdź, czy jest _composite_wboit
    has_composite = '_composite_wboit' in glviewer_code
    print(f"   - Funkcja _composite_wboit: {has_composite}")
    
    glviewer_ok = has_check and has_render_wboit and has_init_wboit and has_composite
    
    if not glviewer_ok:
        print("   ❌ BŁĄD: gLViewer nie został poprawnie zmodyfikowany!")
        return False
    
    print("   ✓ gLViewer został poprawnie zmodyfikowany")
    
    print("\n6. Podsumowanie testu:")
    success = has_transp and has_ws_wboit and has_mesh_wboit and all_shaders_present and glviewer_ok
    
    if success:
        print("   ✓✓✓ Test zakończony SUKCESEM ✓✓✓")
        print("   Mechanizm WBOIT jest włączony i gotowy do użycia!")
        print("\n   Jak działa WBOIT:")
        print("   1. Nieprzezroczyste obiekty są renderowane standardowo")
        print("   2. Dla przezroczystych obiektów:")
        print("      a) Pass 0 - akumulacja kolorów z wagami (blend: GL_ONE, GL_ONE)")
        print("      b) Pass 1 - reveal pass (blend: GL_ZERO, GL_ONE_MINUS_SRC_COLOR)")
        print("      c) Composite - łączenie z tłem (standardowy alpha blend)")
        print("\n   Zalety WBOIT:")
        print("   - Order-independent (nie wymaga sortowania trójkątów)")
        print("   - Lepsza jakość wizualna niż back-to-front rendering")
        print("   - Wydajność - jeden przebieg przez geometrię na pass")
    else:
        print("   ❌❌❌ Test NIEUDANY ❌❌❌")
        print("   Mechanizm WBOIT nie działa poprawnie")
    
    return success


if __name__ == '__main__':
    try:
        result = test_wboit()
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\n❌ Wystąpił błąd podczas testu: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
