# -*- coding: utf-8 -*-

"""
Created on Thu Nov 23 13:51:54 2023

@author: pojdulos
"""
from PyQt5.QtWidgets import QDockWidget
from PyQt5 import uic

class DockWidgetPluginPanel(QDockWidget):
	def __init__(self, parent):
		super().__init__(parent)
		uic.loadUi('dpVision/ui/UiDockWidgetPluginPanel.ui', self)

	def showPanel(self, prev_plug, b):
		pass
	def loadPlugin(self):
		pass
    
	def runSelectedPlugin(self):
		pass
    
	def removeSelectedPlugin(self):
		pass
    
	def currentItemChanged(self):
		pass
    