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
		for w in {self.spinWinMin, self.spinWinMax,
			self.fastDrawCheckBox, self.renderBoxesCheckBox,
			self.zBspin, self.zEspin,
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


		self.f1CheckBox.setChecked(self.obj.m_filters[1][0] != 0)
		self.f2CheckBox.setChecked(self.obj.m_filters[2][0] != 0)
		self.f3CheckBox.setChecked(self.obj.m_filters[3][0] != 0)
		self.f4CheckBox.setChecked(self.obj.m_filters[4][0] != 0)
		self.f5CheckBox.setChecked(self.obj.m_filters[5][0] != 0)
		self.f6CheckBox.setChecked(self.obj.m_filters[6][0] != 0)

		self.f1SpinMin.setValue(self.obj.m_filters[1][1])
		self.f1SpinMin.setMinimum(self.obj.m_min)
		self.f1SpinMax.setValue(self.obj.m_filters[1][2])
		self.f1SpinMax.setMaximum(self.obj.m_max)

		self.f2SpinMin.setValue(self.obj.m_filters[2][1])
		self.f2SpinMin.setMinimum(self.obj.m_min)
		self.f2SpinMax.setValue(self.obj.m_filters[2][2])
		self.f2SpinMax.setMaximum(self.obj.m_max)

		self.f3SpinMin.setValue(self.obj.m_filters[3][1])
		self.f3SpinMin.setMinimum(self.obj.m_min)
		self.f3SpinMax.setValue(self.obj.m_filters[3][2])
		self.f3SpinMax.setMaximum(self.obj.m_max)

		self.f4SpinMin.setValue(self.obj.m_filters[4][1])
		self.f4SpinMin.setMinimum(self.obj.m_min)
		self.f4SpinMax.setValue(self.obj.m_filters[4][2])
		self.f4SpinMax.setMaximum(self.obj.m_max)

		self.f5SpinMin.setValue(self.obj.m_filters[5][1])
		self.f5SpinMin.setMinimum(self.obj.m_min)
		self.f5SpinMax.setValue(self.obj.m_filters[5][2])
		self.f5SpinMax.setMaximum(self.obj.m_max)

		self.f6SpinMin.setValue(self.obj.m_filters[6][1])
		self.f6SpinMin.setMinimum(self.obj.m_min)
		self.f6SpinMax.setValue(self.obj.m_filters[6][2])
		self.f6SpinMax.setMaximum(self.obj.m_max)

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


	@pyqtSlot(float)
	def on_f1_min_changed(self, val):
		val = np.round(val,4)
		print(f"f1 min={val}")

		if val > self.obj.m_filters[1][2]:
			val = self.obj.m_filters[1][2]
		elif val < self.obj.m_minDisplWin:
			val = self.obj.m_minDisplWin

		self.obj.m_filters[1][1] = val
		self.f1SpinMax.blockSignals(True)
		self.f1SpinMax.setMinimum(val)
		self.f1SpinMax.blockSignals(False)
		AP.updateAllViews()

	@pyqtSlot(float)
	def on_f1_max_changed(self, val):
		val = np.round(val,4)
		print(f"f1 max={val}")

		if val < self.obj.m_filters[1][1]:
			val = self.obj.m_filters[1][1]
		elif val > self.obj.m_maxDisplWin:
			val = self.obj.m_maxDisplWin

		self.obj.m_filters[1][2] = val
		self.f1SpinMin.blockSignals(True)
		self.f1SpinMin.setMaximum(val)
		self.f1SpinMin.blockSignals(False)
		AP.updateAllViews()

	@pyqtSlot(float)
	def on_f2_min_changed(self, val):
		val = np.round(val,4)
		print(f"f2 min={val}")

		if val > self.obj.m_filters[2][2]:
			val = self.obj.m_filters[2][2]
		elif val < self.obj.m_minDisplWin:
			val = self.obj.m_minDisplWin

		self.obj.m_filters[2][1] = val
		self.f2SpinMax.blockSignals(True)
		self.f2SpinMax.setMinimum(val)
		self.f2SpinMax.blockSignals(False)
		AP.updateAllViews()

	@pyqtSlot(float)
	def on_f2_max_changed(self, val):
		val = np.round(val,4)
		print(f"f2 max={val}")

		if val < self.obj.m_filters[2][1]:
			val = self.obj.m_filters[2][1]
		elif val > self.obj.m_maxDisplWin:
			val = self.obj.m_maxDisplWin

		self.obj.m_filters[2][2] = val
		self.f2SpinMin.blockSignals(True)
		self.f2SpinMin.setMaximum(val)
		self.f2SpinMin.blockSignals(False)
		AP.updateAllViews()

	@pyqtSlot(float)
	def on_f3_min_changed(self, val):
		val = np.round(val,4)
		print(f"f3 min={val}")

		if val > self.obj.m_filters[3][2]:
			val = self.obj.m_filters[3][2]
		elif val < self.obj.m_minDisplWin:
			val = self.obj.m_minDisplWin

		self.obj.m_filters[3][1] = val
		self.f3SpinMax.blockSignals(True)
		self.f3SpinMax.setMinimum(val)
		self.f3SpinMax.blockSignals(False)
		AP.updateAllViews()
	
	@pyqtSlot(float)
	def on_f3_max_changed(self, val):
		val = np.round(val,4)
		print(f"f3 max={val}")

		if val < self.obj.m_filters[3][1]:
			val = self.obj.m_filters[3][1]
		elif val > self.obj.m_maxDisplWin:
			val = self.obj.m_maxDisplWin

		self.obj.m_filters[3][2] = val
		self.f3SpinMin.blockSignals(True)
		self.f3SpinMin.setMaximum(val)
		self.f3SpinMin.blockSignals(False)
		AP.updateAllViews()

	@pyqtSlot(float)
	def on_f4_min_changed(self, val):
		val = np.round(val,4)
		print(f"f4 min={val}")

		if val > self.obj.m_filters[4][2]:
			val = self.obj.m_filters[4][2]
		elif val < self.obj.m_minDisplWin:
			val = self.obj.m_minDisplWin

		self.obj.m_filters[4][1] = val
		self.f4SpinMax.blockSignals(True)
		self.f4SpinMax.setMinimum(val)
		self.f4SpinMax.blockSignals(False)
		AP.updateAllViews()

	@pyqtSlot(float)
	def on_f4_max_changed(self, val):
		val = np.round(val,4)
		print(f"f4 max={val}")

		if val < self.obj.m_filters[4][1]:
			val = self.obj.m_filters[4][1]
		elif val > self.obj.m_maxDisplWin:
			val = self.obj.m_maxDisplWin

		self.obj.m_filters[4][2] = val
		self.f4SpinMin.blockSignals(True)
		self.f4SpinMin.setMaximum(val)
		self.f4SpinMin.blockSignals(False)
		AP.updateAllViews()

	@pyqtSlot(float)
	def on_f5_min_changed(self, val):
		val = np.round(val,4)
		print(f"f5 min={val}")

		if val > self.obj.m_filters[5][2]:
			val = self.obj.m_filters[5][2]
		elif val < self.obj.m_minDisplWin:
			val = self.obj.m_minDisplWin

		self.obj.m_filters[5][1] = val
		self.f5SpinMax.blockSignals(True)
		self.f5SpinMax.setMinimum(val)
		self.f5SpinMax.blockSignals(False)
		AP.updateAllViews()
	
	@pyqtSlot(float)
	def on_f5_max_changed(self, val):
		val = np.round(val,4)
		print(f"f5 max={val}")

		if val < self.obj.m_filters[5][1]:
			val = self.obj.m_filters[5][1]
		elif val > self.obj.m_maxDisplWin:
			val = self.obj.m_maxDisplWin

		self.obj.m_filters[5][2] = val
		self.f5SpinMin.blockSignals(True)
		self.f5SpinMin.setMaximum(val)
		self.f5SpinMin.blockSignals(False)
		AP.updateAllViews()

	@pyqtSlot(float)
	def on_f6_min_changed(self, val):
		val = np.round(val,4)
		print(f"f6 min={val}")

		if val > self.obj.m_filters[6][2]:
			val = self.obj.m_filters[6][2]
		elif val < self.obj.m_minDisplWin:
			val = self.obj.m_minDisplWin

		self.obj.m_filters[6][1] = val
		self.f6SpinMax.blockSignals(True)
		self.f6SpinMax.setMinimum(val)
		self.f6SpinMax.blockSignals(False)
		AP.updateAllViews()
	
	@pyqtSlot(float)
	def on_f6_max_changed(self, val):
		val = np.round(val,4)
		print(f"f6 max={val}")

		if val < self.obj.m_filters[6][1]:
			val = self.obj.m_filters[6][1]
		elif val > self.obj.m_maxDisplWin:
			val = self.obj.m_maxDisplWin

		self.obj.m_filters[6][2] = val
		self.f6SpinMin.blockSignals(True)
		self.f6SpinMin.setMaximum(val)
		self.f6SpinMin.blockSignals(False)
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


