# -*- coding: utf-8 -*-
"""
Parser plików E57 (ASTM E2807).

Wczytywanie odbywa sie w osobnym procesie (_e57_subprocess.py) â€” izoluje
Xerces-C (libE57Format) od sterownika OpenGL, które mają konflikt DLL.
"""

import os
import sys
import json
import subprocess
import tempfile
import threading
import numpy as np

from PyQt5.QtCore import QObject, pyqtSignal
from .. import Parser, Transform, BaseObject
from ..pointCloud import PointCloud
from ..sphereGrid import SphereGrid

# sciezka do worker scriptu (obok tego pliku)
_WORKER_SCRIPT = os.path.join(os.path.dirname(__file__), '_e57_subprocess.py')


# ---------------------------------------------------------------------------
# Budowanie obiektów z danych npz
# ---------------------------------------------------------------------------

def _build_objects_from_npz(npz_path):
    """Wczytuje npz z wynikami subprocess i buduje drzewo obiektĂłw dpVision."""
    data = np.load(npz_path, allow_pickle=True)
    root_meta = json.loads(str(data['meta']))

    label     = root_meta['label']
    scan_meta = root_meta['scans']
    labels    = root_meta['labels']

    root = Transform()
    root.label = label

    for idx, (meta, scan_label) in enumerate(zip(scan_meta, labels)):
        prefix = f"scan_{idx}"
        obj = None

        if meta['type'] == 'sphere_grid':
            range_map  = data[f'{prefix}_range_map']
            intensity  = data[f'{prefix}_intensity'] if meta['has_intensity'] else None
            rgb        = data[f'{prefix}_rgb']       if meta['has_rgb']       else None
            origin     = np.array(meta['origin'], dtype=np.float32)
            az_per_col = np.array(data[f'{prefix}_az_per_col']) if f'{prefix}_az_per_col' in data else None
            el_per_row = np.array(data[f'{prefix}_el_per_row']) if f'{prefix}_el_per_row' in data else None
            obj = SphereGrid(
                range_map,
                azimuth_range=(meta['az_min'], meta['az_max']),
                elevation_range=(meta['el_min'], meta['el_max']),
                intensity=intensity,
                rgb=rgb,
                origin=origin,
                az_per_col=az_per_col,
                el_per_row=el_per_row,
                unit='m',
            )
        elif meta['type'] == 'point_cloud':
            pc = PointCloud()
            pc.m_vertices = data[f'{prefix}_vertices']
            if meta['has_colors']:
                pc.m_vcolors = data[f'{prefix}_colors']
            obj = pc

        if obj is not None:
            obj.label = scan_label

            scan_tra = Transform()
            scan_tra.label = scan_label
            if 'pose_matrix' in meta:
                pose_4x4 = np.array(meta['pose_matrix'], dtype=np.float64).reshape(4, 4)
                obj.pose_matrix = pose_4x4.copy()   # oryginał do celów obliczeniowych
                # Forward pose [R|t]: P_global = R @ P_local + t
                scan_tra.fromNumPy(pose_4x4)
            scan_tra.addChild(obj)
            root.addChild(scan_tra)

    return root


# ---------------------------------------------------------------------------
# Worker (subprocess w osobnym Python thread)
# ---------------------------------------------------------------------------

class E57LoaderWorker(QObject):
    progressChanged = pyqtSignal(int)
    statusChanged   = pyqtSignal(str)
    loadingFinished = pyqtSignal(object)
    errorOccurred   = pyqtSignal(str)

    def __init__(self, path):
        super().__init__()
        self.path = path
        self._is_running = True
        self._thread = None
        self._proc = None

    def stop(self):
        self._is_running = False
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()

    def start(self):
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()

    def run(self):
        npz_fd, npz_path = tempfile.mkstemp(suffix='.npz')
        os.close(npz_fd)
        try:
            cmd = [sys.executable, _WORKER_SCRIPT, self.path, npz_path]
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
            )

            stderr_lines = []
            for line in self._proc.stdout:
                line = line.rstrip()
                if not self._is_running:
                    self._proc.terminate()
                    break
                if line.startswith('PROGRESS:'):
                    try:
                        self.progressChanged.emit(int(line[9:]))
                    except ValueError:
                        pass
                elif line.startswith('STATUS:'):
                    self.statusChanged.emit(line[7:])
                    print(f"[E57] {line[7:]}", flush=True)
                elif line.startswith('ERROR:'):
                    stderr_lines.append(line[6:])
                elif line == 'DONE':
                    pass

            _, stderr_out = self._proc.communicate()
            if stderr_out:
                stderr_lines.append(stderr_out)

            if not self._is_running:
                self.errorOccurred.emit("Przerwano")
                return

            if self._proc.returncode != 0:
                err = '\n'.join(stderr_lines) or f"exit code {self._proc.returncode}"
                self.errorOccurred.emit(err)
                return

            self.statusChanged.emit("BudujÄ™ obiekty...")
            obj = _build_objects_from_npz(npz_path)
            self.loadingFinished.emit(obj)

        except Exception as e:
            import traceback; traceback.print_exc()
            self.errorOccurred.emit(str(e))
        finally:
            try:
                os.unlink(npz_path)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class ParserE57(Parser):
    loadingFinished = pyqtSignal(BaseObject)
    errorOccurred   = pyqtSignal()

    descr     = 'E57 3D scan files'
    load_exts = ['.e57']

    def __init__(self, path):
        super().__init__()
        self.path = path
        self._worker = None

    @classmethod
    def is_not_static(cls):
        return True

    def _on_finished(self, obj):
        self.loadingFinished.emit(obj)

    def _on_error(self, msg):
        print(f"B\u0142\u0105d wczytywania E57: {msg}", flush=True)
        self.errorOccurred.emit()

    def on_stop_loading(self):
        if self._worker:
            self._worker.stop()

    def load_async(self, progressBar=None):
        print(f"parserE57.load_async() dla '{self.path}'", flush=True)
        self._worker = E57LoaderWorker(self.path)
        self._worker.loadingFinished.connect(self._on_finished)
        self._worker.errorOccurred.connect(self._on_error)
        if progressBar is not None:
            self._worker.progressChanged.connect(progressBar.setValue)
        self._worker.start()

    @staticmethod
    def load(path):
        """Synchroniczny fallback â€” uruchamia subprocess i czeka."""
        print(f"parserE57.load() dla '{path}'", flush=True)
        npz_fd, npz_path = tempfile.mkstemp(suffix='.npz')
        os.close(npz_fd)
        try:
            cmd = [sys.executable, _WORKER_SCRIPT, path, npz_path]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            if result.returncode != 0:
                print(result.stderr, flush=True)
                return None
            return _build_objects_from_npz(npz_path)
        except Exception as e:
            import traceback; traceback.print_exc()
            return None
        finally:
            try:
                os.unlink(npz_path)
            except Exception:
                pass

    @staticmethod
    def inPlugin():
        return False

ParserE57.regParser()


