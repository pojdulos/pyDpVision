# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 20:40:37 2023

@author: darek
"""

from abc import ABC, abstractmethod
from PyQt5 import uic
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from .propBaseObject import PropBaseObject
from .propWidget import PropWidget
import weakref
from .. import AP

class PropNDimCloud(PropWidget):
	def __init__(self, _obj, parent=None):
		super( PropNDimCloud, self ).__init__( parent )
		self.obj_ref = weakref.ref(_obj)
		self.buildUI()

	def buildUI(self):
		obj = self.obj_ref()
		formLayout = QFormLayout()

		self.label01 = QLabel("Spatial dimensions:")
		formLayout.addRow(self.label01)

		real_dims = [f"[{i}] {obj.m_headers[i]}" for i in range(obj.m_dimensions)]

		sel_names = ["X", "Y", "Z", "W"]

		self.dim_selector = []
		self.gains = []

		for i in range(4):
			s = QComboBox(self)
			s.setObjectName(sel_names[i])
			s.addItems(real_dims)
			self.dim_selector.append(s)
			s.currentIndexChanged.connect(lambda x, i=i: self.on_index_changed(i, x))

			g = QDoubleSpinBox(self)
			g.setMinimum(0.1)
			g.setMaximum(10.0)
			g.setSingleStep(0.1)
			g.setDecimals(2)
			g.setValue(obj.m_gains[i])
			self.gains.append(g)
			g.valueChanged.connect(lambda x, i=i: self.on_gain_changed(i, x))
			g.setFixedWidth(48)

			lbl = QLabel(f"{sel_names[i]}:")
			lbl.setFixedWidth(12)

			l = QHBoxLayout()
			l.addWidget(lbl)
			l.addWidget(s)
			l.addWidget(g)
			w = QWidget(self)
			w.setLayout(l)

			# formLayout.addRow(lbl, w)
			formLayout.addRow(w)

		layout = QVBoxLayout()
		layout.addLayout(formLayout)

		formLayout = QFormLayout()
		self.label02 = QLabel("Mouse navigation:")
		formLayout.addRow(self.label02)

		self.horNav = QComboBox(self)
		formLayout.addRow("horizontal:", self.horNav)

		self.verNav = QComboBox(self)
		formLayout.addRow("vertical:", self.verNav)

		layout.addLayout(formLayout)
		
		self.setLayout(layout)


	@staticmethod
	def create(m, parent = 0):
		return PropWidget.build( [ 
			# PropBaseObject(m),
			PropNDimCloud(m) ], parent )

	def updateProperties(self):
		obj = self.obj_ref()
		w = self.get_subwidgets()
		for i in w:	i.blockSignals(True)

		for i in range(4):
			self.dim_selector[i].setCurrentIndex(obj.m_real_dims[i])
			self.gains[i].setValue(obj.m_gains[i])

		for i in w:	i.blockSignals(False)

	def on_gain_changed(self, cur_idx, cur_val):
		obj = self.obj_ref()
		obj.m_gains[cur_idx] = cur_val

		obj.projectTo3D()
		
		AP.mainWin.dock["workspace"].refreshAll()
		AP.updateAllViews()

	def on_index_changed(self, cur_idx, cur_val):
		obj = self.obj_ref()

		for i in range (4):
			if i != cur_idx and obj.m_real_dims[i] == cur_val:
				obj.m_real_dims[i] = obj.m_real_dims[cur_idx]
				break

		obj.m_real_dims[cur_idx] = cur_val
		
		obj.projectTo3D()

		self.updateProperties()				

		AP.mainWin.dock["workspace"].refreshAll()
		AP.updateAllViews()


	@pyqtSlot(bool)
	def onChangedSelfVisibility(self, b):
		obj = self.obj_ref()
		obj.setSelfVisibility(b)
		AP.mainWin.dock["workspace"].refreshAll()
		AP.updateAllViews()

	@pyqtSlot(bool)
	def onChangedSelection(self, b):
		print('PropBaseObject: checked' if b else 'PropBaseObject: unchecked')
		obj = self.obj_ref()
		if obj is not None:
			obj.checked = b
			self.object_updated.emit(obj)

	@pyqtSlot(str)
	def onChangedLabel(self, s):
		obj = self.obj_ref()
		obj.label = s
		AP.mainWin.dock["workspace"].refreshAll()
		AP.updateAllViews()

	@pyqtSlot()
	def onDescrChanged(self):
		obj = self.obj_ref()
		obj.description = self.descrEdit.toPlainText()


