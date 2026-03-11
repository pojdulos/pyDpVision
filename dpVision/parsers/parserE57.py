# -*- coding: utf-8 -*-
"""
Parser plików E57 (ASTM E2807).

Obsługuje dwa tryby:
  1. Skany *ustrukturyzowane* (rowIndex / columnIndex) → SphereGrid
     a. dane sferyczne w pliku   (sphericalRange / …Azimuth / …Elevation)
     b. dane kartezjańskie       (cartesianX/Y/Z) — przeliczane na r, az, el
  2. Skany *nieustrukturyzowane*                   → PointCloud

Jeśli plik zawiera wiele skanów, każdy dostaje swojego Transforma
i wszystkie są pakowane do wspólnego Transforma-korzenia.
"""

import os
import numpy as np
import threading
import faulthandler
faulthandler.enable()

try:
    import pye57
except ImportError:
    pye57 = None

from PyQt5.QtCore import QObject, pyqtSignal
from .. import Parser, Transform, BaseObject
from ..pointCloud import PointCloud
from ..sphereGrid import SphereGrid


# ---------------------------------------------------------------------------
# Pomocnicze funkcje budujące obiekty
# ---------------------------------------------------------------------------

def _header_float(header, *attrs):
    """Pobiera float z ScanHeader; zwraca None jeśli atrybut niedostępny."""
    for name in attrs:
        try:
            val = getattr(header, name)
            if val is not None:
                return float(val)
        except Exception:
            pass
    return None


