from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QObject, pyqtSlot
from PyQt5 import uic

from dpVision.Globals import Globals

from .DockWidgetWorkspace import DockWidgetWorkspace
from .DockWidgetProperties import DockWidgetProperties
from .DockWidgetPluginList import DockWidgetPluginList
from .DockWidgetPluginPanel import DockWidgetPluginPanel
from .MdiChild import MdiChild
from .Workspace import Workspace
from .ParserOBJ import ParserOBJ
from .GLViewer import GLViewer
from dpVision.Transform import Transform

class MainWindow(QMainWindow):
	def __init__(self):
		super(MainWindow, self).__init__()
		uic.loadUi('dpVision/ui/UiMainWindow.ui', self)

		self.workspace = Workspace()
		
		self.dock = {}

		self.dock["workspace"] = DockWidgetWorkspace(self)
		self.addDockWidget(
			Qt.DockWidgetArea.LeftDockWidgetArea, self.dock["workspace"])

		self.dock["properties"] = DockWidgetProperties(self)
		self.addDockWidget(
			Qt.DockWidgetArea.LeftDockWidgetArea, self.dock["properties"])

		self.dock["plugins"] = DockWidgetPluginList(self)
		self.addDockWidget(
			Qt.DockWidgetArea.RightDockWidgetArea, self.dock["plugins"])

		self.dock["panel"] = DockWidgetPluginPanel(self)
		self.addDockWidget(
			Qt.DockWidgetArea.RightDockWidgetArea, self.dock["panel"])

		leftDocks = [self.dock["workspace"], self.dock["properties"]]
		rightDocks = [self.dock["plugins"], self.dock["panel"]]

		wh = self.size().height()
		hA = int(0.25 * wh)
		hB = wh - hA
		dockSizes = [hA, hB]

		self.resizeDocks(leftDocks, dockSizes, Qt.Orientation.Vertical)
		self.resizeDocks(rightDocks, dockSizes, Qt.Orientation.Vertical)

		self.dock["workspace"].rebuildTree()

		self.mdiArea.subWindowActivated.connect(self.onSubWindowActivated)
		# self.mdiArea = self.findChild(QMdiArea, 'mdiArea')

		# MdiChild::create(MdiChild::Type::GL, ui.mdiArea, MdiChild::Show::Maximized);
		child = MdiChild.create(self, self.mdiArea, MdiChild.Show.Maximized)


		self.dock["properties"].selectionChanged(child.widget().m_widget )

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

		myGlobals = Globals()
		print(myGlobals.mainApp)
		print(myGlobals.mainWin)


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

	@pyqtSlot(QObject)	
	def onCurrentObjectChanged( self, obj ):
		self.workspace.m_currentObject = obj
		if obj is None:
			obj = self.currentGLViewer()
		self.dock["properties"].selectionChanged(obj)

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
		#fileName = QFileDialog.getOpenFileName( this, tr("Open File"), AP::mainApp().settings->value("recentFile").toString(), CFileConnector::getLoadExts() );
		fileName = QFileDialog.getOpenFileName( self, "Open File", "", "*.obj" )
		
		if fileName[0] != "":
			obj = ParserOBJ.load(fileName[0])
			if not obj is None:
				tra = Transform()
				if not tra is None:
					tra.addChild(obj)
					self.workspace.m_data.append(tra)
					self.dock["workspace"].addNewItem(tra)

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

	def renderAsFaces(self):
		pass

	def renderAsEdges(self):
		pass

	def renderAsVertices(self):
		pass

	def textureOnOff(self):
		pass

	def smoothingOnOff(self):
		pass

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
