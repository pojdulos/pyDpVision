# -*- coding: utf-8 -*-
"""World-space X-ray projection backend prepared for multiple scene source types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from time import perf_counter
from typing import Iterable, Sequence

import cv2
import numpy as np
import pydicom
from scipy.ndimage import map_coordinates

from .mesh import Mesh
from .volumetric import Volumetric


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
		}
	elif isinstance(source_object, Mesh):
		defaults = {
			"xray_source_enabled": True,
			"xray_scalar_scale": 1.0,
			"xray_scalar_bias": 0.0,
			"xray_attenuation_multiplier": 1.0,
			"xray_mesh_mode": "solid",
			"xray_mesh_scalar_value": 1800.0,
			"xray_mesh_shell_thickness_mm": 1.0,
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
	                      progress_callback=None, progress_fraction=(0.0, 1.0)):
		"""Optionally return direct line-integral contributions for full rays.

		Sources with analytic or surface-based behaviour can override this hook and
		return a tuple `(integrals, work_item_count)`. Point-sampled volumetric
		sources should keep the default `None` and will be integrated by ray
		marching in `XRayProjector`.
		"""
		return None


class VolumetricXRaySource(XRaySampleSource):
	"""Adapt a `Volumetric` object into a world-space X-ray attenuation source."""

	def __init__(self, volumetric, global_transform=None, interpolation="linear", fill_value=None, scalar_preprocessor=None,
	             scalar_scale=1.0, scalar_bias=0.0, attenuation_multiplier=1.0):
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


class MeshXRaySource(XRaySampleSource):
	"""Adapt one closed triangle mesh into a simplified solid or shell X-ray source."""

	def __init__(self, mesh, global_transform=None, scalar_value=2000.0, mode="solid", shell_thickness_mm=1.0,
	             scalar_scale=1.0, scalar_bias=0.0, attenuation_multiplier=1.0):
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
		if self.mode not in {"solid", "shell"}:
			raise ValueError("mode must be either 'solid' or 'shell'.")

		vertices_world = _transform_points(self.global_transform, np.asarray(self.mesh.m_vertices, dtype=np.float32))
		faces = np.asarray(self.mesh.m_faces, dtype=np.int32)
		self._vertices_world = vertices_world
		self._faces = faces
		self._triangles_world = vertices_world[faces] if faces.size else np.empty((0, 3, 3), dtype=np.float32)
		self._bvh_nodes = _build_triangle_bvh(self._triangles_world, max_leaf_size=8)

	def bounds_world(self):
		"""Return the world-space AABB of the transformed mesh vertices."""
		if self._vertices_world.size == 0:
			zero = np.zeros(3, dtype=np.float32)
			return zero.copy(), zero.copy()
		if self._bvh_nodes:
			root = self._bvh_nodes[0]
			return root["bbox_min"].copy(), root["bbox_max"].copy()
		return self._vertices_world.min(axis=0).astype(np.float32), self._vertices_world.max(axis=0).astype(np.float32)

	def sample_attenuation_world(self, points_world, physics_model):
		"""Mesh sources are integrated analytically per ray and do not support point sampling."""
		points_world = np.asarray(points_world, dtype=np.float32)
		return np.zeros(points_world.shape[0], dtype=np.float32)

	def ray_integral_world(self, ray_origins, ray_directions, t_starts, t_ends, physics_model, step_mm,
	                      progress_callback=None, progress_fraction=(0.0, 1.0)):
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

		intersection_work_count = 0
		dedup_eps = max(1e-4, 0.25 * float(step_mm))
		progress_start = float(progress_fraction[0])
		progress_end = float(progress_fraction[1])
		progress_span = max(0.0, progress_end - progress_start)
		progress_stride = max(1, n_rays // 200)
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
			else:
				# Fallback for open or imperfect meshes: treat one isolated hit as a thin shell.
				integrals[ray_idx] = self.shell_thickness_mm * mu_value

		if progress_callback is not None:
			progress_callback(progress_end)
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

		# Vectorized AABB intersection for all rays
		t_starts, t_ends, hit_mask = _ray_box_intersections_vectorized(
			ray_origins, ray_directions, scene_min_world, scene_max_world,
		)
		t_starts = np.maximum(t_starts, 0.0)
		hit_mask &= t_ends > t_starts
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
		projection_flat = np.zeros(n_pixels, dtype=np.float32)
		total_sample_count = 0
		traced_pixels = int(np.sum(hit_mask))

		if traced_pixels > 0:
			hit_indices = np.where(hit_mask)[0]
			marched_sources = []
			direct_sources = []
			for source in self.sample_sources:
				if type(source).ray_integral_world is not XRaySampleSource.ray_integral_world:
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
				direct_integral = source.ray_integral_world(
					ray_origins=ray_origins[hit_indices],
					ray_directions=ray_directions[hit_indices],
					t_starts=t_starts[hit_indices],
					t_ends=t_ends[hit_indices],
					physics_model=physics_model,
					step_mm=step_mm,
					progress_callback=progress_callback,
					progress_fraction=(source_progress_start, source_progress_end),
				)
				source_integrals, source_work_count = direct_integral
				projection_flat[hit_indices] += np.asarray(source_integrals, dtype=np.float32)
				total_sample_count += int(source_work_count)

			if marched_sources:
				t_global_max = float(np.max(t_ends[hit_mask]))
				t_values = np.arange(0.0, t_global_max + step_mm * 0.5, step_mm, dtype=np.float64)
				n_steps = len(t_values)
				for i, t_k in enumerate(t_values):
					if progress_callback is not None and i % 10 == 0:
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

			if progress_callback is not None:
				progress_callback(1.0)

		projection = physics_model.integral_to_image(
			projection_flat,
			source_to_detector_distance_mm=source_to_detector_distance_mm,
			projection_mode="cone" if geometry.is_cone_beam() else "parallel",
		).reshape(height, width)

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
