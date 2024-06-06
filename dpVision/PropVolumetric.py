# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 20:40:37 2023

@author: darek
"""

from abc import ABC, abstractmethod
from PyQt5 import uic
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import numpy as np

from .globals import AP
from .propWidget import PropWidget
from .propBaseObject import PropBaseObject
from .mesh import Mesh

class PropVolumetric(PropWidget):
	def __init__(self, _obj, parent=None):
		super( PropVolumetric, self ).__init__( parent )
		uic.loadUi('dpVision/ui/UiPropVolumetric.ui', self)
		self.obj = _obj
		self.f_check = [self.f0CheckBox, self.f1CheckBox, self.f2CheckBox, self.f3CheckBox, self.f4CheckBox, self.f5CheckBox, self.f6CheckBox]
		self.spin_min = [self.f0SpinMin, self.f1SpinMin, self.f2SpinMin, self.f3SpinMin, self.f4SpinMin, self.f5SpinMin, self.f6SpinMin]
		self.spin_max = [self.f0SpinMax, self.f1SpinMax, self.f2SpinMax, self.f3SpinMax, self.f4SpinMax, self.f5SpinMax, self.f6SpinMax]

	@staticmethod
	def create(m, parent = 0):
		return PropWidget.build( [ PropBaseObject(m), PropVolumetric(m) ], parent )

	def blockAll(self, b):
		for w in {self.spinWinMin, self.spinWinMax,
			self.fastDrawCheckBox, self.renderBoxesCheckBox,
			self.zBspin, self.zEspin,
			self.f0CheckBox, self.f0SpinMin, self.f0SpinMax,
			self.f1CheckBox, self.f1SpinMin, self.f1SpinMax,
			self.f2CheckBox, self.f2SpinMin, self.f2SpinMax,
			self.f3CheckBox, self.f3SpinMin, self.f3SpinMax,
			self.f4CheckBox, self.f4SpinMin, self.f4SpinMax,
			self.f5CheckBox, self.f5SpinMin, self.f5SpinMax,
			self.f6CheckBox, self.f6SpinMin, self.f6SpinMax }:
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

		for idx in range(7):
			self.f_check[idx].setChecked(self.obj.m_filters[idx][0] != 0)

			self.spin_min[idx].setMinimum(self.obj.m_min)
			self.spin_min[idx].setValue(self.obj.m_filters[idx][1])

			self.spin_max[idx].setMaximum(self.obj.m_max)
			self.spin_max[idx].setValue(self.obj.m_filters[idx][2])

			self.spin_max[idx].setMinimum(max(self.obj.m_min,self.spin_min[idx].value()))
			self.spin_min[idx].setMaximum(min(self.obj.m_max,self.spin_max[idx].value()))

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
	def on_f0_checkbox(self, b):
		self.obj.m_filters[0][0] = 1 if b else 0
		AP.updateAllViews()

	@pyqtSlot(bool)
	def on_f1_checkbox(self, b):
		self.obj.m_filters[1][0] = 1 if b else 0
		AP.updateAllViews()

	@pyqtSlot(bool)
	def on_f2_checkbox(self, b):
		self.obj.m_filters[2][0] = 1 if b else 0
		AP.updateAllViews()

	@pyqtSlot(bool)
	def on_f3_checkbox(self, b):
		self.obj.m_filters[3][0] = 1 if b else 0
		AP.updateAllViews()

	@pyqtSlot(bool)
	def on_f4_checkbox(self, b):
		self.obj.m_filters[4][0] = 1 if b else 0
		AP.updateAllViews()

	@pyqtSlot(bool)
	def on_f5_checkbox(self, b):
		self.obj.m_filters[5][0] = 1 if b else 0
		AP.updateAllViews()

	@pyqtSlot(bool)
	def on_f6_checkbox(self, b):
		self.obj.m_filters[6][0] = 1 if b else 0
		AP.updateAllViews()


	def change_filter_min(self, idx, val):
		val = np.round(val,4)
		print(f"f{idx} min={val}")

		if val > self.obj.m_filters[idx][2]:
			val = self.obj.m_filters[idx][2]
		elif val < self.obj.m_minDisplWin:
			val = self.obj.m_minDisplWin

		self.obj.m_filters[idx][1] = val
		self.spin_max[idx].blockSignals(True)
		self.spin_max[idx].setMinimum(val)
		self.spin_max[idx].blockSignals(False)
		AP.updateAllViews()


	@pyqtSlot(float)
	def on_f0_min_changed(self, val):
		self.change_filter_min(0, val)

	@pyqtSlot(float)
	def on_f1_min_changed(self, val):
		self.change_filter_min(1, val)

	@pyqtSlot(float)
	def on_f2_min_changed(self, val):
		self.change_filter_min(2, val)

	@pyqtSlot(float)
	def on_f3_min_changed(self, val):
		self.change_filter_min(3, val)

	@pyqtSlot(float)
	def on_f4_min_changed(self, val):
		self.change_filter_min(4, val)

	@pyqtSlot(float)
	def on_f5_min_changed(self, val):
		self.change_filter_min(5, val)

	@pyqtSlot(float)
	def on_f6_min_changed(self, val):
		self.change_filter_min(6, val)

	def change_filter_max(self, idx, val):
		val = np.round(val,4)
		print(f"f{idx} max={val}")

		if val < self.obj.m_filters[idx][1]:
			val = self.obj.m_filters[idx][1]
		elif val > self.obj.m_maxDisplWin:
			val = self.obj.m_maxDisplWin

		self.obj.m_filters[idx][2] = val
		self.spin_min[idx].blockSignals(True)
		self.spin_min[idx].setMaximum(val)
		self.spin_min[idx].blockSignals(False)
		AP.updateAllViews()

	@pyqtSlot(float)
	def on_f0_max_changed(self, val):
		self.change_filter_max(0, val)

	@pyqtSlot(float)
	def on_f1_max_changed(self, val):
		self.change_filter_max(1, val)

	@pyqtSlot(float)
	def on_f2_max_changed(self, val):
		self.change_filter_max(2, val)

	@pyqtSlot(float)
	def on_f3_max_changed(self, val):
		self.change_filter_max(3, val)

	@pyqtSlot(float)
	def on_f4_max_changed(self, val):
		self.change_filter_max(4, val)

	@pyqtSlot(float)
	def on_f5_max_changed(self, val):
		self.change_filter_max(5, val)

	@pyqtSlot(float)
	def on_f6_max_changed(self, val):
		self.change_filter_max(6, val)

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


