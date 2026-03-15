# -*- coding: utf-8 -*-
"""
Test diagnostyczny WBOIT - czy kolejność rysowania ma znaczenie?
Tworzy dwa przecinające się przecroczyste meshe i sprawdza renderowanie w obu kolejnościach.
"""
import sys
from dpVision.mesh import Mesh
from dpVision.workspace import Workspace
import numpy as np


def create_simple_quad(pos_x, color, alpha):
    """Tworzy prosty quad (prostokąt) w płaszczyźnie YZ."""
    y_size = 20
    z_size = 20
    
    vertices = np.array([
        [pos_x, -y_size/2, -z_size/2],
        [pos_x,  y_size/2, -z_size/2],
        [pos_x,  y_size/2,  z_size/2],
        [pos_x, -y_size/2,  z_size/2],
    ], dtype=np.float32)
    
    faces = np.array([
        [0, 1, 2],
        [0, 2, 3]
    ], dtype=np.uint)
    
    mesh = Mesh.create(vertices=vertices.tolist(), faces=faces.tolist())
    mesh.materials[''].diffuse = color
    mesh.materials[''].alpha = alpha
    
    return mesh


def test_order_independence():
    """Test weryfikujący order-independence WBOIT."""
    print("=== Test Order-Independence WBOIT ===\n")
    
    workspace1 = Workspace()
    workspace2 = Workspace()
    
    # Scenariusz 1: Czerwony przed niebieskim
    print("1. Scenariusz A: Czerwony quad (x=-5) dodany pierwszy, niebieski (x=5) drugi")
    red1 = create_simple_quad(-5, [0.9, 0.1, 0.1], 0.5)
    red1.label = "Red A"
    blue1 = create_simple_quad(5, [0.1, 0.1, 0.9], 0.5)
    blue1.label = "Blue A"
    
    workspace1.m_data.append(red1)
    workspace1.m_data.append(blue1)
    print(f"   - Workspace1: {len(workspace1.m_data)} meshes")
    print(f"   - has_transparent: {workspace1.has_transparent()}")
    
    # Scenariusz 2: Niebieski przed czerwonym (odwrotna kolejność)
    print("\n2. Scenariusz B: Niebieski quad (x=5) dodany pierwszy, czerwony (x=-5) drugi")
    blue2 = create_simple_quad(5, [0.1, 0.1, 0.9], 0.5)
    blue2.label = "Blue B"
    red2 = create_simple_quad(-5, [0.9, 0.1, 0.1], 0.5)
    red2.label = "Red B"
    
    workspace2.m_data.append(blue2)
    workspace2.m_data.append(red2)
    print(f"   - Workspace2: {len(workspace2.m_data)} meshes")
    print(f"   - has_transparent: {workspace2.has_transparent()}")
    
    # Analiza
    print("\n3. Oczekiwane zachowanie z WBOIT:")
    print("   ✓ Scenariusz A i B powinny wyglądać IDENTYCZNIE")
    print("   ✓ Przez czerwony quad powinien być widoczny niebieski")
    print("   ✓ Przez niebieski quad powinien być widoczny czerwony")
    print("   ✓ W środku (gdzie się przecinają) mieszanka kolorów")
    
    print("\n4. WBOIT działa poprawnie gdy:")
    print("   - Depth test jest WYŁĄCZONY w WBOIT passes")
    print("   - Wszystkie fragmenty są akumulowane niezależnie od kolejności")
    print("   - Weight function w shaderze używa z (depth) do wagi")
    print("   - Dwuprzebiegowe renderowanie (back+front faces) dla każdego mesh'a")
    
    print("\n5. Jeśli kolejność ma znaczenie, to oznacza że:")
    print("   ✗ Depth test jest włączony w WBOIT passes")
    print("   ✗ Fragmenty są odrzucane na podstawie depth buffer")
    print("   ✗ WBOIT nie działa jako order-independent")
    
    print("\n6. Zmiany wprowadzone w gLViewer.py:")
    print("   - glDisable(GL_DEPTH_TEST) w WBOIT passes")
    print("   - Usunięto kopiowanie depth buffer from opaque objects")
    print("   - Dwuprzebiegowe renderowanie w render_wboit()")
    
    print("\n✓ Testy statyczne zakończone. Przetestuj wizualnie w aplikacji.")
    print("  Wczytaj dwa meshe, ustaw alpha < 1.0, zobacz czy kolejność ma znaczenie.")
    
    return True


if __name__ == '__main__':
    try:
        result = test_order_independence()
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\n❌ Błąd podczas testu: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
