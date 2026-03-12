from dpVision import AP, Transform, Image, AnnotationPoint, AnnotationSphere, AnnotationPath

from PyQt5.QtCore import QTimer

from dpVision.meshUncertaintyModel import MeshUncertaintyModel, colorize_mesh_by_confidence, uncertainty_colormap
from dpVision.volumetric import Volumetric

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

	obj = AnnotationSphere()
	if not obj is None:
		AP.mainWin.workspace.m_data.append(obj)
		AP.mainWin.dock["workspace"].addNewItem(obj)
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

from dpVision import NDimCloud
import numpy as np

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
	AP.addObject(sg_lidar)

	# ------------------------------------------------------------------
	# 3. PointCloud z LiDAR-a — porównanie reprezentacji
	# ------------------------------------------------------------------
	pc = sg_lidar.to_point_cloud()
	pc.label = "PointCloud – z LiDAR (z SphereGrid)"
	AP.addObject(pc)

	AP.updateAllViews()

# test_sphere_grid()


def test_uncertainty():
	def colorize_mesh_by_uncertainty(mesh, uncertainty):

		colors = uncertainty_colormap(uncertainty)

		mesh.m_vcolors = colors
		
	def normalize_robust(x, p_low=5, p_high=95):
		lo = np.percentile(x, p_low)
		hi = np.percentile(x, p_high)
		y = (x - lo) / max(hi - lo, 1e-12)
		return np.clip(y, 0.0, 1.0)
		
	def analyse_mesh(mesh):
		model = MeshUncertaintyModel(mesh)
		result = model.analyze()

		# curv = result["metrics"]["vertex_curvature"]
		# curv_log = np.log1p(curv * 1000)
		# curv_vis = normalize_robust(curv_log, 2, 98)
		# colorize_mesh_by_uncertainty(mesh, curv_vis)

		confidence = result["confidence"]
		uncertainty = 1.0 - confidence
		colorize_mesh_by_uncertainty(mesh, uncertainty)

		AP.updateAllViews()

	# filename = "d:\\praca\\dane\\190911100545.obj"
	filename = "d:\\praca\\dane\\zdeb\\1000000008.obj"
	AP.load(filename, on_success=analyse_mesh)

test_uncertainty()
