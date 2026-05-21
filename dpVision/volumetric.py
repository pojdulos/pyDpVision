import itertools
from math import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from OpenGL.GL import *
import numpy as np
import matplotlib.pyplot as plt
import cv2
import os
import pydicom
from scipy.ndimage import map_coordinates
from tqdm import tqdm

from .globals import AP
from .object import Object
from .shaders import load_and_compile_shader, compile_shader
from .pointCloud import PointCloud
from .mesh import Mesh

class SliceMetadata():
	def __init__(self):
		"""Initialize per-slice geometry and display metadata."""
		self.image_position_patient = [0.0,0.0,0.0]
		self.axis_x = [1.0, 0.0, 0.0]
		self.axis_y = [0.0, 1.0, 0.0]
		self.axis_z = [0.0, 0.0, 1.0]
		self.voxel_spacing = [1.0, 1.0, 1.0]
		self.slice_location = 0.0
		self.pixel_spacing = [1.0, 1.0]
		self.slice_thickness = 1.0
		self.slice_distance = 1.0
		self.gantry_detector_tilt = 0.0
	
	def __str__(self):
		"""Return a short debug string with the current geometry."""
		txt  = f"SliceMetadata"
		txt += f"( gantry_detector_tilt = {self.gantry_detector_tilt}"
		txt += f", slice_thickness = {self.slice_thickness}"
		txt += f", slice_location = {self.slice_location}"
		txt += f", pixel_spacing = {self.pixel_spacing}"
		txt += f", voxel_spacing = {self.voxel_spacing}"
		txt += f", image_position_patient = {self.image_position_patient} )"
		return txt
	
	def __repr__(self):
		return self.__str__()
	
