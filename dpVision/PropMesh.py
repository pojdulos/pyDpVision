# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 20:40:37 2023

@author: darek
"""

from abc import ABC, abstractmethod
from PyQt5 import uic

from dpVision.PropWidget import PropWidget
from dpVision.PropBaseObject import PropBaseObject
from dpVision.Mesh import Mesh

class PropMesh(PropWidget):
	def __init__(self, _obj, parent=None):
		super( PropMesh, self ).__init__( parent )
		uic.loadUi('dpVision/ui/UiPropMesh.ui', self)
		self.obj = _obj

	@staticmethod
	def create(m, parent = 0):
		return PropWidget.build( [ PropBaseObject(m), PropMesh(m) ], parent )


	def updateProperties(self):
		obj = self.obj

