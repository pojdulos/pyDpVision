import dpVision.gui.dpVision_rc

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QObject, QFileInfo, pyqtSlot
from PyQt5 import uic

from .. import AP, Workspace, Parser, Transform

from .dockWidgetWorkspace import DockWidgetWorkspace
from .dockWidgetProperties import DockWidgetProperties
from .dockWidgetPluginList import DockWidgetPluginList
from .dockWidgetPluginPanel import DockWidgetPluginPanel
from .mdiChild import MdiChild
from .gLViewer import GLViewer
from .taskManager import TaskManager, ParserLoadTaskRunner, ParserSaveTaskRunner
import os
import re


MAX_NUMBER_OF_RECENT_FILES = 10

class MainWindow(QMainWindow):
	def __init__(self):
		super(MainWindow, self).__init__()
		#uic.loadUi('dpVision/gui/forms/mainWindow.ui', self)
		AP.loadUi('mainWindow.ui', self)
		self.action_File_SaveAs.triggered.connect(self.fileSave)

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
		 	Qt.DockWidgetArea.LeftDockWidgetArea, self.dock["panel"])

		self.tabifyDockWidget(self.dock["panel"],self.dock["properties"])

		leftDocks = [self.dock["workspace"], self.dock["properties"]]
		#rightDocks = [self.dock["plugins"], self.dock["panel"]]

		wh = self.size().height()
		hA = int(0.25 * wh)
		hB = wh - hA
		dockSizes = [hA, hB]

		self.resizeDocks(leftDocks, dockSizes, Qt.Orientation.Vertical)
		#self.resizeDocks(rightDocks, dockSizes, Qt.Orientation.Vertical)

		self.dock["workspace"].rebuildTree()

		self.taskManager = TaskManager(self)
		self.loadTaskManager = self.taskManager

		self.create_recent_files_menu()

		self.dock["workspace"].object_updated.connect(self.onCurrentObjectUpdated)
		self.dock["workspace"].object_changed.connect(self.onCurrentObjectChanged)
		self.dock["properties"].object_updated.connect(self.onCurrentObjectUpdated)

		self.mdiArea.subWindowActivated.connect(self.onSubWindowActivated)
		MdiChild.create(self, self.mdiArea, MdiChild.Show.Maximized)

	# def load_ui(self):
	# 	if hasattr(sys, '_MEIPASS'):
	# 		# PyInstaller uruchamia się z pliku spakowanego
	# 		ui_path = os.path.join(sys._MEIPASS, 'dpVision/gui/forms/mainWindow.ui')
	# 	else:
	# 		# Tryb developerski
	# 		ui_path = os.path.join(os.path.dirname(__file__), 'forms/mainWindow.ui')
	# 	uic.loadUi(ui_path, self)

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

	def create_recent_files_menu(self):
		# create empty recent menu (all actions are invisible)
		for _ in range(MAX_NUMBER_OF_RECENT_FILES):
			action = QAction(self)
			action.setVisible(False)
			action.triggered.connect(self.openRecent)
			self.menuRecentFiles.addAction(action)
		
		self.menuRecentFiles.setToolTipsVisible(True)
		# and fill it with recentFiles from registry
		self.update_recent_files_menu()

	
	def	update_recent_files_menu(self, paths=None):
		def shorten_path(my_path, max_length=60):
			if len(my_path) <= max_length:
				return my_path
			else:
				part_length = (max_length - 3) // 2
				return my_path[:part_length] + '...' + my_path[-part_length:]

		if not paths or not isinstance(paths, list):
			paths = AP.settings.value("recentFiles",[])

		actions_list = self.menuRecentFiles.actions()
		paths_count = min(len(paths), MAX_NUMBER_OF_RECENT_FILES)

		# Aktualizacja widoczności i danych akcji
		for i in range(MAX_NUMBER_OF_RECENT_FILES):
			if i < paths_count:
				actions_list[i].setText(QFileInfo(paths[i]).fileName())
				# actions_list[i].setToolTip(shorten_path(paths[i]))
				actions_list[i].setToolTip(paths[i])
				actions_list[i].setData(paths[i])
				actions_list[i].setVisible(True)
			else:
				actions_list[i].setVisible(False)


	def update_recent_files(self, file_path):
		self.setWindowFilePath(file_path)

		recent_paths = AP.settings.value("recentFiles",[])
		
		recent_paths = [i for i in recent_paths if i != file_path]
		recent_paths.insert(0, file_path)

		recent_paths = recent_paths[:MAX_NUMBER_OF_RECENT_FILES]
		# while len(recent_paths) > MAX_NUMBER_OF_RECENT_FILES:
		# 	recent_paths.pop()
		
		AP.settings.setValue("recentFiles", recent_paths)
		AP.settings.setValue("recentFile", file_path)
		self.update_recent_files_menu(paths=recent_paths)

	def remove_from_recent_files(self, file_path):
		recent_paths = AP.settings.value("recentFiles",[])
		if file_path in recent_paths:
			recent_paths.remove(file_path)
			AP.settings.setValue("recentFiles", recent_paths)
			self.update_recent_files_menu(paths=recent_paths)


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
		sender = self.sender()
		#print('MainWindow.onCurrentObjectUpdated(obj)', sender)

		# if type(sender) is not DockWidgetWorkspace:
		if not sender == self.dock["workspace"]:
			self.dock["workspace"].refreshAll()

		if type(sender) is not DockWidgetProperties:
			# self.dock["properties"].updateProperties()
			self.dock["properties"].selectionChanged(obj)

		AP.updateAllViews()

	@pyqtSlot(QObject)	
	def onCurrentObjectChanged( self, obj ):
		self.workspace.m_currentObject = obj
		if obj is None:
			obj = self.currentGLViewer()
		
		sender = self.sender()
		if type(sender) is not DockWidgetWorkspace:
			self.dock["workspace"].refreshAll()

		if type(sender) is not DockWidgetProperties:
			self.dock["properties"].selectionChanged(obj)
		AP.updateAllViews()


	@pyqtSlot()
	def on_model_showbb(self):
		sel = self.dock["workspace"].getSelectedObjects()
		if len(sel):
			for obj in sel:
				obj.m_showBB = not obj.m_showBB
			AP.updateAllViews()

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


	def load_file(self, fileName, on_success=None, on_error=None):
		if not os.path.exists(fileName):
			print(f"File not exists: {fileName}")
			return False
		runner = ParserLoadTaskRunner(fileName, parent=self.taskManager)
		if runner.parser is None:
			return False

		def handle_success(obj):
			if obj:
				if isinstance(obj, list) and len(obj) > 0:
					tra = Transform()
					for kid in obj:
						tra.addChild(kid)
				elif hasattr(obj, 'hasType'):
					if obj.hasType('Transform'):
						tra = obj
					else:
						tra = Transform()
						tra.addChild(obj)
				else:
					if on_error:
						on_error(None)
					return

				tra.label = os.path.basename(fileName)
				print(f"Loaded: {fileName} as {obj.__class__.__name__}, label: {tra.label}")
				print(f"{obj.info()}")

				self.workspace.m_data.append(tra)
				self.dock["workspace"].addNewItem(tra)
				self.update_recent_files(fileName)
				from ..globals import AP
				AP.updateAllViews()

				if on_success:
					on_success(obj)
			elif on_error:
				try:
					on_error(None)
				except TypeError:
					on_error()

		def handle_error(error):
			if on_error:
				try:
					on_error(error)
				except TypeError:
					on_error()

		task = self.taskManager.start_runner(
			runner,
			on_success=handle_success,
			on_error=handle_error,
			kind="load",
			label=os.path.basename(fileName),
		)
		return task is not None

	@pyqtSlot()
	def fileOpen(self):
		recentFile = AP.settings.value("recentFile","")

		exts = Parser.getLoadExts()
		fileName = QFileDialog.getOpenFileName( self, "Open File", recentFile, exts )
		
		if fileName[0] != '':
			self.load_file(fileName[0])

	@pyqtSlot()
	def openRecent(self):
		action = self.sender()
		if action:
			fileName = action.data()
			if not self.load_file(fileName):
				self.remove_from_recent_files(fileName)

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
					obj.gl_renderAs = 4
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

	@pyqtSlot()
	def projectionOrthogonal(self):
		self.currentGLViewer().applyProjection(GLViewer.Projection.ORTHOGONAL)
		self.currentGLViewer().recalcView()
		self.currentGLViewer().update()

	@pyqtSlot()
	def projectionPerspective(self):
		self.currentGLViewer().applyProjection(GLViewer.Projection.PERSPECTIVE)
		self.currentGLViewer().recalcView()
		self.currentGLViewer().update()

	@pyqtSlot()
	def bbShowHide(self):
		self.currentGLViewer().switchBB()
		self.currentGLViewer().update()

	def openWorkspace(self):
		pass

	@pyqtSlot()
	def modelClose(self):
		sel = self.dock["workspace"].getSelectedObjects()
		if len(sel):
			for obj in sel:
				if obj.parent is None:
					self.workspace.m_data.remove(obj)
				else:
					obj.parent.removeChild(obj)
				self.dock["workspace"].removeItem(obj)
			# self.update()

			for v in self.allGLViewers():
				v.update()
		self.workspace.m_currentObject = None



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

	@pyqtSlot()
	def actionSelectVertex(self):
		"""Obsługa Select->Area (Shift+V) - włącza tryb zaznaczania obszaru"""
		viewer = self.currentGLViewer()
		if viewer:
			viewer.enableSelectionMode()
			# Upewnij się, że akcja jest zaznaczona
			self.action_select_Vertex.setChecked(True)
			self.action_select_None.setChecked(False)

	@pyqtSlot()
	def actionSelectFace(self):
		pass
	
	@pyqtSlot()
	def actionSelectNone(self):
		"""Obsługa Select->None - wyłącza tryb zaznaczania i czyści zaznaczenie"""
		viewer = self.currentGLViewer()
		if viewer:
			viewer.disableSelectionMode()
			# Upewnij się, że akcja jest zaznaczona
			self.action_select_None.setChecked(True)
			self.action_select_Vertex.setChecked(False)

	def saveWorkspace(self):
		pass

	def fileSave(self):
		selected = self.dock["workspace"].getSelectedObjects()
		obj = selected[0] if len(selected) == 1 else self.workspace.m_currentObject

		if obj is None:
			QMessageBox.warning(self, "Save as...", "Nie wybrano obiektu do zapisania.")
			return

		save_parsers = Parser.getSaveParsers(obj)
		if not len(save_parsers):
			QMessageBox.warning(
				self,
				"Save as...",
				f"Brak dostępnych formatów zapisu dla obiektu typu {obj.__class__.__name__}."
			)
			return

		save_filters = Parser.getSaveExts(obj)
		default_ext = save_parsers[0].save_exts[0]
		default_name = getattr(obj, "label", "export")
		if os.path.splitext(default_name)[1] == '':
			default_name = default_name + default_ext

		file_name, selected_filter = QFileDialog.getSaveFileName(
			self,
			"Save File",
			default_name,
			save_filters
		)
		if file_name == '':
			return

		file_root, file_ext = os.path.splitext(file_name)
		if file_ext == '':
			filter_text = selected_filter if selected_filter else save_filters.split(';;')[0]
			filter_match = re.search(r'\*(\.[A-Za-z0-9]+)', filter_text)
			file_ext = filter_match.group(1) if filter_match else default_ext
			file_name = file_root + file_ext

		runner = ParserSaveTaskRunner(obj, file_name, parent=self.taskManager)
		if runner.parser_cls is None:
			QMessageBox.warning(self, "Save as...", "Nie udało się dobrać parsera zapisu dla wybranego formatu.")
			return

		def handle_success(saved_path):
			self.statusBar.showMessage(f"Saved: {saved_path}", 5000)

		def handle_error(_error):
			QMessageBox.warning(self, "Save as...", "Nie udało się zapisać obiektu w wybranym formacie.")

		self.taskManager.start_runner(
			runner,
			on_success=handle_success,
			on_error=handle_error,
			kind="save",
			label=os.path.basename(file_name),
		)

	def pmEcol(self):
		pass

	def pmVsplit(self):
		pass

	@pyqtSlot()
	def helpAbout(self):
		uic.loadUi('dpVision/gui/forms/aboutDialog.ui').exec()

	def resetAllTransformations(self):
		pass

	def resetSelectedTransformations(self):
		pass
