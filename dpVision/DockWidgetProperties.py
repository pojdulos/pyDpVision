# -*- coding: utf-8 -*-

"""
Created on Thu Nov 23 13:51:54 2023

@author: pojdulos
"""
from PyQt5.QtCore import QObject, pyqtSlot
from PyQt5.QtWidgets import QDockWidget, QSizePolicy, QScrollArea,QVBoxLayout
from PyQt5 import uic
from dpVision.PropWidget import PropWidget
from dpVision.PropViewer import PropViewer
from dpVision.PropBaseObject import PropBaseObject
from dpVision.PropMesh import PropMesh
from dpVision.PropTransform import PropTransform

class DockWidgetProperties(QDockWidget):
	def __init__(self, parent):
		super().__init__(parent)
		uic.loadUi('dpVision/ui/UiDockWidgetProperties.ui', self)
		
		self.m_scroll = QScrollArea()
	
		policy = self.m_scroll.sizePolicy()
	
		policy.setVerticalStretch(1)
		policy.setHorizontalStretch(1)
	
		self.m_layout = QVBoxLayout(self.m_scroll)
	
		self.setWidget(self.m_scroll)
	
		self.m_widget = PropWidget()

		self.addWidgetToScrollArea(self.m_widget);
	
	@pyqtSlot(QObject)	
	def selectionChanged( self, obj ):
		if obj.__class__.__name__ == 'GLViewer':
			print("GLViewer selected")
			self.m_widget = PropViewer.create(obj, self)
		elif obj.__class__.__name__ == 'Transform':
			print("Transform selected")
			self.m_widget = PropTransform.create(obj, self)
		elif obj.__class__.__name__ == 'Mesh':
			print("Mesh selected")
			self.m_widget = PropMesh.create(obj, self)
		elif obj.__class__.__name__ == 'BaseObject' or obj.__class__.__name__ == 'Object':
			print("BaseObject selected")
			self.m_widget = PropBaseObject.create(obj, self)
		else:
			print("Any object selected")
			self.m_widget = None
		self.addWidgetToScrollArea(self.m_widget)
		self.updateProperties()

	def updateProperties(self):
		if not self.m_widget is None:
			self.m_widget.updateProperties()
		self.update()

	def addWidgetToScrollArea(self, widget):
		if not widget is None:
			widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
			adjustSize = widget.size()
			widget.setMinimumSize(adjustSize)
	
		self.m_scroll.setWidgetResizable(True)
		self.m_scroll.setWidget(widget)


	def loadPlugin(self):
		pass
    
	def runSelectedPlugin(self):
		pass
    
	def removeSelectedPlugin(self):
		pass
    
	def currentItemChanged(self):
		pass
    