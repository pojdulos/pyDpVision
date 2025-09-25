from PyQt5 import QtWidgets, QtCore, QtGui
import sip

def get_palette(color:QtGui.QColor, bgcolor:QtGui.QColor=None):
	palette = QtGui.QPalette()
	brush = QtGui.QBrush(color)
	brush.setStyle(QtCore.Qt.SolidPattern)
	palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
	return palette


class MultiSpinBoxBase(QtWidgets.QGroupBox):
	valueChanged = QtCore.pyqtSignal(tuple)

	def __init__(self, count=3, parent=None):
		super().__init__(parent)
		self.spinboxes = []
		for _ in range(count):
			box = QtWidgets.QDoubleSpinBox(self)
			box.setRange(-9999.0, 9999.0)
			box.setDecimals(3)
			box.setSingleStep(0.1)
			box.valueChanged.connect(self._on_value_changed)
			self.spinboxes.append(box)

	def getValue(self):
		return tuple(box.value() for box in self.spinboxes)

	def setValue(self, values, emit=False):
		values = tuple(values)
		for i, box in enumerate(self.spinboxes):
			if i < len(values):
				was_blocked = box.blockSignals(True)
				box.setValue(values[i])
				box.blockSignals(was_blocked)
		if emit:
			self.valueChanged.emit(self.getValue())

	def setRange(self, min_val, max_val):
		for box in self.spinboxes:
			box.setRange(min_val, max_val)

	def setSingleStep(self, step):
		for box in self.spinboxes:
			box.setSingleStep(step)

	def setDecimals(self, decimals):
		for box in self.spinboxes:
			box.setDecimals(decimals)

	def setPalette(self, palettes):
		if palettes is None:
			return
		palettes = tuple(palettes)

		for i, box in enumerate(self.spinboxes):
			if i < len(palettes):
				box.setPalette(get_palette(palettes[i]))

	def setSuffix(self, suffixes):
		if suffixes is None:
			return
		suffixes = tuple(suffixes)

		for i, box in enumerate(self.spinboxes):
			if i < len(suffixes):
				box.setSuffix(suffixes[i])

	def setPrefix(self, prefixes):
		if prefixes is None:
			return
		prefixes = tuple(prefixes)

		for i, box in enumerate(self.spinboxes):
			if i < len(prefixes):
				box.setPrefix(prefixes[i])

	def _on_value_changed(self, _):
		self.valueChanged.emit(self.getValue())

class MultiSpinBox(MultiSpinBoxBase):
	def __init__(self, count=3, orientation=QtCore.Qt.Vertical, parent=None, labels=None):
		super().__init__(count, parent)

		if orientation == QtCore.Qt.Horizontal:
			layout = QtWidgets.QHBoxLayout(self)
			layout.setAlignment(QtCore.Qt.AlignLeft)
		else:
			layout = QtWidgets.QVBoxLayout(self)
			layout.setAlignment(QtCore.Qt.AlignTop)

		layout.setContentsMargins(0,0,0,0)
		layout.setSpacing(2)

		for i, box in enumerate(self.spinboxes):
			if labels and i < len(labels):
				sub = QtWidgets.QHBoxLayout()
				lbl = QtWidgets.QLabel(labels[i])
				sub.addWidget(lbl)
				sub.addWidget(box)
				layout.addLayout(sub)
			else:
				layout.addWidget(box)

class MultiSpinBoxWithLock(MultiSpinBoxBase):
	def __init__(self, count=3, orientation=QtCore.Qt.Vertical, parent=None, labels=None):
		super().__init__(count, parent)
		self.checkbox = QtWidgets.QCheckBox(self)
		self.checkbox.setChecked(False)
		self.checkbox.toggled.connect(self._on_checkbox_toggled)

		if orientation == QtCore.Qt.Vertical:
			grid = QtWidgets.QGridLayout(self)
			grid.setContentsMargins(0,0,0,0)
			grid.setSpacing(2)

			# pierwszy spinbox – cała szerokość
			if labels and len(labels) > 0:
				lbl = QtWidgets.QLabel(labels[0])
				grid.addWidget(lbl, 0, 0)
				grid.addWidget(self.spinboxes[0], 0, 1, 1, 2)
			else:
				grid.addWidget(self.spinboxes[0], 0, 0, 1, 3)

			# druga linia: checkbox + spinbox
			grid.addWidget(self.checkbox, 1, 0, len(self.spinboxes)-1, 1)
			if len(self.spinboxes) > 1:
				if labels and len(labels) > 1:
					lbl = QtWidgets.QLabel(labels[1])
					grid.addWidget(lbl, 1, 1)
					grid.addWidget(self.spinboxes[1], 1, 2)
				else:
					grid.addWidget(self.spinboxes[1], 1, 1, 1, 2)

			# kolejne spinboxy w prawej kolumnie
			for i in range(2, len(self.spinboxes)):
				if labels and i < len(labels):
					lbl = QtWidgets.QLabel(labels[i])
					grid.addWidget(lbl, i, 1)
					grid.addWidget(self.spinboxes[i], i, 2)
				else:
					grid.addWidget(self.spinboxes[i], i, 1)
		else:
			layout = QtWidgets.QHBoxLayout(self)
			layout.setContentsMargins(0,0,0,0)
			layout.setSpacing(2)
			layout.addWidget(self.checkbox)
			for i, box in enumerate(self.spinboxes):
				if labels and i < len(labels):
					sub = QtWidgets.QHBoxLayout()
					lbl = QtWidgets.QLabel(labels[i])
					sub.addWidget(lbl)
					sub.addWidget(box)
					layout.addLayout(sub)
				else:
					layout.addWidget(box)

		self._disable_boxes(self.checkbox.isChecked())


	def _disable_boxes(self, disable:bool, first=1):
		for i, box in enumerate(self.spinboxes):
			box.setEnabled(i < first or not disable)

	def _on_checkbox_toggled(self, checked):
		self._disable_boxes(checked)
		self.valueChanged.emit(self.getValue())

	def getValue(self):
		if hasattr(self, "checkbox") and self.checkbox.isChecked():
			v = self.spinboxes[0].value()
			return tuple(v for _ in self.spinboxes)
		return super().getValue()

	def setLockedToFirst(self, value:bool=True):
		if hasattr(self, "checkbox"):
			self.checkbox.setChecked(value)

	def isLockedToFirst(self):
		if hasattr(self, "checkbox"):
			return self.checkbox.isChecked()
		return False
