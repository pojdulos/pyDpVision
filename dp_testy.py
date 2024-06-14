from dpVision import AP, Transform, Image, AnnotationPoint, AnnotationSphere, AnnotationPath

from PyQt5.QtCore import QTimer

from dpVision.volumetric import Volumetric

def fastTest1():
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

def fastTest2():
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
	obj = AnnotationPath( points=[[-5,-5,-5],[-5,-5,5],[5,-5,5],[5,5,5]] )
	if not obj is None:
		AP.mainWin.workspace.m_data.append(obj)
		AP.mainWin.dock["workspace"].addNewItem(obj)

	AP.mainWin.update()

def fastTest4():
	def onTimeout():
		if not hasattr(onTimeout, "cnt"):
			onTimeout.cnt = 0
		print(f"step: {onTimeout.cnt}")
		onTimeout.cnt += 1
		timer.start(1000)
	timer = QTimer()
	timer.setSingleShot(True)
	timer.timeout.connect(onTimeout)
	timer.start(1000)

def fast_test_5():
	volum = Volumetric.create(layers=128, rows=128, columns=128)
	volum.set_position(x=-64.0, y=-64.0, z=-64.0)
	#volum.set_pixel_size(image_x=0.4, image_y=0.1, slice_thickness=0.2)
	#volum.drawBox(origin=[10,10,10], size=[10,50,100], color=1000.)
	#volum.drawBox(origin=[70,10,30], size=[50,50,70], color=800.)
	#volum.drawBox(origin=[10,10,50], size=[60,50,20], color=1200.)
	volum.drawSphere(origin=[64,54,64], radius=30, color=2000.)
	volum.drawSphere(origin=[64,54,64], radius=25, color=0.)
	volum.drawBox(origin=[10,0,10], size=[100,50,100], color=0.)
	volum.drawCylinder(origin=[64,100,64], radius=6, height=35, axis='y', color=2000.)
	volum.drawBox(origin=[50,117,50], size=[28,10,28], color=2000.)
	AP.addObject(volum)
	volum.export(dir="v:/test/", file_base="image")

def fast_test_6():
	import numpy as np
	ar = np.array([[[1,2,3],[4,5,6]],[[11,12,13],[14,15,16]],[[21,22,23],[24,25,26]],[[31,32,33],[34,35,36]]])
	print(ar.shape)

fast_test_5()
