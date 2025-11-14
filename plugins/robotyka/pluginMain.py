# -*- coding: utf-8 -*-
"""
Created on Wed Nov 22 11:08:03 2023

@author: pojdulos
"""

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from dpVision import AP, PluginInterface

class Robotyka(PluginInterface):
	def __init__(self):
		self.plugin_name = '(dp) Testy robotów'
		self.panel = None
		self.animation = None
		self.joints = None

	def on_load(self):
		print( "plugin "+self.plugin_name+" loaded.")
		
		# self.mainWindow.helpAbout()
		self.add_menu()
		# self.create_panel(AP.mainWin)
		
		#self.onAction_ShowModel()
		#self.onAction_Start()

	def create_panel(self, parent):
		self.panel = QDockWidget(parent)
		self.panel.setWindowTitle(self.plugin_name)
		AP.mainWin.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.panel)

	def on_unload(self):
		self.remove_menu()
		if self.panel:
			AP.mainWin.removeDockWidget(self.panel);    
		print( "Bye bye")
		
	def add_menu(self):
		nadrzedne_menu = self.add_plugins_menu()

		self.menu = QMenu("Robotyka", AP.mainWin)
		
		nadrzedne_menu.addMenu(self.menu)

		action = QAction("Add joint", AP.mainWin)
		self.menu.addAction(action)
		action.triggered.connect(self.onAction_newDHJoint)

		self.menu.addSeparator()
		
		action = QAction("Show model", AP.mainWin)
		self.menu.addAction(action)
		action.triggered.connect(self.onAction_ShowModel)

		action = QAction("Start", AP.mainWin)
		self.menu.addAction(action)
		action.triggered.connect(self.onAction_Start)

		action = QAction("Stop", AP.mainWin)
		self.menu.addAction(action)
		action.triggered.connect(self.onAction_Stop)

		self.menu.addSeparator()
		
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
				if action.text() == "Robotyka" and action.menu():
					plugin_menu_action = action
					break
			
			if plugin_menu_action:
				nadrzedne_menu.removeAction(plugin_menu_action)
		
		self.remove_plugins_menu()
		

	def onAction_UnLoad(self):
		print("Akcja menu: Wyładuj plugin")
		AP.mainApp.unload_plugin(self)
		
		
	def perform_action(self):
		print("Akcja wykonana przez "+self.plugin_name)

	def on_button1(self):
		#QMessageBox.information(self.mainWindow, 'Komunikat', 'Akcja wykonana przez '+self.plugin_name)
		pass

	def onAction_ShowModel(self):
		from .hand_demo import poses, build_scene_from_dh_dictionary, prepare_animation
		from .hand_model import hand_model
		self.joints = build_scene_from_dh_dictionary(hand_model)
		self.animation = prepare_animation(self.joints, poses, duration_ms=700, fps=30, loop=True)

	def onAction_Start(self):
		if self.animation:
			self.animation.start()

	def onAction_Stop(self):
		if self.animation:
			self.animation.stop()

	def onAction_newDHJoint(self):
		from dpVision import AP, DHJoint
		joint = DHJoint()
		AP.addObject(joint)
