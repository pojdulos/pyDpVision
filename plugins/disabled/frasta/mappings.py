
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from dpVision import GridData64
from dpVision.annotationPlane import AnnotationPlane

import numpy as np

from scipy.ndimage import gaussian_filter
from scipy.ndimage import map_coordinates


def resample_grids_to_plane(ref_grid: GridData64, adj_grid: GridData64,
							ref_plane: AnnotationPlane, T_final: np.ndarray,
							stepX=None, stepY=None,
							mode="bilinear", max_dist=None):
	"""
	Przekształca oba gridy do wspólnego układu ref_plane i zwraca:
	- ref_in_plane : GridData64 (ref_grid w układzie płaszczyzny)
	- adj_in_plane : GridData64 (adj_grid w układzie płaszczyzny po T_final)
	- dist_map     : GridData64 (różnica ref - adj w układzie płaszczyzny)
	"""

	# --- 1. baza układu: ref_plane ---
	c = np.array(ref_plane.m_center, dtype=float)  # centroid
	n = np.array(ref_plane.m_normal, dtype=float)  # normalna (unit)
	n /= np.linalg.norm(n)

	# znajdź wektory u,v w płaszczyźnie
	tmp = np.array([1, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1, 0])
	u = np.cross(n, tmp); u /= np.linalg.norm(u)
	v = np.cross(n, u)

	# macierz świat→płaszczyzna
	R = np.stack([u, v, n], axis=1)  # 3x3
	T_world_to_plane = np.eye(4)
	T_world_to_plane[:3, :3] = R.T
	T_world_to_plane[:3, 3] = -R.T @ c

	# --- 2. bounding box w układzie płaszczyzny ---
	def project_bbox(grid, T_extra=None):
		h, w = grid.m_grid64.shape
		xs = grid.offsetX + np.arange(w) * grid.stepX
		ys = grid.offsetY + np.arange(h) * grid.stepY
		X, Y = np.meshgrid(xs, ys)
		Z = grid.m_grid64
		pts = np.stack([X.ravel(), Y.ravel(), Z.ravel(), np.ones_like(Z).ravel()], axis=1)

		T_total = T_world_to_plane
		if T_extra is not None:
			# UWAGA: zakładamy, że T_final: adj_local -> ref_world
			T_total = T_world_to_plane @ T_extra

		pts_plane = (T_total @ pts.T).T
		return pts_plane[:, 0], pts_plane[:, 1]

	x_ref, y_ref = project_bbox(ref_grid)
	x_adj, y_adj = project_bbox(adj_grid, T_extra=T_final)

	x_all = np.hstack([x_ref, x_adj])
	y_all = np.hstack([y_ref, y_adj])

	xmin, xmax = np.nanmin(x_all), np.nanmax(x_all)
	ymin, ymax = np.nanmin(y_all), np.nanmax(y_all)

	if stepX is None: stepX = ref_grid.stepX
	if stepY is None: stepY = ref_grid.stepY

	w = int(np.ceil((xmax - xmin) / stepX))
	h = int(np.ceil((ymax - ymin) / stepY))

	xs = xmin + np.arange(w) * stepX
	ys = ymin + np.arange(h) * stepY
	Xp, Yp = np.meshgrid(xs, ys)

	# --- 3. funkcja pomocnicza: próbkowanie siatki ---
	def sample_grid(grid, T_extra=None):
		# punkty w układzie płaszczyzny (Z=0)
		pts_plane = np.stack([Xp.ravel(), Yp.ravel(),
							np.zeros_like(Xp).ravel(),
							np.ones(Xp.size)], axis=1)

		# płaszczyzna -> świat(ref)
		T_plane_to_world = np.linalg.inv(T_world_to_plane)

		# dla adj_grid: płaszczyzna -> świat(ref) -> lokalny adj  (czyli inv(T_final))
		if T_extra is not None:
			T_world_ref_to_adj_local = np.linalg.inv(T_extra)
			T_for_sampling = T_world_ref_to_adj_local @ T_plane_to_world
		else:
			# dla ref_grid: płaszczyzna -> świat(ref) == lokalny ref
			T_for_sampling = T_plane_to_world

		# współrzędne XY w lokalnym układzie danej siatki (na płaszczyźnie Z=0)
		pts_local_on_plane = (T_for_sampling @ pts_plane.T).T
		x_loc = pts_local_on_plane[:, 0]
		y_loc = pts_local_on_plane[:, 1]

		# zamiana na indeksy w rastrze siatki
		gx = (x_loc - grid.offsetX) / grid.stepX
		gy = (y_loc - grid.offsetY) / grid.stepY

		coords = np.vstack([gy, gx])
		z_local = map_coordinates(
			grid.m_grid64, coords,
			order=(1 if mode == "bilinear" else 0),
			mode='nearest'
		).reshape(h, w)

		# złożenie pełnych punktów lokalnych na powierzchni
		pts_local_surface = np.stack(
			[x_loc.reshape(h, w), y_loc.reshape(h, w), z_local, np.ones((h, w))],
			axis=-1
		).reshape(-1, 4)

		# lokalny -> świat(ref)
		if T_extra is not None:
			pts_world_surface = (T_extra @ pts_local_surface.T).T
		else:
			# ref_grid jest już w świecie referencyjnym
			pts_world_surface = pts_local_surface

		# świat(ref) -> układ płaszczyzny
		pts_plane_surface = (T_world_to_plane @ pts_world_surface.T).T

		# wysokość NAD PŁASZCZYZNĄ (to chcemy zwrócić)
		Zs_plane = pts_plane_surface[:, 2].reshape(h, w)
		return Zs_plane

	# --- 4. przekształcamy obie siatki ---
	ref_in_plane = sample_grid(ref_grid)
	adj_in_plane = sample_grid(adj_grid, T_extra=T_final)

	# --- 5. liczymy mapę różnic ---
	dist = ref_in_plane - adj_in_plane
	if max_dist is not None:
		mask = np.abs(dist) > max_dist
		dist[mask] = np.nan

	# --- 6. wrap w GridData64 z offsetami ---
	ref_grid_out = GridData64(ref_in_plane, stepX=stepX, stepY=stepY,
							offsetX=xmin, offsetY=ymin)
	adj_grid_out = GridData64(adj_in_plane, stepX=stepX, stepY=stepY,
							offsetX=xmin, offsetY=ymin)
	dist_grid_out = GridData64(dist, stepX=stepX, stepY=stepY,
							offsetX=xmin, offsetY=ymin)

	return ref_grid_out, adj_grid_out, dist_grid_out


