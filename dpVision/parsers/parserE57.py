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


def _iter_sphere_grids(node):
    if node is None:
        return
    if isinstance(node, SphereGrid):
        yield node
    for child in node.children():
        yield from _iter_sphere_grids(child)


def _sphere_grid_to_e57_scan(grid):
    rows, cols = grid.shape
    row_idx, col_idx = np.where(grid.mask)
    if len(row_idx) == 0:
        return None

    ranges = np.asarray(grid.range_map[row_idx, col_idx], dtype=np.float64)

    if getattr(grid, '_az_per_col', None) is not None:
        az_deg = np.asarray(grid._az_per_col, dtype=np.float64)[col_idx]
    else:
        az_deg = grid.azimuth_range[0] + (col_idx.astype(np.float64) + 0.5) * (
            (grid.azimuth_range[1] - grid.azimuth_range[0]) / cols
        )

    if getattr(grid, '_el_per_row', None) is not None:
        el_deg = np.asarray(grid._el_per_row, dtype=np.float64)[row_idx]
    else:
        el_deg = grid.elevation_range[0] + (row_idx.astype(np.float64) + 0.5) * (
            (grid.elevation_range[1] - grid.elevation_range[0]) / rows
        )

    az = np.deg2rad(az_deg)
    el = np.deg2rad(el_deg)
    cos_el = np.cos(el)
    origin = np.asarray(grid.origin, dtype=np.float64)

    x = ranges * cos_el * np.cos(az) + origin[0]
    y = ranges * cos_el * np.sin(az) + origin[1]
    z = ranges * np.sin(el) + origin[2]

    scan = {
        'name': getattr(grid, 'label', 'SphereGrid'),
        'cartesianX': x.astype(np.float64),
        'cartesianY': y.astype(np.float64),
        'cartesianZ': z.astype(np.float64),
        'rowIndex': row_idx.astype(np.uint16),
        'columnIndex': col_idx.astype(np.uint16),
    }

    if grid.intensity is not None:
        intensity = np.asarray(grid.intensity[row_idx, col_idx], dtype=np.float32)
        scan['intensity'] = intensity.astype(np.float32)

    if grid.rgb is not None:
        rgb = np.asarray(grid.rgb)
        if rgb.shape[:2] == grid.shape:
            rgb_valid = rgb[row_idx, col_idx]
        elif rgb.shape[0] == rows - 1 and rgb.shape[1] == cols - 1:
            rr = np.clip(row_idx, 0, rgb.shape[0] - 1)
            cc = np.clip(col_idx, 0, rgb.shape[1] - 1)
            rgb_valid = rgb[rr, cc]
        else:
            rgb_valid = None

        if rgb_valid is not None:
            scan['colorRed'] = np.asarray(rgb_valid[:, 0], dtype=np.uint8)
            scan['colorGreen'] = np.asarray(rgb_valid[:, 1], dtype=np.uint8)
            scan['colorBlue'] = np.asarray(rgb_valid[:, 2], dtype=np.uint8)

    return scan


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
    save_exts = ['.e57']

    def __init__(self, path):
        super().__init__()
        self.path = path
        self._worker = None

    @classmethod
    def is_not_static(cls):
        return True

    @classmethod
    def canSaveObject(cls, obj):
        return any(True for _ in _iter_sphere_grids(obj))

    def _on_finished(self, obj):
        self._emit_progress_finished()
        self.loadingFinished.emit(obj)

    def _on_error(self, msg):
        self._emit_progress_finished()
        print(f"B\u0142\u0105d wczytywania E57: {msg}", flush=True)
        self.errorOccurred.emit()

    def on_stop_loading(self):
        if self._worker:
            self._worker.stop()
        self._emit_progress_finished()

    def load_async(self, progressBar=None):
        print(f"parserE57.load_async() dla '{self.path}'", flush=True)
        self._worker = E57LoaderWorker(self.path)
        self._emit_progress_started(0, 100, 0, "Wczytywanie pliku E57")
        self._connect_worker_progress(self._worker)
        self._worker.loadingFinished.connect(self._on_finished)
        self._worker.errorOccurred.connect(self._on_error)
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
    def save(obj, path):
        scans = []
        for grid in _iter_sphere_grids(obj):
            scan = _sphere_grid_to_e57_scan(grid)
            if scan is not None:
                scans.append(scan)

        if not scans:
            print("ParserE57.save: brak SphereGrid do zapisu")
            return False

        npz_fd, npz_path = tempfile.mkstemp(suffix='.npz')
        os.close(npz_fd)
        try:
            arrays = {
                'meta': np.array(json.dumps({
                    'label': getattr(obj, 'label', os.path.basename(path)),
                    'scans': [{'name': scan['name']} for scan in scans],
                }), dtype=object)
            }
            for idx, scan in enumerate(scans):
                prefix = f'scan_{idx}'
                for key, value in scan.items():
                    if key == 'name':
                        continue
                    arrays[f'{prefix}_{key}'] = value

            np.savez_compressed(npz_path, **arrays)

            cmd = [sys.executable, _WORKER_SCRIPT, '--write', npz_path, path]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            if result.returncode != 0:
                print(result.stdout, flush=True)
                print(result.stderr, flush=True)
                return False
            return True
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"ParserE57.save: {e}", flush=True)
            return False
        finally:
            try:
                os.unlink(npz_path)
            except Exception:
                pass

    @staticmethod
    def inPlugin():
        return False

ParserE57.regParser()


