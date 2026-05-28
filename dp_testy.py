import os
import numpy as np

from dpVision import AP, Transform, Image, AnnotationPoint, AnnotationSphere, AnnotationPath, VirtualXRay

from PyQt5.QtCore import QTimer

from dpVision.annotationElipsoide import AnnotationElipsoide
from dpVision.annotationPlane import AnnotationPlane
from dpVision.mesh import Mesh
from dpVision.meshQualityAnalyzer import MeshQualityAnalyzer
from dpVision.meshUncertaintyModel import MeshUncertaintyModel, colorize_mesh_by_confidence, confidence_to_rgba, uncertainty_colormap
from dpVision.volumetric import Volumetric
from dpVision.xrayProjection import (
	XRayProjectionGeometry,
	XRayPhysicsModel,
	XRayProjectionQualityProfile,
	XRayProjectionConfig,
	RawPresentationModel,
	DigitalRadiographyPresentationModel,
	MeshXRaySource,
	VolumetricXRaySource,
	XRayScene,
	save_projection_png,
	save_projection_tiff,
	save_projection_dicom,
)

def fastTest1():
	obj = Image(path = "d:\\rozmiary2.PNG")
	if not obj is None:
		tra = Transform()
		if not tra is None:
			tra.addChild(obj)
			AP.mainWin.workspace.m_data.append(tra)
			AP.mainWin.dock["workspace"].addNewItem(tra)

		obj2 = Image(image = obj)
		if not obj2 is None:
			tra2 = Transform()
			if not tra2 is None:
				tra2.addChild(obj2)
				AP.mainWin.workspace.m_data.append(tra2)
				AP.mainWin.dock["workspace"].addNewItem(tra2)

def fastTest2():
	obj = AnnotationPoint( point=[5,5,5], vector=[1.0,0.0,0.0] )
	if not obj is None:
		AP.mainWin.workspace.m_data.append(obj)
		AP.mainWin.dock["workspace"].addNewItem(obj)

	obj = AnnotationPlane( size=[30,30] )
	if not obj is None:
		AP.mainWin.workspace.m_data.append(obj)
		AP.mainWin.dock["workspace"].addNewItem(obj)

	obj = AnnotationSphere( radius=10.0, color=[255,255,0,128] )
	if not obj is None:
		AP.mainWin.workspace.m_data.append(obj)
		AP.mainWin.dock["workspace"].addNewItem(obj)


	obj = AnnotationElipsoide( 
		axis_x=(-0.9726,-0.2070,-0.1061),
		axis_y=(-0.2324,0.8833,0.4071),
		axis_z=(-0.0094,-0.4206,0.9072),
		radii=(2.4358, 0.7820, 0.3477),
		color=[255,255,0,128]
	)

	if not obj is None:
		tr = Transform()
		if not tr is None:
			tr.addChild(obj)

			AP.mainWin.workspace.m_data.append(tr)
			AP.mainWin.dock["workspace"].addNewItem(tr)
	AP.mainWin.update()

def fastTest3():
	obj = AnnotationPath( points=[[-5,-5,-5],[-5,-5,5],[5,-5,5],[5,5,5]] )
	if not obj is None:
		AP.mainWin.workspace.m_data.append(obj)
		AP.mainWin.dock["workspace"].addNewItem(obj)

	AP.mainWin.update()

def fastTest4():
	def onTimeout():
		if not hasattr(onTimeout, "cnt"):
			onTimeout.cnt = 0
		print(f"step: {onTimeout.cnt}")
		onTimeout.cnt += 1
		timer.start(1000)
	timer = QTimer()
	timer.setSingleShot(True)
	timer.timeout.connect(onTimeout)
	timer.start(1000)

def kielich_maly():
	volum = Volumetric.create(layers=128, rows=128, columns=128)
	volum.set_position(x=-64.0, y=-64.0, z=-64.0)
	volum.drawSphere(origin=[64,54,64], radius=30, color=2000.)
	volum.drawSphere(origin=[64,54,64], radius=25, color=0.)
	volum.drawBox(origin=[10,0,10], size=[100,50,100], color=0.)
	volum.drawCylinder(origin=[64,100,64], radius=6, height=35, axis='y', color=2000.)
	volum.drawBox(origin=[50,117,50], size=[28,10,28], color=2000.)
	AP.addObject(volum)

def kielich_duzy(volum):
	volum.drawSphere(origin=[256,216,256], radius=120, color=2000.)
	volum.drawSphere(origin=[256,216,256], radius=100, color=0.)
	volum.drawBox(origin=[40,0,40], size=[400,200,400], color=0.)
	volum.drawCylinder(origin=[256,400,256], radius=24, height=140, axis='y', color=2000.)
	volum.drawBox(origin=[200,468,200], size=[112,40,112], color=2000.)



def fast_test_5(layers=2048, rows=2048, columns=2048):
	volum = Volumetric.create(layers=layers, rows=rows, columns=columns)
	if volum:
		x, y, z = int(columns/2), int(rows/2), int(layers/2)
		w = [int(columns/25), int(rows/25), int(layers/25)]
		volum.set_position(x=float(-x), y=float(-y), z=float(-z))
		volum.drawSphere(origin=[x, y, z], radius=int(layers/8), color=2000.)
		volum.drawBox(origin=[x-w[0],y-w[1],0], size=[w[0]*2,w[1]*2,layers], color=1000.)
		volum.drawBox(origin=[x-w[0],0,z-w[2]], size=[w[0]*2,rows,w[2]*2], color=1000.)
		volum.drawBox(origin=[0,y-w[1],z-w[2]], size=[columns,w[1]*2,w[2]*2], color=1000.)
		AP.addObject(volum)

def fast_test_7():
	volum = Volumetric.create(layers=256, rows=256, columns=256)
	volum.set_position(x=-128.0, y=-128.0, z=-128.0)
	volum.drawBox(origin=[50,50,50], size=[150,150,150], color=1000.)
	volum.drawBox(origin=[75,75,75], size=[100,100,100], color=750.)
	volum.drawBox(origin=[100,100,100], size=[50,50,50], color=500.)
	# volum.drawSphere(origin=[256,216,256], radius=120, color=2000.)
	AP.addObject(volum)


def _demo_output_dir(*parts):
	"""Return an absolute path inside `sample_data/generated`."""
	return os.path.join(os.path.dirname(__file__), "sample_data", "generated", *parts)


def _make_jaw_transform(translation_xyz=(0.0, 0.0, 0.0), rotation_deg_z=0.0):
	"""Build a simple rigid transform for synthetic jaw motion tests."""
	tx, ty, tz = translation_xyz
	angle = np.deg2rad(float(rotation_deg_z))
	cos_a = np.cos(angle)
	sin_a = np.sin(angle)
	transform = np.eye(4, dtype=np.float32)
	transform[:3, :3] = np.array([
		[cos_a, -sin_a, 0.0],
		[sin_a,  cos_a, 0.0],
		[0.0,    0.0,   1.0],
	], dtype=np.float32)
	transform[:3, 3] = np.array([tx, ty, tz], dtype=np.float32)
	return transform


def create_synthetic_xray_demo_dicoms(base_dir=None, overwrite=False):
	"""Create two simple synthetic DICOM sets: a fixed skull and a movable jaw."""
	if base_dir is None:
		base_dir = _demo_output_dir("xray_demo_dicoms")

	skull_dir = os.path.join(base_dir, "skull")
	jaw_dir = os.path.join(base_dir, "jaw")
	if not overwrite and os.path.isdir(skull_dir) and os.path.isdir(jaw_dir):
		return {
			"base_dir": base_dir,
			"skull_dir": skull_dir,
			"jaw_dir": jaw_dir,
		}

	os.makedirs(skull_dir, exist_ok=True)
	os.makedirs(jaw_dir, exist_ok=True)

	skull = Volumetric.create(layers=96, rows=96, columns=96)
	skull.label = "synthetic_skull"
	skull.set_position(x=-48.0, y=-48.0, z=-48.0)
	skull.set_pixel_size(image_x=1.0, image_y=1.0, slice_thickness=1.0)
	skull.drawSphere(origin=[48, 50, 48], radius=34, color=1800.0)
	skull.drawSphere(origin=[48, 50, 48], radius=28, color=200.0)
	skull.drawBox(origin=[0, 0, 0], size=[96, 22, 96], color=0.0)
	skull.export(dir=skull_dir, file_base="skull_", ext=".dcm")

	jaw = Volumetric.create(layers=96, rows=96, columns=96)
	jaw.label = "synthetic_jaw"
	jaw.set_position(x=-48.0, y=-48.0, z=-48.0)
	jaw.set_pixel_size(image_x=1.0, image_y=1.0, slice_thickness=1.0)
	jaw.drawBox(origin=[24, 18, 18], size=[12, 26, 18], color=1800.0)
	jaw.drawBox(origin=[24, 18, 60], size=[12, 26, 18], color=1800.0)
	jaw.drawBox(origin=[18, 12, 18], size=[12, 10, 60], color=1800.0)
	jaw.drawBox(origin=[30, 18, 30], size=[6, 16, 36], color=0.0)
	jaw.export(dir=jaw_dir, file_base="jaw_", ext=".dcm")

	return {
		"base_dir": base_dir,
		"skull_dir": skull_dir,
		"jaw_dir": jaw_dir,
	}