class Volumetric(Object):
	def __init__(self, parent=None):
		super( Volumetric, self ).__init__( parent )
		self.m_dicom_files = []
		self.m_volume = [[[]]]
		self.i = 0
		self.v_vbo = None
		self.shader_program = None
		self.m_minDisplWin = 0.0
		self.m_maxDisplWin = 1.0
		self.m_fastDraw = True
		self.m_renderBoxes = False
		self.m_renderSplats  = False
		self.m_splat_transparent = True
		self.m_splat_scale   = 1.0
		self.m_splat_tint    = [1.0, 1.0, 1.0]
		self.m_splat_additive = False
		self.m_splat_depth_prepass = True
		self.m_splat_depth_cutoff = 0.25
		self.m_splat_hq_sort = False
		self.m_wboit_alpha_scale = 0.7
		self.m_wboit_alpha_gamma = 1.35
		self.m_wboit_alpha_cutoff = 0.02
		self.m_wboit_front_weight = 6.0
		self.splat_shader    = None
		self.splat_hq_shader = None
		self.splat_vbo       = None
		self.splat_hq_vbo    = None
		self.wboit_splat_shader = None
		self.metadata : list[SliceMetadata] = []
		self.m_minSlice = 0
		self.m_maxSlice = 0
		self.m_minRow = 0
		self.m_maxRow = 0
		self.m_minColumn = 0
		self.m_maxColumn = 0
		self.m_filters = [
			[0,  -100,   799],
			[0, -9999, 99999],
			[0, -9999, 99999],
			[0, -9999,  4000],
			[0, -9999, 99999],
			[0, -9999, 99999],
			[0,   800,  4095]]
		
		self.m_fcolors = [
			[1.0, 0.0, 0.0],
			[0.0, 1.0, 0.0],
			[0.0, 0.0, 1.0],
			[1.0, 1.0, 0.0],
			[0.0, 1.0, 1.0],
			[1.0, 0.0, 1.0],
			[1.0, 1.0, 1.0]]

		self.m_shape = (0,0,0)
	
	@property
	def shape(self):
		return self.m_shape
	
	@shape.setter
	def shape(self, _shape):
		self.m_shape = _shape
		

	@property
	def is_transparent(self):
		return self.m_renderSplats and self.m_splat_transparent

	def test_gauss(self):
		from scipy.ndimage import gaussian_filter
		#volume = np.array(trójwymiarowa_lista)  # zamień 'trójwymiarowa_lista' na swoją listę
		
		sigma = 3  # Parametr sigma kontroluje stopień rozmycia
		self.m_volume = gaussian_filter(self.m_volume, sigma=sigma)

	def aply_window(self, x, c, w, ymin=0.0, ymax=1.0):
		'''	windowing C.11.2.1.2.1 Default LINEAR Function
			c - window center, w - window width
			ymin, ymax - destination data intensity range
		'''
		y = np.zeros_like(x)
		y[x <= (c - 0.5 - (w - 1) / 2)] = ymin
		y[x > (c - 0.5 + (w - 1) / 2)] = ymax
		y[(x > (c - 0.5 - (w - 1) / 2)) & (x <= (c - 0.5 + (w - 1) / 2))] = \
			((x[(x > (c - 0.5 - (w - 1) / 2)) & (x <= (c - 0.5 + (w - 1) / 2))] - (c - 0.5)) / (w - 1) + 0.5) * (
					ymax - ymin) + ymin
		return y

	def show_histogram(self):
		data = np.array(self.m_volume).flatten()

		#data = data.clip(lower=data.quantile(0.1), upper=data.quantile(0.9))
		#data = data.clip(lower=0, upper=4096)
		
		biny = np.round(np.arange(0, 1.01, 0.01),2)

		# wygeneruj histogram i zapisz wyniki
		counts, bins = np.histogram(data, bins=biny)

		# wypisz krawędzie binów i częstości
		for i in range(len(bins)-1):
			print(f"Bin: ({bins[i]}, {bins[i+1]}), Częstość: {counts[i]}")

		plt.hist(bins[:-1], bins, weights=counts)

		plt.title('Histogram')
		plt.xlabel('Wartości')
		plt.ylabel('Częstotliwość')
		plt.grid(axis='y', alpha=0.5)
		plt.show()


	def _volume_array(self):
		"""Return the current voxel buffer as a NumPy array."""
		return np.asarray(self.m_volume)

	def get_plane_count(self, plane="XY"):
		"""Return the number of slices available for the requested anatomical plane."""
		shape = self.shape
		if plane == "YZ":
			return int(shape[2])
		if plane == "ZX":
			return int(shape[1])
		return int(shape[0])

	def get_slice_array(self, index, plane="XY"):
		"""Return one 2D slice as a float32 array for the selected plane."""
		volume = self._volume_array()
		if volume.ndim != 3:
			raise ValueError("Volumetric data must be a 3D array.")

		if plane == "YZ":
			index = int(np.clip(index, 0, volume.shape[2] - 1))
			return volume[:, :, index].T.astype(np.float32, copy=False)

		if plane == "ZX":
			index = int(np.clip(index, 0, volume.shape[1] - 1))
			return volume[:, index, :].astype(np.float32, copy=False)

		index = int(np.clip(index, 0, volume.shape[0] - 1))
		return volume[index, :, :].astype(np.float32, copy=False)

	def _reduce_projection_stack(self, sampled_stack, mode="mean", step_mm=1.0, xray_gain=0.03):
		"""Reduce a stack of samples into one 2D projection image."""
		mode = str(mode).lower()
		step_mm = max(1e-6, float(step_mm))
		xray_gain = max(1e-6, float(xray_gain))

		if mode == "sum":
			return np.sum(sampled_stack, axis=0)
		if mode == "max":
			return np.max(sampled_stack, axis=0)
		if mode == "min":
			return np.min(sampled_stack, axis=0)
		if mode == "xray":
			line_integral = np.sum(sampled_stack, axis=0) * step_mm
			# Preview-friendly pseudo-radiograph with smoother low-end response.
			# Log compression keeps weak structures visible without requiring very large gains.
			return np.log1p(xray_gain * line_integral)
		return np.mean(sampled_stack, axis=0)

	def _xray_display_range(self, image):
		"""Return a robust display range for pseudo-Xray preview images."""
		image = np.asarray(image, dtype=np.float32)
		finite_values = image[np.isfinite(image)]
		if finite_values.size == 0:
			return (0.0, 1.0)

		vmin = float(np.min(finite_values))
		vmax = float(np.percentile(finite_values, 99.5))
		if vmax <= vmin:
			vmax = float(np.max(finite_values))
		if vmax <= vmin:
			vmax = vmin + 1.0
		return (vmin, vmax)

	def _map_to_xray_attenuation(self, volume, use_display_window=False):
		"""Map scalar voxel intensities into a positive attenuation proxy for pseudo-Xray."""
		volume = np.asarray(volume, dtype=np.float32)

		if use_display_window:
			low = float(self.m_minDisplWin)
			high = float(self.m_maxDisplWin)
			if high <= low:
				high = low + 1.0
			clipped = np.clip(volume, low, high)
			return (clipped - low) / (high - low)

		# Fallback tuned for CT-like HU ranges: air -> low attenuation, dense tissue/bone -> high.
		low = -1000.0
		high = 2000.0
		clipped = np.clip(volume, low, high)
		return (clipped - low) / (high - low)

	def get_projection_array(self, plane="XY", use_display_window=False, projection_mode="mean", xray_gain=0.03):
		"""Return a projection image for the selected plane."""
		volume = self._volume_array().astype(np.float32, copy=False)
		if volume.ndim != 3:
			raise ValueError("Volumetric data must be a 3D array.")

		if projection_mode == "xray":
			volume = self._map_to_xray_attenuation(
				volume,
				use_display_window=use_display_window,
			)
		elif use_display_window:
			volume = np.clip(volume, self.m_minDisplWin, self.m_maxDisplWin)

		_origin, _basis, spacing = self.get_volume_geometry()
		if plane == "YZ":
			stack = np.transpose(volume, (2, 1, 0))
			return self._reduce_projection_stack(stack, mode=projection_mode, step_mm=spacing[0], xray_gain=xray_gain).astype(np.float32, copy=False)
		if plane == "ZX":
			stack = np.transpose(volume, (1, 0, 2))
			return self._reduce_projection_stack(stack, mode=projection_mode, step_mm=spacing[1], xray_gain=xray_gain).astype(np.float32, copy=False)
		return self._reduce_projection_stack(volume, mode=projection_mode, step_mm=spacing[2], xray_gain=xray_gain).astype(np.float32, copy=False)

	def normalize_slice_to_uint8(self, image, use_display_window=False, invert=False, fixed_range=None, gamma=1.0):
		"""Normalize a 2D float image into an 8-bit grayscale preview buffer."""
		image = np.asarray(image, dtype=np.float32)

		if fixed_range is not None:
			vmin = float(fixed_range[0])
			vmax = float(fixed_range[1])
		elif use_display_window:
			vmin = float(self.m_minDisplWin)
			vmax = float(self.m_maxDisplWin)
		else:
			vmin = float(np.nanmin(image))
			vmax = float(np.nanmax(image))

		if not np.isfinite(vmin):
			vmin = 0.0
		if not np.isfinite(vmax):
			vmax = vmin + 1.0
		if vmax <= vmin:
			vmax = vmin + 1.0

		normalized = np.clip((image - vmin) / (vmax - vmin), 0.0, 1.0)
		gamma = max(1e-6, float(gamma))
		if abs(gamma - 1.0) > 1e-6:
			normalized = np.power(normalized, 1.0 / gamma)
		if invert:
			normalized = 1.0 - normalized

		return np.ascontiguousarray(np.round(normalized * 255.0).astype(np.uint8))

	def get_preview_qimage(self, index, plane="XY", use_display_window=False, invert=False, rtg=False,
	                      projection_mode="mean", xray_gain=0.03, xray_gamma=1.0):
		"""Build a QImage preview for one slice or projection."""
		if rtg:
			image = self.get_projection_array(
				plane=plane,
				use_display_window=use_display_window,
				projection_mode=projection_mode,
				xray_gain=xray_gain,
			)
		else:
			image = self.get_slice_array(index=index, plane=plane)

		buffer = self.normalize_slice_to_uint8(
			image=image,
			use_display_window=(use_display_window and (not rtg or projection_mode != "xray")),
			invert=invert,
			fixed_range=self._xray_display_range(image) if (rtg and projection_mode == "xray") else None,
			gamma=xray_gamma if (rtg and projection_mode == "xray") else 1.0,
		)
		height, width = buffer.shape
		qimage = QImage(buffer.data, width, height, buffer.strides[0], QImage.Format_Grayscale8)
		return qimage.copy()

	def _reduce_slab_samples(self, sampled_stack, slab_mode="mean", step_mm=1.0, xray_gain=0.03):
		"""Reduce stacked slab samples into one 2D preview image."""
		slab_mode = str(slab_mode).lower()
		if slab_mode == "max":
			return np.max(sampled_stack, axis=0)
		if slab_mode == "min":
			return np.min(sampled_stack, axis=0)
		if slab_mode == "center":
			return sampled_stack[len(sampled_stack) // 2]
		return self._reduce_projection_stack(sampled_stack, mode=slab_mode, step_mm=step_mm, xray_gain=xray_gain)

	def _slab_offsets(self, slab_thickness_mm=0.0, slab_samples=1):
		"""Return world-space offsets along the slab normal."""
		slab_samples = max(1, int(slab_samples))
		slab_thickness_mm = max(0.0, float(slab_thickness_mm))
		if slab_samples == 1 or slab_thickness_mm <= 0.0:
			return np.array([0.0], dtype=np.float32)
		return np.linspace(
			-slab_thickness_mm / 2.0,
			slab_thickness_mm / 2.0,
			slab_samples,
			dtype=np.float32,
		)

	def get_slice_array_slab(self, index, plane="XY", slab_thickness_mm=0.0, slab_samples=1,
	                        slab_mode="mean", use_display_window=False, xray_gain=0.03):
		"""Return one orthogonal slice or slab reduced along the selected plane normal."""
		slab_samples = max(1, int(slab_samples))
		slab_thickness_mm = max(0.0, float(slab_thickness_mm))
		if slab_samples == 1 or slab_thickness_mm <= 0.0:
			return self.get_slice_array(index=index, plane=plane)

		volume = self._volume_array().astype(np.float32, copy=False)
		slab_mode = str(slab_mode).lower()
		if slab_mode == "xray":
			volume = self._map_to_xray_attenuation(volume, use_display_window=use_display_window)
		origin, basis, spacing = self.get_volume_geometry()
		offsets = self._slab_offsets(slab_thickness_mm=slab_thickness_mm, slab_samples=slab_samples)
		step_mm = float(abs(offsets[1] - offsets[0])) if len(offsets) > 1 else float(spacing[0] if plane == "YZ" else spacing[1] if plane == "ZX" else spacing[2])

		if plane == "YZ":
			axis_index = 0
			base_voxel = np.array([float(index), 0.0, 0.0], dtype=np.float32)
			height = volume.shape[1]
			width = volume.shape[0]
			x_coords = np.arange(width, dtype=np.float32)
			y_coords = np.arange(height, dtype=np.float32)
			grid_x, grid_y = np.meshgrid(x_coords, y_coords)
			base_points_voxel = np.stack([
				np.full_like(grid_x, base_voxel[0]),
				grid_y,
				grid_x,
			], axis=-1)
		elif plane == "ZX":
			axis_index = 1
			base_voxel = np.array([0.0, float(index), 0.0], dtype=np.float32)
			height = volume.shape[0]
			width = volume.shape[2]
			x_coords = np.arange(width, dtype=np.float32)
			y_coords = np.arange(height, dtype=np.float32)
			grid_x, grid_y = np.meshgrid(x_coords, y_coords)
			base_points_voxel = np.stack([
				grid_x,
				np.full_like(grid_x, base_voxel[1]),
				grid_y,
			], axis=-1)
		else:
			axis_index = 2
			base_voxel = np.array([0.0, 0.0, float(index)], dtype=np.float32)
			height = volume.shape[1]
			width = volume.shape[2]
			x_coords = np.arange(width, dtype=np.float32)
			y_coords = np.arange(height, dtype=np.float32)
			grid_x, grid_y = np.meshgrid(x_coords, y_coords)
			base_points_voxel = np.stack([
				grid_x,
				grid_y,
				np.full_like(grid_x, base_voxel[2]),
			], axis=-1)

		base_world = self.voxel_to_world(base_points_voxel.reshape(-1, 3).T).T.reshape(height, width, 3)
		normal_world = basis[:, axis_index]
		normal_world = normal_world / max(np.linalg.norm(normal_world), 1e-8)

		sampled_images = []
		for offset in offsets:
			points_world = base_world + offset * normal_world[None, None, :]
			points_voxel = self.world_to_voxel(points_world.reshape(-1, 3).T).T.reshape(height, width, 3)
			sampled = map_coordinates(
				volume,
				[
					points_voxel[:, :, 2].ravel(),
					points_voxel[:, :, 1].ravel(),
					points_voxel[:, :, 0].ravel(),
				],
				order=1,
				mode='constant',
				cval=0.0 if slab_mode == "xray" else float(self.m_min),
			).reshape(height, width)
			sampled_images.append(sampled.astype(np.float32, copy=False))

		return self._reduce_slab_samples(
			np.stack(sampled_images, axis=0),
			slab_mode=slab_mode,
			step_mm=step_mm,
			xray_gain=xray_gain,
		).astype(np.float32, copy=False)

	def _axis_vector_from_name(self, axis_name):
		"""Return a unit world axis vector for a short axis name."""
		axis_name = str(axis_name).upper()
		if axis_name == "Y":
			return np.array([0.0, 1.0, 0.0], dtype=np.float32)
		if axis_name == "Z":
			return np.array([0.0, 0.0, 1.0], dtype=np.float32)
		return np.array([1.0, 0.0, 0.0], dtype=np.float32)

	def _rotation_matrix_world(self, axis_vector, angle_degrees):
		"""Build a world-space rotation matrix from axis-angle parameters."""
		axis_vector = np.asarray(axis_vector, dtype=np.float32)
		norm = np.linalg.norm(axis_vector)
		if norm <= 0.0:
			return np.eye(3, dtype=np.float32)

		axis_vector = axis_vector / norm
		angle_radians = np.deg2rad(float(angle_degrees))
		cos_angle = np.cos(angle_radians)
		sin_angle = np.sin(angle_radians)
		one_minus_cos = 1.0 - cos_angle
		x_val, y_val, z_val = axis_vector

		return np.array([
			[
				cos_angle + x_val * x_val * one_minus_cos,
				x_val * y_val * one_minus_cos - z_val * sin_angle,
				x_val * z_val * one_minus_cos + y_val * sin_angle,
			],
			[
				y_val * x_val * one_minus_cos + z_val * sin_angle,
				cos_angle + y_val * y_val * one_minus_cos,
				y_val * z_val * one_minus_cos - x_val * sin_angle,
			],
			[
				z_val * x_val * one_minus_cos - y_val * sin_angle,
				z_val * y_val * one_minus_cos + x_val * sin_angle,
				cos_angle + z_val * z_val * one_minus_cos,
			],
		], dtype=np.float32)

	def _oblique_basis_world(self, base_right, base_up, base_normal,
	                         yaw_degrees=0.0, pitch_degrees=0.0,
	                         yaw_axis="Y", pitch_axis="X"):
		"""Rotate the default slice basis around selected world axes."""
		rotation_yaw = self._rotation_matrix_world(
			self._axis_vector_from_name(yaw_axis),
			yaw_degrees,
		)
		rotation_pitch = self._rotation_matrix_world(
			self._axis_vector_from_name(pitch_axis),
			pitch_degrees,
		)
		rotation_total = rotation_pitch @ rotation_yaw

		right_world = rotation_total @ np.asarray(base_right, dtype=np.float32)
		up_world = rotation_total @ np.asarray(base_up, dtype=np.float32)
		normal_world = rotation_total @ np.asarray(base_normal, dtype=np.float32)

		normal_world /= max(np.linalg.norm(normal_world), 1e-8)
		right_world = np.cross(up_world, normal_world)
		if np.linalg.norm(right_world) < 1e-6:
			fallback_axis = self._axis_vector_from_name("X")
			right_world = np.cross(fallback_axis, normal_world)
		right_world /= max(np.linalg.norm(right_world), 1e-8)
		up_world = np.cross(normal_world, right_world)
		up_world /= max(np.linalg.norm(up_world), 1e-8)
		return right_world, up_world, normal_world

	def get_volume_geometry(self):
		"""Return origin, unit axes and voxel spacing for the current volume geometry."""
		if not self.metadata:
			return (
				np.zeros(3, dtype=np.float32),
				np.eye(3, dtype=np.float32),
				np.ones(3, dtype=np.float32),
			)

		metadata0 = self.metadata[0]
		origin = np.asarray(metadata0.image_position_patient, dtype=np.float32)
		axis_x = np.asarray(getattr(metadata0, "axis_x", [1.0, 0.0, 0.0]), dtype=np.float32)
		axis_y = np.asarray(getattr(metadata0, "axis_y", [0.0, 1.0, 0.0]), dtype=np.float32)
		axis_z = np.asarray(getattr(metadata0, "axis_z", [0.0, 0.0, 1.0]), dtype=np.float32)

		for axis in (axis_x, axis_y, axis_z):
			norm = np.linalg.norm(axis)
			if norm > 0.0:
				axis /= norm

		default_spacing = np.array([
			float(metadata0.pixel_spacing[0]) if len(metadata0.pixel_spacing) > 0 else 1.0,
			float(metadata0.pixel_spacing[1]) if len(metadata0.pixel_spacing) > 1 else 1.0,
			float(metadata0.slice_distance or metadata0.slice_thickness or 1.0),
		], dtype=np.float32)
		stored_spacing = np.asarray(getattr(metadata0, "voxel_spacing", default_spacing), dtype=np.float32)
		spacing = np.where(stored_spacing > 0.0, stored_spacing, default_spacing)

		if len(self.metadata) > 1:
			position0 = np.asarray(self.metadata[0].image_position_patient, dtype=np.float32)
			position1 = np.asarray(self.metadata[1].image_position_patient, dtype=np.float32)
			delta = position1 - position0
			distance = float(np.linalg.norm(delta))
			if distance > 1e-6:
				axis_z = delta / distance
				spacing[2] = distance

		basis = np.column_stack((axis_x, axis_y, axis_z)).astype(np.float32)
		return origin, basis, spacing

	def voxel_to_world(self, point_xyz):
		"""Convert voxel indices [x, y, z] into world coordinates."""
		origin, basis, spacing = self.get_volume_geometry()
		point_xyz = np.asarray(point_xyz, dtype=np.float32)
		if point_xyz.ndim == 1:
			scaled = point_xyz * spacing
			return origin + basis @ scaled

		scaled = point_xyz * spacing[:, None]
		return origin[:, None] + basis @ scaled

	def world_to_voxel(self, point_world):
		"""Convert world coordinates into fractional voxel indices [x, y, z]."""
		origin, basis, spacing = self.get_volume_geometry()
		point_world = np.asarray(point_world, dtype=np.float32)
		transform = basis @ np.diag(spacing)
		inverse = np.linalg.inv(transform)
		if point_world.ndim == 1:
			return inverse @ (point_world - origin)

		return inverse @ (point_world - origin[:, None])

	def _normalize_basis_world(self, basis_world):
		"""Return a basis matrix with unit-length world axes stored in columns."""
		basis_world = np.asarray(basis_world, dtype=np.float32)
		if basis_world.shape != (3, 3):
			raise ValueError("target_basis_world must be a 3x3 matrix with axes in columns.")

		normalized_basis = basis_world.copy()
		for axis_idx in range(3):
			axis_vector = normalized_basis[:, axis_idx]
			norm = float(np.linalg.norm(axis_vector))
			if norm <= 1e-8:
				raise ValueError("Every target basis axis must have non-zero length.")
			normalized_basis[:, axis_idx] = axis_vector / norm
		return normalized_basis

	def _build_metadata_for_grid(self, target_origin_world, target_basis_world, target_spacing_xyz, target_shape_zyx):
		"""Create per-slice metadata that describes the supplied world-space voxel grid."""
		target_origin_world = np.asarray(target_origin_world, dtype=np.float32)
		target_basis_world = self._normalize_basis_world(target_basis_world)
		target_spacing_xyz = np.asarray(target_spacing_xyz, dtype=np.float32)
		layers, _rows, _columns = [int(v) for v in target_shape_zyx]

		metadata = []
		for layer_idx in range(layers):
			mdata = SliceMetadata()
			slice_origin = target_origin_world + target_basis_world[:, 2] * (float(layer_idx) * target_spacing_xyz[2])
			mdata.image_position_patient = slice_origin.astype(np.float32).tolist()
			mdata.axis_x = target_basis_world[:, 0].astype(np.float32).tolist()
			mdata.axis_y = target_basis_world[:, 1].astype(np.float32).tolist()
			mdata.axis_z = target_basis_world[:, 2].astype(np.float32).tolist()
			mdata.voxel_spacing = target_spacing_xyz.astype(np.float32).tolist()
			mdata.pixel_spacing = target_spacing_xyz[:2].astype(np.float32).tolist()
			mdata.slice_thickness = float(target_spacing_xyz[2])
			mdata.slice_distance = float(target_spacing_xyz[2])
			mdata.slice_location = float(layer_idx) * float(target_spacing_xyz[2])
			metadata.append(mdata)
		return metadata

	def _valid_voxel_mask(self, points_voxel, volume_shape):
		"""Return a mask of sampling points that fall inside the source voxel domain."""
		points_voxel = np.asarray(points_voxel, dtype=np.float32)
		columns = int(volume_shape[2])
		rows = int(volume_shape[1])
		layers = int(volume_shape[0])
		return (
			(points_voxel[:, :, 0] >= 0.0) & (points_voxel[:, :, 0] <= float(columns - 1)) &
			(points_voxel[:, :, 1] >= 0.0) & (points_voxel[:, :, 1] <= float(rows - 1)) &
			(points_voxel[:, :, 2] >= 0.0) & (points_voxel[:, :, 2] <= float(layers - 1))
		)

	def _transform_world_points(self, point_world, transform_matrix):
		"""Apply a 4x4 homogeneous transform to one world point or a 3xN point matrix."""
		point_world = np.asarray(point_world, dtype=np.float32)
		transform_matrix = np.asarray(transform_matrix, dtype=np.float32)
		if transform_matrix.shape != (4, 4):
			raise ValueError("transform_matrix must be a 4x4 homogeneous matrix.")

		if point_world.ndim == 1:
			point_h = np.ones(4, dtype=np.float32)
			point_h[:3] = point_world
			return (transform_matrix @ point_h)[:3]

		points_h = np.vstack((
			point_world,
			np.ones((1, point_world.shape[1]), dtype=np.float32),
		))
		return (transform_matrix @ points_h)[:3, :]

	def resample_to_grid(self, target_origin_world, target_basis_world, target_spacing_xyz, target_shape_zyx,
	                     interpolation="linear", fill_value=None, label_suffix="resampled",
	                     source_world_from_target_world=None, return_valid_mask=False):
		"""Resample the volume into a new world-space voxel grid and return a new Volumetric object."""
		volume = self._volume_array().astype(np.float32, copy=False)
		if volume.ndim != 3:
			raise ValueError("Volumetric data must be a 3D array.")

		target_origin_world = np.asarray(target_origin_world, dtype=np.float32)
		if target_origin_world.shape != (3,):
			raise ValueError("target_origin_world must be a 3-element world coordinate.")

		target_basis_world = self._normalize_basis_world(target_basis_world)
		target_spacing_xyz = np.asarray(target_spacing_xyz, dtype=np.float32)
		if target_spacing_xyz.shape != (3,):
			raise ValueError("target_spacing_xyz must be a 3-element spacing vector.")
		if np.any(target_spacing_xyz <= 0.0):
			raise ValueError("target_spacing_xyz must contain only positive values.")

		layers, rows, columns = [int(v) for v in target_shape_zyx]
		if layers <= 0 or rows <= 0 or columns <= 0:
			raise ValueError("target_shape_zyx must contain positive dimensions.")

		interpolation = str(interpolation).lower()
		order_by_interpolation = {
			"nearest": 0,
			"linear": 1,
			"cubic": 3,
		}
		if interpolation not in order_by_interpolation:
			raise ValueError("interpolation must be one of: nearest, linear, cubic.")

		if fill_value is None:
			fill_value = float(self.m_min)
		else:
			fill_value = float(fill_value)

		if source_world_from_target_world is None:
			source_world_from_target_world = np.eye(4, dtype=np.float32)
		else:
			source_world_from_target_world = np.asarray(source_world_from_target_world, dtype=np.float32)
			if source_world_from_target_world.shape != (4, 4):
				raise ValueError("source_world_from_target_world must be a 4x4 homogeneous matrix.")

		x_coords = np.arange(columns, dtype=np.float32)
		y_coords = np.arange(rows, dtype=np.float32)
		grid_x, grid_y = np.meshgrid(x_coords, y_coords)
		output_volume = np.empty((layers, rows, columns), dtype=np.float32)
		valid_volume = np.zeros((layers, rows, columns), dtype=bool) if return_valid_mask else None

		for layer_idx in range(layers):
			slice_origin_world = target_origin_world + target_basis_world[:, 2] * (float(layer_idx) * target_spacing_xyz[2])
			points_world = (
				slice_origin_world[None, None, :]
				+ (grid_x[:, :, None] * target_spacing_xyz[0]) * target_basis_world[:, 0][None, None, :]
				+ (grid_y[:, :, None] * target_spacing_xyz[1]) * target_basis_world[:, 1][None, None, :]
			)
			source_points_world = self._transform_world_points(
				points_world.reshape(-1, 3).T,
				source_world_from_target_world,
			)
			points_voxel = self.world_to_voxel(source_points_world).T.reshape(rows, columns, 3)
			if return_valid_mask:
				valid_volume[layer_idx] = self._valid_voxel_mask(points_voxel, volume.shape)
			sampled_slice = map_coordinates(
				volume,
				[
					points_voxel[:, :, 2].ravel(),
					points_voxel[:, :, 1].ravel(),
					points_voxel[:, :, 0].ravel(),
				],
				order=order_by_interpolation[interpolation],
				mode='constant',
				cval=fill_value,
			).reshape(rows, columns)
			output_volume[layer_idx] = sampled_slice.astype(np.float32, copy=False)

		resampled = Volumetric()
		resampled.label = f"{self.label}_{label_suffix}" if label_suffix else self.label
		resampled.description = self.description
		resampled.m_volume = output_volume
		resampled.shape = output_volume.shape
		resampled.metadata = self._build_metadata_for_grid(
			target_origin_world=target_origin_world,
			target_basis_world=target_basis_world,
			target_spacing_xyz=target_spacing_xyz,
			target_shape_zyx=output_volume.shape,
		)
		resampled.m_dicom_files = list(self.m_dicom_files)
		resampled.adjustMinMax()
		if return_valid_mask:
			return resampled, valid_volume
		return resampled

	def resample_like(self, other_volumetric, interpolation="linear", fill_value=None, label_suffix="resampled_like"):
		"""Resample this volume into the world-space voxel grid used by another volumetric object."""
		if not isinstance(other_volumetric, Volumetric):
			raise TypeError("other_volumetric must be an instance of Volumetric.")

		target_origin_world, target_basis_world, target_spacing_xyz = other_volumetric.get_volume_geometry()
		return self.resample_to_grid(
			target_origin_world=target_origin_world,
			target_basis_world=target_basis_world,
			target_spacing_xyz=target_spacing_xyz,
			target_shape_zyx=other_volumetric.shape,
			interpolation=interpolation,
			fill_value=fill_value,
			label_suffix=label_suffix,
		)

	def resample_like_global(self, other_volumetric, source_global_transform, target_global_transform,
	                         interpolation="linear", fill_value=None, label_suffix="matched_global"):
		"""Resample this volume into another volume grid while respecting both hierarchy transforms."""
		if not isinstance(other_volumetric, Volumetric):
			raise TypeError("other_volumetric must be an instance of Volumetric.")

		source_global_transform = np.asarray(source_global_transform, dtype=np.float32)
		target_global_transform = np.asarray(target_global_transform, dtype=np.float32)
		if source_global_transform.shape != (4, 4):
			raise ValueError("source_global_transform must be a 4x4 homogeneous matrix.")
		if target_global_transform.shape != (4, 4):
			raise ValueError("target_global_transform must be a 4x4 homogeneous matrix.")

		source_world_from_target_world = np.linalg.inv(source_global_transform) @ target_global_transform
		target_origin_world, target_basis_world, target_spacing_xyz = other_volumetric.get_volume_geometry()
		return self.resample_to_grid(
			target_origin_world=target_origin_world,
			target_basis_world=target_basis_world,
			target_spacing_xyz=target_spacing_xyz,
			target_shape_zyx=other_volumetric.shape,
			interpolation=interpolation,
			fill_value=fill_value,
			label_suffix=label_suffix,
			source_world_from_target_world=source_world_from_target_world,
		)

	@staticmethod
	def _volume_corners_world(volumetric, global_transform=None):
		"""Return the eight world-space corners of a volumetric bounding box."""
		if not isinstance(volumetric, Volumetric):
			raise TypeError("volumetric must be an instance of Volumetric.")

		origin_world, basis_world, spacing_xyz = volumetric.get_volume_geometry()
		global_transform = np.eye(4, dtype=np.float32) if global_transform is None else np.asarray(global_transform, dtype=np.float32)
		if global_transform.shape != (4, 4):
			raise ValueError("global_transform must be a 4x4 homogeneous matrix.")

		shape_xyz = np.array([volumetric.shape[2], volumetric.shape[1], volumetric.shape[0]], dtype=np.float32)
		max_indices_xyz = np.maximum(shape_xyz - 1.0, 0.0)
		local_corners = []
		for x_idx in (0.0, max_indices_xyz[0]):
			for y_idx in (0.0, max_indices_xyz[1]):
				for z_idx in (0.0, max_indices_xyz[2]):
					local_corner = origin_world + basis_world @ np.array([
						x_idx * spacing_xyz[0],
						y_idx * spacing_xyz[1],
						z_idx * spacing_xyz[2],
					], dtype=np.float32)
					local_corners.append(local_corner)

		local_corners = np.asarray(local_corners, dtype=np.float32)
		corners_h = np.column_stack((local_corners, np.ones(local_corners.shape[0], dtype=np.float32)))
		return (global_transform @ corners_h.T).T[:, :3]

	@classmethod
	def compute_common_grid_global(cls, source_volumes, source_global_transforms, spacing_policy="reference",
	                               reference_volume=None, reference_global_transform=None, manual_spacing_xyz=None,
	                               basis_policy="reference", align_origin=True):
		"""Compute one world-space voxel grid that can hold multiple transformed volumes."""
		if not source_volumes:
			raise ValueError("source_volumes must contain at least one volumetric object.")
		if len(source_volumes) != len(source_global_transforms):
			raise ValueError("source_volumes and source_global_transforms must have the same length.")

		normalized_policy = str(spacing_policy).lower()
		if normalized_policy not in ("reference", "finest", "coarsest", "manual"):
			raise ValueError("spacing_policy must be one of: reference, finest, coarsest, manual.")

		normalized_basis_policy = str(basis_policy).lower()
		if normalized_basis_policy not in ("reference", "global_xyz"):
			raise ValueError("basis_policy must be one of: reference, global_xyz.")

		if normalized_policy == "reference" or normalized_basis_policy == "reference":
			if reference_volume is None:
				raise ValueError("reference_volume is required for reference-based grid policies.")
			if not isinstance(reference_volume, Volumetric):
				raise TypeError("reference_volume must be an instance of Volumetric.")
			if reference_global_transform is None:
				raise ValueError("reference_global_transform is required for reference-based grid policies.")
			reference_global_transform = np.asarray(reference_global_transform, dtype=np.float32)
			if reference_global_transform.shape != (4, 4):
				raise ValueError("reference_global_transform must be a 4x4 homogeneous matrix.")

		if normalized_basis_policy == "reference":
			reference_origin_world, reference_basis_world, reference_spacing_xyz = reference_volume.get_volume_geometry()
			target_basis_world = reference_global_transform[:3, :3] @ reference_basis_world
			target_basis_world = source_volumes[0]._normalize_basis_world(target_basis_world)
		else:
			target_basis_world = np.eye(3, dtype=np.float32)
			reference_origin_world = None
			reference_spacing_xyz = None

		if normalized_policy == "manual":
			if manual_spacing_xyz is None:
				raise ValueError("manual_spacing_xyz is required when spacing_policy='manual'.")
			target_spacing_xyz = np.asarray(manual_spacing_xyz, dtype=np.float32)
		elif normalized_policy == "reference":
			target_spacing_xyz = np.asarray(reference_spacing_xyz, dtype=np.float32)
		else:
			spacing_candidates = []
			for source_vol, source_global_transform in zip(source_volumes, source_global_transforms):
				if not isinstance(source_vol, Volumetric):
					raise TypeError("Every source volume must be an instance of Volumetric.")
				_source_origin, source_basis_world, source_spacing_xyz = source_vol.get_volume_geometry()
				source_global_transform = np.asarray(source_global_transform, dtype=np.float32)
				world_steps = np.column_stack([
					source_global_transform[:3, :3] @ (source_basis_world[:, axis_idx] * source_spacing_xyz[axis_idx])
					for axis_idx in range(3)
				])
				spacing_candidates.extend(np.linalg.norm(world_steps, axis=0).astype(np.float32).tolist())

			picker = np.min if normalized_policy == "finest" else np.max
			iso_spacing = float(picker(np.asarray(spacing_candidates, dtype=np.float32)))
			target_spacing_xyz = np.array([iso_spacing, iso_spacing, iso_spacing], dtype=np.float32)

		if target_spacing_xyz.shape != (3,) or np.any(target_spacing_xyz <= 0.0):
			raise ValueError("Resolved target spacing must be a positive 3-element vector.")

		projection_mins = []
		projection_maxs = []
		for source_vol, source_global_transform in zip(source_volumes, source_global_transforms):
			corners_world = cls._volume_corners_world(source_vol, global_transform=source_global_transform)
			projected = corners_world @ target_basis_world
			projection_mins.append(projected.min(axis=0))
			projection_maxs.append(projected.max(axis=0))

		global_min_proj = np.min(np.stack(projection_mins, axis=0), axis=0)
		global_max_proj = np.max(np.stack(projection_maxs, axis=0), axis=0)

		if normalized_basis_policy == "reference" and align_origin:
			reference_origin_global = (reference_global_transform @ np.array([*reference_origin_world, 1.0], dtype=np.float32))[:3]
			reference_origin_proj = reference_origin_global @ target_basis_world
			start_indices = np.floor((global_min_proj - reference_origin_proj) / target_spacing_xyz)
			target_origin_proj = reference_origin_proj + start_indices * target_spacing_xyz
		elif align_origin:
			target_origin_proj = np.floor(global_min_proj / target_spacing_xyz) * target_spacing_xyz
		else:
			target_origin_proj = global_min_proj

		target_extent_proj = np.maximum(global_max_proj - target_origin_proj, 0.0)
		target_shape_xyz = np.maximum(1, np.ceil(target_extent_proj / target_spacing_xyz).astype(np.int32) + 1)
		target_origin_world = target_basis_world @ target_origin_proj.astype(np.float32)
		target_shape_zyx = (int(target_shape_xyz[2]), int(target_shape_xyz[1]), int(target_shape_xyz[0]))
		return target_origin_world.astype(np.float32), target_basis_world.astype(np.float32), target_spacing_xyz.astype(np.float32), target_shape_zyx

	@classmethod
	def merge_to_common_grid_global(cls, source_volumes, source_global_transforms, spacing_policy="reference",
	                                reference_volume=None, reference_global_transform=None, manual_spacing_xyz=None,
	                                basis_policy="reference", align_origin=True, interpolation="linear",
	                                merge_mode="max", fill_value=None, label="merged_common"):
		"""Compute a common world-space grid for multiple volumes and merge them into one result."""
		target_origin_world, target_basis_world, target_spacing_xyz, target_shape_zyx = cls.compute_common_grid_global(
			source_volumes=source_volumes,
			source_global_transforms=source_global_transforms,
			spacing_policy=spacing_policy,
			reference_volume=reference_volume,
			reference_global_transform=reference_global_transform,
			manual_spacing_xyz=manual_spacing_xyz,
			basis_policy=basis_policy,
			align_origin=align_origin,
		)
		return cls.merge_to_grid_global(
			source_volumes=source_volumes,
			source_global_transforms=source_global_transforms,
			target_origin_world=target_origin_world,
			target_basis_world=target_basis_world,
			target_spacing_xyz=target_spacing_xyz,
			target_shape_zyx=target_shape_zyx,
			interpolation=interpolation,
			merge_mode=merge_mode,
			fill_value=fill_value,
			label=label,
		)

	@staticmethod
	def _merge_resampled_arrays(sampled_arrays, valid_masks, merge_mode="max", fill_value=0.0):
		"""Merge arrays that already live on the same voxel grid using the selected conflict policy."""
		merge_mode = str(merge_mode).lower()
		if not sampled_arrays:
			raise ValueError("sampled_arrays must contain at least one resampled volume.")
		if len(sampled_arrays) != len(valid_masks):
			raise ValueError("sampled_arrays and valid_masks must have the same length.")

		stack = np.stack([np.asarray(arr, dtype=np.float32) for arr in sampled_arrays], axis=0)
		mask_stack = np.stack([np.asarray(mask, dtype=bool) for mask in valid_masks], axis=0)
		fill_value = float(fill_value)

		if merge_mode == "overwrite":
			result = np.full(stack.shape[1:], fill_value, dtype=np.float32)
			for idx in range(stack.shape[0]):
				current_mask = mask_stack[idx]
				result[current_mask] = stack[idx][current_mask]
			return result

		if merge_mode == "first_non_empty":
			result = np.full(stack.shape[1:], fill_value, dtype=np.float32)
			filled_mask = np.zeros(stack.shape[1:], dtype=bool)
			for idx in range(stack.shape[0]):
				current_mask = mask_stack[idx] & (~filled_mask)
				result[current_mask] = stack[idx][current_mask]
				filled_mask |= current_mask
			return result

		masked_stack = np.where(mask_stack, stack, np.nan).astype(np.float32, copy=False)
		with np.errstate(invalid='ignore'):
			if merge_mode == "max":
				result = np.nanmax(masked_stack, axis=0)
			elif merge_mode == "min":
				result = np.nanmin(masked_stack, axis=0)
			elif merge_mode == "sum":
				result = np.nansum(masked_stack, axis=0)
				result[np.sum(mask_stack, axis=0) == 0] = np.nan
			elif merge_mode == "mean":
				result = np.nanmean(masked_stack, axis=0)
			else:
				raise ValueError("merge_mode must be one of: max, min, mean, sum, overwrite, first_non_empty.")

		return np.nan_to_num(result, nan=fill_value).astype(np.float32, copy=False)

	@classmethod
	def merge_to_grid_global(cls, source_volumes, source_global_transforms, target_origin_world, target_basis_world,
	                         target_spacing_xyz, target_shape_zyx, interpolation="linear", merge_mode="max",
	                         fill_value=None, label="merged"):
		"""Resample multiple volumes into one world-space grid and merge them into a new Volumetric."""
		if not source_volumes:
			raise ValueError("source_volumes must contain at least one volumetric object.")
		if len(source_volumes) != len(source_global_transforms):
			raise ValueError("source_volumes and source_global_transforms must have the same length.")

		resampled_volumes = []
		valid_masks = []
		resolved_fill_value = float(source_volumes[0].m_min if fill_value is None else fill_value)

		for source_vol, source_global_transform in zip(source_volumes, source_global_transforms):
			if not isinstance(source_vol, Volumetric):
				raise TypeError("Every source volume must be an instance of Volumetric.")
			resampled, valid_mask = source_vol.resample_to_grid(
				target_origin_world=target_origin_world,
				target_basis_world=target_basis_world,
				target_spacing_xyz=target_spacing_xyz,
				target_shape_zyx=target_shape_zyx,
				interpolation=interpolation,
				fill_value=resolved_fill_value,
				label_suffix="merge_tmp",
				source_world_from_target_world=np.linalg.inv(np.asarray(source_global_transform, dtype=np.float32)),
				return_valid_mask=True,
			)
			resampled_volumes.append(np.asarray(resampled.m_volume, dtype=np.float32))
			valid_masks.append(valid_mask)

		merged_volume = cls._merge_resampled_arrays(
			sampled_arrays=resampled_volumes,
			valid_masks=valid_masks,
			merge_mode=merge_mode,
			fill_value=resolved_fill_value,
		)

		merged = Volumetric()
		merged.label = label
		merged.description = "Merged volumetric"
		merged.m_volume = merged_volume
		merged.shape = merged_volume.shape
		merged.metadata = source_volumes[0]._build_metadata_for_grid(
			target_origin_world=np.asarray(target_origin_world, dtype=np.float32),
			target_basis_world=np.asarray(target_basis_world, dtype=np.float32),
			target_spacing_xyz=np.asarray(target_spacing_xyz, dtype=np.float32),
			target_shape_zyx=merged_volume.shape,
		)
		merged.adjustMinMax()
		return merged

	@classmethod
	def merge_like_global(cls, source_volumes, source_global_transforms, reference_volume, reference_global_transform,
	                      interpolation="linear", merge_mode="max", fill_value=None, label=None):
		"""Merge multiple volumes directly into the voxel grid of a reference volume."""
		if not isinstance(reference_volume, Volumetric):
			raise TypeError("reference_volume must be an instance of Volumetric.")

		target_origin_world, target_basis_world, target_spacing_xyz = reference_volume.get_volume_geometry()
		if label is None:
			label = f"merged_like_{reference_volume.label}"
		if len(source_volumes) != len(source_global_transforms):
			raise ValueError("source_volumes and source_global_transforms must have the same length.")

		resampled_volumes = []
		valid_masks = []
		reference_global_transform = np.asarray(reference_global_transform, dtype=np.float32)
		resolved_fill_value = float(source_volumes[0].m_min if fill_value is None else fill_value)

		for source_vol, source_global_transform in zip(source_volumes, source_global_transforms):
			if not isinstance(source_vol, Volumetric):
				raise TypeError("Every source volume must be an instance of Volumetric.")
			source_global_transform = np.asarray(source_global_transform, dtype=np.float32)
			resampled, valid_mask = source_vol.resample_to_grid(
				target_origin_world=target_origin_world,
				target_basis_world=target_basis_world,
				target_spacing_xyz=target_spacing_xyz,
				target_shape_zyx=reference_volume.shape,
				interpolation=interpolation,
				fill_value=resolved_fill_value,
				label_suffix="merge_tmp",
				source_world_from_target_world=np.linalg.inv(source_global_transform) @ reference_global_transform,
				return_valid_mask=True,
			)
			resampled_volumes.append(np.asarray(resampled.m_volume, dtype=np.float32))
			valid_masks.append(valid_mask)

		merged_volume = cls._merge_resampled_arrays(
			sampled_arrays=resampled_volumes,
			valid_masks=valid_masks,
			merge_mode=merge_mode,
			fill_value=resolved_fill_value,
		)

		merged = Volumetric()
		merged.label = label
		merged.description = "Merged volumetric"
		merged.m_volume = merged_volume
		merged.shape = merged_volume.shape
		merged.metadata = reference_volume._build_metadata_for_grid(
			target_origin_world=target_origin_world,
			target_basis_world=target_basis_world,
			target_spacing_xyz=target_spacing_xyz,
			target_shape_zyx=merged_volume.shape,
		)
		merged.adjustMinMax()
		return merged

	def get_oblique_slice_array(self, center_xyz, yaw_degrees=0.0, pitch_degrees=0.0,
	                            yaw_axis="Y", pitch_axis="X", output_size=None,
	                            slab_thickness_mm=0.0, slab_samples=1, slab_mode="mean",
	                            use_display_window=False, xray_gain=0.03):
		"""Sample an oblique slice around the given voxel-space center in world coordinates."""

		volume = self._volume_array().astype(np.float32, copy=False)
		slab_mode = str(slab_mode).lower()
		if slab_mode == "xray":
			volume = self._map_to_xray_attenuation(volume, use_display_window=use_display_window)
		if volume.ndim != 3:
			raise ValueError("Volumetric data must be a 3D array.")

		layers, rows, columns = volume.shape
		origin, basis, spacing = self.get_volume_geometry()
		volume_extent = basis @ np.array([
			spacing[0] * max(columns - 1, 1),
			spacing[1] * max(rows - 1, 1),
			spacing[2] * max(layers - 1, 1),
		], dtype=np.float32)
		world_diagonal = float(np.linalg.norm(volume_extent))
		in_plane_step = max(1e-6, float(np.min(spacing)))

		if output_size is None:
			side = int(np.ceil(world_diagonal / in_plane_step))
			width = max(32, side)
			height = max(32, side)
		else:
			width, height = output_size
			width = max(8, int(width))
			height = max(8, int(height))

		base_right = basis[:, 0]
		base_up = basis[:, 1]
		base_normal = basis[:, 2]
		right_world, up_world, _normal_world = self._oblique_basis_world(
			base_right=base_right,
			base_up=base_up,
			base_normal=base_normal,
			yaw_degrees=yaw_degrees,
			pitch_degrees=pitch_degrees,
			yaw_axis=yaw_axis,
			pitch_axis=pitch_axis,
		)

		center_world = self.voxel_to_world(center_xyz)
		x_coords = np.linspace(-(width - 1) / 2.0, (width - 1) / 2.0, width, dtype=np.float32)
		y_coords = np.linspace(-(height - 1) / 2.0, (height - 1) / 2.0, height, dtype=np.float32)
		grid_x, grid_y = np.meshgrid(x_coords, y_coords)

		base_points_world = (
			center_world[None, None, :]
			+ (grid_x[:, :, None] * in_plane_step) * right_world[None, None, :]
			+ (grid_y[:, :, None] * in_plane_step) * up_world[None, None, :]
		)
		offsets = self._slab_offsets(slab_thickness_mm=slab_thickness_mm, slab_samples=slab_samples)
		step_mm = float(abs(offsets[1] - offsets[0])) if len(offsets) > 1 else in_plane_step
		sampled_images = []

		for offset in offsets:
			points_world = base_points_world + offset * _normal_world[None, None, :]
			points_voxel = self.world_to_voxel(points_world.reshape(-1, 3).T).T.reshape(height, width, 3)
			sampled = map_coordinates(
				volume,
				[
					points_voxel[:, :, 2].ravel(),
					points_voxel[:, :, 1].ravel(),
					points_voxel[:, :, 0].ravel(),
				],
				order=1,
				mode='constant',
				cval=0.0 if slab_mode == "xray" else float(self.m_min),
			).reshape(height, width)
			sampled_images.append(sampled.astype(np.float32, copy=False))

		return self._reduce_slab_samples(
			np.stack(sampled_images, axis=0),
			slab_mode=slab_mode,
			step_mm=step_mm,
			xray_gain=xray_gain,
		).astype(np.float32, copy=False)

	def get_oblique_preview_qimage(self, center_xyz, yaw_degrees=0.0, pitch_degrees=0.0,
	                               yaw_axis="Y", pitch_axis="X",
	                               use_display_window=False, invert=False, output_size=None,
	                               slab_thickness_mm=0.0, slab_samples=1, slab_mode="mean",
	                               xray_gain=0.03, xray_gamma=1.0):
		"""Build a QImage preview for an oblique slice around the selected center."""
		image = self.get_oblique_slice_array(
			center_xyz=center_xyz,
			yaw_degrees=yaw_degrees,
			pitch_degrees=pitch_degrees,
			yaw_axis=yaw_axis,
			pitch_axis=pitch_axis,
			output_size=output_size,
			slab_thickness_mm=slab_thickness_mm,
			slab_samples=slab_samples,
			slab_mode=slab_mode,
			use_display_window=use_display_window,
			xray_gain=xray_gain,
		)
		buffer = self.normalize_slice_to_uint8(
			image=image,
			use_display_window=(use_display_window and slab_mode != "xray"),
			invert=invert,
			fixed_range=self._xray_display_range(image) if slab_mode == "xray" else None,
			gamma=xray_gamma if slab_mode == "xray" else 1.0,
		)
		height, width = buffer.shape
		qimage = QImage(buffer.data, width, height, buffer.strides[0], QImage.Format_Grayscale8)
		return qimage.copy()

	def on_mouse_move(self, dx, dy):
		self.m_minDisplWin = self.m_minDisplWin + dx
		self.m_minDisplWin = self.m_minDisplWin + dy
		if self.m_minDisplWin < self.m_min:
			self.m_minDisplWin = self.m_min

		self.m_maxDisplWin = self.m_maxDisplWin - dx
		self.m_maxDisplWin = self.m_maxDisplWin + dy
		if self.m_maxDisplWin > self.m_max:
			self.m_maxDisplWin = self.m_max

		AP.updateProperties()
		AP.updateAllViews()
		#print(f"dx={dx}, dy={dy}")

	def remove_shader_program(self):
		glDeleteProgram(self.shader_program)
		self.shader_program = None

	def remove_splat_shader(self):
		if self.splat_shader is not None:
			glDeleteProgram(self.splat_shader)
			self.splat_shader = None
		if self.splat_hq_shader is not None:
			glDeleteProgram(self.splat_hq_shader)
			self.splat_hq_shader = None

	def _compile_splat_shader(self):
		from .shaders import create_program
		try:
			self.splat_shader = create_program(
				vertex_shader_name='volumetricSplat.vert',
				fragment_shader_name='volumetricSplat.frag'
			)
			print('[Volumetric] splat_shader OK', flush=True)
		except Exception as e:
			print(f'[Volumetric] BLAD kompilacji splat_shader: {e}', flush=True)
			self.splat_shader = None

	def _compile_splat_hq_shader(self):
		from .shaders import create_program
		try:
			self.splat_hq_shader = create_program(
				vertex_shader_name='volumetricSplatHQ.vert',
				fragment_shader_name='volumetricSplat.frag'
			)
			print('[Volumetric] splat_hq_shader OK', flush=True)
		except Exception as e:
			print(f'[Volumetric] BLAD kompilacji splat_hq_shader: {e}', flush=True)
			self.splat_hq_shader = None

	def _render_splat(self):
		"""Renderowanie wokseli jako Gaussian splaty (analogicznie do SphereGrid)."""
		if self.m_splat_hq_sort and not self.m_splat_transparent:
			self._render_splat_hq()
			return

		if self.splat_shader is None:
			self._compile_splat_shader()
		if self.splat_shader is None:
			return

		glEnable(GL_PROGRAM_POINT_SIZE)

		glUseProgram(self.splat_shader)

		if self.splat_vbo is None:
			self.splat_vbo = glGenBuffers(1)
		glBindBuffer(GL_ARRAY_BUFFER, self.splat_vbo)
		glEnableVertexAttribArray(0)
		glVertexAttribPointer(0, 1, GL_FLOAT, GL_FALSE, 0, None)

		modelview = np.array(glGetFloatv(GL_MODELVIEW_MATRIX), dtype=np.float32)
		glUniformMatrix4fv(glGetUniformLocation(self.splat_shader, "modelviewMatrix"),
		                   1, GL_FALSE, modelview)

		projection = np.array(glGetFloatv(GL_PROJECTION_MATRIX), dtype=np.float32)
		glUniformMatrix4fv(glGetUniformLocation(self.splat_shader, "projectionMatrix"),
		                   1, GL_FALSE, projection)

		glUniform1f(glGetUniformLocation(self.splat_shader, "minColor"), self.m_minDisplWin)
		glUniform1f(glGetUniformLocation(self.splat_shader, "maxColor"), self.m_maxDisplWin)

		glUniform3fv(glGetUniformLocation(self.splat_shader, "f"),       7, self.m_filters)
		glUniform3fv(glGetUniformLocation(self.splat_shader, "fcolors"), 7, self.m_fcolors)

		viewport = glGetIntegerv(GL_VIEWPORT)
		glUniform1f(glGetUniformLocation(self.splat_shader, "u_viewport_h"), float(viewport[3]))
		glUniform1f(glGetUniformLocation(self.splat_shader, "u_focal_y"),    float(projection[1, 1]))
		glUniform1f(glGetUniformLocation(self.splat_shader, "u_splat_scale"), float(self.m_splat_scale))
		glUniform1f(glGetUniformLocation(self.splat_shader, "u_depth_cutoff"), float(self.m_splat_depth_cutoff))
		glUniform1i(glGetUniformLocation(self.splat_shader, "u_depth_prepass"), 0)
		glUniform3fv(glGetUniformLocation(self.splat_shader, "u_tint"), 1,
		             np.array(self.m_splat_tint, dtype=np.float32))

		if not self.m_fastDraw and not AP.mouse_key_pressed:
			factor = 1
		elif len(self.m_volume) < 1536:
			factor = 4
		else:
			factor = 8

		glUniform1i(glGetUniformLocation(self.splat_shader, "factor"), factor)

		first_slice  = factor * int(self.m_minSlice  / factor)
		first_row    = factor * int(self.m_minRow    / factor)
		first_column = factor * int(self.m_minColumn / factor)

		subvolume = [
			s[first_row:self.m_maxRow+1:factor, first_column:self.m_maxColumn+1:factor]
			for s in self.m_volume[first_slice:self.m_maxSlice+1:factor]
		]
		small_shape = (len(subvolume), subvolume[0].shape[0], subvolume[0].shape[1])

		glUniform1i(glGetUniformLocation(self.splat_shader, "sizeX"), small_shape[2])
		glUniform1i(glGetUniformLocation(self.splat_shader, "sizeY"), small_shape[1])

		# Sortowanie warstw: rysuj od tyłu do przodu względem kamery.
		# M[2][2] to składowa Z kierunku +Z świata w przestrzeni oka.
		# Przy numpy bez transpozycji: numpy[2][2] == M[2][2] (element diagonalny).
		# M[2][2] >= 0 → kamera po stronie +Z → mniejsze Z jest dalej → kolejność rosnąca
		# M[2][2] <  0 → kamera po stronie -Z → większe Z jest dalej → kolejność malejąca
		slice_depths = []
		for idx_in_subvolume in range(small_shape[0]):
			true_index = first_slice + idx_in_subvolume * factor
			metadata = self.metadata[true_index]
			image_position = np.array([
				metadata.image_position_patient[0] + metadata.pixel_spacing[0] * float(first_column),
				metadata.image_position_patient[1] + metadata.pixel_spacing[1] * float(first_row),
				metadata.image_position_patient[2]
			], dtype=np.float32)
			voxel_size = np.array([
				metadata.pixel_spacing[0],
				metadata.pixel_spacing[1],
				metadata.slice_thickness
			], dtype=np.float32)
			slice_center = image_position + voxel_size * np.array([
				0.5 * max(small_shape[2] - 1, 0),
				0.5 * max(small_shape[1] - 1, 0),
				0.0
			], dtype=np.float32)
			eye_center = modelview @ np.array([slice_center[0], slice_center[1], slice_center[2], 1.0], dtype=np.float32)
			slice_depths.append((float(eye_center[2]), idx_in_subvolume))
		slice_indices = [idx for _, idx in sorted(slice_depths)]

		def _draw_sorted_slices():
			for idx_in_subvolume in slice_indices:
				true_index = first_slice + idx_in_subvolume * factor

				colors = np.array(subvolume[idx_in_subvolume], dtype=np.float32).flatten()
				glBufferData(GL_ARRAY_BUFFER, colors.nbytes, colors, GL_STATIC_DRAW)

				metadata = self.metadata[true_index]
				imagePosition = [
					metadata.image_position_patient[0] + metadata.pixel_spacing[0] * float(first_column),
					metadata.image_position_patient[1] + metadata.pixel_spacing[1] * float(first_row),
					metadata.image_position_patient[2]
				]
				voxel_size = [
					metadata.pixel_spacing[0],
					metadata.pixel_spacing[1],
					metadata.slice_thickness
				]
				glUniform3fv(glGetUniformLocation(self.splat_shader, "imagePosition"), 1, imagePosition)
				glUniform3fv(glGetUniformLocation(self.splat_shader, "voxelSize"),      1, voxel_size)

				glDrawArrays(GL_POINTS, 0, colors.shape[0])

		if self.m_splat_depth_prepass:
			glDisable(GL_BLEND)
			glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE)
			glDepthMask(GL_TRUE)
			glDepthFunc(GL_LEQUAL)
			glUniform1i(glGetUniformLocation(self.splat_shader, "u_depth_prepass"), 1)
			_draw_sorted_slices()
			glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)

		glEnable(GL_BLEND)
		if self.m_splat_additive:
			glBlendFunc(GL_SRC_ALPHA, GL_ONE)
		else:
			glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
		glDepthMask(GL_FALSE)
		glDepthFunc(GL_LEQUAL)
		glUniform1i(glGetUniformLocation(self.splat_shader, "u_depth_prepass"), 0)
		_draw_sorted_slices()

		glBindBuffer(GL_ARRAY_BUFFER, 0)
		glUseProgram(0)
		glDepthFunc(GL_LEQUAL)
		glDepthMask(GL_TRUE)
		glDisable(GL_BLEND)
		glDisable(GL_PROGRAM_POINT_SIZE)

	def _build_hq_splat_points(self, factor, modelview):
		first_slice  = factor * int(self.m_minSlice  / factor)
		first_row    = factor * int(self.m_minRow    / factor)
		first_column = factor * int(self.m_minColumn / factor)

		point_blocks = []
		for true_index in range(first_slice, self.m_maxSlice + 1, factor):
			slice_2d = np.asarray(
				self.m_volume[true_index][first_row:self.m_maxRow+1:factor, first_column:self.m_maxColumn+1:factor],
				dtype=np.float32
			)
			if slice_2d.size == 0:
				continue

			mask = (slice_2d >= self.m_minDisplWin) & (slice_2d <= self.m_maxDisplWin)
			if not np.any(mask):
				continue

			metadata = self.metadata[true_index]
			row_idx, col_idx = np.nonzero(mask)
			values = slice_2d[mask]

			x = metadata.image_position_patient[0] + metadata.pixel_spacing[0] * (first_column + col_idx * factor)
			y = metadata.image_position_patient[1] + metadata.pixel_spacing[1] * (first_row + row_idx * factor)
			z = np.full_like(values, metadata.image_position_patient[2], dtype=np.float32)

			points = np.empty((values.shape[0], 4), dtype=np.float32)
			points[:, 0] = x.astype(np.float32)
			points[:, 1] = y.astype(np.float32)
			points[:, 2] = z
			points[:, 3] = values
			point_blocks.append(points)

		if not point_blocks:
			return np.empty((0, 4), dtype=np.float32)

		points = np.vstack(point_blocks)
		ones = np.ones((points.shape[0], 1), dtype=np.float32)
		eye = np.hstack((points[:, :3], ones)) @ modelview.T
		order = np.argsort(-eye[:, 2], kind='stable')
		return points[order]

	def _render_splat_hq(self):
		import ctypes

		if self.splat_hq_shader is None:
			self._compile_splat_hq_shader()
		if self.splat_hq_shader is None:
			return

		modelview = np.array(glGetFloatv(GL_MODELVIEW_MATRIX), dtype=np.float32)
		projection = np.array(glGetFloatv(GL_PROJECTION_MATRIX), dtype=np.float32)

		if not self.m_fastDraw and not AP.mouse_key_pressed:
			factor = 1
		elif len(self.m_volume) < 1536:
			factor = 4
		else:
			factor = 8

		points = self._build_hq_splat_points(factor, modelview)
		if len(points) == 0:
			return

		if self.splat_hq_vbo is None:
			self.splat_hq_vbo = glGenBuffers(1)

		glEnable(GL_PROGRAM_POINT_SIZE)
		glEnable(GL_BLEND)
		if self.m_splat_additive:
			glBlendFunc(GL_SRC_ALPHA, GL_ONE)
		else:
			glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
		glDepthMask(GL_FALSE)
		glDepthFunc(GL_LEQUAL)

		glUseProgram(self.splat_hq_shader)

		glUniformMatrix4fv(glGetUniformLocation(self.splat_hq_shader, "modelviewMatrix"),
		                   1, GL_FALSE, modelview)
		glUniformMatrix4fv(glGetUniformLocation(self.splat_hq_shader, "projectionMatrix"),
		                   1, GL_FALSE, projection)
		glUniform1f(glGetUniformLocation(self.splat_hq_shader, "minColor"), self.m_minDisplWin)
		glUniform1f(glGetUniformLocation(self.splat_hq_shader, "maxColor"), self.m_maxDisplWin)
		glUniform3fv(glGetUniformLocation(self.splat_hq_shader, "f"), 7, self.m_filters)
		glUniform3fv(glGetUniformLocation(self.splat_hq_shader, "fcolors"), 7, self.m_fcolors)
		viewport = glGetIntegerv(GL_VIEWPORT)
		glUniform1f(glGetUniformLocation(self.splat_hq_shader, "u_viewport_h"), float(viewport[3]))
		glUniform1f(glGetUniformLocation(self.splat_hq_shader, "u_focal_y"), float(projection[1, 1]))
		px = float(self.metadata[0].pixel_spacing[0]) if self.metadata else 1.0
		py = float(self.metadata[0].pixel_spacing[1]) if self.metadata else 1.0
		pz = float(self.metadata[0].slice_thickness) if self.metadata else 1.0
		glUniform3f(glGetUniformLocation(self.splat_hq_shader, "u_voxel_size"), px * factor, py * factor, pz * factor)
		glUniform1f(glGetUniformLocation(self.splat_hq_shader, "u_splat_scale"), float(self.m_splat_scale))
		glUniform3fv(glGetUniformLocation(self.splat_hq_shader, "u_tint"), 1,
		             np.array(self.m_splat_tint, dtype=np.float32))
		glUniform1f(glGetUniformLocation(self.splat_hq_shader, "u_depth_cutoff"), float(self.m_splat_depth_cutoff))
		glUniform1i(glGetUniformLocation(self.splat_hq_shader, "u_depth_prepass"), 0)

		glBindBuffer(GL_ARRAY_BUFFER, self.splat_hq_vbo)
		glBufferData(GL_ARRAY_BUFFER, points.nbytes, points, GL_DYNAMIC_DRAW)
		stride = 4 * 4
		glEnableVertexAttribArray(0)
		glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
		glEnableVertexAttribArray(1)
		glVertexAttribPointer(1, 1, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(12))
		glDrawArrays(GL_POINTS, 0, points.shape[0])

		glDisableVertexAttribArray(0)
		glDisableVertexAttribArray(1)
		glBindBuffer(GL_ARRAY_BUFFER, 0)
		glUseProgram(0)
		glDepthMask(GL_TRUE)
		glDisable(GL_BLEND)
		glDisable(GL_PROGRAM_POINT_SIZE)

	def _compile_wboit_splat_shader(self):
		from .shaders import load_and_compile_shader
		try:
			vs = load_and_compile_shader('volumetricSplat.vert', GL_VERTEX_SHADER)
			fs = load_and_compile_shader('wboit_splat.frag',     GL_FRAGMENT_SHADER)
			prog = glCreateProgram()
			glAttachShader(prog, vs)
			glAttachShader(prog, fs)
			glLinkProgram(prog)
			if not glGetProgramiv(prog, GL_LINK_STATUS):
				print(glGetProgramInfoLog(prog))
				glDeleteProgram(prog)
				return
			glDeleteShader(vs)
			glDeleteShader(fs)
			self.wboit_splat_shader = prog
		except Exception as e:
			print(f'WBOIT splat shader error: {e}')

	def render_wboit(self, pass_idx):
		"""WBOIT rendering of gaussian splats (called by workspace in WBOIT passes)."""
		if not self.m_renderSplats:
			return
		if self.wboit_splat_shader is None:
			self._compile_wboit_splat_shader()
		if self.wboit_splat_shader is None:
			return

		glEnable(GL_PROGRAM_POINT_SIZE)
		glUseProgram(self.wboit_splat_shader)

		if self.splat_vbo is None:
			self.splat_vbo = glGenBuffers(1)
		glBindBuffer(GL_ARRAY_BUFFER, self.splat_vbo)
		glEnableVertexAttribArray(0)
		glVertexAttribPointer(0, 1, GL_FLOAT, GL_FALSE, 0, None)

		modelview  = np.array(glGetFloatv(GL_MODELVIEW_MATRIX),  dtype=np.float32)
		projection = np.array(glGetFloatv(GL_PROJECTION_MATRIX), dtype=np.float32)
		glUniformMatrix4fv(glGetUniformLocation(self.wboit_splat_shader, 'modelviewMatrix'),  1, GL_FALSE, modelview)
		glUniformMatrix4fv(glGetUniformLocation(self.wboit_splat_shader, 'projectionMatrix'), 1, GL_FALSE, projection)

		glUniform1f(glGetUniformLocation(self.wboit_splat_shader, 'minColor'), self.m_minDisplWin)
		glUniform1f(glGetUniformLocation(self.wboit_splat_shader, 'maxColor'), self.m_maxDisplWin)
		glUniform3fv(glGetUniformLocation(self.wboit_splat_shader, 'f'),       7, self.m_filters)
		glUniform3fv(glGetUniformLocation(self.wboit_splat_shader, 'fcolors'), 7, self.m_fcolors)

		viewport = glGetIntegerv(GL_VIEWPORT)
		glUniform1f(glGetUniformLocation(self.wboit_splat_shader, 'u_viewport_h'), float(viewport[3]))
		glUniform1f(glGetUniformLocation(self.wboit_splat_shader, 'u_focal_y'),    float(projection[1, 1]))
		glUniform1f(glGetUniformLocation(self.wboit_splat_shader, 'u_splat_scale'), float(self.m_splat_scale))
		glUniform1f(glGetUniformLocation(self.wboit_splat_shader, 'u_alpha_scale'), float(self.m_wboit_alpha_scale))
		glUniform1f(glGetUniformLocation(self.wboit_splat_shader, 'u_alpha_gamma'), float(self.m_wboit_alpha_gamma))
		glUniform1f(glGetUniformLocation(self.wboit_splat_shader, 'u_alpha_cutoff'), float(self.m_wboit_alpha_cutoff))
		glUniform1f(glGetUniformLocation(self.wboit_splat_shader, 'u_front_weight'), float(self.m_wboit_front_weight))
		glUniform3fv(glGetUniformLocation(self.wboit_splat_shader, 'u_tint'), 1,
		             np.array(self.m_splat_tint, dtype=np.float32))
		glUniform1i(glGetUniformLocation(self.wboit_splat_shader, 'u_wboit_pass'), pass_idx)

		if not self.m_fastDraw and not AP.mouse_key_pressed:
			factor = 1
		elif len(self.m_volume) < 1536:
			factor = 4
		else:
			factor = 8
		glUniform1i(glGetUniformLocation(self.wboit_splat_shader, 'factor'), factor)

		first_slice  = factor * int(self.m_minSlice  / factor)
		first_row    = factor * int(self.m_minRow    / factor)
		first_column = factor * int(self.m_minColumn / factor)

		subvolume = [
			s[first_row:self.m_maxRow+1:factor, first_column:self.m_maxColumn+1:factor]
			for s in self.m_volume[first_slice:self.m_maxSlice+1:factor]
		]
		small_shape = (len(subvolume), subvolume[0].shape[0], subvolume[0].shape[1])

		glUniform1i(glGetUniformLocation(self.wboit_splat_shader, 'sizeX'), small_shape[2])
		glUniform1i(glGetUniformLocation(self.wboit_splat_shader, 'sizeY'), small_shape[1])

		# Back-to-front layer sort
		slice_depths = []
		for idx_in_subvolume in range(small_shape[0]):
			true_index = first_slice + idx_in_subvolume * factor
			metadata = self.metadata[true_index]
			image_position = np.array([
				metadata.image_position_patient[0] + metadata.pixel_spacing[0] * float(first_column),
				metadata.image_position_patient[1] + metadata.pixel_spacing[1] * float(first_row),
				metadata.image_position_patient[2]
			], dtype=np.float32)
			voxel_size = np.array([
				metadata.pixel_spacing[0],
				metadata.pixel_spacing[1],
				metadata.slice_thickness
			], dtype=np.float32)
			slice_center = image_position + voxel_size * np.array([
				0.5 * max(small_shape[2] - 1, 0),
				0.5 * max(small_shape[1] - 1, 0),
				0.0
			], dtype=np.float32)
			eye_center = modelview @ np.array([slice_center[0], slice_center[1], slice_center[2], 1.0], dtype=np.float32)
			slice_depths.append((float(eye_center[2]), idx_in_subvolume))
		slice_indices = [idx for _, idx in sorted(slice_depths)]

		for idx_in_subvolume in slice_indices:
			true_index = first_slice + idx_in_subvolume * factor
			colors = np.array(subvolume[idx_in_subvolume], dtype=np.float32).flatten()
			glBufferData(GL_ARRAY_BUFFER, colors.nbytes, colors, GL_STATIC_DRAW)

			metadata = self.metadata[true_index]
			imagePosition = [
				metadata.image_position_patient[0] + metadata.pixel_spacing[0] * float(first_column),
				metadata.image_position_patient[1] + metadata.pixel_spacing[1] * float(first_row),
				metadata.image_position_patient[2]
			]
			voxel_size = [
				metadata.pixel_spacing[0],
				metadata.pixel_spacing[1],
				metadata.slice_thickness
			]
			glUniform3fv(glGetUniformLocation(self.wboit_splat_shader, 'imagePosition'), 1, imagePosition)
			glUniform3fv(glGetUniformLocation(self.wboit_splat_shader, 'voxelSize'),      1, voxel_size)
			glDrawArrays(GL_POINTS, 0, colors.shape[0])

		glBindBuffer(GL_ARRAY_BUFFER, 0)
		glUseProgram(0)
		glDisable(GL_PROGRAM_POINT_SIZE)

	def create_program(self):
		# Inicjalizacja i konfiguracja shaderów
		geom_filename = 'volumetric_box.geom' if self.m_renderBoxes else 'volumetric.geom'
		try:
			vertex_shader = load_and_compile_shader('volumetric.vert', GL_VERTEX_SHADER)
			geometry_shader = load_and_compile_shader(geom_filename, GL_GEOMETRY_SHADER)
			fragment_shader = load_and_compile_shader('volumetric.frag', GL_FRAGMENT_SHADER)
		except Exception as e:
			print( e )
			return
		
		# Tworzenie programu shaderów
		self.shader_program = glCreateProgram()
		
		glAttachShader(self.shader_program, vertex_shader)
		glAttachShader(self.shader_program, geometry_shader)
		glAttachShader(self.shader_program, fragment_shader)
		
		glLinkProgram(self.shader_program)
		
		# Sprawdzanie, czy program został powiązany poprawnie
		if not glGetProgramiv(self.shader_program, GL_LINK_STATUS):
			info = glGetProgramInfoLog(self.shader_program)
			if isinstance(info, bytes):
				info = info.decode('utf-8')
			print(f"Shader program link failed:\n{info}")
			glDeleteProgram(self.shader_program)
			self.shader_program = None
			return
		
		# Usuwanie shaderów (już nie są potrzebne po powiązaniu programu)
		glDeleteShader(vertex_shader)
		glDeleteShader(geometry_shader)
		glDeleteShader(fragment_shader)


	def renderSelf(self):
		from .globals import AP

		if AP.wboit_pass is not None:
			if AP.wboit_pass >= 0:
				if self.is_transparent:
					self.render_wboit(AP.wboit_pass)
				return
			if self.is_transparent:
				return

		if self.m_renderSplats:
			self._render_splat()
			return

		glEnable(GL_PROGRAM_POINT_SIZE)
		if self.shader_program is None:
			self.create_program()

		# Używanie programu shaderów
		glUseProgram(self.shader_program)

		if self.v_vbo is None:
			self.v_vbo = glGenBuffers(1)

		glBindBuffer(GL_ARRAY_BUFFER, self.v_vbo)
		
		# Konfiguracja atrybutów wierzchołka
		glEnableVertexAttribArray(0)  # np. dla pozycji wierzchołka
		glVertexAttribPointer(0, 1, GL_FLOAT, GL_FALSE, 0, None)

		modelview = np.array(glGetFloatv(GL_MODELVIEW_MATRIX), dtype=np.float32)
		modelview_loc = glGetUniformLocation(self.shader_program, "modelviewMatrix")
		glUniformMatrix4fv(modelview_loc, 1, GL_FALSE, modelview)

		projection = np.array(glGetFloatv(GL_PROJECTION_MATRIX), dtype=np.float32)
		projection_loc = glGetUniformLocation(self.shader_program, "projectionMatrix")
		glUniformMatrix4fv(projection_loc, 1, GL_FALSE, projection)

		minColor_loc = glGetUniformLocation(self.shader_program, "minColor")
		glUniform1f( minColor_loc, self.m_minDisplWin )

		maxColor_loc = glGetUniformLocation(self.shader_program, "maxColor")
		glUniform1f( maxColor_loc, self.m_maxDisplWin )

		f_loc = glGetUniformLocation(self.shader_program, "f")
		glUniform3fv(f_loc, 7, self.m_filters)

		fcolors_loc = glGetUniformLocation(self.shader_program, "fcolors")
		glUniform3fv(fcolors_loc, 7, self.m_fcolors)

		if not self.m_fastDraw and not AP.mouse_key_pressed:
			factor = 1
		elif len(self.m_volume) < 1536:
			factor = 4
		else:
			factor = 8

		factor_loc = glGetUniformLocation(self.shader_program, "factor")
		glUniform1i( factor_loc, factor )
		
		first_slice = factor*int(self.m_minSlice/factor)
		first_row = factor*int(self.m_minRow/factor)
		first_column = factor*int(self.m_minColumn/factor)

		# subvolume = self.m_volume[
		# 	first_slice:self.m_maxSlice+1:factor,
		# 	first_row:self.m_maxRow+1:factor,
		# 	first_column:self.m_maxColumn+1:factor
		# 	]

		subvolume = [slice[first_row:self.m_maxRow+1:factor,first_column:self.m_maxColumn+1:factor] for slice in self.m_volume[first_slice:self.m_maxSlice+1:factor]]
