# -*- coding: utf-8 -*-
"""
Created on Wed Nov 22 11:08:03 2023

@author: pojdulos
"""

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from dpVision import AP, PluginInterface, AnnotationSphere, AnnotationPath, Transform
from .celestialBody import ORBIT_SCALE, PLANET_SIZE_SCALE, REAL_SIZE, CelestialBody
from .planet import Planet
from .moon import Moon
from .planets_data import planets_data, sun_data
import numpy as np


def generate_ring_paths(planet, n_levels=40, n_points=100, color="#d8c6a5"):
	def _rot_z(vec, deg):
		a = np.deg2rad(deg); c, s = np.cos(a), np.sin(a)
		x, y, z = vec
		return np.array([c*x - s*y, s*x + c*y, z])

	def _rot_x(vec, deg):
		a = np.deg2rad(deg); c, s = np.cos(a), np.sin(a)
		x, y, z = vec
		return np.array([x, c*y - s*z, s*y + c*z])

	# inner_AU = getattr(planet, "ring_inner_AU", None)
	# outer_AU = getattr(planet, "ring_outer_AU", None)
	# if inner_AU is None or outer_AU is None:
	# 	return []

	# # --- Skalowanie AU → scena ---
	# base = PLANET_SIZE_SCALE if REAL_SIZE else 1.0
	# inner = inner_AU * base
	# outer = outer_AU * base

	inner = planet.ring_inner_visual
	outer = planet.ring_outer_visual
	if inner is None or outer is None:
		return []

	# --- Orientacja pierścieni = orientacja równika planety (super ważne!) ---
	spin_node = getattr(planet, "spin_node_deg", 0.0)
	obliq     = getattr(planet, "obliquity_deg", 0.0)

	def rz(v, a): return _rot_z(v, a)
	def rx(v, a): return _rot_x(v, a)

	rings = []
	r = inner
	step = (outer - inner) / max(1, n_levels - 1)
	for _ in range(n_levels):
		pts = []
		for k in range(n_points):
			ang = 2*np.pi * k / n_points
			p = np.array([r*np.cos(ang), r*np.sin(ang), 0.0])
			p = rz(rx(p, obliq), spin_node)
			pts.append(p)

		path = AnnotationPath(pts)
		path.m_color = QColor(color)
		path.label = f"pierścień ({planet.name})"
		rings.append(path)
		r += step

	return rings

# def generate_ring_paths2(planet, n_levels=40, n_points=100, color="#d8c6a5"):
# 	def _rot_z(vec, deg):
# 		a = np.deg2rad(deg); c, s = np.cos(a), np.sin(a)
# 		x, y, z = vec
# 		return np.array([c*x - s*y, s*x + c*y, z])

# 	def _rot_x(vec, deg):
# 		a = np.deg2rad(deg); c, s = np.cos(a), np.sin(a)
# 		x, y, z = vec
# 		return np.array([x, c*y - s*z, s*y + c*z])

# 	inner_AU = getattr(planet, "ring_inner_AU", None)
# 	outer_AU = getattr(planet, "ring_outer_AU", None)
# 	if inner_AU is None or outer_AU is None:
# 		return []

# 	base = ORBIT_SCALE if REAL_SIZE else 1.0
# 	inner = inner_AU * base
# 	outer = outer_AU * base

# 	# chroń przed „zjedzeniem” przez planetę
# 	R_planet = planet.visual_radius()
# 	inner = max(inner, R_planet * 1.2)

# 	spin_node = getattr(planet, "spin_node_deg", 0.0)
# 	obliq     = getattr(planet, "obliquity_deg", 0.0)

# 	rings = []
# 	for level in range(n_levels):
# 		r = inner + (outer - inner) * (level / max(1, n_levels - 1))
# 		pts = []
# 		for k in range(n_points):
# 			ang = 2*np.pi * k / n_points
# 			p = np.array([r*np.cos(ang), r*np.sin(ang), 0.0])
# 			# osadzenie w płaszczyźnie równika planety (J2000)
# 			p = _rot_z(_rot_x(p, obliq), spin_node)
# 			pts.append(p)
# 		path = AnnotationPath(pts)
# 		path.m_color = QColor(color)
# 		path.label = f"pierścień ({planet.name})"
# 		rings.append(path)
# 	return rings

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
		moon_sphere.radius = moon.visual_radius()
		moon_sphere.m_color = QColor(moon.color)
		moon_sphere.label = f"sfera ({moon.name})"

		moon_transform = Transform()
		moon_transform.label = moon.name
		moon_transform.locked = True

		# Początkowa pozycja (relatywna do planety)
		moon_pos = moon.position_visual_relative(0.0)
		moon_transform.setTranslation(*moon_pos)

		moon_transform.addChild(moon_sphere)

		# 🌙🌀 ORBITA KSIĘŻYCA
		moon_orbit = AnnotationPath(moon.orbit_points_visual())
		moon_orbit.label = f"orbita ({moon.name})"
		moon_orbit.m_color = QColor("#888888")  # możesz dobrać kolor/typ

		# orbita jest także dzieckiem planety (tak jak księżyc)
		#moon_transform.addChild(moon_orbit) #planety a nie księżyca - dodaje się w create_planet

		return moon_transform, moon_orbit

	def create_planet(self, planet:Planet):
		planet_sphere = AnnotationSphere()
		planet_sphere.radius = planet.visual_radius()
		planet_sphere.m_color = QColor(planet.color)
		planet_sphere.label = f"sfera ({planet.name})"

		planet_transform = Transform()
		planet_transform.label = planet.name
		planet_transform.locked = True
		
		planet_pos = planet.visual_position(0.0)
		planet_transform.setTranslation(*planet_pos)

		planet_transform.addChild(planet_sphere)

		# Dodaj pierścienie, jeśli planeta je ma
		ring_paths = generate_ring_paths(planet)
		for ring in ring_paths:
			planet_transform.addChild(ring)

		points = [pt for pt in planet.orbit_points()]
		planet_path = AnnotationPath(points)
		planet_path.label = f"orbita ({planet.name})"

		moons = dict()
		for moon in planet.moons:
			moon_transform, moon_orbit = self.create_moon(moon)

			print(f"{planet.name}: dodaję {moon.name}")
			
			moons[moon.name] = moon_transform
			planet_transform.addChild(moon_orbit)
			planet_transform.addChild(moon_transform)

		return (planet_transform, planet_path, moons)

	def create_solar_system(self):
		# ================== budowa układu ==================
		# --- tworzymy Słońce jako główny obiekt ---
		self.sun = CelestialBody(**sun_data)

		sun_sphere = AnnotationSphere()
		sun_sphere.position = self.sun.position(0.0)
		sun_sphere.radius = self.sun.visual_radius()
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
				onTimeout.date += timedelta(hours=24)

			delta_days = (onTimeout.date - J2000).total_seconds() / 86400.0
			delta_years = delta_days / 365.25

			self.date_label.setText(onTimeout.date.strftime("%Y-%m-%d"))

			for planet in self.solar_system:
				self.move_planet(planet, delta_years)

			AP.updateAllViews()

		self.timer = QTimer()
		self.timer.timeout.connect(onTimeout)
		self.timer.start(100)
