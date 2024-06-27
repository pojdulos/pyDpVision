from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

class DialogVolumetricMetadata(QDialog):
	def __init__(self, volum, parent=None):
		super( DialogVolumetricMetadata, self ).__init__( parent )

		self.volum = volum

		self.setWindowTitle("Volumetric Metadata")

		origin = self.volum.metadata[0].image_position_patient
		
		group1 = self.create_origin_group(origin)

		vsizeX = self.volum.metadata[1].pixel_spacing[0]
		vsizeY = self.volum.metadata[1].pixel_spacing[1]
		vsizeZ = self.volum.metadata[1].slice_distance

		group2 = self.create_pixel_spacing_group(vsizeX, vsizeY, vsizeZ)

		hboxlayout = QHBoxLayout()

		hboxlayout.addWidget(group1)
		hboxlayout.addWidget(group2)

		okButton = QPushButton("OK", self)
		cancelButton = QPushButton("Cancel", self)

		okButton.clicked.connect(self.on_ok_button)
		cancelButton.clicked.connect(self.reject)

		shape = self.volum.m_shape

		crl = f"Volume size: {shape[2]} x {shape[1]} x {shape[0]} ({vsizeX * shape[2]}mm x {vsizeY * shape[1]}mm x {vsizeZ * shape[0]}mm)"

		layout = QVBoxLayout()
		layout.addWidget(QLabel(crl))
		layout.addLayout(hboxlayout)
		layout.addWidget(okButton)
		layout.addWidget(cancelButton)

		self.setLayout(layout)

	def create_origin_group(self, origin):
		self.input1 = QDoubleSpinBox(self)
		self.input2 = QDoubleSpinBox(self)
		self.input3 = QDoubleSpinBox(self)

		self.input1.setValue(origin[0])
		self.input2.setValue(origin[1])
		self.input3.setValue(origin[2])

		formLayout1 = QFormLayout()
		formLayout1.addRow("x:", self.input1)
		formLayout1.addRow("y:", self.input2)
		formLayout1.addRow("z:", self.input3)

		group1 = QGroupBox(self)
		group1.setTitle("Origin:")
		group1.setToolTip("ImagePositionPatient and SliceLocation of first image")
		group1.setLayout(formLayout1)
		return group1

	def create_pixel_spacing_group(self, vsizeX, vsizeY, vsizeZ):
		self.input4 = QDoubleSpinBox(self)
		self.input5 = QDoubleSpinBox(self)
		self.input6 = QDoubleSpinBox(self)

		self.input4.setValue(vsizeX)
		self.input5.setValue(vsizeY)
		self.input6.setValue(vsizeZ)

		formLayout2 = QFormLayout()
		formLayout2.addRow("x:", self.input4)
		formLayout2.addRow("y:", self.input5)
		formLayout2.addRow("z:", self.input6)

		group2 = QGroupBox(self)
		group2.setTitle("Voxel spacing:")
		group2.setToolTip("PixelSpacing and SliceThickness of all images")
		group2.setLayout(formLayout2)
		return group2

	def on_ok_button(self):
		posX = self.input1.value()
		posY = self.input2.value()
		posZ = self.input3.value()

		vsizeX = self.input4.value()
		vsizeY = self.input5.value()
		vsizeZ = self.input6.value()

		#origin = self.volum.metadata[0].image_position_patient
		#delta = [ posX - origin[0], posY - origin[1], posZ - origin[2] ]

		for i in range(len(self.volum.metadata)):
			self.volum.metadata[i].image_position_patient[0] = posX
			self.volum.metadata[i].image_position_patient[1] = posY
			self.volum.metadata[i].image_position_patient[2] = posZ + vsizeZ * i
			
			self.volum.metadata[i].slice_location = self.volum.metadata[i].image_position_patient[2]

			self.volum.metadata[i].pixel_spacing[0] = vsizeX
			self.volum.metadata[i].pixel_spacing[1] = vsizeY
			self.volum.metadata[i].slice_distance = vsizeZ
			self.volum.metadata[i].slice_thickness = vsizeZ
	
		self.accept()
