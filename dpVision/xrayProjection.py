# -*- coding: utf-8 -*-
"""World-space X-ray projection backend prepared for multiple scene source types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable, Sequence

import cv2
import numpy as np
import pydicom
from scipy.ndimage import map_coordinates

from .volumetric import Volumetric


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
	ds = pydicom.FileDataset(str(file_path), {}, file_meta=None, preamble=b"\0" * 128)
	ds.file_meta.TransferSyntaxUID = pydicom.uid.ImplicitVRLittleEndian
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

	def validate(self):
		"""Validate geometry fields before projection."""
		height, width = int(self.detector_shape_hw[0]), int(self.detector_shape_hw[1])
		if height <= 0 or width <= 0:
			raise ValueError("detector_shape_hw must contain positive height and width.")
		if float(self.step_mm) <= 0.0:
			raise ValueError("step_mm must be positive.")
		if self.source_position_ref is None and self.ray_direction_ref is None:
			raise ValueError("Either source_position_ref or ray_direction_ref must be provided.")


@dataclass
class XRayPhysicsModel:
	"""Map scalar values to attenuation and convert integrals into detector intensities."""

	mu_air: float = 0.0
	mu_water: float = 0.02
	hounsfield_air: float = -1000.0
	attenuation_scale: float = 1.0
	output_mode: str = "intensity"
	intensity_floor: float = 0.0

	def scalar_to_mu(self, scalar_values):
		"""Convert scalar CT-like values into a linear attenuation coefficient."""
		scalar_values = np.asarray(scalar_values, dtype=np.float32)
		relative_density = np.maximum(0.0, 1.0 + scalar_values / abs(float(self.hounsfield_air)))
		return (float(self.mu_air) + float(self.mu_water) * relative_density) * float(self.attenuation_scale)

	def integral_to_image(self, line_integral):
		"""Convert integrated attenuation into a detector-space image value."""
		line_integral = np.asarray(line_integral, dtype=np.float32)
		mode = str(self.output_mode).lower()
		if mode == "integral":
			return line_integral
		return np.maximum(float(self.intensity_floor), np.exp(-line_integral))


class XRaySampleSource(ABC):
	"""Abstract RTG source that can provide attenuation samples in world coordinates."""

	@abstractmethod
	def bounds_world(self):
		"""Return source world bounds as `(min_xyz, max_xyz)`."""

	@abstractmethod
	def sample_attenuation_world(self, points_world, physics_model):
		"""Return attenuation coefficients sampled at `points_world`."""


class VolumetricXRaySource(XRaySampleSource):
	"""Adapt a `Volumetric` object into a world-space X-ray attenuation source."""

	def __init__(self, volumetric, global_transform=None, interpolation="linear", fill_value=None):
		"""Store volumetric data and transformation used for world-space sampling."""
		if not isinstance(volumetric, Volumetric):
			raise TypeError("volumetric must be an instance of Volumetric.")

		self.volumetric = volumetric
		self.global_transform = np.eye(4, dtype=np.float32) if global_transform is None else np.asarray(global_transform, dtype=np.float32)
		if self.global_transform.shape != (4, 4):
			raise ValueError("global_transform must be a 4x4 homogeneous matrix.")

		self.interpolation = str(interpolation).lower()
		self.fill_value = float(volumetric.m_min if fill_value is None else fill_value)
		self._inverse_global_transform = np.linalg.inv(self.global_transform)
		self._volume = np.asarray(self.volumetric.m_volume, dtype=np.float32)

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
		return map_coordinates(
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

	def sample_attenuation_world(self, points_world, physics_model):
		"""Sample attenuation coefficients in world coordinates using the supplied physics model."""
		return physics_model.scalar_to_mu(self.sample_scalar_world(points_world))


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

	def project(self, geometry, physics_model, reference_transform=None):
		"""Project all sample sources through the provided X-ray geometry."""
		geometry.validate()
		reference_transform = np.eye(4, dtype=np.float32) if reference_transform is None else np.asarray(reference_transform, dtype=np.float32)
		if reference_transform.shape != (4, 4):
			raise ValueError("reference_transform must be a 4x4 homogeneous matrix.")

		scene_min_world, scene_max_world = self.scene_bounds_world()
		height, width = int(geometry.detector_shape_hw[0]), int(geometry.detector_shape_hw[1])
		projection = np.zeros((height, width), dtype=np.float32)

		for row_idx in range(height):
			for col_idx in range(width):
				detector_point_world = self._detector_pixel_world(geometry, reference_transform, row_idx, col_idx)
				ray_origin_world, ray_direction_world = self._ray_definition_world(
					geometry=geometry,
					reference_transform=reference_transform,
					detector_point_world=detector_point_world,
				)
				interval = _ray_box_intersection(
					ray_origin=ray_origin_world,
					ray_direction=ray_direction_world,
					box_min=scene_min_world,
					box_max=scene_max_world,
				)
				if interval is None:
					continue

				t_start, t_end = interval
				if t_end < 0.0:
					continue
				t_start = max(0.0, t_start)
				sample_count = max(1, int(np.ceil((t_end - t_start) / float(geometry.step_mm))) + 1)
				t_values = np.linspace(t_start, t_end, sample_count, dtype=np.float32)
				points_world = ray_origin_world[None, :] + t_values[:, None] * ray_direction_world[None, :]
				total_mu = np.zeros(sample_count, dtype=np.float32)
				for source in self.sample_sources:
					total_mu += source.sample_attenuation_world(points_world, physics_model)
				line_integral = np.sum(total_mu) * float(geometry.step_mm)
				projection[row_idx, col_idx] = physics_model.integral_to_image(line_integral)

		return projection
