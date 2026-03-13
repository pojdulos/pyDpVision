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

from .. import AP

from .propWidget import PropWidget
from .propBaseObject import PropBaseObject

import weakref

class PropVolumetric(PropWidget):
	def __init__(self, _obj, parent=None):
		super( PropVolumetric, self ).__init__( parent )
		#uic.loadUi('dpVision/gui/forms/propVolumetric.ui', self)
		AP.loadUi('propVolumetric.ui', self)

		self.obj_ref = weakref.ref(_obj)

		self.f_check = [self.f0CheckBox, self.f1CheckBox, self.f2CheckBox, self.f3CheckBox, self.f4CheckBox, self.f5CheckBox, self.f6CheckBox]
		self.spin_min = [self.f0SpinMin, self.f1SpinMin, self.f2SpinMin, self.f3SpinMin, self.f4SpinMin, self.f5SpinMin, self.f6SpinMin]
		self.spin_max = [self.f0SpinMax, self.f1SpinMax, self.f2SpinMax, self.f3SpinMax, self.f4SpinMax, self.f5SpinMax, self.f6SpinMax]

	@staticmethod
	def create(m, parent = 0):
		return PropWidget.build( [ PropBaseObject(m), PropVolumetric(m) ], parent )

	def blockAll(self, b):
		for w in {self.spinWinMin, self.spinWinMax,
			self.fastDrawCheckBox, self.renderBoxesCheckBox,
			self.renderSplatsCheckBox, self.splatAdditiveCheckBox, self.splatScaleSpin,
			self.xBspin, self.xEspin,
			self.yBspin, self.yEspin,
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
		obj = self.obj_ref()
		self.blockAll(True)

		self.spinWinMin.setValue(obj.m_minDisplWin)
		self.spinWinMin.setMinimum(obj.m_min)

		self.spinWinMax.setValue(obj.m_maxDisplWin)
		self.spinWinMax.setMaximum(obj.m_max)

		self.xBspin.setValue(obj.m_minColumn)
		self.xBspin.setMinimum(0)

		self.xEspin.setValue(obj.m_maxColumn)
		self.xEspin.setMaximum(obj.shape[2]-1)

		self.yBspin.setValue(obj.m_minRow)
		self.yBspin.setMinimum(0)

		self.yEspin.setValue(obj.m_maxRow)
		self.yEspin.setMaximum(obj.shape[1]-1)

		self.zBspin.setValue(obj.m_minSlice)
		self.zBspin.setMinimum(0)

		self.zEspin.setValue(obj.m_maxSlice)
		self.zEspin.setMaximum(obj.shape[0]-1)

		for idx in range(7):
			self.f_check[idx].setChecked(obj.m_filters[idx][0] != 0)

			self.spin_min[idx].setMinimum(obj.m_min)
			self.spin_min[idx].setValue(obj.m_filters[idx][1])

			self.spin_max[idx].setMaximum(obj.m_max)
			self.spin_max[idx].setValue(obj.m_filters[idx][2])

			self.spin_max[idx].setMinimum(max(obj.m_min,self.spin_min[idx].value()))
			self.spin_min[idx].setMaximum(min(obj.m_max,self.spin_max[idx].value()))

		self.fastDrawCheckBox.setChecked(obj.m_fastDraw)
		self.renderBoxesCheckBox.setChecked(obj.m_renderBoxes)
		self.renderSplatsCheckBox.setChecked(obj.m_renderSplats)
		self.splatAdditiveCheckBox.setChecked(obj.m_splat_additive)
		self.splatScaleSpin.setValue(obj.m_splat_scale)
		self._update_splat_color_button()

		self.blockAll(False)


	@pyqtSlot()
	def addColorWidgetButtonClicked(self):
		pass
	
	@pyqtSlot(float)
	def winMinValueChanged(self, val):
		obj = self.obj_ref()
		val = np.round(val,4)
		print(f"win min={val}")

		if val > obj.m_maxDisplWin:
			val = obj.m_maxDisplWin
		elif val < obj.m_min:
			val = obj.m_min

		obj.m_minDisplWin = val
		self.spinWinMax.blockSignals(True)
		self.spinWinMax.setMinimum(val)
		self.spinWinMax.blockSignals(False)
		AP.updateAllViews()

	@pyqtSlot(float)
	def winMaxValueChanged(self, val):
		obj = self.obj_ref()
		val = np.round(val,4)
		print(f"win max={val}")

		if val < obj.m_minDisplWin:
			val = obj.m_minDisplWin
		elif val > obj.m_max:
			val = obj.m_max

		obj.m_maxDisplWin = val
		self.spinWinMin.blockSignals(True)
		self.spinWinMin.setMaximum(val)
		self.spinWinMin.blockSignals(False)
		AP.updateAllViews()

	@pyqtSlot(bool)
	def on_render_boxes_checkbox(self, b):
		obj = self.obj_ref()
		obj.m_renderBoxes = b
		print(f"render boxes: {b}")
		obj.remove_shader_program()
		AP.updateAllViews()

	@pyqtSlot(bool)
	def on_render_splats_checkbox(self, b):
		obj = self.obj_ref()
		obj.m_renderSplats = b
		print(f"gaussian splats: {b}")
		AP.updateAllViews()

	@pyqtSlot(bool)
	def on_splat_additive_checkbox(self, b):
		obj = self.obj_ref()
		obj.m_splat_additive = b
		AP.updateAllViews()

	@pyqtSlot(float)
	def on_splat_scale_changed(self, val):
		obj = self.obj_ref()
		obj.m_splat_scale = val
		AP.updateAllViews()

	def _update_splat_color_button(self):
		obj = self.obj_ref()
		r, g, b = (int(c * 255) for c in obj.m_splat_tint)
		self.splatColorButton.setStyleSheet(f"background-color: rgb({r},{g},{b});")

	@pyqtSlot()
	def on_splat_color_button(self):
		from PyQt5.QtWidgets import QColorDialog
		from PyQt5.QtGui import QColor
		obj = self.obj_ref()
		r, g, b = (int(c * 255) for c in obj.m_splat_tint)
		color = QColorDialog.getColor(QColor(r, g, b), self)
		if color.isValid():
			obj.m_splat_tint = [color.redF(), color.greenF(), color.blueF()]
			self._update_splat_color_button()
			AP.updateAllViews()


	@pyqtSlot(bool)
	def on_f0_checkbox(self, b):
		obj = self.obj_ref()
		obj.m_filters[0][0] = 1 if b else 0
		AP.updateAllViews()

	@pyqtSlot(bool)
	def on_f1_checkbox(self, b):
		obj = self.obj_ref()
		obj.m_filters[1][0] = 1 if b else 0
		AP.updateAllViews()

	@pyqtSlot(bool)
	def on_f2_checkbox(self, b):
		obj = self.obj_ref()
		obj.m_filters[2][0] = 1 if b else 0
		AP.updateAllViews()

	@pyqtSlot(bool)
	def on_f3_checkbox(self, b):
		obj = self.obj_ref()
		obj.m_filters[3][0] = 1 if b else 0
		AP.updateAllViews()

	@pyqtSlot(bool)
	def on_f4_checkbox(self, b):
		obj = self.obj_ref()
		obj.m_filters[4][0] = 1 if b else 0
		AP.updateAllViews()

	@pyqtSlot(bool)
	def on_f5_checkbox(self, b):
		obj = self.obj_ref()
		obj.m_filters[5][0] = 1 if b else 0
		AP.updateAllViews()

	@pyqtSlot(bool)
	def on_f6_checkbox(self, b):
		obj = self.obj_ref()
		obj.m_filters[6][0] = 1 if b else 0
		AP.updateAllViews()


	def change_filter_min(self, idx, val):
		obj = self.obj_ref()
		val = np.round(val,4)
		print(f"f{idx} min={val}")

		if val > obj.m_filters[idx][2]:
			val = obj.m_filters[idx][2]
		elif val < obj.m_minDisplWin:
			val = obj.m_minDisplWin

		obj.m_filters[idx][1] = val
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
		obj = self.obj_ref()
		val = np.round(val,4)
		print(f"f{idx} max={val}")

		if val < obj.m_filters[idx][1]:
			val = obj.m_filters[idx][1]
		elif val > obj.m_maxDisplWin:
			val = obj.m_maxDisplWin

		obj.m_filters[idx][2] = val
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
		obj = self.obj_ref()
		obj.m_fastDraw = b
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
	def xBchanged(self, val):
		obj = self.obj_ref()
		val = np.round(val,0)
		print(f"min column={val}")

		if val > obj.m_maxColumn:
			val = obj.m_maxColumn
		elif val < 0:
			val = 0

		obj.m_minColumn = val
		self.xEspin.blockSignals(True)
		self.xEspin.setMinimum(val)
		self.xEspin.blockSignals(False)
		AP.updateAllViews()

	@pyqtSlot(int)
	def yBchanged(self, val):
		obj = self.obj_ref()
		val = np.round(val,0)
		print(f"min row={val}")

		if val > obj.m_maxRow:
			val = obj.m_maxRow
		elif val < 0:
			val = 0

		obj.m_minRow = val
		self.yEspin.blockSignals(True)
		self.yEspin.setMinimum(val)
		self.yEspin.blockSignals(False)
		AP.updateAllViews()

	@pyqtSlot(int)
	def zBchanged(self, val):
		obj = self.obj_ref()
		val = np.round(val,0)
		print(f"min slice={val}")

		if val > obj.m_maxSlice:
			val = obj.m_maxSlice
		elif val < 0:
			val = 0

		obj.m_minSlice = val
		self.zEspin.blockSignals(True)
		self.zEspin.setMinimum(val)
		self.zEspin.blockSignals(False)
		AP.updateAllViews()

	@pyqtSlot(int)
	def xEchanged(self, val):
		obj = self.obj_ref()
		val = np.round(val,0)
		print(f"max column={val}")

		if val < obj.m_minColumn:
			val = obj.m_minColumn
		elif val >= obj.shape[2]:
			val = obj.shape[2] - 1

		obj.m_maxColumn = val
		self.xBspin.blockSignals(True)
		self.xBspin.setMaximum(val)
		self.xBspin.blockSignals(False)
		AP.updateAllViews()

	@pyqtSlot(int)
	def yEchanged(self, val):
		obj = self.obj_ref()
		val = np.round(val,0)
		print(f"max row={val}")

		if val < obj.m_minRow:
			val = obj.m_minRow
		elif val >= obj.shape[1]:
			val = obj.shape[1] - 1

		obj.m_maxRow = val
		self.yBspin.blockSignals(True)
		self.yBspin.setMaximum(val)
		self.yBspin.blockSignals(False)
		AP.updateAllViews()

	@pyqtSlot(int)
	def zEchanged(self, val):
		obj = self.obj_ref()
		val = np.round(val,0)
		print(f"max slice={val}")

		if val < obj.m_minSlice:
			val = obj.m_minSlice
		elif val >= obj.shape[0]:
			val = obj.shape[0] - 1

		obj.m_maxSlice = val
		self.zBspin.blockSignals(True)
		self.zBspin.setMaximum(val)
		self.zBspin.blockSignals(False)
		AP.updateAllViews()


