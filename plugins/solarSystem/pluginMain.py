# -*- coding: utf-8 -*-
"""
Created on Wed Nov 22 11:08:03 2023

@author: pojdulos
"""

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from dpVision import AP, PluginInterface, AnnotationSphere, AnnotationPath, Transform
from .celestialBody import CelestialBody
from .planet import Planet
from .moon import Moon
from .planets_data import planets_data, sun_data
import numpy as np

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
		self.create_solar_system()



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

	# def get_moon_orbit_gain(self, moon:Moon):
	# 	planet_name = moon.parent.name
	# 	if planet_name == "Mars":
	# 		moon_orbit_gain = position_gain * size_gain * 10.0 #1000.0
	# 	elif planet_name == "Ziemia":
	# 		moon_orbit_gain = position_gain * size_gain * 0.5 #50.0
	# 	else:
	# 		moon_orbit_gain = position_gain * size_gain * 0.5 #100.0
	# 	return moon_orbit_gain

	# def get_moon_pos(self, moon:Moon, delta_years=0.0):
	# 	pos_rel = moon.position_relative(delta_years)
	# 	moon_orbit_gain = self.get_moon_orbit_gain(moon)
	# 	moon_pos = pos_rel * moon_orbit_gain * position_gain
	# 	return moon_pos

	def get_moon_pos(self, moon: Moon, delta_years=0.0):
		"""
		Zwraca pozycję księżyca w układzie planety (AU → jednostki sceny).
		Uwzględnia przesunięcie nad powierzchnią planety i globalne skalowanie.
		"""
		# Pozycja księżyca względem planety w jednostkach AU
		pos_rel = moon.position_visual_relative(delta_years)

		# Stałe przeliczniki (można ewentualnie regulować)
		moon_orbit_gain = 0.5
		offset = moon.parent.size * 2.0  # odsunięcie orbity od powierzchni planety

		# Korekta pozycji o offset w kierunku promienia orbity
		direction = pos_rel / np.linalg.norm(pos_rel)
		pos_rel = pos_rel + direction * offset

		# Przeliczenie do jednostek sceny
		return pos_rel * moon_orbit_gain


	# def move_planet(self, planet:Planet, delta_years):
	# 	planet_transform = self.visual_objects[planet.name][0]
	# 	moons_dict = self.visual_objects[planet.name][2]
		
	# 	planet_pos = planet.visual_position(delta_years)
	# 	planet_transform.setTranslation(*planet_pos)
		
	# 	for moon in planet.moons:
	# 		moon_pos = self.get_moon_pos(moon, delta_years=delta_years)
	# 		moons_dict[moon.name].setTranslation(*moon_pos)

	def move_planet(self, planet, delta_years):
		planet_transform, _, moons = self.visual_objects[planet.name]

		# Planeta
		planet_pos = planet.visual_position(delta_years)
		planet_transform.setTranslation(*planet_pos)

		# Księżyce (względem planety)
		for moon in planet.moons:
			moon_rel = moon.position_visual_relative(delta_years)
			moons[moon.name].setTranslation(*moon_rel)

	def create_moon(self, moon:Moon):
		moon_sphere = AnnotationSphere()
		moon_sphere.radius = moon.size
		moon_sphere.m_color = QColor(moon.color)
		moon_sphere.label = f"sfera ({moon.name})"

		moon_transform = Transform()

		moon_pos = self.get_moon_pos(moon)
		moon_transform.setTranslation(*moon_pos)

		moon_transform.addChild(moon_sphere)
		moon_transform.label = moon.name
		moon_transform.locked = True
		return moon_transform

	def create_planet(self, planet:Planet):
		planet_sphere = AnnotationSphere()
		planet_sphere.radius = planet.size
		planet_sphere.m_color = QColor(planet.color)
		planet_sphere.label = f"sfera ({planet.name})"

		planet_transform = Transform()
		planet_transform.label = planet.name
		planet_transform.locked = True
		
		planet_pos = planet.visual_position(0.0)
		planet_transform.setTranslation(*planet_pos)

		planet_transform.addChild(planet_sphere)

		points = [pt for pt in planet.orbit_points()]
		planet_path = AnnotationPath(points)
		planet_path.label = f"orbita ({planet.name})"

		moons = dict()
		for moon in planet.moons:
			moon_transform = self.create_moon(moon)

			print(f"{planet.name}: dodaję {moon.name}")
			
			moons[moon.name] = moon_transform
			planet_transform.addChild(moon_transform)

		return (planet_transform, planet_path, moons)

	def create_solar_system(self):
		# ================== budowa układu ==================
		# --- tworzymy Słońce jako główny obiekt ---
		self.sun = CelestialBody(**sun_data)

		sun_sphere = AnnotationSphere()
		sun_sphere.position = self.sun.position(0.0)
		sun_sphere.radius = self.sun.size
		sun_sphere.m_color = QColor(self.sun.color)
		sun_sphere.label = self.sun.name

		AP.addObject(sun_sphere)

		self.visual_objects = dict()
		self.solar_system = [Planet(parent=self.sun, **p) for p in planets_data]
		for planet in self.solar_system:
			planet_transform, planet_path, moons = self.create_planet(planet)
			
			self.visual_objects[planet.name] = (planet_transform, planet_path, moons)

			AP.addObject(planet_transform)
			AP.addObject(planet_path)


	def on_button1(self):
		from datetime import datetime, timedelta
		J2000 = datetime(2000, 1, 1, 12)
		
		def onTimeout():
			if not hasattr(onTimeout, "date"):
				onTimeout.date = J2000
			else:
				onTimeout.date += timedelta(hours=6)

			delta_days = (onTimeout.date - J2000).total_seconds() / 86400.0
			delta_years = delta_days / 365.25

			self.date_label.setText(onTimeout.date.strftime("%Y-%m-%d"))

			for planet in self.solar_system:
				self.move_planet(planet, delta_years)

			AP.updateAllViews()

		self.timer = QTimer()
		self.timer.timeout.connect(onTimeout)
		self.timer.start(50)
