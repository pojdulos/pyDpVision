# -*- coding: utf-8 -*-
"""
Created on Thu Nov 23 09:13:35 2023

@author: pojdulos
"""

from PyQt5.QtWidgets import QApplication
import os
import sys
import importlib.util

from .globals import AP
from .pluginInterface import PluginInterface
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject
from PyQt5.QtGui import QMouseEvent

class MainApplication(QApplication):
    mouseMovedSignal = pyqtSignal(tuple)
    mousePressedSignal = pyqtSignal(tuple)

    def __init__(self, *args, **kwargs):
        super(MainApplication, self).__init__(*args, **kwargs)
        self.m_lastObjectId = 1000000
        self.plugins = set()
        self.activePlugin = None

    def event(self, event):
        return super(MainApplication, self).event(event)

    def run_plugins(self):
        for plugin in self.plugins:
            plugin.perform_action()

    def load_plugins(self, directory):
        sys.path.append(os.path.abspath(directory))
        for folder_name in os.listdir(directory):
            folder_path = os.path.join(directory, folder_name)
            if os.path.isdir(folder_path):
                main_file = os.path.join(folder_path, "pluginMain.py")
                if os.path.isfile(main_file):
                    self.load_plugin(folder_name, main_file)



    def load_plugin(self, package_name, path):
        module_name = f'{package_name}.{os.path.basename(path)[:-3]}'
        print(module_name)
        module = importlib.import_module(module_name)

        for attribute_name in dir(module):
            attribute = getattr(module, attribute_name)
            if isinstance(attribute, type) and issubclass(attribute, PluginInterface) and attribute is not PluginInterface:
                plugin_instance = attribute()
                plugin_instance.on_load()
                self.plugins.add(plugin_instance)
                AP.mainWin.dock['plugins'].addPluginToList(plugin_instance, plugin_instance.name())
 
    def unload_plugin(self, plugin_instance):
        print("UnLoading plugin "+plugin_instance.plugin_name)
        plugin_instance.on_unload()
        self.plugins.discard(plugin_instance)
    
    def getUniqueId(self):
        self.m_lastObjectId = self.m_lastObjectId + 1
        return self.m_lastObjectId

    @pyqtSlot(tuple)
    def onMouseMoveSlot(self, event):
        self.mouseMovedSignal.emit(event)

    @pyqtSlot(tuple)
    def onMousePressSlot(self, event):
        self.mousePressedSignal.emit(event)
