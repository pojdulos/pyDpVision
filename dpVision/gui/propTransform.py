# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
import re
from PyQt5 import uic
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from .. import AP

from .propWidget import PropWidget
from .propBaseObject import PropBaseObject
import weakref

class PropTransform(PropWidget):
	def __init__(self, _obj, parent=None):
		super( PropTransform, self ).__init__( parent )
		#uic.loadUi('dpVision/gui/forms/propTransform.ui', self)
		AP.loadUi('propTransform.ui', self)
		
		self.treeView.setVisible(False)
		self.resize(self.layout().sizeHint())

		#self.m_trans = _obj
		self.obj_ref = weakref.ref(_obj)

	@staticmethod
	def create(m, parent = 0):
		return PropWidget.build( [ PropBaseObject(m), PropTransform(m) ], parent )

	def updateMatrix(self):
		m_trans = self.obj_ref()
		self.matrixTable.blockSignals(True)
		for row in range(4):
			for col in range(4):
				index = self.matrixTable.model().index(row,col)
				value = m_trans.matrix[row,col]
				self.matrixTable.model().setData(index, value)
		self.matrixTable.blockSignals(False)

	def updateEuler(self):
		m_trans = self.obj_ref()
		rot = m_trans.getEulerAnglesDeg()
		self.eulerX.blockSignals(True)
		self.eulerY.blockSignals(True)
		self.eulerZ.blockSignals(True)
		self.eulerX.setValue(rot[0])
		self.eulerY.setValue(rot[1])
		self.eulerZ.setValue(rot[2])
		self.eulerX.blockSignals(False)
		self.eulerY.blockSignals(False)
		self.eulerZ.blockSignals(False)

	def updateQuat(self):
		m_trans = self.obj_ref()
		qua = m_trans.toQuaternion()
		self.quatW.blockSignals(True)
		self.quatX.blockSignals(True)
		self.quatY.blockSignals(True)
		self.quatZ.blockSignals(True)
		self.quatW.setValue(qua[0])
		self.quatX.setValue(qua[1])
		self.quatY.setValue(qua[2])
		self.quatZ.setValue(qua[3])
		self.quatW.blockSignals(False)
		self.quatX.blockSignals(False)
		self.quatY.blockSignals(False)
		self.quatZ.blockSignals(False)

	def updateProperties(self):
		m_trans = self.obj_ref()
		if m_trans is None:
			return
		
		# w = {	self.showScrewCheckBox, \
	   	# 		self.transX, self.transY, self.transZ }
		w = self.get_subwidgets()

		for i in w: i.blockSignals(True)
		self.updateMatrix()
		self.updateEuler()
		self.updateQuat()

		s = m_trans.getScale()
		self.scaleX.setValue(s[0])
		self.scaleY.setValue(s[1])
		self.scaleZ.setValue(s[2])
		# self.scaleCheck.setChecked(True)

		self.showScrewCheckBox.setChecked(m_trans.m_show_screw)

		tra = m_trans.getTranslation()
		self.transX.setValue(tra[0])
		self.transY.setValue(tra[1])
		self.transZ.setValue(tra[2])
		for i in w: i.blockSignals(False)


	def changedEul(self,d):
		m_trans = self.obj_ref()
		edit = self.sender()
		if isinstance(edit, QDoubleSpinBox):
			# old = self.m_trans.getEulerAnglesDeg()
			# print('old: ', old, 'd: ', d)
			# if edit == self.eulerX:
			# 	diff = d-old[0]
			# 	self.m_trans.rotate(diff,[1,0,0])
			# elif edit == self.eulerY:
			# 	diff = d-old[1]
			# 	self.m_trans.rotate(diff,[0,1,0])
			# elif edit == self.eulerZ:
			# 	diff = d-old[2]
			# 	self.m_trans.rotate(diff,[0,0,1])
			#self.updateEuler()
			roll = self.eulerX.value()				
			pitch = self.eulerY.value()				
			yaw = self.eulerZ.value()				
			m_trans.fromEulerAngles(roll, pitch, yaw)

			self.updateMatrix()
			self.updateQuat()
			AP.updateAllViews()
	
	def changedTra(self,d):
		m_trans = self.obj_ref()
		edit = self.sender()
		if isinstance(edit, QDoubleSpinBox):
			old = m_trans.getTranslation()
			if edit == self.transX:
				diff = d-old[0]
				m_trans.translate(diff,0,0)
			elif edit == self.transY:
				diff = d-old[1]
				m_trans.translate(0,diff,0)
			elif edit == self.transZ:
				diff = d-old[2]
				m_trans.translate(0,0,diff)
			AP.updateAllViews()

	def changedSca(self,d):
		m_trans = self.obj_ref()
		s = m_trans.getScale()
		print(f"scale: {d}")
		m_trans.scale(d/s[0],d/s[1],d/s[2])
		AP.updateAllViews()

	def changedQua(self, d):
		pass
	
	def clearMatrix(self):
		m_trans = self.obj_ref()
		m_trans.reset()
		AP.mainWin.dock['properties'].updateProperties()
		AP.updateAllViews()
	
	def copyToClipboard(self):
		m_trans = self.obj_ref()
		m_trans.copyToClipboard()

	def pasteFromClipboard(self):
		m_trans = self.obj_ref()
		m_trans.pasteFromClipboard()
		AP.mainWin.dock['properties'].updateProperties()
		AP.updateAllViews()

	def onRotButton(self):
		pass

	def onScaleCheck(self,i):
		pass

	@pyqtSlot(float)
	def onOriginPointValueChanged(self,d):
		m_trans = self.obj_ref()
		edit = self.sender()
		if isinstance(edit, QDoubleSpinBox) and (edit == self.originX or edit == self.originY or edit == self.originZ):
			m_trans.m_origin = [self.originX.value(), self.originY.value(), self.originZ.value()]

	@pyqtSlot(bool)
	def onShowScrewCheckBox(self, b):
		m_trans = self.obj_ref()
		m_trans.m_show_screw = b
		AP.updateAllViews()

	@pyqtSlot(bool)
	def onOriginRadio(self,b):
		m_trans = self.obj_ref()
		radio = self.sender()
		if not isinstance(radio, QRadioButton): return
		if radio == self.originRadioObj:
			pass
		elif radio == self.originRadioBB:
			_b, _min, _max = m_trans.getBB()
			
			pass
		elif radio == self.originRadioWeight:
			pass
		elif radio == self.originRadioPoint:
			self.originX.setEnabled( b )
			self.originY.setEnabled( b )
			self.originZ.setEnabled( b )
			m_trans.m_origin = [self.originX.value(), self.originY.value(), self.originZ.value()] if b else [0.,0.,0.]
		
		
