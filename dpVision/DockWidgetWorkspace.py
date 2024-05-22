# -*- coding: utf-8 -*-

from dpVision.ContextMenu import ContextMenu
import dpVision.ui.dpVision_rc

from PyQt5 import uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class DeselectableTreeView(QTreeView):
	clickedSomewhere = pyqtSignal(QModelIndex)
	
	def __init__(self, parent):
		super().__init__(parent)
		
	def mousePressEvent(self, event):
		index = self.indexAt(event.pos())

		if (not index.isValid()):
			self.selectionModel().clear()

		self.clickedSomewhere.emit(index)
		QTreeView.mousePressEvent(self, event)



class DockWidgetWorkspace(QDockWidget):
	def __init__(self, parent):
		super().__init__(parent)
		self.setupUi()
		self.mainWindow = parent

		
	def setupUi(self):
		if (self.objectName()==""):
			self.setObjectName("DockWidgetWorkspace")
		self.resize(885, 177)
		self.setMinimumSize(QSize(200, 168))
		self.setMaximumSize(QSize(524287, 524287))
		self.setFloating(False)
		self.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
		
		self.dockWidgetContents = QWidget()
		self.dockWidgetContents.setObjectName("dockWidgetContents")
		
		self.gridLayout = QGridLayout(self.dockWidgetContents)
		self.gridLayout.setObjectName("gridLayout")
		self.gridLayout.setContentsMargins(0, 0, 0, 0)
		
		self.treeView = DeselectableTreeView(self.dockWidgetContents)
		self.treeView.setObjectName("treeView")
		self.treeView.setMouseTracking(False)
		self.treeView.setEditTriggers(QAbstractItemView.AllEditTriggers)
		
		self.treeView.clickedSomewhere.connect(self.onTreeViewItemClicked)

		model = QStandardItemModel(self.treeView)
		model.setHorizontalHeaderLabels(['name', '', '', '' ]);
		self.treeView.setModel(model)
	
		#//connect(model, SIGNAL(itemChanged(QStandardItem*)), SLOT(onItemChanged(QStandardItem*)));
		#//ui.treeView->setSelectionMode(QAbstractItemView::ExtendedSelection);
	
		self.treeView.setSelectionBehavior( QAbstractItemView.SelectionBehavior.SelectRows )
	
		self.treeView.setContextMenuPolicy( Qt.ContextMenuPolicy.CustomContextMenu )
		self.treeView.customContextMenuRequested.connect(self.onCustomContextMenu)
		
		self.treeView.header().resizeSection(1, 16)
		self.treeView.header().resizeSection(2, 16)
		self.treeView.header().resizeSection(3, 24)
		
		self.treeView.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch )
		self.treeView.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents )
		self.treeView.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents )
		self.treeView.header().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents )
		
		self.treeView.header().setStretchLastSection(False)
		
		self.treeView.setHeaderHidden(True)


		self.gridLayout.addWidget(self.treeView, 0, 0, 1, 1)
	
		self.setWidget(self.dockWidgetContents)
	
		self.setWindowTitle("Workspace")
	
		QMetaObject.connectSlotsByName(self)

	@pyqtSlot(QModelIndex)
	def onTreeViewItemClicked(self, current):
		# print("clicked on the tree")
		if current.isValid():
			model = self.treeView.model()
			clickedItem = model.itemFromIndex(current)

			clickedObject = self.getItemObject(clickedItem)

			if clickedObject is None:
				return

			col = current.column()
			if col == 0:
				# colNameClicked(clickedObject, clickedItem)
				pass
			elif col == 1:
				clickedObject.setSelfVisibility(not clickedObject.getSelfVisibility())
			elif col == 2:
				clickedObject.setKidsVisibility(not clickedObject.getKidsVisibility())
			elif col == 3:
				# colLockClicked((CModel3D*)clickedObject, clickedItem)
				pass
			else:
				pass
			
			self.mainWindow.onCurrentObjectChanged(clickedObject)
			#emit(currentObjectChanged(clickedObject->id()));
		else:
			self.mainWindow.onCurrentObjectChanged(None)
			#emit(currentObjectChanged(NO_CURRENT_MODEL));
			pass

	#const QPoint &
	def onCustomContextMenu(self, point):
		index = self.treeView.indexAt(point)
		
		if index.isValid():
			model = self.treeView.model()
			clickedObject = self.getItemObject( model.itemFromIndex(index) )
			if clickedObject is None:
				return

			ContextMenu(clickedObject, self.treeView).exec(self.treeView.mapToGlobal(point))
		else:
			self.treeView.clearSelection()
			self.mainWindow.onCurrentObjectChanged(None)
			ContextMenu(None, self.treeView).exec(self.treeView.mapToGlobal(point))

	def setItemObject(self, item, obj):
		#item.setData(QVariant.fromValue(obj.id()), Qt.UserRole + 1)
		item.setData(obj, Qt.UserRole)
		pass

	def getItemObject(self, item):
		return item.data(Qt.UserRole)

	@staticmethod
	def getNewIcon(obj, col):
		if col == 1:
			if obj.typeStr() == "Transform":
				return QIcon(":/icons/VisibleMatrix.ico") if obj.getSelfVisibility() else QIcon(":/icons/HiddenMatrix.ico")
			else:
				return QIcon(":/icons/Visible.ico") if obj.getSelfVisibility() else QIcon(":/icons/Hidden.ico")
		elif col == 2:
			return QIcon(":/icons/VisibleKids.ico") if obj.getKidsVisibility() else QIcon(":/icons/HiddenKids.ico")
		elif col == 3:
			return QIcon(":/icons/Unlock.ico")
			#return QIcon(":/icons/Lock.ico") if obj.isLocked() else QIcon(":/icons/Unlock.ico")
		return QIcon()


	def addTreeItem(self,root,obj):
		item = QStandardItem(obj.getLabel())
		item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
		item.setCheckable(True)
		item.setCheckState(Qt.Unchecked)
		self.setItemObject(item, obj)

		sV = QStandardItem()
		sV.setIcon(DockWidgetWorkspace.getNewIcon(obj, 1))
		sV.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
		sV.setToolTip("change own visibility")
		self.setItemObject(sV, obj)

		kV = QStandardItem()
		kV.setIcon(DockWidgetWorkspace.getNewIcon(obj, 2))
		kV.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
		kV.setToolTip("change kids visibility")
		self.setItemObject(kV, obj)

		lK = QStandardItem()
		lK.setIcon(DockWidgetWorkspace.getNewIcon(obj, 3))
		lK.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
		lK.setToolTip("Lock / Unlock")
		self.setItemObject(lK, obj)
		
		items = [item, sV, kV, lK] # all are QStandardItem type
		root.appendRow(items)	# root is QStandardItem type
		for child in obj.children():
			self.addTreeItem(item, child)
		
		return item
		
	def refreshAll(self, rootItem=None):
		model = self.treeView.model()
		if (rootItem is None):
			rootItem = model.invisibleRootItem()

		for row in range(rootItem.rowCount()):
			for col in range(4):
				childItem = rootItem.child(row,col)
				obj = self.getItemObject(childItem)

				if col == 0:
					childItem.setText(obj.getLabel())
					# Rekurencyjne wywołanie dla dzieci, jeśli istnieją
					if childItem.hasChildren():
						self.refreshAll(childItem)
				elif col == 1:
					childItem.setIcon(DockWidgetWorkspace.getNewIcon(obj, 1))
				elif col == 2:
					childItem.setIcon(DockWidgetWorkspace.getNewIcon(obj, 2))

	def rebuildTree(self):
		self.treeView.blockSignals(True)
		self.treeView.reset()

		model = self.treeView.model()

		if model.hasChildren():
			model.removeRows(0, model.rowCount())
	
		for obj in self.mainWindow.workspace.m_data:
			self.addTreeItem(model.invisibleRootItem(), obj)
	
		self.treeView.blockSignals(False)

	def addNewItem(self, obj, parent=None):
		self.treeView.blockSignals(True)
		model = self.treeView.model()

		root = model.invisibleRootItem()
		
		if parent:
			index = self.findWorkspaceTreeModelIndex(parent)
			if index and index.isValid():
				root = model.itemFromIndex(index)

		self.addTreeItem(root, obj)

		self.treeView.blockSignals(False)
		self.mainWindow.update()


	def findWorkspaceTreeModelIndex(self, obj):
		model = self.treeView.model()
		items = model.match(
			model.index(0, 0),
			Qt.UserRole,
			obj,
			1, # look *
			Qt.MatchRecursive)

		if len(items):
			return items[0]

		return None

	def removeItem(self, obj):
		self.treeView.blockSignals(True)

		index = self.findWorkspaceTreeModelIndex(obj)

		if not index is None and index.isValid():
			model = self.treeView.model()
			model.removeRow(index.row(), index.parent())

		self.treeView.blockSignals(False)

	def getSelectedObjects(self):
		result = []

		indexes = self.treeView.selectionModel().selectedIndexes()
		
		for idx in indexes:
			if not idx.column(): #tylko zerowa kolumna
				model = self.treeView.model()
				item = model.itemFromIndex(idx)
				obj = self.getItemObject(item)
				parent = obj.getParent()

				if parent is None:
					result.append(obj)
				else:
					while not parent is None:
						if parent in result:
							break

						parent = parent.getParent()

						if parent is None:
							result.append(obj)
							break

		return result



