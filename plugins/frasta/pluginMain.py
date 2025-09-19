# -*- coding: utf-8 -*-
"""
Created on Wed Nov 22 11:08:03 2023

@author: pojdulos
"""

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from dpVision import AP, PluginInterface, Parser, BaseObject
from dpVision.parsers import ParserCSV
from .profileViewer import ProfileViewer

import weakref
import numpy as np

class Frasta(PluginInterface):
	def __init__(self):
		self.plugin_name = '(dp) Frasta'
		self.panel = None

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

		profile_button = QPushButton("Profile view")
		profile_button.clicked.connect(self.onAction_profile_view)

		layout = QFormLayout()
		layout.addRow(refresh_button)
		layout.addRow("Ref:", self.selref)
		layout.addRow("Adj:", self.seladj)
		layout.addRow(swap_button)
		layout.addRow(rotY_button)
		layout.addRow(profile_button)
		
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
		if old_obj is not None:
			grid_data = old_obj.m_data[0]
			grid_data.uniform_color = [0.6,0.6,0.6]

		new_obj = new() if new else None
		if new_obj is not None:
			new_obj.setScale(0.005, 0.005, 0.005)
			grid_data = new_obj.m_data[0]
			grid_data.uniform_color = [0.0,1.0,0.0]

		# odblokuj wszystkie w drugim
		for i in range(self.seladj.count()):
			if self.seladj.model().item(i) is not None:
				self.seladj.model().item(i).setEnabled(True) 

		# zablokuj aktualnie wybrane w ref
		if idx >= 0 and self.seladj.model().item(idx) is not None:
			self.seladj.model().item(idx).setEnabled(False)

		AP.mainWin.update()
		AP.updateAllViews()


	def on_adj_changed(self, idx):
		# new = self.seladj.itemData(idx, role=0) or self.seladj.currentText()
		new = self.seladj.itemData(idx)
		old = self._old_adj
		self._old_adj = new

		print(f"ADJ: old={old}, new={new}")

		old_obj = old() if old else None
		if old_obj is not None:
			grid_data = old_obj.m_data[0]
			grid_data.uniform_color = [0.6,0.6,0.6]

		new_obj = new() if new else None
		if new_obj is not None:
			new_obj.setScale(0.005, 0.005, 0.005)
			grid_data = new_obj.m_data[0]
			grid_data.uniform_color = [0.0,0.0,1.0]

		# odblokuj wszystkie w pierwszym
		for i in range(self.selref.count()):
			if self.selref.model().item(i) is not None:
				self.selref.model().item(i).setEnabled(True)

		# zablokuj aktualnie wybrane w adj
		if idx >= 0 and self.selref.model().item(idx) is not None:
			self.selref.model().item(idx).setEnabled(False)

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

	def onAction_profile_view(self):
		ref = self.selref.itemData(self.selref.currentIndex())
		adj = self.seladj.itemData(self.seladj.currentIndex())

		if ref is None or adj is None:
			return

		self._old_adj = None
		self._old_ref = None	

		ref_obj = ref().m_data[0]
		adj_obj = adj().m_data[0]
		grid1 = ref_obj.m_grid64
		grid2 = adj_obj.m_grid64

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
			ref_obj.stepX, ref_obj.stepY,
			adj_obj.stepX, adj_obj.stepY
		)
		self._profile_viewer.show()
		self._profile_viewer.raise_()
		self._profile_viewer.activateWindow()

	def onAction_RotY(self):
		ref = self.seladj.currentData()
		obj = ref() if ref else None
		if obj is None:
			print("No object selected in Adj")
			return
		else:
			print(f"Selected object in Adj: {obj.label}")
		
		#if not isinstance(obj, BaseObject):
		#	print("Selected object is not a BaseObject")
	
	
		grid_data = obj.m_data[0]
		grid_data.m_grid64 = np.flipud(grid_data.m_grid64)
		grid_data.m_grid64 = -grid_data.m_grid64
		grid_data.upload_to_gpu()

		#print("Akcja menu: Nowy graf")
		# self.graphs.append( Graph( rows=self.edit1.value(), cols=self.edit2.value() ) )
		# AP.mainWin.workspace.m_data.append(self.graphs[-1])
		# AP.mainWin.dock["workspace"].addNewItem(self.graphs[-1])
		AP.mainWin.update()
		AP.updateAllViews()


	def onAction_UnLoad(self):
		print("Akcja menu: Wyładuj plugin")
		AP.mainApp.unload_plugin(self)
		
		
	def perform_action(self):
		print("Akcja wykonana przez "+self.plugin_name)

	def on_button1(self):
		#QMessageBox.information(self.mainWindow, 'Komunikat', 'Akcja wykonana przez '+self.plugin_name)
		pass
