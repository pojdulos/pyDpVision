# -*- coding: utf-8 -*-
"""
Created on Wed Nov 22 11:08:03 2023

@author: pojdulos
"""

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from dpVision import AP, PluginInterface, Parser, BaseObject, Transform, GridData64
from dpVision.parsers import ParserCSV
from .profileViewer import ProfileViewer

import weakref
import numpy as np

import numpy as np

def make_distance_map_fast(grid1: GridData64, grid2: GridData64, transform: np.ndarray,
						mode="bilinear", max_dist=None) -> GridData64:
	h, w = grid1.h, grid1.w
	stepX, stepY = grid1.stepX, grid1.stepY

	# współrzędne w grid1
	xs = grid1.offsetX + np.arange(w) * stepX
	ys = grid1.offsetY + np.arange(h) * stepY
	X, Y = np.meshgrid(xs, ys)

	Z = grid1.m_grid64

	transform = np.linalg.inv(transform)
	
	# flatten
	pts = np.stack([X.ravel(), Y.ravel(), Z.ravel(), np.ones_like(Z).ravel()], axis=1)
	pts_t = (transform @ pts.T).T  # (N,4)

	px, py, pz = pts_t[:,0], pts_t[:,1], pts_t[:,2]

	# współrzędne w grid2
	gx = (px - grid2.offsetX) / grid2.stepX
	gy = (py - grid2.offsetY) / grid2.stepY

	valid = (
		np.isfinite(pz) &
		(gx >= 0) & (gy >= 0) &
		(gx < grid2.w-1) & (gy < grid2.h-1)
	)

	gx, gy, pz = gx[valid], gy[valid], pz[valid]
	ix, iy = np.floor(gx).astype(int), np.floor(gy).astype(int)
	dx, dy = gx - ix, gy - iy

	if mode == "nearest":
		z_interp = grid2.m_grid64[iy, ix]
	else:  # bilinear
		z11 = grid2.m_grid64[iy, ix]
		z21 = grid2.m_grid64[iy, ix+1]
		z12 = grid2.m_grid64[iy+1, ix]
		z22 = grid2.m_grid64[iy+1, ix+1]
		z_interp = (
			z11*(1-dx)*(1-dy) +
			z21*dx*(1-dy) +
			z12*(1-dx)*dy +
			z22*dx*dy
		)

	dist = np.full(Z.shape, np.nan, dtype=np.float64)
	dist.ravel()[valid] = pz - z_interp

	# --- ograniczenie maksymalnej odległości ---
	if max_dist is not None:
		#mask = np.abs(dist) > max_dist
		mask = (dist <= 0) # max_dist
		dist[mask] = np.nan   # albo np.clip(dist, -max_dist, max_dist) jeśli chcesz "przyciąć"

	return GridData64(dist, stepX=stepX, stepY=stepY)


class Frasta(PluginInterface):
	def __init__(self):
		self.plugin_name = '(dp) Frasta'
		self.panel = None
		self.scale_transform = None
		self.adj_transform = None
		self.ref_grid = None
		self.adj_grid = None

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

		layout = QFormLayout()
		layout.addRow(refresh_button)
		layout.addRow("Ref:", self.selref)
		layout.addRow("Adj:", self.seladj)
		layout.addRow(swap_button)
		layout.addRow(rotY_button)
		layout.addRow(alignBB_button)
		layout.addRow(profile_button)
		layout.addRow(map_button)
		
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

	def onAction_profile_view(self):
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
		map = make_distance_map_fast(self.ref_grid, self.adj_grid,
							self.adj_transform.toNumPy(), mode="bilinear", max_dist=50.0)
		map.use_uniform_color = False
		AP.addObject(map, self.scale_transform)

	def onAction_UnLoad(self):
		print("Akcja menu: Wyładuj plugin")
		AP.mainApp.unload_plugin(self)
		
		
	def perform_action(self):
		print("Akcja wykonana przez "+self.plugin_name)

	def on_button1(self):
		#QMessageBox.information(self.mainWindow, 'Komunikat', 'Akcja wykonana przez '+self.plugin_name)
		pass