def build_T_ref(pC_ref, n_ref):
	"""
	Buduje macierz transformacji 4x4, która ustawia płaszczyznę referencyjną:
	- normalna n_ref idzie w [0,0,1]
	- punkt pC_ref idzie w [0,0,0]
	"""
	n = np.array(n_ref, dtype=float)
	n /= np.linalg.norm(n)

	# wybierz wektor pomocniczy (unikaj równoległości)
	tmp = np.array([0, 0, 1]) if abs(n[2]) < 0.9 else np.array([1, 0, 0])

	u = np.cross(tmp, n); u /= np.linalg.norm(u)
	v = np.cross(n, u)

	R = np.stack([u, v, n], axis=1)  # kolumny: u,v,n

	T = np.eye(4)
	T[:3,:3] = R.T     # rotacja odwrotna – sprowadza n → [0,0,1]
	T[:3, 3] = -R.T @ np.array(pC_ref, dtype=float)
	return T

def apply_transform_to_grid(grid, T, ref_grid=None):
	"""
	Przekształca GridData64 macierzą 4x4 (T).
	Jeśli podano ref_grid, wynik jest próbkowany tak,
	aby mieć ten sam rozmiar i kroki co ref_grid.
	"""
	h, w = grid.m_grid64.shape
	sx, sy, sz = grid.stepX, grid.stepY, 1.0

	# współrzędne w oryginalnym gridzie
	xs = grid.offsetX + np.arange(w) * sx
	ys = grid.offsetY + np.arange(h) * sy
	X, Y = np.meshgrid(xs, ys)
	Z = grid.m_grid64

	pts = np.stack([X.ravel(), Y.ravel(), Z.ravel(), np.ones_like(Z).ravel()], axis=1)
	pts_t = (T @ pts.T).T
	xt, yt, zt = pts_t[:,0], pts_t[:,1], pts_t[:,2]

	if ref_grid is not None:
		# raster docelowy wg ref_grid
		h2, w2 = ref_grid.m_grid64.shape
		sx2, sy2 = ref_grid.stepX, ref_grid.stepY
		xs2 = ref_grid.offsetX + np.arange(w2) * sx2
		ys2 = ref_grid.offsetY + np.arange(h2) * sy2
		X2, Y2 = np.meshgrid(xs2, ys2)

		# map_coordinates potrzebuje współrzędnych w indeksach (y,x)
		gx = (xt - xs2[0]) / sx2
		gy = (yt - ys2[0]) / sy2

		coords = np.vstack([gy, gx])
		Zt = map_coordinates(Z, coords, order=1, mode='nearest').reshape(h, w)

		return GridData64(Zt, stepX=sx2, stepY=sy2,
						offsetX=ref_grid.offsetX, offsetY=ref_grid.offsetY)
	else:
		# zwróć tylko chmurę punktów
		return np.stack([xt, yt, zt], axis=1)

