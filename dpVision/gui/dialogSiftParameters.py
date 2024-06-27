from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

class DialogSiftParameters(QDialog):
	def __init__(self, parent=None, nfeatures=0, nOctaveLayers=3, contrastThreshold=0.04, edgeThreshold=10.0, sigma=1.6, factor=1):
		super( DialogSiftParameters, self ).__init__( parent )
		formLayout = QFormLayout()

		self.input1 = QSpinBox(self)
		self.input1.setValue(nfeatures)
		formLayout.addRow("nfeatures:", self.input1)

		self.input2 = QSpinBox(self)
		self.input2.setValue(nOctaveLayers)
		formLayout.addRow("nOctaveLayers:", self.input2)

		self.input3 = QDoubleSpinBox(self)
		self.input3.setValue(contrastThreshold)
		formLayout.addRow("contrastThreshold:", self.input3)

		self.input4 = QDoubleSpinBox(self)
		self.input4.setValue(edgeThreshold)
		formLayout.addRow("edgeThreshold:", self.input4)

		self.input5 = QDoubleSpinBox(self)
		self.input5.setValue(sigma)
		formLayout.addRow("Sigma:", self.input5)

		self.input6 = QSpinBox(self)
		self.input6.setValue(factor)
		formLayout.addRow("Factor:", self.input6)
		self.input6.setDisabled(True)

		okButton = QPushButton("OK", self)
		cancelButton = QPushButton("Cancel", self)

		okButton.clicked.connect(self.accept)
		cancelButton.clicked.connect(self.reject)

		layout = QVBoxLayout()
		layout.addLayout(formLayout)
		layout.addWidget(okButton)
		layout.addWidget(cancelButton)
		
		self.setLayout(layout)

	def get_fields(self, as_dict=False):
		nfeatures = self.input1.value()
		nOctaveLayers = self.input2.value()
		contrastThreshold = self.input3.value()
		edgeThreshold = self.input4.value()
		sigma = self.input5.value()
		factor = self.input6.value()
		if as_dict:
			return {
				'nfeatures':nfeatures, 
				'nOctaveLayers':nOctaveLayers, 
				'contrastThreshold':contrastThreshold, 
				'edgeThreshold':edgeThreshold, 
				'sigma':sigma, 
				'factor':factor }
		else:
			return nfeatures, nOctaveLayers, contrastThreshold, edgeThreshold, sigma, factor