def _build_sphere_grid_spherical(header, raw):
    """
    Buduje SphereGrid z surowych danych sferycznych E57.
    raw: dict z kluczami sphericalRange, sphericalAzimuth, sphericalElevation
    """
    rows = int(header.rowMaximum) + 1
    cols = int(header.columnMaximum) + 1

    r_flat   = np.asarray(raw['sphericalRange'],     dtype=np.float32)
    az_flat  = np.asarray(raw['sphericalAzimuth'],   dtype=np.float32)  # [rad]
    el_flat  = np.asarray(raw['sphericalElevation'], dtype=np.float32)  # [rad]

    row_idx = np.asarray(raw.get('rowIndex',    np.arange(len(r_flat)) // cols), dtype=int)
    col_idx = np.asarray(raw.get('columnIndex', np.arange(len(r_flat)) %  cols), dtype=int)

    range_map = np.full((rows, cols), np.nan, dtype=np.float32)
    range_map[row_idx, col_idx] = r_flat

    # Zakresy kątowe [°] — z danych, nie z headera (bardziej wiarygodne)
    az_deg = np.degrees(az_flat)
    el_deg = np.degrees(el_flat)
    az_min, az_max = float(az_deg.min()), float(az_deg.max())
    el_min, el_max = float(el_deg.min()), float(el_deg.max())

    # Intensywność
    intens = None
    if 'intensity' in raw:
        intens_flat = np.asarray(raw['intensity'], dtype=np.float32)
        i_min = _header_float(header, 'intensityMinimum') or float(intens_flat.min())
        i_max = _header_float(header, 'intensityMaximum') or float(intens_flat.max())
        if i_max > i_min:
            intens_flat = (intens_flat - i_min) / (i_max - i_min)
        intens_map = np.zeros((rows, cols), dtype=np.float32)
        intens_map[row_idx, col_idx] = intens_flat
        intens = intens_map

    # RGB
    rgb = None
    if 'colorRed' in raw and 'colorGreen' in raw and 'colorBlue' in raw:
        r_ch = np.asarray(raw['colorRed'],   dtype=np.uint8)
        g_ch = np.asarray(raw['colorGreen'], dtype=np.uint8)
        b_ch = np.asarray(raw['colorBlue'],  dtype=np.uint8)
        rgb_map = np.zeros((rows, cols, 3), dtype=np.uint8)
        rgb_map[row_idx, col_idx, 0] = r_ch
        rgb_map[row_idx, col_idx, 1] = g_ch
        rgb_map[row_idx, col_idx, 2] = b_ch
        rgb = rgb_map

    # Pozycja skanera z pose
    origin = _pose_translation(header)

    return SphereGrid(
        range_map,
        azimuth_range=(az_min, az_max),
        elevation_range=(el_min, el_max),
        intensity=intens,
        rgb=rgb,
        origin=origin,
        unit="m",
    )


def _build_sphere_grid_cartesian(header, data):
    """
    Buduje SphereGrid z kartezjańskich danych ustrukturyzowanego skanu.
    data: dict z read_scan(..., row_column=True)

    Używa float32 przez cały czas i zwalnia tablice pośrednie, żeby
    nie przekraczać ~1 GB RAM przy skanach rzędu 40–50M punktów.
    """
    rows = int(header.rowMaximum) + 1
    cols = int(header.columnMaximum) + 1
    n_pts = rows * cols
    print(f"    [cart] siatka {rows}\u00d7{cols} = {n_pts:,} punkt\u00f3w (~{n_pts*4*3//1024//1024} MB float32 x3)", flush=True)

    # float32 — o połowę mniej RAM niż float64 (356 MB → 178 MB na tablicę)
    print("    [cart] wczytuję X...", flush=True)
    x = np.asarray(data.pop('cartesianX'), dtype=np.float32)
    print("    [cart] wczytuję Y...", flush=True)
    y = np.asarray(data.pop('cartesianY'), dtype=np.float32)
    print("    [cart] wczytuję Z...", flush=True)
    z = np.asarray(data.pop('cartesianZ'), dtype=np.float32)
    print(f"    [cart] XYZ gotowe, shape={x.shape}", flush=True)

    print("    [cart] row/col idx...", flush=True)
    row_idx = np.asarray(data.pop('rowIndex',    np.arange(len(x)) // cols), dtype=np.int32)
    col_idx = np.asarray(data.pop('columnIndex', np.arange(len(x)) %  cols), dtype=np.int32)
    print(f"    [cart] idx gotowe, rowIdx range=({row_idx.min()},{row_idx.max()}) colIdx range=({col_idx.min()},{col_idx.max()})", flush=True)

    origin = _pose_translation(header)
    print(f"    [cart] origin={origin}", flush=True)
    x -= origin[0]; y -= origin[1]; z -= origin[2]

    print("    [cart] obliczam r...", flush=True)
    # r bez zbędnych tablic pośrednich — nadpisujemy x w miejscu jako r²
    r = x * x
    r += y * y
    r += z * z
    np.sqrt(r, out=r)
    print(f"    [cart] r gotowe, range=({float(r.min()):.2f}, {float(r.max()):.2f})", flush=True)

    print("    [cart] obliczam az, el...", flush=True)
    # az, el — nadal potrzebujemy x, y, z
    xy = np.hypot(x, y)
    az = np.degrees(np.arctan2(y, x)).astype(np.float32)
    el = np.degrees(np.arctan2(z, xy)).astype(np.float32)
    del xy, x, y, z
    print(f"    [cart] az=({float(az.min()):.1f},{float(az.max()):.1f}) el=({float(el.min()):.1f},{float(el.max()):.1f})", flush=True)

    print("    [cart] wypełniam range_map...", flush=True)
    valid = r > 0
    print(f"    [cart] valid points: {int(valid.sum()):,} / {len(r):,}", flush=True)
    range_map = np.full((rows, cols), np.nan, dtype=np.float32)
    range_map[row_idx[valid], col_idx[valid]] = r[valid]

    az_min = float(az[valid].min()) if valid.any() else -180.0
    az_max = float(az[valid].max()) if valid.any() else  180.0
    el_min = float(el[valid].min()) if valid.any() else  -90.0
    el_max = float(el[valid].max()) if valid.any() else   90.0
    del az, el, r
    print(f"    [cart] range_map gotowe: az=({az_min:.1f},{az_max:.1f}) el=({el_min:.1f},{el_max:.1f})", flush=True)

    # Intensywność
    intens = None
    if 'intensity' in data:
        print("    [cart] intensywność...", flush=True)
        intens_flat = np.asarray(data.pop('intensity'), dtype=np.float32)
        i_min = _header_float(header, 'intensityMinimum') or float(intens_flat[valid].min() if valid.any() else 0)
        i_max = _header_float(header, 'intensityMaximum') or float(intens_flat[valid].max() if valid.any() else 1)
        if i_max > i_min:
            intens_flat = (intens_flat - i_min) / (i_max - i_min)
        intens_map = np.zeros((rows, cols), dtype=np.float32)
        intens_map[row_idx[valid], col_idx[valid]] = intens_flat[valid]
        del intens_flat
        intens = intens_map
        print("    [cart] intensywność gotowa", flush=True)

    # RGB
    rgb = None
    if 'colorRed' in data and 'colorGreen' in data and 'colorBlue' in data:
        print("    [cart] kolory RGB...", flush=True)
        r_ch = np.asarray(data.pop('colorRed'),   dtype=np.uint8)
        g_ch = np.asarray(data.pop('colorGreen'), dtype=np.uint8)
        b_ch = np.asarray(data.pop('colorBlue'),  dtype=np.uint8)
        rgb_map = np.zeros((rows, cols, 3), dtype=np.uint8)
        rgb_map[row_idx[valid], col_idx[valid], 0] = r_ch[valid]
        rgb_map[row_idx[valid], col_idx[valid], 1] = g_ch[valid]
        rgb_map[row_idx[valid], col_idx[valid], 2] = b_ch[valid]
        del r_ch, g_ch, b_ch
        rgb = rgb_map
        print("    [cart] RGB gotowe", flush=True)

    del valid, row_idx, col_idx
    print("    [cart] tworzę SphereGrid...", flush=True)

    return SphereGrid(
        range_map,
        azimuth_range=(az_min, az_max),
        elevation_range=(el_min, el_max),
        intensity=intens,
        rgb=rgb,
        origin=origin,
        unit="m",
    )


def _build_point_cloud(data, origin=(0.0, 0.0, 0.0)):
    """Buduje PointCloud z nieustrukturyzowanego skanu E57."""
    x = np.asarray(data['cartesianX'], dtype=np.float32)
    y = np.asarray(data['cartesianY'], dtype=np.float32)
    z = np.asarray(data['cartesianZ'], dtype=np.float32)

    pc = PointCloud()
    pc.m_vertices = np.stack([x, y, z], axis=1)

    if 'colorRed' in data and 'colorGreen' in data and 'colorBlue' in data:
        r_ch = np.asarray(data['colorRed'],   dtype=np.uint8)
        g_ch = np.asarray(data['colorGreen'], dtype=np.uint8)
        b_ch = np.asarray(data['colorBlue'],  dtype=np.uint8)
        alpha = np.full(len(r_ch), 255, dtype=np.uint8)
        pc.m_vcolors = np.stack([r_ch, g_ch, b_ch, alpha], axis=1)
    elif 'intensity' in data:
        intens = np.asarray(data['intensity'], dtype=np.float32)
        i_min, i_max = float(intens.min()), float(intens.max())
        if i_max > i_min:
            intens = (intens - i_min) / (i_max - i_min)
        c = (intens * 255).astype(np.uint8)
        alpha = np.full(len(c), 255, dtype=np.uint8)
        pc.m_vcolors = np.stack([c, c, c, alpha], axis=1)

    return pc


def _pose_translation(header):
    """Zwraca wektor translacji z pose headera (lub [0,0,0])."""
    try:
        t = header.translation
        if t is not None:
            return np.array([float(t[0]), float(t[1]), float(t[2])], dtype=np.float32)
    except Exception:
        pass
    return np.zeros(3, dtype=np.float32)


# ---------------------------------------------------------------------------
# Główna funkcja parsowania
# ---------------------------------------------------------------------------

def _load_e57(e57_or_path, progress_cb=None, status_cb=None):
    """
    Wczytuje plik E57 i zwraca BaseObject.
    e57_or_path: już otwarty obiekt pye57.E57 LUB ścieżka (sync fallback).
    """
    if isinstance(e57_or_path, str):
        # Tryb synchroniczny — otwieramy sami (musimy być na głównym wątku)
        if pye57 is None:
            raise ImportError(
                "Wymagana biblioteka pye57 nie jest zainstalowana. "
                "Uruchom: pip install pye57"
            )
        path = e57_or_path
        print(f"[E57] pye57.E57('{path}') ...", flush=True)
        e57 = pye57.E57(path)
        print("[E57] plik otwarty", flush=True)
    else:
        # Tryb async — plik już otwarty na głównym wątku
        e57 = e57_or_path
        path = e57.path

    label = os.path.basename(path)
    n_scans = e57.scan_count
    print(f"E57: '{label}' \u2014 {n_scans} skan(\u00f3w)", flush=True)

    root = Transform()
    root.label = label

    for idx in range(n_scans):
        if progress_cb:
            progress_cb(int(idx / n_scans * 90))
        if status_cb:
            status_cb(f"Wczytuję skan {idx + 1}/{n_scans}…")

        header = e57.get_header(idx)
        scan_label = f"{label} – skan {idx}"

        # Sprawdź czy skan jest ustrukturyzowany (ma siatkę wierszy × kolumn)
        is_structured = False
        rows = cols = 0
        try:
            rows = int(header.rowMaximum) + 1
            cols = int(header.columnMaximum) + 1
            is_structured = rows > 1 and cols > 1
        except Exception:
            pass

        coord_sys = 'cartesian'
        try:
            coord_sys = header.get_coordinate_system()
        except Exception:
            pass

        obj = None

        if is_structured:
            print(f"  Skan {idx}: ustrukturyzowany {rows}×{cols}, układ: {coord_sys}", flush=True)
            try:
                if coord_sys == 'spherical':
                    # Próbuj raw (szybsze, oryginalne dane sferyczne)
                    raw = e57.read_scan_raw(idx)
                    if 'sphericalRange' in raw and 'sphericalAzimuth' in raw:
                        obj = _build_sphere_grid_spherical(header, raw)
                    else:
                        # fallback: skonwertuj kartezjańskie read_scan
                        data = e57.read_scan(
                            idx, intensity=True, colors=True,
                            row_column=True, ignore_missing_fields=True
                        )
                        obj = _build_sphere_grid_cartesian(header, data)
                else:
                    data = e57.read_scan(
                        idx, intensity=True, colors=True,
                        row_column=True, ignore_missing_fields=True
                    )
                    print(f"    read_scan gotowe, klucze: {list(data.keys())}", flush=True)
                    obj = _build_sphere_grid_cartesian(header, data)
                    del data
            except Exception as e:
                print(f"  Błąd budowania SphereGrid (skan {idx}), fallback → PointCloud: {e}", flush=True)
                import traceback; traceback.print_exc()
                obj = None

        if obj is None:
            # Nieustrukturyzowany lub błąd powyżej → PointCloud
            print(f"  Skan {idx}: nieustrukturyzowany → PointCloud", flush=True)
            try:
                data = e57.read_scan(
                    idx, intensity=True, colors=True,
                    transform=True, ignore_missing_fields=True
                )
                obj = _build_point_cloud(data, _pose_translation(header))
            except Exception as e:
                print(f"  Nie udało się wczytać skanu {idx}: {e}", flush=True)
                continue

        obj.label = scan_label
        print(f"  Skan {idx}: obj={obj!r}", flush=True)
        root.addChild(obj)

    e57.close()

    if progress_cb:
        progress_cb(100)
    if status_cb:
        status_cb("Gotowe!")

    # Jeśli tylko jeden skan — zwróć bezpośrednio transform z dzieckiem
    return root


# ---------------------------------------------------------------------------
# Worker (async — Python threading, nie QThread)
# ---------------------------------------------------------------------------

class E57LoaderWorker(QObject):
    progressChanged = pyqtSignal(int)
    statusChanged   = pyqtSignal(str)
    loadingFinished = pyqtSignal(object)
    errorOccurred   = pyqtSignal(str)

    def __init__(self, e57):
        super().__init__()
        self._e57 = e57
        self._is_running = True
        self._thread = None

    def stop(self):
        self._is_running = False

    def start(self):
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()

    def run(self):
        print("[E57 worker] run() start", flush=True)
        try:
            obj = _load_e57(
                self._e57,
                progress_cb=self.progressChanged.emit,
                status_cb=self.statusChanged.emit,
            )
            self.loadingFinished.emit(obj)
        except Exception as e:
            import traceback; traceback.print_exc()
            self.errorOccurred.emit(str(e))


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
        # pye57.E57() otwieramy tutaj — na głównym wątku Qt
        print(f"[E57] pye57.E57('{self.path}') ...", flush=True)
        e57 = pye57.E57(self.path)
        print("[E57] plik otwarty", flush=True)
        self._worker = E57LoaderWorker(e57)
        self._worker.loadingFinished.connect(self._on_finished)
        self._worker.errorOccurred.connect(self._on_error)
        if progressBar is not None:
            self._worker.progressChanged.connect(progressBar.setValue)
        self._worker.start()

    @staticmethod
    def load(path):
        print(f"parserE57.load() dla '{path}'", flush=True)
        try:
            return _load_e57(path)
        except Exception as e:
            import traceback; traceback.print_exc()
            print(f"B\u0142\u0105d wczytywania E57: {e}", flush=True)
            return None

    @staticmethod
    def inPlugin():
        return False

ParserE57.regParser()
