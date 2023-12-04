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
from dpVision.PropAnnotation import PropAnnotation
from dpVision.PropAnnotationPoint import PropAnnotationPoint
from dpVision.PropAnnotationSphere import PropAnnotationSphere
from dpVision.Annotation import Annotation
from dpVision.Object import Object

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

		self.addWidgetToScrollArea(self.m_widget)
	
	@pyqtSlot(QObject)	
	def selectionChanged( self, obj ):
		name = obj.__class__.__name__
		print(name+" selected")
		
		if name == 'GLViewer':
			self.m_widget = PropViewer.create(obj, self)
		elif obj.hasCategory(Object):
			if name == 'Transform':
				self.m_widget = PropTransform.create(obj, self)
			elif name == 'Mesh':
				self.m_widget = PropMesh.create(obj, self)
			else:
				self.m_widget = PropBaseObject.create(obj, self)
		elif obj.hasCategory(Annotation):
			if name == 'AnnotationPoint':
				self.m_widget = PropAnnotationPoint.create(obj, self)
			elif name == 'AnnotationSphere':
				self.m_widget = PropAnnotationSphere.create(obj, self)
			else:
				self.m_widget = PropAnnotation.create(obj, self)
		else:
			self.m_widget = PropWidget()

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
    