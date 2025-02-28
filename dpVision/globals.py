import sys, os

class Globals:
	_instance = None

	def __new__(cls, *args, **kwargs):
		if not cls._instance:
			cls._instance = super(Globals, cls).__new__(cls, *args, **kwargs)
			cls._instance.mainApp = None
			cls._instance.mainWin = None
			cls._instance.settings = None
			#cls._instance.docksettings = None
			cls._instance.mouse_key_pressed = False
		return cls._instance

	# def updateGlobals(self):
	# 	self.mainWin = MainWindow()

	def addObject(self, child, parent=None):
		if child is None:
			return
		if parent:
			parent.addChild(child)
		else:
			self.mainWin.workspace.m_data.append(child)
		self.mainWin.dock["workspace"].addNewItem(child, parent)
		self.updateAllViews()

	def removeObject(self, child, parent=None):
		if child is None:
			return
		if parent:
			parent.removeChild(child)
		elif child.parent is not None:
			child.parent.removeChild(child)
		else:
			self.mainWin.workspace.m_data.remove(child)
		self.mainWin.dock["workspace"].removeItem(child)

	def updateProperties(self):
		self.mainWin.dock["properties"].updateProperties()

	def updateAllViews(self):
		for v in self.mainWin.allGLViewers():
			v.update()

	def not_implemented(self):
		from PyQt5.QtWidgets import QMessageBox
		msg = QMessageBox() 
		msg.setIcon(QMessageBox.Information) 
		msg.setText("Function not implemented yet") 
		msg.setWindowTitle("Information") 
		msg.setStandardButtons(QMessageBox.Ok) 
		retval = msg.exec_()

	def loadUi(self, fname, win):
		from PyQt5 import uic
		if hasattr(sys, '_MEIPASS'):
			# PyInstaller uruchamia się z pliku spakowanego
			ui_path = os.path.join(sys._MEIPASS, f"dpVision/gui/forms/{fname}")
		else:
			# Tryb developerski
			ui_path = os.path.join(os.path.dirname(__file__), f"gui/forms/{fname}")
		uic.loadUi(ui_path, win)

AP = Globals()

