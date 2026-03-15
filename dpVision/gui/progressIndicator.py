from PyQt5 import uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from .. import AP

class ProgressIndicator(QWidget):
	cancel_button_pressed = pyqtSignal()

	def __init__(self, _obj, parent=None):
		super( ProgressIndicator, self ).__init__( parent )
		#uic.loadUi('dpVision/gui/forms/progressIndicator.ui', self)
		AP.loadUi('progressIndicator.ui', self)
		self.actionCancelled = False
		if hasattr(self, 'cancelButton'):
			self.cancelButton.clicked.connect(self.onCancelButton)

	def init(self, min=0, max=100, val=0, text = ""):
		self.progressBar.setMinimum(min)
		self.progressBar.setMaximum(max)
		self.progressBar.setValue(val)
		self.workInfo.setText(text)
		#self.cancelButton.hide()
		self.actionCancelled = False
		self.show()

	def setCancelVisible(self, visible):
		if hasattr(self, 'cancelButton'):
			self.cancelButton.setVisible(bool(visible))

	@pyqtSlot(int, int, int, str)
	def start(self, min_value=0, max_value=100, value=0, text=""):
		self.init(min=min_value, max=max_value, val=value, text=text)

	def onCancelButton(self):
		self.workInfo.setText("Cancelling ! Please wait...")
		self.actionCancelled = True
		self.cancel_button_pressed.emit()
		self.hide()

	@pyqtSlot(int)
	def setValue(self, value):
		self.progressBar.setValue(value)

	@pyqtSlot()
	def increase(self):
		val = self.progressBar.value()+1
		if val > self.progressBar.maximum():
			val = self.progressBar.minimum()
		self.progressBar.setValue(val)

	def setText(self, text):
		self.workInfo.setText(text)

	@pyqtSlot()
	def finish(self):
		self.hide()