def transform_grids_to_ref_plane(ref_grid, adj_grid, ref_plane, T_final):
	"""
	Zwraca grid1_in_map i grid2_in_map – obie siatki przekształcone do układu ref_plane
	i docięte do wspólnego obszaru.
	"""
	pC_ref = ref_plane.m_center
	n_ref = ref_plane.m_normal
	T_ref = build_T_ref(pC_ref, n_ref)

	# ref_grid do układu ref_plane
	grid1_in_map = apply_transform_to_grid(ref_grid, T_ref)

	# adj_grid do układu ref_plane, przez T_final
	grid2_in_map = apply_transform_to_grid(adj_grid, T_ref @ T_final, ref_grid=grid1_in_map)

	return grid1_in_map, grid2_in_map




def preprocess_for_registration(H, sigma_px=3.0, bandpass=None):
	"""
	H – mapa reszt (po odjęciu płaszczyzny), z NaN.
	sigma_px – sigma Gaussa do łagodnego wygładzenia.
	bandpass – None albo (sigma_lo, sigma_hi) w px; DoG = G(σ_hi) - G(σ_lo).
	"""
	A = np.array(H, dtype=float)
	# NaNy -> 0 do konwolucji + maska korygująca (normalized convolution)
	M = np.isfinite(A).astype(float)
	A = np.nan_to_num(A, nan=0.0)
	if bandpass:
		σlo, σhi = bandpass
		num_hi = gaussian_filter(A, σhi)
		den_hi = gaussian_filter(M, σhi) + 1e-12
		H_hi = num_hi / den_hi
		num_lo = gaussian_filter(A, σlo)
		den_lo = gaussian_filter(M, σlo) + 1e-12
		H_lo = num_lo / den_lo
		Hf = H_hi - H_lo
	else:
		num = gaussian_filter(A, sigma_px)
		den = gaussian_filter(M, sigma_px) + 1e-12
		Hf = num / den
	return Hf


