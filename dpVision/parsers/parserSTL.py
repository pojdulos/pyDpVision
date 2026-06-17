
from .. import ThreadedParser, AP, Mesh, Transform, BaseObject
from ..conversion import verts_to_grid25D

import numpy as np
import re
import os
import struct
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *


# ---------------------------------------------------------------------------
# Szybkie wczytywanie STL
# ---------------------------------------------------------------------------

class _STLLoadCancelled(Exception):
    pass


def _ensure_running(is_running):
    if is_running is not None and not is_running():
        raise _STLLoadCancelled()

def _read_binary_stl_verts(path, is_running=None):
    """Wczytuje binary STL, zwraca (N*3, 3) float32 — wszystkie wierzchołki trójkątów."""
    data = bytearray()
    with open(path, 'rb') as f:
        while True:
            _ensure_running(is_running)
            chunk = f.read(4 * 1024 * 1024)
            if not chunk:
                break
            data.extend(chunk)
    raw = bytes(data)
    n_tri = np.frombuffer(raw, dtype=np.uint32, count=1, offset=80)[0]
    # każdy trójkąt: 12b normal + 9*4b verts + 2b attr = 50 bajtów
    dtype = np.dtype([
        ('normal', np.float32, 3),
        ('v0',     np.float32, 3),
        ('v1',     np.float32, 3),
        ('v2',     np.float32, 3),
        ('attr',   np.uint16),
    ])
    _ensure_running(is_running)
    tris = np.frombuffer(raw, dtype=dtype, count=n_tri, offset=84)
    # przeplatana kolejność: v0₀,v1₀,v2₀, v0₁,v1₁,v2₁, ... — wymagana przez _verts_to_mesh
    verts = np.stack([tris['v0'], tris['v1'], tris['v2']], axis=1).reshape(-1, 3)
    return verts


def _read_text_stl_verts(path, progress_cb=None, is_running=None):
    """Wczytuje text STL, zwraca (N, 3) float32 — tylko wiersze 'vertex x y z'."""
    vertex_pattern = re.compile(
        r'^\s*vertex\s+([\S]+)\s+([\S]+)\s+([\S]+)', re.IGNORECASE)
    verts = []
    total_size = os.path.getsize(path)
    read_size = 0
    last_pct = 0
    with open(path, 'r', errors='replace') as f:
        for line in f:
            _ensure_running(is_running)
            read_size += len(line)
            m = vertex_pattern.match(line)
            if m:
                verts.append((float(m.group(1)), float(m.group(2)), float(m.group(3))))
            if progress_cb is not None:
                pct = int(read_size / total_size * 100)
                if pct != last_pct:
                    last_pct = pct
                    progress_cb(pct)
    return np.array(verts, dtype=np.float32)


def _is_binary_stl(path):
    """Heurystyka: binary STL nie ma 'solid' jako pierwszego słowa w ASCII."""
    with open(path, 'rb') as f:
        header = f.read(80)
    try:
        txt = header.decode('ascii', errors='ignore').strip().lower()
    except Exception:
        return True
    # Jeśli nagłówek zaczyna się od "solid" i plik jest w całości ASCII → text
    if not txt.startswith('solid'):
        return True
    # Dodatkowa weryfikacja: sprawdź rozmiar vs liczba trójkątów z nagłówka binarnego
    with open(path, 'rb') as f:
        f.seek(80)
        raw4 = f.read(4)
    if len(raw4) < 4:
        return False
    n_tri = struct.unpack('<I', raw4)[0]
    expected_size = 84 + 50 * n_tri
    actual_size = os.path.getsize(path)
    return abs(actual_size - expected_size) < 100  # binary jeśli rozmiar się zgadza


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------