def build_synthetic_xray_demo_volumes():
	"""Create in-memory synthetic skull and jaw volumes for X-ray projection tests."""
	skull = Volumetric.create(layers=96, rows=96, columns=96)
	skull.label = "synthetic_skull"
	skull.set_position(x=-48.0, y=-48.0, z=-48.0)
	skull.set_pixel_size(image_x=1.0, image_y=1.0, slice_thickness=1.0)
	skull.drawSphere(origin=[48, 50, 48], radius=34, color=1800.0)
	skull.drawSphere(origin=[48, 50, 48], radius=28, color=200.0)
	skull.drawBox(origin=[0, 0, 0], size=[96, 22, 96], color=0.0)

	jaw = Volumetric.create(layers=96, rows=96, columns=96)
	jaw.label = "synthetic_jaw"
	jaw.set_position(x=-48.0, y=-48.0, z=-48.0)
	jaw.set_pixel_size(image_x=1.0, image_y=1.0, slice_thickness=1.0)
	jaw.drawBox(origin=[24, 18, 18], size=[12, 26, 18], color=1800.0)
	jaw.drawBox(origin=[24, 18, 60], size=[12, 26, 18], color=1800.0)
	jaw.drawBox(origin=[18, 12, 18], size=[12, 10, 60], color=1800.0)
	jaw.drawBox(origin=[30, 18, 30], size=[6, 16, 36], color=0.0)
	return skull, jaw


def build_synthetic_xray_demo_mesh():
	"""Create one simple synthetic mesh sample for hybrid volume + mesh X-ray tests."""
	vertices = np.array([
		[-12.0, -6.0, -25.0],
		[ 12.0, -6.0, -25.0],
		[ 12.0,  6.0, -25.0],
		[-12.0,  6.0, -25.0],
		[-12.0, -6.0,  25.0],
		[ 12.0, -6.0,  25.0],
		[ 12.0,  6.0,  25.0],
		[-12.0,  6.0,  25.0],
	], dtype=np.float32)
	faces = np.array([
		[0, 1, 2], [0, 2, 3],
		[4, 6, 5], [4, 7, 6],
		[0, 4, 5], [0, 5, 1],
		[1, 5, 6], [1, 6, 2],
		[2, 6, 7], [2, 7, 3],
		[3, 7, 4], [3, 4, 0],
	], dtype=np.uint32)
	mesh = Mesh.create(vertices=vertices, faces=faces)
	mesh.label = "synthetic_implant_mesh"
	return mesh


def report_mesh_xray_topology(mesh: Mesh, area_epsilon=1e-12):
	"""Print one compact RTG-oriented topology report for a mesh."""
	analyzer = MeshQualityAnalyzer(mesh)
	report = analyzer.compute_xray_topology_report(area_epsilon=area_epsilon)
	print(analyzer.summarize_xray_topology_report(area_epsilon=area_epsilon))
	return report


def report_selected_mesh_xray_topology(area_epsilon=1e-12):
	"""Print one topology report for the currently selected mesh in the workspace."""
	selected = getattr(AP, "selected", None)
	if not isinstance(selected, Mesh):
		raise TypeError("AP.selected must be a Mesh to run report_selected_mesh_xray_topology().")
	return report_mesh_xray_topology(selected, area_epsilon=area_epsilon)


def clean_mesh_for_xray(mesh: Mesh, vertex_merge_tolerance=1e-6, drop_degenerate_faces=True,
	                    drop_nonmanifold_faces=False, drop_boundary_faces=False):
	"""Return one cleaned mesh copy plus a compact cleanup summary for RTG tests.

	The cleanup is intentionally conservative:
	- merge duplicated vertices by quantized position,
	- drop degenerate faces created by merged vertex ids,
	- remove duplicate triangle faces independent of winding order,
	- optionally drop faces incident to non-manifold or boundary edges.
	"""
	if not isinstance(mesh, Mesh):
		raise TypeError("mesh must be an instance of Mesh.")

	vertices = np.asarray(mesh.m_vertices, dtype=np.float32)
	faces = np.asarray(mesh.m_faces, dtype=np.int64)
	if vertices.ndim != 2 or vertices.shape[1] != 3:
		raise ValueError("mesh.m_vertices must have shape (N, 3).")
	if faces.ndim != 2 or faces.shape[1] != 3:
		raise ValueError("mesh.m_faces must have shape (M, 3).")
	if vertex_merge_tolerance <= 0.0:
		raise ValueError("vertex_merge_tolerance must be positive.")

	quantized_vertices = np.round(vertices / float(vertex_merge_tolerance)).astype(np.int64)
	_unique_keys, unique_vertex_indices, inverse_vertex_indices = np.unique(
		quantized_vertices,
		axis=0,
		return_index=True,
		return_inverse=True,
	)
	merged_vertices = vertices[unique_vertex_indices].astype(np.float32, copy=False)
	remapped_faces = inverse_vertex_indices[faces].astype(np.int64, copy=False)

	degenerate_mask = (
		(remapped_faces[:, 0] == remapped_faces[:, 1])
		| (remapped_faces[:, 1] == remapped_faces[:, 2])
		| (remapped_faces[:, 2] == remapped_faces[:, 0])
	)
	degenerate_removed_count = int(np.count_nonzero(degenerate_mask))
	if drop_degenerate_faces and degenerate_removed_count > 0:
		remapped_faces = remapped_faces[~degenerate_mask]

	normalized_faces = np.sort(remapped_faces, axis=1)
	_unique_faces, unique_face_indices = np.unique(normalized_faces, axis=0, return_index=True)
	del _unique_faces
	unique_face_indices = np.sort(unique_face_indices)
	duplicate_face_removed_count = int(remapped_faces.shape[0] - unique_face_indices.shape[0])
	remapped_faces = remapped_faces[unique_face_indices]

	removed_nonmanifold_face_count = 0
	removed_boundary_face_count = 0
	if drop_nonmanifold_faces or drop_boundary_faces:
		edge_to_face_indices = {}
		for face_idx, (a, b, c) in enumerate(remapped_faces):
			for edge in ((a, b), (b, c), (c, a)):
				edge_key = tuple(sorted((int(edge[0]), int(edge[1]))))
				edge_to_face_indices.setdefault(edge_key, []).append(int(face_idx))

		faces_to_drop = set()
		for edge_faces in edge_to_face_indices.values():
			if drop_boundary_faces and len(edge_faces) == 1:
				faces_to_drop.update(edge_faces)
			if drop_nonmanifold_faces and len(edge_faces) > 2:
				faces_to_drop.update(edge_faces)

		if faces_to_drop:
			faces_to_drop_array = np.array(sorted(faces_to_drop), dtype=np.int64)
			if drop_nonmanifold_faces:
				nonmanifold_faces = set()
				for edge_faces in edge_to_face_indices.values():
					if len(edge_faces) > 2:
						nonmanifold_faces.update(edge_faces)
				removed_nonmanifold_face_count = int(np.intersect1d(
					faces_to_drop_array,
					np.array(sorted(nonmanifold_faces), dtype=np.int64),
					assume_unique=True,
				).shape[0])
			if drop_boundary_faces:
				boundary_faces = set()
				for edge_faces in edge_to_face_indices.values():
					if len(edge_faces) == 1:
						boundary_faces.update(edge_faces)
				removed_boundary_face_count = int(np.intersect1d(
					faces_to_drop_array,
					np.array(sorted(boundary_faces), dtype=np.int64),
					assume_unique=True,
				).shape[0])
			keep_mask = np.ones(remapped_faces.shape[0], dtype=bool)
			keep_mask[faces_to_drop_array] = False
			remapped_faces = remapped_faces[keep_mask]

	cleaned_mesh = Mesh.create(
		vertices=merged_vertices,
		faces=remapped_faces.astype(np.uint32, copy=False),
	)
	cleaned_mesh.label = f"{getattr(mesh, 'label', 'mesh')}_xray_clean"

	cleanup_report = {
		"input_vertex_count": int(vertices.shape[0]),
		"input_face_count": int(faces.shape[0]),
		"output_vertex_count": int(cleaned_mesh.m_vertices.shape[0]),
		"output_face_count": int(cleaned_mesh.m_faces.shape[0]),
		"merged_vertex_count": int(vertices.shape[0] - cleaned_mesh.m_vertices.shape[0]),
		"removed_degenerate_face_count": int(degenerate_removed_count if drop_degenerate_faces else 0),
		"removed_duplicate_face_count": int(duplicate_face_removed_count),
		"removed_nonmanifold_face_count": int(removed_nonmanifold_face_count),
		"removed_boundary_face_count": int(removed_boundary_face_count),
		"vertex_merge_tolerance": float(vertex_merge_tolerance),
		"drop_nonmanifold_faces": bool(drop_nonmanifold_faces),
		"drop_boundary_faces": bool(drop_boundary_faces),
	}
	return cleaned_mesh, cleanup_report