def make_distance_map_fast(grid1: GridData64, grid2: GridData64, transform: np.ndarray,
						mode="bilinear", max_dist=None) -> GridData64:
	h, w = grid1.h, grid1.w
	stepX, stepY = grid1.stepX, grid1.stepY

	# współrzędne w grid1
	xs = grid1.offsetX + np.arange(w) * stepX
	ys = grid1.offsetY + np.arange(h) * stepY
	X, Y = np.meshgrid(xs, ys)

	Z = grid1.m_grid64

	transform = np.linalg.inv(transform)
	
	# flatten
	pts = np.stack([X.ravel(), Y.ravel(), Z.ravel(), np.ones_like(Z).ravel()], axis=1)
	pts_t = (transform @ pts.T).T  # (N,4)

	px, py, pz = pts_t[:,0], pts_t[:,1], pts_t[:,2]

	# współrzędne w grid2
	gx = (px - grid2.offsetX) / grid2.stepX
	gy = (py - grid2.offsetY) / grid2.stepY

	valid = (
		np.isfinite(pz) &
		(gx >= 0) & (gy >= 0) &
		(gx < grid2.w-1) & (gy < grid2.h-1)
	)

	gx, gy, pz = gx[valid], gy[valid], pz[valid]
	ix, iy = np.floor(gx).astype(int), np.floor(gy).astype(int)
	dx, dy = gx - ix, gy - iy

	if mode == "nearest":
		z_interp = grid2.m_grid64[iy, ix]
	else:  # bilinear
		z11 = grid2.m_grid64[iy, ix]
		z21 = grid2.m_grid64[iy, ix+1]
		z12 = grid2.m_grid64[iy+1, ix]
		z22 = grid2.m_grid64[iy+1, ix+1]
		z_interp = (
			z11*(1-dx)*(1-dy) +
			z21*dx*(1-dy) +
			z12*(1-dx)*dy +
			z22*dx*dy
		)

	dist = np.full(Z.shape, np.nan, dtype=np.float64)
	dist.ravel()[valid] = pz - z_interp

	# --- ograniczenie maksymalnej odległości ---
	if max_dist is not None:
		mask = np.abs(dist) > max_dist
		# mask = (dist <= 0) # max_dist
		dist[mask] = np.nan   # albo np.clip(dist, -max_dist, max_dist) jeśli chcesz "przyciąć"

	return GridData64(dist, stepX=stepX, stepY=stepY)


def make_distance_map_plane(grid1: GridData64, grid2: GridData64, transform: np.ndarray,
							plane_abc, mode="bilinear", max_dist=None) -> GridData64:
	"""
	Odległość grid1->grid2 liczona wzdłuż normalnej płaszczyzny dopasowanej do grid2.
	plane_abc -- [a, b, c] z RANSAC (w jednostkach świata, mm)
	"""

	h, w = grid1.h, grid1.w
	stepX, stepY = grid1.stepX, grid1.stepY

	xs = grid1.offsetX + np.arange(w) * stepX
	ys = grid1.offsetY + np.arange(h) * stepY

	X, Y = np.meshgrid(xs, ys)
	Z = grid1.m_grid64

	transform = np.linalg.inv(transform)

	pts = np.stack([X.ravel(), Y.ravel(), Z.ravel(), np.ones_like(Z).ravel()], axis=1)
	pts_t = (transform @ pts.T).T
	px, py, pz = pts_t[:,0], pts_t[:,1], pts_t[:,2]

	gx = (px - grid2.offsetX) / grid2.stepX
	gy = (py - grid2.offsetY) / grid2.stepY

	valid = (
		np.isfinite(pz) &
		(gx >= 0) & (gy >= 0) &
		(gx < grid2.w-1) & (gy < grid2.h-1)
	)

	gx, gy, pz, px, py = gx[valid], gy[valid], pz[valid], px[valid], py[valid]
	ix, iy = np.floor(gx).astype(int), np.floor(gy).astype(int)
	dx, dy = gx - ix, gy - iy

	if mode == "nearest":
		z_interp = grid2.m_grid64[iy, ix]
	else:  # bilinear
		z11 = grid2.m_grid64[iy, ix]
		z21 = grid2.m_grid64[iy, ix+1]
		z12 = grid2.m_grid64[iy+1, ix]
		z22 = grid2.m_grid64[iy+1, ix+1]
		z_interp = (
			z11*(1-dx)*(1-dy) +
			z21*dx*(1-dy) +
			z12*(1-dx)*dy +
			z22*dx*dy
		)

	# --- dystans wzdłuż normalnej ---
	a, b, c = plane_abc
	n = np.array([a, b, 1.0], dtype=float)
	n /= np.linalg.norm(n)

	# kroki rastra po rzutowaniu na płaszczyznę (bez ścinania)
	nx, ny, nz = n
	stepX_plane = stepX * np.sqrt(max(0.0, 1.0 - nx*nx))
	stepY_plane = stepY * np.sqrt(max(0.0, 1.0 - ny*ny))

	p = np.stack([px, py, pz], axis=1)
	q = np.stack([px, py, z_interp], axis=1)

	d = np.sum((p - q) * n, axis=1)

	# wysokości względem płaszczyzny
	p_h = p @ n
	q_h = q @ n

	ref_in_plane = np.full(Z.shape, np.nan, dtype=np.float64)
	ref_in_plane.ravel()[valid] = p_h

	adj_in_plane = np.full(Z.shape, np.nan, dtype=np.float64)
	adj_in_plane.ravel()[valid] = q_h

	dist = np.full(Z.shape, np.nan, dtype=np.float64)
	dist.ravel()[valid] = d

	if max_dist is not None:
		mask = np.abs(dist) > max_dist
		dist[mask] = np.nan

	# dist_map = GridData64(dist, stepX=stepX_plane, stepY=stepY_plane)
	# new_ref  = GridData64(ref_in_plane, stepX=stepX_plane, stepY=stepY_plane)
	# new_adj  = GridData64(adj_in_plane, stepX=stepX_plane, stepY=stepY_plane)

	if np.any(valid):
		y_idx, x_idx = np.where(np.isfinite(dist))
		if len(x_idx) > 0 and len(y_idx) > 0:
			ymin, ymax = y_idx.min(), y_idx.max()
			xmin, xmax = x_idx.min(), x_idx.max()

			# przycięcie tablic
			ref_in_plane = ref_in_plane[ymin:ymax+1, xmin:xmax+1]
			adj_in_plane = adj_in_plane[ymin:ymax+1, xmin:xmax+1]
			dist         = dist[ymin:ymax+1, xmin:xmax+1]

			# przesunięcie offsetów, żeby nie przesunąć siatki względem świata
			new_offsetX = grid1.offsetX + xmin * stepX_plane
			new_offsetY = grid1.offsetY + ymin * stepY_plane
		else:
			new_offsetX, new_offsetY = grid1.offsetX, grid1.offsetY
	else:
		new_offsetX, new_offsetY = grid1.offsetX, grid1.offsetY

	# --- tworzenie przyciętych GridData64 ---
	dist_map = GridData64(dist, stepX=stepX_plane, stepY=stepY_plane,
						offsetX=new_offsetX, offsetY=new_offsetY)
	new_ref  = GridData64(ref_in_plane, stepX=stepX_plane, stepY=stepY_plane,
						offsetX=new_offsetX, offsetY=new_offsetY)
	new_adj  = GridData64(adj_in_plane, stepX=stepX_plane, stepY=stepY_plane,
						offsetX=new_offsetX, offsetY=new_offsetY)

	print(f"shapes: {dist.shape}, {ref_in_plane.shape}, {adj_in_plane.shape}")

	return new_ref, new_adj, dist_map





