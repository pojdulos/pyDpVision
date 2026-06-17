#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Standalone worker uruchamiany jako subprocess przez parserE57.
Dziala w osobnym procesie (bez Qt i OpenGL), dzieki czemu nie ma
konfliktu DLL miedzy Xerces-C a sterownikiem GPU.

Uzycie:
    python _e57_subprocess.py <sciezka_e57> <sciezka_wyjsciowa.npz>
    python _e57_subprocess.py --write <wejscie.npz> <wyjscie.e57>
"""

import sys
import os
import json
import numpy as np


def _pose_rotation_matrix(header):
    try:
        if header.has_pose():
            return header.rotation_matrix
    except Exception:
        pass
    return np.eye(3, dtype=np.float64)


def _pose_translation(header):
    try:
        t = header.translation
        if t is not None:
            return [float(t[0]), float(t[1]), float(t[2])]
    except Exception:
        pass
    return [0.0, 0.0, 0.0]


def _log_and_get_pose(header, idx):
    import math

    if not header.has_pose():
        print(f"STATUS:  Skan {idx}: brak pose -> origin=[0,0,0], R=I", flush=True)
        return [0.0, 0.0, 0.0], np.eye(3, dtype=np.float64)

    t = _pose_translation(header)

    R = np.eye(3, dtype=np.float64)
    try:
        R = np.array(header.rotation_matrix, dtype=np.float64)
    except Exception:
        pass

    print(f"STATUS:  Skan {idx} pose:", flush=True)
    print(f"STATUS:    translation = [{t[0]:.6f}, {t[1]:.6f}, {t[2]:.6f}]", flush=True)
    print(f"STATUS:    rotation_matrix =\n"
          f"STATUS:      [{R[0,0]:9.6f}  {R[0,1]:9.6f}  {R[0,2]:9.6f}]\n"
          f"STATUS:      [{R[1,0]:9.6f}  {R[1,1]:9.6f}  {R[1,2]:9.6f}]\n"
          f"STATUS:      [{R[2,0]:9.6f}  {R[2,1]:9.6f}  {R[2,2]:9.6f}]", flush=True)

    sy = math.sqrt(R[0, 0] ** 2 + R[1, 0] ** 2)
    if sy > 1e-6:
        roll = math.degrees(math.atan2(R[2, 1], R[2, 2]))
        pitch = math.degrees(math.atan2(-R[2, 0], sy))
        yaw = math.degrees(math.atan2(R[1, 0], R[0, 0]))
    else:
        roll = math.degrees(math.atan2(-R[1, 2], R[1, 1]))
        pitch = math.degrees(math.atan2(-R[2, 0], sy))
        yaw = 0.0
    print(f"STATUS:    Euler ZYX [deg]: yaw={yaw:.3f}  pitch={pitch:.3f}  roll={roll:.3f}", flush=True)

    try:
        q = header.rotation
        if q is not None:
            qv = [round(float(v), 7) for v in q]
            print(f"STATUS:    quaternion (pye57) = {qv}", flush=True)
    except Exception:
        pass

    return t, R


def _header_float(header, *attrs):
    for name in attrs:
        try:
            val = getattr(header, name)
            if val is not None:
                return float(val)
        except Exception:
            pass
    return None


def _process_cartesian(header, data, prefix, arrays):
    rows = int(header.rowMaximum) + 1
    cols = int(header.columnMaximum) + 1

    print(f"STATUS:  [cart] {rows}x{cols}...", flush=True)

    x = np.asarray(data.pop('cartesianX'), dtype=np.float64)
    y = np.asarray(data.pop('cartesianY'), dtype=np.float64)
    z = np.asarray(data.pop('cartesianZ'), dtype=np.float64)

    row_idx = np.asarray(data.pop('rowIndex', np.arange(len(x)) // cols), dtype=np.int32)
    col_idx = np.asarray(data.pop('columnIndex', np.arange(len(x)) % cols), dtype=np.int32)

    origin = [0.0, 0.0, 0.0]

    dx = x
    dy = y
    dz = z

    r = dx * dx
    r += dy * dy
    r += dz * dz
    np.sqrt(r, out=r)

    xy = np.hypot(dx, dy)
    az = np.degrees(np.arctan2(dy, dx)).astype(np.float32)
    el = np.degrees(np.arctan2(dz, xy)).astype(np.float32)
    del xy, dx, dy, dz

    valid = r > 0
    range_map = np.full((rows, cols), np.nan, dtype=np.float32)
    range_map[row_idx[valid], col_idx[valid]] = r[valid]

    col_fill = np.isfinite(range_map).any(axis=0)
    empty_cols = np.where(~col_fill)[0]
    if len(empty_cols):
        if len(empty_cols) <= 20:
            print(f"STATUS:  [cart] puste kolumny ({len(empty_cols)}): {empty_cols.tolist()}", flush=True)
        else:
            print(f"STATUS:  [cart] puste kolumny: {len(empty_cols)} (pierwsza={empty_cols[0]}, ostatnia={empty_cols[-1]})", flush=True)

    az_min = float(az[valid].min()) if valid.any() else -180.0
    az_max = float(az[valid].max()) if valid.any() else 180.0
    el_min = float(el[valid].min()) if valid.any() else -90.0
    el_max = float(el[valid].max()) if valid.any() else 90.0

    if valid.any():
        row_v = row_idx[valid]
        col_v = col_idx[valid]
        el_v = el[valid].astype(np.float64)
        az_v = az[valid].astype(np.float64)

        el_row_sums = np.bincount(row_v, weights=el_v, minlength=rows)
        el_row_counts = np.bincount(row_v, minlength=rows)
        el_per_row = np.full(rows, np.nan, dtype=np.float32)
        nz = el_row_counts > 0
        el_per_row[nz] = (el_row_sums[nz] / el_row_counts[nz]).astype(np.float32)

        az_col_sums = np.bincount(col_v, weights=az_v, minlength=cols)
        az_col_counts = np.bincount(col_v, minlength=cols)
        az_per_col = np.full(cols, np.nan, dtype=np.float32)
        nz = az_col_counts > 0
        az_per_col[nz] = (az_col_sums[nz] / az_col_counts[nz]).astype(np.float32)

        arrays[f'{prefix}_el_per_row'] = el_per_row
        arrays[f'{prefix}_az_per_col'] = az_per_col

    del az, el, r

    arrays[f'{prefix}_range_map'] = range_map

    meta = {
        'type': 'sphere_grid',
        'rows': rows, 'cols': cols,
        'az_min': az_min, 'az_max': az_max,
        'el_min': el_min, 'el_max': el_max,
        'origin': origin,
        'has_intensity': False,
        'has_rgb': False,
    }

    if 'intensity' in data:
        intens_flat = np.asarray(data.pop('intensity'), dtype=np.float32)
        i_min = _header_float(header, 'intensityMinimum') or float(intens_flat[valid].min() if valid.any() else 0)
        i_max = _header_float(header, 'intensityMaximum') or float(intens_flat[valid].max() if valid.any() else 1)
        if i_max > i_min:
            intens_flat = (intens_flat - i_min) / (i_max - i_min)
        intens_map = np.zeros((rows, cols), dtype=np.float32)
        intens_map[row_idx[valid], col_idx[valid]] = intens_flat[valid]
        arrays[f'{prefix}_intensity'] = intens_map
        meta['has_intensity'] = True

    if 'colorRed' in data and 'colorGreen' in data and 'colorBlue' in data:
        r_ch = np.asarray(data.pop('colorRed'), dtype=np.uint8)
        g_ch = np.asarray(data.pop('colorGreen'), dtype=np.uint8)
        b_ch = np.asarray(data.pop('colorBlue'), dtype=np.uint8)
        rgb_map = np.zeros((rows, cols, 3), dtype=np.uint8)
        rgb_map[row_idx[valid], col_idx[valid], 0] = r_ch[valid]
        rgb_map[row_idx[valid], col_idx[valid], 1] = g_ch[valid]
        rgb_map[row_idx[valid], col_idx[valid], 2] = b_ch[valid]
        arrays[f'{prefix}_rgb'] = rgb_map
        meta['has_rgb'] = True

    del valid, row_idx, col_idx
    return meta


def _process_spherical(header, raw, prefix, arrays):
    rows = int(header.rowMaximum) + 1
    cols = int(header.columnMaximum) + 1

    r_flat = np.asarray(raw['sphericalRange'], dtype=np.float32)
    az_flat = np.asarray(raw['sphericalAzimuth'], dtype=np.float32)
    el_flat = np.asarray(raw['sphericalElevation'], dtype=np.float32)

    row_idx = np.asarray(raw.get('rowIndex', np.arange(len(r_flat)) // cols), dtype=np.int32)
    col_idx = np.asarray(raw.get('columnIndex', np.arange(len(r_flat)) % cols), dtype=np.int32)

    range_map = np.full((rows, cols), np.nan, dtype=np.float32)
    range_map[row_idx, col_idx] = r_flat
    arrays[f'{prefix}_range_map'] = range_map

    az_deg = np.degrees(az_flat)
    el_deg = np.degrees(el_flat)

    el_row_sums = np.bincount(row_idx, weights=el_deg.astype(np.float64), minlength=rows)
    el_row_counts = np.bincount(row_idx, minlength=rows)
    el_per_row = np.full(rows, np.nan, dtype=np.float32)
    nz = el_row_counts > 0
    el_per_row[nz] = (el_row_sums[nz] / el_row_counts[nz]).astype(np.float32)

    az_col_sums = np.bincount(col_idx, weights=az_deg.astype(np.float64), minlength=cols)
    az_col_counts = np.bincount(col_idx, minlength=cols)
    az_per_col = np.full(cols, np.nan, dtype=np.float32)
    nz = az_col_counts > 0
    az_per_col[nz] = (az_col_sums[nz] / az_col_counts[nz]).astype(np.float32)

    arrays[f'{prefix}_el_per_row'] = el_per_row
    arrays[f'{prefix}_az_per_col'] = az_per_col

    meta = {
        'type': 'sphere_grid',
        'rows': rows, 'cols': cols,
        'az_min': float(az_deg.min()), 'az_max': float(az_deg.max()),
        'el_min': float(el_deg.min()), 'el_max': float(el_deg.max()),
        'origin': [0.0, 0.0, 0.0],
        'has_intensity': False,
        'has_rgb': False,
    }

    if 'intensity' in raw:
        intens_flat = np.asarray(raw['intensity'], dtype=np.float32)
        i_min = _header_float(header, 'intensityMinimum') or float(intens_flat.min())
        i_max = _header_float(header, 'intensityMaximum') or float(intens_flat.max())
        if i_max > i_min:
            intens_flat = (intens_flat - i_min) / (i_max - i_min)
        intens_map = np.zeros((rows, cols), dtype=np.float32)
        intens_map[row_idx, col_idx] = intens_flat
        arrays[f'{prefix}_intensity'] = intens_map
        meta['has_intensity'] = True

    if 'colorRed' in raw and 'colorGreen' in raw and 'colorBlue' in raw:
        rgb_map = np.zeros((rows, cols, 3), dtype=np.uint8)
        rgb_map[row_idx, col_idx, 0] = np.asarray(raw['colorRed'], dtype=np.uint8)
        rgb_map[row_idx, col_idx, 1] = np.asarray(raw['colorGreen'], dtype=np.uint8)
        rgb_map[row_idx, col_idx, 2] = np.asarray(raw['colorBlue'], dtype=np.uint8)
        arrays[f'{prefix}_rgb'] = rgb_map
        meta['has_rgb'] = True

    return meta


def _try_load_color_jpg(e57_path, idx, n_scans, rows, cols):
    stem = os.path.splitext(os.path.basename(e57_path))[0]
    dirpath = os.path.dirname(os.path.abspath(e57_path))

    candidates = [
        os.path.join(dirpath, f"{stem}_{idx}_color.jpg"),
        os.path.join(dirpath, f"{stem}_color.jpg"),
    ]

    for path in candidates:
        if not os.path.isfile(path):
            continue
        try:
            from PIL import Image
            img = Image.open(path).convert('RGB')
            w_img, h_img = img.size
            if (w_img == cols and h_img == rows) or (w_img == cols - 1 and h_img == rows - 1):
                if w_img == cols - 1:
                    print(f"STATUS:  Color JPG: rozm. {img.size} = skan-1xskan-1 (piksele miedzy punktami)", flush=True)
            else:
                print(f"STATUS:  Color JPG: resize {img.size} -> ({cols}x{rows})", flush=True)
                img = img.resize((cols, rows), Image.BILINEAR)
            rgb = np.array(img, dtype=np.uint8)
            print(f"STATUS:  Color JPG wczytany: {os.path.basename(path)} {rgb.shape}", flush=True)
            return rgb
        except Exception as exc:
            print(f"STATUS:  Blad wczytywania color JPG {os.path.basename(path)}: {exc}", flush=True)
    return None


def _process_point_cloud(data, origin, prefix, arrays):
    x = np.asarray(data['cartesianX'], dtype=np.float32)
    y = np.asarray(data['cartesianY'], dtype=np.float32)
    z = np.asarray(data['cartesianZ'], dtype=np.float32)
    arrays[f'{prefix}_vertices'] = np.stack([x, y, z], axis=1)

    meta = {'type': 'point_cloud', 'origin': origin, 'has_colors': False}

    if 'colorRed' in data and 'colorGreen' in data and 'colorBlue' in data:
        r_ch = np.asarray(data['colorRed'], dtype=np.uint8)
        g_ch = np.asarray(data['colorGreen'], dtype=np.uint8)
        b_ch = np.asarray(data['colorBlue'], dtype=np.uint8)
        alpha = np.full(len(r_ch), 255, dtype=np.uint8)
        arrays[f'{prefix}_colors'] = np.stack([r_ch, g_ch, b_ch, alpha], axis=1)
        meta['has_colors'] = True
    elif 'intensity' in data:
        intens = np.asarray(data['intensity'], dtype=np.float32)
        i_min, i_max = float(intens.min()), float(intens.max())
        if i_max > i_min:
            intens = (intens - i_min) / (i_max - i_min)
        c = (intens * 255).astype(np.uint8)
        alpha = np.full(len(c), 255, dtype=np.uint8)
        arrays[f'{prefix}_colors'] = np.stack([c, c, c, alpha], axis=1)
        meta['has_colors'] = True

    return meta


def _write_e57_from_npz(npz_path, e57_path):
    import pye57

    data = np.load(npz_path, allow_pickle=True)
    meta = json.loads(str(data['meta']))
    scans = meta.get('scans', [])

    print(f"STATUS:Tworze {os.path.basename(e57_path)}...", flush=True)
    with pye57.E57(e57_path, mode='w') as e57:
        for idx, scan_meta in enumerate(scans):
            prefix = f"scan_{idx}"
            print(f"PROGRESS:{int(idx / max(len(scans), 1) * 100)}", flush=True)
            print(f"STATUS:Zapis skanu {idx+1}/{len(scans)}...", flush=True)

            scan_data = {
                'cartesianX': np.asarray(data[f'{prefix}_cartesianX'], dtype=np.float64),
                'cartesianY': np.asarray(data[f'{prefix}_cartesianY'], dtype=np.float64),
                'cartesianZ': np.asarray(data[f'{prefix}_cartesianZ'], dtype=np.float64),
                'rowIndex': np.asarray(data[f'{prefix}_rowIndex'], dtype=np.uint16),
                'columnIndex': np.asarray(data[f'{prefix}_columnIndex'], dtype=np.uint16),
            }

            if f'{prefix}_intensity' in data:
                scan_data['intensity'] = np.asarray(data[f'{prefix}_intensity'], dtype=np.float32)
            if f'{prefix}_colorRed' in data and f'{prefix}_colorGreen' in data and f'{prefix}_colorBlue' in data:
                scan_data['colorRed'] = np.asarray(data[f'{prefix}_colorRed'], dtype=np.uint8)
                scan_data['colorGreen'] = np.asarray(data[f'{prefix}_colorGreen'], dtype=np.uint8)
                scan_data['colorBlue'] = np.asarray(data[f'{prefix}_colorBlue'], dtype=np.uint8)

            e57.write_scan_raw(scan_data, name=scan_meta.get('name', f'Scan {idx}'))

    print("PROGRESS:100", flush=True)
    print("DONE", flush=True)


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == '--write':
        if len(sys.argv) < 4:
            print("ERROR:Uzycie: _e57_subprocess.py --write <wejscie.npz> <wyjscie.e57>", flush=True)
            sys.exit(1)
        try:
            _write_e57_from_npz(sys.argv[2], sys.argv[3])
            return
        except Exception as exc:
            import traceback
            traceback.print_exc()
            print(f"ERROR:{exc}", flush=True)
            sys.exit(1)

    if len(sys.argv) < 3:
        print("ERROR:Uzycie: _e57_subprocess.py <plik.e57> <wyjscie.npz>", flush=True)
        sys.exit(1)

    e57_path = sys.argv[1]
    npz_path = sys.argv[2]

    import pye57

    print(f"STATUS:Otwieram {os.path.basename(e57_path)}...", flush=True)
    e57 = pye57.E57(e57_path)
    n_scans = e57.scan_count
    print(f"STATUS:{n_scans} skan(ow)", flush=True)

    arrays = {}
    scan_metas = []
    scan_labels = []

    for idx in range(n_scans):
        print(f"PROGRESS:{int(idx / n_scans * 90)}", flush=True)
        print(f"STATUS:Skan {idx+1}/{n_scans}...", flush=True)

        header = e57.get_header(idx)
        prefix = f"scan_{idx}"

        t_pose, R_pose = _log_and_get_pose(header, idx)

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

        scan_label = f"{os.path.basename(e57_path)} - skan {idx}"
        meta = None

        if is_structured:
            try:
                if coord_sys == 'spherical':
                    raw = e57.read_scan_raw(idx)
                    if 'sphericalRange' in raw and 'sphericalAzimuth' in raw:
                        meta = _process_spherical(header, raw, prefix, arrays)
                    else:
                        data = e57.read_scan(idx, intensity=True, colors=True,
                                             row_column=True, transform=False,
                                             ignore_missing_fields=True)
                        meta = _process_cartesian(header, data, prefix, arrays)
                else:
                    data = e57.read_scan(idx, intensity=True, colors=True,
                                         row_column=True, transform=False,
                                         ignore_missing_fields=True)
                    meta = _process_cartesian(header, data, prefix, arrays)
            except Exception as exc:
                import traceback
                traceback.print_exc()
                print(f"STATUS:  Skan {idx}: blad SphereGrid, fallback PointCloud: {exc}", flush=True)
                meta = None

        if meta is None:
            try:
                data = e57.read_scan(idx, intensity=True, colors=True,
                                     transform=False, ignore_missing_fields=True)
                meta = _process_point_cloud(data, [0.0, 0.0, 0.0], prefix, arrays)
            except Exception as exc:
                import traceback
                traceback.print_exc()
                print(f"STATUS:  Skan {idx}: nieudany: {exc}", flush=True)
                meta = {'type': 'failed'}

        if meta is not None and meta.get('type') != 'failed':
            pose_4x4 = np.eye(4, dtype=np.float64)
            pose_4x4[:3, :3] = R_pose
            pose_4x4[:3, 3] = t_pose
            meta['pose_matrix'] = pose_4x4.flatten().tolist()

        if meta is not None and meta.get('type') == 'sphere_grid':
            rows_m = meta['rows']
            cols_m = meta['cols']
            jpg_rgb = _try_load_color_jpg(e57_path, idx, n_scans, rows_m, cols_m)
            if jpg_rgb is not None:
                arrays[f'{prefix}_rgb'] = jpg_rgb
                meta['has_rgb'] = True

        scan_metas.append(meta)
        scan_labels.append(scan_label)

    e57.close()

    root_meta = {
        'label': os.path.basename(e57_path),
        'scans': scan_metas,
        'labels': scan_labels,
    }

    print("STATUS:Zapisuje wyniki...", flush=True)
    np.savez_compressed(
        npz_path,
        meta=np.array(json.dumps(root_meta), dtype=object),
        **arrays
    )

    print("PROGRESS:100", flush=True)
    print("DONE", flush=True)


if __name__ == '__main__':
    main()