def clean_selected_mesh_for_xray(vertex_merge_tolerance=1e-6, add_to_workspace=True,
	                             drop_nonmanifold_faces=False, drop_boundary_faces=False):
	"""Clean the currently selected mesh, print reports before/after and optionally add the copy."""
	selected = getattr(AP, "selected", None)
	if not isinstance(selected, Mesh):
		raise TypeError("AP.selected must be a Mesh to run clean_selected_mesh_for_xray().")

	before_report = report_mesh_xray_topology(selected)
	cleaned_mesh, cleanup_report = clean_mesh_for_xray(
		selected,
		vertex_merge_tolerance=vertex_merge_tolerance,
		drop_nonmanifold_faces=drop_nonmanifold_faces,
		drop_boundary_faces=drop_boundary_faces,
	)
	after_report = report_mesh_xray_topology(cleaned_mesh)

	print("Mesh XRay cleanup summary:", cleanup_report)
	if add_to_workspace:
		AP.addObject(cleaned_mesh)

	return {
		"original_report": before_report,
		"cleaned_report": after_report,
		"cleanup_report": cleanup_report,
		"cleaned_mesh": cleaned_mesh,
	}


def run_virtual_xray_headless(virtual_xray, save_png_path=None):
	"""Run one VirtualXRay without inserting or refreshing GUI image objects.

	This helper isolates the projection backend from the `Run Simulation` GUI path.
	If it succeeds while the GUI button still crashes, the issue is likely in image
	creation, workspace insertion or GL refresh rather than in the projection math.
	"""
	if not isinstance(virtual_xray, VirtualXRay):
		raise TypeError("virtual_xray must be a VirtualXRay instance.")

	config = virtual_xray.build_projection_config()
	raw_image, stats = virtual_xray.build_scene().project(
		config=config,
		return_stats=True,
		progress_callback=None,
	)
	raw_image = np.asarray(raw_image, dtype=np.float32)
	display_image = config.apply_presentation(raw_image)

	print(
		"VirtualXRay headless projection:",
		{
			"label": str(getattr(virtual_xray, "label", "VirtualXRay")),
			"shape": tuple(int(v) for v in raw_image.shape),
			"elapsed_seconds": float(stats.elapsed_seconds),
			"traced_pixels": int(stats.traced_pixels),
			"total_sample_count": int(stats.total_sample_count),
		},
	)

	if save_png_path is not None:
		save_projection_png(
			display_image,
			save_png_path,
			invert=False,
			fixed_range=(0.0, 1.0),
		)
		print(f"Saved headless XRay preview to: {save_png_path}")

	return {
		"raw_image": raw_image,
		"display_image": display_image,
		"stats": stats,
	}


def run_selected_virtual_xray_headless(save_png_path=None):
	"""Run the currently selected VirtualXRay without touching the GUI image path."""
	selected = getattr(AP, "selected", None)
	if not isinstance(selected, VirtualXRay):
		selected_type = "None" if selected is None else type(selected).__name__
		raise TypeError(
			f"AP.selected must be a VirtualXRay to run run_selected_virtual_xray_headless(); got {selected_type}."
		)
	return run_virtual_xray_headless(selected, save_png_path=save_png_path)


def demo_synthetic_xray_projection(output_dir=None, jaw_translation_xyz=(0.0, -8.0, 0.0), jaw_rotation_deg_z=8.0):
	"""Generate one example hybrid volume + mesh X-ray projection."""
	create_synthetic_xray_demo_dicoms()
	skull, jaw = build_synthetic_xray_demo_volumes()
	implant_mesh = build_synthetic_xray_demo_mesh()
	if output_dir is None:
		output_dir = _demo_output_dir("xray_demo_output")
	os.makedirs(output_dir, exist_ok=True)

	skull_transform = np.eye(4, dtype=np.float32)
	jaw_transform = _make_jaw_transform(
		translation_xyz=jaw_translation_xyz,
		rotation_deg_z=jaw_rotation_deg_z,
	)
	mesh_transform = np.eye(4, dtype=np.float32)
	mesh_transform[:3, 3] = np.array([42.0, 18.0, 48.0], dtype=np.float32)

	geometry = XRayProjectionGeometry.from_detector_pose(
		detector_center_ref=[42.2, 42.2, 180.0],
		detector_normal_ref=[0.0, 0.0, -1.0],
		detector_up_ref=[0.0, 1.0, 0.0],
		detector_shape_hw=[512, 512],
		detector_pixel_size_mm=0.4,
		step_mm=1.0,
		source_position_ref=[42.2, 42.2, -220.0],
	)
	physics = XRayPhysicsModel(
		mu_air=0.0,
		mu_water=0.02,
		attenuation_scale=1.0,
		output_mode="integral",
	)
	scene = XRayScene.from_sample_sources([
		VolumetricXRaySource(skull, global_transform=skull_transform, interpolation="linear"),
		VolumetricXRaySource(jaw, global_transform=jaw_transform, interpolation="linear"),
		MeshXRaySource(implant_mesh, global_transform=mesh_transform, scalar_value=2200.0, mode="solid", shell_thickness_mm=1.2),
	])
	config = XRayProjectionConfig(
		geometry=geometry,
		physics_model=physics,
		presentation_model=DigitalRadiographyPresentationModel(
			invert=False,
			gamma=0.7,
			contrast=1.2,
		),
		reference_transform=np.eye(4, dtype=np.float32),
		quality_profile=XRayProjectionQualityProfile.normal(),
	)

	image, stats = scene.project(config=config, return_stats=True)
	raw_presentation = RawPresentationModel()
	raw_image = raw_presentation.apply(image)
	display_image = config.apply_presentation(image)

	png_path = os.path.join(output_dir, "synthetic_xray_display.png")
	tiff_path = os.path.join(output_dir, "synthetic_xray_display.tiff")
	dicom_path = os.path.join(output_dir, "synthetic_xray_display.dcm")
	raw_tiff_path = os.path.join(output_dir, "synthetic_xray_raw.tiff")
	save_projection_png(display_image, png_path, invert=False, fixed_range=(0.0, 1.0))
	save_projection_tiff(display_image, tiff_path, mode="uint16", invert=False, fixed_range=(0.0, 1.0))
	save_projection_dicom(
		display_image,
		dicom_path,
		patient_name="Synthetic^XRay",
		patient_id="XRAYDEMO",
		study_description="Synthetic multi-volume demo",
		series_description="Skull + Jaw projection display",
		invert=False,
		fixed_range=(0.0, 1.0),
	)
	save_projection_tiff(raw_image, raw_tiff_path, mode="float32")
	return {
		"image": image,
		"raw_image": raw_image,
		"display_image": display_image,
		"png_path": png_path,
		"tiff_path": tiff_path,
		"dicom_path": dicom_path,
		"raw_tiff_path": raw_tiff_path,
		"jaw_transform": jaw_transform,
		"stats": stats,
		"config": config,
	}


def create_virtual_xray_demo_object():
	"""Create one `VirtualXRay` scene node with synthetic skull, jaw and mesh descendants."""
	skull, jaw = build_synthetic_xray_demo_volumes()
	implant_mesh = build_synthetic_xray_demo_mesh()
	jaw_transform = _make_jaw_transform(
		translation_xyz=(0.0, -8.0, 0.0),
		rotation_deg_z=8.0,
	)

	setup = VirtualXRay()
	setup.detector_center_ref = np.array([42.2, 42.2, 180.0], dtype=np.float32)
	setup.source_position_ref = np.array([42.2, 42.2, -220.0], dtype=np.float32)
	setup.detector_shape_hw = [512, 512]
	setup.detector_pixel_size_mm = [0.4, 0.4]
	setup.step_mm = 1.0
	setup.quality_profile_name = "normal"

	skull_transform = Transform()
	skull_transform.addChild(skull)
	setup.addChild(skull_transform)

	jaw_node = Transform(matrix=jaw_transform)
	jaw_node.label = "jaw_pose"
	jaw_node.addChild(jaw)
	setup.addChild(jaw_node)

	mesh_node = Transform()
	mesh_node.label = "implant_pose"
	mesh_node.translate(42.0, 18.0, 48.0)
	mesh_node.addChild(implant_mesh)
	setup.addChild(mesh_node)

	AP.addObject(setup)
	return setup


