# -*- coding: utf-8 -*-

"""
Created on Thu Nov 23 13:51:54 2023

@author: pojdulos
"""
import os, sys
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import uic

from .. import AP

class DockWidgetPluginList(QDockWidget):
	def __init__(self, parent):
		super().__init__(parent)
		#uic.loadUi('dpVision/gui/forms/dockWidgetPluginList.ui', self)
		AP.loadUi('dockWidgetPluginList.ui', self)

	def addPluginToList(self, plugin_instance, txt):
		item = QListWidgetItem( txt, self.listPlugins )
		item.setData(Qt.UserRole, plugin_instance)
			
		self.listPlugins.addItem( item )


	def loadPlugin(self):
		sciezka_pliku = os.path.realpath(__file__)
		sciezka_katalogu = os.path.dirname(sciezka_pliku)
		
		fileName = QFileDialog.getOpenFileName(
				self, "Load plugin", sciezka_katalogu + "/../plugins",
				"Main plugin file (PluginMain.py)" )[0]
		
		fileName = QDir.toNativeSeparators( fileName )

		dirName = os.path.dirname( fileName )
		baseDirName = os.path.basename(dirName)

		plugins_root = QDir.toNativeSeparators(os.path.dirname(dirName))
		if plugins_root not in sys.path:
			sys.path.append(plugins_root)
		AP.mainApp.load_plugin( baseDirName, fileName );    

	def runSelectedPlugin(self):
		pass
    
	def removeSelectedPlugin(self):
		lista = self.listPlugins.selectedItems()
		if not lista: return
		for item in lista:
			plugin_instance = item.data(Qt.UserRole)
			self.listPlugins.takeItem(self.listPlugins.row(item))
			AP.mainApp.unload_plugin( plugin_instance )

	# QListWidgetItem *curr, QListWidgetItem *prev
	def currentItemChanged(self, curr, prev):
		if prev:
			prev_plug = prev.data(Qt.UserRole)
			
			AP.mainWin.dock["panel"].showPanel(prev_plug, False)
			prev_plug.on_deactivate()
			AP.mainApp.activePlugin = None

		if curr:
			curr_plug = curr.data(Qt.UserRole )
			
			AP.mainWin.dock['panel'].showPanel( curr_plug, True )
			AP.mainApp.activePlugin = curr_plug
			curr_plug.on_activate()
    