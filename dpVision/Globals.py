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

	def removeObject(self, child, parent=None):
		if child is None:
			return
		if parent:
			parent.removeChild(child)
		else:
			self.mainWin.workspace.m_data.remove(child)
		self.mainWin.dock["workspace"].removeItem(child)

	def updateAllViews(self):
		for v in self.mainWin.allGLViewers():
			v.update()


AP = Globals()