from scipy.spatial.transform import Rotation as R

def plane_transform(center1, normal1, center2, normal2):
	# normalizacja
	n1 = normal1 / np.linalg.norm(normal1)
	n2 = normal2 / np.linalg.norm(normal2)

	# oś i kąt rotacji
	v = np.cross(n1, n2)
	s = np.linalg.norm(v)
	c = np.dot(n1, n2)

	if s == 0:  # normalne równoległe
		if c > 0:
			rot = np.eye(3)
		else:
			# rotacja o 180° wokół dowolnej osi prostopadłej do n1
			axis = np.array([1, 0, 0]) if abs(n1[0]) < 0.9 else np.array([0, 1, 0])
			v = np.cross(n1, axis)
			v /= np.linalg.norm(v)
			rot = R.from_rotvec(np.pi * v).as_matrix()
	else:
		v /= s
		angle = np.arctan2(s, c)
		rot = R.from_rotvec(angle * v).as_matrix()

	# translacja
	t = center2 - rot @ center1

	# macierz 4x4
	T = np.eye(4)
	T[:3, :3] = rot
	T[:3, 3] = t
	return T

import numpy as np
from scipy import ndimage
from numpy.fft import fft2, ifft2


import numpy as np

def overlap_crop(A, B, dy, dx):
	"""Zwróć nakładające się fragmenty A,B bez zawijania (no-wrap)."""
	h, w = A.shape
	y0a = max(0,  dy); y1a = min(h, h + dy)
	x0a = max(0,  dx); x1a = min(w, w + dx)
	y0b = max(0, -dy); y1b = min(h, h - dy)
	x0b = max(0, -dx); x1b = min(w, w - dx)
	if (y1a - y0a) <= 5 or (x1a - x0a) <= 5:
		return None, None  # za mały overlap
	return A[y0a:y1a, x0a:x1a], B[y0b:y1b, x0b:x1b]

