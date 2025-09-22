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

		self.treeView.setVisible(False)
		self.resize(self.layout().sizeHint())

		self.originGroup.setVisible(False)

		self.quatW.setEnabled(True)
		self.quatX.setEnabled(True)
		self.quatY.setEnabled(True)
		self.quatZ.setEnabled(True)

		self.scaleCheck.setChecked(_obj.m_lock_scale) # domyślnie "lock aspect ratio"
		self.scaleY.setEnabled(not _obj.m_lock_scale)
		self.scaleZ.setEnabled(not _obj.m_lock_scale)

		self.quatW.valueChanged.connect(self.changedQua)
		self.quatX.valueChanged.connect(self.changedQua)
		self.quatY.valueChanged.connect(self.changedQua)
		self.quatZ.valueChanged.connect(self.changedQua)

		self.obj_ref = weakref.ref(_obj)

	@staticmethod
	def	create(m, parent=0):
		return	PropWidget.build([PropTransform(m), PropBaseObject(m)], parent)

	def	updateMatrix(self):
		m_trans:	Transform	=	self.obj_ref()
		mat	=	m_trans.toNumPy()		#	zawsze	numpy	4x4
		self.matrixTable.blockSignals(True)
		for	row	in	range(4):
			for	col	in	range(4):
				value	=	mat[row,	col]
				item	=	self.matrixTable.item(row,	col)
				if	item	is	None:
					item	=	QTableWidgetItem()
					self.matrixTable.setItem(row,	col,	item)
				item.setText(f"{value:.6f}")		#	format	ładniej
		self.matrixTable.blockSignals(False)



	def	updateEuler(self):
		m_trans	=	self.obj_ref()
		rot	=	m_trans.getEulerAnglesDeg()
		self.eulerX.blockSignals(True)
		self.eulerY.blockSignals(True)
		self.eulerZ.blockSignals(True)
		self.eulerX.setValue(rot[0])
		self.eulerY.setValue(rot[1])
		self.eulerZ.setValue(rot[2])
		self.eulerX.blockSignals(False)
		self.eulerY.blockSignals(False)
		self.eulerZ.blockSignals(False)

	def	updateQuat(self):
		m_trans	=	self.obj_ref()
		qua	=	m_trans.getRotation()
		self.quatW.blockSignals(True)
		self.quatX.blockSignals(True)
		self.quatY.blockSignals(True)
		self.quatZ.blockSignals(True)
		self.quatW.setValue(qua[0])
		self.quatX.setValue(qua[1])
		self.quatY.setValue(qua[2])
		self.quatZ.setValue(qua[3])
		self.quatW.blockSignals(False)
		self.quatX.blockSignals(False)
		self.quatY.blockSignals(False)
		self.quatZ.blockSignals(False)

	def	updateProperties(self):
		m_trans	=	self.obj_ref()
		if	m_trans	is	None:
			return
		
		#	w	=	{	self.showScrewCheckBox,	\
					#			self.transX,	self.transY,	self.transZ	}
		w	=	self.get_subwidgets()

		for	i	in	w:	i.blockSignals(True)
		self.updateMatrix()
		self.updateEuler()
		self.updateQuat()

		s	=	m_trans.getScale()
		self.scaleX.setValue(s[0])
		self.scaleY.setValue(s[1])
		self.scaleZ.setValue(s[2])
		#	self.scaleCheck.setChecked(True)

		self.showScrewCheckBox.setChecked(m_trans.m_show_screw)

		tra	=	m_trans.getTranslation()
		print(f"translation:	{tra}")
		self.transX.setValue(tra[0])
		self.transY.setValue(tra[1])
		self.transZ.setValue(tra[2])
		for	i	in	w:	i.blockSignals(False)


	def changedEul(self, d):
		if not isinstance(self.sender(), QDoubleSpinBox):
			return

		m_trans = self.obj_ref()
		roll  = self.eulerX.value()
		pitch = self.eulerY.value()
		yaw   = self.eulerZ.value()

		m_trans.fromEulerAngles(roll, pitch, yaw)
		self.updateMatrix()
		self.updateQuat()
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


	# def	changedSca(self,d):
	# 	m_trans	=	self.obj_ref()
	# 	s	=	m_trans.getScale()
	# 	print(f"scale:	{d}")
	# 	m_trans.scale(d/s[0],d/s[1],d/s[2])
	# 	AP.updateAllViews()

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

		self.updateMatrix()
		AP.updateAllViews()

	def changedQua(self, d):
		m_trans: Transform = self.obj_ref()
		if not isinstance(self.sender(), QDoubleSpinBox):
			return

		w = self.quatW.value()
		x = self.quatX.value()
		y = self.quatY.value()
		z = self.quatZ.value()

		m_trans.setRotation([w, x, y, z])
		self.updateMatrix()
		self.updateEuler()
		AP.updateAllViews()

	
	def	clearMatrix(self):
		m_trans	=	self.obj_ref()
		m_trans.reset()
		AP.mainWin.dock['properties'].updateProperties()
		AP.updateAllViews()
	
	def	copyToClipboard(self):
		m_trans	=	self.obj_ref()
		m_trans.copyToClipboard()

	def	pasteFromClipboard(self):
		m_trans	=	self.obj_ref()
		m_trans.pasteFromClipboard()
		AP.mainWin.dock['properties'].updateProperties()
		AP.updateAllViews()

	def	onRotButton(self):
		pass

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

	@pyqtSlot(float)
	def	onOriginPointValueChanged(self,d):
		m_trans	=	self.obj_ref()
		edit	=	self.sender()
		if	isinstance(edit,	QDoubleSpinBox)	and	(edit	==	self.originX	or	edit	==	self.originY	or	edit	==	self.originZ):
			m_trans.m_origin	=	[self.originX.value(),	self.originY.value(),	self.originZ.value()]

	@pyqtSlot(bool)
	def	onShowScrewCheckBox(self,	b):
		m_trans	=	self.obj_ref()
		m_trans.m_show_screw	=	b
		AP.updateAllViews()

	@pyqtSlot(bool)
	def	onOriginRadio(self,b):
		m_trans	=	self.obj_ref()
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
