import os
import numpy as np

from dpVision import AP, Transform, Image, AnnotationPoint, AnnotationSphere, AnnotationPath, VirtualXRay

from PyQt5.QtCore import QTimer

from dpVision.annotationElipsoide import AnnotationElipsoide
from dpVision.annotationPlane import AnnotationPlane
from dpVision.mesh import Mesh
from dpVision.meshUncertaintyModel import MeshUncertaintyModel, colorize_mesh_by_confidence, confidence_to_rgba, uncertainty_colormap
from dpVision.volumetric import Volumetric
from dpVision.xrayProjection import (
	XRayProjectionGeometry,
	XRayPhysicsModel,
	XRayProjectionQualityProfile,
	XRayProjectionConfig,
	RawPresentationModel,
	DigitalRadiographyPresentationModel,
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


def demo_synthetic_xray_projection(output_dir=None, jaw_translation_xyz=(0.0, -8.0, 0.0), jaw_rotation_deg_z=8.0):
	"""Generate synthetic DICOM sets and one example multi-volume X-ray projection."""
	create_synthetic_xray_demo_dicoms()
	skull, jaw = build_synthetic_xray_demo_volumes()
	if output_dir is None:
		output_dir = _demo_output_dir("xray_demo_output")
	os.makedirs(output_dir, exist_ok=True)

	skull_transform = np.eye(4, dtype=np.float32)
	jaw_transform = _make_jaw_transform(
		translation_xyz=jaw_translation_xyz,
		rotation_deg_z=jaw_rotation_deg_z,
	)

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
	"""Create one `VirtualXRay` scene node with synthetic skull and jaw descendants."""
	skull, jaw = build_synthetic_xray_demo_volumes()
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

	AP.addObject(setup)
	return setup


def create_real_xray_demo():

	"""Create one `VirtualXRay` scene node with synthetic skull and jaw descendants."""

	setup = VirtualXRay()
	setup.detector_center_ref = np.array([0, 0, 300.0], dtype=np.float32)
	setup.source_position_ref = np.array([0, 0, -1600.0], dtype=np.float32)
	setup.detector_shape_hw = [1024, 1024]
	setup.detector_pixel_size_mm = [0.2, 0.2]
	setup.step_mm = 0.5
	setup.quality_profile_name = "normal"

	AP.addObject(setup)

	def on_success(skull):
		if skull is None:
			return

		AP.removeObject(child=skull.parent)

		skull_transform = Transform()
		# skull_transform.translate(-100, 45, 0)
		skull_transform.rotate(90, [1,0,0])
		skull_transform.rotate(90, [0,1,0])
		skull_transform.addChild(skull)
		setup.addChild(skull_transform)

		AP.updateAllViews()
		AP.mainWin.dock["workspace"].rebuildTree()
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

	pathG = "d:/praca/dane/vols/gora/filtered_194.dcm"
	pathD = "d:/praca/dane/vols/dol/filtered_080.dcm"

	if os.path.isfile(pathG):
		AP.load(pathG, on_success=on_success)
	
	if os.path.isfile(pathD):
		AP.load(pathD, on_success=on_success)
	
	

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

create_real_xray_demo()
# result = demo_synthetic_xray_projection()
# print(result["png_path"])
# print(result["tiff_path"])
# print(result["dicom_path"])

