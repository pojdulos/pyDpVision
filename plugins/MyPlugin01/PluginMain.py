# -*- coding: utf-8 -*-
"""
Created on Wed Nov 22 11:08:03 2023

@author: pojdulos
"""

from PyQt5.QtWidgets import QMenu, QPushButton, QMessageBox, QMenuBar, QAction
from dpVision.Globals import Globals 
from dpVision import PluginInterface

myGlobals = Globals()

class Plugin01(PluginInterface):
    def on_load(self):
        self.mainWindow = myGlobals.mainWin
        print( "plugin "+self.plugin_name+" loaded.")
        
        # self.mainWindow.helpAbout()
        self.add_menu()
        
    def on_unload(self):
        self.remove_menu()   
        print( "Bye bye")
        
    def add_menu(self):
        nadrzedne_menu = self.add_plugins_menu()

        self.menu = QMenu("Plugin01", self.mainWindow)
        
        nadrzedne_menu.addMenu(self.menu)
        
        action = QAction("Akcja1", self.mainWindow)
        self.menu.addAction(action)
        action.triggered.connect(self.menu_action)
        
    def remove_menu(self):
        # Znajdź "NadrzędneMenu"
        nadrzedne_menu = None
        for action in self.mainWindow.menuBar.actions():
            if action.text() == "Plugins":
                nadrzedne_menu = action.menu()
                break
        
        if nadrzedne_menu:
            # Znajdź i usuń "Plugin01"
            plugin_menu_action = None
            for action in nadrzedne_menu.actions():
                if action.text() == "Plugin01" and action.menu():
                    plugin_menu_action = action
                    break
            
            if plugin_menu_action:
                nadrzedne_menu.removeAction(plugin_menu_action)
        
        self.remove_plugins_menu()
        

    def menu_action(self):
        print("Akcja1 została aktywowana")
        MainApplication.instance().unload_plugin(self)
        #self.remove_menu()
        
        
    def perform_action(self):
        print("Akcja wykonana przez "+self.plugin_name)

    def on_button1(self):
        #QMessageBox.information(self.mainWindow, 'Komunikat', 'Akcja wykonana przez '+self.plugin_name)
        pass
 