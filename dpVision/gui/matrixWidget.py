# matrixWidget.py
from PyQt5.QtWidgets import * #(
#    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
#    QTableWidget, QTableWidgetItem, QSizePolicy, QHeaderView, QFrame
#)
from PyQt5.QtGui import * #QFont, QIcon, QPixmap
from PyQt5.QtCore import * # Qt, QSize, pyqtSignal
import numpy as np

class MatrixWidget(QWidget):
	valueChanged = pyqtSignal(np.ndarray)   # emituje macierz 4x4 numpy

	def __init__(self, parent=None):
		super().__init__(parent)
		self._matrix = np.eye(4, dtype=float)
		self._setupUi()

	def _setupUi(self):
		mainLayout = QVBoxLayout(self)
		mainLayout.setContentsMargins(0, 0, 0, 0)
		mainLayout.setSpacing(2)

		# Pasek tytułu z przyciskami
		barLayout = QHBoxLayout()
		barLayout.setContentsMargins(0, 0, 0, 0)
		barLayout.setSpacing(2)

		self.label = QLabel("Matrix:")
		barLayout.addWidget(self.label)

		self.clearButton = QPushButton()
		self.clearButton.setMaximumSize(QSize(24, 16777215))
		self.clearButton.setIcon(QIcon(QPixmap(":/icons/Erase.ico")))
		barLayout.addWidget(self.clearButton)

		self.copyButton = QPushButton()
		self.copyButton.setMaximumSize(QSize(24, 16777215))
		self.copyButton.setIcon(QIcon(QPixmap(":/icons/Copy.ico")))
		barLayout.addWidget(self.copyButton)

		self.pasteButton = QPushButton()
		self.pasteButton.setMaximumSize(QSize(24, 16777215))
		self.pasteButton.setIcon(QIcon(QPixmap(":/icons/Paste.ico")))
		barLayout.addWidget(self.pasteButton)

		mainLayout.addLayout(barLayout)

		# Tabela 4x4
		self.table = QTableWidget(4, 4)
		self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
		self.table.setMaximumHeight(120)
		self.table.horizontalHeader().setVisible(False)
		self.table.verticalHeader().setVisible(False)

		header = self.table.horizontalHeader()
		header.setSectionResizeMode(QHeaderView.Stretch)

		font = QFont()
		font.setPointSize(7)
		self.table.setFont(font)

		self.table.setFrameShape(QFrame.StyledPanel)
		self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

		mainLayout.addWidget(self.table)

		# sygnały
		self.clearButton.clicked.connect(self.clearMatrix)
		self.copyButton.clicked.connect(self.copyToClipboard)
		self.pasteButton.clicked.connect(self.pasteFromClipboard)
		self.table.itemChanged.connect(self._on_item_changed)

		self._refresh()

	# --- API ---
	def setValue(self, mat: np.ndarray):
		"""Ustawia macierz w widżecie"""
		assert mat.shape == (4, 4)
		self._matrix = mat.copy()
		self._refresh()

	def getValue(self) -> np.ndarray:
		"""Zwraca aktualną macierz"""
		return self._matrix.copy()

	# --- Obsługa tabeli ---
	def _refresh(self):
		self.table.blockSignals(True)
		for r in range(4):
			for c in range(4):
				val = self._matrix[r, c]
				item = self.table.item(r, c)
				if item is None:
					item = QTableWidgetItem()
					self.table.setItem(r, c, item)
				item.setText(f"{val:.6f}")
			self.table.setRowHeight(r, 20)
		self.table.blockSignals(False)

	def _on_item_changed(self, item: QTableWidgetItem):
		try:
			val = float(item.text())
			self._matrix[item.row(), item.column()] = val
			self.valueChanged.emit(self._matrix.copy())
		except ValueError:
			self._refresh()

	# --- Operacje ---
	def clearMatrix(self):
		self.setValue(np.eye(4, dtype=float))
		self.valueChanged.emit(self._matrix.copy())

	def copyToClipboard(self):
		text = " ".join(f"{v:.6f}" for v in self._matrix.flatten())
		QApplication.clipboard().setText(text, QClipboard.Clipboard)

	def pasteFromClipboard(self):
		text = QApplication.clipboard().text(QClipboard.Clipboard)
		if text:
			parts = text.strip().split()
			try:
				values = [float(v) for v in parts]
				if len(values) == 16:
					mat = np.array(values, dtype=float).reshape(4, 4)
					self.setValue(mat)
					self.valueChanged.emit(self._matrix.copy())
			except ValueError:
				pass
