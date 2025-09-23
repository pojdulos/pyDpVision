#	-*-	coding:	utf-8	-*-

from	abc	import	ABC,	abstractmethod
import	re
from	PyQt5	import	uic
from	PyQt5.QtGui	import	*
from	PyQt5.QtCore	import	*
from	PyQt5.QtWidgets	import	*

from	..	import	AP,Transform

from	.propWidget	import	PropWidget
from	.propBaseObject	import	PropBaseObject
import	weakref

class	PropTransform(PropWidget):
	def	__init__(self, _obj:Transform,	parent=None):
		super(PropTransform, self).__init__(parent)
		AP.loadUi('propTransform.ui', self)
		#self.createUI()

		self.obj_ref = weakref.ref(_obj)

		self.treeView.setVisible(False)
		self.resize(self.layout().sizeHint())

		self.originGroup.setVisible(False)

		self.quatW.setEnabled(True)
		self.quatX.setEnabled(True)
		self.quatY.setEnabled(True)
		self.quatZ.setEnabled(True)

		self.quatW.valueChanged.connect(self.changedQua)
		self.quatX.valueChanged.connect(self.changedQua)
		self.quatY.valueChanged.connect(self.changedQua)
		self.quatZ.valueChanged.connect(self.changedQua)


	@staticmethod
	def	create(m, parent=0):
		return	PropWidget.build([PropTransform(m), PropBaseObject(m)], parent)

	def	updateMatrix(self, m_trans:Transform):
		mat	= m_trans.toNumPy()
		self.matrixTable.blockSignals(True)
		for row in range(4):
			for	col in range(4):
				value = mat[row, col]
				item = self.matrixTable.item(row,	col)
				if	item is None:
					item = QTableWidgetItem()
					self.matrixTable.setItem(row, col, item)
				item.setText(f"{value:.6f}")
		self.matrixTable.blockSignals(False)


	def updateSpinBoxes(self, widgets:tuple, values):
		if len(widgets) != len(values):
			raise ValueError("Liczba widgetów i wartości nie jest zgodna")
		for w in widgets:
			w.blockSignals(True)
		for w, val in zip(widgets, values):
			w.setValue(val)
		for w in widgets:
			w.blockSignals(False)

	def updateEuler(self, m_trans:Transform):
		rot = m_trans.getEulerAnglesDeg()
		widgets = (self.eulerX, self.eulerY, self.eulerZ)
		self.updateSpinBoxes(widgets, rot)

	def	updateQuat(self, m_trans:Transform):
		qua	=	m_trans.getRotation()
		widgets = (self.quatW, self.quatX, self.quatY, self.quatZ)
		self.updateSpinBoxes(widgets, qua)

	def updateTranslation(self, m_trans:Transform):
		tra = m_trans.getTranslation()
		widgets= (self.transX,self.transY,self.transZ)
		self.updateSpinBoxes(widgets, tra)

	def updateScale(self, m_trans:Transform):
		s = m_trans.getScale()
		widgets = (self.scaleX,self.scaleY,self.scaleZ)
		self.updateSpinBoxes(widgets, s)

		lock = m_trans.m_lock_scale
		self.scaleCheck.blockSignals(True)
		self.scaleCheck.setChecked(lock) # domyślnie "lock aspect ratio"
		self.scaleCheck.blockSignals(False)
		self.scaleY.setEnabled(not lock)
		self.scaleZ.setEnabled(not lock)

	def	updateProperties(self):
		m_trans	=	self.obj_ref()
		if	m_trans	is	None:
			return
		
		self.updateMatrix(m_trans)
		self.updateEuler(m_trans)
		self.updateQuat(m_trans)
		self.updateScale(m_trans)
		self.updateTranslation(m_trans)

		self.showScrewCheckBox.blockSignals(True)
		self.showScrewCheckBox.setChecked(m_trans.m_show_screw)
		self.showScrewCheckBox.blockSignals(False)


	def changedQua(self, d):
		m_trans: Transform = self.obj_ref()
		if not isinstance(self.sender(), QDoubleSpinBox):
			return

		w = self.quatW.value()
		x = self.quatX.value()
		y = self.quatY.value()
		z = self.quatZ.value()

		m_trans.setRotation([w, x, y, z])
		self.updateMatrix(m_trans)
		self.updateEuler(m_trans)
		AP.updateAllViews()

	def changedEul(self, d):
		if not isinstance(self.sender(), QDoubleSpinBox):
			return

		m_trans = self.obj_ref()
		roll  = self.eulerX.value()
		pitch = self.eulerY.value()
		yaw   = self.eulerZ.value()

		m_trans.fromEulerAngles(roll, pitch, yaw)
		self.updateMatrix(m_trans)
		self.updateQuat(m_trans)
		AP.updateAllViews()

	
	def changedTra(self, d):
		m_trans = self.obj_ref()
		if not isinstance(self.sender(), QDoubleSpinBox):
			return

		tx = self.transX.value()
		ty = self.transY.value()
		tz = self.transZ.value()

		m_trans.setTranslation(tx, ty, tz)
		AP.updateAllViews()

	def changedSca(self, d):
		if not isinstance(self.sender(), QDoubleSpinBox):
			return

		m_trans = self.obj_ref()

		if self.scaleCheck.isChecked():
			# lock aspect ratio → wszystkie osie takie same
			s = self.scaleX.value()
			m_trans.setScale(s, s, s)
			self.scaleY.setValue(s)
			self.scaleZ.setValue(s)
		else:
			# niezależne osie → bierzemy wszystkie trzy z UI
			sx = self.scaleX.value()
			sy = self.scaleY.value()
			sz = self.scaleZ.value()
			m_trans.setScale(sx, sy, sz)

		self.updateMatrix(m_trans)
		AP.updateAllViews()

	def onScaleCheck(self, checked: bool):
		if checked:
			# tryb "lock aspect ratio" → tylko X aktywny
			self.scaleX.setEnabled(True)
			self.scaleY.setEnabled(False)
			self.scaleZ.setEnabled(False)

			# zsynchronizuj wartości Y,Z z X
			s = self.scaleX.value()
			self.scaleY.setValue(s)
			self.scaleZ.setValue(s)
		else:
			# tryb "independent axes" → wszystkie aktywne
			self.scaleX.setEnabled(True)
			self.scaleY.setEnabled(True)
			self.scaleZ.setEnabled(True)

		m_trans	=	self.obj_ref()
		m_trans.m_lock_scale = checked
		sx = self.scaleX.value()
		sy = self.scaleY.value()
		sz = self.scaleZ.value()
		m_trans.setScale(sx, sy, sz)

		self.updateMatrix()
		AP.updateAllViews()


	
	def	clearMatrix(self):
		m_trans = self.obj_ref()
		m_trans.reset()
		self.updateProperties()
		AP.updateAllViews()
	
	def	copyToClipboard(self):
		m_trans = self.obj_ref()
		m_trans.copyToClipboard()

	def	pasteFromClipboard(self):
		m_trans = self.obj_ref()
		m_trans.pasteFromClipboard()
		self.updateProperties()
		AP.updateAllViews()

	def	onRotButton(self):
		pass


	@pyqtSlot(float)
	def	onOriginPointValueChanged(self,d):
		m_trans	=	self.obj_ref()
		edit	=	self.sender()
		if	isinstance(edit,	QDoubleSpinBox)	and	(edit	==	self.originX	or	edit	==	self.originY	or	edit	==	self.originZ):
			m_trans.m_origin	=	[self.originX.value(),	self.originY.value(),	self.originZ.value()]

	@pyqtSlot(bool)
	def	onShowScrewCheckBox(self, b):
		m_trans = self.obj_ref()
		m_trans.m_show_screw = b
		AP.updateAllViews()

	@pyqtSlot(bool)
	def	onOriginRadio(self,b):
		m_trans = self.obj_ref()
		radio	=	self.sender()
		if	not	isinstance(radio,	QRadioButton):	return
		if	radio	==	self.originRadioObj:
			pass
		elif	radio	==	self.originRadioBB:
			_b,	_min,	_max	=	m_trans.getBB()
			
			pass
		elif	radio	==	self.originRadioWeight:
			pass
		elif	radio	==	self.originRadioPoint:
			self.originX.setEnabled(	b	)
			self.originY.setEnabled(	b	)
			self.originZ.setEnabled(	b	)
			m_trans.m_origin	=	[self.originX.value(),	self.originY.value(),	self.originZ.value()]	if	b	else	[0.,0.,0.]
		
		
	def	createUI(self):
		# self.setMinimumSize(200,	130)
		# self.setMaximumSize(200,	16777215)

		mainLayout	=	QHBoxLayout(self)
		mainLayout.setContentsMargins(0,	0,	0,	0)

		#	---	główny	groupbox	---
		transformGroup	=	QGroupBox("Transformation",	self)
		transformGroup.setMinimumSize(200,	0)
		transformGroup.setMaximumSize(200,	16777215)
		mainLayout.addWidget(transformGroup)

		v_layout	=	QVBoxLayout(transformGroup)
		v_layout.setContentsMargins(0,	0,	0,	0)

		#	---	checkbox	"show	screw"	---
		self.showScrewCheckBox	=	QCheckBox("show	screw",	transformGroup)
		v_layout.addWidget(self.showScrewCheckBox)

		#	---	matrix	group	---
		self.matrixLabel	=	QLabel("Transf.	matrix:")
		self.matrixTable	=	QTableWidget(4,	4)
		self.matrixTable = QTableWidget(4, 4)
		self.matrixTable.setFixedSize(182, 82)
		self.matrixTable.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		self.matrixTable.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		self.matrixTable.verticalHeader().setVisible(False)
		self.matrixTable.horizontalHeader().setVisible(False)

		# ustaw rozmiary komórek
		h = self.matrixTable.horizontalHeader()
		v = self.matrixTable.verticalHeader()
		h.setDefaultSectionSize(45)
		h.setMinimumSectionSize(45)
		v.setDefaultSectionSize(20)
		v.setMinimumSectionSize(20)

		matLayout	=	QVBoxLayout()
		matLayout.addWidget(self.matrixLabel)
		matLayout.addWidget(self.matrixTable)
		v_layout.addLayout(matLayout)

		#	---	scale	group	---
		scaleGroup	=	QGroupBox("scale")
		self.scaleX	=	QDoubleSpinBox();	self.scaleX.setPrefix("⨯	")
		self.scaleY	=	QDoubleSpinBox();	self.scaleY.setPrefix("⨯	");	self.scaleY.setEnabled(False)
		self.scaleZ	=	QDoubleSpinBox();	self.scaleZ.setPrefix("⨯	");	self.scaleZ.setEnabled(False)
		self.scaleCheck	=	QCheckBox()

		scaleLayout	=	QVBoxLayout(scaleGroup)
		scaleLayout.addWidget(self.scaleX)
		scaleLayout.addWidget(self.scaleY)
		scaleLayout.addWidget(self.scaleZ)
		scaleLayout.addWidget(self.scaleCheck)
		v_layout.addWidget(scaleGroup)

		#	---	translation	group	---
		transGroup	=	QGroupBox("translation")
		self.transX	=	QDoubleSpinBox();	self.transX.setPrefix("X:	")
		self.transY	=	QDoubleSpinBox();	self.transY.setPrefix("Y:	")
		self.transZ	=	QDoubleSpinBox();	self.transZ.setPrefix("Z:	")
		transLayout	=	QVBoxLayout(transGroup)
		transLayout.addWidget(self.transX)
		transLayout.addWidget(self.transY)
		transLayout.addWidget(self.transZ)
		v_layout.addWidget(transGroup)

		#	---	euler	group	---
		eulerGroup	=	QGroupBox("euler")
		self.eulerX	=	QDoubleSpinBox();	self.eulerX.setSuffix("°")
		self.eulerY	=	QDoubleSpinBox();	self.eulerY.setSuffix("°")
		self.eulerZ	=	QDoubleSpinBox();	self.eulerZ.setSuffix("°")
		eulerLayout	=	QVBoxLayout(eulerGroup)
		eulerLayout.addWidget(self.eulerX)
		eulerLayout.addWidget(self.eulerY)
		eulerLayout.addWidget(self.eulerZ)
		v_layout.addWidget(eulerGroup)

		#	---	quaternion	group	---
		quatGroup	=	QGroupBox("quaternion")
		self.quatW	=	QDoubleSpinBox();	self.quatW.setEnabled(False)
		self.quatX	=	QDoubleSpinBox();	self.quatX.setEnabled(False)
		self.quatY	=	QDoubleSpinBox();	self.quatY.setEnabled(False)
		self.quatZ	=	QDoubleSpinBox();	self.quatZ.setEnabled(False)
		quatLayout	=	QVBoxLayout(quatGroup)
		quatLayout.addWidget(self.quatW)
		quatLayout.addWidget(self.quatX)
		quatLayout.addWidget(self.quatY)
		quatLayout.addWidget(self.quatZ)
		v_layout.addWidget(quatGroup)

		#	---	tree	view	---
		self.treeView	=	QTreeView(transformGroup)
		v_layout.addWidget(self.treeView)
