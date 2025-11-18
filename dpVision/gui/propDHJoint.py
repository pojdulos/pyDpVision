# -*- coding: utf-8 -*-
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from ..	import AP, DHJoint

from .propWidget import PropWidget
from .propBaseObject import PropBaseObject
import weakref
from .multiSpinBox import MultiSpinBox,MultiSpinBoxWithLock
from .matrixWidget import MatrixWidget
import numpy as np

def get_palette(color:QColor, bgcolor:QColor=None):
	palette = QPalette()
	brush = QBrush(color)
	brush.setStyle(Qt.SolidPattern)
	palette.setBrush(QPalette.Active, QPalette.Text, brush)
	return palette

class PropDHJoint(PropWidget):
	def __init__(self, _obj:DHJoint, parent=None):
		super(PropDHJoint, self).__init__(parent)
		self.obj_ref = weakref.ref(_obj)
		self.setupUi()
		self.connect_signals()
		self.resize(self.layout().sizeHint())

	def connect_signals(self):
		pass

	@staticmethod
	def	create(m, parent=0):
		return	PropWidget.build([PropDHJoint(m), PropBaseObject(m)], parent)

	def	updateMatrix(self, m_trans:DHJoint):
		mat	= m_trans.toNumPy()
		self.matrixWidget.setValue(mat)

	def	updateDH(self, m_trans:DHJoint):
		self.dh_theta_spinbox.blockSignals(True)
		self.dh_theta_slider.blockSignals(True)
		self.dh_a_spinbox.blockSignals(True)
		self.dh_a_slider.blockSignals(True)
		self.dh_d_spinbox.blockSignals(True)
		self.dh_d_slider.blockSignals(True)
		self.dh_alpha_spinbox.blockSignals(True)
		self.dh_alpha_slider.blockSignals(True)

		self.dh_theta_spinbox.setMinimum(m_trans.theta_limits[0] if m_trans.theta_limits else -180.0)
		self.dh_theta_spinbox.setMaximum(m_trans.theta_limits[1] if m_trans.theta_limits else 180.0)
		self.dh_theta_spinbox.setValue(np.degrees(m_trans.theta))

		self.dh_theta_slider.setMinimum(int(m_trans.theta_limits[0]*1000) if m_trans.theta_limits else -180000)
		self.dh_theta_slider.setMaximum(int(m_trans.theta_limits[1]*1000) if m_trans.theta_limits else 180000)
		self.dh_theta_slider.setValue(int(np.degrees(m_trans.theta)*1000))

		default_a_limits = [0.0, 100.0]
		self.dh_a_spinbox.setMinimum(m_trans.a_limits[0] if m_trans.a_limits else default_a_limits[0])
		self.dh_a_spinbox.setMaximum(m_trans.a_limits[1] if m_trans.a_limits else default_a_limits[1])
		self.dh_a_spinbox.setValue(m_trans.a)

		self.dh_a_slider.setMinimum(int(m_trans.a_limits[0]*1000) if m_trans.a_limits else int(default_a_limits[0]*1000))
		self.dh_a_slider.setMaximum(int(m_trans.a_limits[1]*1000) if m_trans.a_limits else int(default_a_limits[1]*1000))
		self.dh_a_slider.setValue(int(m_trans.a * 1000))

		default_d_limits = [-100.0, 100.0]	
		self.dh_d_spinbox.setMinimum(m_trans.d_limits[0] if m_trans.d_limits else default_d_limits[0])
		self.dh_d_spinbox.setMaximum(m_trans.d_limits[1] if m_trans.d_limits else default_d_limits[1])
		self.dh_d_spinbox.setValue(m_trans.d)

		self.dh_d_slider.setMinimum(int(m_trans.d_limits[0]*1000) if m_trans.d_limits else int(default_d_limits[0]*1000))
		self.dh_d_slider.setMaximum(int(m_trans.d_limits[1]*1000) if m_trans.d_limits else int(default_d_limits[1]*1000))
		self.dh_d_slider.setValue(int(m_trans.d * 1000))

		self.dh_alpha_spinbox.setMinimum(m_trans.alpha_limits[0] if m_trans.alpha_limits else -180.0)
		self.dh_alpha_spinbox.setMaximum(m_trans.alpha_limits[1] if m_trans.alpha_limits else 180.0)
		self.dh_alpha_spinbox.setValue(np.degrees(m_trans.alpha))

		self.dh_alpha_slider.setMinimum(int(m_trans.alpha_limits[0]*1000) if m_trans.alpha_limits else -180000)
		self.dh_alpha_slider.setMaximum(int(m_trans.alpha_limits[1]*1000) if m_trans.alpha_limits else 180000)
		self.dh_alpha_slider.setValue(int(np.degrees(m_trans.alpha)*1000))
		
		self.dh_d_slider.setEnabled(m_trans.d_variable or self.dh_d_checkbox.isChecked())
		self.dh_d_spinbox.setEnabled(m_trans.d_variable or self.dh_d_checkbox.isChecked())
		self.dh_d_checkbox.setDisabled(m_trans.d_variable)

		self.dh_theta_slider.setEnabled(m_trans.theta_variable or self.dh_theta_checkbox.isChecked())
		self.dh_theta_spinbox.setEnabled(m_trans.theta_variable or self.dh_theta_checkbox.isChecked())
		self.dh_theta_checkbox.setDisabled(m_trans.theta_variable)

		self.dh_a_slider.setEnabled(self.dh_a_checkbox.isChecked())
		self.dh_a_spinbox.setEnabled(self.dh_a_checkbox.isChecked())

		self.dh_alpha_slider.setEnabled(self.dh_alpha_checkbox.isChecked())
		self.dh_alpha_spinbox.setEnabled(self.dh_alpha_checkbox.isChecked())

		self.dh_theta_spinbox.blockSignals(False)
		self.dh_theta_slider.blockSignals(False)
		self.dh_a_spinbox.blockSignals(False)
		self.dh_a_slider.blockSignals(False)
		self.dh_d_spinbox.blockSignals(False)
		self.dh_d_slider.blockSignals(False)
		self.dh_alpha_spinbox.blockSignals(False)
		self.dh_alpha_slider.blockSignals(False)
		

	def	updateProperties(self):
		m_trans = self.obj_ref()
		if m_trans is None:
			return

		self.updateDH(m_trans)
		self.updateMatrix(m_trans)

	def on_dh_theta_value_changed(self, value:float):
		m_trans: DHJoint = self.obj_ref()
		# if not isinstance(self.sender(), QDoubleSpinBox):
		# 	return

		#print(f"spinbox changed, theta= {value}")
		m_trans.set_theta_deg(value)
		
		self.updateMatrix(m_trans)
		AP.updateAllViews()

	def on_dh_d_value_changed(self, value:float):
		m_trans: DHJoint = self.obj_ref()
		# if not isinstance(self.sender(), QDoubleSpinBox):
		# 	return

		#print(f"spinbox changed, d= {value}")
		m_trans.set_d(value)
		
		self.updateMatrix(m_trans)
		AP.updateAllViews()

	def on_dh_a_value_changed(self, value:float):
		m_trans: DHJoint = self.obj_ref()
		# if not isinstance(self.sender(), QDoubleSpinBox):
		# 	return

		#print(f"spinbox changed, a= {value}")
		m_trans.set_a(value)
		
		self.updateMatrix(m_trans)
		AP.updateAllViews()

	def on_dh_alpha_value_changed(self, value:float):
		m_trans: DHJoint = self.obj_ref()
		# if not isinstance(self.sender(), QDoubleSpinBox):
		# 	return

		#print(f"spinbox changed, alpha= {value}")
		m_trans.set_alpha_deg(value)
		
		self.updateMatrix(m_trans)
		AP.updateAllViews()


	def buildMatrixSection(self):
		self.matrixWidget = MatrixWidget()
		self.matrixWidget.valueChanged.connect(self.onMatrixEdited)
		self.layout_transformGroup.addWidget(self.matrixWidget)


	def onMatrixEdited(self, mat: np.ndarray):
		print("Edycja macierzy zabroniona w przypadku DHJoint.")
		self.updateMatrix(self.obj_ref())
		pass
		# m_trans = self.obj_ref()
		# if m_trans is not None:
		# 	m_trans.fromNumPy(mat)
		# 	# self.updateEuler(m_trans)
		# 	# self.updateQuat(m_trans)
		# 	# self.updateScale(m_trans)
		# 	# self.updateTranslation(m_trans)
		# 	AP.updateAllViews()

	def getDHWidget(self):
		"""
		Tworzy widget do edycji parametrów Denavit-Hartenberg:
		θ (theta) - kąt obrotu wokół osi Z [stopnie]
		d - przesunięcie wzdłuż osi Z
		a - długość ogniwa (przesunięcie wzdłuż osi X)
		α (alpha) - skręcenie wokół osi X [stopnie]
		"""
		dh_widget = QGroupBox("DH Parameters")
		dh_layout = QVBoxLayout(dh_widget)
		dh_layout.setContentsMargins(5, 5, 5, 5)
		dh_layout.setSpacing(3)

		# Funkcja pomocnicza do tworzenia wiersza z etykietą, spinboxem i sliderem
		def create_dh_row(label_text: str, min_val: float, max_val: float, 
						  decimals: int = 3, suffix: str = "", color: QColor = None):
			row_layout = QVBoxLayout()
			row_layout.setSpacing(5)
			
			row1_layout = QHBoxLayout()
			# Etykieta
			label = QLabel(label_text)
			label.setMinimumWidth(20)
			if color:
				label.setStyleSheet(f"color: {color.name()};")
			row1_layout.addWidget(label)
			
			# SpinBox
			spinbox = QDoubleSpinBox()
			spinbox.setDecimals(decimals)
			spinbox.setRange(min_val, max_val)
			spinbox.setSingleStep((max_val - min_val) / 100.0)
			spinbox.setValue(0.0)
			if suffix:
				spinbox.setSuffix(suffix)
			if color:
				palette = get_palette(color)
				spinbox.setPalette(palette)
			spinbox.setMinimumWidth(80)
			row1_layout.addWidget(spinbox, stretch=1)
			
			checkbox = QCheckBox("force")
			checkbox.setEnabled(True)
			checkbox.setChecked(False)
			row1_layout.addWidget(checkbox)
			
			row_layout.addLayout(row1_layout)

			# Slider
			slider = QSlider(Qt.Horizontal)
			slider.setRange(int(min_val * 1000), int(max_val * 1000))  # rozdzielczość 0.001
			slider.setValue(0)
			slider.setMinimumWidth(100)
			row_layout.addWidget(slider, stretch=2)
			
			# Połączenie sygnałów
			def on_spinbox_changed(value):
				slider.blockSignals(True)
				slider.setValue(int(value * 1000))
				slider.blockSignals(False)
			
			def on_slider_changed(value):
				spinbox.blockSignals(True)
				spinbox.setValue(value / 1000.0)
				spinbox.blockSignals(False)
			
			def on_checkbox_changed(state):
				self.updateDH(self.obj_ref())
				# slider.setEnabled(state == Qt.Checked)
				# spinbox.setEnabled(state == Qt.Checked)

			spinbox.valueChanged.connect(on_spinbox_changed)
			slider.valueChanged.connect(on_slider_changed)
			checkbox.stateChanged.connect(on_checkbox_changed)

			return row_layout, spinbox, slider, checkbox

		# θ (theta) - kąt obrotu wokół osi Z [-180°, 180°]
		theta_layout, self.dh_theta_spinbox, self.dh_theta_slider, self.dh_theta_checkbox = create_dh_row(
			"θ:", -180.0, 180.0, decimals=2, suffix="°", color=QColor(255, 0, 0)
		)
		dh_layout.addLayout(theta_layout)

		# d - przesunięcie wzdłuż osi Z [-1000, 1000]
		d_layout, self.dh_d_spinbox, self.dh_d_slider, self.dh_d_checkbox = create_dh_row(
			"d:", -100.0, 100.0, decimals=3, color=QColor(0, 128, 0)
		)
		dh_layout.addLayout(d_layout)

		# a - długość ogniwa (przesunięcie wzdłuż osi X) [0, 1000]
		a_layout, self.dh_a_spinbox, self.dh_a_slider, self.dh_a_checkbox = create_dh_row(
			"a:", 0.0, 100.0, decimals=3, color=QColor(0, 0, 255)
		)
		dh_layout.addLayout(a_layout)

		# α (alpha) - skręcenie wokół osi X [-180°, 180°]
		alpha_layout, self.dh_alpha_spinbox, self.dh_alpha_slider, self.dh_alpha_checkbox = create_dh_row(
			"α:", -180.0, 180.0, decimals=2, suffix="°", color=QColor(128, 0, 128)
		)
		dh_layout.addLayout(alpha_layout)

		return dh_widget


	def buildDHSection(self):
		self.layout_DH_section = QHBoxLayout()

		self.groupBox_DH = self.getDHWidget()
		self.layout_DH_section.addWidget(self.groupBox_DH)
		
		self.dh_theta_spinbox.valueChanged.connect(self.on_dh_theta_value_changed)
		self.dh_theta_slider.valueChanged.connect(lambda val:self.on_dh_theta_value_changed(val/1000))
		self.dh_d_spinbox.valueChanged.connect(self.on_dh_d_value_changed)
		self.dh_d_slider.valueChanged.connect(lambda val:self.on_dh_d_value_changed(val/1000))
		self.dh_a_spinbox.valueChanged.connect(self.on_dh_a_value_changed)
		self.dh_a_slider.valueChanged.connect(lambda val:self.on_dh_a_value_changed(val/1000))
		self.dh_alpha_spinbox.valueChanged.connect(self.on_dh_alpha_value_changed)
		self.dh_alpha_slider.valueChanged.connect(lambda val:self.on_dh_alpha_value_changed(val/1000))

		self.layout_transformGroup.addLayout(self.layout_DH_section)

	def getTransformGroupWidget(self):
		self.transformGroup = QGroupBox(self)
		self.transformGroup.setObjectName("transformGroup")
		self.transformGroup.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
		self.transformGroup.setMaximumSize(QSize(200, 16777215))
		#self.transformGroup.setMinimumSize(QSize(200, 0))
		
		self.layout_transformGroup = QVBoxLayout(self.transformGroup)
		self.layout_transformGroup.setContentsMargins(5, 5, 5, 5)
		self.layout_transformGroup.setSpacing(5)
		self.layout_transformGroup.setObjectName("layout_transformGroup")

		self.buildDHSection()
		self.buildMatrixSection()
		return self.transformGroup

	def setupUi(self):
		self.setObjectName("PropDHJoint")
		sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
		sizePolicy.setHorizontalStretch(0)
		sizePolicy.setVerticalStretch(0)
		sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
		self.setSizePolicy(sizePolicy)

		self.layout_main = QVBoxLayout(self)
		self.layout_main.setContentsMargins(0, 0, 0, 0)
		self.layout_main.setSpacing(0)
		self.layout_main.setObjectName("layout_main")

		self.transformGroup = self.getTransformGroupWidget()
		self.layout_main.addWidget(self.transformGroup)
		self.retranslateUi()

	def retranslateUi(self):
		_translate = QCoreApplication.translate
		self.setWindowTitle(_translate("PropDHJoint", "Form"))
		self.transformGroup.setTitle(_translate("PropDHJoint", "Transformation"))
