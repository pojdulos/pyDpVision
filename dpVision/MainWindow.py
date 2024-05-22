import dpVision.ui.dpVision_rc

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QObject, QFileInfo, pyqtSlot
from PyQt5 import uic

from dpVision.Globals import AP

from dpVision.DockWidgetWorkspace import DockWidgetWorkspace
from dpVision.DockWidgetProperties import DockWidgetProperties
from dpVision.DockWidgetPluginList import DockWidgetPluginList
from dpVision.DockWidgetPluginPanel import DockWidgetPluginPanel
from dpVision.MdiChild import MdiChild
from dpVision.Workspace import Workspace
from dpVision.Parser import Parser
from dpVision.GLViewer import GLViewer
from dpVision.Transform import Transform
from dpVision.ProgressIndicator import ProgressIndicator


maxRecentFiles = 10

class MainWindow(QMainWindow):
	def __init__(self):
		super(MainWindow, self).__init__()
		uic.loadUi('dpVision/ui/UiMainWindow.ui', self)

		self.workspace = Workspace()
		
		self.dock = {}

		self.dock["workspace"] = DockWidgetWorkspace(self)
		self.addDockWidget(
			Qt.DockWidgetArea.LeftDockWidgetArea, self.dock["workspace"])

		self.dock["plugins"] = DockWidgetPluginList(self)
		self.addDockWidget(
			Qt.DockWidgetArea.LeftDockWidgetArea, self.dock["plugins"])

		self.tabifyDockWidget(self.dock["plugins"],self.dock["workspace"])

		self.dock["properties"] = DockWidgetProperties(self)
		self.addDockWidget(
			Qt.DockWidgetArea.LeftDockWidgetArea, self.dock["properties"])


		self.dock["panel"] = DockWidgetPluginPanel(self)
		self.addDockWidget(
			Qt.DockWidgetArea.RightDockWidgetArea, self.dock["panel"])

		leftDocks = [self.dock["workspace"], self.dock["properties"]]
		#rightDocks = [self.dock["plugins"], self.dock["panel"]]

		wh = self.size().height()
		hA = int(0.25 * wh)
		hB = wh - hA
		dockSizes = [hA, hB]

		self.resizeDocks(leftDocks, dockSizes, Qt.Orientation.Vertical)
		#self.resizeDocks(rightDocks, dockSizes, Qt.Orientation.Vertical)

		self.dock["workspace"].rebuildTree()

		self.progressIndicator = ProgressIndicator(self.statusBar)
		self.progressIndicator.hide()
		self.statusBar.addPermanentWidget(self.progressIndicator, 0)

		self.recentFileActionList = []
		self.createRecentActions()
		self.createRecentMenus()

		self.mdiArea.subWindowActivated.connect(self.onSubWindowActivated)
		MdiChild.create(self, self.mdiArea, MdiChild.Show.Maximized)

	def closeEvent(self, event):
		# reply = QMessageBox.question(self, 'Wiadomość',
		#							  "Czy na pewno chcesz zamknąć?",
		#							  QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

		# if reply == QMessageBox.Yes:
		#	 event.accept()  # Użytkownik potwierdza zamknięcie
		# else:
		#	 event.ignore()  # Użytkownik anuluje zamknięcie
		pass

	def buttonClicked(self):
		QMessageBox.information(self, 'Komunikat', 'Kliknięto przycisk!')

	def createRecentActions(self):
		for i in range(maxRecentFiles):
			action = QAction(self)
			action.setVisible(False)
			action.triggered.connect(self.openRecent)
			self.recentFileActionList.append( action )
	

	def createRecentMenus(self):
		for i in range(maxRecentFiles):
			self.menuRecentFiles.addAction(self.recentFileActionList[i])
		self.updateRecentActionList()


	def adjustForCurrentFile(self, filePath):
		currentFilePath = filePath
		self.setWindowFilePath(currentFilePath)

		recentFilePaths = AP.settings.value("recentFiles",[])
		recentFilePaths = [i for i in recentFilePaths if i != filePath]
		recentFilePaths.insert(0, filePath)
		while len(recentFilePaths) > maxRecentFiles:
			recentFilePaths.pop()
		AP.settings.setValue("recentFiles", recentFilePaths)

		self.updateRecentActionList()


	def	updateRecentActionList(self):
		recentFilePaths = AP.settings.value("recentFiles",[])

		itEnd = min( len(recentFilePaths), maxRecentFiles )

		for i in range(itEnd):
			strippedName = QFileInfo(recentFilePaths[i]).fileName()
			self.recentFileActionList[i].setText(strippedName)
			self.recentFileActionList[i].setData(recentFilePaths[i])
			self.recentFileActionList[i].setVisible(True)


		for i in range(itEnd, maxRecentFiles):
			self.recentFileActionList[i].setVisible(False)


	@pyqtSlot(QMdiSubWindow)
	def onSubWindowActivated(self, subWindow):
		if not subWindow is None:
			# print("subWindow activated")
			child = subWindow.widget()
			if not child is None:
				self.dock["properties"].selectionChanged(child.m_widget)
		# else:
		# 	print("last subWindow deactivated")

	@pyqtSlot()
	def createGLViewer(self):
		# MdiChild.create(MdiChild::Type::GL, ui.mdiArea, MdiChild::Show::Normal);
		MdiChild.create(self, self.mdiArea)

	def currentGLViewer(self):
		win = self.mdiArea.activeSubWindow()
		if not win is None:
			child = win.widget()
			if not child is None and type(child.m_widget) is GLViewer:
				return child.m_widget
		return None

	def allGLViewers(self):
		result = []
		for win in self.mdiArea.subWindowList():
			child = win.widget()
			if type(child.m_widget) is GLViewer:
				result.append(child.m_widget)
		return result


	@pyqtSlot(QObject)	
	def onCurrentObjectUpdated( self, obj ):
		self.dock["properties"].updateProperties()
		self.dock["workspace"].refreshAll()

	@pyqtSlot(QObject)	
	def onCurrentObjectChanged( self, obj ):
		self.workspace.m_currentObject = obj
		if obj is None:
			obj = self.currentGLViewer()
		self.dock["properties"].selectionChanged(obj)
		self.dock["workspace"].refreshAll()

	def viewerSelected(self):
		pass

	def useShaders(self):
		pass

	def modelLock(self):
		pass

	def modelInvertNormals(self):
		pass

	def modelVisibility(self):
		pass

	def meshApplyTransformations(self):
		pass

	def pickSnap(self):
		pass

	def grabPoints(self):
		pass

	def viewChildFS(self):
		pass

	@pyqtSlot()
	def fileOpen(self):
		recentFile = AP.settings.value("recentFile","")

		exts = Parser.getLoadExts()
		fileName = QFileDialog.getOpenFileName( self, "Open File", recentFile, exts )
		
		if fileName[0] != "":
			obj = Parser.load(fileName[0])
			if not obj is None:
				tra = Transform()
				if not tra is None:
					tra.addChild(obj)
					self.workspace.m_data.append(tra)
					self.dock["workspace"].addNewItem(tra)
					self.adjustForCurrentFile(fileName[0])
					AP.settings.setValue("recentFile", fileName[0])
		AP.updateAllViews()


	@pyqtSlot()
	def openRecent(self):
		action = self.sender()
		if action:
			fileName = action.data()
			obj = Parser.load(fileName)
			if not obj is None:
				tra = Transform()
				if not tra is None:
					tra.addChild(obj)
					self.workspace.m_data.append(tra)
					self.dock["workspace"].addNewItem(tra)
					self.adjustForCurrentFile(fileName)
					AP.settings.setValue("recentFile", fileName)
		AP.updateAllViews()


	def stereoscopyOff(self):
		pass

	def stereoscopyQuadbuff(self):
		pass

	def stereoscopyRedCyan(self):
		pass

	def stereoscopyBlueRed(self):
		pass

	def stereoscopyGreenRed(self):
		pass

	def stereoscopyRedBlue(self):
		pass

	def stereoscopyCyanRed(self):
		pass

	def stereoscopyRedGreen(self):
		pass

	def stereoscopyAboveBelow(self):
		pass

	def stereoscopySideBySide(self):
		pass

	def stereoscopyRowInterlaced(self):
		pass

	def stereoscopyColInterlaced(self):
		pass

	def mesh_renderAsFaces(self):
		sel = self.dock["workspace"].getSelectedObjects()
		if len(sel):
			for obj in sel:
				if obj.hasType('Mesh'):
					obj.gl_renderAs = 2
					AP.updateAllViews()

	def mesh_renderAsEdges(self):
		sel = self.dock["workspace"].getSelectedObjects()
		if len(sel):
			for obj in sel:
				if obj.hasType('Mesh'):
					obj.gl_renderAs = 1
					AP.updateAllViews()

	def mesh_renderAsVertices(self):
		sel = self.dock["workspace"].getSelectedObjects()
		if len(sel):
			for obj in sel:
				if obj.hasType('Mesh'):
					obj.gl_renderAs = 0
					AP.updateAllViews()

	@pyqtSlot(bool)
	def textureOnOff(self, b):
		sel = self.dock["workspace"].getSelectedObjects()
		if len(sel):
			for obj in sel:
				if obj.hasType('Mesh'):
					obj.b_renderTexture = b
					AP.updateAllViews()

	def mesh_renderSmooth(self, b):
		sel = self.dock["workspace"].getSelectedObjects()
		if len(sel):
			for obj in sel:
				if obj.hasType('Mesh'):
					print('Smoothing set to ', b)
					obj.b_renderSmooth = b
					AP.updateAllViews()

	def createNewCopy(self):
		pass

	def cameraResetPosition(self):
		pass

	def projectionOrthogonal(self):
		pass

	def projectionPerspective(self):
		pass

	def bbShowHide(self):
		pass

	def openWorkspace(self):
		pass

	@pyqtSlot()
	def modelClose(self):
		sel = self.dock["workspace"].getSelectedObjects()
		if len(sel):
			for obj in sel:
				if obj.getParent() is None:
					self.workspace.m_data.remove(obj)
				else:
					obj.getParent().removeChild(obj)
				self.dock["workspace"].removeItem(obj)
			# self.update()
			for v in self.allGLViewers():
				v.update()

	def removeAllModels(self):
		pass

	def removeSelectedModels(self):
		pass

	def lockAllModels(self):
		pass

	def lockSelectedModels(self):
		pass

	def unlockAllModels(self):
		pass

	def unlockSelectedModels(self):
		pass

	def selectAll(self):
		pass

	def unselectAll(self):
		pass

	def hideAllModels(self):
		pass

	def hideSelectedModels(self):
		pass

	def showAllModels(self):
		pass

	def showSelectedModels(self):
		pass

	def modelInSelection(self):
		pass

	def modelResetTransformations(self):
		pass

	def actionSelectVertex(self):
		pass

	def actionSelectFace(self):
		pass

	def saveWorkspace(self):
		pass

	def fileSave(self):
		pass

	def pmEcol(self):
		pass

	def pmVsplit(self):
		pass

	@pyqtSlot()
	def helpAbout(self):
		# dialog = QDialog(self)
		# uic.loadUi('dpVision/UiAboutDialog.ui', dialog)
		# dialog.exec() # uruchamia jako modalny
		uic.loadUi('dpVision/ui/UiAboutDialog.ui').exec()

	def resetAllTransformations(self):
		pass

	def resetSelectedTransformations(self):
		pass
