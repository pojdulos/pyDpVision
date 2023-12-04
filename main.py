import sys

from PyQt5.QtCore import QSettings

from dpVision.Globals import AP
from dpVision.MainApplication import MainApplication
from dpVision.MainWindow import MainWindow
from dpVision.Parser import Parser
from dpVision.ParserOBJ import ParserOBJ

def fastTest():
	from dpVision.AnnotationPoint import AnnotationPoint

	obj = AnnotationPoint( point=[5,5,5], vector=[1.0,0.0,0.0] )
	if not obj is None:
		AP.mainWin.workspace.m_data.append(obj)
		AP.mainWin.dock["workspace"].addNewItem(obj)

	from dpVision.AnnotationSphere import AnnotationSphere

	obj = AnnotationSphere()
	if not obj is None:
		AP.mainWin.workspace.m_data.append(obj)
		AP.mainWin.dock["workspace"].addNewItem(obj)
	AP.mainWin.update()



MainApplication.setOrganizationName('IITiS PAN')
MainApplication.setOrganizationDomain("iitis.pl")
MainApplication.setApplicationName("dpVision")

AP.mainApp = MainApplication(sys.argv)
AP.settings = QSettings()
AP.mainWin = MainWindow()

Parser.regParser(ParserOBJ)

AP.mainApp.load_plugins("./plugins")

if AP.settings.value("mainwindow/maximized", False, type=bool):
	AP.mainWin.showMaximized()
else:
	AP.mainWin.show()

#fastTest()

sys.exit(AP.mainApp.exec_())
