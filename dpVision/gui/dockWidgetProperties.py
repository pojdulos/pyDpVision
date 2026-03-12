# -*- coding: utf-8 -*-

"""
Created on Thu Nov 23 13:51:54 2023

@author: pojdulos
"""
from PyQt5.QtCore import *
from PyQt5.QtWidgets import QDockWidget, QSizePolicy, QScrollArea,QVBoxLayout
from PyQt5 import uic

from .propVolumetric import PropVolumetric
from .propMotion import PropMotion
from .propWidget import PropWidget
from .propViewer import PropViewer
from .propBaseObject import PropBaseObject
from .propMesh import PropMesh
from .propNDimCloud import PropNDimCloud
from .propTransform import PropTransform
from .propAnnotation import PropAnnotation
from .propAnnotationPlane import PropAnnotationPlane
from .propAnnotationPoint import PropAnnotationPoint
from .propAnnotationSphere import PropAnnotationSphere
from .propGridData64 import PropGridData64
from .propSphereGrid import PropSphereGrid
from .propDHJoint import PropDHJoint

from .. import BaseObject, Object, Annotation, AP

class DockWidgetProperties(QDockWidget):
	object_updated = pyqtSignal(QObject)

	def __init__(self, parent):
		super().__init__(parent)
		#uic.loadUi('dpVision/gui/forms/dockWidgetProperties.ui', self)
		AP.loadUi('dockWidgetProperties.ui', self)
		
		self.m_scroll = QScrollArea()
	
		policy = self.m_scroll.sizePolicy()
	
		policy.setVerticalStretch(1)
		policy.setHorizontalStretch(1)
	
		self.m_layout = QVBoxLayout(self.m_scroll)
	
		self.setWidget(self.m_scroll)
	
		self.m_widget = PropWidget()

		
		self.properties_map = {
			Object: {
				'Transform': PropTransform,
				'DHJoint': PropDHJoint,
				'Mesh' : PropMesh,
				#'PointCloud' : PropMesh,
				'GridData64' : PropGridData64,
				'SphereGrid' : PropSphereGrid,
				'NDimCloud': PropNDimCloud,
				'Motion': PropMotion,
				'Volumetric': PropVolumetric,
				'default': PropBaseObject,
			},
			Annotation: {
				'AnnotationPlane': PropAnnotationPlane,
				'AnnotationPoint': PropAnnotationPoint,
				'AnnotationSphere': PropAnnotationSphere,
				'default': PropAnnotation,
			},
			BaseObject: {
				'default': PropBaseObject
			},
		}

		self.addWidgetToScrollArea(self.m_widget)
	
	@pyqtSlot(QObject)	
	def selectionChanged( self, obj ):
		name = obj.__class__.__name__
		#print(name+" selected")

		if name == 'GLViewer':
			self.m_widget = PropViewer.create(obj, self)
		else:
			not_found = True
			for category in self.properties_map.keys():
				if obj.hasCategory(category):
					if name in self.properties_map[category].keys():
						self.m_widget = self.properties_map[category][name].create(obj, self)
					else:
						self.m_widget = self.properties_map[category]['default'].create(obj, self)
					not_found = False
					break
			if not_found:
				self.m_widget = PropWidget()

		self.m_widget.object_updated.connect(self.on_object_updated_by_widget)
		self.addWidgetToScrollArea(self.m_widget)
		self.updateProperties()

	@pyqtSlot(QObject)
	def on_object_updated_by_widget(self, obj):
		print('DockWidgetProperties.on_object_updated_by_widget()')
		self.object_updated.emit(obj)

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
    