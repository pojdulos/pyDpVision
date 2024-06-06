import sys
# import os
# sciezka_pliku = os.path.realpath(__file__)
# sciezka_katalogu = os.path.dirname(sciezka_pliku)
# sys.path.append(sciezka_katalogu)

from PyQt5.QtCore import QSettings

from dpVision import AP, MainApplication, MainWindow, Transform

def fastTest2():
	from dpVision import Image

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
	from dpVision import AnnotationPoint, AnnotationSphere

	obj = AnnotationPoint( point=[5,5,5], vector=[1.0,0.0,0.0] )
	if not obj is None:
		AP.mainWin.workspace.m_data.append(obj)
		AP.mainWin.dock["workspace"].addNewItem(obj)

	obj = AnnotationSphere()
	if not obj is None:
		AP.mainWin.workspace.m_data.append(obj)
		AP.mainWin.dock["workspace"].addNewItem(obj)
	AP.mainWin.update()

def fastTest3():
	from dpVision import AnnotationPath

	obj = AnnotationPath( points=[[-5,-5,-5],[-5,-5,5],[5,-5,5],[5,5,5]] )
	if not obj is None:
		AP.mainWin.workspace.m_data.append(obj)
		AP.mainWin.dock["workspace"].addNewItem(obj)

	AP.mainWin.update()

def register_parsers():
	from dpVision import Parser, ParserATMDL, ParserDICOM, ParserIMAGE2D, ParserNRRD, ParserOBJ, ParserSTL
	Parser.regParser(ParserSTL)
	Parser.regParser(ParserOBJ)
	Parser.regParser(ParserATMDL)
	Parser.regParser(ParserDICOM)
	Parser.regParser(ParserNRRD)
	Parser.regParser(ParserIMAGE2D)

MainApplication.setOrganizationName('IITiS PAN')
MainApplication.setOrganizationDomain("iitis.pl")
MainApplication.setApplicationName("dpVision")

AP.mainApp = MainApplication(sys.argv)
AP.settings = QSettings()
AP.mainWin = MainWindow()
# AP.updateGlobals()

register_parsers()

AP.mainApp.load_plugins("./plugins")

if AP.settings.value("mainwindow/maximized", False, type=bool):
	AP.mainWin.showMaximized()
else:
	AP.mainWin.show()

#fastTest3()

sys.exit(AP.mainApp.exec_())
