# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 20:40:37 2023

@author: darek
"""

#from abc import ABC, abstractmethod
#from PyQt5 import uic
from PyQt5.QtCore import QRegularExpression
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSizePolicy

class PropWidget(QWidget):
	def __init__(self, parent=None):
		super( PropWidget, self ).__init__( parent )

	def updateProperties(self):
		for i in self.findChildren(PropWidget):
			i.updateProperties()
		
	@staticmethod
	def build(content, parent = 0):
		widget = PropWidget(parent)
		layout = QVBoxLayout(widget)
		# QFormLayout* layout = new QFormLayout(widget);

		for i in content:
			layout.addWidget( i )
	
		widget.resize(layout.sizeHint())
		widget.setMinimumSize(layout.sizeHint())
		widget.setMaximumSize(layout.sizeHint())
	
		widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
	
		return widget

