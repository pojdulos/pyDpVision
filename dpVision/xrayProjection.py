# -*- coding: utf-8 -*-
"""World-space X-ray projection backend prepared for multiple scene source types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, replace
import logging
import os
from time import perf_counter
from typing import Iterable, Sequence

import cv2
import numpy as np
import pydicom
from scipy.ndimage import map_coordinates

from .mesh import Mesh
from .volumetric import Volumetric

_log = logging.getLogger(__name__)


def ensure_xray_source_config(source_object):
	"""Attach default per-object X-ray source settings to one scene object.

	The settings live directly on `Volumetric` and `Mesh` instances so that each
	object can be configured independently in the property panels and later read
	by `VirtualXRay` during scene assembly.
	"""
	if isinstance(source_object, Volumetric):
		defaults = {
			"xray_source_enabled": True,
			"xray_scalar_scale": 1.0,
			"xray_scalar_bias": 0.0,
			"xray_attenuation_multiplier": 1.0,
			"xray_interpolation_override": "default",
			"xray_fill_value_override_enabled": False,
			"xray_fill_value_override": 0.0,
			"xray_volume_backend": "sampling",
		}
	elif isinstance(source_object, Mesh):
		defaults = {
			"xray_source_enabled": True,
			"xray_scalar_scale": 1.0,
			"xray_scalar_bias": 0.0,
			"xray_attenuation_multiplier": 1.0,
			"xray_mesh_backend": "analytic_bvh",
			"xray_mesh_mode": "solid",
			"xray_mesh_scalar_value": 1800.0,
			"xray_mesh_shell_thickness_mm": 1.0,
			"xray_projected_min_abs_cos": 0.0,
			"xray_debug_export_dir": None,
			"xray_debug_compare_analytic": True,
		}
	else:
		return source_object

	for attr_name, default_value in defaults.items():
		if not hasattr(source_object, attr_name):
			setattr(source_object, attr_name, default_value)
	return source_object


def _identity_matrix():
	"""Return a 4x4 identity matrix used as a default homogeneous transform."""
	return np.eye(4, dtype=np.float32)


def _normalize_vector(vector):
	"""Return a normalized 3D vector."""
	vector = np.asarray(vector, dtype=np.float32)
	norm = float(np.linalg.norm(vector))
	if norm <= 1e-8:
		raise ValueError("Vector norm must be greater than zero.")
	return vector / norm


def _transform_point(transform_matrix, point_xyz):
	"""Apply a 4x4 homogeneous transform to a 3D point."""
	point_h = np.ones(4, dtype=np.float32)
	point_h[:3] = np.asarray(point_xyz, dtype=np.float32)
	return (np.asarray(transform_matrix, dtype=np.float32) @ point_h)[:3]


def _transform_direction(transform_matrix, direction_xyz):
	"""Apply a 4x4 homogeneous transform to a 3D direction vector."""
	return np.asarray(transform_matrix, dtype=np.float32)[:3, :3] @ np.asarray(direction_xyz, dtype=np.float32)


def _transform_points(transform_matrix, points_xyz):
	"""Apply one homogeneous transform to an array of 3D points."""
	points_xyz = np.asarray(points_xyz, dtype=np.float32)
	if points_xyz.ndim != 2 or points_xyz.shape[1] != 3:
		raise ValueError("points_xyz must have shape (N, 3).")
	points_h = np.ones((points_xyz.shape[0], 4), dtype=np.float32)
	points_h[:, :3] = points_xyz
	return (points_h @ np.asarray(transform_matrix, dtype=np.float32).T)[:, :3]


def _ray_box_intersection(ray_origin, ray_direction, box_min, box_max):
	"""Intersect one ray with an axis-aligned box and return the parametric interval."""
	ray_origin = np.asarray(ray_origin, dtype=np.float32)
	ray_direction = np.asarray(ray_direction, dtype=np.float32)
	box_min = np.asarray(box_min, dtype=np.float32)
	box_max = np.asarray(box_max, dtype=np.float32)

	t_min = -np.inf
	t_max = np.inf
	for axis_idx in range(3):
		direction_component = float(ray_direction[axis_idx])
		if abs(direction_component) <= 1e-8:
			if ray_origin[axis_idx] < box_min[axis_idx] or ray_origin[axis_idx] > box_max[axis_idx]:
				return None
			continue

		inv_dir = 1.0 / direction_component
		t0 = (box_min[axis_idx] - ray_origin[axis_idx]) * inv_dir
		t1 = (box_max[axis_idx] - ray_origin[axis_idx]) * inv_dir
		if t0 > t1:
			t0, t1 = t1, t0
		t_min = max(t_min, t0)
		t_max = min(t_max, t1)
		if t_max < t_min:
			return None

	return float(t_min), float(t_max)


def _ray_box_intersections_vectorized(ray_origins, ray_directions, box_min, box_max):
	"""Vectorized AABB intersection for N rays. Returns t_start (N,), t_end (N,), hit_mask (N,)."""
	ray_origins = np.asarray(ray_origins, dtype=np.float32)
	ray_directions = np.asarray(ray_directions, dtype=np.float32)
	box_min = np.asarray(box_min, dtype=np.float32)
	box_max = np.asarray(box_max, dtype=np.float32)

	n = ray_origins.shape[0]
	t_start = np.full(n, -np.inf, dtype=np.float32)
	t_end = np.full(n, np.inf, dtype=np.float32)
	hit_mask = np.ones(n, dtype=bool)

	for axis in range(3):
		d = ray_directions[:, axis]
		o = ray_origins[:, axis]
		parallel = np.abs(d) <= 1e-8
		nonparallel = ~parallel
		hit_mask &= ~(parallel & ((o < box_min[axis]) | (o > box_max[axis])))
		safe_d = np.where(nonparallel, d, 1.0)
		inv_d = np.where(nonparallel, 1.0 / safe_d, 0.0)
		t0 = (box_min[axis] - o) * inv_d
		t1 = (box_max[axis] - o) * inv_d
		t_near = np.where(nonparallel, np.minimum(t0, t1), -np.inf)
		t_far = np.where(nonparallel, np.maximum(t0, t1), np.inf)
		t_start = np.maximum(t_start, t_near)
		t_end = np.minimum(t_end, t_far)
		hit_mask &= t_end >= t_start

	return t_start, t_end, hit_mask


def _ray_planar_slab_intersections_vectorized(ray_origins, ray_directions, slab_origin, slab_axis, slab_min, slab_max):
	"""Intersect N rays with one infinite planar slab defined in axis coordinates."""
	ray_origins = np.asarray(ray_origins, dtype=np.float32)
	ray_directions = np.asarray(ray_directions, dtype=np.float32)
	slab_origin = np.asarray(slab_origin, dtype=np.float32)
	slab_axis = _normalize_vector(slab_axis)
	slab_min = float(slab_min)
	slab_max = float(slab_max)

	n = ray_origins.shape[0]
	t_start = np.full(n, -np.inf, dtype=np.float32)
	t_end = np.full(n, np.inf, dtype=np.float32)
	hit_mask = np.ones(n, dtype=bool)

	offsets = ray_origins - slab_origin[np.newaxis, :]
	s0 = np.sum(offsets * slab_axis[np.newaxis, :], axis=1)
	ds = np.sum(ray_directions * slab_axis[np.newaxis, :], axis=1)
	parallel = np.abs(ds) <= 1e-8
	inside_parallel = parallel & (s0 >= slab_min) & (s0 <= slab_max)
	hit_mask &= (~parallel) | inside_parallel

	nonparallel = ~parallel
	if np.any(nonparallel):
		ds_safe = ds[nonparallel]
		t0 = (slab_min - s0[nonparallel]) / ds_safe
		t1 = (slab_max - s0[nonparallel]) / ds_safe
		t_near = np.minimum(t0, t1)
		t_far = np.maximum(t0, t1)
		t_start[nonparallel] = t_near.astype(np.float32)
		t_end[nonparallel] = t_far.astype(np.float32)

	hit_mask &= t_end >= t_start
	return t_start, t_end, hit_mask


def _ray_triangle_hit_distances(ray_origin, ray_direction, triangles_world, epsilon=1e-6):
	"""Return unsorted hit distances for one ray and many world-space triangles."""
	triangles_world = np.asarray(triangles_world, dtype=np.float32)
	if triangles_world.ndim != 3 or triangles_world.shape[1:] != (3, 3):
		raise ValueError("triangles_world must have shape (N, 3, 3).")
	if triangles_world.shape[0] == 0:
		return np.empty((0,), dtype=np.float32)

	v0 = triangles_world[:, 0, :]
	v1 = triangles_world[:, 1, :]
	v2 = triangles_world[:, 2, :]
	edge1 = v1 - v0
	edge2 = v2 - v0

	pvec = np.cross(np.broadcast_to(ray_direction, edge2.shape), edge2)
	det = np.einsum("ij,ij->i", edge1, pvec)
	hit_mask = np.abs(det) > float(epsilon)
	if not np.any(hit_mask):
		return np.empty((0,), dtype=np.float32)

	inv_det = np.zeros_like(det, dtype=np.float32)
	inv_det[hit_mask] = 1.0 / det[hit_mask]
	tvec = np.asarray(ray_origin, dtype=np.float32)[np.newaxis, :] - v0
	u = np.einsum("ij,ij->i", tvec, pvec) * inv_det
	hit_mask &= (u >= -epsilon) & (u <= 1.0 + epsilon)
	if not np.any(hit_mask):
		return np.empty((0,), dtype=np.float32)

	qvec = np.cross(tvec, edge1)
	v = np.einsum("j,ij->i", np.asarray(ray_direction, dtype=np.float32), qvec) * inv_det
	hit_mask &= (v >= -epsilon) & ((u + v) <= 1.0 + epsilon)
	if not np.any(hit_mask):
		return np.empty((0,), dtype=np.float32)

	t_values = np.einsum("ij,ij->i", edge2, qvec) * inv_det
	t_values = t_values[hit_mask]
	t_values = t_values[t_values >= -epsilon]
	if t_values.size == 0:
		return np.empty((0,), dtype=np.float32)
	return t_values.astype(np.float32, copy=False)


def _ray_triangle_intersections(ray_origin, ray_direction, triangles_world, epsilon=1e-6):
	"""Return sorted ray-triangle hit distances for one ray and many world-space triangles."""
	return np.sort(_ray_triangle_hit_distances(
		ray_origin=ray_origin,
		ray_direction=ray_direction,
		triangles_world=triangles_world,
		epsilon=epsilon,
	))


def _rays_single_triangle_hit_distances(ray_origins, ray_directions, triangle_world, epsilon=1e-6):
	"""Return one hit distance per ray for one triangle, or `nan` when there is no hit."""
	ray_origins = np.asarray(ray_origins, dtype=np.float32)
	ray_directions = np.asarray(ray_directions, dtype=np.float32)
	triangle_world = np.asarray(triangle_world, dtype=np.float32)
	if ray_origins.ndim != 2 or ray_origins.shape[1] != 3:
		raise ValueError("ray_origins must have shape (N, 3).")
	if ray_directions.shape != ray_origins.shape:
		raise ValueError("ray_directions must have the same shape as ray_origins.")
	if triangle_world.shape != (3, 3):
		raise ValueError("triangle_world must have shape (3, 3).")

	n_rays = ray_origins.shape[0]
	t_out = np.full(n_rays, np.nan, dtype=np.float32)
	if n_rays == 0:
		return t_out

	v0 = triangle_world[0]
	v1 = triangle_world[1]
	v2 = triangle_world[2]
	edge1 = v1 - v0
	edge2 = v2 - v0

	pvec = np.cross(ray_directions, edge2[np.newaxis, :])
	det = np.sum(edge1[np.newaxis, :] * pvec, axis=1)
	hit_mask = np.abs(det) > float(epsilon)
	if not np.any(hit_mask):
		return t_out

	inv_det = np.zeros_like(det, dtype=np.float32)
	inv_det[hit_mask] = 1.0 / det[hit_mask]
	tvec = ray_origins - v0[np.newaxis, :]
	u = np.sum(tvec * pvec, axis=1) * inv_det
	hit_mask &= (u >= -epsilon) & (u <= 1.0 + epsilon)
	if not np.any(hit_mask):
		return t_out

	qvec = np.cross(tvec, edge1[np.newaxis, :])
	v = np.sum(ray_directions * qvec, axis=1) * inv_det
	hit_mask &= (v >= -epsilon) & ((u + v) <= 1.0 + epsilon)
	if not np.any(hit_mask):
		return t_out

	t_values = np.sum(edge2[np.newaxis, :] * qvec, axis=1) * inv_det
	hit_mask &= t_values >= -epsilon
	t_out[hit_mask] = t_values[hit_mask].astype(np.float32, copy=False)
	return t_out


def _one_ray_per_triangle_hit(ray_origins, ray_directions, triangles_world, epsilon=1e-6):
	"""Möller-Trumbore intersection — one *distinct* ray per triangle, fully vectorised.

	Unlike `_rays_single_triangle_hit_distances` (many rays, one triangle), this
	function handles M ray-triangle pairs where every pair uses a different triangle.

	Args:
		ray_origins:     (M, 3) float32 world-space ray origins.
		ray_directions:  (M, 3) float32 unit-length ray directions.
		triangles_world: (M, 3, 3) float32 world-space triangle vertices.

	Returns:
		t_values: (M,) float32 — hit distance along the ray, or ``nan`` where
		          there is no valid intersection.
	"""
	v0    = triangles_world[:, 0, :]             # (M, 3)
	edge1 = triangles_world[:, 1, :] - v0       # (M, 3)
	edge2 = triangles_world[:, 2, :] - v0       # (M, 3)
	pvec  = np.cross(ray_directions, edge2)      # (M, 3)
	det   = np.einsum("ij,ij->i", edge1, pvec)   # (M,)
	mask  = np.abs(det) > float(epsilon)
	# Replace near-zero det with 1 to avoid ZeroDivision — discarded by mask.
	safe_det = np.where(mask, det, np.float32(1.0))
	inv_det  = np.where(mask, np.float32(1.0) / safe_det, np.float32(0.0))
	tvec = ray_origins - v0                                            # (M, 3)
	u    = np.einsum("ij,ij->i", tvec, pvec) * inv_det                # (M,)
	mask &= (u >= -epsilon) & (u <= 1.0 + epsilon)
	qvec = np.cross(tvec, edge1)                                       # (M, 3)
	v    = np.einsum("ij,ij->i", ray_directions, qvec) * inv_det      # (M,)
	mask &= (v >= -epsilon) & ((u + v) <= 1.0 + epsilon)
	t    = np.einsum("ij,ij->i", edge2, qvec) * inv_det               # (M,)
	mask &= t >= -epsilon
	return np.where(mask, t, np.float32(np.nan)).astype(np.float32)


def _is_top_left_edge_2d(point_a, point_b):
	"""Return `True` when one directed 2D edge should be inclusive in top-left rasterization."""
	dy = float(point_b[1] - point_a[1])
	dx = float(point_b[0] - point_a[0])
	return (dy > 0.0) or (abs(dy) <= 1e-8 and dx < 0.0)


def _build_triangle_bvh(triangles_world, max_leaf_size=8):
	"""Build one binary AABB tree over triangle geometry and return a compact node list."""
	triangles_world = np.asarray(triangles_world, dtype=np.float32)
	if triangles_world.ndim != 3 or triangles_world.shape[1:] != (3, 3):
		raise ValueError("triangles_world must have shape (N, 3, 3).")

	triangle_count = triangles_world.shape[0]
	if triangle_count == 0:
		return []

	tri_mins = triangles_world.min(axis=1)
	tri_maxs = triangles_world.max(axis=1)
	tri_centroids = triangles_world.mean(axis=1)
	ordered_indices = []
	nodes = []

	def _build_node(triangle_indices):
		node_index = len(nodes)
		node_min = np.min(tri_mins[triangle_indices], axis=0).astype(np.float32)
		node_max = np.max(tri_maxs[triangle_indices], axis=0).astype(np.float32)
		node = {
			"bbox_min": node_min,
			"bbox_max": node_max,
			"left": -1,
			"right": -1,
			"start": -1,
			"count": 0,
		}
		nodes.append(node)

		if len(triangle_indices) <= max_leaf_size:
			node["start"] = len(ordered_indices)
			node["count"] = int(len(triangle_indices))
			ordered_indices.extend(int(idx) for idx in triangle_indices)
			return node_index

		centroids = tri_centroids[triangle_indices]
		extent = np.ptp(centroids, axis=0)
		split_axis = int(np.argmax(extent))
		sort_order = np.argsort(centroids[:, split_axis], kind="mergesort")
		sorted_indices = triangle_indices[sort_order]
		mid = len(sorted_indices) // 2
		if mid <= 0 or mid >= len(sorted_indices):
			node["start"] = len(ordered_indices)
			node["count"] = int(len(triangle_indices))
			ordered_indices.extend(int(idx) for idx in triangle_indices)
			return node_index

		node["left"] = int(_build_node(sorted_indices[:mid]))
		node["right"] = int(_build_node(sorted_indices[mid:]))
		return node_index

	root_triangle_indices = np.arange(triangle_count, dtype=np.int32)
	_build_node(root_triangle_indices)
	ordered_indices = np.asarray(ordered_indices, dtype=np.int32)
	for node in nodes:
		if node["count"] > 0:
			node["indices"] = ordered_indices[node["start"]: node["start"] + node["count"]]
		else:
			node["indices"] = np.empty((0,), dtype=np.int32)
	return nodes


def _ray_triangle_intersections_bvh(ray_origin, ray_direction, triangles_world, bvh_nodes, epsilon=1e-6):
	"""Return sorted ray-triangle hit distances by traversing one mesh BVH."""
	if not bvh_nodes:
		return np.empty((0,), dtype=np.float32)

	hit_values = []
	stack = [0]
	while stack:
		node_index = stack.pop()
		node = bvh_nodes[node_index]
		if _ray_box_intersection(ray_origin, ray_direction, node["bbox_min"], node["bbox_max"]) is None:
			continue

		if node["count"] > 0:
			leaf_hits = _ray_triangle_hit_distances(
				ray_origin=ray_origin,
				ray_direction=ray_direction,
				triangles_world=triangles_world[node["indices"]],
				epsilon=epsilon,
			)
			if leaf_hits.size:
				hit_values.append(leaf_hits)
			continue

		if node["right"] >= 0:
			stack.append(node["right"])
		if node["left"] >= 0:
			stack.append(node["left"])

	if not hit_values:
		return np.empty((0,), dtype=np.float32)
	return np.sort(np.concatenate(hit_values).astype(np.float32, copy=False))


def normalize_projection_to_uint8(image, fixed_range=None, robust_percentile=99.5, invert=False):
	"""Normalize a projection image into an 8-bit grayscale image."""
	image = np.asarray(image, dtype=np.float32)
	finite_values = image[np.isfinite(image)]
	if finite_values.size == 0:
		return np.zeros(image.shape, dtype=np.uint8)

	if fixed_range is not None:
		vmin = float(fixed_range[0])
		vmax = float(fixed_range[1])
	else:
		vmin = float(np.min(finite_values))
		vmax = float(np.percentile(finite_values, float(robust_percentile)))
		if vmax <= vmin:
			vmax = float(np.max(finite_values))
		if vmax <= vmin:
			vmax = vmin + 1.0

	normalized = np.clip((image - vmin) / (vmax - vmin), 0.0, 1.0)
	if invert:
		normalized = 1.0 - normalized
	return np.ascontiguousarray(np.round(normalized * 255.0).astype(np.uint8))


def normalize_projection_to_uint16(image, fixed_range=None, robust_percentile=99.5, invert=False):
	"""Normalize a projection image into a 16-bit grayscale image."""
	image = np.asarray(image, dtype=np.float32)
	finite_values = image[np.isfinite(image)]
	if finite_values.size == 0:
		return np.zeros(image.shape, dtype=np.uint16)

	if fixed_range is not None:
		vmin = float(fixed_range[0])
		vmax = float(fixed_range[1])
	else:
		vmin = float(np.min(finite_values))
		vmax = float(np.percentile(finite_values, float(robust_percentile)))
		if vmax <= vmin:
			vmax = float(np.max(finite_values))
		if vmax <= vmin:
			vmax = vmin + 1.0

	normalized = np.clip((image - vmin) / (vmax - vmin), 0.0, 1.0)
	if invert:
		normalized = 1.0 - normalized
	return np.ascontiguousarray(np.round(normalized * 65535.0).astype(np.uint16))


def save_projection_png(image, file_path, fixed_range=None, robust_percentile=99.5, invert=False):
	"""Save a projection image as an 8-bit grayscale PNG."""
	image_u8 = normalize_projection_to_uint8(
		image=image,
		fixed_range=fixed_range,
		robust_percentile=robust_percentile,
		invert=invert,
	)
	if not cv2.imwrite(str(file_path), image_u8):
		raise IOError(f"Failed to save PNG projection to: {file_path}")
	return image_u8


def save_projection_tiff(image, file_path, mode="uint16", fixed_range=None, robust_percentile=99.5, invert=False):
	"""Save a projection image as TIFF in `uint16`, `float32` or `uint8` mode."""
	mode = str(mode).lower()
	if mode == "float32":
		image_out = np.asarray(image, dtype=np.float32)
	elif mode == "uint8":
		image_out = normalize_projection_to_uint8(
			image=image,
			fixed_range=fixed_range,
			robust_percentile=robust_percentile,
			invert=invert,
		)
	else:
		image_out = normalize_projection_to_uint16(
			image=image,
			fixed_range=fixed_range,
			robust_percentile=robust_percentile,
			invert=invert,
		)
	if not cv2.imwrite(str(file_path), image_out):
		raise IOError(f"Failed to save TIFF projection to: {file_path}")
	return image_out


def save_projection_dicom(image, file_path, patient_name="Anonymous", patient_id="XRAY001",
	                      study_description="Synthetic XRay", series_description="Projection",
	                      fixed_range=None, robust_percentile=99.5, invert=False):
	"""Save a projection image as a simple 16-bit DICOM Secondary Capture."""
	image_u16 = normalize_projection_to_uint16(
		image=image,
		fixed_range=fixed_range,
		robust_percentile=robust_percentile,
		invert=invert,
	)
	file_meta = pydicom.Dataset()
	file_meta.MediaStorageSOPClassUID = pydicom.uid.SecondaryCaptureImageStorage
	file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
	file_meta.TransferSyntaxUID = pydicom.uid.ImplicitVRLittleEndian
	ds = pydicom.FileDataset(str(file_path), {}, file_meta=file_meta, preamble=b"\0" * 128)
	ds.is_implicit_VR = True
	ds.is_little_endian = True
	ds.SOPClassUID = pydicom.uid.SecondaryCaptureImageStorage
	ds.SOPInstanceUID = pydicom.uid.generate_uid()
	ds.StudyInstanceUID = pydicom.uid.generate_uid()
	ds.SeriesInstanceUID = pydicom.uid.generate_uid()
	ds.PatientName = patient_name
	ds.PatientID = patient_id
	ds.Modality = "OT"
	ds.StudyDescription = study_description
	ds.SeriesDescription = series_description
	ds.Rows, ds.Columns = image_u16.shape
	ds.SamplesPerPixel = 1
	ds.PhotometricInterpretation = "MONOCHROME2"
	ds.BitsAllocated = 16
	ds.BitsStored = 16
	ds.HighBit = 15
	ds.PixelRepresentation = 0
	ds.ImagesInAcquisition = 1
	ds.InstanceNumber = 1
	ds.RescaleIntercept = 0.0
	ds.RescaleSlope = 1.0
	ds.PixelData = image_u16.tobytes()
	ds.save_as(str(file_path))
	return image_u16


class XRayPresentationModel(ABC):
	"""Transform raw projection output into a presentation-ready image."""

	@abstractmethod
	def apply(self, image):
		"""Return a presentation image derived from the raw projection result."""


@dataclass
class RawPresentationModel(XRayPresentationModel):
	"""Return the raw projection output without any presentation processing."""

	def apply(self, image):
		"""Return a float32 copy of the acquisition image."""
		return np.asarray(image, dtype=np.float32).copy()


@dataclass
class FilmLikePresentationModel(XRayPresentationModel):
	"""Apply a simple inverted, non-linear film-like tone curve."""

	robust_percentile: float = 99.5
	gamma: float = 1.4
	contrast: float = 1.0
	invert: bool = True
	fixed_range: Sequence[float] | None = None

	def apply(self, image):
		"""Return a film-like normalized float image in the range `[0, 1]`."""
		image = np.asarray(image, dtype=np.float32)
		finite_values = image[np.isfinite(image)]
		if finite_values.size == 0:
			return np.zeros(image.shape, dtype=np.float32)

		if self.fixed_range is not None:
			vmin = float(self.fixed_range[0])
			vmax = float(self.fixed_range[1])
		else:
			vmin = float(np.min(finite_values))
			vmax = float(np.percentile(finite_values, float(self.robust_percentile)))
			if vmax <= vmin:
				vmax = float(np.max(finite_values))
			if vmax <= vmin:
				vmax = vmin + 1.0

		normalized = np.clip((image - vmin) / (vmax - vmin), 0.0, 1.0)
		if self.invert:
			normalized = 1.0 - normalized
		normalized = np.clip(0.5 + (normalized - 0.5) * float(self.contrast), 0.0, 1.0)
		gamma = max(1e-6, float(self.gamma))
		return np.power(normalized, 1.0 / gamma).astype(np.float32, copy=False)


@dataclass
class DigitalRadiographyPresentationModel(XRayPresentationModel):
	"""Apply a simple digital-radiography style windowing and tone mapping."""

	window_center: float | None = None
	window_width: float | None = None
	robust_percentile: float = 99.5
	invert: bool = True
	gamma: float = 1.0
	contrast: float = 1.0

	def apply(self, image):
		"""Return a digital-radiography style normalized float image in the range `[0, 1]`."""
		
		if (image is None) or (not np.any(np.isfinite(image))):
			_log.warning("Input image is empty or contains no finite values. Returning zero image.")
			return np.zeros(image.shape, dtype=np.float32)
		
		image = np.asarray(image, dtype=np.float32)
		finite_values = image[np.isfinite(image)]
		if finite_values.size == 0:
			return np.zeros(image.shape, dtype=np.float32)

		if self.window_center is not None and self.window_width is not None and float(self.window_width) > 0.0:
			vmin = float(self.window_center) - float(self.window_width) / 2.0
			vmax = float(self.window_center) + float(self.window_width) / 2.0
		else:
			vmin = float(np.min(finite_values))
			vmax = float(np.percentile(finite_values, float(self.robust_percentile)))
			if vmax <= vmin:
				vmax = float(np.max(finite_values))
			if vmax <= vmin:
				vmax = vmin + 1.0

		normalized = np.clip((image - vmin) / (vmax - vmin), 0.0, 1.0)
		if self.invert:
			normalized = 1.0 - normalized
		normalized = np.clip(0.5 + (normalized - 0.5) * float(self.contrast), 0.0, 1.0)
		gamma = max(1e-6, float(self.gamma))
		return np.power(normalized, 1.0 / gamma).astype(np.float32, copy=False)


@dataclass
class XRayScalarPreprocessor:
	"""Optionally normalize source scalar values before the physics model consumes them."""

	mode: str = "none"
	input_low_percentile: float = 0.5
	input_high_percentile: float = 99.5
	output_low_value: float = -1000.0
	output_high_value: float = 2500.0

	def is_active(self):
		"""Return `True` when this preprocessor should modify source scalar values."""
		return str(self.mode).lower() != "none"

	def estimate_volume_stats(self, volume):
		"""Estimate robust scalar range statistics from one source volume."""
		volume = np.asarray(volume, dtype=np.float32)
		finite_values = volume[np.isfinite(volume)]
		if finite_values.size == 0:
			return None

		low_q = float(np.percentile(finite_values, np.clip(float(self.input_low_percentile), 0.0, 100.0)))
		high_q = float(np.percentile(finite_values, np.clip(float(self.input_high_percentile), 0.0, 100.0)))
		if high_q <= low_q:
			high_q = low_q + 1.0
		return {
			"input_low": low_q,
			"input_high": high_q,
		}

	def apply(self, scalar_values, stats):
		"""Return optionally normalized scalar values using previously estimated source statistics."""
		scalar_values = np.asarray(scalar_values, dtype=np.float32)
		if not self.is_active() or stats is None:
			return scalar_values

		mode = str(self.mode).lower()
		if mode == "percentile_rescale":
			input_low = float(stats["input_low"])
			input_high = float(stats["input_high"])
			output_low = float(self.output_low_value)
			output_high = float(self.output_high_value)
			normalized = np.clip((scalar_values - input_low) / max(input_high - input_low, 1e-6), 0.0, 1.0)
			return (output_low + normalized * (output_high - output_low)).astype(np.float32, copy=False)

		return scalar_values


@dataclass
class XRayProjectionGeometry:
	"""Describe the source-detector setup in a configurable reference frame."""

	detector_origin_ref: Sequence[float]
	detector_u_ref: Sequence[float]
	detector_v_ref: Sequence[float]
	detector_shape_hw: Sequence[int]
	step_mm: float = 1.0
	source_position_ref: Sequence[float] | None = None
	ray_direction_ref: Sequence[float] | None = None
	depth_window_mode: str | None = None
	depth_window_mm: Sequence[float] | None = None
	depth_window_origin_ref: Sequence[float] | None = None
	depth_window_axis_ref: Sequence[float] | None = None

	@classmethod
	def from_detector_pose(
		cls,
		detector_center_ref,
		detector_normal_ref,
		detector_up_ref,
		detector_shape_hw,
		detector_pixel_size_mm=None,
		detector_size_mm_hw=None,
		step_mm=1.0,
		source_position_ref=None,
		ray_direction_ref=None,
		depth_window_mode=None,
		depth_window_mm=None,
		depth_window_origin_ref=None,
		depth_window_axis_ref=None,
	):
		"""Build geometry from a detector center, orientation and either size or pixel spacing."""
		height = int(detector_shape_hw[0])
		width = int(detector_shape_hw[1])
		if height <= 0 or width <= 0:
			raise ValueError("detector_shape_hw must contain positive height and width.")

		normal = _normalize_vector(detector_normal_ref)
		up = np.asarray(detector_up_ref, dtype=np.float32)
		up = up - normal * float(np.dot(up, normal))
		up = _normalize_vector(up)
		u_axis = _normalize_vector(np.cross(up, normal))
		v_axis = up

		if detector_pixel_size_mm is not None and detector_size_mm_hw is not None:
			raise ValueError("Provide either detector_pixel_size_mm or detector_size_mm_hw, not both.")
		if detector_pixel_size_mm is None and detector_size_mm_hw is None:
			raise ValueError("Either detector_pixel_size_mm or detector_size_mm_hw must be provided.")

		if detector_size_mm_hw is not None:
			size_h = float(detector_size_mm_hw[0])
			size_w = float(detector_size_mm_hw[1])
			if size_h <= 0.0 or size_w <= 0.0:
				raise ValueError("detector_size_mm_hw must contain positive physical dimensions.")
			pixel_size_v = size_h / float(height)
			pixel_size_u = size_w / float(width)
		else:
			if np.isscalar(detector_pixel_size_mm):
				pixel_size_u = float(detector_pixel_size_mm)
				pixel_size_v = float(detector_pixel_size_mm)
			else:
				pixel_size_u = float(detector_pixel_size_mm[0])
				pixel_size_v = float(detector_pixel_size_mm[1])
			if pixel_size_u <= 0.0 or pixel_size_v <= 0.0:
				raise ValueError("detector_pixel_size_mm must be positive.")

		detector_u_ref = u_axis * pixel_size_u
		detector_v_ref = v_axis * pixel_size_v
		detector_center_ref = np.asarray(detector_center_ref, dtype=np.float32)
		detector_origin_ref = (
			detector_center_ref
			- detector_u_ref * (float(width - 1) / 2.0)
			- detector_v_ref * (float(height - 1) / 2.0)
		)
		return cls(
			detector_origin_ref=detector_origin_ref.astype(np.float32),
			detector_u_ref=detector_u_ref.astype(np.float32),
			detector_v_ref=detector_v_ref.astype(np.float32),
			detector_shape_hw=[height, width],
			step_mm=float(step_mm),
			source_position_ref=source_position_ref,
			ray_direction_ref=ray_direction_ref,
			depth_window_mode=depth_window_mode,
			depth_window_mm=depth_window_mm,
			depth_window_origin_ref=depth_window_origin_ref,
			depth_window_axis_ref=depth_window_axis_ref,
		)

	def detector_pixel_size_mm_uv(self):
		"""Return detector pixel pitch along the `u` and `v` detector axes."""
		return (
			float(np.linalg.norm(np.asarray(self.detector_u_ref, dtype=np.float32))),
			float(np.linalg.norm(np.asarray(self.detector_v_ref, dtype=np.float32))),
		)

	def detector_size_mm_hw(self):
		"""Return the physical detector size in millimeters as `(height_mm, width_mm)`."""
		height, width = int(self.detector_shape_hw[0]), int(self.detector_shape_hw[1])
		pixel_size_u, pixel_size_v = self.detector_pixel_size_mm_uv()
		return float(height) * pixel_size_v, float(width) * pixel_size_u

	def detector_center_ref_point(self):
		"""Return the detector center point expressed in the geometry reference frame."""
		height, width = int(self.detector_shape_hw[0]), int(self.detector_shape_hw[1])
		return (
			np.asarray(self.detector_origin_ref, dtype=np.float32)
			+ np.asarray(self.detector_u_ref, dtype=np.float32) * (float(width - 1) / 2.0)
			+ np.asarray(self.detector_v_ref, dtype=np.float32) * (float(height - 1) / 2.0)
		).astype(np.float32)

	def detector_normal_ref_vector(self):
		"""Return the detector plane normal vector derived from the `u` and `v` axes."""
		return _normalize_vector(np.cross(
			np.asarray(self.detector_u_ref, dtype=np.float32),
			np.asarray(self.detector_v_ref, dtype=np.float32),
		))

	def is_cone_beam(self):
		"""Return `True` when the geometry is driven by a point source."""
		return self.source_position_ref is not None

	def is_parallel_beam(self):
		"""Return `True` when the geometry uses one shared ray direction."""
		return self.ray_direction_ref is not None

	def has_depth_window(self):
		"""Return `True` when the geometry requests depth-limited integration."""
		return self.depth_window_mode is not None and self.depth_window_mm is not None

	def normalized_depth_window_mode(self):
		"""Return the normalized depth-window mode string or `None`."""
		if self.depth_window_mode is None:
			return None
		mode = str(self.depth_window_mode).strip().lower()
		return mode or None

	def depth_window_limits_mm(self):
		"""Return sorted depth-window limits in millimetres or `None` when disabled."""
		if self.depth_window_mm is None:
			return None
		if len(self.depth_window_mm) != 2:
			raise ValueError("depth_window_mm must contain exactly two values.")
		depth_from = float(self.depth_window_mm[0])
		depth_to = float(self.depth_window_mm[1])
		return (min(depth_from, depth_to), max(depth_from, depth_to))

	def effective_depth_window_origin_ref(self):
		"""Return the planar depth-window origin or a detector-centred default."""
		if self.depth_window_origin_ref is not None:
			return np.asarray(self.depth_window_origin_ref, dtype=np.float32)
		return self.detector_center_ref_point()

	def effective_depth_window_axis_ref(self):
		"""Return the planar depth-window axis or the detector normal by default."""
		if self.depth_window_axis_ref is not None:
			return _normalize_vector(self.depth_window_axis_ref)
		return self.detector_normal_ref_vector()

	def with_quality_profile(self, quality_profile):
		"""Return a geometry copy modified by a quality profile."""
		if quality_profile is None:
			return replace(self)
		return quality_profile.apply_to_geometry(self)

	def validate(self):
		"""Validate geometry fields before projection."""
		height, width = int(self.detector_shape_hw[0]), int(self.detector_shape_hw[1])
		if height <= 0 or width <= 0:
			raise ValueError("detector_shape_hw must contain positive height and width.")
		if float(self.step_mm) <= 0.0:
			raise ValueError("step_mm must be positive.")
		if self.source_position_ref is None and self.ray_direction_ref is None:
			raise ValueError("Either source_position_ref or ray_direction_ref must be provided.")
		if self.source_position_ref is not None and self.ray_direction_ref is not None:
			raise ValueError("Geometry must define either source_position_ref or ray_direction_ref, not both.")
		if np.linalg.norm(np.asarray(self.detector_u_ref, dtype=np.float32)) <= 1e-8:
			raise ValueError("detector_u_ref must have a non-zero length.")
		if np.linalg.norm(np.asarray(self.detector_v_ref, dtype=np.float32)) <= 1e-8:
			raise ValueError("detector_v_ref must have a non-zero length.")
		depth_mode = self.normalized_depth_window_mode()
		depth_limits = self.depth_window_limits_mm()
		if depth_mode is None:
			if depth_limits is not None:
				raise ValueError("depth_window_mm requires depth_window_mode to be enabled.")
			return
		if depth_limits is None:
			raise ValueError("depth_window_mode requires depth_window_mm to be provided.")
		if depth_mode not in {"ray", "planar"}:
			raise ValueError("depth_window_mode must be one of: 'ray', 'planar'.")
		if depth_mode == "planar":
			if np.linalg.norm(np.asarray(self.effective_depth_window_axis_ref(), dtype=np.float32)) <= 1e-8:
				raise ValueError("depth_window_axis_ref must have a non-zero length for planar depth windows.")


@dataclass
class XRayPhysicsModel:
	"""Map scalar values to attenuation and convert integrals into detector intensities."""

	mu_air: float = 0.0
	mu_water: float = 0.02
	hounsfield_air: float = -1000.0
	attenuation_scale: float = 1.0
	source_energy_kev: float = 70.0
	reference_energy_kev: float = 70.0
	attenuation_energy_exponent: float = 2.0
	output_mode: str = "integral"
	intensity_floor: float = 0.0
	source_distance_falloff_mode: str = "none"
	source_distance_reference_mm: float | None = None
	source_distance_power: float = 2.0
	material_response_mode: str = "linear"
	bone_threshold_hu: float | None = None
	bone_threshold_softness: float = 250.0
	material_window_center: float | None = None
	material_window_width: float | None = None
	material_window_mode: str = "hard"
	material_window_softness: float = 150.0

	def attenuation_energy_scale(self):
		"""Return one heuristic scale factor that decreases attenuation for higher source energy."""
		source_energy = max(1e-6, float(self.source_energy_kev))
		reference_energy = max(1e-6, float(self.reference_energy_kev))
		exponent = max(0.0, float(self.attenuation_energy_exponent))
		return float((reference_energy / source_energy) ** exponent)

	def scalar_to_mu(self, scalar_values):
		"""Convert scalar CT-like values into a linear attenuation coefficient."""
		scalar_values = np.asarray(scalar_values, dtype=np.float32)
		energy_scale = self.attenuation_energy_scale()
		mode = str(self.material_response_mode).lower()
		if mode == "piecewise_bone":
			mu = self._scalar_to_mu_piecewise_bone(scalar_values, energy_scale=energy_scale)
		elif mode == "piecewise_soft_tissue":
			mu = self._scalar_to_mu_piecewise_soft_tissue(scalar_values, energy_scale=energy_scale)
		elif mode == "bone_threshold":
			mu = self._scalar_to_mu_bone_threshold(scalar_values, energy_scale=energy_scale)
		else:
			relative_density = np.maximum(0.0, 1.0 + scalar_values / abs(float(self.hounsfield_air)))
			mu = (float(self.mu_air) + float(self.mu_water) * relative_density) * float(self.attenuation_scale) * energy_scale
		if self.material_window_center is not None and self.material_window_width is not None and float(self.material_window_width) > 0.0:
			vmin = float(self.material_window_center) - float(self.material_window_width) / 2.0
			vmax = float(self.material_window_center) + float(self.material_window_width) / 2.0
			mode = str(self.material_window_mode).lower()
			softness = max(1e-6, float(self.material_window_softness))
			if mode == "linear":
				lower = np.clip((scalar_values - (vmin - softness)) / softness, 0.0, 1.0)
				upper = np.clip(((vmax + softness) - scalar_values) / softness, 0.0, 1.0)
				weight = lower * upper
			elif mode == "sigmoid":
				lower = 1.0 / (1.0 + np.exp(-(scalar_values - vmin) / softness))
				upper = 1.0 / (1.0 + np.exp((scalar_values - vmax) / softness))
				weight = lower * upper
			else:
				weight = ((scalar_values >= vmin) & (scalar_values <= vmax)).astype(np.float32)
			mu = mu * weight.astype(np.float32, copy=False)
		return mu

	def _piecewise_linear_map(self, scalar_values, control_points):
		"""Map scalar values with a piecewise-linear attenuation curve."""
		xp = np.asarray([point[0] for point in control_points], dtype=np.float32)
		fp = np.asarray([point[1] for point in control_points], dtype=np.float32)
		return np.interp(scalar_values, xp, fp, left=fp[0], right=fp[-1]).astype(np.float32, copy=False)

	def _scalar_to_mu_piecewise_bone(self, scalar_values, energy_scale=1.0):
		"""Return one bone-emphasis attenuation curve tuned for craniofacial structures."""
		base = float(self.mu_water) * float(self.attenuation_scale) * float(energy_scale)
		control_points = [
			(-1000.0, float(self.mu_air)),
			(-300.0, 0.03 * base),
			(0.0, 0.10 * base),
			(150.0, 0.18 * base),
			(400.0, 0.35 * base),
			(800.0, 0.75 * base),
			(1200.0, 1.20 * base),
			(2000.0, 1.85 * base),
			(3000.0, 2.30 * base),
			(4000.0, 2.60 * base),
		]
		return self._piecewise_linear_map(scalar_values, control_points)

	def _scalar_to_mu_piecewise_soft_tissue(self, scalar_values, energy_scale=1.0):
		"""Return one soft-tissue-oriented attenuation curve with reduced bone dominance."""
		base = float(self.mu_water) * float(self.attenuation_scale) * float(energy_scale)
		control_points = [
			(-1000.0, float(self.mu_air)),
			(-300.0, 0.05 * base),
			(0.0, 0.45 * base),
			(80.0, 0.70 * base),
			(200.0, 0.85 * base),
			(500.0, 1.05 * base),
			(1000.0, 1.20 * base),
			(2000.0, 1.35 * base),
			(4000.0, 1.55 * base),
		]
		return self._piecewise_linear_map(scalar_values, control_points)

	def _scalar_to_mu_bone_threshold(self, scalar_values, energy_scale=1.0):
		"""Blend one neutral attenuation model with a bone-emphasis model above an HU threshold."""
		relative_density = np.maximum(0.0, 1.0 + scalar_values / abs(float(self.hounsfield_air)))
		linear_mu = (float(self.mu_air) + float(self.mu_water) * relative_density) * float(self.attenuation_scale) * float(energy_scale)
		bone_mu = self._scalar_to_mu_piecewise_bone(scalar_values, energy_scale=energy_scale)
		threshold = 350.0 if self.bone_threshold_hu is None else float(self.bone_threshold_hu)
		softness = max(1e-6, float(self.bone_threshold_softness))
		weight = 1.0 / (1.0 + np.exp(-(scalar_values - threshold) / softness))
		soft_tissue_mix = 0.85
		return (
			linear_mu * (1.0 - soft_tissue_mix * weight)
			+ bone_mu * weight
		).astype(np.float32, copy=False)

	def source_distance_gain(self, source_to_detector_distance_mm, projection_mode=None):
		"""Return one multiplicative detector gain caused by distance from the source."""
		if source_to_detector_distance_mm is None:
			return None
		if projection_mode is not None and str(projection_mode).lower() != "cone":
			return None
		mode = str(self.source_distance_falloff_mode).strip().lower()
		if mode in {"", "none", "off"}:
			return None
		if mode != "inverse_square":
			raise ValueError("source_distance_falloff_mode must be one of: 'none', 'inverse_square'.")
		distances = np.asarray(source_to_detector_distance_mm, dtype=np.float32)
		reference_distance = self.source_distance_reference_mm
		if reference_distance is None or float(reference_distance) <= 0.0:
			finite_distances = distances[np.isfinite(distances) & (distances > 0.0)]
			if finite_distances.size == 0:
				return None
			reference_distance = float(np.median(finite_distances))
		reference_distance = max(1e-6, float(reference_distance))
		power = max(0.0, float(self.source_distance_power))
		safe_distances = np.maximum(distances, 1e-6)
		return np.power(reference_distance / safe_distances, power).astype(np.float32, copy=False)

	def integral_to_image(self, line_integral, source_to_detector_distance_mm=None, projection_mode=None):
		"""Convert integrated attenuation into a detector-space image value."""
		line_integral = np.asarray(line_integral, dtype=np.float32)
		distance_gain = self.source_distance_gain(
			source_to_detector_distance_mm=source_to_detector_distance_mm,
			projection_mode=projection_mode,
		)
		mode = str(self.output_mode).lower()
		if mode == "integral":
			if distance_gain is None:
				return line_integral
			safe_gain = np.maximum(distance_gain, 1e-12)
			return line_integral - np.log(safe_gain)
		intensity = np.exp(-line_integral)
		if distance_gain is not None:
			intensity = intensity * distance_gain
		return np.maximum(float(self.intensity_floor), intensity)


@dataclass
class XRayProjectionQualityProfile:
	"""Describe a reusable quality preset that modifies geometry sampling density."""

	name: str
	step_mm: float | None = None
	detector_downsample: int = 1

	@classmethod
	def draft(cls):
		"""Return a low-cost profile useful for quick geometry debugging."""
		return cls(name="draft", step_mm=2.0, detector_downsample=2)

	@classmethod
	def normal(cls):
		"""Return a balanced profile for standard interactive work."""
		return cls(name="normal", step_mm=1.0, detector_downsample=1)

	@classmethod
	def high(cls):
		"""Return a high-quality profile prioritizing detail over runtime."""
		return cls(name="high", step_mm=0.5, detector_downsample=1)

	def apply_to_geometry(self, geometry):
		"""Return a geometry copy with detector sampling and ray step adapted to this profile."""
		geometry = replace(geometry)
		downsample = max(1, int(self.detector_downsample))
		if downsample > 1:
			height = max(1, int(np.ceil(int(geometry.detector_shape_hw[0]) / float(downsample))))
			width = max(1, int(np.ceil(int(geometry.detector_shape_hw[1]) / float(downsample))))
			geometry = replace(
				geometry,
				detector_shape_hw=[height, width],
				detector_u_ref=np.asarray(geometry.detector_u_ref, dtype=np.float32) * float(downsample),
				detector_v_ref=np.asarray(geometry.detector_v_ref, dtype=np.float32) * float(downsample),
			)
		if self.step_mm is not None:
			geometry = replace(geometry, step_mm=float(self.step_mm))
		return geometry


@dataclass
class XRayProjectionConfig:
	"""Bundle projection geometry, physics and optional presentation into one scenario."""

	geometry: XRayProjectionGeometry
	physics_model: XRayPhysicsModel
	presentation_model: XRayPresentationModel | None = None
	reference_transform: np.ndarray = field(default_factory=_identity_matrix)
	quality_profile: XRayProjectionQualityProfile | None = None

	def effective_geometry(self):
		"""Return the geometry after applying any quality profile override."""
		return self.geometry.with_quality_profile(self.quality_profile)

	def apply_presentation(self, image):
		"""Return either the raw image or a presentation-mapped view of it."""
		if self.presentation_model is None:
			return np.asarray(image, dtype=np.float32)
		return self.presentation_model.apply(image)


@dataclass
class XRayProjectionStats:
	"""Collect basic runtime and workload statistics for one projection call."""

	elapsed_seconds: float
	total_pixels: int
	traced_pixels: int
	total_sample_count: int
	source_count: int
	step_mm: float
	projection_mode: str
	detector_shape_hw: tuple[int, int]
	depth_window_mode: str | None = None
	# Per-phase wall-clock timing breakdown (phase_name -> seconds).
	# Keys: "ray_setup", "aabb_intersection", "depth_clipping",
	#       "direct_sources_total", "marching_total", "physics_conversion".
	phase_timings: dict = field(default_factory=dict)
	# Per-source statistics — one dict per XRaySampleSource in scene order.
	# Volumetric keys: "label", "source_type", "elapsed_s", "work_count",
	#   "volume_shape", "interpolation".
	# Mesh keys additionally: "backend", "mode", "triangle_count",
	#   "bvh_build_s" (analytic_bvh only), "stack_build_s", "stack_uv_projection_s",
	#   "stack_rasterize_s", "stack_csr_s", "integration_s".
	per_source_stats: list = field(default_factory=list)

	@property
	def average_samples_per_traced_pixel(self):
		"""Return the average sample count over rays that crossed the scene bounds."""
		if self.traced_pixels <= 0:
			return 0.0
		return float(self.total_sample_count) / float(self.traced_pixels)

	@property
	def samples_per_second(self):
		"""Return the effective throughput in attenuation samples per second."""
		if self.elapsed_seconds <= 1e-9:
			return 0.0
		return float(self.total_sample_count) / float(self.elapsed_seconds)

	@property
	def rays_per_second(self):
		"""Return the number of traced rays (pixels that hit the scene AABB) per second."""
		if self.elapsed_seconds <= 1e-9:
			return 0.0
		return float(self.traced_pixels) / float(self.elapsed_seconds)

	def format_report(self):
		"""Return a formatted multi-line performance report suitable for building tables."""
		lines = []
		h, w = self.detector_shape_hw
		lines.append("=== XRay Projection Performance Report ===")
		lines.append(f"  Detector:          {w} x {h} px  ({self.total_pixels:,} total)")
		lines.append(f"  Traced pixels:     {self.traced_pixels:,}  ({100.0 * self.traced_pixels / max(self.total_pixels, 1):.1f} %)")
		lines.append(f"  Step:              {self.step_mm:.2f} mm")
		lines.append(f"  Projection mode:   {self.projection_mode}")
		lines.append(f"  Sources:           {self.source_count}")
		lines.append(f"  Total samples:     {self.total_sample_count:,}")
		lines.append(f"  Samples/s:         {self.samples_per_second:,.0f}")
		lines.append(f"  Avg samples/ray:   {self.average_samples_per_traced_pixel:.1f}")
		lines.append(f"  Total elapsed:     {self.elapsed_seconds * 1000:.1f} ms")
		if self.phase_timings:
			lines.append("  --- Phase breakdown ---")
			phase_total = sum(self.phase_timings.values())
			for phase_name, t_s in self.phase_timings.items():
				pct = 100.0 * t_s / max(phase_total, 1e-9)
				lines.append(f"    {phase_name:<30s} {t_s * 1000:8.1f} ms  ({pct:.1f} %)")
		if self.per_source_stats:
			lines.append("  --- Per-source breakdown ---")
			for i, src in enumerate(self.per_source_stats):
				label = src.get("label", f"source_{i}")
				stype = src.get("source_type", "?")
				t_s   = src.get("elapsed_s", 0.0)
				wc    = src.get("work_count", 0)
				lines.append(f"    [{i}] {stype:<24s} '{label}'  {t_s * 1000:.1f} ms  work={wc:,}")
				if src.get("backend") is not None:
					lines.append(f"         backend={src['backend']}  mode={src.get('mode', '?')}  triangles={src.get('triangle_count', '?'):,}")
				if src.get("volume_shape") is not None:
					lines.append(f"         volume_shape={src['volume_shape']}  interpolation={src.get('interpolation', '?')}")
				for sub_key in ("bvh_build_s", "stack_build_s", "stack_uv_projection_s",
				                "stack_rasterize_s", "stack_csr_s", "integration_s"):
					if sub_key in src:
						lines.append(f"         {sub_key:<28s} {src[sub_key] * 1000:.1f} ms")
		lines.append("==========================================")
		return "\n".join(lines)

	def print_report(self):
		"""Print the formatted performance report to stdout."""
		print(self.format_report())


@dataclass
class ProjectedTrianglePixelStack:
	"""Store one memory-compact per-pixel stack of mesh-triangle intersection samples."""

	detector_shape_hw: tuple[int, int]
	pixel_offsets: np.ndarray
	sample_t: np.ndarray
	sample_triangle_index: np.ndarray
	sample_shell_gain: np.ndarray

	@property
	def sample_count(self):
		"""Return the total number of stored per-pixel intersection samples."""
		return int(self.sample_t.shape[0])

	def pixel_sample_slice(self, pixel_index):
		"""Return the half-open slice bounds inside the flat sample arrays for one pixel."""
		start = int(self.pixel_offsets[int(pixel_index)])
		end = int(self.pixel_offsets[int(pixel_index) + 1])
		return start, end


@dataclass
class XRayScene:
	"""Own the set of sources taking part in one X-ray acquisition scenario."""

	sample_sources: list[XRaySampleSource]

	@classmethod
	def from_sample_sources(cls, sample_sources):
		"""Build a scene from already prepared X-ray sample sources."""
		return cls(sample_sources=list(sample_sources))

	@classmethod
	def from_volumetrics(cls, volumetric_entries):
		"""Build a scene directly from volumetric objects and optional transforms."""
		sample_sources = []
		for entry in volumetric_entries:
			if isinstance(entry, VolumetricXRaySource):
				sample_sources.append(entry)
				continue
			if isinstance(entry, Volumetric):
				sample_sources.append(VolumetricXRaySource(entry))
				continue
			if not isinstance(entry, Sequence) or len(entry) == 0:
				raise TypeError("Each volumetric entry must be a Volumetric, VolumetricXRaySource or a configuration tuple.")
			volumetric = entry[0]
			global_transform = entry[1] if len(entry) > 1 else None
			interpolation = entry[2] if len(entry) > 2 else "linear"
			fill_value = entry[3] if len(entry) > 3 else None
			sample_sources.append(VolumetricXRaySource(
				volumetric=volumetric,
				global_transform=global_transform,
				interpolation=interpolation,
				fill_value=fill_value,
			))
		return cls(sample_sources=sample_sources)

	def build_projector(self):
		"""Return a projector bound to the sources stored in this scene."""
		return XRayProjector(self.sample_sources)

	def project(self, config, return_stats=False, progress_callback=None):
		"""Project the scene using a single combined configuration object."""
		return self.build_projector().project_config(config=config, return_stats=return_stats, progress_callback=progress_callback)

	def render(self, config, return_stats=False, progress_callback=None):
		"""Project the scene and optionally apply the configured presentation model."""
		if return_stats:
			raw_image, stats = self.project(config=config, return_stats=True, progress_callback=progress_callback)
			return config.apply_presentation(raw_image), stats
		return config.apply_presentation(self.project(config=config, return_stats=False, progress_callback=progress_callback))


class XRaySampleSource(ABC):
	"""Abstract RTG source that can provide attenuation samples in world coordinates."""

	@abstractmethod
	def bounds_world(self):
		"""Return source world bounds as `(min_xyz, max_xyz)`."""

	@abstractmethod
	def sample_attenuation_world(self, points_world, physics_model):
		"""Return attenuation coefficients sampled at `points_world`."""

	def ray_integral_world(self, ray_origins, ray_directions, t_starts, t_ends, physics_model, step_mm,
	                      progress_callback=None, progress_fraction=(0.0, 1.0),
	                      geometry=None, reference_transform=None, hit_ray_indices=None, detector_shape_hw=None):
		"""Optionally return direct line-integral contributions for full rays.

		Sources with analytic or surface-based behaviour can override this hook and
		return a tuple `(integrals, work_item_count)`. Point-sampled volumetric
		sources should keep the default `None` and will be integrated by ray
		marching in `XRayProjector`.
		"""
		return None

	def uses_direct_integral(self):
		"""Return True when this source provides direct line integrals via ray_integral_world.

		Override in subclasses that implement ray_integral_world. The projector uses
		this to classify sources into 'direct' (analytic/Siddon) vs 'marched' buckets
		without relying on method-identity comparisons.
		"""
		return False
		return None


class VolumetricXRaySource(XRaySampleSource):
	"""Adapt a `Volumetric` object into a world-space X-ray attenuation source."""

	def __init__(self, volumetric, global_transform=None, interpolation="linear", fill_value=None, scalar_preprocessor=None,
	             scalar_scale=1.0, scalar_bias=0.0, attenuation_multiplier=1.0, volume_backend="sampling"):
		"""Store volumetric data and transformation used for world-space sampling."""
		if not isinstance(volumetric, Volumetric):
			raise TypeError("volumetric must be an instance of Volumetric.")

		self.volumetric = volumetric
		self.global_transform = np.eye(4, dtype=np.float32) if global_transform is None else np.asarray(global_transform, dtype=np.float32)
		if self.global_transform.shape != (4, 4):
			raise ValueError("global_transform must be a 4x4 homogeneous matrix.")

		self.interpolation = str(interpolation).lower()
		default_fill = float(getattr(volumetric, 'm_min', -1000.0))
		self.fill_value = float(default_fill if fill_value is None else fill_value)
		self._inverse_global_transform = np.linalg.inv(self.global_transform)
		self._volume = np.asarray(self.volumetric.m_volume, dtype=np.float32)
		self.scalar_preprocessor = scalar_preprocessor
		self.scalar_scale = float(scalar_scale)
		self.scalar_bias = float(scalar_bias)
		self.attenuation_multiplier = float(attenuation_multiplier)
		self.volume_backend = str(volume_backend).lower()
		if self.volume_backend not in {"sampling", "siddon"}:
			raise ValueError("volume_backend must be 'sampling' or 'siddon'.")
		self._scalar_stats = None if scalar_preprocessor is None else scalar_preprocessor.estimate_volume_stats(self._volume)

	def bounds_world(self):
		"""Return the world-space axis-aligned bounding box of the transformed volume."""
		corners = Volumetric._volume_corners_world(self.volumetric, global_transform=self.global_transform)
		return corners.min(axis=0).astype(np.float32), corners.max(axis=0).astype(np.float32)

	def sample_scalar_world(self, points_world):
		"""Sample scalar voxel values at world-space points."""
		points_world = np.asarray(points_world, dtype=np.float32)
		local_world = self.volumetric._transform_world_points(points_world.T, self._inverse_global_transform).T
		points_voxel = self.volumetric.world_to_voxel(local_world.T).T
		order = {"nearest": 0, "linear": 1, "cubic": 3}.get(self.interpolation, 1)
		sampled = map_coordinates(
			self._volume,
			[
				points_voxel[:, 2],
				points_voxel[:, 1],
				points_voxel[:, 0],
			],
			order=order,
			mode='constant',
			cval=self.fill_value,
		).astype(np.float32, copy=False)
		if self.scalar_preprocessor is None:
			return sampled * self.scalar_scale + self.scalar_bias
		sampled = self.scalar_preprocessor.apply(sampled, self._scalar_stats)
		return sampled * self.scalar_scale + self.scalar_bias

	def sample_attenuation_world(self, points_world, physics_model):
		"""Sample attenuation coefficients in world coordinates using the supplied physics model."""
		return physics_model.scalar_to_mu(self.sample_scalar_world(points_world)) * self.attenuation_multiplier

	def _siddon_integral_vectorized(
		self,
		ray_origins_world,
		ray_directions_world,
		t_starts,
		t_ends,
		physics_model,
		progress_callback=None,
		progress_fraction=(0.0, 1.0),
	):
		"""Analytically integrate attenuation using the Siddon exact voxel-traversal algorithm.

		For every active ray the method computes the exact chord length inside each
		traversed voxel by collecting all voxel-boundary plane crossings along each
		axis, sorting them, and accumulating ``mu * chord_length`` per segment.
		The result is fully independent of any step-size parameter.

		Assumptions
		-----------
		* ``global_transform`` is a rigid (rotation + translation) transform so
		  the ray parameter ``t`` stays in world-millimetres after the local-space
		  change of coordinates.
		* The volume grid is an axis-aligned lattice in the local frame returned
		  by ``Volumetric.get_volume_geometry()``.

		Args:
			ray_origins_world:    (N, 3) float32 ray origins in world space.
			ray_directions_world: (N, 3) float32 unit ray directions in world mm.
			t_starts:             (N,) float32 entry parametric distances (mm).
			t_ends:               (N,) float32 exit parametric distances (mm).
			physics_model:        ``XRayPhysicsModel`` instance.
			progress_callback:    Optional callable receiving progress in [0, 1].
			progress_fraction:    (start, end) fraction of the overall progress bar
			                      assigned to this source.

		Returns:
			(N,) float32 line integrals in the same order as the input rays.
		"""
		N = int(ray_origins_world.shape[0])
		if N == 0:
			return np.empty((0,), dtype=np.float32)
		integrals = np.zeros(N, dtype=np.float32)

		# --- Volume geometry in local space ---------------------------------
		origin, basis, spacing = self.volumetric.get_volume_geometry()
		origin  = origin.astype(np.float64)
		basis   = basis.astype(np.float64)
		spacing = spacing.astype(np.float64)
		# T maps fractional voxel index -> local-space offset:
		#   local_point = origin + T @ voxel_idx
		T     = basis * spacing[np.newaxis, :]  # (3, 3) = basis @ diag(spacing)
		T_inv = np.linalg.inv(T)               # (3, 3)

		vol_shape = self._volume.shape  # (Nz, Ny, Nx)
		Nz, Ny, Nx = int(vol_shape[0]), int(vol_shape[1]), int(vol_shape[2])
		NyNx     = Ny * Nx
		vol_flat = self._volume.ravel()  # (Nz*Ny*Nx,) read-only view

		# --- Transform rays: world -> local -> voxel-index space -----------
		inv_g = self._inverse_global_transform.astype(np.float64)
		R_inv = inv_g[:3, :3]  # rotation part
		t_inv = inv_g[:3, 3]   # translation part

		# world -> local  (rigid: only rotation + translation)
		o_l = ray_origins_world.astype(np.float64) @ R_inv.T + t_inv[np.newaxis, :]  # (N, 3)
		d_l = ray_directions_world.astype(np.float64) @ R_inv.T                        # (N, 3)

		# local -> voxel-index:
		#   o_v = T_inv @ (o_l - origin),  d_v = T_inv @ d_l
		o_v = (o_l - origin[np.newaxis, :]) @ T_inv.T  # (N, 3)  fractional (x, y, z)
		d_v = d_l @ T_inv.T                             # (N, 3)  voxel-units per world-mm

		# --- Pre-build grid-boundary arrays --------------------------------
		# Boundaries are at integer voxel indices 0, 1, ..., Na for axis a.
		kx = np.arange(0, Nx + 1, dtype=np.float64)  # (Nx+1,)
		ky = np.arange(0, Ny + 1, dtype=np.float64)  # (Ny+1,)
		kz = np.arange(0, Nz + 1, dtype=np.float64)  # (Nz+1,)
		n_cross = (Nx + 1) + (Ny + 1) + (Nz + 1)  # max plane crossings per ray

		# Adaptive chunk size: target ~16 MB for t_all (float64 = 8 bytes)
		chunk_size = max(64, min(1024, int(16 * 1024 * 1024 // max(n_cross * 8, 1))))

		_INF = np.float64(1e30)
		_EPS = np.float64(1e-7)

		n_chunks = (N + chunk_size - 1) // chunk_size
		_last_progress_clock = perf_counter()

		for ci in range(n_chunks):
			if progress_callback is not None and perf_counter() - _last_progress_clock >= 0.15:
				_last_progress_clock = perf_counter()
				frac = float(ci) / float(max(n_chunks, 1))
				progress_callback(
					progress_fraction[0] + (progress_fraction[1] - progress_fraction[0]) * frac
				)

			cs = ci * chunk_size
			ce = min(cs + chunk_size, N)
			n  = ce - cs

			ov = o_v[cs:ce]                         # (n, 3)
			dv = d_v[cs:ce]                         # (n, 3)
			ts = t_starts[cs:ce].astype(np.float64) # (n,)
			te = t_ends[cs:ce].astype(np.float64)   # (n,)

			# X-axis boundary crossings: tx[i,k] = (kx[k] - ov[i,0]) / dv[i,0]
			# np.errstate suppresses harmless div-by-zero / NaN warnings that arise
			# because np.where evaluates both branches before applying the mask.
			dv_x = dv[:, 0:1]  # (n, 1)
			with np.errstate(divide='ignore', invalid='ignore'):
				tx = np.where(
					np.abs(dv_x) > 1e-12,
					(kx[np.newaxis, :] - ov[:, 0:1]) / dv_x,
					_INF,
				)  # (n, Nx+1)

			# Y-axis boundary crossings
			dv_y = dv[:, 1:2]
			with np.errstate(divide='ignore', invalid='ignore'):
				ty = np.where(
					np.abs(dv_y) > 1e-12,
					(ky[np.newaxis, :] - ov[:, 1:2]) / dv_y,
					_INF,
				)  # (n, Ny+1)

			# Z-axis boundary crossings
			dv_z = dv[:, 2:3]
			with np.errstate(divide='ignore', invalid='ignore'):
				tz = np.where(
					np.abs(dv_z) > 1e-12,
					(kz[np.newaxis, :] - ov[:, 2:3]) / dv_z,
					_INF,
				)  # (n, Nz+1)

			# Merge all boundary t-values plus the ray entry and exit endpoints.
			# Shape: (n, n_cross + 2)
			t_all = np.concatenate(
				[tx, ty, tz, ts[:, np.newaxis], te[:, np.newaxis]], axis=1
			)

			# Discard crossings outside the active ray segment → push to +INF.
			ts_b = ts[:, np.newaxis]
			te_b = te[:, np.newaxis]
			t_all = np.where(
				(t_all >= ts_b - _EPS) & (t_all <= te_b + _EPS), t_all, _INF
			)

			# Sort ascending; +INF values migrate to the right end.
			t_all.sort(axis=1)

			# Adjacent pairs define voxel chord segments.
			t_left  = t_all[:, :-1]           # (n, n_cross+1)
			t_right = t_all[:, 1:]            # (n, n_cross+1)
			dl    = t_right - t_left          # chord lengths in world-mm
			t_mid = 0.5 * (t_left + t_right)  # midpoint parameter

			# Valid segment: positive chord length and not in the +INF tail.
			seg_valid = (dl > 1e-10) & (t_mid < _INF * 0.5)

			if not np.any(seg_valid):
				continue

			# Voxel indices at segment midpoints (in voxel-index space x,y,z).
			pt_x = ov[:, 0:1] + t_mid * dv[:, 0:1]  # (n, n_cross+1)
			pt_y = ov[:, 1:2] + t_mid * dv[:, 1:2]
			pt_z = ov[:, 2:3] + t_mid * dv[:, 2:3]

			# Floor + cast: +INF slots produce garbage int values but are masked
			# by `seg_valid`; suppress the unavoidable invalid-cast warning.
			with np.errstate(invalid='ignore'):
				ix = np.floor(pt_x).astype(np.int32, casting='unsafe')
				iy = np.floor(pt_y).astype(np.int32, casting='unsafe')
				iz = np.floor(pt_z).astype(np.int32, casting='unsafe')

			idx_valid = (
				(ix >= 0) & (ix < Nx) &
				(iy >= 0) & (iy < Ny) &
				(iz >= 0) & (iz < Nz)
			)
			valid = seg_valid & idx_valid

			if not np.any(valid):
				continue

			# Flat index in volume array: volume[iz, iy, ix]
			# Use 0 for invalid positions (result masked out below).
			lin_idx = np.where(valid, iz * NyNx + iy * Nx + ix, 0)  # (n, n_cross+1)

			scalar_values = vol_flat[lin_idx].astype(np.float32)  # (n, n_cross+1)

			if self.scalar_preprocessor is not None:
				scalar_values = self.scalar_preprocessor.apply(scalar_values, self._scalar_stats)
			scalar_values = scalar_values * self.scalar_scale + self.scalar_bias

			mu = physics_model.scalar_to_mu(scalar_values) * self.attenuation_multiplier

			# Integrate: accumulate mu * dl for valid segments.
			mu_dl = np.where(valid, mu * dl.astype(np.float32), 0.0)
			integrals[cs:ce] = mu_dl.sum(axis=1).astype(np.float32)

		return integrals

	def uses_direct_integral(self):
		"""Return True only when the Siddon backend is active."""
		return self.volume_backend == "siddon"

	def ray_integral_world(
		self, ray_origins, ray_directions, t_starts, t_ends, physics_model, step_mm,
		progress_callback=None, progress_fraction=(0.0, 1.0),
		geometry=None, reference_transform=None, hit_ray_indices=None, detector_shape_hw=None,
	):
		"""Return Siddon line integrals when the 'siddon' volume backend is active.

		When ``volume_backend == 'sampling'`` this method returns ``None`` and
		the projector falls back to the standard vectorised slab-marching loop.
		"""
		if self.volume_backend != "siddon":
			return None
		integrals = self._siddon_integral_vectorized(
			ray_origins_world=ray_origins,
			ray_directions_world=ray_directions,
			t_starts=t_starts,
			t_ends=t_ends,
			physics_model=physics_model,
			progress_callback=progress_callback,
			progress_fraction=progress_fraction,
		)
		return integrals, int(ray_origins.shape[0])


class MeshXRaySource(XRaySampleSource):
	"""Adapt one closed triangle mesh into a simplified solid or shell X-ray source."""

	def __init__(self, mesh, global_transform=None, scalar_value=2000.0, mode="solid", shell_thickness_mm=1.0,
	             scalar_scale=1.0, scalar_bias=0.0, attenuation_multiplier=1.0, backend="analytic_bvh"):
		"""Store mesh geometry and one simplified material model for X-ray projection.

		The current implementation assumes triangle faces define either:
		- one closed solid of constant attenuation (`mode="solid"`), or
		- one thin radiopaque shell (`mode="shell"`).
		"""
		if not isinstance(mesh, Mesh):
			raise TypeError("mesh must be an instance of Mesh.")

		self.mesh = mesh
		self.global_transform = np.eye(4, dtype=np.float32) if global_transform is None else np.asarray(global_transform, dtype=np.float32)
		if self.global_transform.shape != (4, 4):
			raise ValueError("global_transform must be a 4x4 homogeneous matrix.")

		self.scalar_value = float(scalar_value)
		self.mode = str(mode).strip().lower()
		self.shell_thickness_mm = max(1e-4, float(shell_thickness_mm))
		self.scalar_scale = float(scalar_scale)
		self.scalar_bias = float(scalar_bias)
		self.attenuation_multiplier = float(attenuation_multiplier)
		self.backend = str(backend).strip().lower()
		self.projected_min_abs_cos = max(0.0, min(1.0, float(getattr(self.mesh, "xray_projected_min_abs_cos", 0.0))))
		self.debug_export_dir = getattr(self.mesh, "xray_debug_export_dir", None)
		self.debug_compare_analytic = bool(getattr(self.mesh, "xray_debug_compare_analytic", True))
		if self.mode not in {"solid", "shell"}:
			raise ValueError("mode must be either 'solid' or 'shell'.")
		if self.backend not in {"analytic_bvh", "projected_intersection_list"}:
			raise ValueError("backend must be either 'analytic_bvh' or 'projected_intersection_list'.")

		vertices_world = _transform_points(self.global_transform, np.asarray(self.mesh.m_vertices, dtype=np.float32))
		faces = np.asarray(self.mesh.m_faces, dtype=np.int32)
		self._vertices_world = vertices_world
		self._faces = faces
		self._triangles_world = vertices_world[faces] if faces.size else np.empty((0, 3, 3), dtype=np.float32)
		if getattr(self.mesh, "m_vnormals", None) is not None and np.asarray(self.mesh.m_vnormals).shape == self._vertices_world.shape:
			vertex_normals_world = _transform_points(
				np.block([
					[self.global_transform[:3, :3], np.zeros((3, 1), dtype=np.float32)],
					[np.zeros((1, 3), dtype=np.float32), np.ones((1, 1), dtype=np.float32)],
				]),
				np.asarray(self.mesh.m_vnormals, dtype=np.float32),
			)
			vertex_normals_world /= np.maximum(np.linalg.norm(vertex_normals_world, axis=1, keepdims=True), 1e-8)
			self._vertex_normals_world = vertex_normals_world.astype(np.float32, copy=False)
		else:
			self._vertex_normals_world = np.empty((0, 3), dtype=np.float32)
		self._triangle_vertex_normals_world = (
			self._vertex_normals_world[faces]
			if self._vertex_normals_world.shape[0] == self._vertices_world.shape[0] and faces.size
			else np.empty((0, 3, 3), dtype=np.float32)
		)
		if self._triangles_world.shape[0] > 0:
			face_normals = np.cross(
				self._triangles_world[:, 1, :] - self._triangles_world[:, 0, :],
				self._triangles_world[:, 2, :] - self._triangles_world[:, 0, :],
			)
			face_normals /= np.maximum(np.linalg.norm(face_normals, axis=1, keepdims=True), 1e-8)
			self._face_normals_world = face_normals.astype(np.float32, copy=False)
		else:
			self._face_normals_world = np.empty((0, 3), dtype=np.float32)
		# BVH is built lazily on first use (not needed for projected_intersection_list backend).
		self._bvh_nodes = None
		self._projected_stack_cache = {}
		# Persistent thread pool — reused across projection calls to amortise
		# OS thread-creation overhead (~150 ms/thread on Windows).
		self._thread_pool: "ThreadPoolExecutor | None" = None
		self._thread_pool_workers: int = 0

	def _ensure_bvh(self):
		"""Build the BVH on first call; no-op on subsequent calls."""
		if self._bvh_nodes is not None:
			return
		_t_bvh = perf_counter()
		_log.info("MeshXRaySource: building BVH for %d triangles …", self._triangles_world.shape[0])
		self._bvh_nodes = _build_triangle_bvh(self._triangles_world, max_leaf_size=8)
		self._last_bvh_build_s = float(perf_counter() - _t_bvh)
		_log.info("MeshXRaySource: BVH built in %.3f s (%d nodes)",
		          self._last_bvh_build_s, len(self._bvh_nodes))

	def bounds_world(self):
		"""Return the world-space AABB of the transformed mesh vertices."""
		if self._vertices_world.size == 0:
			zero = np.zeros(3, dtype=np.float32)
			return zero.copy(), zero.copy()
		return self._vertices_world.min(axis=0).astype(np.float32), self._vertices_world.max(axis=0).astype(np.float32)

	def sample_attenuation_world(self, points_world, physics_model):
		"""Mesh sources are integrated analytically per ray and do not support point sampling."""
		points_world = np.asarray(points_world, dtype=np.float32)
		return np.zeros(points_world.shape[0], dtype=np.float32)

	def _projected_stack_cache_key(self, geometry, reference_transform):
		"""Build one hashable cache key for the projected mesh stack."""
		reference_transform = np.eye(4, dtype=np.float32) if reference_transform is None else np.asarray(reference_transform, dtype=np.float32)
		return (
			tuple(int(v) for v in geometry.detector_shape_hw),
			np.asarray(geometry.detector_origin_ref, dtype=np.float32).tobytes(),
			np.asarray(geometry.detector_u_ref, dtype=np.float32).tobytes(),
			np.asarray(geometry.detector_v_ref, dtype=np.float32).tobytes(),
			np.asarray(reference_transform, dtype=np.float32).tobytes(),
			None if geometry.source_position_ref is None else np.asarray(geometry.source_position_ref, dtype=np.float32).tobytes(),
			None if geometry.ray_direction_ref is None else np.asarray(geometry.ray_direction_ref, dtype=np.float32).tobytes(),
		)

	def _detector_projection_context(self, geometry, reference_transform):
		"""Return world-space detector data reused by the projected intersection backend."""
		reference_transform = np.eye(4, dtype=np.float32) if reference_transform is None else np.asarray(reference_transform, dtype=np.float32)
		detector_origin_world = _transform_point(reference_transform, geometry.detector_origin_ref).astype(np.float32)
		detector_u_world = _transform_direction(reference_transform, geometry.detector_u_ref).astype(np.float32)
		detector_v_world = _transform_direction(reference_transform, geometry.detector_v_ref).astype(np.float32)
		detector_normal_world = _normalize_vector(np.cross(detector_u_world, detector_v_world)).astype(np.float32)
		u_scale_sq = max(float(np.dot(detector_u_world, detector_u_world)), 1e-12)
		v_scale_sq = max(float(np.dot(detector_v_world, detector_v_world)), 1e-12)
		context = {
			"detector_origin_world": detector_origin_world,
			"detector_u_world": detector_u_world,
			"detector_v_world": detector_v_world,
			"detector_normal_world": detector_normal_world,
			"detector_shape_hw": (int(geometry.detector_shape_hw[0]), int(geometry.detector_shape_hw[1])),
			"u_scale_sq": u_scale_sq,
			"v_scale_sq": v_scale_sq,
			"reference_transform": reference_transform.astype(np.float32, copy=False),
		}
		if geometry.is_cone_beam():
			context["projection_mode"] = "cone"
			context["source_world"] = _transform_point(reference_transform, geometry.source_position_ref).astype(np.float32)
		else:
			context["projection_mode"] = "parallel"
			context["ray_direction_world"] = _normalize_vector(
				_transform_direction(reference_transform, geometry.ray_direction_ref)
			).astype(np.float32)
		return context

	def _project_points_to_detector_pixels(self, points_world, context):
		"""Project world-space points onto detector pixel coordinates."""
		points_world = np.asarray(points_world, dtype=np.float32)
		normal = context["detector_normal_world"]
		detector_origin_world = context["detector_origin_world"]

		if context["projection_mode"] == "cone":
			source_world = context["source_world"]
			line_dirs = points_world - source_world[np.newaxis, :]
			denom = np.sum(line_dirs * normal[np.newaxis, :], axis=1)
			valid = np.abs(denom) > 1e-8
			lambda_plane = np.full(points_world.shape[0], np.nan, dtype=np.float32)
			lambda_plane[valid] = (
				np.dot(detector_origin_world - source_world, normal) / denom[valid]
			).astype(np.float32, copy=False)
			projected_points = source_world[np.newaxis, :] + line_dirs * lambda_plane[:, np.newaxis]
		else:
			back_dir = -context["ray_direction_world"]
			denom = float(np.dot(back_dir, normal))
			valid = np.full(points_world.shape[0], abs(denom) > 1e-8, dtype=bool)
			lambda_plane = np.full(points_world.shape[0], np.nan, dtype=np.float32)
			if abs(denom) > 1e-8:
				lambda_plane[:] = np.sum((detector_origin_world[np.newaxis, :] - points_world) * normal[np.newaxis, :], axis=1) / denom
			projected_points = points_world + back_dir[np.newaxis, :] * lambda_plane[:, np.newaxis]

		delta = projected_points - detector_origin_world[np.newaxis, :]
		cols = np.sum(delta * context["detector_u_world"][np.newaxis, :], axis=1) / context["u_scale_sq"]
		rows = np.sum(delta * context["detector_v_world"][np.newaxis, :], axis=1) / context["v_scale_sq"]
		uv_pixels = np.stack([cols, rows], axis=1).astype(np.float32, copy=False)
		return uv_pixels, projected_points.astype(np.float32, copy=False), valid

	def _triangle_shell_gain(self, triangle_index, hit_points_world, ray_directions):
		"""Return one shell path-length gain per hit point based on local surface normal."""
		hit_points_world = np.asarray(hit_points_world, dtype=np.float32)
		ray_directions = np.asarray(ray_directions, dtype=np.float32)
		if hit_points_world.shape != ray_directions.shape:
			raise ValueError("hit_points_world and ray_directions must have the same shape.")
		if hit_points_world.ndim != 2 or hit_points_world.shape[1] != 3:
			raise ValueError("hit_points_world must have shape (N, 3).")
		if hit_points_world.shape[0] == 0:
			return np.empty((0,), dtype=np.float32)

		if self._triangle_vertex_normals_world.shape[0] == self._triangles_world.shape[0]:
			triangle = self._triangles_world[triangle_index]
			v0 = triangle[0]
			v1 = triangle[1]
			v2 = triangle[2]
			v0v1 = v1 - v0
			v0v2 = v2 - v0
			v0p = hit_points_world - v0[np.newaxis, :]
			d00 = float(np.dot(v0v1, v0v1))
			d01 = float(np.dot(v0v1, v0v2))
			d11 = float(np.dot(v0v2, v0v2))
			d20 = np.sum(v0p * v0v1[np.newaxis, :], axis=1)
			d21 = np.sum(v0p * v0v2[np.newaxis, :], axis=1)
			denom = d00 * d11 - d01 * d01
			if abs(denom) > 1e-12:
				v_weight = (d11 * d20 - d01 * d21) / denom
				w_weight = (d00 * d21 - d01 * d20) / denom
				u_weight = 1.0 - v_weight - w_weight
				weights = np.stack([u_weight, v_weight, w_weight], axis=1).astype(np.float32, copy=False)
				normals = np.sum(
					self._triangle_vertex_normals_world[triangle_index][np.newaxis, :, :] * weights[:, :, np.newaxis],
					axis=1,
				)
				normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-8)
			else:
				normals = np.repeat(self._face_normals_world[triangle_index][np.newaxis, :], hit_points_world.shape[0], axis=0)
		else:
			normals = np.repeat(self._face_normals_world[triangle_index][np.newaxis, :], hit_points_world.shape[0], axis=0)

		cos_incidence = np.abs(np.sum(normals * ray_directions, axis=1))
		cos_floor = 0.08
		return (1.0 / np.maximum(cos_incidence, cos_floor)).astype(np.float32, copy=False)

	def _merge_sorted_shell_hits(self, t_hits, shell_gains, dedup_eps):
		"""Merge nearly identical shell hits and average their angular gains.

		Projected rasterisation can emit duplicate hits on shared triangle edges or
		vertices. For a shell model those duplicates should behave like one surface
		crossing, not like multiple extra material layers, so hits that land within
		`dedup_eps` along the ray are collapsed into one cluster.
		"""
		t_hits = np.asarray(t_hits, dtype=np.float32)
		shell_gains = np.asarray(shell_gains, dtype=np.float32)
		if t_hits.size == 0:
			return t_hits, shell_gains
		if t_hits.shape != shell_gains.shape:
			raise ValueError("t_hits and shell_gains must have identical shapes.")

		merged_t = [float(t_hits[0])]
		merged_gains = [float(shell_gains[0])]
		cluster_count = 1
		for hit_idx in range(1, int(t_hits.size)):
			t_value = float(t_hits[hit_idx])
			if abs(t_value - merged_t[-1]) <= dedup_eps:
				cluster_count += 1
				merged_t[-1] = merged_t[-1] + (t_value - merged_t[-1]) / float(cluster_count)
				merged_gains[-1] = merged_gains[-1] + (float(shell_gains[hit_idx]) - merged_gains[-1]) / float(cluster_count)
				continue
			cluster_count = 1
			merged_t.append(t_value)
			merged_gains.append(float(shell_gains[hit_idx]))

		return (
			np.asarray(merged_t, dtype=np.float32),
			np.asarray(merged_gains, dtype=np.float32),
		)

	def _save_projected_debug_maps(self, detector_shape_hw, hit_ray_indices, projected_raw_counts,
	                               projected_merged_counts, projected_odd_mask, projected_path_lengths,
	                               projected_max_shell_gain, projected_min_abs_cos,
	                               analytic_merged_counts=None, analytic_path_lengths=None):
		"""Save projected-backend diagnostic maps for one mesh when debug export is enabled."""
		debug_export_dir = getattr(self, "debug_export_dir", None)
		if debug_export_dir is None:
			return
		debug_export_dir = str(debug_export_dir).strip()
		if not debug_export_dir:
			return

		os.makedirs(debug_export_dir, exist_ok=True)
		height, width = int(detector_shape_hw[0]), int(detector_shape_hw[1])
		n_pixels = height * width
		hit_ray_indices = np.asarray(hit_ray_indices, dtype=np.int32)

		def _full_map_from_hits(hit_values):
			full_map = np.zeros(n_pixels, dtype=np.float32)
			full_map[hit_ray_indices] = np.asarray(hit_values, dtype=np.float32)
			return full_map.reshape(height, width)

		def _safe_max(image):
			max_value = float(np.max(np.asarray(image, dtype=np.float32)))
			return max(1.0, max_value)

		def _safe_label(label_text):
			return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in str(label_text))

		label_prefix = _safe_label(getattr(self.mesh, "label", "mesh"))
		base_name = f"{label_prefix}_{self.backend}_{self.mode}"

		projected_raw_count_map = _full_map_from_hits(projected_raw_counts)
		projected_merged_count_map = _full_map_from_hits(projected_merged_counts)
		projected_odd_mask_map = _full_map_from_hits(projected_odd_mask)
		projected_path_length_map = _full_map_from_hits(projected_path_lengths)
		projected_max_shell_gain_map = _full_map_from_hits(projected_max_shell_gain)
		projected_min_abs_cos_map = _full_map_from_hits(projected_min_abs_cos)

		save_projection_png(
			projected_raw_count_map,
			os.path.join(debug_export_dir, f"{base_name}_projected_raw_hit_count.png"),
			fixed_range=(0.0, _safe_max(projected_raw_count_map)),
			invert=False,
		)
		save_projection_png(
			projected_merged_count_map,
			os.path.join(debug_export_dir, f"{base_name}_projected_merged_hit_count.png"),
			fixed_range=(0.0, _safe_max(projected_merged_count_map)),
			invert=False,
		)
		save_projection_png(
			projected_odd_mask_map,
			os.path.join(debug_export_dir, f"{base_name}_projected_odd_mask.png"),
			fixed_range=(0.0, 1.0),
			invert=False,
		)
		save_projection_png(
			projected_path_length_map,
			os.path.join(debug_export_dir, f"{base_name}_projected_path_length.png"),
			fixed_range=(0.0, _safe_max(projected_path_length_map)),
			invert=False,
		)
		save_projection_png(
			projected_max_shell_gain_map,
			os.path.join(debug_export_dir, f"{base_name}_projected_max_shell_gain.png"),
			fixed_range=(0.0, _safe_max(projected_max_shell_gain_map)),
			invert=False,
		)
		save_projection_png(
			projected_min_abs_cos_map,
			os.path.join(debug_export_dir, f"{base_name}_projected_min_abs_cos.png"),
			fixed_range=(0.0, 1.0),
			invert=False,
		)

		if analytic_merged_counts is None or analytic_path_lengths is None:
			return

		analytic_merged_count_map = _full_map_from_hits(analytic_merged_counts)
		analytic_path_length_map = _full_map_from_hits(analytic_path_lengths)
		count_mismatch_map = (projected_merged_count_map != analytic_merged_count_map).astype(np.float32)
		path_length_abs_diff_map = np.abs(projected_path_length_map - analytic_path_length_map).astype(np.float32, copy=False)

		save_projection_png(
			analytic_merged_count_map,
			os.path.join(debug_export_dir, f"{base_name}_analytic_merged_hit_count.png"),
			fixed_range=(0.0, _safe_max(analytic_merged_count_map)),
			invert=False,
		)
		save_projection_png(
			count_mismatch_map,
			os.path.join(debug_export_dir, f"{base_name}_hit_count_mismatch.png"),
			fixed_range=(0.0, 1.0),
			invert=False,
		)
		save_projection_png(
			path_length_abs_diff_map,
			os.path.join(debug_export_dir, f"{base_name}_path_length_abs_diff.png"),
			fixed_range=(0.0, _safe_max(path_length_abs_diff_map)),
			invert=False,
		)

	def _triangle_projected_pixel_hits(self, triangle_index, context, precomputed_uv=None):
		"""Return pixel indices, ray parameters and shell gains hit by one projected triangle."""
		height, width = context["detector_shape_hw"]
		triangle_world = self._triangles_world[triangle_index]
		if precomputed_uv is not None:
			triangle_uv = precomputed_uv
		else:
			triangle_uv, _projected_points, valid = self._project_points_to_detector_pixels(triangle_world, context)
			if not np.all(valid):
				return np.empty((0,), dtype=np.int32), np.empty((0,), dtype=np.float32), np.empty((0,), dtype=np.float32)

		uv_min = np.min(triangle_uv, axis=0)
		uv_max = np.max(triangle_uv, axis=0)
		col_min = max(0, int(np.ceil(uv_min[0])))
		col_max = min(width - 1, int(np.floor(uv_max[0])))
		row_min = max(0, int(np.ceil(uv_min[1])))
		row_max = min(height - 1, int(np.floor(uv_max[1])))
		if col_max < col_min or row_max < row_min:
			return np.empty((0,), dtype=np.int32), np.empty((0,), dtype=np.float32), np.empty((0,), dtype=np.float32)

		cols = np.arange(col_min, col_max + 1, dtype=np.float32)
		rows = np.arange(row_min, row_max + 1, dtype=np.float32)
		col_grid, row_grid = np.meshgrid(cols, rows)
		pixel_points_2d = np.stack([col_grid, row_grid], axis=-1)

		a = triangle_uv[0].astype(np.float32, copy=False)
		b = triangle_uv[1].astype(np.float32, copy=False)
		c = triangle_uv[2].astype(np.float32, copy=False)
		area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
		if abs(float(area)) <= 1e-8:
			return np.empty((0,), dtype=np.int32), np.empty((0,), dtype=np.float32), np.empty((0,), dtype=np.float32)

		e0 = (pixel_points_2d[..., 0] - b[0]) * (c[1] - b[1]) - (pixel_points_2d[..., 1] - b[1]) * (c[0] - b[0])
		e1 = (pixel_points_2d[..., 0] - c[0]) * (a[1] - c[1]) - (pixel_points_2d[..., 1] - c[1]) * (a[0] - c[0])
		e2 = (pixel_points_2d[..., 0] - a[0]) * (b[1] - a[1]) - (pixel_points_2d[..., 1] - a[1]) * (b[0] - a[0])
		winding_sign = 1.0 if area < 0.0 else -1.0
		e0 *= winding_sign
		e1 *= winding_sign
		e2 *= winding_sign
		# Top-left rasterisation convention: each projected-edge pixel is owned by
		# exactly one adjacent triangle, eliminating shared-edge duplicate hits.
		if area > 0:
			# CCW in standard 2D – edges traverse B→C, C→A, A→B
			tl_e0 = _is_top_left_edge_2d(b, c)
			tl_e1 = _is_top_left_edge_2d(c, a)
			tl_e2 = _is_top_left_edge_2d(a, b)
		else:
			# CW in standard 2D – edges effectively traverse C→B, A→C, B→A
			tl_e0 = _is_top_left_edge_2d(c, b)
			tl_e1 = _is_top_left_edge_2d(a, c)
			tl_e2 = _is_top_left_edge_2d(b, a)
		eps_e0 = np.float32(0.0) if tl_e0 else np.float32(1e-8)
		eps_e1 = np.float32(0.0) if tl_e1 else np.float32(1e-8)
		eps_e2 = np.float32(0.0) if tl_e2 else np.float32(1e-8)
		inside_mask = (
			(e0 >= eps_e0)
			& (e1 >= eps_e1)
			& (e2 >= eps_e2)
		)
		if not np.any(inside_mask):
			return np.empty((0,), dtype=np.int32), np.empty((0,), dtype=np.float32), np.empty((0,), dtype=np.float32)

		hit_rows = row_grid[inside_mask].astype(np.int32, copy=False)
		hit_cols = col_grid[inside_mask].astype(np.int32, copy=False)
		pixel_indices = (hit_rows * width + hit_cols).astype(np.int32, copy=False)
		pixel_centers_world = (
			context["detector_origin_world"][np.newaxis, :]
			+ context["detector_u_world"][np.newaxis, :] * hit_cols[:, np.newaxis]
			+ context["detector_v_world"][np.newaxis, :] * hit_rows[:, np.newaxis]
		).astype(np.float32, copy=False)

		if context["projection_mode"] == "cone":
			source_world = context["source_world"]
			ray_origins = np.repeat(source_world[np.newaxis, :], pixel_centers_world.shape[0], axis=0)
			ray_directions = pixel_centers_world - source_world[np.newaxis, :]
			ray_directions /= np.maximum(np.linalg.norm(ray_directions, axis=1, keepdims=True), 1e-8)
		else:
			ray_origins = pixel_centers_world
			ray_directions = np.repeat(context["ray_direction_world"][np.newaxis, :], pixel_centers_world.shape[0], axis=0)

		t_values = _rays_single_triangle_hit_distances(
			ray_origins=ray_origins,
			ray_directions=ray_directions,
			triangle_world=triangle_world,
		)
		valid_hits = np.isfinite(t_values)
		if not np.any(valid_hits):
			return np.empty((0,), dtype=np.int32), np.empty((0,), dtype=np.float32), np.empty((0,), dtype=np.float32)
		# shell_gain is only used in shell mode; skip the costly barycentric
		# interpolation entirely when computing a solid mesh projection.
		if self.mode == "shell":
			hit_points_world = ray_origins[valid_hits] + ray_directions[valid_hits] * t_values[valid_hits][:, np.newaxis]
			shell_gain = self._triangle_shell_gain(
				triangle_index=triangle_index,
				hit_points_world=hit_points_world,
				ray_directions=ray_directions[valid_hits],
			)
		else:
			shell_gain = np.empty(int(valid_hits.sum()), dtype=np.float32)
		return (
			pixel_indices[valid_hits],
			t_values[valid_hits].astype(np.float32, copy=False),
			shell_gain.astype(np.float32, copy=False),
		)

	def _vectorized_rasterize(self, vis_idx, tri_uvs_vis, context):
		"""Rasterise all visible triangles in a single vectorised NumPy pass.

		Replaces the per-triangle Python loop with five bulk operations:
		  1. Expand every triangle's integer bbox into candidate (col, row) pixels.
		  2. Run the 2-D inside test (edge functions + top-left rule) for all candidates.
		  3. Build world rays for every inside candidate.
		  4. One-ray-per-triangle Möller-Trumbore for all inside candidates at once.
		  5. Assemble flat output arrays.

		Returns:
			(pixel_indices, t_values, shell_gains, tri_indices) — four (M,) flat arrays.
		"""
		height, width = context["detector_shape_hw"]
		N_vis = len(vis_idx)
		_e32  = np.empty(0, dtype=np.float32)
		_e32i = np.empty(0, dtype=np.int32)
		if N_vis == 0:
			return _e32i.copy(), _e32.copy(), _e32.copy(), _e32i.copy()

		# ── 1. Integer bbox for every visible triangle ────────────────────────
		bbox_min  = tri_uvs_vis.min(axis=1)   # (N_vis, 2)
		bbox_max  = tri_uvs_vis.max(axis=1)   # (N_vis, 2)
		col_lo = np.clip(np.ceil(bbox_min[:, 0]).astype(np.int32), 0, width  - 1)
		col_hi = np.clip(np.floor(bbox_max[:, 0]).astype(np.int32), 0, width  - 1)
		row_lo = np.clip(np.ceil(bbox_min[:, 1]).astype(np.int32), 0, height - 1)
		row_hi = np.clip(np.floor(bbox_max[:, 1]).astype(np.int32), 0, height - 1)
		n_cols    = (col_hi - col_lo + 1).astype(np.int32)   # (N_vis,)
		n_rows    = (row_hi - row_lo + 1).astype(np.int32)   # (N_vis,)
		bbox_area = n_cols * n_rows                           # (N_vis,) candidates per triangle

		# ── 2. Expand every bbox into candidate (col, row, tri) triples ───────
		total_cands = int(bbox_area.sum())
		if total_cands == 0:
			return _e32i.copy(), _e32.copy(), _e32.copy(), _e32i.copy()
		cand_tri = np.repeat(np.arange(N_vis, dtype=np.int32), bbox_area)   # (C,)
		cum = np.empty(N_vis + 1, dtype=np.int64)
		cum[0] = 0
		np.cumsum(bbox_area, out=cum[1:])
		offset   = np.arange(total_cands, dtype=np.int64) - cum[cand_tri]
		ncols_c  = n_cols[cand_tri].astype(np.int64)
		cand_col = (col_lo[cand_tri] + offset % ncols_c).astype(np.int32)    # (C,)
		cand_row = (row_lo[cand_tri] + offset // ncols_c).astype(np.int32)   # (C,)

		# ── 3. Vectorised 2-D inside test (matches _triangle_projected_pixel_hits) ──
		uvA = tri_uvs_vis[cand_tri, 0, :]   # (C, 2)
		uvB = tri_uvs_vis[cand_tri, 1, :]   # (C, 2)
		uvC = tri_uvs_vis[cand_tri, 2, :]   # (C, 2)
		px  = cand_col.astype(np.float32)   # (C,)
		py  = cand_row.astype(np.float32)   # (C,)

		# Signed 2-D area per triangle (broadcast to candidates via cand_tri index).
		v_area = (
			(tri_uvs_vis[:, 1, 0] - tri_uvs_vis[:, 0, 0]) * (tri_uvs_vis[:, 2, 1] - tri_uvs_vis[:, 0, 1])
			- (tri_uvs_vis[:, 1, 1] - tri_uvs_vis[:, 0, 1]) * (tri_uvs_vis[:, 2, 0] - tri_uvs_vis[:, 0, 0])
		)  # (N_vis,)
		area_c = v_area[cand_tri]            # (C,)

		# Edge functions — identical formulas to _triangle_projected_pixel_hits.
		e0 = (px - uvB[:, 0]) * (uvC[:, 1] - uvB[:, 1]) - (py - uvB[:, 1]) * (uvC[:, 0] - uvB[:, 0])
		e1 = (px - uvC[:, 0]) * (uvA[:, 1] - uvC[:, 1]) - (py - uvC[:, 1]) * (uvA[:, 0] - uvC[:, 0])
		e2 = (px - uvA[:, 0]) * (uvB[:, 1] - uvA[:, 1]) - (py - uvA[:, 1]) * (uvB[:, 0] - uvA[:, 0])
		winding = np.where(area_c < 0, np.float32(1.0), np.float32(-1.0))
		e0 = (e0 * winding).astype(np.float32)
		e1 = (e1 * winding).astype(np.float32)
		e2 = (e2 * winding).astype(np.float32)

		# Vectorised top-left rule — mirrors _is_top_left_edge_2d exactly.
		def _tl(p, q):
			dy = q[:, 1] - p[:, 1]
			return (dy > 0.0) | ((np.abs(dy) <= 1e-8) & (q[:, 0] - p[:, 0] < 0.0))

		uvA_l = tri_uvs_vis[:, 0, :]
		uvB_l = tri_uvs_vis[:, 1, :]
		uvC_l = tri_uvs_vis[:, 2, :]
		ccw_l = v_area > 0                                          # (N_vis,) True = CCW
		tl0 = np.where(ccw_l, _tl(uvB_l, uvC_l), _tl(uvC_l, uvB_l))  # (N_vis,)
		tl1 = np.where(ccw_l, _tl(uvC_l, uvA_l), _tl(uvA_l, uvC_l))
		tl2 = np.where(ccw_l, _tl(uvA_l, uvB_l), _tl(uvB_l, uvA_l))
		_eps = np.float32(1e-8)
		inside = (
			(e0 >= np.where(tl0[cand_tri], np.float32(0.0), _eps))
			& (e1 >= np.where(tl1[cand_tri], np.float32(0.0), _eps))
			& (e2 >= np.where(tl2[cand_tri], np.float32(0.0), _eps))
			& (np.abs(area_c) > 1e-8)
		)
		if not np.any(inside):
			return _e32i.copy(), _e32.copy(), _e32.copy(), _e32i.copy()

		# ── 4. Build world rays for inside candidates ─────────────────────────
		in_col     = cand_col[inside]                       # (M,)
		in_row     = cand_row[inside]                       # (M,)
		in_tri_loc = cand_tri[inside]                       # (M,) local index into vis_idx
		in_tri_gbl = vis_idx[in_tri_loc]                    # (M,) global triangle index
		pixel_centers_world = (
			context["detector_origin_world"]
			+ context["detector_u_world"] * in_col[:, np.newaxis].astype(np.float32)
			+ context["detector_v_world"] * in_row[:, np.newaxis].astype(np.float32)
		).astype(np.float32)
		M = in_col.shape[0]
		if context["projection_mode"] == "cone":
			src      = context["source_world"].astype(np.float32)
			ray_orig = np.broadcast_to(src, (M, 3)).copy()
			ray_dir  = pixel_centers_world - src
			ray_dir /= np.maximum(np.linalg.norm(ray_dir, axis=1, keepdims=True), np.float32(1e-8))
		else:
			ray_orig = pixel_centers_world.copy()
			rdir     = context["ray_direction_world"].astype(np.float32)
			ray_dir  = np.broadcast_to(rdir, (M, 3)).copy()

		# ── 5. Vectorised one-ray-per-triangle Möller-Trumbore ────────────────
		tris_w = self._triangles_world[in_tri_gbl]          # (M, 3, 3)
		t_vals = _one_ray_per_triangle_hit(ray_orig, ray_dir, tris_w)
		valid  = np.isfinite(t_vals)
		if not np.any(valid):
			return _e32i.copy(), _e32.copy(), _e32.copy(), _e32i.copy()

		# ── 6. Assemble output ────────────────────────────────────────────────
		out_pixel = (in_row[valid] * width + in_col[valid]).astype(np.int32)
		out_t     = t_vals[valid].astype(np.float32)
		out_tri   = in_tri_gbl[valid].astype(np.int32)
		n_hits    = int(valid.sum())
		if self.mode == "shell":
			out_shell = np.empty(n_hits, dtype=np.float32)
			# Group valid hits by triangle and call _triangle_shell_gain for each.
			ray_orig_hits = ray_orig[valid]   # (n_hits, 3)
			ray_dir_hits  = ray_dir[valid]    # (n_hits, 3)
			unique_tris, inv = np.unique(out_tri, return_inverse=True)
			for k, tri_idx in enumerate(unique_tris):
				sel = inv == k
				hp  = ray_orig_hits[sel] + ray_dir_hits[sel] * out_t[sel][:, np.newaxis]
				out_shell[sel] = self._triangle_shell_gain(
					triangle_index=int(tri_idx),
					hit_points_world=hp,
					ray_directions=ray_dir_hits[sel],
				)
		else:
			out_shell = np.empty(n_hits, dtype=np.float32)
		return out_pixel, out_t, out_shell, out_tri

	def build_projected_intersection_stack(self, geometry, reference_transform=None, progress_callback=None,
	                                       progress_fraction=(0.0, 1.0), use_cache=True):
		"""Build one compact per-pixel stack of projected mesh-triangle intersections."""
		cache_key = self._projected_stack_cache_key(geometry, reference_transform)
		if use_cache and cache_key in self._projected_stack_cache:
			_log.info("build_projected_intersection_stack: returning cached stack")
			return self._projected_stack_cache[cache_key]

		context = self._detector_projection_context(geometry, reference_transform)
		height, width = context["detector_shape_hw"]
		triangle_count = int(self._triangles_world.shape[0])
		progress_start = float(progress_fraction[0])
		progress_end = float(progress_fraction[1])
		progress_span = max(0.0, progress_end - progress_start)

		# Signal immediately so the progress bar appears before any heavy work.
		if progress_callback is not None:
			progress_callback(progress_start)

		# Vectorised UV pre-projection: project all N×3 vertices in a single NumPy
		# call instead of N separate function calls (each handling only 3 points).
		# Also pre-filters triangles that project entirely outside the detector so
		# the parallel loop can skip them without any per-pixel work.
		_t_proj = perf_counter()
		all_uvs_flat, _, all_valid_flat = self._project_points_to_detector_pixels(
			self._triangles_world.reshape(-1, 3), context
		)
		tri_uvs = all_uvs_flat.reshape(triangle_count, 3, 2).astype(np.float32, copy=False)
		tri_all_valid = all_valid_flat.reshape(triangle_count, 3).all(axis=1)
		bbox_min_uv = tri_uvs.min(axis=1)  # (N, 2)
		bbox_max_uv = tri_uvs.max(axis=1)  # (N, 2)
		tri_visible = (
			tri_all_valid
			& (bbox_max_uv[:, 0] >= -0.5) & (bbox_min_uv[:, 0] <= float(width)  - 0.5)
			& (bbox_max_uv[:, 1] >= -0.5) & (bbox_min_uv[:, 1] <= float(height) - 0.5)
		)
		# Pixel-centre filter: pixel at column c has its centre at u=c (integer).
		# A bbox [min_u, max_u] contains at least one integer centre iff
		#   floor(max_u) >= ceil(min_u)  (same in v).
		# Triangles that fail this test produce zero hits even after the full
		# edge-function test — skip them completely.
		tri_visible &= (
			(np.floor(bbox_max_uv[:, 0]) >= np.ceil(bbox_min_uv[:, 0]))
			& (np.floor(bbox_max_uv[:, 1]) >= np.ceil(bbox_min_uv[:, 1]))
		)
		n_visible = int(tri_visible.sum())
		_log.info(
			"build_projected_intersection_stack: UV pre-projection done in %.3f s: "
			"%d/%d triangles with pixel centres in projected bbox (%d skipped as sub-pixel)",
			perf_counter() - _t_proj, n_visible, triangle_count, triangle_count - n_visible,
		)

		_log.info(
			"build_projected_intersection_stack: rasterising %d/%d visible triangles "
			"onto %dx%d detector …",
			n_visible, triangle_count, width, height,
		)
		_t_raster = perf_counter()
		vis_idx = np.where(tri_visible)[0]
		all_pixel_indices, all_t_values, all_shell_gains, all_tri_indices = \
			self._vectorized_rasterize(vis_idx, tri_uvs[vis_idx], context)
		if progress_callback is not None:
			progress_callback(progress_start + 0.5 * progress_span)
		_log.info(
			"build_projected_intersection_stack: rasterisation done in %.3f s (%d hits)",
			perf_counter() - _t_raster, len(all_t_values),
		)

		# Build CSR offsets with np.argsort + np.bincount.
		_t_csr = perf_counter()
		if len(all_pixel_indices) > 0:
			sort_order            = np.argsort(all_pixel_indices, kind="stable")
			sample_pixel_sorted   = all_pixel_indices[sort_order]
			sample_t              = all_t_values[sort_order]
			sample_triangle_index = all_tri_indices[sort_order]
			sample_shell_gain     = all_shell_gains[sort_order]
			pixel_hit_counts      = np.bincount(sample_pixel_sorted, minlength=height * width).astype(np.int32)
		else:
			sample_t              = np.empty(0, dtype=np.float32)
			sample_triangle_index = np.empty(0, dtype=np.int32)
			sample_shell_gain     = np.empty(0, dtype=np.float32)
			pixel_hit_counts      = np.zeros(height * width, dtype=np.int32)

		pixel_offsets = np.zeros(pixel_hit_counts.shape[0] + 1, dtype=np.int64)
		pixel_offsets[1:] = np.cumsum(pixel_hit_counts, dtype=np.int64)

		total_hits = int(pixel_offsets[-1])
		_t_stack_end = perf_counter()
		_log.info(
			"build_projected_intersection_stack: CSR stack built in %.3f s (%d total hits)",
			_t_stack_end - _t_csr, total_hits,
		)
		self._last_stack_timing = {
			"uv_projection_s": float(_t_raster - _t_proj),
			"rasterize_s": float(_t_csr - _t_raster),
			"csr_s": float(_t_stack_end - _t_csr),
			"total_s": float(_t_stack_end - _t_proj),
		}

		stack = ProjectedTrianglePixelStack(
			detector_shape_hw=(height, width),
			pixel_offsets=pixel_offsets.astype(np.int32, copy=False),
			sample_t=sample_t,
			sample_triangle_index=sample_triangle_index,
			sample_shell_gain=sample_shell_gain,
		)
		if use_cache:
			self._projected_stack_cache[cache_key] = stack
		if progress_callback is not None:
			progress_callback(progress_end)
		return stack

	def uses_direct_integral(self):
		"""Mesh sources always compute integrals analytically per ray."""
		return True

	def ray_integral_world(self, ray_origins, ray_directions, t_starts, t_ends, physics_model, step_mm,
	                      progress_callback=None, progress_fraction=(0.0, 1.0),
	                      geometry=None, reference_transform=None, hit_ray_indices=None, detector_shape_hw=None):
		"""Return one simplified per-ray integral by intersecting rays with mesh triangles."""
		ray_origins = np.asarray(ray_origins, dtype=np.float32)
		ray_directions = np.asarray(ray_directions, dtype=np.float32)
		t_starts = np.asarray(t_starts, dtype=np.float32)
		t_ends = np.asarray(t_ends, dtype=np.float32)
		n_rays = ray_origins.shape[0]
		integrals = np.zeros(n_rays, dtype=np.float32)
		if n_rays == 0 or self._triangles_world.shape[0] == 0:
			return integrals, 0

		# Reuse the current physics model by mapping one synthetic scalar value into
		# a constant attenuation coefficient for the whole mesh material.
		mu_value = float(np.asarray(
			physics_model.scalar_to_mu(np.array([self.scalar_value * self.scalar_scale + self.scalar_bias], dtype=np.float32)),
			dtype=np.float32,
		)[0]) * self.attenuation_multiplier
		if mu_value <= 0.0:
			return integrals, 0

		if self.backend == "projected_intersection_list":
			if geometry is None or hit_ray_indices is None or detector_shape_hw is None:
				raise ValueError("Projected mesh backend requires geometry, detector_shape_hw and hit_ray_indices.")
			hit_ray_indices = np.asarray(hit_ray_indices, dtype=np.int32)
			stack = self.build_projected_intersection_stack(
				geometry=geometry,
				reference_transform=reference_transform,
				progress_callback=progress_callback,
				progress_fraction=progress_fraction,
			)
			dedup_eps = max(1e-4, 0.25 * float(step_mm))
			intersection_work_count = 0
			debug_export_enabled = self.debug_export_dir is not None and str(self.debug_export_dir).strip() != ""
			projected_raw_counts = np.zeros(n_rays, dtype=np.float32) if debug_export_enabled else None
			projected_merged_counts = np.zeros(n_rays, dtype=np.float32) if debug_export_enabled else None
			projected_odd_mask = np.zeros(n_rays, dtype=np.float32) if debug_export_enabled else None
			projected_path_lengths = np.zeros(n_rays, dtype=np.float32) if debug_export_enabled else None
			projected_max_shell_gain = np.zeros(n_rays, dtype=np.float32) if debug_export_enabled else None
			projected_min_abs_cos = np.ones(n_rays, dtype=np.float32) if debug_export_enabled else None
			analytic_merged_counts = np.zeros(n_rays, dtype=np.float32) if debug_export_enabled and self.debug_compare_analytic else None
			analytic_path_lengths = np.zeros(n_rays, dtype=np.float32) if debug_export_enabled and self.debug_compare_analytic else None
			# Pre-compute all CSR start/end offsets at once to skip empty pixels without
			# iterating over them in Python — avoids overhead for typically ~50-70 % of rays.
			_idx64 = hit_ray_indices.astype(np.int64)
			batch_starts = stack.pixel_offsets[_idx64]
			batch_ends   = stack.pixel_offsets[_idx64 + 1]
			active_local_indices = np.where(batch_ends > batch_starts)[0]
			n_active = len(active_local_indices)
			_log.info(
				"ray_integral_world: projected integration starting — %d/%d rays have CSR hits …",
				n_active, len(hit_ray_indices),
			)
			_t_integ = perf_counter()
			progress_span_integ = 0.5 * (float(progress_fraction[1]) - float(progress_fraction[0]))
			progress_base_integ = float(progress_fraction[0]) + progress_span_integ
			progress_stride = max(1, n_active // 50)
			for k, local_ray_idx in enumerate(active_local_indices.tolist()):
				if progress_callback is not None and k % progress_stride == 0:
					progress_callback(progress_base_integ + progress_span_integ * (k / max(n_active, 1)))
				pixel_index = int(hit_ray_indices[local_ray_idx])
				start_idx   = int(batch_starts[local_ray_idx])
				end_idx     = int(batch_ends[local_ray_idx])
				raw_t_hits = np.asarray(stack.sample_t[start_idx:end_idx], dtype=np.float32)
				raw_shell_gains = np.asarray(stack.sample_shell_gain[start_idx:end_idx], dtype=np.float32)
				raw_tri_indices = np.asarray(stack.sample_triangle_index[start_idx:end_idx], dtype=np.int32)
				sort_order = np.argsort(raw_t_hits, kind="mergesort")
				t_hits = raw_t_hits[sort_order]
				shell_gains = raw_shell_gains[sort_order]
				tri_indices = raw_tri_indices[sort_order]
				range_mask = (
					(t_hits >= t_starts[local_ray_idx] - dedup_eps)
					& (t_hits <= t_ends[local_ray_idx] + dedup_eps)
				)
				t_hits = t_hits[range_mask]
				shell_gains = shell_gains[range_mask]
				tri_indices = tri_indices[range_mask]
				# Compute actual face-normal cosines for accurate grazing filtering and
				# winding determination (avoids the cos_floor bias in stored shell_gain).
				ray_dir_local = ray_directions[local_ray_idx]
				if tri_indices.size > 0:
					face_normals_hits = self._face_normals_world[tri_indices]
					face_dots = np.einsum("ij,j->i", face_normals_hits, ray_dir_local).astype(np.float32, copy=False)
					abs_cos_hits = np.abs(face_dots)
				else:
					face_dots = np.empty((0,), dtype=np.float32)
					abs_cos_hits = np.empty((0,), dtype=np.float32)
				if self.projected_min_abs_cos > 0.0 and t_hits.size > 0:
					grazing_mask = abs_cos_hits >= self.projected_min_abs_cos
					t_hits = t_hits[grazing_mask]
					shell_gains = shell_gains[grazing_mask]
					tri_indices = tri_indices[grazing_mask]
					face_dots = face_dots[grazing_mask]
					abs_cos_hits = abs_cos_hits[grazing_mask]
				if debug_export_enabled:
					projected_raw_counts[local_ray_idx] = float(t_hits.size)
					if t_hits.size > 0:
						projected_max_shell_gain[local_ray_idx] = float(np.max(shell_gains))
						projected_min_abs_cos[local_ray_idx] = float(np.min(abs_cos_hits))
				if t_hits.size == 0:
					if analytic_merged_counts is not None:
						self._ensure_bvh()
						analytic_hits = _ray_triangle_intersections_bvh(
							ray_origin=ray_origins[local_ray_idx],
							ray_direction=ray_directions[local_ray_idx],
							triangles_world=self._triangles_world,
							bvh_nodes=self._bvh_nodes,
						)
						analytic_hits = analytic_hits[
							(analytic_hits >= t_starts[local_ray_idx] - dedup_eps)
							& (analytic_hits <= t_ends[local_ray_idx] + dedup_eps)
						]
						if analytic_hits.size > 0:
							analytic_merged_hits = [float(analytic_hits[0])]
							for t_value in analytic_hits[1:]:
								if abs(float(t_value) - analytic_merged_hits[-1]) > dedup_eps:
									analytic_merged_hits.append(float(t_value))
							analytic_hits = np.asarray(analytic_merged_hits, dtype=np.float32)
						analytic_merged_counts[local_ray_idx] = float(analytic_hits.size)
					continue
				if self.mode == "shell":
					t_hits, shell_gains = self._merge_sorted_shell_hits(
						t_hits=t_hits,
						shell_gains=shell_gains,
						dedup_eps=dedup_eps,
					)
					path_length = float(np.sum(shell_gains, dtype=np.float32) * self.shell_thickness_mm)
					integrals[local_ray_idx] = path_length * mu_value
					intersection_work_count += int(t_hits.size)
					if debug_export_enabled:
						projected_merged_counts[local_ray_idx] = float(t_hits.size)
						projected_odd_mask[local_ray_idx] = float(int(t_hits.size) % 2)
						projected_path_lengths[local_ray_idx] = path_length
					if analytic_merged_counts is not None:
						self._ensure_bvh()
						analytic_hits = _ray_triangle_intersections_bvh(
							ray_origin=ray_origins[local_ray_idx],
							ray_direction=ray_directions[local_ray_idx],
							triangles_world=self._triangles_world,
							bvh_nodes=self._bvh_nodes,
						)
						analytic_hits = analytic_hits[
							(analytic_hits >= t_starts[local_ray_idx] - dedup_eps)
							& (analytic_hits <= t_ends[local_ray_idx] + dedup_eps)
						]
						if analytic_hits.size > 0:
							analytic_merged_hits = [float(analytic_hits[0])]
							for t_value in analytic_hits[1:]:
								if abs(float(t_value) - analytic_merged_hits[-1]) > dedup_eps:
									analytic_merged_hits.append(float(t_value))
							analytic_hits = np.asarray(analytic_merged_hits, dtype=np.float32)
						analytic_merged_counts[local_ray_idx] = float(analytic_hits.size)
						analytic_path_lengths[local_ray_idx] = float(analytic_hits.size) * self.shell_thickness_mm
					continue
				# Signed crossing: cluster hits within dedup_eps and aggregate face-normal
				# winding votes per cluster, then use a depth counter for path length.
				# Fully vectorised with NumPy cumsum — no Python loops over hits.
				n_solid_hits = t_hits.size
				if n_solid_hits > 0:
					# Assign a monotone cluster id to every hit.
					new_cluster = np.empty(n_solid_hits, dtype=bool)
					new_cluster[0] = True
					if n_solid_hits > 1:
						new_cluster[1:] = (t_hits[1:] - t_hits[:-1]) > dedup_eps
					cluster_ids = np.cumsum(new_cluster, dtype=np.int32) - 1
					n_clusters  = int(cluster_ids[-1]) + 1
					# Net winding sign and mean t per cluster via np.bincount.
					cluster_count = np.bincount(cluster_ids, minlength=n_clusters).astype(np.int32)
					cluster_net   = np.bincount(cluster_ids, weights=np.sign(face_dots),
					                            minlength=n_clusters).astype(np.float32)
					cluster_t_sum = np.bincount(cluster_ids, weights=t_hits.astype(np.float64),
					                            minlength=n_clusters)
					cluster_t_mean = (cluster_t_sum / np.maximum(cluster_count, 1).astype(np.float64)).astype(np.float32)
					# Discard clusters whose net sign is zero (shared-edge cancellation).
					nonzero_mask     = np.abs(cluster_net) > 1e-8
					cluster_t_arr    = cluster_t_mean[nonzero_mask]
					cluster_sign_arr = np.sign(cluster_net[nonzero_mask]).astype(np.int8)
					n_valid = int(nonzero_mask.sum())
				else:
					n_valid = 0
					cluster_t_arr    = np.empty(0, dtype=np.float32)
					cluster_sign_arr = np.empty(0, dtype=np.int8)
				intersection_work_count += n_valid
				if debug_export_enabled:
					projected_merged_counts[local_ray_idx] = float(n_valid)
					projected_odd_mask[local_ray_idx] = float(n_valid % 2)
				if n_valid > 0:
					# Vectorised depth counter.
					# sign < 0 (front face, entering) → depth +1
					# sign > 0 (back face,  exiting)  → depth -1
					depth_delta  = np.where(cluster_sign_arr < 0, np.int32(1), np.int32(-1))
					depth_before = np.r_[np.int32(0),
					                     np.cumsum(depth_delta, dtype=np.int32)[:-1]]
					# 0→1 transitions are outer-surface entries; 1→0 are outer exits.
					enters   = (depth_before == 0) & (depth_delta > 0)
					exits    = (depth_before == 1) & (depth_delta < 0)
					enter_ts = cluster_t_arr[enters]
					exit_ts  = cluster_t_arr[exits]
					n_pairs  = min(enter_ts.size, exit_ts.size)
					path_length = float(np.sum(
						np.maximum(exit_ts[:n_pairs] - enter_ts[:n_pairs], np.float32(0.0))
					))
					integrals[local_ray_idx] = path_length * mu_value
					if debug_export_enabled:
						projected_path_lengths[local_ray_idx] = path_length
				if analytic_merged_counts is not None:
					self._ensure_bvh()
					analytic_hits = _ray_triangle_intersections_bvh(
						ray_origin=ray_origins[local_ray_idx],
						ray_direction=ray_directions[local_ray_idx],
						triangles_world=self._triangles_world,
						bvh_nodes=self._bvh_nodes,
					)
					analytic_hits = analytic_hits[
						(analytic_hits >= t_starts[local_ray_idx] - dedup_eps)
						& (analytic_hits <= t_ends[local_ray_idx] + dedup_eps)
					]
					if analytic_hits.size > 0:
						analytic_merged_hits = [float(analytic_hits[0])]
						for t_value in analytic_hits[1:]:
							if abs(float(t_value) - analytic_merged_hits[-1]) > dedup_eps:
								analytic_merged_hits.append(float(t_value))
						analytic_hits = np.asarray(analytic_merged_hits, dtype=np.float32)
					analytic_merged_counts[local_ray_idx] = float(analytic_hits.size)
					if self.mode == "shell":
						analytic_path_lengths[local_ray_idx] = float(analytic_hits.size) * self.shell_thickness_mm
					elif analytic_hits.size >= 2:
						if analytic_hits.size % 2 == 1:
							analytic_hits = analytic_hits[:-1]
						analytic_inside_lengths = analytic_hits[1::2] - analytic_hits[::2]
						analytic_path_lengths[local_ray_idx] = float(np.sum(np.maximum(analytic_inside_lengths, 0.0), dtype=np.float32))
			_t_integ_end = perf_counter()
			_log.info(
				"ray_integral_world: projected integration done in %.3f s (%d work intersections)",
				_t_integ_end - _t_integ, intersection_work_count,
			)
			self._last_integral_timing = {"integration_s": float(_t_integ_end - _t_integ)}
			if debug_export_enabled:
				self._save_projected_debug_maps(
					detector_shape_hw=detector_shape_hw,
					hit_ray_indices=hit_ray_indices,
					projected_raw_counts=projected_raw_counts,
					projected_merged_counts=projected_merged_counts,
					projected_odd_mask=projected_odd_mask,
					projected_path_lengths=projected_path_lengths,
					projected_max_shell_gain=projected_max_shell_gain,
					projected_min_abs_cos=projected_min_abs_cos,
					analytic_merged_counts=analytic_merged_counts,
					analytic_path_lengths=analytic_path_lengths,
				)
			return integrals, intersection_work_count

		intersection_work_count = 0
		dedup_eps = max(1e-4, 0.25 * float(step_mm))
		progress_start = float(progress_fraction[0])
		progress_end = float(progress_fraction[1])
		progress_span = max(0.0, progress_end - progress_start)
		progress_stride = max(1, n_rays // 200)
		_t_analytic_start = perf_counter()
		self._ensure_bvh()
		for ray_idx in range(n_rays):
			if progress_callback is not None and (ray_idx % progress_stride == 0):
				progress_callback(progress_start + progress_span * (float(ray_idx) / float(max(n_rays, 1))))
			t_hits = _ray_triangle_intersections_bvh(
				ray_origin=ray_origins[ray_idx],
				ray_direction=ray_directions[ray_idx],
				triangles_world=self._triangles_world,
				bvh_nodes=self._bvh_nodes,
			)
			if t_hits.size == 0:
				continue

			t_hits = t_hits[(t_hits >= t_starts[ray_idx] - dedup_eps) & (t_hits <= t_ends[ray_idx] + dedup_eps)]
			if t_hits.size == 0:
				continue

			# Merge nearly identical hits caused by neighbouring triangles sharing one
			# edge or by grazing the mesh exactly at a vertex.
			merged_hits = [float(t_hits[0])]
			for t_value in t_hits[1:]:
				if abs(float(t_value) - merged_hits[-1]) > dedup_eps:
					merged_hits.append(float(t_value))
			t_hits = np.asarray(merged_hits, dtype=np.float32)
			intersection_work_count += int(t_hits.size)

			if self.mode == "shell":
				integrals[ray_idx] = float(t_hits.size) * self.shell_thickness_mm * mu_value
				continue

			if t_hits.size >= 2:
				if t_hits.size % 2 == 1:
					t_hits = t_hits[:-1]
				inside_lengths = t_hits[1::2] - t_hits[::2]
				integrals[ray_idx] = np.sum(np.maximum(inside_lengths, 0.0), dtype=np.float32) * mu_value

		if progress_callback is not None:
			progress_callback(progress_end)
		self._last_integral_timing = {"integration_s": float(perf_counter() - _t_analytic_start)}
		return integrals, intersection_work_count


class XRayProjector:
	"""Project one or more world-space attenuation sources onto a detector plane."""

	def __init__(self, sample_sources: Iterable[XRaySampleSource]):
		"""Store the list of sample sources used during projection."""
		self.sample_sources = list(sample_sources)
		if not self.sample_sources:
			raise ValueError("sample_sources must contain at least one X-ray source.")

	def scene_bounds_world(self):
		"""Return the world-space AABB covering every source registered in the projector."""
		mins = []
		maxs = []
		for source in self.sample_sources:
			source_min, source_max = source.bounds_world()
			mins.append(np.asarray(source_min, dtype=np.float32))
			maxs.append(np.asarray(source_max, dtype=np.float32))
		return np.min(np.stack(mins, axis=0), axis=0), np.max(np.stack(maxs, axis=0), axis=0)

	def _detector_pixel_world(self, geometry, reference_transform, row_idx, col_idx):
		"""Return one detector pixel center in world coordinates."""
		detector_origin_world = _transform_point(reference_transform, geometry.detector_origin_ref)
		detector_u_world = _transform_direction(reference_transform, geometry.detector_u_ref)
		detector_v_world = _transform_direction(reference_transform, geometry.detector_v_ref)
		return (
			detector_origin_world
			+ detector_u_world * float(col_idx)
			+ detector_v_world * float(row_idx)
		)

	def _ray_definition_world(self, geometry, reference_transform, detector_point_world):
		"""Return one ray origin and direction in world coordinates."""
		if geometry.source_position_ref is not None:
			ray_origin_world = _transform_point(reference_transform, geometry.source_position_ref)
			ray_direction_world = _normalize_vector(detector_point_world - ray_origin_world)
			return ray_origin_world, ray_direction_world

		ray_origin_world = detector_point_world
		ray_direction_world = _normalize_vector(_transform_direction(reference_transform, geometry.ray_direction_ref))
		return ray_origin_world, ray_direction_world

	def project(self, geometry, physics_model, reference_transform=None, return_stats=False, progress_callback=None):
		"""Project all sample sources through the provided X-ray geometry (vectorized slab marching)."""
		geometry.validate()
		reference_transform = np.eye(4, dtype=np.float32) if reference_transform is None else np.asarray(reference_transform, dtype=np.float32)
		if reference_transform.shape != (4, 4):
			raise ValueError("reference_transform must be a 4x4 homogeneous matrix.")

		scene_min_world, scene_max_world = self.scene_bounds_world()
		height, width = int(geometry.detector_shape_hw[0]), int(geometry.detector_shape_hw[1])
		n_pixels = height * width
		step_mm = float(geometry.step_mm)
		start_time = perf_counter()
		_phase_timings: dict = {}
		_per_source_stats: list = []

		# Build all detector pixel centers (H*W, 3)
		detector_origin_world = _transform_point(reference_transform, geometry.detector_origin_ref).astype(np.float32)
		detector_u_world = _transform_direction(reference_transform, geometry.detector_u_ref).astype(np.float32)
		detector_v_world = _transform_direction(reference_transform, geometry.detector_v_ref).astype(np.float32)
		col_grid, row_grid = np.meshgrid(
			np.arange(width, dtype=np.float32),
			np.arange(height, dtype=np.float32),
		)
		pixel_centers = (
			detector_origin_world
			+ detector_u_world * col_grid[:, :, np.newaxis]
			+ detector_v_world * row_grid[:, :, np.newaxis]
		).reshape(n_pixels, 3)

		# Build per-ray origins and normalized directions (H*W, 3)
		if geometry.source_position_ref is not None:
			source_world = _transform_point(reference_transform, geometry.source_position_ref).astype(np.float32)
			ray_origins = np.empty((n_pixels, 3), dtype=np.float32)
			ray_origins[:] = source_world
			raw_dirs = pixel_centers - source_world
			source_to_detector_distance_mm = np.linalg.norm(raw_dirs, axis=1).astype(np.float32)
			norms = np.linalg.norm(raw_dirs, axis=1, keepdims=True)
			ray_directions = raw_dirs / np.maximum(norms, 1e-8)
		else:
			ray_dir_world = _normalize_vector(
				_transform_direction(reference_transform, geometry.ray_direction_ref)
			).astype(np.float32)
			ray_origins = pixel_centers
			ray_directions = np.empty((n_pixels, 3), dtype=np.float32)
			ray_directions[:] = ray_dir_world
			source_to_detector_distance_mm = None

		_phase_timings["ray_setup"] = float(perf_counter() - start_time)

		# Vectorized AABB intersection for all rays
		_t_aabb_start = perf_counter()
		t_starts, t_ends, hit_mask = _ray_box_intersections_vectorized(
			ray_origins, ray_directions, scene_min_world, scene_max_world,
		)
		t_starts = np.maximum(t_starts, 0.0)
		hit_mask &= t_ends > t_starts
		_phase_timings["aabb_intersection"] = float(perf_counter() - _t_aabb_start)

		_t_depth_start = perf_counter()
		depth_mode = geometry.normalized_depth_window_mode()
		depth_limits = geometry.depth_window_limits_mm()
		if depth_mode == "ray" and depth_limits is not None:
			depth_start, depth_end = depth_limits
			t_starts = np.maximum(t_starts, depth_start)
			t_ends = np.minimum(t_ends, depth_end)
			hit_mask &= t_ends > t_starts
		elif depth_mode == "planar" and depth_limits is not None:
			depth_origin_world = _transform_point(
				reference_transform,
				geometry.effective_depth_window_origin_ref(),
			).astype(np.float32)
			depth_axis_world = _normalize_vector(_transform_direction(
				reference_transform,
				geometry.effective_depth_window_axis_ref(),
			)).astype(np.float32)
			depth_start, depth_end = depth_limits
			slab_t_starts, slab_t_ends, slab_hit_mask = _ray_planar_slab_intersections_vectorized(
				ray_origins,
				ray_directions,
				depth_origin_world,
				depth_axis_world,
				depth_start,
				depth_end,
			)
			t_starts = np.maximum(t_starts, slab_t_starts)
			t_ends = np.minimum(t_ends, slab_t_ends)
			hit_mask &= slab_hit_mask & (t_ends > t_starts)

		# Slab marching: one Python iteration per depth step, all active rays batched
		_phase_timings["depth_clipping"] = float(perf_counter() - _t_depth_start)
		projection_flat = np.zeros(n_pixels, dtype=np.float32)
		total_sample_count = 0
		traced_pixels = int(np.sum(hit_mask))

		if traced_pixels > 0:
			hit_indices = np.where(hit_mask)[0]
			marched_sources = []
			direct_sources = []
			for source in self.sample_sources:
				if source.uses_direct_integral():
					direct_sources.append(source)
					continue
				marched_sources.append(source)

			has_direct = len(direct_sources) > 0
			has_marched = len(marched_sources) > 0
			if has_direct and has_marched:
				direct_progress_fraction = (0.0, 0.6)
				marched_progress_fraction = (0.6, 1.0)
			elif has_direct:
				direct_progress_fraction = (0.0, 1.0)
				marched_progress_fraction = (1.0, 1.0)
			else:
				direct_progress_fraction = (0.0, 0.0)
				marched_progress_fraction = (0.0, 1.0)

			_t_direct_start = perf_counter()
			for source_idx, source in enumerate(direct_sources):
				source_progress_start = direct_progress_fraction[0]
				source_progress_end = direct_progress_fraction[1]
				if has_direct:
					source_progress_start = direct_progress_fraction[0] + (
						(direct_progress_fraction[1] - direct_progress_fraction[0]) * (float(source_idx) / float(len(direct_sources)))
					)
					source_progress_end = direct_progress_fraction[0] + (
						(direct_progress_fraction[1] - direct_progress_fraction[0]) * (float(source_idx + 1) / float(len(direct_sources)))
					)
				_t_src_start = perf_counter()
				direct_integral = source.ray_integral_world(
					ray_origins=ray_origins[hit_indices],
					ray_directions=ray_directions[hit_indices],
					t_starts=t_starts[hit_indices],
					t_ends=t_ends[hit_indices],
					physics_model=physics_model,
					step_mm=step_mm,
					progress_callback=progress_callback,
					progress_fraction=(source_progress_start, source_progress_end),
					geometry=geometry,
					reference_transform=reference_transform,
					hit_ray_indices=hit_indices,
					detector_shape_hw=(height, width),
				)
				source_integrals, source_work_count = direct_integral
				projection_flat[hit_indices] += np.asarray(source_integrals, dtype=np.float32)
				total_sample_count += int(source_work_count)
				_t_src_elapsed = float(perf_counter() - _t_src_start)
				_src_stat: dict = {
					"label": getattr(
						getattr(source, "mesh", None) or getattr(source, "volumetric", None),
						"label", type(source).__name__,
					),
					"source_type": type(source).__name__,
					"elapsed_s": _t_src_elapsed,
					"work_count": int(source_work_count),
				}
				if isinstance(source, MeshXRaySource):
					_src_stat["backend"] = source.backend
					_src_stat["mode"] = source.mode
					_src_stat["triangle_count"] = int(source._triangles_world.shape[0])
					if hasattr(source, "_last_bvh_build_s"):
						_src_stat["bvh_build_s"] = float(source._last_bvh_build_s)
					if hasattr(source, "_last_stack_timing"):
						_src_stat["stack_build_s"]         = float(source._last_stack_timing.get("total_s", 0.0))
						_src_stat["stack_uv_projection_s"] = float(source._last_stack_timing.get("uv_projection_s", 0.0))
						_src_stat["stack_rasterize_s"]     = float(source._last_stack_timing.get("rasterize_s", 0.0))
						_src_stat["stack_csr_s"]           = float(source._last_stack_timing.get("csr_s", 0.0))
					if hasattr(source, "_last_integral_timing"):
						_src_stat["integration_s"] = float(source._last_integral_timing.get("integration_s", 0.0))
				_per_source_stats.append(_src_stat)
			_phase_timings["direct_sources_total"] = float(perf_counter() - _t_direct_start)
			_t_marching_start = perf_counter()
			if marched_sources:
				t_start_global = float(np.min(t_starts[hit_mask]))
				t_global_max = float(np.max(t_ends[hit_mask]))
				t_values = np.arange(t_start_global, t_global_max + step_mm * 0.5, step_mm, dtype=np.float64)
				n_steps = len(t_values)
				_last_progress_clock = perf_counter()
				for i, t_k in enumerate(t_values):
					if progress_callback is not None and perf_counter() - _last_progress_clock >= 0.15:
						_last_progress_clock = perf_counter()
						progress_callback(
							marched_progress_fraction[0]
							+ (marched_progress_fraction[1] - marched_progress_fraction[0]) * (i / max(n_steps, 1))
						)
					t_k_f = float(t_k)
					active = hit_mask & (t_k_f >= t_starts) & (t_k_f <= t_ends)
					if not np.any(active):
						continue
					active_idx = np.where(active)[0]
					points_world = ray_origins[active_idx] + t_k_f * ray_directions[active_idx]
					total_mu = np.zeros(len(active_idx), dtype=np.float32)
					for source in marched_sources:
						total_mu += source.sample_attenuation_world(points_world, physics_model)
					projection_flat[active_idx] += total_mu * step_mm
					total_sample_count += len(active_idx)

			_phase_timings["marching_total"] = float(perf_counter() - _t_marching_start)
			for _vsrc in marched_sources:
				_vol_label = getattr(getattr(_vsrc, "volumetric", None), "label", None) or type(_vsrc).__name__
				_vsrc_stat: dict = {
					"label": _vol_label,
					"source_type": type(_vsrc).__name__,
					"elapsed_s": _phase_timings["marching_total"] / max(len(marched_sources), 1),
					"work_count": int(total_sample_count),
				}
				if isinstance(_vsrc, VolumetricXRaySource):
					_vsrc_stat["volume_shape"] = tuple(int(x) for x in _vsrc._volume.shape)
					_vsrc_stat["interpolation"] = _vsrc.interpolation
				_per_source_stats.append(_vsrc_stat)

			if progress_callback is not None:
				progress_callback(1.0)

		_t_physics_start = perf_counter()
		projection = physics_model.integral_to_image(
			projection_flat,
			source_to_detector_distance_mm=source_to_detector_distance_mm,
			projection_mode="cone" if geometry.is_cone_beam() else "parallel",
		).reshape(height, width)
		_phase_timings["physics_conversion"] = float(perf_counter() - _t_physics_start)

		if not return_stats:
			return projection

		elapsed_seconds = perf_counter() - start_time
		stats = XRayProjectionStats(
			elapsed_seconds=float(elapsed_seconds),
			total_pixels=n_pixels,
			traced_pixels=traced_pixels,
			total_sample_count=total_sample_count,
			source_count=int(len(self.sample_sources)),
			step_mm=step_mm,
			projection_mode="cone" if geometry.is_cone_beam() else "parallel",
			detector_shape_hw=(height, width),
			depth_window_mode=depth_mode,
			phase_timings=_phase_timings,
			per_source_stats=_per_source_stats,
		)
		return projection, stats

	def project_config(self, config, return_stats=False, progress_callback=None):
		"""Project the scene using a higher-level configuration object."""
		if not isinstance(config, XRayProjectionConfig):
			raise TypeError("config must be an instance of XRayProjectionConfig.")
		return self.project(
			geometry=config.effective_geometry(),
			physics_model=config.physics_model,
			reference_transform=config.reference_transform,
			return_stats=return_stats,
			progress_callback=progress_callback,
		)
