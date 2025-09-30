# -*- coding: utf-8 -*-
"""
Created on Wed Nov 22 11:08:03 2023

@author: pojdulos
"""

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from dpVision import AP, PluginInterface, Transform, GridData64
from dpVision.annotationPlane import AnnotationPlane
from dpVision.parsers import ParserCSV
from .profileViewer import ProfileViewer
from .frastaViewer import FrastaViewer

import weakref
import numpy as np

from .mappings import *

class Frasta(PluginInterface):
	def __init__(self):
		self.plugin_name = '(dp) Frasta'
		self.panel = None
		self.scale_transform = None
		self.adj_transform = None
		self.ref_grid = None
		self.adj_grid = None
		self.ref_abc = None
		self.ref_plane = AnnotationPlane()
		self.distance_map = None

	def on_load(self):
		print( f"plugin {self.plugin_name} loaded.")
		
		#AP.mainWin.load_file("d:/praca/frasta/source_data/3-0a x5 conf.dat")
		#AP.mainWin.load_file("d:/praca/frasta/source_data/3-0b x5 conf.dat")
		# self.mainWindow.helpAbout()
		self.add_menu()
		self.create_panel(AP.mainWin)

	def create_panel(self, parent):
		self.panel = QDockWidget(parent)
		self.panel.setWindowTitle(self.plugin_name)

		refresh_button = QPushButton("refresh")
		refresh_button.clicked.connect(self.onAction_refresh_refsel)

		self.selref = QComboBox()
		self.seladj = QComboBox()
		# self.edit1.setMaximum(16)
		# self.edit1.setValue(4)
		# self.edit2 = QSpinBox()
		# self.edit2.setMinimum(1)
		# self.edit2.setMaximum(16)
		# self.edit2.setValue(4)

		# śledzimy stary wybór
		self._old_ref = None
		self._old_adj = None

		self.selref.currentIndexChanged.connect(self.on_ref_changed)
		self.seladj.currentIndexChanged.connect(self.on_adj_changed)

		swap_button = QPushButton("swap")
		swap_button.clicked.connect(self.onAction_swapSelections)
	
		rotY_button = QPushButton("Y-Rotate (Adj)")
		rotY_button.clicked.connect(self.onAction_RotY)

		alignBB_button = QPushButton("Align BBs")
		alignBB_button.clicked.connect(self.onAction_align_bboxes)

		profile_button = QPushButton("Profile view")
		profile_button.clicked.connect(self.onAction_profile_view)

		map_button = QPushButton("test map")
		map_button.clicked.connect(self.onAction_test_map)

		ransac_button = QPushButton("ransac test")
		ransac_button.clicked.connect(self.onAction_ransac)



		layout = QFormLayout()
		layout.addRow(refresh_button)
		layout.addRow("Ref:", self.selref)
		layout.addRow("Adj:", self.seladj)
		layout.addRow(swap_button)
		layout.addRow(rotY_button)
		layout.addRow(alignBB_button)
		layout.addRow(profile_button)
		layout.addRow(map_button)
		layout.addRow(ransac_button)
		
		central_widget = QWidget()
		central_widget.setLayout(layout)
		self.panel.setWidget(central_widget)
		
		AP.mainWin.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.panel)

	def on_ref_changed(self, idx):
		# new = self.selref.itemData(idx, role=0) or self.selref.currentText()
		new = self.selref.itemData(idx)
		old = self._old_ref
		self._old_ref = new
		print(f"REF: old={old}, new={new}")

		old_obj = old() if old else None
		if old_obj is not None and self.ref_grid is not None:
			self.ref_grid.uniform_color = [0.6,0.6,0.6]
			old_obj.addChild(self.ref_grid)

		new_obj = new() if new else None
		if new_obj is not None:
			self.ref_grid = new_obj.m_data[0]
			self.ref_grid.uniform_color = [0.0,1.0,0.0]
			self.scale_transform.addChild(self.ref_grid)

		# odblokuj wszystkie w drugim
		for i in range(self.seladj.count()):
			if self.seladj.model().item(i) is not None:
				self.seladj.model().item(i).setEnabled(True) 

		# zablokuj aktualnie wybrane w ref
		if idx >= 0 and self.seladj.model().item(idx) is not None:
			self.seladj.model().item(idx).setEnabled(False)

		AP.mainWin.dock["workspace"].rebuildTree()
		AP.mainWin.update()
		AP.updateAllViews()


	def on_adj_changed(self, idx):
		# new = self.seladj.itemData(idx, role=0) or self.seladj.currentText()
		new = self.seladj.itemData(idx)
		old = self._old_adj
		self._old_adj = new

		print(f"ADJ: old={old}, new={new}")

		old_obj = old() if old else None
		if old_obj is not None and self.adj_grid is not None:
			self.adj_grid.uniform_color = [0.6,0.6,0.6]
			old_obj.addChild(self.adj_grid)

		new_obj = new() if new else None
		if new_obj is not None:
			self.adj_grid = new_obj.m_data[0]
			self.adj_grid.uniform_color = [0.0,0.0,1.0]
			self.adj_transform.addChild(self.adj_grid)

		# odblokuj wszystkie w pierwszym
		for i in range(self.selref.count()):
			if self.selref.model().item(i) is not None:
				self.selref.model().item(i).setEnabled(True)

		# zablokuj aktualnie wybrane w adj
		if idx >= 0 and self.selref.model().item(idx) is not None:
			self.selref.model().item(idx).setEnabled(False)

		AP.mainWin.dock["workspace"].rebuildTree()
		AP.mainWin.update()
		AP.updateAllViews()

	def on_unload(self):
		self.remove_menu()
		if self.panel:
			AP.mainWin.removeDockWidget(self.panel);	
		print( "Bye bye")
		
	def add_menu(self):
		nadrzedne_menu = self.add_plugins_menu()

		self.menu = QMenu("Frasta", AP.mainWin)
		
		nadrzedne_menu.addMenu(self.menu)

		# action = QAction("Load Ref", AP.mainWin)
		# self.menu.addAction(action)
		# action.triggered.connect(self.onAction_Load_ref)

		# action = QAction("Load Adj", AP.mainWin)
		# self.menu.addAction(action)
		# action.triggered.connect(self.onAction_Load_adj)

		action = QAction("RotY", AP.mainWin)
		self.menu.addAction(action)
		action.triggered.connect(self.onAction_RotY)
		
		action = QAction("UnLoad", AP.mainWin)
		self.menu.addAction(action)
		action.triggered.connect(self.onAction_UnLoad)
		
	def remove_menu(self):
		# Znajdź "NadrzędneMenu"
		nadrzedne_menu = None
		for action in AP.mainWin.menuBar.actions():
			if action.text() == "Plugins":
				nadrzedne_menu = action.menu()
				break
		
		if nadrzedne_menu:
			# Znajdź i usuń "Plugin01"
			plugin_menu_action = None
			for action in nadrzedne_menu.actions():
				if action.text() == "Frasta" and action.menu():
					plugin_menu_action = action
					break
			
			if plugin_menu_action:
				nadrzedne_menu.removeAction(plugin_menu_action)
		
		self.remove_plugins_menu()


	def onAction_refresh_refsel(self):
		# zapamiętaj poprzednie wybory
		old_ref = None
		old_adj = None
		if self.selref.currentIndex() >= 0:
			ref = self.selref.itemData(self.selref.currentIndex())
			if ref: 
				old_ref = ref()
		if self.seladj.currentIndex() >= 0:
			ref = self.seladj.itemData(self.seladj.currentIndex())
			if ref: 
				old_adj = ref()

		tmp = list(AP.mainWin.workspace.m_data)
		
		# tmp2 = []
		# for tt in AP.mainWin.workspace.m_data:
		# 	gtt = tt.children_by_type(GridData64)
		# 	if len(gtt) != 0:
		# 		tmp2.append(*gtt)
		# print(f"Znaleziono {len(tmp2)} obiektów GridData64: {gtt}")

		if self.scale_transform is None:
			self.scale_transform = Transform()
			self.scale_transform.label = "Frasta scale (0.01x)"
			self.scale_transform.locked = True
			self.scale_transform.setScale(0.01, 0.01, 0.01)  # skalowanie skanów
			AP.addObject(self.scale_transform)
		if self.adj_transform is None:
			self.adj_transform = Transform()
			self.adj_transform.label = "Frasta Adjusted position"
			self.adj_transform.locked = True
			AP.addObject(self.adj_transform,self.scale_transform)

		if self.scale_transform in tmp:
			tmp.remove(self.scale_transform)
		if self.adj_transform in tmp:
			tmp.remove(self.adj_transform)

		# --- odświeżenie REF ---
		self.selref.blockSignals(True)
		self.selref.clear()
		for item in tmp:
			self.selref.addItem(item.label, weakref.ref(item))
		self.selref.blockSignals(False)

		# --- odświeżenie ADJ ---
		self.seladj.blockSignals(True)
		self.seladj.clear()
		for item in tmp:
			self.seladj.addItem(item.label, weakref.ref(item))
		self.seladj.blockSignals(False)

		# --- przywracanie wyborów ---
		ref_idx = -1
		adj_idx = -1

		if old_ref and old_ref in tmp:
			for i in range(self.selref.count()):
				if self.selref.itemData(i)() is old_ref:
					ref_idx = i
					break

		if old_adj and old_adj in tmp:
			for i in range(self.seladj.count()):
				if self.seladj.itemData(i)() is old_adj:
					adj_idx = i
					break

		# fallback jeśli brak starego wyboru
		if ref_idx == -1 and len(tmp) > 0:
			ref_idx = 0

		if adj_idx == -1 and len(tmp) > 1:
			# znajdź pierwszy inny niż ref_idx
			for i in range(self.seladj.count()):
				if i != ref_idx:
					adj_idx = i
					break

		# --- ustawiamy wybory dopiero teraz ---
		self.selref.setCurrentIndex(ref_idx)
		self.seladj.setCurrentIndex(adj_idx)

		# ręczne wywołanie logiki blokowania
		if ref_idx >= 0:
			self.on_ref_changed(ref_idx)
		if adj_idx >= 0:
			self.on_adj_changed(adj_idx)

		AP.mainWin.update()
		AP.updateAllViews()

	def onAction_swapSelections(self):
		ref = self.selref.itemData(self.selref.currentIndex())
		adj = self.seladj.itemData(self.seladj.currentIndex())

		if ref is None or adj is None:
			return

		self._old_adj = None
		self._old_ref = None	

		ref_obj = ref()
		adj_obj = adj()

		# znajdź indeksy obiektów w drugim combo
		ref_idx = -1
		adj_idx = -1
		for i in range(self.selref.count()):
			if self.selref.itemData(i)() is adj_obj:
				ref_idx = i
				break
		for i in range(self.seladj.count()):
			if self.seladj.itemData(i)() is ref_obj:
				adj_idx = i
				break

		# ustaw nowe indeksy
		if ref_idx >= 0:
			self.selref.setCurrentIndex(ref_idx)
		if adj_idx >= 0:
			self.seladj.setCurrentIndex(adj_idx)

	def onAction_align_bboxes(self):
		refbb = self.ref_grid.getBB()
		adjBB = self.adj_grid.getBB()
		z_diff = refbb[2][2] - adjBB[1][2]
		self.adj_transform.translate(0.0, 0.0, 0.8*z_diff)
		AP.updateAllViews()

	def onAction_profile_view(self):
		if self.distance_map is None:
			QMessageBox.warning(
				self.panel, "Brak danych",
				"Najpierw oblicz mapę odległości."
			)
			return

		if getattr(self, "_profile_viewer", None) is None:
			self._profile_viewer = FrastaViewer(parent=AP.mainWin)

		# przekazujemy już gotowe obiekty
		self._profile_viewer.set_data(
			self.distance_map,
			self.ref_in_plane,
			self.adj_in_plane
		)

		# ustaw wstępny separation, np. z transformacji
		self._profile_viewer.spinbox_separation.setValue(
			float(self.adj_transform.getTranslation()[2])
		)

		self._profile_viewer.show()
		self._profile_viewer.raise_()
		self._profile_viewer.activateWindow()


	def onAction_profile_view_old(self):
		grid1 = self.ref_grid.m_grid64.copy()
		grid2 = self.adj_grid.m_grid64.copy()

		if grid1.shape != grid2.shape:
			h = min(grid1.shape[0], grid2.shape[0])
			w = min(grid1.shape[1], grid2.shape[1])
			reply = QMessageBox.question(
				self.panel, "Różne rozmiary",
				f"Skany mają różne rozmiary:\n"
				f"{grid1.shape} vs {grid2.shape}\n"
				f"Przyciąć oba do wspólnego obszaru {h}x{w} i kontynuować?",
				QMessageBox.Yes | QMessageBox.No
			)
			if reply != QMessageBox.Yes:
				return
			grid1 = grid1[:h, :w]
			grid2 = grid2[:h, :w]

		# -- TYLKO JEDNO OKNO --
		if getattr(self, "_profile_viewer", None) is None:
			self._profile_viewer = ProfileViewer(parent=AP.mainWin)

		self._profile_viewer.set_data(
			grid1, grid2,
			self.ref_grid.stepX, self.ref_grid.stepY,
			self.adj_grid.stepX, self.adj_grid.stepY
		)

		self._profile_viewer.spinbox_separation.setValue(int(self.adj_transform.getTranslation()[2]))

		self._profile_viewer.show()
		self._profile_viewer.raise_()
		self._profile_viewer.activateWindow()

	def onAction_RotY(self):
		if self.adj_grid is None:
			print("No object selected in Adj")
			return
	
		self.adj_grid.m_grid64 = np.flipud(self.adj_grid.m_grid64)
		self.adj_grid.m_grid64 = -self.adj_grid.m_grid64
		self.adj_grid.upload_to_gpu()

		AP.mainWin.update()
		AP.updateAllViews()


	def onAction_test_map(self):
		T_final = self.adj_transform.toNumPy()  # pełna macierz dopasowania adj→ref

		#ref_plane = self.ref_plane    # z calc_ransac
		# ref_in_plane, adj_in_plane, dist_map = resample_grids_to_plane(
		# 	self.ref_grid, self.adj_grid,
		# 	ref_plane, T_final,
		# 	mode="bilinear", max_dist=None
		# )
		# ref_in_plane.offsetX == adj_in_plane.offsetX == dist_map.offsetX
		# ref_in_plane.offsetY == adj_in_plane.offsetY == dist_map.offsetY

		
		ref_in_plane, adj_in_plane, dist_map = make_distance_map_plane(self.ref_grid, self.adj_grid,
			T_final, self.ref_abc, mode="bilinear", max_dist=None)
		

		dist_map.use_uniform_color = False

		AP.addObject(dist_map, self.scale_transform)
		AP.addObject(ref_in_plane, self.scale_transform)
		AP.addObject(adj_in_plane, self.scale_transform)
		
		self.distance_map = dist_map
		self.ref_in_plane = ref_in_plane
		self.adj_in_plane = adj_in_plane


	def onAction_ransac(self):
		crop = True

		ref_grid: GridData64 = self.ref_grid
		grid = ref_grid.m_grid64
		# --- rozdzielczości (mm/pix) ---
		sx = getattr(ref_grid, "stepX", 2.76)
		sy = getattr(ref_grid, "stepY", 2.76)
		sz = 1.0
		ref_plane, ref_abc = self.calc_ransac(grid, sx=sx, sy=sy, sz=sz, use_crop=crop)
		ref_plane.m_color=QColor(128,255,192,128)
		AP.addObject(ref_plane, self.scale_transform)
		AP.updateAllViews()

		adj_grid: GridData64 = self.adj_grid
		grid = adj_grid.m_grid64
		# --- rozdzielczości (mm/pix) ---
		sx = getattr(adj_grid, "stepX", 2.76)
		sy = getattr(adj_grid, "stepY", 2.76)
		sz = 1.0
		adj_plane, adj_abc = self.calc_ransac(grid, sx=sx, sy=sy, sz=sz, use_crop=crop)
		adj_plane.m_color=QColor(128,164,255,128)
		AP.addObject(adj_plane, self.adj_transform)
		AP.updateAllViews()

		T0 = plane_transform(adj_plane.m_center, adj_plane.m_normal,
							ref_plane.m_center, ref_plane.m_normal)

		T_refined = refine_in_plane_transform(ref_grid, adj_grid,
											ref_abc, adj_abc, T0,
											pre_theta=174.5,  # <- wstępny obrót
											angle_range=0.5,
											angle_step=0.5)

		T_final = T_refined @ T0

		self.ref_plane = ref_plane
		self.ref_abc = ref_abc
		self.adj_transform.fromNumPy(T_final)

		print(*T_final.flatten())

	def calc_ransac(self, _grid, sx=1.0, sy=1.0, sz=1.0, use_crop=False):
		grid = _grid
		h, w = grid.shape

		if use_crop:
			# --- WYCIĘCIE 500x500 WOKÓŁ ŚRODKA ---
			cx, cy = w // 2, h // 2
			r = 500
			x0, x1 = max(cx - r, 0), min(cx + r, w)
			y0, y1 = max(cy - r, 0), min(cy + r, h)

			sub = grid[y0:y1, x0:x1]
			X_px, Y_px = np.meshgrid(np.arange(x0, x1), np.arange(y0, y1))
			Z_u = sub
		else:
			# --- CAŁA SIATKA ---
			X_px, Y_px = np.meshgrid(np.arange(w), np.arange(h))
			Z_u = grid

		# Usuwamy NaN
		mask = ~np.isnan(Z_u)
		x_px = X_px[mask].ravel()
		y_px = Y_px[mask].ravel()
		z_u  = Z_u[mask].ravel()

		Xy = np.column_stack((x_px, y_px))

		from sklearn.linear_model import RANSACRegressor, LinearRegression
		ransac = RANSACRegressor(
			estimator=LinearRegression(),
			min_samples=3,
			residual_threshold=50.0,  # dopasuj do jednostek Z
			max_trials=1000,
			random_state=0
		)
		ransac.fit(Xy, z_u)

		a, b = ransac.estimator_.coef_
		c = ransac.estimator_.intercept_

		# --- PRZESKALOWANIE DO JEDNOSTEK ŚWIATA ---
		a_w = a * (sz / sx)
		b_w = b * (sz / sy)
		c_w = c * sz

		print(f"Plane (pixels-unscaled): z_u = {a:.6f}*x_px + {b:.6f}*y_px + {c:.6f}")
		print(f"Plane (world-scaled):   z   = {a_w:.6f}*x   + {b_w:.6f}*y   + {c_w:.6f}")

		# Normalna
		normal = np.array([a_w, b_w, -1.0], dtype=float)
		normal /= np.linalg.norm(normal)
		print("Normal (world):", normal)

		# Centrum płaszczyzny – zależy od trybu
		if use_crop:
			cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
		else:
			cx, cy = w // 2, h // 2

		center_world = np.array([
			sx * cx,
			sy * cy,
			a_w * (sx * cx) + b_w * (sy * cy) + c_w
		], dtype=float)

		#plane = AnnotationPlane(pC=center_world, pN=normal, size=8000)
		plane = AnnotationPlane(pC=[0,0,center_world[2]], pN=normal, size=8000)

		return plane, [a_w, b_w, c_w]


	def onAction_ransac2(self):
		ref_grid: GridData64 = self.ref_grid
		grid = ref_grid.m_grid64
		h, w = grid.shape

		# --- JEŚLI ZNASZ ROZDZIELCZOŚCI (świat na piksel/voxel) ---
		# Podstaw swoje wartości (mm/pix lub inne):
		sx = getattr(ref_grid, "spacing_x", 2.76)  # świat / piksel w osi X
		sy = getattr(ref_grid, "spacing_y", 2.76)  # świat / piksel w osi Y
		sz = getattr(ref_grid, "spacing_z", 1.0)  # świat / jednostkę Z (np. mm na jednostkę wysokości)

		# --- WYCIĘCIE 500x500 WOKÓŁ ŚRODKA ---
		cx, cy = w // 2, h // 2
		r = 500 #250  # połowa boku -> 500x500
		x0, x1 = max(cx - r, 0), min(cx + r, w)
		y0, y1 = max(cy - r, 0), min(cy + r, h)

		sub = grid[y0:y1, x0:x1]  # pamiętaj: [row, col] = [y, x]
		H, W = sub.shape

		X_px, Y_px = np.meshgrid(np.arange(x0, x1), np.arange(y0, y1))  # współrzędne w pikselach
		Z_u = sub  # Z w jednostkach oryginalnych (np. mm lub „wartość wysokości”)

		mask = ~np.isnan(Z_u)
		x_px = X_px[mask].ravel()
		y_px = Y_px[mask].ravel()
		z_u  = Z_u[mask].ravel()

		Xy = np.column_stack((x_px, y_px))

		from sklearn.linear_model import RANSACRegressor, LinearRegression
		ransac = RANSACRegressor(
			estimator=LinearRegression(),
			min_samples=3,
			residual_threshold=50.0,
			max_trials=1000,
			random_state=0
		)
		ransac.fit(Xy, z_u)

		a, b = ransac.estimator_.coef_
		c = ransac.estimator_.intercept_

		# --- PRZESKALOWANIE DO JEDNOSTEK ŚWIATA ---
		a_w = a * (sz / sx)
		b_w = b * (sz / sy)
		c_w = c * sz  # jeśli chcesz też poprawnie przesunąć w świecie

		print(f"Plane (pixels-unscaled): z_u = {a:.6f}*x_px + {b:.6f}*y_px + {c:.6f}")
		print(f"Plane (world-scaled):   z   = {a_w:.6f}*x   + {b_w:.6f}*y   + {c_w:.6f}")

		# Normalna w świecie dla z = a_w x + b_w y + c_w
		normal = np.array([a_w, b_w, -1.0], dtype=float)
		normal /= np.linalg.norm(normal)
		print("Normal (world):", normal)

		# Środek płaszczyzny ustaw w centrum wycinka (w świecie):
		center_world = np.array([sx * cx, sy * cy, a_w * (sx * cx) + b_w * (sy * cy) + c_w], dtype=float)

		from dpVision.annotationPlane import AnnotationPlane
		plane = AnnotationPlane(pC=[0,0,700], pN=normal, size=8000)

		# Uwaga: jeśli scale_transform skaluje niejednorodnie, może przekłamać normalną przy renderze.
		# Lepiej dodać bezpośrednio (albo upewnić się, że scale_transform jest jednorodny):
		AP.addObject(plane, self.scale_transform)
		AP.updateAllViews()

	def onAction_ransac1(self):
		ref_grid:GridData64 = self.ref_grid
		grid = ref_grid.m_grid64
		# h, w = grid.shape
		
		# X, Y = np.meshgrid(np.arange(w), np.arange(h))  # współrzędne siatki
		# points = np.column_stack((X.ravel(), Y.ravel(), grid.ravel()))

		# # Usuwamy punkty, gdzie Z = NaN
		# mask = ~np.isnan(points[:, 2])
		# points_clean = points[mask]


		h, w = grid.shape
		cx, cy = w // 2, h // 2   # środek siatki
		r = 500                   # promień/połowa rozmiaru wycinka w pikselach

		X, Y = np.meshgrid(np.arange(w), np.arange(h))
		points = np.column_stack((X.ravel(), Y.ravel(), grid.ravel()))

		# maska: brak NaN + ograniczenie do prostokąta wokół środka
		mask = (
			~np.isnan(points[:, 2]) &
			(np.abs(points[:, 0] - cx) < r) &
			(np.abs(points[:, 1] - cy) < r)
		)

		points_clean = points[mask]

		Xy = points_clean[:, :2]
		z  = points_clean[:, 2]

		from sklearn.linear_model import RANSACRegressor, LinearRegression

		ransac = RANSACRegressor(
			estimator=LinearRegression(),
			min_samples=3,
			residual_threshold=50.0,  # próg w jednostkach Z (dobierz do szumu/outlierów)
			max_trials=1000
		)
		ransac.fit(Xy, z)

		a, b = ransac.estimator_.coef_
		c = ransac.estimator_.intercept_

		print(f"Równanie płaszczyzny: z = {a:.4f} * x + {b:.4f} * y + {c:.4f}")

		normal = np.array([a, b, -1.0])
		normal /= np.linalg.norm(normal)
		print("Normalna:", normal)

		from dpVision.annotationPlane import AnnotationPlane

		plane = AnnotationPlane(pC=[0,0,700],pN=normal, size=8000)
		AP.addObject(plane, self.scale_transform)
		AP.updateAllViews()

	def onAction_UnLoad(self):
		print("Akcja menu: Wyładuj plugin")
		AP.mainApp.unload_plugin(self)
		
		
	def perform_action(self):
		print("Akcja wykonana przez "+self.plugin_name)

	def on_button1(self):
		#QMessageBox.information(self.mainWindow, 'Komunikat', 'Akcja wykonana przez '+self.plugin_name)
		pass