def masked_zncc(A, B):
	"""ZNCC na pikselach wspólnych (finite). Zwraca (score, N)."""
	M = np.isfinite(A) & np.isfinite(B)
	if not np.any(M):
		return -np.inf, 0
	a = A[M]; b = B[M]
	a0 = a - a.mean()
	b0 = b - b.mean()
	den = np.sqrt((a0*a0).sum() * (b0*b0).sum())
	if den == 0:
		return -np.inf, M.sum()
	return float((a0*b0).sum() / den), M.sum()

def rotation_about_normal(normal, theta_deg):
	n = normal / np.linalg.norm(normal)
	th = np.deg2rad(theta_deg)
	K = np.array([[0, -n[2], n[1]],
				[n[2], 0, -n[0]],
				[-n[1], n[0], 0]])
	R = np.eye(3) + np.sin(th) * K + (1-np.cos(th)) * (K @ K)
	T = np.eye(4)
	T[:3,:3] = R
	return T

def rotate_2d(img, angle_deg):
	return ndimage.rotate(img, angle=angle_deg, reshape=False,
						order=1, mode='constant', cval=np.nan)

def phase_correlation(im1, im2):
	A = np.nan_to_num(im1, copy=False)
	B = np.nan_to_num(im2, copy=False)
	FA, FB = fft2(A), fft2(B)
	R = FA * np.conj(FB)
	R /= np.maximum(np.abs(R), 1e-12)
	r = np.real(ifft2(R))
	maxpos = np.unravel_index(np.argmax(r), r.shape)
	shift = np.array(maxpos, dtype=float)
	for k, N in enumerate(r.shape):
		if shift[k] > N // 2:
			shift[k] -= N
	return int(shift[0]), int(shift[1])

