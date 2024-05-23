import sys
# import os
# sciezka_pliku = os.path.realpath(__file__)
# sciezka_katalogu = os.path.dirname(sciezka_pliku)
# sys.path.append(sciezka_katalogu)

from PyQt5.QtCore import QSettings

from dpVision.Globals import AP
from dpVision.MainApplication import MainApplication
from dpVision.MainWindow import MainWindow
from dpVision.Transform import Transform

def fastTest2():
	from dpVision.Image import Image
	from PyQt5.QtGui import QImage

	obj = Image(path = "d:\\rozmiary2.PNG")
	if not obj is None:
		tra = Transform()
		if not tra is None:
			tra.addChild(obj)
			AP.mainWin.workspace.m_data.append(tra)
			AP.mainWin.dock["workspace"].addNewItem(tra)

		obj2 = Image(image = obj)
		if not obj2 is None:
			tra2 = Transform()
			if not tra2 is None:
				tra2.addChild(obj2)
				AP.mainWin.workspace.m_data.append(tra2)
				AP.mainWin.dock["workspace"].addNewItem(tra2)

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

def fastTest3():
	from dpVision.AnnotationPath import AnnotationPath

	obj = AnnotationPath( points=[[-5,-5,-5],[-5,-5,5],[5,-5,5],[5,5,5]] )
	if not obj is None:
		AP.mainWin.workspace.m_data.append(obj)
		AP.mainWin.dock["workspace"].addNewItem(obj)

	AP.mainWin.update()

def init_parsers():
	from dpVision.Parser import Parser
	from dpVision.ParserSTL import ParserSTL
	Parser.regParser(ParserSTL)
	from dpVision.ParserOBJ import ParserOBJ
	Parser.regParser(ParserOBJ)
	from dpVision.ParserATMDL import ParserATMDL
	Parser.regParser(ParserATMDL)
	from dpVision.ParserDICOM import ParserDICOM
	Parser.regParser(ParserDICOM)
	from dpVision.ParserNRRD import ParserNRRD
	Parser.regParser(ParserNRRD)
	from dpVision.ParserIMAGE2D import ParserIMAGE2D
	Parser.regParser(ParserIMAGE2D)

MainApplication.setOrganizationName('IITiS PAN')
MainApplication.setOrganizationDomain("iitis.pl")
MainApplication.setApplicationName("dpVision")

AP.mainApp = MainApplication(sys.argv)
AP.settings = QSettings()
AP.mainWin = MainWindow()
# AP.updateGlobals()

init_parsers()

AP.mainApp.load_plugins("./plugins")

if AP.settings.value("mainwindow/maximized", False, type=bool):
	AP.mainWin.showMaximized()
else:
	AP.mainWin.show()

#fastTest3()

sys.exit(AP.mainApp.exec_())
