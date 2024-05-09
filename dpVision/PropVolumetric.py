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


	def updateProperties(self):
		self.spinWinMin.blockSignals(True)
		self.spinWinMin.setValue(self.obj.m_minDisplWin)
		self.spinWinMin.blockSignals(False)

		self.spinWinMax.blockSignals(True)
		self.spinWinMax.setValue(self.obj.m_maxDisplWin)
		self.spinWinMax.blockSignals(False)

		self.fastDrawCheckBox.blockSignals(True)
		self.fastDrawCheckBox.setChecked(self.obj.m_fastDraw)
		self.fastDrawCheckBox.blockSignals(False)


	@pyqtSlot()
	def addColorWidgetButtonClicked(self):
		pass
	
	@pyqtSlot(float)
	def winMinValueChanged(self, val):
		val = np.round(val,4)
		print(f"win min={val}")

		if val < 0.0:
			val = 0.0
		elif val > self.obj.m_maxDisplWin:
			val = self.obj.m_maxDisplWin

		self.obj.m_minDisplWin = val
		self.spinWinMax.blockSignals(True)
		self.spinWinMax.setMinimum(val)
		self.spinWinMax.blockSignals(False)
		AP.updateAllViews()

	@pyqtSlot(float)
	def winMaxValueChanged(self, val):
		val = np.round(val,4)
		print(f"win max={val}")

		if val > 1.0:
			val = 1.0
		elif val < self.obj.m_minDisplWin:
			val = self.obj.m_minDisplWin

		self.obj.m_maxDisplWin = val
		self.spinWinMin.blockSignals(True)
		self.spinWinMin.setMaximum(val)
		self.spinWinMin.blockSignals(False)
		AP.updateAllViews()

	@pyqtSlot(bool)
	def on_fast_draw_checkbox(self, b):
		print(f"checkbox state is {b}")
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
	def zBchanged(int):
		pass

	@pyqtSlot(int)
	def xEchanged(int):
		pass

	@pyqtSlot(int)
	def yEchanged(int):
		pass

	@pyqtSlot(int)
	def zEchanged(int):
		pass