def refine_in_plane_transform(ref_grid, adj_grid, ref_abc, adj_abc, T0,
							pre_theta=0.0,
							angle_range=10.0,
							angle_step=0.5):
	"""
	Szacuje dodatkowy obrót wokół normalnej i przesunięcia w płaszczyźnie
	względem macierzy wstępnej T0.

	Wszystkie obliczenia prowadzone w jednostkach świata (mm).

	pre_theta   -- wstępny obrót "na oko" (np. 180°)
	angle_range -- zakres przeszukiwania wokół pre_theta (± stopni)
	angle_step  -- krok w stopniach
	"""

	# dane i rozmiary
	Zref = np.array(ref_grid.m_grid64, dtype=float)
	Zadj = np.array(adj_grid.m_grid64, dtype=float)
	h = min(Zref.shape[0], Zadj.shape[0])
	w = min(Zref.shape[1], Zadj.shape[1])
	Zref = Zref[:h, :w]
	Zadj = Zadj[:h, :w]

	sx = getattr(ref_grid, "stepX", 1.0)
	sy = getattr(ref_grid, "stepY", 1.0)
	sz = 1.0

	# równania płaszczyzn w jednostkach świata (mm)
	ar, br, cr = ref_abc
	aa, ba, ca = adj_abc

	# siatka współrzędnych w mm
	X, Y = np.meshgrid(np.arange(w) * sx, np.arange(h) * sy)
	Zref_mm = Zref * sz
	Zadj_mm = Zadj * sz

	# reszty względem płaszczyzn (mm)
	Href1 = Zref_mm - (ar * X + br * Y + cr)
	Hadj1 = Zadj_mm - (aa * X + ba * Y + ca)

	# preprocessing (np. band-pass) -> filtrowane dane
	Href_f = preprocess_for_registration(Href1, bandpass=(2, 30))
	Hadj_f = preprocess_for_registration(Hadj1, bandpass=(2, 30))

	# --- krok 1: obrót wokół normalnej + przesunięcia w płaszczyźnie ---
	best = dict(theta=0.0, dy=0, dx=0, score=-np.inf)
	thetas = np.arange(-angle_range, angle_range + angle_step, angle_step)

	for theta in thetas:
		R2 = rotate_2d(-Hadj_f, pre_theta + theta)  # uwzględnia pre_theta
		dy_px, dx_px = phase_correlation(Href_f, R2)

		# konwersja przesunięć pikselowych na mm
		dx = dx_px * sx
		dy = dy_px * sy

		A = Href_f
		B = R2
		Aov, Bov = overlap_crop(A, B, dy_px, dx_px)  # overlap liczone w pikselach
		if Aov is None:
			score = -np.inf
		else:
			wy = np.hanning(Aov.shape[0])[:, None]
			wx = np.hanning(Aov.shape[1])[None, :]
			W = wy * wx
			score, N = masked_zncc(Aov * W, Bov * W)

			min_overlap = 0.25 * A.size
			if N < min_overlap:
				score = -np.inf

		print(f"theta = {theta}, score = {score}")
		if score > best["score"]:
			best.update(dict(theta=pre_theta + theta,
							dy=dy, dx=dx, score=score))

	theta = best["theta"]
	dx = best["dx"]
	dy = best["dy"]

	# --- krok 2: offset normalny ---
	R2 = rotate_2d(-Hadj1, theta)
	R2s = np.roll(np.roll(R2, int(dy / sy), axis=0),
				int(dx / sx), axis=1)  # wracamy do pikseli do przesunięcia
	valid = np.isfinite(Href1) & np.isfinite(R2s)
	dn = np.median(Href1[valid] + R2s[valid]) if np.any(valid) else 0.0

	print(f"Best alignment: θ = {theta:.2f}°, dx = {dx:.3f} mm, dy = {dy:.3f} mm, dn = {dn:.3f} mm, score = {best['score']:.3f}")

	# --- krok 3: macierz 3D ---
	n = np.array([ar, br, -1.0], dtype=float)
	n /= np.linalg.norm(n)
	tmp = np.array([0, 0, 1.0]) if abs(n[2]) < 0.9 else np.array([1.0, 0, 0])
	u = np.cross(tmp, n); u /= np.linalg.norm(u)
	v = np.cross(n, u)

	th = np.deg2rad(theta)
	K = np.array([[0, -n[2], n[1]],
				[n[2], 0, -n[0]],
				[-n[1], n[0], 0]])
	Rn = np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * (K @ K)

	t = dx * u + dy * v + dn * n

	T_refine = np.eye(4)
	T_refine[:3, :3] = Rn
	T_refine[:3, 3] = t

	return T_refine

