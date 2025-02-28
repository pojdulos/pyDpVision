# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 20:40:37 2023

@author: darek
"""

#from abc import ABC, abstractmethod
#from PyQt5 import uic
from PyQt5.QtCore import *
from PyQt5.QtWidgets import * #QWidget, QVBoxLayout, QSizePolicy

class PropWidget(QWidget):
	object_updated = pyqtSignal(QObject)

	def __init__(self, parent=None):
		super( PropWidget, self ).__init__( parent )

	def get_subwidgets(self):
		# Tworzymy listę pól będących instancjami QWidget
		return [attr for attr in vars(self).values() if isinstance(attr, QWidget)]

	def updateProperties(self):
		for i in self.findChildren(PropWidget):
			i.updateProperties()


	@pyqtSlot(QObject)
	def on_object_updated_by_subwidget(self, obj):
		self.object_updated.emit(obj)

	@staticmethod
	def build(content, parent=None):
		widget = PropWidget(parent)
		#widget = QStackedWidget(parent)
		layout = QVBoxLayout(widget)
		# QFormLayout* layout = new QFormLayout(widget);

		for subwidget in content:
			subwidget.object_updated.connect(widget.on_object_updated_by_subwidget)
			layout.addWidget( subwidget )
	
		widget.resize(layout.sizeHint())
		widget.setMinimumSize(layout.sizeHint())
		widget.setMaximumSize(layout.sizeHint())
	
		widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
	
		return widget