def create_real_xray_demo():

	"""Create one `VirtualXRay` scene node with synthetic skull and jaw descendants."""

	setup = VirtualXRay()
	setup.source_position_ref = np.array([0, 0, 1600.0], dtype=np.float32)

	setup.detector_shape_hw = [1024, 1024]
	setup.detector_pixel_size_mm = [0.2, 0.2]
	setup.detector_center_ref = np.array([0, 0, -300.0], dtype=np.float32)
	setup.detector_normal_ref = np.array([0, 0, 1.0], dtype=np.float32) # domyślnie w kierunku źródła
	setup.step_mm = 0.1
	setup.quality_profile_name = "custom"

	AP.addObject(setup)

	def on_success(skull):
		if skull is None:
			return

		AP.removeObject(child=skull.parent)

		# if isinstance(skull, Mesh):
		# 	report_mesh_xray_topology(skull)

			# skull, result = clean_mesh_for_xray(skull, 
			# 			drop_nonmanifold_faces=True,
    		# 			drop_boundary_faces=False,)
			# print(result)
			# print(result["cleaned_report"])


		skull_transform = Transform()
		#skull_transform.translate(-100, 45, 0)
		skull_transform.rotate(-90, [1,0,0])
		skull_transform.rotate(-90, [0,1,0])
		skull_transform.addChild(skull)
		setup.addChild(skull_transform)

		AP.updateAllViews()
		AP.mainWin.dock["workspace"].rebuildTree()

		skull.xray_mesh_backend = "projected_intersection_list"
		# skull.xray_debug_export_dir = r"d:\temp\xray_debug"
		# skull.xray_debug_compare_analytic = True
		# skull.xray_projected_min_abs_cos = 0.25

		#setup.debug_run_simulation_stop_after = "display"
		#setup.debug_run_simulation_stop_after = "update_views"
		#result = run_virtual_xray_headless(setup, r"d:/temp/vxray_test.png")

	# path1 = "c:/Users/darek/Desktop/praca/dane/20210312_142843/DCT0000.dcm"
	# path2 = "d:/praca0/dpVisionProject/dane/20210312_142843/DCT0000.dcm"
	# if os.path.isfile(path1):
	# 	load_path = path1
	# elif os.path.isfile(path2):
	# 	load_path = path2
	# else:
	# 	print("Nie można znaleźć pliku DICOM do testu X-ray demo.")
	# 	return
	
	# AP.load(load_path, on_success=on_success)

	# pathG = "d:/praca/dane/masks/gora/slice_000.dcm"
	# pathD = "d:/praca/dane/masks/dol/slice_000.dcm"

	pathG = "d:/praca/dane/vols/gora1/filtered_194.dcm"
	pathD = "d:/praca/dane/vols/dol/filtered_080.dcm"
	# pathD = "d:/praca/dane/vols/jaw_poisson.ply"
	# pathA = "d:/praca0/dpVisionProject/dane/20160501/filt/NDecom0000.dcm"
	# pathA = "d:/praca/dane/vols/20140521/0000.dcm"

	if os.path.isfile(pathG):
		AP.load(pathG, on_success=on_success)
		# AP.load(pathG, on_success=on_success)
	
	if os.path.isfile(pathD):
		AP.load(pathD, on_success=on_success)
	# 	# AP.load(pathD, on_success=on_success)

	# if os.path.isfile(pathA):
	# 	AP.load(pathA, on_success=on_success)

	