def refine_in_plane_transform_inPx(ref_grid, adj_grid, ref_abc, adj_abc, T0,
							pre_theta=0.0,
							angle_range=10.0,
							angle_step=0.5):
	"""
	Szacuje dodatkowy obrót wokół normalnej i przesunięcia w płaszczyźnie
	względem macierzy wstępnej T0.

	pre_theta   -- wstępny obrót "na oko" (np. 180°)
	angle_range -- zakres przeszukiwania wokół pre_theta (± stopni)
	angle_step  -- krok w stopniach
	"""

	Zref = np.array(ref_grid.m_grid64, dtype=float)
	Zadj = np.array(adj_grid.m_grid64, dtype=float)

	# przycięcie do wspólnego wymiaru
	h = min(Zref.shape[0], Zadj.shape[0])
	w = min(Zref.shape[1], Zadj.shape[1])
	Zref = Zref[:h, :w]
	Zadj = Zadj[:h, :w]

	# równania płaszczyzn
	ar, br, cr = ref_abc
	aa, ba, ca = adj_abc

	X, Y = np.meshgrid(np.arange(w), np.arange(h))

	Href1 = Zref - (ar * X + br * Y + cr)
	Hadj1 = Zadj - (aa * X + ba * Y + ca)

	# przykładowe parametry:
	# - miękkie wygładzenie: sigma_px=3
	# - albo pasmowo: np. usuń fale > ~30 px i < ~2 px: bandpass=(2, 30)
	Href_f = preprocess_for_registration(Href1, bandpass=(2, 30))
	Hadj_f = preprocess_for_registration(Hadj1, bandpass=(2, 30))


	# --- krok 1: szukanie kąta wokół normalnej ---
	best = dict(theta=0.0, dy=0, dx=0, score=-np.inf)
	thetas = np.arange(-angle_range, angle_range + angle_step, angle_step)

	for theta in thetas:
		R2 = rotate_2d(-Hadj_f, pre_theta + theta)  # uwzględniamy pre_theta
		dy, dx = phase_correlation(Href_f, R2)

		# A = np.nan_to_num(Href)
		# B = np.roll(np.roll(R2, dy, axis=0), dx, axis=1)
		# score = np.sum(A * B)

		# A = np.nan_to_num(Href)
		# B = np.roll(np.roll(R2, dy, axis=0), dx, axis=1)
		# # zerowanie średnich
		# A0 = A - np.mean(A)
		# B0 = B - np.mean(B)
		# num = np.sum(A0 * B0)
		# den = np.sqrt(np.sum(A0**2) * np.sum(B0**2)) + 1e-12
		# score = num / den

		# po wyznaczeniu (dy, dx) np. z phase correlation:
		A = Href_f
		B = R2  # obrócone -Hadj

		Aov, Bov = overlap_crop(A, B, dy, dx)
		if Aov is None:
			score = -np.inf
		else:
			# opcjonalnie okno Hann:
			wy = np.hanning(Aov.shape[0])[:,None]
			wx = np.hanning(Aov.shape[1])[None,:]
			W = wy * wx
			score, N = masked_zncc(Aov*W, Bov*W)

			# kara za mały overlap – np. wymaga ≥ 0.25 * całego pola:
			min_overlap = 0.25 * A.size
			if N < min_overlap:
				score = -np.inf


		print(f"theta = {theta}, score = {score}")
		if score > best["score"]:
			best.update(dict(theta=pre_theta + theta,
							dy=dy, dx=dx, score=score))

	theta = best["theta"]
	dy, dx = best["dy"], best["dx"]

	# --- krok 2: offset normalny ---
	R2 = rotate_2d(-Hadj1, theta)
	R2s = np.roll(np.roll(R2, dy, axis=0), dx, axis=1)
	valid = np.isfinite(Href1) & np.isfinite(R2s)
	dn = np.median(Href1[valid] + R2s[valid]) if np.any(valid) else 0.0

	print(f"Best alignment: θ = {theta:.2f}°, dx = {dx}, dy = {dy}, dn = {dn:.3f}, score = {best['score']:.3f}")

	# --- krok 3: złożenie transformacji 3D ---
	n = np.array([ar, br, -1.0], dtype=float)
	n /= np.linalg.norm(n)
	tmp = np.array([0, 0, 1.0]) if abs(n[2]) < 0.9 else np.array([1.0, 0, 0])
	u = np.cross(tmp, n); u /= np.linalg.norm(u)
	v = np.cross(n, u)

	th = np.deg2rad(theta)
	K = np.array([[0, -n[2], n[1]],
				[n[2], 0, -n[0]],
				[-n[1], n[0], 0]])
	Rn = np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * (K @ K)

	t = dx * u + dy * v + dn * n

	T_refine = np.eye(4)
	T_refine[:3, :3] = Rn
	T_refine[:3, 3] = t

	return T_refine

# from scipy.interpolate import griddata

# def apply_transform_to_grid(Z, sx, sy, sz, T):
# 	h, w = Z.shape
# 	X, Y = np.meshgrid(np.arange(w), np.arange(h))

# 	# współrzędne oryginalne (fizyczne)
# 	xw = X * sx
# 	yw = Y * sy
# 	zw = Z * sz

# 	pts = np.column_stack((xw.ravel(), yw.ravel(), zw.ravel(), np.ones(h*w)))
# 	pts_T = (T @ pts.T).T

# 	# nowe współrzędne
# 	xw_T, yw_T, zw_T = pts_T[:,0], pts_T[:,1], pts_T[:,2]

# 	# z powrotem na regularną siatkę XY ref_grid
# 	grid_x, grid_y = np.meshgrid(np.arange(w)*sx, np.arange(h)*sy)

# 	Z_new = griddata(
# 		np.column_stack((xw_T, yw_T)),
# 		zw_T / sz,
# 		(grid_x, grid_y),
# 		method='linear',
# 		fill_value=np.nan
# 	)
# 	return Z_new

