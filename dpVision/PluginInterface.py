from abc import ABC, abstractmethod
from .globals import AP

class PluginInterface(ABC):
	def __init__(self):
		self.plugin_name = self.__class__.__name__
    
	def name(self):
		return self.plugin_name
	
	@abstractmethod
	def on_load(self):
		pass

	@abstractmethod
	def on_unload(self):
		pass

	#@abstractmethod
	def on_activate(self):
		pass

	#@abstractmethod
	def on_deactivate(self):
		pass

	@abstractmethod
	def perform_action(self):
		pass

	def add_plugins_menu(self):
		# Załóżmy, że nazwa istniejącego menu to "NadrzędneMenu"
		nadrzedne_menu = None
		for action in AP.mainWin.menuBar.actions():
			if action.text() == "Plugins":
				nadrzedne_menu = action.menu()
				break
        
		if not nadrzedne_menu:
			# Jeśli nie znaleziono, możesz utworzyć nowe menu nadrzędne
			nadrzedne_menu = AP.mainWin.menuBar.addMenu("Plugins")

		return nadrzedne_menu

	def remove_plugins_menu(self):
        # Znajdź "NadrzędneMenu"
		nadrzedne_menu = None
		for action in AP.mainWin.menuBar.actions():
			if action.text() == "Plugins":
				nadrzedne_menu = action.menu()
				break
        
		if nadrzedne_menu and not nadrzedne_menu.actions():
            # Jeśli "NadrzędneMenu" jest puste, usuń je z paska menu
			AP.mainWin.menuBar.removeAction(nadrzedne_menu.menuAction())
    