#		subvolume = np.array(subvolume, dtype=np.float32)

		# small_shape = subvolume.shape
		small_shape = (len(subvolume), subvolume[0].shape[0], subvolume[0].shape[1])
		
		sizeX_loc = glGetUniformLocation(self.shader_program, "sizeX")
		glUniform1i( sizeX_loc, small_shape[2] )

		sizeY_loc = glGetUniformLocation(self.shader_program, "sizeY")
		glUniform1i( sizeY_loc, small_shape[1] )

		for idx_in_subvolume in range(small_shape[0]):
			true_index_of_slice = first_slice + idx_in_subvolume * factor
			
			colors = np.array(subvolume[idx_in_subvolume], dtype=np.float32).flatten()

			glBufferData(GL_ARRAY_BUFFER, colors.nbytes, colors, GL_STATIC_DRAW)
		
			metadata = self.metadata[true_index_of_slice]

			imagePosition = [
				metadata.image_position_patient[0] + metadata.pixel_spacing[0] * float(first_column),
				metadata.image_position_patient[1] + metadata.pixel_spacing[1] * float(first_row),
				metadata.image_position_patient[2]
			]
			
			voxel_size = [
				metadata.pixel_spacing[0],
				metadata.pixel_spacing[1],
				metadata.slice_thickness
			]

			imagePosition_loc = glGetUniformLocation(self.shader_program, "imagePosition")
			glUniform3fv( imagePosition_loc, 1, imagePosition )
			
			voxelSize_loc = glGetUniformLocation(self.shader_program, "voxelSize")
			glUniform3fv( voxelSize_loc, 1, voxel_size )

			glDrawArrays(GL_POINTS, 0, colors.shape[0])

		glBindBuffer(GL_ARRAY_BUFFER, 0)
		glUseProgram(0) # Wyłączenie programu shaderów
		glDisable(GL_PROGRAM_POINT_SIZE)


	# Domyślne ustawienie parametrów dla algorytmu SIFT
	# nfeatures - Liczba kluczowych punktów do zachowania. Domyślnie 0, co oznacza, że nie ma limitu.
	# nOctaveLayers - Liczba warstw w każdej oktawie. Domyślnie 3
	# contrastThreshold - Próg eliminacji kluczowych punktów o niskim kontraście. Domyślnie 0.04
	# edgeThreshold - Próg eliminacji kluczowych punktów na krawędziach. Domyślnie 10
	# sigma - Początkowa sigma dla Gaussowskiego rozmycia. Domyślnie 1.6
	def sift_cloud(self, nfeatures = 0, nOctaveLayers = 3, contrastThreshold = 0.04, edgeThreshold = 10, sigma = 1.6, factor=1):
		vertices = []

		for idx_of_slice in range(self.m_minSlice, self.m_maxSlice+1):
			image = self.m_volume[idx_of_slice][self.m_minRow:self.m_maxRow+1, self.m_minColumn:self.m_maxColumn+1]

			pixel_spacing = list( self.metadata[idx_of_slice].pixel_spacing )
			
			position = [
				self.metadata[idx_of_slice].image_position_patient[0] + pixel_spacing[0] * float(self.m_minColumn),
				self.metadata[idx_of_slice].image_position_patient[1] + pixel_spacing[1] * float(self.m_minRow),
				self.metadata[idx_of_slice].image_position_patient[2]
			]

			# position = self.metadata[idx_of_slice].image_position_patient

			print(f"slice {idx_of_slice}: position = {position}")
			

			# if gauss:
			# 	image = gaussian_filter(image, sigma=gauss)

			image = [ [min(max(self.m_minDisplWin,i),self.m_maxDisplWin) for i in row] for row in image]

			# Normalizuj dane obrazu do zakresu 0-255
			obraz = cv2.normalize(np.array(image), None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)


			# Domyślne ustawienie parametrów dla algorytmu SIFT
			
			# Liczba kluczowych punktów do zachowania. Domyślnie 0, co oznacza, że nie ma limitu.
			nfeatures = 0
			
			# Liczba warstw w każdej oktawie. Domyślnie 3
			nOctaveLayers = 5
			
			# Próg eliminacji kluczowych punktów o niskim kontraście. Domyślnie 0.04
			contrastThreshold = 0.05
			
			# Próg eliminacji kluczowych punktów na krawędziach. Domyślnie 10
			edgeThreshold = 10
			
			# Początkowa sigma dla Gaussowskiego rozmycia. Domyślnie 1.6
			sigma = 0.4

			# Tworzenie obiektu SIFT z ustawionymi parametrami
			sift = cv2.SIFT_create(	nfeatures=nfeatures, nOctaveLayers=nOctaveLayers, 
			 						contrastThreshold=contrastThreshold, edgeThreshold=edgeThreshold, sigma=sigma)

			# Znajdź punkty kluczowe i deskryptory za pomocą SIFT
			keypoints, descriptors = sift.detectAndCompute(obraz, None)

			# orb = cv2.ORB_create()
			# keypoints, descriptors = orb.detectAndCompute(obraz, None)

			for key in keypoints:
				point = [
							float(position[0]) + pixel_spacing[0] * key.pt[0],
							float(position[1]) + pixel_spacing[1] * key.pt[1],
							float(position[2])
				]
				
				vertices.append(np.array(point, dtype=np.float32))

		cloud = PointCloud()
		cloud.m_vertices = np.array(vertices, dtype=np.float32)
		return cloud

	# Wersja wyjściowa algorytmu marching cubes, bez dodatkowego filtrowania trójkątów.
	def marching_cube(self, factor=1, close_boundary=True, sigma_mm=None, threshold=None, threshold_min=300.0,
	                  min_volume=50, sharpening=False, taubin_iterations=10, denoise=True, fill_holes=True,
	                  denoise_iter=50, denoise_3d=False):
		vertices, faces = self.marching_cube_compute(
			factor=factor, close_boundary=close_boundary, sigma_mm=sigma_mm,
			threshold=threshold, threshold_min=threshold_min, min_volume=min_volume,
			sharpening=sharpening, taubin_iterations=taubin_iterations,
			denoise=denoise, fill_holes=fill_holes, denoise_3d=denoise_3d)
		mesh = Mesh.create(vertices=vertices, faces=faces, invert_normals=True)
		AP.addObject(mesh, self)

	def marching_cube_compute(self, factor=1, close_boundary=True, sigma_mm=None, threshold=None,
	                          threshold_min=300.0, min_volume=50, sharpening=False,
	                          taubin_iterations=10, denoise=True, fill_holes=True, denoise_iter=50,
	                          denoise_3d=False, progress_cb=None, status_cb=None):
		"""Całkowite obliczenia MC – bez Qt. Bezpieczne do uruchomienia w wątku.
		Zwraca (vertices, faces) gotowe do Mesh.create()."""
		import time
		import mcubes
		import numpy as np
		from scipy.ndimage import map_coordinates
		from .marchingCubes import (mc_preprocess, mc_gradient, mc_estimate_threshold,
		                             mc_segment, mc_sharpen, mc_to_world, taubin_smooth)

		t0 = t = time.perf_counter()
		def _log(msg):
			nonlocal t
			now = time.perf_counter()
			print(f"[MC] {msg}  ({now-t:.1f}s / total {now-t0:.1f}s)")
			t = now

		def _set_progress(value, text=None):
			if text and status_cb is not None:
				status_cb(text)
			if progress_cb is not None:
				progress_cb(value)

		px = self.metadata[1].pixel_spacing[0]
		py = self.metadata[1].pixel_spacing[1]
		pz = self.metadata[1].slice_distance
		print(f"[MC] start  voxel={px:.3f}x{py:.3f}x{pz:.3f}mm")
		_set_progress(2, "Przygotowuję marching cubes...")

		# 1. ROI
		_set_progress(5, "Wycinam ROI...")
		first_slice = factor * int(self.m_minSlice / factor)
		first_row   = factor * int(self.m_minRow    / factor)
		first_col   = factor * int(self.m_minColumn / factor)
		image = np.array([
			s[first_row:self.m_maxRow+1, first_col:self.m_maxColumn+1]
			for s in self.m_volume[first_slice:self.m_maxSlice+1]
		], dtype=np.float32)
		_log(f"1. ROI  {image.shape}")

		# 2. Preprocessing
		_set_progress(15, "Preprocessing wolumenu...")
		def _preprocess_progress(local_value):
			local_value = max(0, min(int(local_value), 100))
			_set_progress(15 + int(local_value * 13 / 100))

		image, image_full, zoom_z, pz_eff = mc_preprocess(
				image, px, py, pz, factor, sigma_mm, sharpening, denoise,
				denoise_iter, denoise_3d,
				progress_cb=_preprocess_progress,
				status_cb=status_cb)
		_log(f"2. preprocess  shape={image.shape}  denoise={denoise}  denoise_3d={denoise_3d}")

		# 3. Gradient
		_set_progress(28, "Liczę gradient...")
		grad, gx_full, gy_full, gz_full = mc_gradient(
			image, image_full, pz_eff, py, px, sharpening)
		_log("3. gradient")

		# 4. Threshold
		_set_progress(40, "Wyznaczam threshold...")
		threshold = mc_estimate_threshold(image, grad, threshold, threshold_min)
		_log(f"4. threshold={threshold:.1f}")

		# 5. Segmentacja
		_set_progress(50, "Segmentuję wolumen...")
		image_clean = mc_segment(image, threshold, px, py, pz_eff, min_volume, fill_holes)
		_log("5. segmentation")

		# 6. Marching cubes
		_set_progress(65, "Uruchamiam marching cubes...")
		image_mc = np.pad(image_clean, 1, mode='constant') if close_boundary else image_clean
		points, faces = mcubes.marching_cubes(image_mc, threshold)
		offset = 1 if close_boundary else 0
		_log(f"6. marching cubes  {len(points)} vertices, {len(faces)} faces")

		# 7. Voxel sharpening (opcjonalne)
		if sharpening:
			_set_progress(78, "Wyostrzam powierzchnię...")
			points = mc_sharpen(
				points, offset, factor, image_full, gx_full, gy_full, gz_full, threshold)
			_log("7. sharpening")

		# 8. Gradient confidence (diagnostyka)
		_set_progress(84, "Analizuję gradient na powierzchni...")
		coords = np.vstack([points[:,0]-offset, points[:,1]-offset, points[:,2]-offset])
		gv = map_coordinates(grad, coords, order=1, mode='nearest')
		_log(f"8. gradient on surface  min={gv.min():.1f}  mean={gv.mean():.1f}  max={gv.max():.1f}")

		# 9. Transformacja do układu world
		_set_progress(90, "Transformuję siatkę do world coordinates...")
		origin = [
			self.metadata[first_slice].image_position_patient[0] + px * float(first_col),
			self.metadata[first_slice].image_position_patient[1] + py * float(first_row),
			self.metadata[first_slice].image_position_patient[2],
		]
		if first_slice > 0:
			slice_distance = (self.metadata[first_slice  ].image_position_patient[2] -
			                  self.metadata[first_slice-1].image_position_patient[2])
		else:
			slice_distance = (self.metadata[first_slice+1].image_position_patient[2] -
			                  self.metadata[first_slice  ].image_position_patient[2])

		vertices = mc_to_world(
			points, origin, slice_distance, self.metadata[0].gantry_detector_tilt,
			px, py, zoom_z, factor, close_boundary, offset)

		# 10. Taubin smoothing
		if taubin_iterations > 0:
			_set_progress(95, "Wygładzam siatkę...")
			vertices = taubin_smooth(vertices, faces, iterations=taubin_iterations)
			_log(f"10. Taubin smoothing  iterations={taubin_iterations}")

		_set_progress(100, "Marching cubes zakończony")
		_log("done")
		return vertices, faces

	def adjustMinMax(self, calc_color=True, winMin=None, winMax=None, min_slice=None, max_slice=None, min_row=None, max_row=None, min_column=None, max_column=None):
		if calc_color:
			self.m_min = np.min(self.m_volume[0])
			self.m_max = np.max(self.m_volume[0])
			for i in tqdm(range(len(self.m_volume)), desc='Processing'):
				self.m_min = min(self.m_min, np.min(self.m_volume[i]))
				self.m_max = max(self.m_max, np.max(self.m_volume[i]))
		self.m_minDisplWin = winMin if winMin else self.m_min
		self.m_maxDisplWin = winMax if winMax else self.m_max
		self.m_minSlice = min_slice if min_slice else 0
		self.m_maxSlice = max_slice if max_slice else self.shape[0]-1
		self.m_minRow = min_row if min_row else 0
		self.m_maxRow = max_row if max_row else self.shape[1]-1
		self.m_minColumn = min_column if min_column else 0
		self.m_maxColumn = max_column if max_column else self.shape[2]-1

	def adjustMinMaxColor(self, color):
		self.m_min = min(self.m_min, color)
		self.m_max = max(self.m_max, color)
		self.m_minDisplWin = self.m_min
		self.m_maxDisplWin = self.m_max

	@staticmethod
	def create(layers=256, rows=256, columns=256):
		volum = Volumetric()
		volum.m_volume = [] #np.zeros((layers, rows, columns), dtype=np.float32)

		for i in tqdm(range(layers), desc=f"creating volume ({layers}, {rows}, {columns})..."):
			try:
				subarray = np.zeros((rows,columns), dtype='float32')
			except MemoryError:
				print("\nBRAK PAMIĘCI !!!")
				return None
			# subarray[:,:] = i
			volum.m_volume.append(subarray)

		volum.shape = (layers, rows, columns)

		for l in range(layers):
			mdata = SliceMetadata()
			mdata.image_position_patient[2] = float(l)
			volum.metadata.append(mdata)

		volum.m_min, volum.m_max = 0., 0.
		volum.adjustMinMax(calc_color=False)

		for filter in volum.m_filters:
			filter[1] = max(filter[1], volum.m_minDisplWin)
			filter[2] = min(filter[2], volum.m_maxDisplWin)
		return volum
	
	def drawBox(self, origin=[0,0,0], size=[10,10,10], color=1000.):
		layers, rows, cols = self.shape
		for z in tqdm(range(size[0]), desc=f"drawing volumetric box: origin = {origin}, size = {size}..."):
			for y in range(size[1]):
				for x in range(size[2]):
					if (col := origin[2] + x) < cols and (row := origin[1] + y) < rows and (layer := origin[0] + z) < layers:
						self.m_volume[layer][row, col] = color
		self.adjustMinMaxColor(color)

	def drawSphere(self, origin=[0,0,0], radius=1, color=1000.):
		origin_z, origin_y, origin_x = origin
		z_min = max(0, origin_z - radius)
		z_max = min(self.shape[0], origin_z + radius + 1)
		y_min = max(0, origin_y - radius)
		y_max = min(self.shape[1], origin_y + radius + 1)
		x_min = max(0, origin_x - radius)
		x_max = min(self.shape[2], origin_x + radius + 1)

		# Przygotowanie danych wejściowych
		radius_squared = radius**2

		# Tworzenie siatki współrzędnych
		z = np.arange(z_min, z_max)
		y = np.arange(y_min, y_max)
		x = np.arange(x_min, x_max)
		zv, yv, xv = np.meshgrid(z, y, x, indexing='ij')

		# Obliczanie maski dla sfer
		mask = (xv - origin_x)**2 + (yv - origin_y)**2 + (zv - origin_z)**2 <= radius_squared

		# Rysowanie sfery
		for z_idx in tqdm(range(z_min,z_max), desc=f"drawing volumetric sphere: origin = {origin}, radius = {radius}..."):
			slice_mask = mask[z_idx - z_min,:,:]

			shifted_mask = np.zeros_like(self.m_volume[z_idx], dtype=bool)
			shifted_mask[y_min:y_min+slice_mask.shape[0], x_min:x_min+slice_mask.shape[1]] = slice_mask

			self.m_volume[z_idx][shifted_mask] = color			
		self.adjustMinMaxColor(color)


	# def drawEllipsoid(self, origin=[0,0,0], radii=[1,1,1], color=1000.):
	# 	origin_z, origin_y, origin_x = origin
	# 	radius_z, radius_y, radius_x = radii
	# 	for z in range(self.shape[0]):
	# 		for y in range(self.shape[1]):
	# 			for x in range(self.shape[2]):
	# 				if ((x - origin_x) / radius_x) ** 2 + ((y - origin_y) / radius_y) ** 2 + ((z - origin_z) / radius_z) ** 2 <= 1:
	# 					self.m_volume[z, y, x] = color
	# 	# self.m_volume.flush()
	# 	self.adjustMinMax()

	def drawCylinder(self, origin=[0,0,0], radius=1, height=1, axis='z', color=1000.):
		origin_z, origin_y, origin_x = origin
		#radius = float(radius)
		height = int(height)
		
		if axis == 'z':
			for z in range(origin_z - height // 2, origin_z + height // 2 + 1):
				for y in range(origin_y - radius, origin_y + radius + 1):
					for x in range(origin_x - radius, origin_x + radius + 1):
						if ((y - origin_y) ** 2 + (x - origin_x) ** 2 <= radius ** 2):
							self.m_volume[z][y, x] = color
		elif axis == 'y':
			for z in range(origin_z - radius, origin_z + radius + 1):
				for y in range(origin_y - height // 2, origin_y + height // 2 + 1):
					for x in range(origin_x - radius, origin_x + radius + 1):
						if ((z - origin_z) ** 2 + (x - origin_x) ** 2 <= radius ** 2):
							self.m_volume[z][y, x] = color
		elif axis == 'x':
			for z in range(origin_z - radius, origin_z + radius + 1):
				for y in range(origin_y - radius, origin_y + radius + 1):
					for x in range(origin_x - height // 2, origin_x + height // 2 + 1):
						if ((z - origin_z) ** 2 + (y - origin_y) ** 2 <= radius ** 2):
							self.m_volume[z][y, x] = color
		else:
			raise ValueError("Axis must be one of 'x', 'y', or 'z'.")
		# self.m_volume.flush()
		self.adjustMinMaxColor(color)

	def set_pixel_size(self, image_x=1.0, image_y=1.0, slice_thickness=1.0):
		"""Update spacing metadata for procedurally created or edited volumes."""
		for n,mdata in enumerate(self.metadata):
			mdata.pixel_spacing = [image_x, image_y]
			mdata.voxel_spacing = [image_x, image_y, slice_thickness]
			mdata.slice_thickness = slice_thickness
			mdata.slice_distance = slice_thickness
			mdata.slice_location = slice_thickness*n
			mdata.image_position_patient[2] = slice_thickness*n

	def set_position(self, x=0.0, y=0.0, z=0.0):
		for n,mdata in enumerate(self.metadata):
			mdata.image_position_patient[0] = x
			mdata.image_position_patient[1] = y
			mdata.image_position_patient[2] = z + mdata.slice_distance*n
			mdata.slice_location = mdata.image_position_patient[2]

	# def export(self, dir="v:/test/", file_base="image_", ext=".png"):
	# 	from PIL import Image
	# 	import os
	# 	for i,layer in enumerate(self.m_volume):
	# 		# stwórz obraz
	# 		img = Image.fromarray(layer.astype(np.uint8))

	# 		# Utwórz nazwę pliku zgodnie z formatem "file_base_numer.ext"
	# 		filename = os.path.join(dir, f"{file_base}{i:03}{ext}")

	# 		# Zapisz obraz na dysku
	# 		img.save(filename)			

	def export(self, dir="v:/test/", file_base="image_", ext=".dcm"):
		if not os.path.exists(dir):
			os.makedirs(dir)

		for i, layer in enumerate(self.m_volume):
			# Tworzenie obiektu DICOM
			ds = pydicom.FileDataset(os.path.join(dir, f"{file_base}{i:03}{ext}"), {}, file_meta=None, preamble=b"\0" * 128)
			
			# Ustawienie podstawowych atrybutów DICOM
			ds.PatientName = "Anonymous"
			ds.PatientID = "123456"
			ds.Modality = "MR"
			ds.SeriesDescription = "generated with pyDpVision software"
			ds.Rows, ds.Columns = layer.shape
			ds.PixelSpacing = self.metadata[i].pixel_spacing
			ds.BitsAllocated = 16  # Ustawiamy na 16 bitów
			ds.BitsStored = 16
			ds.HighBit = 15
			ds.PixelRepresentation = 1  # Ustawiamy na wartość ze znakiem (signed)
			
			# Przykładowe dodatkowe atrybuty DICOM
			ds.ImagePositionPatient = self.metadata[i].image_position_patient
			ds.RescaleIntercept = -1000.0  # Jeśli potrzebne, ustawienie interceptu
			ds.RescaleSlope = 1.0  # Jeśli potrzebne, ustawienie nachylenia
			ds.SliceThickness = self.metadata[i].slice_thickness
			ds.SliceLocation = self.metadata[i].slice_location

			ds.SamplesPerPixel = 1
			ds.PhotometricInterpretation = 'MONOCHROME2'
			
			ds.file_meta.TransferSyntaxUID = pydicom.uid.ImplicitVRLittleEndian 
			
			# Konwersja warstwy na format DICOM
			# Zakładając, że warstwa jest typu int lub float, możesz ją rzutować na int16
			image = layer.astype(np.int16)
			ds.PixelData = image.tobytes()

			# Zapisanie pliku DICOM
			ds.save_as(os.path.join(dir, f"{file_base}{i:03}{ext}"))
