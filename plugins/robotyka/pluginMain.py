# -*- coding: utf-8 -*-
"""
Created on Wed Nov 22 11:08:03 2023

@author: pojdulos
"""

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from dpVision import AP, PluginInterface
from dpVision import AP, DHJoint

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

		action = QAction("Load JSON", AP.mainWin)
		self.menu.addAction(action)
		action.triggered.connect(self.onAction_loadJSON)

		action = QAction("Add joint", AP.mainWin)
		self.menu.addAction(action)
		action.triggered.connect(self.onAction_newDHJoint)

		self.menu.addSeparator()
		
		# action = QAction("Show model", AP.mainWin)
		# self.menu.addAction(action)
		# action.triggered.connect(self.onAction_ShowModel)

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

	# def onAction_ShowModel(self):
	# 	from .hand_demo import poses, build_scene_from_dh_dictionary, prepare_animation
	# 	from .hand_model import hand_model
	# 	self.joints = build_scene_from_dh_dictionary(hand_model)
	# 	self.animation = prepare_animation(self.joints, poses, duration_ms=700, fps=30, loop=True)

	def get_selected_dhjoint(self):
		tmp = AP.mainWin.dock["workspace"].getSelectedObjects()
		for obj in tmp:
			if isinstance(obj, DHJoint):
				return obj
		return None
	
	def onAction_Start(self):
		if self.animation is None:
			from .hand_demo import poses, prepare_animation
			joint = self.joints if self.joints else self.get_selected_dhjoint()
			if joint is None:
				QMessageBox.information(AP.mainWin, 'Info', 'Select a DHJoint to animate.')
				return
			
			def	get_child_joints_dict(joint):
				joints={}
				joints[joint.label] = joint
				for child in joint.children():
					tmp = get_child_joints_dict(child)
					for k,v in tmp.items():
						joints[k] = v
				return joints
			
			joint_dict = get_child_joints_dict(joint)
			
			self.animation = prepare_animation(joint_dict, poses, duration_ms=700, fps=30, loop=True)	
		
			if self.animation:
				self.animation.start()

	def onAction_Stop(self):
		if self.animation:
			self.animation.stop()

	def onAction_newDHJoint(self):
		joint = DHJoint()
		AP.addObject(joint)



	def build_model(self, m):
		# for key, value in m['meta'].items():
		# 	print(f"{key}: {value}")

		angle_unit = m['meta'].get('angle_unit','deg')
		convention = m['meta'].get('convention','classical')
		scheme = m['meta'].get('scheme','joints-only')
		length_unit = m['meta'].get('length_unit','mm')
		version = m['meta'].get('version','1.0')

		joints = {}
		for j in m['joints']:
			joint = DHJoint(
						joint_type=j['type'],
				    	angle_unit=angle_unit,
						theta=j['theta'],
						d=j['d'],
						a=j['a'],
						alpha=j['alpha'],
						name = j['name']
					)

			limits = j.get('limits', None)
			if limits:
				if j['type']=='revolute':
					joint.theta_limits = limits
				elif j['type']=='prismatic':
					joint.d_limits = limits

			joints[j['name']] = joint

		# Ustaw rodziców
		model = []
		for j in m['joints']:
			joint = joints[j['name']]
			parent_name = j['parent_joint']
			if not parent_name is None and parent_name in joints:
				parent_joint = joints[parent_name]
				parent_joint.addChild(joint)
			else:
				model.append(joint)
		return model

	def load_JSON_model(self, filename):
		import json
		import os
		try:
			model = open(filename).read()
		except FileNotFoundError:
			script_dir = os.path.dirname(os.path.abspath(__file__))
			try:
				model = open(os.path.join(script_dir, filename)).read()
			except FileNotFoundError:
				raise FileNotFoundError(f"File {filename} not found in the current directory or script directory.")
		return json.loads(model)

	def onAction_loadJSON(self):
		filename, _ = QFileDialog.getOpenFileName(AP.mainWin, "Open JSON Model", "", "JSON Files (*.json);;All Files (*)")
		if filename:
			model_data = self.load_JSON_model(filename)
			model = self.build_model(model_data)
			for joint in model:
				AP.addObject(joint)
			AP.updateAllViews()