class STLLoaderWorker(QObject):
    progressChanged = pyqtSignal(int)
    statusChanged   = pyqtSignal(str)  # informacja o aktualnym kroku
    loadingFinished  = pyqtSignal(object)  # emituje gotowy BaseObject
    errorOccurred    = pyqtSignal(str)

    def __init__(self, path):
        super().__init__()
        self.path = path
        self._is_running = True

    def stop(self):
        self._is_running = False

    def load_stl(self):
        try:
            label = os.path.basename(self.path)
            print(f"\nParsuję plik: {self.path}")
            self.statusChanged.emit("Wczytuję plik...")
            if _is_binary_stl(self.path):
                self.progressChanged.emit(0)
                verts = _read_binary_stl_verts(self.path, is_running=lambda: self._is_running)
                self.progressChanged.emit(30)
            else:
                verts = _read_text_stl_verts(self.path,
                    progress_cb=self.progressChanged.emit,
                    is_running=lambda: self._is_running)
                self.progressChanged.emit(30)
            if not self._is_running:
                self.errorOccurred.emit("Przerwano")
                return
            # konwersja w wątku roboczym, nie w GUI
            print(f"Wczytano {len(verts)} wierzchołków, konwertuję…")
            obj = verts_to_grid25D(verts, is_running=lambda: self._is_running)
            if obj is None:
                obj = _verts_to_mesh(verts, label,
                    progress_cb=self.progressChanged.emit,
                    status_cb=self.statusChanged.emit,
                    is_running=lambda: self._is_running)
            obj.label = label
            self.progressChanged.emit(100)
            self.statusChanged.emit("Gotowe!")
            if self._is_running:
                self.loadingFinished.emit(obj)
            else:
                self.errorOccurred.emit("Przerwano")
        except _STLLoadCancelled:
            self.errorOccurred.emit("Przerwano")
        except RuntimeError as e:
            if str(e) == "Przerwano":
                self.errorOccurred.emit("Przerwano")
            else:
                self.errorOccurred.emit(str(e))
        except Exception as e:
            import traceback; traceback.print_exc()
            self.errorOccurred.emit(str(e))


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class ParserSTL(ThreadedParser):
    descr     = 'STL files'
    load_exts = ['.stl']
    save_exts = ['.stl']

    def __init__(self, path):
        super().__init__(path, STLLoaderWorker(path), 'load_stl', "Wczytywanie pliku STL")

    @classmethod
    def is_not_static(cls):
        return True

    @classmethod
    def canSaveObject(cls, obj):
        def has_mesh(node):
            if node is None:
                return False
            if isinstance(node, Mesh):
                return True
            return any(has_mesh(child) for child in node.children())

        return has_mesh(obj)

    @classmethod
    def supports_save_progress(cls):
        return True

    def _error_prefix(self):
        return "Błąd wczytywania STL"

    @staticmethod
    def load(path):
        """Synchroniczne wczytanie (fallback gdy get_instance zwraca None)."""
        label = os.path.basename(path)
        try:
            if _is_binary_stl(path):
                verts = _read_binary_stl_verts(path)
            else:
                verts = _read_text_stl_verts(path)
        except Exception as e:
            print(f"Błąd wczytywania STL: {e}")
            return None
        obj = verts_to_grid25D(verts)
        if obj is None:
            obj = _verts_to_mesh(verts, label)
        obj.label = label
        return obj

    @staticmethod
    def save(obj, path, progress_cb=None, status_cb=None):
        def iter_meshes(node):
            if node is None:
                return
            if node.hasType('Mesh'):
                yield node
            for child in node.children():
                yield from iter_meshes(child)

        def transform_vertices(vertices, matrix):
            if len(vertices) == 0:
                return np.empty((0, 3), dtype=np.float32)
            verts = np.asarray(vertices, dtype=np.float64)
            verts_h = np.hstack([verts, np.ones((len(verts), 1), dtype=np.float64)])
            return (verts_h @ matrix.T)[:, :3].astype(np.float32)

        def face_normals(triangles):
            v01 = triangles[:, 1] - triangles[:, 0]
            v02 = triangles[:, 2] - triangles[:, 0]
            normals = np.cross(v01, v02)
            norms = np.linalg.norm(normals, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            return (normals / norms).astype(np.float32)

        if status_cb:
            status_cb("Zbieram siatki do zapisu STL...")
        if progress_cb:
            progress_cb(5)

        meshes = list(iter_meshes(obj))
        if not meshes:
            print("ParserSTL.save: brak siatek do zapisu")
            return False

        triangles_parts = []
        total_meshes = max(len(meshes), 1)
        for mesh_idx, mesh in enumerate(meshes, start=1):
            if not hasattr(mesh, 'm_vertices') or not hasattr(mesh, 'm_faces'):
                continue
            if len(mesh.m_vertices) == 0 or len(mesh.m_faces) == 0:
                continue

            matrix = np.asarray(mesh.getGlobalTransformation(), dtype=np.float64)
            vertices = transform_vertices(mesh.m_vertices, matrix)
            faces = np.asarray(mesh.m_faces, dtype=np.int64)
            triangles_parts.append(vertices[faces])
            if progress_cb:
                progress_cb(5 + int(mesh_idx / total_meshes * 45))

        if not triangles_parts:
            print("ParserSTL.save: znalezione siatki nie zawierają trójkątów")
            return False

        if status_cb:
            status_cb("BudujÄ™ trĂłjkÄ…ty i normalne STL...")
        triangles = np.ascontiguousarray(np.vstack(triangles_parts), dtype=np.float32)
        normals = face_normals(triangles)
        if progress_cb:
            progress_cb(70)

        header_text = f"pyDpVision STL: {getattr(obj, 'label', 'object')}"
        header = header_text.encode('ascii', errors='replace')[:80].ljust(80, b' ')
        tri_count = np.uint32(len(triangles))

        dtype = np.dtype([
            ('normal', np.float32, 3),
            ('v0',     np.float32, 3),
            ('v1',     np.float32, 3),
            ('v2',     np.float32, 3),
            ('attr',   np.uint16),
        ])
        data = np.empty(len(triangles), dtype=dtype)
        data['normal'] = normals
        data['v0'] = triangles[:, 0]
        data['v1'] = triangles[:, 1]
        data['v2'] = triangles[:, 2]
        data['attr'] = 0

        try:
            if status_cb:
                status_cb("ZapisujÄ™ plik STL...")
            with open(path, 'wb') as f:
                f.write(header)
                f.write(tri_count.tobytes())
                f.write(data.tobytes())
            if progress_cb:
                progress_cb(100)
            return True
        except Exception as e:
            print(f"ParserSTL.save: błąd zapisu STL: {e}")
            return False

    @staticmethod
    def inPlugin():
        return False


def _verts_to_mesh(verts, label='', progress_cb=None, status_cb=None, is_running=None):
    """Buduje obiekt Mesh z tablicy wierzchołków (3N, 3) (każda trójka = trójkąt)."""
    _ensure_running(is_running)
    n_tri = len(verts) // 3
    v = verts[:n_tri * 3].astype(np.float32)

    # Deduplikacja wierzchołków - zawsze włączona
    if status_cb:
        status_cb(f"Deduplikuję {len(v)} wierzchołków...")
    print(f"Deduplikuję {len(v)} wierzchołków...")
    if progress_cb:
        progress_cb(40)
    
    _ensure_running(is_running)
    v_view = v.view(np.dtype((np.void, v.dtype.itemsize * 3)))
    _, inv = np.unique(v_view, return_inverse=True)
    unique_idx = np.unique(inv, return_index=True)[1]
    unique_verts = v[unique_idx]
    print(f"Po deduplikacji: {len(unique_verts)} unikalnych wierzchołków ({len(unique_verts)/len(v)*100:.1f}%)")
    if progress_cb:
        progress_cb(60)
    
    # Reshape inv directly to avoid extra dimensions from fancy indexing
    _ensure_running(is_running)
    faces = inv.reshape(n_tri, 3).astype(np.int64)
        
    # Ensure proper shapes and data types
    unique_verts = np.ascontiguousarray(unique_verts, dtype=np.float32)
    faces = np.ascontiguousarray(faces)

    mesh = Mesh()
    mesh.m_vertices = unique_verts
    mesh.m_faces = faces
    mesh.label = label
    
    _ensure_running(is_running)
    if status_cb:
        status_cb("Obliczam normalne...")
    if progress_cb:
        progress_cb(70)
    mesh.calcVN()
    
    # Pre-obliczanie bounding box w tle, żeby nie blokować GUI przy pierwszym renderowaniu
    _ensure_running(is_running)
    if status_cb:
        status_cb("Obliczam bounding box...")
    if progress_cb:
        progress_cb(90)
    _ = mesh.getBB()  # Wywołujemy getBB() żeby cache się zapełnił
    
    return mesh


ParserSTL.regParser()
