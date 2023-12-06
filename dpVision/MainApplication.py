# -*- coding: utf-8 -*-
"""
Created on Thu Nov 23 09:13:35 2023

@author: pojdulos
"""

from PyQt5.QtWidgets import QApplication
import os
import importlib.util

from .PluginInterface import PluginInterface

class MainApplication(QApplication):
    def __init__(self, *args, **kwargs):
        super(MainApplication, self).__init__(*args, **kwargs)
        self.m_lastObjectId = 1000000
        self.plugins = []

    def event(self, event):
        return super(MainApplication, self).event(event)

    def run_plugins(self):
        for plugin in self.plugins:
            plugin.perform_action()

    def load_plugins(self, directory):
        for folder_name in os.listdir(directory):
            folder_path = os.path.join(directory, folder_name)
            if os.path.isdir(folder_path):
                main_file = os.path.join(folder_path, "PluginMain.py")
                if os.path.isfile(main_file):
                    self.load_plugin(main_file)
                    
    def load_plugin(self, path):
        module_name = os.path.basename(path)[:-3]  # Usuwa ".py" z nazwy pliku
        spec = importlib.util.spec_from_file_location(module_name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for attribute_name in dir(module):
            attribute = getattr(module, attribute_name)
            if isinstance(attribute, type) and issubclass(attribute, PluginInterface) and attribute is not PluginInterface:
                plugin_instance = attribute()
                plugin_instance.on_load()
                self.plugins.append(plugin_instance)

    def unload_plugin(self, plugin_instance):
        print("UnLoading plugin "+plugin_instance.plugin_name)
        plugin_instance.on_unload()
        self.plugins.remove(plugin_instance)
        
    def getUniqueId(self):
        self.m_lastObjectId = self.m_lastObjectId + 1
        return self.m_lastObjectId
