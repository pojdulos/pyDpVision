# -*- coding: utf-8 -*-
"""Scene-tree object that owns X-ray geometry and gathers descendant volumetric sources."""

from __future__ import annotations

import json
from pathlib import Path

import OpenGL.GL as gl
import numpy as np

from .marchingCubes import mc_estimate_threshold, mc_gradient
from .object import Object
from .volumetric import Volumetric
from .xrayProjection import (
	DigitalRadiographyPresentationModel,
	FilmLikePresentationModel,
	RawPresentationModel,
	VolumetricXRaySource,
	XRayPhysicsModel,
	XRayProjectionConfig,
	XRayProjectionGeometry,
	XRayProjectionQualityProfile,
	XRayScalarPreprocessor,
	XRayScene,
)


class VirtualXRay(Object):
	"""Represent one virtual X-ray setup integrated with the existing scene tree."""

	GEOMETRY_PRESET_FILE = Path(__file__).resolve().parent / "presets" / "xray_geometry_presets.json"

	DEFAULT_GEOMETRY_PRESETS = {
		"ceph_lateral": {
			"projection_mode": "cone",
			"detector_center_ref": [400.0, 0.0, 0.0],
			"detector_normal_ref": [-1.0, 0.0, 0.0],
			"detector_up_ref": [0.0, 0.0, 1.0],
			"detector_shape_hw": [800, 1000],
			"detector_pixel_size_mm": [0.30, 0.30],
			"source_position_ref": [-1500.0, 0.0, 0.0],
			"ray_direction_ref": [1.0, 0.0, 0.0],
			"step_mm": 1.0,
			"quality_profile_name": "normal",
		},
		"ceph_pa": {
			"projection_mode": "cone",
			"detector_center_ref": [0.0, 400.0, 0.0],
			"detector_normal_ref": [0.0, -1.0, 0.0],
			"detector_up_ref": [0.0, 0.0, 1.0],
			"detector_shape_hw": [800, 1000],
			"detector_pixel_size_mm": [0.30, 0.30],
			"source_position_ref": [0.0, -1500.0, 0.0],
			"ray_direction_ref": [0.0, 1.0, 0.0],
			"step_mm": 1.0,
			"quality_profile_name": "normal",
		},
		"skull_ap": {
			"projection_mode": "cone",
			"detector_center_ref": [0.0, 400.0, 0.0],
			"detector_normal_ref": [0.0, -1.0, 0.0],
			"detector_up_ref": [0.0, 0.0, 1.0],
			"detector_shape_hw": [900, 900],
			"detector_pixel_size_mm": [0.28, 0.28],
			"source_position_ref": [0.0, -1100.0, 0.0],
			"ray_direction_ref": [0.0, 1.0, 0.0],
			"step_mm": 0.9,
			"quality_profile_name": "normal",
		},
		"cone_closeup": {
			"projection_mode": "cone",
			"detector_center_ref": [0.0, 0.0, 180.0],
			"detector_normal_ref": [0.0, 0.0, -1.0],
			"detector_up_ref": [0.0, 1.0, 0.0],
			"detector_shape_hw": [768, 768],
			"detector_pixel_size_mm": [0.22, 0.22],
			"source_position_ref": [0.0, 0.0, -260.0],
			"ray_direction_ref": [0.0, 0.0, 1.0],
			"step_mm": 0.8,
			"quality_profile_name": "normal",
		},
	}

	PRESENTATION_PRESETS = {
		"balanced": {
			"presentation_mode": "digital",
			"presentation_invert": False,
			"presentation_gamma": 0.85,
			"presentation_contrast": 1.10,
			"presentation_robust_percentile": 99.2,
			"presentation_window_center": None,
			"presentation_window_width": None,
		},
		"bone_soft": {
			"presentation_mode": "digital",
			"presentation_invert": False,
			"presentation_gamma": 1.35,
			"presentation_contrast": 1.18,
			"presentation_robust_percentile": 98.8,
			"presentation_window_center": None,
			"presentation_window_width": None,
		},
		"bone_contrast": {
			"presentation_mode": "digital",
			"presentation_invert": False,
			"presentation_gamma": 1.55,
			"presentation_contrast": 1.40,
			"presentation_robust_percentile": 98.4,
			"presentation_window_center": None,
			"presentation_window_width": None,
		},
		"film_soft": {
			"presentation_mode": "film",
			"presentation_invert": False,
			"presentation_gamma": 1.60,
			"presentation_contrast": 1.10,
			"presentation_robust_percentile": 99.0,
			"presentation_window_center": None,
			"presentation_window_width": None,
		},
	}

	def __init__(self, parent=None):
		"""Initialize one X-ray scene node with default geometry, physics and presentation settings."""
		super().__init__(parent)
		self.label = "VirtualXRay"

		self.detector_center_ref = np.array([0.0, 0.0, 180.0], dtype=np.float32)
		self.detector_normal_ref = np.array([0.0, 0.0, -1.0], dtype=np.float32)
		self.detector_up_ref = np.array([0.0, 1.0, 0.0], dtype=np.float32)
		self.detector_shape_hw = [512, 512]
		self.detector_pixel_size_mm = [0.4, 0.4]

		self.source_position_ref = np.array([0.0, 0.0, -220.0], dtype=np.float32)
		self.ray_direction_ref = np.array([0.0, 0.0, 1.0], dtype=np.float32)
		self.projection_mode = "cone"
		self.step_mm = 1.0
		self.last_raw_projection = None
		self.last_projection_image = None

		self.quality_profile_name = "normal"
		self.source_interpolation = "linear"
		self.source_fill_value = None
		self.source_preprocess_mode = "none"
		self.source_preprocess_low_percentile = 0.5
		self.source_preprocess_high_percentile = 99.5
		self.source_preprocess_output_low = -1000.0
		self.source_preprocess_output_high = 2500.0

		self.physics_mu_air = 0.0
		self.physics_mu_water = 0.02
		self.physics_hounsfield_air = -1000.0
		self.physics_attenuation_scale = 1.0
		self.physics_output_mode = "integral"
		self.physics_intensity_floor = 0.0
		self.physics_material_response_mode = "linear"
		self.physics_bone_threshold_hu = None
		self.physics_bone_threshold_softness = 250.0
		self.physics_material_window_center = None
		self.physics_material_window_width = None
		self.physics_material_window_mode = "hard"
		self.physics_material_window_softness = 150.0

		self.presentation_mode = "digital"
		self.presentation_invert = False
		self.presentation_gamma = 0.7
		self.presentation_contrast = 1.2
		self.presentation_robust_percentile = 99.5
		self.presentation_window_center = None
		self.presentation_window_width = None

		self.detector_fill_color = (0.18, 0.55, 0.62)
		self.detector_edge_color = (0.42, 0.90, 0.95)
		self.detector_cross_color = (0.24, 0.72, 0.78)
		self.source_color = (1.00, 0.72, 0.22)
		self.link_color = (0.96, 0.78, 0.34)
		self.frustum_color = (0.86, 0.84, 0.52)
		self.axis_colors = (
			(0.92, 0.30, 0.30),
			(0.30, 0.82, 0.42),
			(0.34, 0.54, 0.95),
		)
		self.detector_fill_alpha = 0.10
		self.frustum_alpha = 0.28
		self.source_gizmo_size_mm = 4.0
		self.axis_gizmo_length_mm = 18.0

	def reference_transform(self):
		"""Return the global transform of this scene node used as a local X-ray reference frame."""
		return np.asarray(self.getGlobalTransformation(), dtype=np.float32)

	def child_transform_relative_to_self(self, child):
		"""Return one descendant transform expressed in the local frame of this X-ray object."""
		self_global = self.reference_transform()
		child_global = np.asarray(child.getGlobalTransformation(), dtype=np.float32)
		return np.linalg.inv(self_global) @ child_global

	def _iter_descendants(self, node=None):
		"""Yield descendants recursively while treating nested `VirtualXRay` nodes as separate sub-scenes."""
		node = self if node is None else node
		for child in node.children():
			yield child
			if isinstance(child, VirtualXRay):
				continue
			yield from self._iter_descendants(child)

	def collect_volumetrics(self):
		"""Return volumetric descendants that should participate in this X-ray scene."""
		return [node for node in self._iter_descendants() if isinstance(node, Volumetric)]

	def scene_sources(self):
		"""Build X-ray sample sources from descendant volumetrics in the local frame of this object."""
		scalar_preprocessor = self.build_scalar_preprocessor()
		return [
			VolumetricXRaySource(
				volumetric=vol,
				global_transform=self.child_transform_relative_to_self(vol),
				interpolation=self.source_interpolation,
				fill_value=self.source_fill_value,
				scalar_preprocessor=scalar_preprocessor,
			)
			for vol in self.collect_volumetrics()
		]

	def build_scene(self):
		"""Return an `XRayScene` assembled from the current descendant volumetrics."""
		return XRayScene.from_sample_sources(self.scene_sources())

	def quality_profile(self):
		"""Return the selected quality profile instance."""
		name = str(self.quality_profile_name).lower()
		if name == "draft":
			return XRayProjectionQualityProfile.draft()
		if name == "high":
			return XRayProjectionQualityProfile.high()
		return XRayProjectionQualityProfile.normal()

	def build_geometry(self):
		"""Build the current projection geometry from intuitive detector pose parameters."""
		is_cone = str(self.projection_mode).lower() == "cone"
		return XRayProjectionGeometry.from_detector_pose(
			detector_center_ref=self.detector_center_ref,
			detector_normal_ref=self.detector_normal_ref,
			detector_up_ref=self.detector_up_ref,
			detector_shape_hw=self.detector_shape_hw,
			detector_pixel_size_mm=self.detector_pixel_size_mm,
			step_mm=self.step_mm,
			source_position_ref=self.source_position_ref if is_cone else None,
			ray_direction_ref=self.ray_direction_ref if not is_cone else None,
		)

	def build_scalar_preprocessor(self):
		"""Build the optional source scalar preprocessor used before attenuation mapping."""
		return XRayScalarPreprocessor(
			mode=self.source_preprocess_mode,
			input_low_percentile=self.source_preprocess_low_percentile,
			input_high_percentile=self.source_preprocess_high_percentile,
			output_low_value=self.source_preprocess_output_low,
			output_high_value=self.source_preprocess_output_high,
		)

	def build_physics_model(self):
		"""Build the physics model described by the current object state."""
		return XRayPhysicsModel(
			mu_air=self.physics_mu_air,
			mu_water=self.physics_mu_water,
			hounsfield_air=self.physics_hounsfield_air,
			attenuation_scale=self.physics_attenuation_scale,
			output_mode=self.physics_output_mode,
			intensity_floor=self.physics_intensity_floor,
			material_response_mode=self.physics_material_response_mode,
			bone_threshold_hu=self.physics_bone_threshold_hu,
			bone_threshold_softness=self.physics_bone_threshold_softness,
			material_window_center=self.physics_material_window_center,
			material_window_width=self.physics_material_window_width,
			material_window_mode=self.physics_material_window_mode,
			material_window_softness=self.physics_material_window_softness,
		)

	def build_presentation_model(self):
		"""Build the selected presentation model for display-ready output."""
		mode = str(self.presentation_mode).lower()
		if mode == "raw":
			return RawPresentationModel()
		if mode == "film":
			return FilmLikePresentationModel(
				robust_percentile=self.presentation_robust_percentile,
				gamma=self.presentation_gamma,
				contrast=self.presentation_contrast,
				invert=self.presentation_invert,
			)
		return DigitalRadiographyPresentationModel(
			window_center=self.presentation_window_center,
			window_width=self.presentation_window_width,
			robust_percentile=self.presentation_robust_percentile,
			invert=self.presentation_invert,
			gamma=self.presentation_gamma,
			contrast=self.presentation_contrast,
		)

	@classmethod
	def presentation_preset_names(cls):
		"""Return presentation preset names exposed by the scene object."""
		return list(cls.PRESENTATION_PRESETS.keys())

	@classmethod
	def geometry_preset_names(cls):
		"""Return geometry preset names exposed by the scene object."""
		return list(cls.load_geometry_presets().keys())

	@classmethod
	def load_geometry_presets(cls):
		"""Load geometry presets from JSON and fall back to built-in defaults when needed."""
		preset_file = Path(cls.GEOMETRY_PRESET_FILE)
		if not preset_file.exists():
			return dict(cls.DEFAULT_GEOMETRY_PRESETS)

		try:
			with preset_file.open("r", encoding="utf-8") as handle:
				payload = json.load(handle)
		except Exception:
			return dict(cls.DEFAULT_GEOMETRY_PRESETS)

		if not isinstance(payload, dict):
			return dict(cls.DEFAULT_GEOMETRY_PRESETS)

		presets = {}
		for preset_name, preset_definition in payload.items():
			if not isinstance(preset_definition, dict):
				continue
			presets[str(preset_name).lower()] = dict(preset_definition)

		if not presets:
			return dict(cls.DEFAULT_GEOMETRY_PRESETS)
		return presets

	def apply_presentation_preset(self, preset_name):
		"""Apply one predefined presentation preset to the current object state."""
		preset = self.PRESENTATION_PRESETS.get(str(preset_name).lower())
		if preset is None:
			raise KeyError(f"Unknown presentation preset: {preset_name}")
		for attr_name, attr_value in preset.items():
			setattr(self, attr_name, attr_value)

	def apply_geometry_preset(self, preset_name):
		"""Apply one predefined geometry preset to the current X-ray setup."""
		preset = self.load_geometry_presets().get(str(preset_name).lower())
		if preset is None:
			raise KeyError(f"Unknown geometry preset: {preset_name}")
		for attr_name, attr_value in preset.items():
			if attr_name.endswith("_ref"):
				setattr(self, attr_name, np.asarray(attr_value, dtype=np.float32))
			elif attr_name in {"detector_shape_hw"}:
				setattr(self, attr_name, [int(attr_value[0]), int(attr_value[1])])
			elif attr_name in {"detector_pixel_size_mm"}:
				setattr(self, attr_name, [float(attr_value[0]), float(attr_value[1])])
			elif attr_name == "step_mm":
				setattr(self, attr_name, float(attr_value))
			else:
				setattr(self, attr_name, attr_value)

	def build_projection_config(self):
		"""Return a complete projection configuration based on this scene object."""
		return XRayProjectionConfig(
			geometry=self.build_geometry(),
			physics_model=self.build_physics_model(),
			presentation_model=self.build_presentation_model(),
			reference_transform=np.eye(4, dtype=np.float32),
			quality_profile=self.quality_profile(),
		)

	def estimate_bone_threshold(self, threshold_min=300.0, max_sample_voxels=4_000_000):
		"""Estimate one bone HU threshold from descendant volumetrics.

		This reuses the gradient-driven heuristic from `marchingCubes.py`, but
		stops at the threshold estimate instead of expanding it into a full
		projection window.
		"""
		estimates = []
		for volumetric in self.collect_volumetrics():
			volume = np.asarray(volumetric.m_volume, dtype=np.float32)
			if volume.ndim != 3 or volume.size == 0:
				continue

			downsample = 1
			if volume.size > max_sample_voxels:
				downsample = int(np.ceil((volume.size / float(max_sample_voxels)) ** (1.0 / 3.0)))
			volume_sample = volume[::downsample, ::downsample, ::downsample]

			_origin_world, _axes_world, spacing_xyz = volumetric.get_volume_geometry()
			px = max(1e-6, float(spacing_xyz[0]) * downsample)
			py = max(1e-6, float(spacing_xyz[1]) * downsample)
			pz = max(1e-6, float(spacing_xyz[2]) * downsample)
			gradient, _gx_full, _gy_full, _gz_full = mc_gradient(
				volume_sample,
				None,
				pz,
				py,
				px,
				sharpening=False,
			)
			threshold = mc_estimate_threshold(
				volume_sample,
				gradient,
				threshold=None,
				threshold_min=threshold_min,
			)
			estimates.append({
				"threshold": float(threshold),
				"voxel_count": int(volume_sample.size),
			})

		if not estimates:
			raise ValueError("Could not estimate one bone HU threshold from the current X-ray scene.")

		weights = np.asarray([item["voxel_count"] for item in estimates], dtype=np.float64)
		weights /= max(weights.sum(), 1.0)

		def _weighted_average(field_name):
			return float(sum(item[field_name] * weight for item, weight in zip(estimates, weights)))

		return {
			"threshold": _weighted_average("threshold"),
			"per_volume": estimates,
		}

	def apply_estimated_bone_threshold(self, threshold_min=300.0):
		"""Estimate and apply one bone HU threshold to the current scene."""
		estimate = self.estimate_bone_threshold(threshold_min=threshold_min)
		self.physics_material_response_mode = "bone_threshold"
		self.physics_bone_threshold_hu = float(estimate["threshold"])
		self.physics_material_window_center = None
		self.physics_material_window_width = None
		return estimate

	def project(self, return_stats=False):
		"""Project all descendant volumetrics using the current setup state."""
		return self.build_scene().project(self.build_projection_config(), return_stats=return_stats)

	def render_projection(self, return_stats=False):
		"""Project and immediately apply the configured presentation model."""
		return self.build_scene().render(self.build_projection_config(), return_stats=return_stats)

	def project_and_cache(self, return_stats=False, progress_callback=None):
		"""Project the scene, store the raw result in `last_raw_projection`, and return it."""
		if return_stats:
			raw, stats = self.build_scene().project(self.build_projection_config(), return_stats=True, progress_callback=progress_callback)
			self.last_raw_projection = np.asarray(raw, dtype=np.float32)
			return self.last_raw_projection, stats
		raw = self.build_scene().project(self.build_projection_config(), return_stats=False, progress_callback=progress_callback)
		self.last_raw_projection = np.asarray(raw, dtype=np.float32)
		return self.last_raw_projection

	def apply_presentation(self):
		"""Apply the current presentation model to `last_raw_projection` without re-projecting.

		Returns the display-ready float32 image, or ``None`` if no projection has been cached yet.
		"""
		if self.last_raw_projection is None:
			return None
		return self.build_presentation_model().apply(self.last_raw_projection)

	def detector_corners_ref(self):
		"""Return detector corners in local reference coordinates for gizmo drawing and bounding box computation."""
		geometry = self.build_geometry()
		height, width = int(geometry.detector_shape_hw[0]), int(geometry.detector_shape_hw[1])
		origin = np.asarray(geometry.detector_origin_ref, dtype=np.float32)
		u = np.asarray(geometry.detector_u_ref, dtype=np.float32)
		v = np.asarray(geometry.detector_v_ref, dtype=np.float32)
		return np.array([
			origin,
			origin + u * float(width - 1),
			origin + u * float(width - 1) + v * float(height - 1),
			origin + v * float(height - 1),
		], dtype=np.float32)

	def getLocalBB(self):
		"""Return a local bounding box covering the source and detector gizmos."""
		points = [self.detector_corners_ref()]
		if str(self.projection_mode).lower() == "cone":
			points.append(np.asarray(self.source_position_ref, dtype=np.float32)[None, :])
		all_points = np.vstack(points)
		return True, all_points.min(axis=0).tolist(), all_points.max(axis=0).tolist()

	def renderSelf(self):
		"""Render a lightweight source-detector gizmo directly in the current OpenGL model space."""
		corners = self.detector_corners_ref()
		center = corners.mean(axis=0)
		axis_length = float(self.axis_gizmo_length_mm)

		gl.glPushAttrib(gl.GL_ALL_ATTRIB_BITS)
		gl.glDisable(gl.GL_TEXTURE_2D)
		gl.glDisable(gl.GL_LIGHTING)
		gl.glDisable(gl.GL_COLOR_MATERIAL)
		gl.glEnable(gl.GL_BLEND)
		gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
		gl.glLineWidth(2.0)

		gl.glColor4f(
			self.detector_fill_color[0],
			self.detector_fill_color[1],
			self.detector_fill_color[2],
			self.detector_fill_alpha,
		)
		gl.glBegin(gl.GL_QUADS)
		for corner in corners:
			gl.glVertex3f(*corner)
		gl.glEnd()

		gl.glColor3f(*self.detector_edge_color)
		gl.glBegin(gl.GL_LINE_LOOP)
		for corner in corners:
			gl.glVertex3f(*corner)
		gl.glEnd()

		gl.glColor3f(*self.detector_cross_color)
		gl.glBegin(gl.GL_LINES)
		gl.glVertex3f(*corners[0]); gl.glVertex3f(*corners[2])
		gl.glVertex3f(*corners[1]); gl.glVertex3f(*corners[3])
		gl.glEnd()

		gl.glLineWidth(1.5)
		gl.glBegin(gl.GL_LINES)
		for axis_idx, axis_color in enumerate(self.axis_colors):
			gl.glColor3f(*axis_color)
			axis_end = np.array(center, dtype=np.float32)
			axis_end[axis_idx] += axis_length
			gl.glVertex3f(*center)
			gl.glVertex3f(*axis_end)
		gl.glEnd()

		if self.projection_mode == "cone":
			source = np.asarray(self.source_position_ref, dtype=np.float32)
			size = float(self.source_gizmo_size_mm)

			gl.glLineWidth(1.0)
			gl.glColor4f(
				self.frustum_color[0],
				self.frustum_color[1],
				self.frustum_color[2],
				self.frustum_alpha,
			)
			gl.glBegin(gl.GL_LINES)
			for corner in corners:
				gl.glVertex3f(*source)
				gl.glVertex3f(*corner)
			gl.glEnd()

			gl.glLineWidth(2.0)
			gl.glColor3f(*self.source_color)
			gl.glBegin(gl.GL_LINES)
			gl.glVertex3f(source[0] - size, source[1], source[2]); gl.glVertex3f(source[0] + size, source[1], source[2])
			gl.glVertex3f(source[0], source[1] - size, source[2]); gl.glVertex3f(source[0], source[1] + size, source[2])
			gl.glVertex3f(source[0], source[1], source[2] - size); gl.glVertex3f(source[0], source[1], source[2] + size)
			gl.glColor3f(*self.link_color)
			gl.glVertex3f(*source); gl.glVertex3f(*center)
			gl.glEnd()
		elif self.projection_mode == "parallel":
			ray_dir = np.asarray(self.ray_direction_ref, dtype=np.float32)
			norm = np.linalg.norm(ray_dir)
			if norm > 1e-8:
				ray_dir = ray_dir / norm
				arrow_length = max(20.0, 0.25 * np.linalg.norm(corners[2] - corners[0]))
				arrow_start = center - ray_dir * arrow_length
				gl.glColor3f(*self.link_color)
				gl.glBegin(gl.GL_LINES)
				gl.glVertex3f(*arrow_start); gl.glVertex3f(*center)
				gl.glEnd()

		gl.glPopAttrib()

	def info(self):
		"""Return a compact textual summary for debugging and quick inspection."""
		volumes = len(self.collect_volumetrics())
		return f"VirtualXRay(mode={self.projection_mode}, volumes={volumes}, detector_shape={self.detector_shape_hw}, step_mm={self.step_mm})"
