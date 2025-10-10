# -*- coding: utf-8 -*-
"""
Created on Wed Nov 22 11:08:03 2023

@author: pojdulos
"""

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from dpVision import AP, PluginInterface, AnnotationSphere, AnnotationPath
from .celestialBody import CelestialBody, Planet, Moon, years_since_j2000, rotate_z_x
from .planets_data import planets_data, sun_data

position_gain = 100.0
size_gain = 2.0

class SolarSystem(PluginInterface):
	def __init__(self):
		self.plugin_name = '(dp) Solar system demo'
		self.panel = None

	def on_load(self):
		print( "plugin "+self.plugin_name+" loaded.")
		
		# self.mainWindow.helpAbout()
		self.add_menu()
		self.create_panel(AP.mainWin)

		self.use_compression = True

		# ================== budowa układu ==================
		# --- tworzymy Słońce jako główny obiekt ---
		self.sun = CelestialBody(**sun_data)
		self.sunanno = AnnotationSphere()
		self.sunanno.position = self.sun.position(0.0) * position_gain
		self.sunanno.radius = self.sun.size * size_gain
		self.sunanno.m_color = QColor(self.sun.color)
		self.sunanno.label = self.sun.name
		AP.addObject(self.sunanno)

		self.solar_system = [Planet(parent=self.sun, **p) for p in planets_data]
		self.anno = dict()
		self.path = dict()
		self.moonanno = dict()
		for planet in self.solar_system:
			points = [pt * position_gain for pt in planet.orbit_points()]
			self.path[planet.name] = AnnotationPath(points)
			self.path[planet.name].label = f"{planet.name} (orbita)"
			AP.addObject(self.path[planet.name])#, self.sunanno)
			
			self.anno[planet.name] = AnnotationSphere()
			planet_pos = planet.visual_position(0.0, position_gain)
			self.anno[planet.name].position = planet_pos
			self.anno[planet.name].radius = planet.size * size_gain
			self.anno[planet.name].m_color = QColor(planet.color)
			self.anno[planet.name].label = planet.name
			AP.addObject(self.anno[planet.name])#, self.sunanno)
			# if planet.name == "Ziemia":
			for moon in planet.moons:
				self.moonanno[moon.name] = AnnotationSphere()

				if planet.name == "Mars":
					moon_orbit_gain = position_gain * size_gain * 10.0 #1000.0
				elif planet.name == "Ziemia":
					moon_orbit_gain = position_gain * size_gain * 0.5 #50.0
				else:
					moon_orbit_gain = position_gain * size_gain * 0.5 #100.0

				moon_pos = moon.visual_position(0.0, position_gain, moon_orbit_gain)
				self.moonanno[moon.name].position = moon_pos

				self.moonanno[moon.name].radius = moon.size * size_gain
				self.moonanno[moon.name].m_color = QColor(moon.color)
				self.moonanno[moon.name].label = moon.name
				print(f"{planet.name}: dodaję {moon.name}")
				AP.addObject(self.moonanno[moon.name])#,self.anno[planet.name])
			# 	print(f"   {moon.name:8s}: {moon.position(t)}")


	def create_panel(self, parent):
		self.panel = QDockWidget(parent)
		self.panel.setWindowTitle(self.plugin_name)
		AP.mainWin.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.panel)
		self.button1 = QPushButton("Start")
		self.button1.clicked.connect(self.on_button1)
		self.date_label = QLabel()

		layout = QFormLayout()
		layout.addRow(self.button1)
		layout.addRow(self.date_label)
		
		central_widget = QWidget()
		central_widget.setLayout(layout)
		self.panel.setWidget(central_widget)

	def on_unload(self):
		self.remove_menu()
		if self.panel:
			AP.mainWin.removeDockWidget(self.panel);    
		print( "Bye bye")
		
	def add_menu(self):
		nadrzedne_menu = self.add_plugins_menu()

		self.menu = QMenu("SolarSystem", AP.mainWin)
		
		nadrzedne_menu.addMenu(self.menu)
		
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
				if action.text() == "SolarSystem" and action.menu():
					plugin_menu_action = action
					break
			
			if plugin_menu_action:
				nadrzedne_menu.removeAction(plugin_menu_action)
		
		self.remove_plugins_menu()
		

	def onAction_UnLoad(self):
		print("Akcja manu: Wyładuj plugin")
		AP.mainApp.unload_plugin(self)
		
		
	def perform_action(self):
		print("Akcja wykonana przez "+self.plugin_name)

			
	def on_button1(self):
		from datetime import datetime, timedelta
		J2000 = datetime(2000, 1, 1, 12)
		
		def onTimeout():
			if not hasattr(onTimeout, "date"):
				onTimeout.date = J2000
			else:
				onTimeout.date += timedelta(hours=2)

			delta_days = (onTimeout.date - J2000).total_seconds() / 86400.0
			delta_years = delta_days / 365.25

			self.date_label.setText(onTimeout.date.strftime("%Y-%m-%d"))
			#self.panel.update()

			for planet in self.solar_system:
				planet_pos = planet.visual_position(delta_years, position_gain)
				self.anno[planet.name].position = planet_pos

				if planet.name == "Mars":
					moon_orbit_gain = position_gain * size_gain * 10.0 #1000.0
				elif planet.name == "Ziemia":
					moon_orbit_gain = position_gain * size_gain * 0.5 #50.0
				else:
					moon_orbit_gain = position_gain * size_gain * 0.5 #100.0

				for moon in planet.moons:
					moon_pos = moon.visual_position(delta_years, position_gain, moon_orbit_gain)
					self.moonanno[moon.name].position = moon_pos

			AP.updateAllViews()
			#print(f"step: {onTimeout.date}, delta = {delta_years:.2f} years")

		print("start timer")

		self.timer = QTimer()
		self.timer.timeout.connect(onTimeout)
		self.timer.start(50)
