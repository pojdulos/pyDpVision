from PyQt5 import QtWidgets, QtCore, QtGui

def get_palette(color:QtGui.QColor, bgcolor:QtGui.QColor=None):
	palette = QtGui.QPalette()
	brush = QtGui.QBrush(color)
	brush.setStyle(QtCore.Qt.SolidPattern)
	palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
	return palette

class DoubleSpinBoxN(QtWidgets.QGroupBox):
	valueChanged = QtCore.pyqtSignal(tuple)  # emituje (x, y, z, ...)

	def __init__(self, count=3, orientation=QtCore.Qt.Horizontal, parent=None, labels=None):
		"""
		count        - ile spinboxów (2, 3, 4, ...)
		orientation  - Qt.Horizontal lub Qt.Vertical
		labels       - opcjonalna lista etykiet dla spinboxów
		"""
		super().__init__(parent)

		# layout
		if orientation == QtCore.Qt.Horizontal:
			layout = QtWidgets.QHBoxLayout(self)
			layout.setAlignment(QtCore.Qt.AlignLeft)
		else:
			layout = QtWidgets.QVBoxLayout(self)
			layout.setAlignment(QtCore.Qt.AlignTop)

		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(2)

		self.spinboxes = []

		for i in range(count):
			box = QtWidgets.QDoubleSpinBox(self)
			box.setRange(-9999.0, 9999.0)
			box.setDecimals(3)
			box.setSingleStep(0.1)

			if labels and i < len(labels):
				sublayout = QtWidgets.QHBoxLayout()
				label = QtWidgets.QLabel(labels[i])
				label.setAlignment(QtCore.Qt.AlignCenter)
				sublayout.addWidget(label)
				sublayout.addWidget(box)
				layout.addLayout(sublayout)
			else:
				layout.addWidget(box)

			box.valueChanged.connect(self._on_value_changed)
			self.spinboxes.append(box)

		# --- property ---
	def getValue(self):
		return tuple(box.value() for box in self.spinboxes)

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

	def setValue(self, values, emit=False):
		if values is None:
			return
		values = tuple(values)

		for i, box in enumerate(self.spinboxes):
			if i < len(values):
				was_blocked = box.blockSignals(True)
				box.setValue(values[i])
				box.blockSignals(was_blocked)

		if emit:
			self.valueChanged.emit(self.getValue())

	#value = QtCore.pyqtProperty(tuple, fget=getValue, fset=setValue, notify=valueChanged)

	# --- wspólne ustawienia ---
	def setRange(self, min_val, max_val):
		for box in self.spinboxes:
			box.setRange(min_val, max_val)

	def setSingleStep(self, step):
		for box in self.spinboxes:
			box.setSingleStep(step)

	def setDecimals(self, decimals):
		for box in self.spinboxes:
			box.setDecimals(decimals)

	# --- slot ---
	def _on_value_changed(self, _):
		self.valueChanged.emit(self.getValue())


class DoubleSpinBoxN2(DoubleSpinBoxN):
	def __init__(self, count=3, orientation=QtCore.Qt.Horizontal, parent=None, labels=None):
		super().__init__(count, orientation, parent, labels)

		if orientation == QtCore.Qt.Vertical:
			# podmieniamy layout na grid
			old_layout = self.layout()
			widgets = []
			while old_layout.count():
				item = old_layout.takeAt(0)
				w = item.widget()
				if w is not None:
					widgets.append(w)
					w.setParent(None)
			QtWidgets.QWidget().setLayout(old_layout)  # żeby nie wyciekało

			grid = QtWidgets.QGridLayout(self)
			grid.setContentsMargins(0, 0, 0, 0)
			grid.setSpacing(2)

			self.checkbox = QtWidgets.QCheckBox()
			self.checkbox.setChecked(False)

			# pierwszy spinbox na górze – cała szerokość
			grid.addWidget(self.spinboxes[0], 0, 0, 1, 2)

			# druga linia: checkbox (col=0), drugi spinbox (col=1)
			grid.addWidget(self.checkbox, 1, 0, len(self.spinboxes)-1, 1)
			if len(self.spinboxes) > 1:
				grid.addWidget(self.spinboxes[1], 1, 1)

			# kolejne spinboxy w prawej kolumnie
			for i in range(2, len(self.spinboxes)):
				grid.addWidget(self.spinboxes[i], i, 1)

			self.setLayout(grid)
			self.checkbox.toggled.connect(self._on_checkbox_toggled)
			self._on_checkbox_toggled(self.checkbox.isChecked())

		else:
			# w poziomym układzie nie kombinujemy – po prostu checkbox na początku
			self.checkbox = QtWidgets.QCheckBox()
			layout = self.layout()
			layout.insertWidget(0, self.checkbox)
			self.checkbox.toggled.connect(self._on_checkbox_toggled)
			self._on_checkbox_toggled(self.checkbox.isChecked())

	def _on_checkbox_toggled(self, checked):
		for i, box in enumerate(self.spinboxes):
			box.setEnabled(i == 0 or not checked)

	def getValue(self):
		if hasattr(self, "checkbox") and self.checkbox.isChecked():
			# checkbox aktywny → zwielokrotniona wartość z pierwszego spinboxa
			v = self.spinboxes[0].value()
			return tuple(v for _ in self.spinboxes)
		else:
			# normalny tryb → wszystkie wartości
			return tuple(box.value() for box in self.spinboxes)

	def setLockedToFirst(self, value:bool=True):
		if hasattr(self, "checkbox"):
			self.checkbox.setChecked(value)
	