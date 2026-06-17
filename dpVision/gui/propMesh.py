# -*- coding: utf-8 -*-
"""Property panel for mesh objects."""

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import (
	QColorDialog,
	QLayout,
	QSizePolicy,
	QVBoxLayout,
	QWidget,
)
from PyQt5.QtGui import QColor

from .. import AP
from .propWidget import PropWidget
from .propBaseObject import PropBaseObject
import weakref


class PropMesh(PropWidget):
	"""Edit mesh appearance."""

	def __init__(self, _obj, parent=None):
		"""Create the mesh property panel."""
		super(PropMesh, self).__init__(parent)
		AP.loadUi('propMesh.ui', self)
		self.obj_ref = weakref.ref(_obj)
		self._relax_ui_constraints()

	@staticmethod
	def create(m, parent=0):
		"""Build the full mesh property panel for the selected object."""
		return PropWidget.build([PropBaseObject(m), PropMesh(m)], parent)

	def _relax_ui_constraints(self):
		"""Remove fixed-size limits inherited from the legacy `.ui` definition."""
		for widget in (self, getattr(self, "mesh", None), getattr(self, "info", None)):
			if widget is None:
				continue
			widget.setMinimumSize(0, 0)
			widget.setMaximumSize(16777215, 16777215)
			widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

		root_layout = self.layout()
		if isinstance(root_layout, QLayout):
			self._main_container = QWidget(self)
			self._main_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
			self._main_layout = QVBoxLayout(self._main_container)
			self._main_layout.setContentsMargins(0, 0, 0, 0)
			self._main_layout.setSpacing(6)
			root_layout.removeWidget(self.mesh)
			self.mesh.setParent(self._main_container)
			self._main_layout.addWidget(self.mesh)
			root_layout.addWidget(self._main_container)

	def updateProperties(self):
		"""Refresh the panel from the current mesh state."""
		obj = self.obj_ref()
		col = obj.materials[obj.currentMaterial].diffuse + [obj.materials[obj.currentMaterial].alpha]
		qc = QColor()
		qc.setRgbF(col[0], col[1], col[2], col[3])
		self.updateDefaultColorButton(qc)

	def updateDefaultColorButton(self, col):
		"""Refresh the button preview for the mesh diffuse colour."""
		s = "background-color: rgb(" + str(col.red()) + ", " + str(col.green()) + ", " + str(col.blue()) + ");"
		self.bgColorButton.setStyleSheet(s)

	@pyqtSlot()
	def on_default_color_button(self):
		"""Open one colour picker and store the selected mesh material colour."""
		obj = self.obj_ref()
		col = obj.materials[obj.currentMaterial].diffuse + [obj.materials[obj.currentMaterial].alpha]
		qc = QColor()
		qc.setRgbF(col[0], col[1], col[2], col[3])
		color = QColorDialog.getColor(qc, self, "Select color", options=QColorDialog.ShowAlphaChannel | QColorDialog.DontUseNativeDialog)
		if color.isValid():
			obj.materials[obj.currentMaterial].diffuse = [color.redF(), color.greenF(), color.blueF()]
			obj.materials[obj.currentMaterial].alpha = color.alphaF()
			self.updateDefaultColorButton(color)
			AP.updateAllViews()


