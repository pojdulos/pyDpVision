import sys
from PyQt5.QtCore import QSettings

from dpVision import AP, MainApplication
from dpVision.gui import MainWindow
from dpVision.parsers import *
import locale

def set_logger():
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            # logging.FileHandler("pyDpVision.log", mode="w", encoding="utf-8"), # logi do pliku
            logging.StreamHandler()              # logi na konsolę
        ]
    )
    logging.getLogger("frasta").setLevel(logging.DEBUG)

set_logger()

locale.setlocale(locale.LC_NUMERIC, 'pl_PL.UTF-8')

MainApplication.setOrganizationName('IITiS PAN')
MainApplication.setOrganizationDomain("iitis.pl")
MainApplication.setApplicationName("dpVision")

# inicjalizacja 'zmiennych globalnych'
AP.mainApp = MainApplication(sys.argv)
AP.settings = QSettings()
AP.mainWin = MainWindow()

# ładowanie pluginów z określonego katalogu
AP.mainApp.load_plugins("./plugins")
#from plugins import *

if AP.settings.value("mainwindow/maximized", False, type=bool):
	AP.mainWin.showMaximized()
else:
	AP.mainWin.show()

#######################################################################
# 
# dp_testy to mój roboczy moduł służący do testowania różnych rzeczy
# import do usunięcia w wersji 'produkcyjnej'
from dp_testy import *
#######################################################################

#from OpenGL.GL import *
#print(glGetString(GL_VERSION))

sys.exit(AP.mainApp.exec_())