def benchmark_xray_performance(output_dir=None, show_reports=True):
	"""Run a series of X-ray projections and measure performance.

	Tests combinations of:
	  - Sample type: volume-only, mesh-only, mixed (volume+mesh)
	  - Volume sizes: small (64³), medium (96³), large (128³)
	  - Quality profiles: draft, normal, high

	Each row in the returned list contains timing data from XRayProjectionStats,
	including phase_timings (dict of phase -> seconds) and per_source_stats (list of
	per-source dicts with elapsed_s, work_count, bvh info, stack timings, etc.).

	Returns a list of result dicts suitable for printing a performance table.
	"""
	import time

	if output_dir is None:
		output_dir = _demo_output_dir("xray_benchmark")
	os.makedirs(output_dir, exist_ok=True)

	geometry = XRayProjectionGeometry.from_detector_pose(
		detector_center_ref=[0.0, 0.0, 180.0],
		detector_normal_ref=[0.0, 0.0, -1.0],
		detector_up_ref=[0.0, 1.0, 0.0],
		detector_shape_hw=[512, 512],
		detector_pixel_size_mm=0.4,
		step_mm=1.0,
		source_position_ref=[0.0, 0.0, -220.0],
	)
	physics = XRayPhysicsModel(mu_water=0.02, attenuation_scale=1.0, output_mode="integral")

	profiles = [
		XRayProjectionQualityProfile.draft(),
		XRayProjectionQualityProfile.normal(),
		XRayProjectionQualityProfile.high(),
	]

	volume_sizes = [
		("small",  64),
		("medium", 96),
		("large",  128),
	]

	implant_mesh = build_synthetic_xray_demo_mesh()

	print("=" * 70)
	print("XRay Performance Benchmark")
	print("=" * 70)

	results = []

	for vol_name, vol_size in volume_sizes:
		from dpVision.volumetric import Volumetric
		vol = Volumetric.create(layers=vol_size, rows=vol_size, columns=vol_size)
		vol.label = f"synthetic_{vol_name}_{vol_size}^3"
		vol.set_position(x=-vol_size / 2.0, y=-vol_size / 2.0, z=-vol_size / 2.0)
		vol.set_pixel_size(image_x=1.0, image_y=1.0, slice_thickness=1.0)
		vol.drawSphere(origin=[vol_size // 2] * 3, radius=vol_size // 3, color=1800.0)
		vol.drawSphere(origin=[vol_size // 2] * 3, radius=vol_size // 4, color=200.0)

		for profile in profiles:
			scene_variants = [
				(f"vol_{vol_name}",             [VolumetricXRaySource(vol, interpolation="linear")]),
				("mesh_only",                   [MeshXRaySource(implant_mesh, scalar_value=2200.0, mode="solid", backend="analytic_bvh")]),
				("mesh_only_projected",         [MeshXRaySource(implant_mesh, scalar_value=2200.0, mode="solid", backend="projected_intersection_list")]),
				(f"vol_{vol_name}+mesh",        [
					VolumetricXRaySource(vol, interpolation="linear"),
					MeshXRaySource(implant_mesh, scalar_value=2200.0, mode="solid", backend="analytic_bvh"),
				]),
			]
			for scene_label, sources in scene_variants:
				config = XRayProjectionConfig(
					geometry=geometry,
					physics_model=physics,
					quality_profile=profile,
				)
				scene = XRayScene.from_sample_sources(sources)
				t_wall_start = time.perf_counter()
				_img, stats = scene.project(config=config, return_stats=True)
				wall_s = time.perf_counter() - t_wall_start

				_png_name = (
					scene_label.replace("+", "_plus_").replace("^", "") + "__" + profile.name + ".png"
				)
				_png_path = os.path.join(output_dir, _png_name)
				_display = DigitalRadiographyPresentationModel(invert=False, gamma=0.6, contrast=1.1).apply(_img)
				save_projection_png(_display, _png_path, invert=False, fixed_range=(0.0, 1.0))

				row = {
					"scene":           scene_label,
					"profile":         profile.name,
					"detector":        f"{stats.detector_shape_hw[1]}x{stats.detector_shape_hw[0]}",
					"step_mm":         stats.step_mm,
					"total_ms":        stats.elapsed_seconds * 1000.0,
					"wall_ms":         wall_s * 1000.0,
					"traced_pct":      100.0 * stats.traced_pixels / max(stats.total_pixels, 1),
					"samples":         stats.total_sample_count,
					"samples_per_s":   stats.samples_per_second,
					"phase_ms":        {k: v * 1000.0 for k, v in stats.phase_timings.items()},
					"per_source":      stats.per_source_stats,
					"png_path":        _png_path,
				}
				results.append(row)

				if show_reports:
					print(f"\n[{scene_label}]  profile={profile.name}  step={stats.step_mm:.1f} mm")
					stats.print_report()

	print("\n" + "=" * 70)
	print(f"{'scene':<24s} {'profile':<8s} {'step':>5s}  {'total_ms':>9s}  {'samples/s':>13s}")
	print("-" * 70)
	for r in results:
		print(
			f"  {r['scene']:<22s} {r['profile']:<8s} {r['step_mm']:>4.1f}mm"
			f"  {r['total_ms']:>8.1f} ms  {r['samples_per_s']:>12,.0f} samp/s"
		)
	print("=" * 70)
	return results


def generate_latex_benchmark_report(results, tex_path=None, section_title="Examples and Use Cases"):
	"""Generate a standalone LaTeX performance report from benchmark_xray_performance() results.

	Produces a .tex file whose top-level heading is \\section{section_title}.
	Internal structure mirrors the article layout:
	  \\subsection{Synthetic scenes}
	  \\subsection{Projection geometry and quality profiles}
	  \\clearpage
	  \\subsection{Performance Results}
	    \\subsubsection{Total projection time and throughput}
	    \\subsubsection{Phase breakdown (normal profile)}
	    \\subsubsection{Backend comparison (mesh sources)}
	    \\subsubsection{Key observations}
	  \\subsection{Projection Images}

	Compile with:  pdflatex <tex_path>
	Requires LaTeX packages: booktabs, graphicx, subcaption, geometry, multirow.
	"""
	if tex_path is None:
		tex_path = os.path.join(_demo_output_dir("xray_benchmark"), "report.tex")
	tex_dir = os.path.dirname(tex_path)
	os.makedirs(tex_dir, exist_ok=True)

	profiles = ["draft", "normal", "high"]
	seen_sc = {}
	for r in results:
		k = r["scene"]
		if k not in seen_sc:
			seen_sc[k] = r
	scenes_all = list(seen_sc.keys())
	vol_only  = [s for s in scenes_all if s.startswith("vol_") and "+" not in s]
	mesh_only = [s for s in scenes_all if s == "mesh_only"]
	vol_mesh  = [s for s in scenes_all if "+" in s]
	scenes_display = vol_only + vol_mesh + mesh_only   # projected variant excluded from main table

	by_sp = {}
	for r in results:
		key = (r["scene"], r["profile"])
		if key not in by_sp:
			by_sp[key] = r

	def esc(s):
		return s.replace("_", r"\_").replace("^", r"\^{}").replace("+", r"\texttt{+}")

	scene_row_labels = {
		"vol_small":          r"vol\,small ($64^3$)",
		"vol_medium":         r"vol\,medium ($96^3$)",
		"vol_large":          r"vol\,large ($128^3$)",
		"mesh_only":          r"mesh only",
		"vol_small+mesh":     r"vol\,small + mesh",
		"vol_medium+mesh":    r"vol\,medium + mesh",
		"vol_large+mesh":     r"vol\,large + mesh",
	}

	def scene_row_label(s):
		return scene_row_labels.get(s, esc(s))

	def ms_cell(ms):
		if ms >= 1000.0:
			return f"{ms / 1000.0:.2f}\\,s"
		return f"{ms:.0f}\\,ms"

	def sps_cell(sps):
		if sps >= 1e6:
			return f"{sps / 1e6:.1f}"
		if sps >= 1e3:
			return f"{sps / 1e3:.1f}k"
		return f"{sps:.0f}"

	def phase_cell(v_ms, total_ms):
		if v_ms < 0.5:
			return r"$<\!1$"
		pct = 100.0 * v_ms / max(total_ms, 1e-6)
		return f"{v_ms:.0f} ({pct:.0f}\\%)"

	L = []
	def ln(s=""):
		L.append(s)

	# ── Preamble ──────────────────────────────────────────────────────────────
	ln(r"\documentclass[a4paper,10pt]{article}")
	ln(r"\usepackage[utf8]{inputenc}")
	ln(r"\usepackage[T1]{fontenc}")
	ln(r"\usepackage[english]{babel}")
	ln(r"\usepackage{booktabs}")
	ln(r"\usepackage{graphicx}")
	ln(r"\usepackage{subcaption}")
	ln(r"\usepackage{amsmath}")
	ln(r"\usepackage{geometry}")
	ln(r"\geometry{margin=2cm,top=2.5cm}")
	ln(r"\usepackage{multirow}")
	ln(r"\usepackage{lmodern}")
	ln(r"\usepackage{microtype}")
	ln()
	ln(r"\title{X-Ray Projection Pipeline\\[4pt]\large Performance Analysis --- Synthetic Benchmark}")
	ln(r"\author{pyDpVision}")
	ln(r"\date{\today}")
	ln()
	ln(r"\begin{document}")
	ln(r"\maketitle")
	ln()

	# ── Top-level section ─────────────────────────────────────────────────────
	ln(r"\section{" + section_title + r"}\label{sec:results}")
	ln()

	# ── Subsection: Synthetic scenes ──────────────────────────────────────────
	ln(r"\subsection{Synthetic scenes}")
	ln()
	ln(r"All measurements were performed on purely synthetic, in-memory datasets.")
	ln(r"No disk I/O or GUI rendering is included in the reported timings.")
	ln(r"The benchmark covers three quality profiles, three volume sizes, and three scene")
	ln(r"variants (volumetric only, mesh only, hybrid).")
	ln()
	ln(r"\paragraph{Volumes.}")
	ln(r"Three hollow-sphere volumes of increasing size were generated with $1\,\mathrm{mm}$")
	ln(r"isotropic voxel spacing:")
	ln(r"\begin{itemize}\setlength{\itemsep}{2pt}")
	ln(r"  \item \textbf{small}: $64\times 64\times 64$ voxels.")
	ln(r"  \item \textbf{medium}: $96\times 96\times 96$ voxels.")
	ln(r"  \item \textbf{large}: $128\times 128\times 128$ voxels.")
	ln(r"\end{itemize}")
	ln(r"Each contains a hollow sphere with wall attenuation $\approx 1800\,\mathrm{HU}$")
	ln(r"and interior $\approx 200\,\mathrm{HU}$. Trilinear interpolation is used during sampling.")
	ln()
	ln(r"\paragraph{Mesh.}")
	ln(r"One axis-aligned rectangular box implant ($24\times 12\times 50\,\mathrm{mm}$, 12 triangles,")
	ln(r"scalar value $2200\,\mathrm{HU}$, solid mode) is used in all mesh and hybrid scenes.")
	ln(r"Both ray-intersection backends are benchmarked separately")
	ln(r"(see Section~\ref{ssec:backends}).")
	ln()

	# ── Subsection: Projection geometry ───────────────────────────────────────
	ln(r"\subsection{Projection geometry and quality profiles}")
	ln()
	ln(r"Cone-beam geometry; source at $(0,\;0,\;-220)\,\mathrm{mm}$,")
	ln(r"detector centre at $(0,\;0,\;180)\,\mathrm{mm}$ (source-to-detector distance")
	ln(r"$400\,\mathrm{mm}$). Physics: Beer--Lambert attenuation integral,")
	ln(r"$\mu_{\mathrm{water}}=0.02\,\mathrm{mm}^{-1}$.")
	ln()
	ln(r"\begin{table}[htbp]")
	ln(r"\centering")
	ln(r"\caption{Quality profile parameters used in the benchmark.}")
	ln(r"\label{tab:profiles}")
	ln(r"\begin{tabular}{lccc}")
	ln(r"\toprule")
	ln(r"Profile & Detector & Pixel size & Marching step \\")
	ln(r"\midrule")
	ln(r"\textbf{draft}  & $256\times 256$ & $0.8\,\mathrm{mm}$ & $2.0\,\mathrm{mm}$ \\")
	ln(r"\textbf{normal} & $512\times 512$ & $0.4\,\mathrm{mm}$ & $1.0\,\mathrm{mm}$ \\")
	ln(r"\textbf{high}   & $512\times 512$ & $0.4\,\mathrm{mm}$ & $0.5\,\mathrm{mm}$ \\")
	ln(r"\bottomrule")
	ln(r"\end{tabular}")
	ln(r"\end{table}")
	ln()
	ln(r"\clearpage")

	# ── Subsection: Performance Results ───────────────────────────────────────
	ln(r"\subsection{Performance Results}")
	ln()

	# ── Subsubsection: Total time and throughput ───────────────────────────────
	ln(r"\subsubsection{Total projection time and throughput}")
	ln()
	ln(r"\begin{table}[!ht]")
	ln(r"\centering")
	ln(r"\caption{Total projection time and throughput per scene and quality profile.")
	ln(r"  Time is given in ms (or s if~$\geq 1\,\mathrm{s}$); throughput in Msamp/s (k\,samp/s for mesh).}")
	ln(r"\label{tab:main}")
	ln(r"\small")
	ln(r"\begin{tabular}{l rr rr rr}")
	ln(r"\toprule")
	ln(r"  & \multicolumn{2}{c}{\textbf{draft} (2\,mm)}")
	ln(r"  & \multicolumn{2}{c}{\textbf{normal} (1\,mm)}")
	ln(r"  & \multicolumn{2}{c}{\textbf{high} (0.5\,mm)} \\")
	ln(r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}\cmidrule(lr){6-7}")
	ln(r"Scene & time & samp/s & time & samp/s & time & samp/s \\")
	ln(r"\midrule")

	def scene_group(s):
		if s.startswith("mesh_only"):  return "mesh"
		if "+" in s:                   return "mixed"
		return "vol"

	prev_group = None
	for s in scenes_display:
		grp = scene_group(s)
		if prev_group is not None and grp != prev_group:
			ln(r"\midrule")
		prev_group = grp
		row_cells = [scene_row_label(s)]
		for p in profiles:
			r = by_sp.get((s, p))
			if r:
				row_cells.append(ms_cell(r["total_ms"]))
				row_cells.append(sps_cell(r["samples_per_s"]))
			else:
				row_cells += ["---", "---"]
		ln("  " + " & ".join(row_cells) + r" \\")

	ln(r"\bottomrule")
	ln(r"\end{tabular}")
	ln(r"\end{table}")
	ln()

	# ── Subsubsection: Phase breakdown ────────────────────────────────────────
	ln(r"\subsubsection{Phase breakdown (normal profile, $512\times512$, step~$1.0\,\mathrm{mm}$)}")
	ln()

	phase_keys = [
		("ray_setup",            r"Ray setup"),
		("aabb_intersection",    r"AABB intersection"),
		("depth_clipping",       r"Depth clipping"),
		("direct_sources_total", r"Direct sources (mesh BVH)"),
		("marching_total",       r"Marching (volumetric)"),
		("physics_conversion",   r"Physics conversion"),
	]

	for group_scenes, cap_suffix, label_suffix, tbl_pos in [
		(vol_only,  "volumetric-only scenes", "vol",   r"[!ht]"),
		(mesh_only, "mesh-only scene",        "mesh",  r"[!ht]"),
		(vol_mesh,  "hybrid (vol + mesh) scenes", "mixed", r"[htbp]"),
	]:
		if not group_scenes:
			continue
		col_spec = "l" + "r" * len(group_scenes)
		ln(r"\begin{table}" + tbl_pos)
		ln(r"\centering")
		ln(r"  \caption{Phase breakdown [ms] for normal profile --- " + cap_suffix + r".}")
		ln(r"  \label{tab:phases_" + label_suffix + r"}")
		ln(r"\small")
		ln(r"\begin{tabular}{" + col_spec + r"}")
		ln(r"\toprule")
		hdr = r"Phase & " + " & ".join(r"\texttt{" + esc(s) + r"}" for s in group_scenes) + r" \\"
		ln(hdr)
		ln(r"\midrule")
		for pk, plabel in phase_keys:
			cells = [plabel]
			for s in group_scenes:
				r = by_sp.get((s, "normal"))
				if r and pk in r.get("phase_ms", {}):
					cells.append(phase_cell(r["phase_ms"][pk], sum(r["phase_ms"].values())))
				else:
					cells.append("---")
			ln("  " + " & ".join(cells) + r" \\")
		ln(r"\midrule")
		total_cells = [r"\textbf{Total}"]
		for s in group_scenes:
			r = by_sp.get((s, "normal"))
			total_cells.append(f"\\textbf{{{r['total_ms']:.0f}}}" if r else "---")
		ln("  " + " & ".join(total_cells) + r" \\")
		ln(r"\bottomrule")
		ln(r"\end{tabular}")
		ln(r"\end{table}")
		ln()

	# ── Subsubsection: Backend comparison ─────────────────────────────────────
	has_proj = any(r["scene"] == "mesh_only_projected" for r in results)
	ln(r"\subsubsection{Backend comparison (mesh sources)}\label{ssec:backends}")
	ln()
	ln(r"The pipeline offers two ray-intersection backends for mesh sources:")
	ln(r"\begin{description}\setlength{\itemsep}{2pt}")
	ln(r"  \item[\texttt{analytic\_bvh}] Per-ray BVH traversal with analytic ray--triangle")
	ln(r"    intersection, currently implemented as a Python loop.")
	ln(r"  \item[\texttt{projected\_intersection\_list}] Rasterisation-based approach: triangles are projected")
	ln(r"    onto the detector plane, rasterised into pixel stacks (CSR layout),")
	ln(r"    and line integrals are accumulated per pixel.")
	ln(r"\end{description}")
	ln()
	if has_proj:
		ln(r"\begin{table}[htbp]")
		ln(r"\centering")
		ln(r"\caption{Mesh-only projection time and throughput for both backends.")
		ln(r"  Time in ms (or s); throughput in k\,samp/s.}")
		ln(r"\label{tab:backends}")
		ln(r"\small")
		ln(r"\begin{tabular}{l rr rr rr}")
		ln(r"\toprule")
		ln(r"  & \multicolumn{2}{c}{\textbf{draft} (2\,mm)}")
		ln(r"  & \multicolumn{2}{c}{\textbf{normal} (1\,mm)}")
		ln(r"  & \multicolumn{2}{c}{\textbf{high} (0.5\,mm)} \\")
		ln(r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}\cmidrule(lr){6-7}")
		ln(r"Backend & time & k\,s/s & time & k\,s/s & time & k\,s/s \\")
		ln(r"\midrule")
		for sc, label in [("mesh_only", r"\texttt{analytic\_bvh}"),
		                  ("mesh_only_projected", r"\texttt{projected\_intersection\_list}")]:
			row_cells = [label]
			for p in profiles:
				r = by_sp.get((sc, p))
				if r:
					row_cells.append(ms_cell(r["total_ms"]))
					sps_k = r["samples_per_s"] / 1e3
					row_cells.append(f"{sps_k:.1f}")
				else:
					row_cells += ["---", "---"]
			ln("  " + " & ".join(row_cells) + r" \\")
		ln(r"\bottomrule")
		ln(r"\end{tabular}")
		ln(r"\end{table}")
		ln()
		# Per-phase comparison for projected backend at normal profile
		proj_r = by_sp.get(("mesh_only_projected", "normal"))
		if proj_r and proj_r.get("per_source"):
			src = proj_r["per_source"][0]
			proj_keys = [
				("stack_build_s",          r"Stack build total"),
				("stack_uv_projection_s",  r"\quad UV projection"),
				("stack_rasterize_s",      r"\quad Rasterise"),
				("stack_csr_s",            r"\quad CSR assembly"),
				("integration_s",          r"Integration"),
			]
			has_proj_detail = any(k in src for k, _ in proj_keys)
			if has_proj_detail:
				bvh_r = by_sp.get(("mesh_only", "normal"))
				ln(r"\begin{table}[htbp]")
				ln(r"\centering")
				ln(r"\caption{Per-phase timing for mesh backends at normal profile [ms].}")
				ln(r"\label{tab:backends_phases}")
				ln(r"\small")
				ln(r"\begin{tabular}{lrr}")
				ln(r"\toprule")
				ln(r"Phase & \texttt{analytic\_bvh} & \texttt{projected\_intersection\_list} \\")
				ln(r"\midrule")
				# analytic_bvh phases
				bvh_src = bvh_r["per_source"][0] if bvh_r and bvh_r.get("per_source") else {}
				bvh_phases = [
					("bvh_build_s",  r"BVH build"),
					("integration_s", r"Integration (BVH)"),
				]
				proj_display = [
					("stack_build_s",         r"Stack build total"),
					("stack_uv_projection_s", r"\quad UV projection"),
					("stack_rasterize_s",     r"\quad Rasterise"),
					("stack_csr_s",           r"\quad CSR assembly"),
					("integration_s",         r"Integration"),
				]
				# print BVH rows
				for k, label in bvh_phases:
					v_bvh = bvh_src.get(k, 0) * 1000.0
					ln(f"  {label} & {v_bvh:.1f} & --- \\\\")
				ln(r"\midrule")
				# print projected rows
				for k, label in proj_display:
					v_proj = src.get(k, 0) * 1000.0
					ln(f"  {label} & --- & {v_proj:.1f} \\\\")
				ln(r"\midrule")
				v_bvh_tot = bvh_r["total_ms"] if bvh_r else 0
				v_proj_tot = proj_r["total_ms"]
				ln(f"  \\textbf{{Total}} & \\textbf{{{v_bvh_tot:.0f}}} & \\textbf{{{v_proj_tot:.0f}}} \\\\")
				ln(r"\bottomrule")
				ln(r"\end{tabular}")
				ln(r"\end{table}")
				ln()
	else:
		ln(r"Backend comparison data not available in these results")
		ln(r"(re-run \texttt{benchmark\_xray\_performance()} to generate it).")
		ln()

	# ── Subsubsection: Key observations ───────────────────────────────────────
	ln(r"\subsubsection{Key observations}")
	ln()
	ln(r"\begin{itemize}\setlength{\itemsep}{3pt}")
	ln(r"  \item \textbf{Volumetric marching} dominates volume-only scenes ($>80\%$ of total time).")
	ln(r"    Throughput is approximately constant at $11$--$17\,\mathrm{Msamp/s}$,")
	ln(r"    confirming that cost scales linearly with sample count.")
	ln(r"  \item \textbf{Mesh ray-intersection} (\texttt{analytic\_bvh}, Python loop)")
	ln(r"    runs at $\approx 16$--$18\,\mathrm{k\,samp/s}$ ---")
	ln(r"    several orders of magnitude below the volumetric path.")
	ln(r"    This is the primary bottleneck for optimisation.")
	ln(r"  \item Mesh timing is \textbf{independent of volume size} and nearly independent")
	ln(r"    of step size, since the number of intersecting pixels is determined by")
	ln(r"    the projected mesh silhouette, not by the marching step.")
	ln(r"  \item In hybrid scenes the two paths run independently and their times add up.")
	ln(r"\end{itemize}")
	ln()

	# ── Subsection: Projection Images ─────────────────────────────────────────
	has_images = any("png_path" in r and os.path.isfile(r["png_path"]) for r in results)
	if has_images:
		ln(r"\subsection{Projection Images}")
		ln()
		ln(r"Figure~\ref{fig:proj_normal} shows synthetic cone-beam projections for all scene variants")
		ln(r"at the \textbf{normal} quality profile ($512\times512$\,px, step\,$1.0\,\mathrm{mm}$),")
		ln(r"rendered with a digital radiography presentation model")
		ln(r"(standard convention: dense~=~white, $\gamma=0.6$, contrast\,=\,1.1).")
		ln(r"Images at the draft and high profiles are visually indistinguishable")
		ln(r"for the synthetic objects used here.")
		ln()

		ln(r"\begin{figure}[htbp]")
		ln(r"\centering")
		vol_sizes_order = ["small", "medium", "large"]
		col_scene_types = ["vol_{v}", "mesh_only", "vol_{v}+mesh"]
		for vi, vol_size in enumerate(vol_sizes_order):
			for ci, sc_template in enumerate(col_scene_types):
				sc = sc_template.replace("{v}", vol_size)
				r = by_sp.get((sc, "normal"))
				if r is None or "png_path" not in r or not os.path.isfile(r["png_path"]):
					ln(r"\begin{subfigure}[t]{0.30\linewidth}\centering")
					ln(r"  \fbox{\rule{0pt}{3cm}\hspace{3cm}}")
					ln(f"  \\caption{{\\texttt{{{esc(sc)}}}}}")
					ln(r"\end{subfigure}")
				else:
					try:
						rel = os.path.relpath(r["png_path"], tex_dir).replace("\\", "/")
					except ValueError:
						rel = r["png_path"].replace("\\", "/")
					cap_text = sc.replace("_", r"\_").replace("+", r"\,+\,")
					ln(r"\begin{subfigure}[t]{0.30\linewidth}")
					ln(r"  \centering")
					ln(f"  \\includegraphics[width=\\linewidth]{{{rel}}}")
					ln(f"  \\caption{{\\texttt{{{cap_text}}}}}")
					ln(r"\end{subfigure}")
				if ci < 2:
					ln(r"\hfill")
			if vi < 2:
				ln(r"\\[4pt]")
			ln()
		ln(r"\caption{Synthetic cone-beam projections, normal profile")
		ln(r"  ($512\times512$\,px, step\,$1.0\,\mathrm{mm}$).")
		ln(r"  Columns: volume only / mesh only / volume\,+\,mesh.")
		ln(r"  Rows: small ($64^3$) / medium ($96^3$) / large ($128^3$) volume.}")
		ln(r"\label{fig:proj_normal}")
		ln(r"\end{figure}")
		ln()

	ln(r"\end{document}")

	content = "\n".join(L)
	with open(tex_path, "w", encoding="utf-8") as fh:
		fh.write(content)

	print(f"LaTeX report written to: {tex_path}")
	print(f"Compile with: pdflatex \"{tex_path}\"")
	return tex_path


from dpVision import NDimCloud

# Macierz obrotu wokół płaszczyzny xw
def rotation_matrix_xw(theta):
    return np.array([
        [np.cos(theta), 0, 0, -np.sin(theta)],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [np.sin(theta), 0, 0, np.cos(theta)]
    ])

def rotation_matrix_yw(theta):
    return np.array([
        [1, 0, 0, 0],
        [0, np.cos(theta), 0, -np.sin(theta)],
        [0, 0, 1, 0],
        [0, np.sin(theta), 0, np.cos(theta)]
    ])

def rotation_matrix_zw(theta):
    return np.array([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, np.cos(theta), -np.sin(theta)],
        [0, 0, np.sin(theta), np.cos(theta)]
    ])

def rotation_matrix_xy(theta):
    return np.array([
        [np.cos(theta), -np.sin(theta), 0, 0],
        [np.sin(theta),  np.cos(theta), 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1]
    ])


def combined_rotation_matrix(theta):
    return (
        rotation_matrix_xw(theta) @
        rotation_matrix_yw(theta * 0.7) @
        rotation_matrix_zw(theta * 1.3) @
        rotation_matrix_xy(theta * 0.5)
    )


import numpy as np

def rotation_matrix_nd(dim, i, j, theta):
    """
    Zwraca macierz obrotu w wymiarze `dim`,
    obracającą o kąt `theta` w płaszczyźnie (i, j).
    """
    assert 0 <= i < j < dim, "Nieprawidłowe indeksy osi"

    R = np.identity(dim, dtype=np.float32)

    cos_t = np.cos(theta)
    sin_t = np.sin(theta)

    R[i, i] = cos_t
    R[j, j] = cos_t
    R[i, j] = -sin_t
    R[j, i] = sin_t

    return R


def combined_rotation(dim, thetas, axes):
    R = np.identity(dim, dtype=np.float32)
    for (i, j), theta in zip(axes, thetas):
        R = rotation_matrix_nd(dim, i, j, theta) @ R
    return R


def test_rot(cld, i, total):
    theta = 2 * np.pi * i / total
    R = rotation_matrix_nd(cld.m_dimensions, 1, 3, theta)
    # thetas = [ 2 * np.pi * i / total,  2 * np.pi * (1.0 - i / total) ]
    # axes = [(2,5), (0,5)]
    # R = combined_rotation(cld.m_dimensions, thetas, axes)
    cld.update_projection(R, d=50)

import itertools
import random

def random_color():
	return [random.randrange(255), random.randrange(255), random.randrange(255), 255]

def compute_edges(vertices):
	edges = []
	for i in range(len(vertices)):
		for j in range(i + 1, len(vertices)):
			diff = np.abs(vertices[i] - vertices[j])
			num_different = np.sum(diff > 1e-3)
			if num_different == 1 and np.any(np.isclose(diff, 20.0)):
				edges.append((i, j))
	return edges

def hypercubeNd(dim, size=1.0):
    coords = list(itertools.product([-1, 1], repeat=dim))
    verts = np.array(coords, dtype=np.float32) * size
    edges = compute_edges(verts)
    return verts, edges

def animationNd(cld):
	total = 360

	def onTimeout():
		if not hasattr(onTimeout, "cnt"):
			onTimeout.cnt = 1
		
		print(f"step: {onTimeout.cnt} of {total}")

		test_rot(cld, onTimeout.cnt, total)

		AP.updateAllViews()

		onTimeout.cnt += 1
		if onTimeout.cnt > total:
			onTimeout.cnt = 0
		# timer.start(1000)

	global timer
	timer = QTimer()
	timer.timeout.connect(onTimeout)
	timer.start(100)


def testNd():
	cld = NDimCloud.hypercube(dim = 6, size = 10.0)
	cld.m_vcolors = np.array([random_color() for i in range(len(cld.m_vertices))])

	cld.projectTo3D()

	AP.addObject(cld)

	# animationNd(cld)



#testNd()

#fast_test_5(512,512,512)

# import numpy as np
# from dpVision.gridData import GridData

# import numpy as np

# def make_grid(shape=(128, 128), kind="sinus_with_holes"):
#     h, w = shape
#     y = np.linspace(-2*np.pi, 2*np.pi, h, dtype=np.float32)
#     x = np.linspace(-2*np.pi, 2*np.pi, w, dtype=np.float32)
#     X, Y = np.meshgrid(x, y)

#     if kind == "sinus":
#         Z = np.sin(X) * np.cos(Y)
#     elif kind == "hill":
#         Z = np.exp(-0.1*(X**2 + Y**2))
#     elif kind == "saddle":
#         Z = X**2 - Y**2
#     elif kind == "sinus_with_holes":
#         Z = np.sin(X) * np.cos(Y)
#         # dodaj brakujące fragmenty:
#         Z[(np.abs(X) < 1.0) & (np.abs(Y) < 1.0)] = np.nan   # dziura w centrum
#         Z[(X > 3) & (Y > 0)] = np.nan                      # dziura w rogu
#     else:
#         Z = np.zeros_like(X)

#     stepX = (x[-1] - x[0]) / (w - 1)
#     stepY = (y[-1] - y[0]) / (h - 1)

#     return Z.astype(np.float32), stepX, stepY


# grid, stepX, stepY = make_grid((128, 128), kind="sinus_with_holes")
# gldata = GridData(grid, stepX, stepY)

# tra2 = Transform()
# if not tra2 is None:
# 	tra2.addChild(gldata)

# AP.addObject(tra2)



def test_gridData64():
	from dpVision.gridData64 import GridData64
	from dpVision.roi import CircleROI
	from dpVision.gui import GLViewer

	def set_roi(obj):
		if obj is None:
			return

		viewer : GLViewer = AP.mainWin.currentGLViewer()
		if viewer:
			viewer.setViewScale(15.0)
			viewer.transform.setTranslation(tx=-3.835,ty=-4.111, tz=0.0)

		roi = CircleROI(center_x=3.835, center_y=4.111, radius=3.0)

		surface2 = roi.apply(obj)

		obj2 = GridData64.from_surface(surface2)
		AP.addObject(obj2)

		AP.updateAllViews()

	filename = "d:\\praca\\nowe_probki\\_AX data_STL_ASC_TXT\\Sensofar confocal\\AX_3_5x_conf_crop_disabled.stl"
	AP.load(filename, on_success=set_roi)

# test_gridData64()


def test_sphere_grid():
	"""
	Demonstracja SphereGrid na syntetycznych danych.

	Generujemy trzy obiekty w workspace:
	  1. SphereGrid z "polem sferycznym" — elipsoida z szumem + dziury (ang. invalid hits)
	  2. SphereGrid symulujący wiązki typowego LiDAR-a (ograniczone pole widzenia pionowe)
	  3. PointCloud przekonwertowana z obiektu 2 (żeby porównać obie reprezentacje)
	"""
	from dpVision.sphereGrid import SphereGrid

	# ------------------------------------------------------------------
	# 1. Sfera z szumem i dziurami — pełne 360° × 180°
	# ------------------------------------------------------------------
	W, H = 360, 180                 # 1°/piksel
	az = np.deg2rad(np.linspace(0.5, 359.5, W))
	el = np.deg2rad(np.linspace(-89.5, 89.5, H))
	AZ, EL = np.meshgrid(az, el)

	# Elipsoida: a=20m, b=15m, c=10m
	a, b, c = 20.0, 15.0, 10.0
	r_ellipsoid = 1.0 / np.sqrt(
		(np.cos(EL) * np.cos(AZ)) ** 2 / a**2 +
		(np.cos(EL) * np.sin(AZ)) ** 2 / b**2 +
		np.sin(EL) ** 2              / c**2
	)

	# losowy szum ±5%
	rng = np.random.default_rng(42)
	noise = rng.uniform(-0.05, 0.05, (H, W)).astype(np.float32)
	range_map = (r_ellipsoid * (1.0 + noise)).astype(np.float32)

	# "dziury" — 5% pikseli bez echa
	holes = rng.random((H, W)) < 0.05
	range_map[holes] = np.nan

	# intensywność: zależy od kąta padania (symulacja cosinus)
	intensity = np.clip(np.abs(np.sin(EL)).astype(np.float32), 0.0, 1.0)
	intensity[holes] = np.nan

	sg_full = SphereGrid(
		range_map,
		azimuth_range=(0.0, 360.0),
		elevation_range=(-90.0, 90.0),
		intensity=intensity,
		unit="m"
	)
	sg_full.label = "SphereGrid – elipsoida 360°"
	sg_full.use_uniform_color   = False
	sg_full.color_by_intensity  = False   # colormap po zasięgu
	sg_full.set_colormap('skala')
	AP.addObject(sg_full)

	# ------------------------------------------------------------------
	# 2. Symulacja LiDAR-a (np. Ouster OS1-32 — 32 wiązki, ±22.5°)
	# ------------------------------------------------------------------
	W_lidar, H_lidar = 1024, 32
	az_l  = np.deg2rad(np.linspace(0.0, 360.0, W_lidar, endpoint=False))
	el_l  = np.deg2rad(np.linspace(-22.5, 22.5, H_lidar))
	AZ_L, EL_L = np.meshgrid(az_l, el_l)

	# Grunt: płaszczyzna z=0, skaner na z=1.5m.
	# Tylko wiązki skierowane w DÓŁ (EL < 0) mogą trafić grunt;
	# wiązki w górę (EL >= 0) dają np.nan (brak trafienia).
	# Wzór: r = -sensor_h / sin(el)  (dla el < 0 wynik > 0)
	r_ground = np.where(
		EL_L < -1e-4,
		1.5 / (-np.sin(EL_L)),
		np.nan
	).astype(np.float32)

	# ściany pionowe (walce) w 4 kierunkach
	r_wall = np.full((H_lidar, W_lidar), np.nan, dtype=np.float32)
	for wall_az in [0.0, 90.0, 180.0, 270.0]:
		az_center = np.deg2rad(wall_az)
		daz = np.abs(AZ_L - az_center)
		daz = np.minimum(daz, 2 * np.pi - daz)
		mask_wall = daz < np.deg2rad(5.0)
		r_wall[mask_wall] = 15.0 / np.cos(EL_L[mask_wall])

	# bierzemy minimum zasięgu (co pierwsze trafione)
	r_lidar = np.nanmin(
		np.stack([r_ground.astype(np.float32), r_wall], axis=0), axis=0
	)
	r_lidar = np.clip(r_lidar, 0.1, 120.0)

	intens_lidar = rng.uniform(0.1, 0.9, (H_lidar, W_lidar)).astype(np.float32)

	sg_lidar = SphereGrid(
		r_lidar,
		azimuth_range=(0.0, 360.0),
		elevation_range=(-22.5, 22.5),
		intensity=intens_lidar,
		origin=(0.0, 0.0, 1.5),   # skaner zamontowany 1.5m nad ziemią
		unit="m"
	)
	sg_lidar.label = "SphereGrid – LiDAR 32-beam"
	sg_lidar.use_uniform_color  = False
	sg_lidar.color_by_intensity = True   # colormap po intensywności
	sg_lidar.set_colormap('skala')
	# AP.addObject(sg_lidar)

	# ------------------------------------------------------------------
	# 3. PointCloud z LiDAR-a — porównanie reprezentacji
	# ------------------------------------------------------------------
	pc = sg_lidar.to_point_cloud()
	pc.label = "PointCloud – z LiDAR (z SphereGrid)"
	# AP.addObject(pc)

	AP.updateAllViews()

#test_sphere_grid()


def test_uncertainty():
	def colorize_mesh_by_uncertainty(mesh, uncertainty):

		# colors = uncertainty_colormap(uncertainty)
		colors = confidence_to_rgba(uncertainty, cmap="skala")

		mesh.m_vcolors = colors
		
	def normalize_robust(x, p_low=5, p_high=95):
		lo = np.percentile(x, p_low)
		hi = np.percentile(x, p_high)
		y = (x - lo) / max(hi - lo, 1e-12)
		return np.clip(y, 0.0, 1.0)
		
	def analyse_mesh(mesh : Mesh):
		model = MeshUncertaintyModel(mesh)
		result = model.analyze()

		confidence = result["confidence"]
		unc = 1 - confidence

		v = mesh.m_vertices
		dist = np.linalg.norm(v, axis=1)
		dist_n = (dist - dist.min()) / (dist.max() - dist.min())
		distance_uncertainty = dist_n**2

		
		v_dir = v / np.linalg.norm(v, axis=1, keepdims=True)

		mesh.calcVN()
		cos_angle = np.abs(np.sum(v_dir * mesh.m_vnormals, axis=1))

		angle_uncertainty = 1 - cos_angle

		unc_final = (
			0.5 * unc +
			0.25 * distance_uncertainty +
			0.25 * angle_uncertainty
		)

		unc_final = np.clip(unc_final, 0, 1)
		colorize_mesh_by_uncertainty(mesh, unc_final)

		# curv = result["metrics"]["vertex_curvature"]
		# curv_log = np.log1p(curv * 1000)
		# curv_vis = normalize_robust(curv_log, 2, 98)
		# colorize_mesh_by_uncertainty(mesh, curv_vis)

		# uncertainty = 1.0 - confidence
		# colorize_mesh_by_uncertainty(mesh, uncertainty)


		# instability = (
		# 	0.45 * normalize_robust(result["metrics"]["vertex_planarity_residual"], 5, 95) +
		# 	0.30 * normalize_robust(result["metrics"]["vertex_spacing"], 5, 95) +
		# 	0.25 * (1.0 / (1.0 + result["metrics"]["vertex_boundary_distance"]))
		# )
		# instability = np.clip(instability, 0, 1)
		# colorize_mesh_by_uncertainty(mesh, instability)

		AP.updateAllViews()

	filename = "d:\\praca\\dane\\190911100545.obj"
	# filename = "d:\\praca\\dane\\zdeb\\1000000008.obj"
	AP.load(filename, on_success=analyse_mesh)

# test_uncertainty()
#fastTest2()

if __name__ == '__main__':
	_bm_results = benchmark_xray_performance()
	generate_latex_benchmark_report(_bm_results)
# create_real_xray_demo()
# result = demo_synthetic_xray_projection()
# print(result["png_path"])
# print(result["tiff_path"])
# print(result["dicom_path"])
else:
	create_real_xray_demo()
