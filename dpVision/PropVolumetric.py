# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 20:40:37 2023

@author: darek
"""

from abc import ABC, abstractmethod
from PyQt5 import uic
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from dpVision.Globals import AP
from dpVision.PropWidget import PropWidget
from dpVision.PropBaseObject import PropBaseObject
from dpVision.Mesh import Mesh
import numpy as np

class PropVolumetric(PropWidget):
	def __init__(self, _obj, parent=None):
		super( PropVolumetric, self ).__init__( parent )
		uic.loadUi('dpVision/ui/UiPropVolumetric.ui', self)
		self.obj = _obj

	@staticmethod
	def create(m, parent = 0):
		return PropWidget.build( [ PropBaseObject(m), PropVolumetric(m) ], parent )

	def blockAll(self, b):
		for w in {self.spinWinMin, self.spinWinMax, self.fastDrawCheckBox, self.renderBoxesCheckBox, self.zBspin, self.zEspin}:
			w.blockSignals(b)

	def updateProperties(self):
		self.blockAll(True)

		self.spinWinMin.setValue(self.obj.m_minDisplWin)
		self.spinWinMin.setMinimum(self.obj.m_min)

		self.spinWinMax.setValue(self.obj.m_maxDisplWin)
		self.spinWinMax.setMaximum(self.obj.m_max)

		self.zBspin.setValue(self.obj.m_minSlice)
		self.zBspin.setMinimum(0)

		self.zEspin.setValue(self.obj.m_maxSlice)
		self.zEspin.setMaximum(self.obj.m_volume.shape[0]-1)

		self.fastDrawCheckBox.setChecked(self.obj.m_fastDraw)
		self.renderBoxesCheckBox.setChecked(self.obj.m_renderBoxes)

		self.blockAll(False)


	@pyqtSlot()
	def addColorWidgetButtonClicked(self):
		pass
	
	@pyqtSlot(float)
	def winMinValueChanged(self, val):
		val = np.round(val,4)
		print(f"win min={val}")

		if val > self.obj.m_maxDisplWin:
			val = self.obj.m_maxDisplWin
		elif val < self.obj.m_min:
			val = self.obj.m_min

		self.obj.m_minDisplWin = val
		self.spinWinMax.blockSignals(True)
		self.spinWinMax.setMinimum(val)
		self.spinWinMax.blockSignals(False)
		AP.updateAllViews()

	@pyqtSlot(float)
	def winMaxValueChanged(self, val):
		val = np.round(val,4)
		print(f"win max={val}")

		if val < self.obj.m_minDisplWin:
			val = self.obj.m_minDisplWin
		elif val > self.obj.m_max:
			val = self.obj.m_max

		self.obj.m_maxDisplWin = val
		self.spinWinMin.blockSignals(True)
		self.spinWinMin.setMaximum(val)
		self.spinWinMin.blockSignals(False)
		AP.updateAllViews()

	@pyqtSlot(bool)
	def on_render_boxes_checkbox(self, b):
		self.obj.m_renderBoxes = b
		print(f"render boxes: {b}")
		self.obj.remove_shader_program()
		AP.updateAllViews()


	@pyqtSlot(bool)
	def on_fast_draw_checkbox(self, b):
		self.obj.m_fastDraw = b
		AP.updateAllViews()

	@pyqtSlot()
	def updateColorFilters():
		pass

	@pyqtSlot()
	def removeFilter():
		pass

	@pyqtSlot(int)
	def xValchanged(int):
		pass

	@pyqtSlot(int)
	def xBchanged(int):
		pass

	@pyqtSlot(int)
	def yBchanged(int):
		pass

	@pyqtSlot(int)
	def zBchanged(self, val):
		val = np.round(val,0)
		print(f"min slice={val}")

		if val > self.obj.m_maxSlice:
			val = self.obj.m_maxSlice
		elif val < 0:
			val = 0

		self.obj.m_minSlice = val
		self.zEspin.blockSignals(True)
		self.zEspin.setMinimum(val)
		self.zEspin.blockSignals(False)
		AP.updateAllViews()

	@pyqtSlot(int)
	def xEchanged(int):
		pass

	@pyqtSlot(int)
	def yEchanged(int):
		pass

	@pyqtSlot(int)
	def zEchanged(self, val):
		val = np.round(val,0)
		print(f"max slice={val}")

		if val < self.obj.m_minSlice:
			val = self.obj.m_minSlice
		elif val >= self.obj.m_volume.shape[0]:
			val = self.obj.m_volume.shape[0] - 1

		self.obj.m_maxSlice = val
		self.zBspin.blockSignals(True)
		self.zBspin.setMaximum(val)
		self.zBspin.blockSignals(False)
		AP.updateAllViews()


