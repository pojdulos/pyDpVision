import sys

from dpVision.Globals import Globals
from dpVision.MainApplication import MainApplication
from dpVision.MainWindow import MainWindow

MainApplication.setOrganizationName('IITiS PAN')
MainApplication.setOrganizationDomain("iitis.pl")
MainApplication.setApplicationName("pyDpVision")

myGlobals = Globals()
myGlobals.mainApp = MainApplication(sys.argv)
myGlobals.mainWin = MainWindow()

myGlobals.mainApp.load_plugins("./plugins")

myGlobals.mainWin.show()

sys.exit(myGlobals.mainApp.exec_())
