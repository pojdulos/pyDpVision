# -*- coding: utf-8 -*-
"""
Created on Thu Apr 16 12:30:00 2026

@author: Codex
"""

from PyQt5.QtCore import pyqtSlot

from .propWidget import PropWidget
from .propBaseObject import PropBaseObject
from .propAnnotation import PropAnnotation
import weakref
from .. import AP


class PropAnnotationElipsoide(PropWidget):
	"""Panel wlasciwosci adnotacji elipsoidy."""

	def __init__(self, _obj, parent=None):
		"""Buduje panel i laduje formularz Qt dla elipsoidy."""
		super(PropAnnotationElipsoide, self).__init__(parent)
		AP.loadUi('propAnnotationElipsoide.ui', self)
		self.obj_ref = weakref.ref(_obj)

	@staticmethod
	def create(m, parent=0):
		"""Tworzy zlozony panel wraz z sekcjami bazowymi adnotacji."""
		return PropWidget.build([PropBaseObject(m), PropAnnotation(m), PropAnnotationElipsoide(m)], parent)

	def updateProperties(self):
		"""Synchronizuje pola formularza z aktualnym stanem obiektu."""
		obj = self.obj_ref()
		if obj is None:
			return

		widgets = [
			self.showAxes,
			self.ctrX, self.ctrY, self.ctrZ,
			self.radX, self.radY, self.radZ,
			self.axisXX, self.axisXY, self.axisXZ,
			self.axisYX, self.axisYY, self.axisYZ,
			self.axisZX, self.axisZY, self.axisZZ,
		]
		for widget in widgets:
			widget.blockSignals(True)

		center = obj.position
		radii = obj.getRadii()
		axis_x, axis_y, axis_z = obj.getAxes()
		self.showAxes.setChecked(bool(obj.m_showAxes))

		self.ctrX.setValue(center[0])
		self.ctrY.setValue(center[1])
		self.ctrZ.setValue(center[2])

		self.radX.setValue(radii[0])
		self.radY.setValue(radii[1])
		self.radZ.setValue(radii[2])

		self.axisXX.setValue(axis_x[0])
		self.axisXY.setValue(axis_x[1])
		self.axisXZ.setValue(axis_x[2])

		self.axisYX.setValue(axis_y[0])
		self.axisYY.setValue(axis_y[1])
		self.axisYZ.setValue(axis_y[2])

		self.axisZX.setValue(axis_z[0])
		self.axisZY.setValue(axis_z[1])
		self.axisZZ.setValue(axis_z[2])

		for widget in widgets:
			widget.blockSignals(False)

	def _apply_center(self):
		"""Zapisuje srodek elipsoidy na podstawie trzech pol formularza."""
		obj = self.obj_ref()
		obj.position = [self.ctrX.value(), self.ctrY.value(), self.ctrZ.value()]
		AP.updateAllViews()

	def _apply_radii(self):
		"""Zapisuje dlugosci polosi i odswieza widoki."""
		obj = self.obj_ref()
		obj.setRadii([self.radX.value(), self.radY.value(), self.radZ.value()])
		AP.updateAllViews()

	def _apply_axes(self):
		"""Zapisuje wektory osi, pozwalajac klasie obiektu je znormalizowac."""
		obj = self.obj_ref()
		obj.setAxes(
			axis_x=[self.axisXX.value(), self.axisXY.value(), self.axisXZ.value()],
			axis_y=[self.axisYX.value(), self.axisYY.value(), self.axisYZ.value()],
			axis_z=[self.axisZX.value(), self.axisZY.value(), self.axisZZ.value()],
		)
		self.updateProperties()
		AP.updateAllViews()

	def _apply_show_axes(self):
		"""Aktualizuje flage rysowania osi lokalnych."""
		obj = self.obj_ref()
		obj.showAxes(self.showAxes.isChecked())
		AP.updateAllViews()

	@pyqtSlot(float)
	def changedCtrX(self, _value):
		"""Obsluguje zmiane wspolrzednej X srodka."""
		self._apply_center()

	@pyqtSlot(float)
	def changedCtrY(self, _value):
		"""Obsluguje zmiane wspolrzednej Y srodka."""
		self._apply_center()

	@pyqtSlot(float)
	def changedCtrZ(self, _value):
		"""Obsluguje zmiane wspolrzednej Z srodka."""
		self._apply_center()

	@pyqtSlot(float)
	def changedRadX(self, _value):
		"""Obsluguje zmiane polosii X."""
		self._apply_radii()

	@pyqtSlot(float)
	def changedRadY(self, _value):
		"""Obsluguje zmiane polosii Y."""
		self._apply_radii()

	@pyqtSlot(float)
	def changedRadZ(self, _value):
		"""Obsluguje zmiane polosii Z."""
		self._apply_radii()

	@pyqtSlot(float)
	def changedAxisXX(self, _value):
		"""Obsluguje zmiane skladowej X dla osi X."""
		self._apply_axes()

	@pyqtSlot(float)
	def changedAxisXY(self, _value):
		"""Obsluguje zmiane skladowej Y dla osi X."""
		self._apply_axes()

	@pyqtSlot(float)
	def changedAxisXZ(self, _value):
		"""Obsluguje zmiane skladowej Z dla osi X."""
		self._apply_axes()

	@pyqtSlot(float)
	def changedAxisYX(self, _value):
		"""Obsluguje zmiane skladowej X dla osi Y."""
		self._apply_axes()

	@pyqtSlot(float)
	def changedAxisYY(self, _value):
		"""Obsluguje zmiane skladowej Y dla osi Y."""
		self._apply_axes()

	@pyqtSlot(float)
	def changedAxisYZ(self, _value):
		"""Obsluguje zmiane skladowej Z dla osi Y."""
		self._apply_axes()

	@pyqtSlot(float)
	def changedAxisZX(self, _value):
		"""Obsluguje zmiane skladowej X dla osi Z."""
		self._apply_axes()

	@pyqtSlot(float)
	def changedAxisZY(self, _value):
		"""Obsluguje zmiane skladowej Y dla osi Z."""
		self._apply_axes()

	@pyqtSlot(float)
	def changedAxisZZ(self, _value):
		"""Obsluguje zmiane skladowej Z dla osi Z."""
		self._apply_axes()

	@pyqtSlot(bool)
	def changedShowAxes(self, _checked):
		"""Obsluguje wlaczenie lub wylaczenie rysowania osi."""
		self._apply_show_axes()
