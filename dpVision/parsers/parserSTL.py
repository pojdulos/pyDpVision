
from .. import Parser, AP, Mesh, Transform, BaseObject
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

def _read_binary_stl_verts(path):
    """Wczytuje binary STL, zwraca (N*3, 3) float32 — wszystkie wierzchołki trójkątów."""
    with open(path, 'rb') as f:
        raw = f.read()
    n_tri = np.frombuffer(raw, dtype=np.uint32, count=1, offset=80)[0]
    # każdy trójkąt: 12b normal + 9*4b verts + 2b attr = 50 bajtów
    dtype = np.dtype([
        ('normal', np.float32, 3),
        ('v0',     np.float32, 3),
        ('v1',     np.float32, 3),
        ('v2',     np.float32, 3),
        ('attr',   np.uint16),
    ])
    tris = np.frombuffer(raw, dtype=dtype, count=n_tri, offset=84)
    # przeplatana kolejność: v0₀,v1₀,v2₀, v0₁,v1₁,v2₁, ... — wymagana przez _verts_to_mesh
    verts = np.stack([tris['v0'], tris['v1'], tris['v2']], axis=1).reshape(-1, 3)
    return verts


def _read_text_stl_verts(path, progress_cb=None):
    """Wczytuje text STL, zwraca (N, 3) float32 — tylko wiersze 'vertex x y z'."""
    vertex_pattern = re.compile(
        r'^\s*vertex\s+([\S]+)\s+([\S]+)\s+([\S]+)', re.IGNORECASE)
    verts = []
    total_size = os.path.getsize(path)
    read_size = 0
    last_pct = 0
    with open(path, 'r', errors='replace') as f:
        for line in f:
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
            if _is_binary_stl(self.path):
                self.progressChanged.emit(0)
                verts = _read_binary_stl_verts(self.path)
                self.progressChanged.emit(50)
            else:
                verts = _read_text_stl_verts(self.path,
                    progress_cb=self.progressChanged.emit if self._is_running else None)
                self.progressChanged.emit(50)
            if not self._is_running:
                return
            # konwersja w wątku roboczym, nie w GUI
            print(f"Wczytano {len(verts)} wierzchołków, konwertuję…")
            obj = verts_to_grid25D(verts)
            if obj is None:
                obj = _verts_to_mesh(verts, label)
            obj.label = label
            self.progressChanged.emit(100)
            if self._is_running:
                self.loadingFinished.emit(obj)
        except Exception as e:
            import traceback; traceback.print_exc()
            self.errorOccurred.emit(str(e))


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class ParserSTL(Parser):
    loadingFinished = pyqtSignal(BaseObject)
    errorOccurred   = pyqtSignal()

    descr     = 'STL files'
    load_exts = ['.stl']

    def __init__(self, path):
        super().__init__()
        self.path = path
        self._thread = QThread()
        self._worker = STLLoaderWorker(path)

    @classmethod
    def is_not_static(cls):
        return True

    def on_loading_finished(self, obj):
        self._thread.quit()
        self._thread.wait()
        self._worker.deleteLater()
        self._thread.deleteLater()
        self.loadingFinished.emit(obj)

    def on_loading_error(self, msg):
        self._thread.quit()
        self._thread.wait()
        self._worker.deleteLater()
        self._thread.deleteLater()
        print(f"Błąd wczytywania STL: {msg}")
        self.errorOccurred.emit()

    def on_stop_loading(self):
        self._worker.stop()
        self._thread.quit()
        self._thread.wait()
        self._worker.deleteLater()
        self._thread.deleteLater()
        self.deleteLater()
        print("Przerwano wczytywanie!")

    def load_async(self, progressBar=None):
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.load_stl)
        if progressBar is not None:
            self._worker.progressChanged.connect(progressBar.setValue)
        self._worker.loadingFinished.connect(self.on_loading_finished)
        self._worker.errorOccurred.connect(self.on_loading_error)
        self._thread.start()

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
    def save(obj, path):
        return False

    @staticmethod
    def inPlugin():
        return False


# Dla dużych siatek deduplikacja (np.unique na 30M wierszach) jest zbyt wolna.
_DEDUP_THRESHOLD = 1_000_000  # trójkątów

def _verts_to_mesh(verts, label=''):
    """Buduje obiekt Mesh z tablicy wierzchołków (3N, 3) (każda trójka = trójkąt)."""
    n_tri = len(verts) // 3
    v = verts[:n_tri * 3].astype(np.float32)

    if n_tri <= _DEDUP_THRESHOLD:
        # deduplikacja dla małych siatek (płynne cieniowanie)
        v_view = v.view(np.dtype((np.void, v.dtype.itemsize * 3)))
        _, inv = np.unique(v_view, return_inverse=True)
        unique_idx = np.unique(inv, return_index=True)[1]
        unique_verts = v[unique_idx]
        faces = inv[np.arange(n_tri * 3, dtype=np.int64).reshape(n_tri, 3)]
    else:
        # brak dedupu dla dużych — flat shading, ale wczytuje się natychmiast
        unique_verts = v
        faces = np.arange(n_tri * 3, dtype=np.uint32).reshape(n_tri, 3)

    mesh = Mesh()
    mesh.m_vertices = unique_verts
    mesh.m_faces = faces
    mesh.label = label
    mesh.calcVN()
    return mesh


ParserSTL.regParser()
