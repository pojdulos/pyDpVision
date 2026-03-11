"""
Funkcje pomocnicze dla algorytmu Marching Cubes na danych wolumetrycznych (CBCT/CT).
Używane przez Volumetric.marching_cube() jako cienki wrapper.
"""

import numpy as np
from math import tan


def _tv_worker(args):
	"""Worker na poziomie modułu – wymagany przez ProcessPoolExecutor (pickle)."""
	i, slice_data, weight, max_num_iter = args
	from skimage.restoration import denoise_tv_chambolle
	return i, denoise_tv_chambolle(slice_data, weight=weight, max_num_iter=max_num_iter)


def mc_preprocess(image, px, py, pz, factor, sigma_mm, denoise, sharpening, denoise_iter=50, denoise_3d=False):
	"""TV denoising → Z-upsampling → Gaussian anti-aliasing → subsampling.

	Returns
	-------
	image       : przetworzony wolumen (po subsamplu)
	image_full  : kopia przed subsamplem (tylko gdy sharpening=True, inaczej None)
	zoom_z      : zastosowany współczynnik skalowania Z (1.0 gdy brak upsamplu)
	pz_eff      : efektywna odległość między warstwami po upsamplu
	"""
	if denoise_3d:
		from skimage.restoration import denoise_tv_chambolle

		img_min   = image.min()
		img_max   = image.max()
		img_range = img_max - img_min if img_max > img_min else 1.0
		norm      = (image - img_min) / img_range

		print(f"[MC] denoising 3D TV (iter={denoise_iter})...")
		norm  = denoise_tv_chambolle(norm, weight=0.02, max_num_iter=denoise_iter)
		image = (norm * img_range + img_min).astype(np.float32)

	elif denoise:
		from concurrent.futures import ProcessPoolExecutor
		import os

		img_min   = image.min()
		img_max   = image.max()
		img_range = img_max - img_min if img_max > img_min else 1.0
		norm      = (image - img_min) / img_range

		n_slices  = image.shape[0]
		n_workers = min(os.cpu_count() or 1, n_slices)
		print(f"[MC] denoising {n_slices} slices (TV 2D, iter={denoise_iter}, workers={n_workers})...")

		tasks = [(i, norm[i].copy(), 0.02, denoise_iter) for i in range(n_slices)]
		done  = 0
		with ProcessPoolExecutor(max_workers=n_workers) as ex:
			for i, result in ex.map(_tv_worker, tasks):
				norm[i] = result
				done += 1
				if done % 50 == 0 or done == n_slices:
					print(f"[MC]   slice {done}/{n_slices}")

		image = (norm * img_range + img_min).astype(np.float32)

	xy_spacing = 0.5 * (px + py)
	zoom_z     = pz / xy_spacing

	if zoom_z > 1.5:
		from scipy.ndimage import zoom as nd_zoom
		image  = nd_zoom(image, [zoom_z, 1.0, 1.0], order=3)
		pz_eff = xy_spacing
		print(f"Z upsampling: {zoom_z:.2f}x  ({pz:.3f}mm -> {pz_eff:.3f}mm)")
	else:
		zoom_z = 1.0
		pz_eff = pz

	if factor > 1:
		from scipy.ndimage import gaussian_filter
		if sigma_mm is None or sigma_mm <= 0.0:
			sigma_mm = 0.8 * xy_spacing
		sigma = (sigma_mm / pz_eff, sigma_mm / py, sigma_mm / px)
		image = gaussian_filter(image, sigma=sigma)

	image_full = image.copy() if sharpening else None

	if factor > 1:
		image = image[::factor, ::factor, ::factor]

	return image, image_full, zoom_z, pz_eff


def mc_gradient(image, image_full, pz_eff, py, px, sharpening):
	"""Oblicza gradient magnitude oraz gradienty kierunkowe (dla sharpening).

	Returns
	-------
	grad                    : magntiuda gradientu (w jednostkach voxela)
	gx_full, gy_full, gz_full : gradienty w mm/HU (tylko gdy sharpening=True)
	"""
	gz, gy, gx = np.gradient(image)
	gx_full = gy_full = gz_full = None
	if sharpening:
		gz_full, gy_full, gx_full = np.gradient(image_full, pz_eff, py, px)
	grad = np.sqrt(gx*gx + gy*gy + gz*gz)
	return grad, gx_full, gy_full, gz_full


def mc_estimate_threshold(image, grad, threshold=None, threshold_min=300.0):
	"""Automatyczna estymacja progu HU na podstawie gradientu.

	Jeśli threshold nie jest None, zwraca go bez zmian (tryb manualny).
	threshold_min: dolna granica bezpieczeństwa – wynik auto-detekcji nie spadnie poniżej tej wartości.
	"""
	if threshold is not None:
		print(f"threshold (manual): {threshold}")
		return float(threshold)

	g = grad.ravel()
	v = image.ravel()
	g_thr     = np.percentile(g, 95)
	mask_grad = (g >= g_thr) & (v > threshold_min) & (v < 6000)
	vals      = v[mask_grad]

	if len(vals) < 100:
		result = float(threshold_min)
	else:
		weights     = g[mask_grad]
		hist, edges = np.histogram(vals, bins=256, weights=weights)
		peak        = np.argmax(hist)
		result      = 0.5 * (edges[peak] + edges[peak+1])

	if result < threshold_min:
		print(f"threshold (auto): {result:.1f}  -> clipped to threshold_min={threshold_min:.1f}")
		result = float(threshold_min)
	else:
		print(f"threshold (auto): {result:.1f}")
	return result


