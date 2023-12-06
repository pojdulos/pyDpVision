from PyQt5 import uic
from PyQt5.QtWidgets import *

class ProgressIndicator(QWidget):
	def __init__(self, _obj, parent=None):
		super( ProgressIndicator, self ).__init__( parent )
		uic.loadUi('dpVision/ui/UiProgressIndicator.ui', self)
		self.cancelButton = QPushButton()
		self.actionCancelled = False

	def init(self, min=0, max=100, val=0, text = ""):
		self.progressBar.setMinimum(min)
		self.progressBar.setMaximum(max)
		self.progressBar.setValue(val)
		self.workInfo.setText(text)
		#self.cancelButton.hide()
		self.actionCancelled = False
		self.show()

	def onCancelButton(self):
		self.workInfo.setText("Cancelled ! Please wait...")
		self.actionCancelled = True

	def setValue(self, value):
		self.progressBar.setValue(value)

	def increase(self):
		self.progressBar.setValue(self.progressBar.value()+1)

	def setText(self, text):
		self.workInfo.setText(text)
