# -*- coding: utf-8 -*-
"""
Konwersje między typami obiektów:
  mesh_to_grid25D(mesh)  – Mesh → GridData64 (jeśli dane tworzą regularny grid 2.5D)
  grid_to_mesh(grid)     – GridData64 → Mesh  (triangulacja)
"""

import numpy as np


def _ensure_running(is_running):
    if is_running is not None and not is_running():
        raise RuntimeError("Przerwano")


def verts_to_grid25D(verts, lateral_tol=1e-3, completeness_threshold=0.5, is_running=None):
    """
    Konwertuje tablicę wierzchołków (N, 3) float na GridData64.
    Zwraca GridData64 lub None jeśli dane nie tworzą regularnego gridu 2.5D.
    """
    from .gridData64 import GridData64

    _ensure_running(is_running)
    verts = np.asarray(verts, dtype=np.float64)
    xs_u = np.unique(np.round(verts[:, 0], 6))
    ys_u = np.unique(np.round(verts[:, 1], 6))

    nx, ny = len(xs_u), len(ys_u)
    if nx < 2 or ny < 2:
        return None

    dx = np.diff(xs_u)
    dy = np.diff(ys_u)
    _ensure_running(is_running)
    stepX = float(np.median(dx))
    stepY = float(np.median(dy))

    if stepX <= 0 or stepY <= 0:
        return None

    frac_x = np.mean(np.abs(dx - stepX) <= stepX * lateral_tol)
    frac_y = np.mean(np.abs(dy - stepY) <= stepY * lateral_tol)
    if frac_x < 0.95 or frac_y < 0.95:
        print(f"[verts→grid] XY nie jest regularną siatką (frac_x={frac_x:.3f}, frac_y={frac_y:.3f})")
        return None

    completeness = len(verts) / (nx * ny)
    if completeness < completeness_threshold:
        print(f"[verts→grid] wypełnienie {completeness:.2f} < {completeness_threshold}")
        return None

    _ensure_running(is_running)
    print(f"[verts→grid] grid {nx}×{ny}, stepX={stepX:.6f}, stepY={stepY:.6f}, "
          f"wypełnienie={completeness:.2f}")

    # buduj grid - np.bincount zamiast pętli Python
    xr = np.round(verts[:, 0], 6)
    yr = np.round(verts[:, 1], 6)
    ix = np.searchsorted(xs_u, xr)
    iy = np.searchsorted(ys_u, yr)
    # ogranicz do prawidłowego zakresu (np. błędy zaokrągleń na krawędziach)
    ix = np.clip(ix, 0, nx - 1)
    iy = np.clip(iy, 0, ny - 1)
    lin = (iy * nx + ix).astype(np.int64)

    z = verts[:, 2].astype(np.float64)
    sums = np.bincount(lin, weights=z, minlength=ny * nx)
    cnts = np.bincount(lin, minlength=ny * nx)
    grid_flat = np.full(ny * nx, np.nan, dtype=np.float64)
    valid = cnts > 0
    grid_flat[valid] = sums[valid] / cnts[valid]
    grid = grid_flat.reshape(ny, nx)

    _ensure_running(is_running)
    g = GridData64(grid, stepX=stepX, stepY=stepY,
                   offsetX=float(xs_u[0]), offsetY=float(ys_u[0]))
    return g


def mesh_to_grid25D(mesh, lateral_tol=1e-3, completeness_threshold=0.5, is_running=None):
    """
    Próbuje przekonwertować Mesh na GridData64.
    Zwraca GridData64 lub None jeśli dane nie są gridem 2.5D.
    """
    verts = np.asarray(mesh.m_vertices, dtype=np.float64)
    g = verts_to_grid25D(verts, lateral_tol=lateral_tol,
                         completeness_threshold=completeness_threshold,
                         is_running=is_running)
    if g is not None:
        g.label = getattr(mesh, 'label', 'grid')
    return g


def grid_to_mesh(grid_obj):
    """
    Trianguluje GridData64 do Mesh.

    Każda komórka (ix, iy) → dwa trójkąty.
    Komórki z NaN są pomijane.

    Zwraca Mesh lub None.
    """
    from .mesh import Mesh

    g64 = np.asarray(grid_obj.m_grid64, dtype=np.float64)
    ny, nx = g64.shape
    stepX = float(grid_obj.stepX)
    stepY = float(grid_obj.stepY)
    offX  = float(grid_obj.offsetX)
    offY  = float(grid_obj.offsetY)

    # buduj tablicę wierzchołków (wszystkie komórki siatki)
    ix_all = np.arange(nx)
    iy_all = np.arange(ny)
    IY, IX = np.meshgrid(iy_all, ix_all, indexing='ij')  # (ny, nx)

    X = offX + IX * stepX
    Y = offY + IY * stepY
    Z = g64

    # liniowy indeks (iy, ix) → vertex index (NaN → -1)
    valid = np.isfinite(Z)
    flat_idx = np.full((ny, nx), -1, dtype=np.int32)
    count = int(valid.sum())
    flat_idx[valid] = np.arange(count, dtype=np.int32)

    verts = np.column_stack([X[valid].ravel(),
                             Y[valid].ravel(),
                             Z[valid].ravel()]).astype(np.float32)

    # trójkąty: każda komórka (iy, ix) gdzie prawdolny jest róg (iy, ix),
    # (iy+1, ix), (iy, ix+1), (iy+1, ix+1)
    faces = []
    for iy in range(ny - 1):
        for ix in range(nx - 1):
            v00 = flat_idx[iy,     ix    ]
            v10 = flat_idx[iy + 1, ix    ]
            v01 = flat_idx[iy,     ix + 1]
            v11 = flat_idx[iy + 1, ix + 1]
            # dolny trójkąt
            if v00 >= 0 and v10 >= 0 and v01 >= 0:
                faces.append([v00, v10, v01])
            # górny trójkąt
            if v10 >= 0 and v11 >= 0 and v01 >= 0:
                faces.append([v10, v11, v01])

    if not faces:
        return None

    mesh = Mesh()
    mesh.label = getattr(grid_obj, 'label', 'mesh')
    mesh.m_vertices = verts
    mesh.m_faces = np.array(faces, dtype=np.uint32)
    mesh.calcVN()
    return mesh