def mc_segment(image, threshold, px, py, pz_eff, min_volume, fill_holes):
	"""Segmentacja binarna kości, usunięcie małych składowych, opcjonalne fill_holes.

	Returns
	-------
	image_clean : wolumen z wyzerowanymi voxelami poza maską kości
	"""
	from scipy import ndimage as ndi

	mask_bone  = image > threshold
	structure  = ndi.generate_binary_structure(3, 1)
	mask_bone  = ndi.binary_opening(mask_bone, structure=structure, iterations=1)
	mask_bone  = ndi.binary_closing(mask_bone, structure=structure, iterations=2)

	labels, n  = ndi.label(mask_bone)
	sizes      = ndi.sum(mask_bone, labels, index=np.arange(1, n+1))
	sizes_mm3  = sizes * (px * py * pz_eff)

	keep       = np.zeros(n + 1, dtype=bool)
	keep[1:][sizes_mm3 >= min_volume] = True
	mask_clean = keep[labels]

	if fill_holes:
		for i in range(mask_clean.shape[0]):
			mask_clean[i] = ndi.binary_fill_holes(mask_clean[i])

	image_clean                = image.copy()
	image_clean[~mask_clean]   = threshold - 1
	return image_clean


def mc_sharpen(points, offset, factor, image_full, gx_full, gy_full, gz_full, threshold):
	"""Voxel sharpening: przesuwa wierzchołki MC na rzeczywistą izopowierzchnię HU."""
	from scipy.ndimage import map_coordinates

	coords = np.vstack([
		(points[:,0] - offset) * factor,
		(points[:,1] - offset) * factor,
		(points[:,2] - offset) * factor,
	])

	I    = map_coordinates(image_full, coords, order=1, mode='nearest')
	gx_v = map_coordinates(gx_full,   coords, order=1, mode='nearest')
	gy_v = map_coordinates(gy_full,   coords, order=1, mode='nearest')
	gz_v = map_coordinates(gz_full,   coords, order=1, mode='nearest')

	eps        = 1e-6
	grad_norm2 = gx_v*gx_v + gy_v*gy_v + gz_v*gz_v + eps
	grad_norm  = np.sqrt(grad_norm2)

	valid            = grad_norm > 50   # HU/mm
	shift            = (threshold - I) / grad_norm2
	shift[~valid]    = 0
	shift            = np.clip(shift, -0.25, 0.25)

	points           = points.copy()
	points[:,0]     += shift * gz_v
	points[:,1]     += shift * gy_v
	points[:,2]     += shift * gx_v
	return points


def mc_to_world(points, origin, slice_distance, gantry_tilt, px, py, zoom_z, factor, close_boundary, offset):
	"""Transformuje wierzchołki MC (indeksy voxeli) do układu współrzędnych world (mm).

	Parameters
	----------
	origin         : [x, y, z] w mm – pozycja pierwszego voxela ROI
	slice_distance : odległość między oryginalnymi warstwami w mm
	gantry_tilt    : kąt przechyłu gantry w radianach
	zoom_z         : współczynnik z-upsampingu (1.0 = brak)
	"""
	step_z = (slice_distance / zoom_z) * factor

	if close_boundary:
		origin = [
			origin[0] - px   * factor,
			origin[1] - px   * factor,
			origin[2] - step_z,
		]

	scale    = [px * factor, px * factor, step_z]

	vertices          = np.empty((len(points), 3), dtype=np.float64)
	vertices[:, 0]    = points[:, 2] * scale[0]
	vertices[:, 1]    = points[:, 1] * scale[1]
	vertices[:, 2]    = points[:, 0] * scale[2]

	if gantry_tilt != 0.0:
		vertices[:, 1] += vertices[:, 2] * tan(gantry_tilt)

	vertices[:, 0] += origin[0]
	vertices[:, 1] += origin[1]
	vertices[:, 2] += origin[2]
	return vertices


def taubin_smooth(vertices, faces, lambda_=0.5, mu=-0.53, iterations=10):
	"""Taubin smoothing siatki: naprzemienne kroki λ/μ – wygładza bez kurczenia.

	Parameters
	----------
	lambda\\_ : współczynnik wygładzania (> 0)
	mu       : współczynnik kompensacji kurczenia (< 0, |mu| > lambda)
	iterations : liczba par kroków λ+μ
	"""
	from scipy.sparse import coo_matrix, diags

	n     = len(vertices)
	faces = np.asarray(faces)

	i_idx = np.concatenate([faces[:,0], faces[:,1], faces[:,2],
	                         faces[:,1], faces[:,2], faces[:,0]])
	j_idx = np.concatenate([faces[:,1], faces[:,2], faces[:,0],
	                         faces[:,0], faces[:,1], faces[:,2]])

	A      = coo_matrix((np.ones(len(i_idx)), (i_idx, j_idx)), shape=(n, n)).tocsr()
	deg    = np.asarray(A.sum(axis=1)).ravel()
	deg[deg == 0] = 1
	A_norm = diags(1.0 / deg) @ A

	vertices = vertices.copy()
	for _ in range(iterations):
		for f in [lambda_, mu]:
			vertices += f * (A_norm @ vertices - vertices)

	return vertices
