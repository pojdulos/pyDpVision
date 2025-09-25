# -*- coding: utf-8 -*-
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from ..	import AP,Transform

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

class PropTransform(PropWidget):
	def __init__(self, _obj:Transform, parent=None):
		super(PropTransform, self).__init__(parent)
		self.obj_ref = weakref.ref(_obj)
		self.setupUi()
		self.connect_signals()
		self.resize(self.layout().sizeHint())

	def connect_signals(self):
		# self.clearButton.clicked.connect(self.clearMatrix)
		# self.copyButton.clicked.connect(self.copyToClipboard)
		# self.pasteButton.clicked.connect(self.pasteFromClipboard)
		
		self.groupBox_quaternion.valueChanged.connect(self.changedQua)
		self.groupBox_euler.valueChanged.connect(self.changedEul)
		self.groupBox_translation.valueChanged.connect(self.changedTra)
		self.groupBox_scale.valueChanged.connect(self.changedSca)
		
		# self.originRadioPoint.toggled.connect(self.onOriginRadio)
		# self.originRadioBB.toggled.connect(self.onOriginRadio)
		# self.originRadioWeight.toggled.connect(self.onOriginRadio)
		# self.originRadioObj.toggled.connect(self.onOriginRadio)
		# self.originX.valueChanged.connect(self.onOriginPointValueChanged)
		# self.originY.valueChanged.connect(self.onOriginPointValueChanged)
		# self.originZ.valueChanged.connect(self.onOriginPointValueChanged)

		# self.rotButton.clicked.connect(self.onRotButton)
		# self.showScrewCheckBox.toggled.connect(self.onShowScrewCheckBox)


	@staticmethod
	def	create(m, parent=0):
		return	PropWidget.build([PropTransform(m), PropBaseObject(m)], parent)

	def updateEuler(self, m_trans:Transform):
		rot:tuple = m_trans.getEulerAnglesDeg()
		self.groupBox_euler.setValue(rot)

	def	updateQuat(self, m_trans:Transform):
		qua:tuple	=	m_trans.getRotation()
		self.groupBox_quaternion.setValue(qua)#.as_quat())  # zwraca [x,y,z,w]

	def updateTranslation(self, m_trans:Transform):
		tra:tuple = m_trans.getTranslation()
		self.groupBox_translation.setValue(tra)

	def updateScale(self, m_trans:Transform):
		s:tuple = m_trans.getScale()
		lock:bool = m_trans.m_lock_scale
		self.groupBox_scale.setValue(s)
		self.groupBox_scale.setLockedToFirst(lock)

	def	updateMatrix(self, m_trans:Transform):
		mat	= m_trans.toNumPy()
		self.matrixWidget.setValue(mat)

	def	updateProperties(self):
		m_trans	=	self.obj_ref()
		if	m_trans	is	None:
			return

		self.updateMatrix(m_trans)
		self.updateEuler(m_trans)
		self.updateQuat(m_trans)
		self.updateScale(m_trans)
		self.updateTranslation(m_trans)

		# self.showScrewCheckBox.blockSignals(True)
		# self.showScrewCheckBox.setChecked(m_trans.m_show_screw)
		# self.showScrewCheckBox.blockSignals(False)

	def changedQua(self, d):
		m_trans: Transform = self.obj_ref()
		if not isinstance(self.sender(), MultiSpinBox):
			return

		m_trans.setRotation(d)

		self.updateMatrix(m_trans)
		self.updateEuler(m_trans)
		AP.updateAllViews()

	def changedEul(self, roll_pitch_yaw:tuple):
		if not isinstance(self.sender(), MultiSpinBox):
			return

		m_trans = self.obj_ref()

		m_trans.fromEulerAngles(*roll_pitch_yaw)
		self.updateMatrix(m_trans)
		self.updateQuat(m_trans)
		AP.updateAllViews()


	def changedTra(self, tx_ty_tz:tuple):
		m_trans = self.obj_ref()
		if not isinstance(self.sender(), MultiSpinBox):
			return

		m_trans.setTranslation(*tx_ty_tz)
		self.updateMatrix(m_trans)
		AP.updateAllViews()

	def changedSca(self, sx_sy_sz:tuple):
		print(f"changedSca: {sx_sy_sz}")
		if not isinstance(self.sender(), MultiSpinBoxWithLock):
			return

		m_trans = self.obj_ref()
		
		m_trans.setScale(*sx_sy_sz)
		m_trans.m_lock_scale = self.groupBox_scale.isLockedToFirst()

		self.updateMatrix(m_trans)
		AP.updateAllViews()

	def onScaleCheck(self, checked: bool):
		m_trans	=	self.obj_ref()
		m_trans.m_lock_scale = checked
		m_trans.setScale(*self.groupBox_scale.getValue())
		self.updateMatrix(m_trans)
		AP.updateAllViews()


	
	# def	clearMatrix(self):
	# 	m_trans = self.obj_ref()
	# 	m_trans.reset()
	# 	self.updateProperties()
	# 	AP.updateAllViews()
	
	# def	copyToClipboard(self):
	# 	m_trans = self.obj_ref()
	# 	m_trans.copyToClipboard()

	# def	pasteFromClipboard(self):
	# 	m_trans = self.obj_ref()
	# 	m_trans.pasteFromClipboard()
	# 	self.updateProperties()
	# 	AP.updateAllViews()

	# def	onRotButton(self):
	# 	pass


	# @pyqtSlot(float)
	# def	onOriginPointValueChanged(self,d):
	# 	m_trans	=	self.obj_ref()
	# 	edit	=	self.sender()
	# 	if	isinstance(edit,	QDoubleSpinBox)	and	(edit	==	self.originX	or	edit	==	self.originY	or	edit	==	self.originZ):
	# 		m_trans.m_origin	=	[self.originX.value(),	self.originY.value(),	self.originZ.value()]

	# @pyqtSlot(bool)
	# def	onShowScrewCheckBox(self, b):
	# 	m_trans = self.obj_ref()
	# 	m_trans.m_show_screw = b
	# 	AP.updateAllViews()

	# @pyqtSlot(bool)
	# def	onOriginRadio(self,b):
	# 	m_trans = self.obj_ref()
	# 	radio	=	self.sender()
	# 	if	not	isinstance(radio,	QRadioButton):	return
	# 	if	radio	==	self.originRadioObj:
	# 		pass
	# 	elif	radio	==	self.originRadioBB:
	# 		_b,	_min,	_max	=	m_trans.getBB()
			
	# 		pass
	# 	elif	radio	==	self.originRadioWeight:
	# 		pass
	# 	elif	radio	==	self.originRadioPoint:
	# 		self.originX.setEnabled(	b	)
	# 		self.originY.setEnabled(	b	)
	# 		self.originZ.setEnabled(	b	)
	# 		m_trans.m_origin	=	[self.originX.value(),	self.originY.value(),	self.originZ.value()]	if	b	else	[0.,0.,0.]
		
		
	# def buildMatrixSection(self):
	# 	# Główny layout sekcji macierzy
	# 	self.matrixSectionLayout = QVBoxLayout()
	# 	self.matrixSectionLayout.setContentsMargins(0, 0, 0, 0)
	# 	self.matrixSectionLayout.setSpacing(0)

	# 	# Pasek z labelką i przyciskami
	# 	self.matrixBarLayout = QHBoxLayout()
	# 	self.matrixBarLayout.setContentsMargins(0, 0, 0, 0)
	# 	self.matrixBarLayout.setSpacing(0)

	# 	self.matrixLabel = QLabel()
	# 	self.matrixLabel.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignVCenter)
	# 	self.matrixBarLayout.addWidget(self.matrixLabel)

	# 	# Przyciski
	# 	self.clearButton = QPushButton()
	# 	self.clearButton.setMaximumSize(QSize(24, 16777215))
	# 	clear_icon = QIcon()
	# 	clear_icon.addPixmap(QPixmap(":/icons/Erase.ico"), QIcon.Normal, QIcon.Off)
	# 	self.clearButton.setIcon(clear_icon)
	# 	self.matrixBarLayout.addWidget(self.clearButton)

	# 	self.copyButton = QPushButton()
	# 	self.copyButton.setMaximumSize(QSize(24, 16777215))
	# 	copy_icon = QIcon()
	# 	copy_icon.addPixmap(QPixmap(":/icons/Copy.ico"), QIcon.Normal, QIcon.Off)
	# 	self.copyButton.setIcon(copy_icon)
	# 	self.matrixBarLayout.addWidget(self.copyButton)

	# 	self.pasteButton = QPushButton()
	# 	self.pasteButton.setMaximumSize(QSize(24, 16777215))
	# 	paste_icon = QIcon()
	# 	paste_icon.addPixmap(QPixmap(":/icons/Paste.ico"), QIcon.Normal, QIcon.Off)
	# 	self.pasteButton.setIcon(paste_icon)
	# 	self.matrixBarLayout.addWidget(self.pasteButton)

	# 	self.matrixSectionLayout.addLayout(self.matrixBarLayout)
	# 	# Tabela macierzy
	# 	self.matrixTable = QTableWidget()
	# 	self.matrixTable.setRowCount(4)
	# 	self.matrixTable.setColumnCount(4)
	# 	self.matrixTable.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
	# 	self.matrixTable.setMaximumWidth(400)  # np. limit szerokości
	# 	self.matrixTable.setMaximumHeight(100)

	# 	header = self.matrixTable.horizontalHeader()
	# 	header.setSectionResizeMode(QHeaderView.Stretch)
	# 	header.setMinimumSectionSize(45)  # minimalna szerokość kolumny
	# 	header.setMaximumSectionSize(100) # opcjonalnie limit szerokości kolumny
	# 	header.setHighlightSections(False)
	# 	self.matrixTable.horizontalHeader().setVisible(False)		

	# 	self.matrixTable.verticalHeader().setVisible(False)
	# 	self.matrixTable.verticalHeader().setDefaultSectionSize(20)
	# 	self.matrixTable.verticalHeader().setHighlightSections(False)
	# 	self.matrixTable.verticalHeader().setMinimumSectionSize(20)


	# 	font = QFont()
	# 	font.setPointSize(7)
	# 	self.matrixTable.setFont(font)
	# 	self.matrixTable.setFrameShape(QFrame.StyledPanel)
	# 	self.matrixTable.setFrameShadow(QFrame.Sunken)
	# 	self.matrixTable.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
	# 	self.matrixTable.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
	# 	self.matrixTable.setAutoScroll(False)
	# 	self.matrixTable.setDragDropOverwriteMode(False)
	# 	self.matrixTable.setTextElideMode(Qt.ElideNone)
	# 	self.matrixTable.setGridStyle(Qt.SolidLine)
	# 	self.matrixTable.setWordWrap(False)
	# 	self.matrixTable.setCornerButtonEnabled(False)
	# 	self.matrixTable.setRowCount(4)
	# 	self.matrixTable.setColumnCount(4)
	# 	self.matrixTable.setObjectName("matrixTable")

	# 	self.matrixSectionLayout.addWidget(self.matrixTable)

	# 	# Dodaj całość do głównego layoutu
	# 	self.layout_transformGroup.addLayout(self.matrixSectionLayout)

	def buildMatrixSection(self):
		self.matrixWidget = MatrixWidget(self.transformGroup)
		self.matrixWidget.valueChanged.connect(self.onMatrixEdited)
		self.layout_transformGroup.addWidget(self.matrixWidget)


	def onMatrixEdited(self, mat: np.ndarray):
		m_trans = self.obj_ref()
		if m_trans is not None:
			m_trans.fromNumPy(mat)
			self.updateEuler(m_trans)
			self.updateQuat(m_trans)
			self.updateScale(m_trans)
			self.updateTranslation(m_trans)
			AP.updateAllViews()


	def buildTranslScaleSection(self):
		#self.widget_transl_scale_section = QWidget(self.transformGroup)
		self.layout_transl_scale_section = QHBoxLayout()##self.widget_transl_scale_section)

		self.groupBox_scale = MultiSpinBoxWithLock(count=3, labels=['x:', 'y:', 'z:'])
		self.groupBox_scale.setDecimals(3)
		self.groupBox_scale.setSingleStep(0.1)
		self.groupBox_scale.setRange(-9999.0, 9999.0)
		self.groupBox_scale.setPalette((QColor(255, 0, 0), QColor(0, 128, 0), QColor(0, 0, 255)))
		self.groupBox_scale.setLockedToFirst(True)  # domyślnie "lock aspect ratio"
		self.groupBox_scale.setPrefix(("⨯ ", "⨯ ", "⨯ "))

		self.layout_transl_scale_section.addWidget(self.groupBox_scale)
		
		self.groupBox_translation = MultiSpinBox(count=3, labels=['X:', 'Y:', 'Z:'])
		self.groupBox_translation.setDecimals(3)
		self.groupBox_translation.setSingleStep(0.1)
		self.groupBox_translation.setRange(-9999.0, 9999.0)
		self.groupBox_translation.setPalette((QColor(255, 0, 0), QColor(0, 128, 0), QColor(0, 0, 255)))

		self.layout_transl_scale_section.addWidget(self.groupBox_translation)
		
		#self.layout_transformGroup.addWidget(self.widget_transl_scale_section)
		self.layout_transformGroup.addLayout(self.layout_transl_scale_section)

	def buildEulerSection(self):
		# Euler
		#self.widget_angle_section = QWidget(self.transformGroup)
		self.layout_angle_section = QHBoxLayout()#self.widget_angle_section)
		
		self.groupBox_euler = MultiSpinBox(count=3)
		self.groupBox_euler.setDecimals(3)
		self.groupBox_euler.setSingleStep(0.1)
		self.groupBox_euler.setRange(-9999.0, 9999.0)
		self.groupBox_euler.setPalette((QColor(255, 0, 0), QColor(0, 128, 0), QColor(0, 0, 255)))
		self.groupBox_euler.setSuffix(("°", "°", "°"))
		self.layout_angle_section.addWidget(self.groupBox_euler)

		self.groupBox_quaternion = MultiSpinBox(count=4, labels=['w:', 'x:', 'y:', 'z:'])
		self.groupBox_quaternion.setDecimals(3)
		self.groupBox_quaternion.setSingleStep(0.1)
		self.groupBox_quaternion.setRange(-9999.0, 9999.0)
		self.groupBox_quaternion.setPalette((QColor(0, 0, 0), QColor(255, 0, 0), QColor(0, 128, 0), QColor(0, 0, 255)))
		
		self.layout_angle_section.addWidget(self.groupBox_quaternion)
		
		#self.layout_transformGroup.addWidget(self.widget_angle_section)
		self.layout_transformGroup.addLayout(self.layout_angle_section)

	# def buildOriginSection(self):
	# 	# Origin
	# 	self.originGroup = QGroupBox(self.transformGroup)
	# 	self.horizontalLayout_10 = QHBoxLayout(self.originGroup)
	# 	self.line_3 = QFrame(self.originGroup)
	# 	self.horizontalLayout_10.addWidget(self.line_3)
	# 	self.originType = QWidget(self.originGroup)
	# 	self.verticalLayout_3 = QVBoxLayout(self.originType)
	# 	self.originRadioObj = QRadioButton(self.originType)
	# 	self.verticalLayout_3.addWidget(self.originRadioObj)
	# 	self.originRadioPoint = QRadioButton(self.originType)
	# 	self.verticalLayout_3.addWidget(self.originRadioPoint)
	# 	self.originRadioBB = QRadioButton(self.originType)
	# 	self.verticalLayout_3.addWidget(self.originRadioBB)
	# 	self.originRadioWeight = QRadioButton(self.originType)
	# 	self.verticalLayout_3.addWidget(self.originRadioWeight)
	# 	self.horizontalLayout_10.addWidget(self.originType)
	# 	self.originCoords = QWidget(self.originGroup)
	# 	self.verticalLayout = QVBoxLayout(self.originCoords)
	# 	self.originX = QDoubleSpinBox(self.originCoords)
	# 	self.verticalLayout.addWidget(self.originX)
	# 	self.originY = QDoubleSpinBox(self.originCoords)
	# 	self.verticalLayout.addWidget(self.originY)
	# 	self.originZ = QDoubleSpinBox(self.originCoords)
	# 	self.verticalLayout.addWidget(self.originZ)
	# 	self.horizontalLayout_10.addWidget(self.originCoords)
	# 	self.line_2 = QFrame(self.originGroup)
	# 	self.horizontalLayout_10.addWidget(self.line_2)
	# 	self.widget_5 = QWidget(self.originGroup)
	# 	self.verticalLayout_4 = QVBoxLayout(self.widget_5)
	# 	self.clearButton_2 = QPushButton(self.widget_5)
	# 	self.verticalLayout_4.addWidget(self.clearButton_2)
	# 	self.copyButton_2 = QPushButton(self.widget_5)
	# 	self.verticalLayout_4.addWidget(self.copyButton_2)
	# 	self.pasteButton_2 = QPushButton(self.widget_5)
	# 	self.verticalLayout_4.addWidget(self.pasteButton_2)
	# 	self.horizontalLayout_10.addWidget(self.widget_5)
	# 	self.main_layout.addWidget(self.originGroup)

	# def buildTreeViewSection(self):
	# 	# TreeView
	# 	self.treeView = QTreeView(self.transformGroup)
	# 	self.main_layout.addWidget(self.treeView)

	def setupUi(self):
		self.setObjectName("PropTransform")
		sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
		sizePolicy.setHorizontalStretch(0)
		sizePolicy.setVerticalStretch(0)
		sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
		self.setSizePolicy(sizePolicy)

		self.layout_main = QVBoxLayout(self)
		self.layout_main.setContentsMargins(0, 0, 0, 0)
		self.layout_main.setSpacing(0)
		self.layout_main.setObjectName("layout_main")

		self.transformGroup = QGroupBox(self)
		self.transformGroup.setObjectName("transformGroup")
		self.transformGroup.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
		self.transformGroup.setMaximumSize(QSize(200, 16777215))
		#self.transformGroup.setMinimumSize(QSize(200, 0))
		
		self.layout_transformGroup = QVBoxLayout(self.transformGroup)
		self.layout_transformGroup.setContentsMargins(5, 5, 5, 5)
		self.layout_transformGroup.setSpacing(5)
		self.layout_transformGroup.setObjectName("layout_transformGroup")

		self.buildMatrixSection()
		self.buildTranslScaleSection()
		self.buildEulerSection()
		# self.buildTreeViewSection()
		# self.buildOriginSection()

		self.layout_main.addWidget(self.transformGroup)
		self.retranslateUi()

	def retranslateUi(self):
		_translate = QCoreApplication.translate
		self.setWindowTitle(_translate("PropTransform", "Form"))
		self.transformGroup.setTitle(_translate("PropTransform", "Transformation"))

		self.groupBox_scale.setTitle(_translate("PropTransform", "scale"))
		self.groupBox_translation.setTitle(_translate("PropTransform", "translation"))
		self.groupBox_euler.setTitle(_translate("PropTransform", "euler"))
		self.groupBox_quaternion.setTitle(_translate("PropTransform", "quaternion"))

		# self.showScrewCheckBox.setText(_translate("PropTransform", "show screw"))
		# self.originGroup.setTitle(_translate("PropTransform", "origin"))
		# self.originRadioObj.setText(_translate("PropTransform", "obj[0,0,0]"))
		# self.originRadioPoint.setText(_translate("PropTransform", "point coords:"))
		# self.originRadioBB.setText(_translate("PropTransform", "bbox ctr"))
		# self.originRadioWeight.setText(_translate("PropTransform", "weight ctr"))
		# self.originX.setPrefix(_translate("PropTransform", "X: "))
		# self.originY.setPrefix(_translate("PropTransform", "Y: "))
		# self.originZ.setPrefix(_translate("PropTransform", "Z: "))
		# self.clearButton_2.setToolTip(_translate("PropTransform", "clear transformation"))
		# self.copyButton_2.setToolTip(_translate("PropTransform", "copy matrix to clipboard"))
		# self.pasteButton_2.setToolTip(_translate("PropTransform", "paste matrix from clipboard"))
		# self.internalAxisRadio.setText(_translate("PropTransform", "internal axis"))
		# self.externalAxisRadio.setText(_translate("PropTransform", "external axis"))
		# self.axisCombo.setItemText(0, _translate("PropTransform", "x"))
		# self.axisCombo.setItemText(1, _translate("PropTransform", "y"))
		# self.axisCombo.setItemText(2, _translate("PropTransform", "z"))
		# self.angleSpinBox.setSuffix(_translate("PropTransform", "°"))
		# self.rotButton.setText(_translate("PropTransform", "rotate"))
