# -*- coding: utf-8 -*-
"""Scene-tree object that owns X-ray geometry and gathers descendant volumetric sources."""

from __future__ import annotations

import OpenGL.GL as gl
import numpy as np

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
	XRayScene,
)


class VirtualXRay(Object):
	"""Represent one virtual X-ray setup integrated with the existing scene tree."""

	def __init__(self, parent=None):
		"""Initialize one X-ray scene node with default geometry, physics and presentation settings."""
		super().__init__(parent)
		self.label = "VirtualXRay"

		self.detector_center_ref = np.array([42.2, 42.2, 180.0], dtype=np.float32)
		self.detector_normal_ref = np.array([0.0, 0.0, -1.0], dtype=np.float32)
		self.detector_up_ref = np.array([0.0, 1.0, 0.0], dtype=np.float32)
		self.detector_shape_hw = [512, 512]
		self.detector_pixel_size_mm = [0.4, 0.4]

		self.source_position_ref = np.array([42.2, 42.2, -220.0], dtype=np.float32)
		self.ray_direction_ref = None
		self.step_mm = 1.0

		self.quality_profile_name = "normal"
		self.source_interpolation = "linear"
		self.source_fill_value = None

		self.physics_mu_air = 0.0
		self.physics_mu_water = 0.02
		self.physics_hounsfield_air = -1000.0
		self.physics_attenuation_scale = 1.0
		self.physics_output_mode = "integral"
		self.physics_intensity_floor = 0.0
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

		self.gizmo_color = (1.0, 0.8, 0.0)
		self.detector_fill_alpha = 0.08
		self.source_gizmo_size_mm = 4.0

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
		return [
			VolumetricXRaySource(
				volumetric=vol,
				global_transform=self.child_transform_relative_to_self(vol),
				interpolation=self.source_interpolation,
				fill_value=self.source_fill_value,
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
		return XRayProjectionGeometry.from_detector_pose(
			detector_center_ref=self.detector_center_ref,
			detector_normal_ref=self.detector_normal_ref,
			detector_up_ref=self.detector_up_ref,
			detector_shape_hw=self.detector_shape_hw,
			detector_pixel_size_mm=self.detector_pixel_size_mm,
			step_mm=self.step_mm,
			source_position_ref=self.source_position_ref,
			ray_direction_ref=self.ray_direction_ref,
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

	def build_projection_config(self):
		"""Return a complete projection configuration based on this scene object."""
		return XRayProjectionConfig(
			geometry=self.build_geometry(),
			physics_model=self.build_physics_model(),
			presentation_model=self.build_presentation_model(),
			reference_transform=np.eye(4, dtype=np.float32),
			quality_profile=self.quality_profile(),
		)

	def project(self, return_stats=False):
		"""Project all descendant volumetrics using the current setup state."""
		return self.build_scene().project(self.build_projection_config(), return_stats=return_stats)

	def render_projection(self, return_stats=False):
		"""Project and immediately apply the configured presentation model."""
		return self.build_scene().render(self.build_projection_config(), return_stats=return_stats)

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
		if self.source_position_ref is not None:
			points.append(np.asarray(self.source_position_ref, dtype=np.float32)[None, :])
		all_points = np.vstack(points)
		return True, all_points.min(axis=0).tolist(), all_points.max(axis=0).tolist()

	def renderSelf(self):
		"""Render a lightweight source-detector gizmo directly in the current OpenGL model space."""
		corners = self.detector_corners_ref()
		center = corners.mean(axis=0)

		gl.glPushAttrib(gl.GL_ALL_ATTRIB_BITS)
		gl.glDisable(gl.GL_TEXTURE_2D)
		gl.glEnable(gl.GL_BLEND)
		gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
		gl.glLineWidth(2.0)

		gl.glColor4f(self.gizmo_color[0], self.gizmo_color[1], self.gizmo_color[2], self.detector_fill_alpha)
		gl.glBegin(gl.GL_QUADS)
		for corner in corners:
			gl.glVertex3f(*corner)
		gl.glEnd()

		gl.glColor3f(*self.gizmo_color)
		gl.glBegin(gl.GL_LINE_LOOP)
		for corner in corners:
			gl.glVertex3f(*corner)
		gl.glEnd()

		gl.glBegin(gl.GL_LINES)
		gl.glVertex3f(*corners[0]); gl.glVertex3f(*corners[2])
		gl.glVertex3f(*corners[1]); gl.glVertex3f(*corners[3])
		gl.glEnd()

		if self.source_position_ref is not None:
			source = np.asarray(self.source_position_ref, dtype=np.float32)
			size = float(self.source_gizmo_size_mm)
			gl.glBegin(gl.GL_LINES)
			gl.glVertex3f(source[0] - size, source[1], source[2]); gl.glVertex3f(source[0] + size, source[1], source[2])
			gl.glVertex3f(source[0], source[1] - size, source[2]); gl.glVertex3f(source[0], source[1] + size, source[2])
			gl.glVertex3f(source[0], source[1], source[2] - size); gl.glVertex3f(source[0], source[1], source[2] + size)
			gl.glVertex3f(*source); gl.glVertex3f(*center)
			gl.glEnd()
		elif self.ray_direction_ref is not None:
			ray_dir = np.asarray(self.ray_direction_ref, dtype=np.float32)
			norm = np.linalg.norm(ray_dir)
			if norm > 1e-8:
				ray_dir = ray_dir / norm
				arrow_length = max(20.0, 0.25 * np.linalg.norm(corners[2] - corners[0]))
				arrow_start = center - ray_dir * arrow_length
				gl.glBegin(gl.GL_LINES)
				gl.glVertex3f(*arrow_start); gl.glVertex3f(*center)
				gl.glEnd()

		gl.glPopAttrib()

	def info(self):
		"""Return a compact textual summary for debugging and quick inspection."""
		mode = "cone" if self.source_position_ref is not None else "parallel"
		volumes = len(self.collect_volumetrics())
		return f"VirtualXRay(mode={mode}, volumes={volumes}, detector_shape={self.detector_shape_hw}, step_mm={self.step_mm})"
