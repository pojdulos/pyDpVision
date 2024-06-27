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

def kielich_maly():
	volum = Volumetric.create(layers=128, rows=128, columns=128)
	volum.set_position(x=-64.0, y=-64.0, z=-64.0)
	volum.drawSphere(origin=[64,54,64], radius=30, color=2000.)
	volum.drawSphere(origin=[64,54,64], radius=25, color=0.)
	volum.drawBox(origin=[10,0,10], size=[100,50,100], color=0.)
	volum.drawCylinder(origin=[64,100,64], radius=6, height=35, axis='y', color=2000.)
	volum.drawBox(origin=[50,117,50], size=[28,10,28], color=2000.)
	AP.addObject(volum)

def kielich_duzy(volum):
	volum.drawSphere(origin=[256,216,256], radius=120, color=2000.)
	volum.drawSphere(origin=[256,216,256], radius=100, color=0.)
	volum.drawBox(origin=[40,0,40], size=[400,200,400], color=0.)
	volum.drawCylinder(origin=[256,400,256], radius=24, height=140, axis='y', color=2000.)
	volum.drawBox(origin=[200,468,200], size=[112,40,112], color=2000.)



def fast_test_5(layers=2048, rows=2048, columns=2048):
	volum = Volumetric.create(layers=layers, rows=rows, columns=columns)
	if volum:
		x, y, z = int(columns/2), int(rows/2), int(layers/2)
		w = [int(columns/25), int(rows/25), int(layers/25)]
		volum.set_position(x=float(-x), y=float(-y), z=float(-z))
		volum.drawSphere(origin=[x, y, z], radius=int(layers/8), color=2000.)
		volum.drawBox(origin=[x-w[0],y-w[1],0], size=[w[0]*2,w[1]*2,layers], color=1000.)
		volum.drawBox(origin=[x-w[0],0,z-w[2]], size=[w[0]*2,rows,w[2]*2], color=1000.)
		volum.drawBox(origin=[0,y-w[1],z-w[2]], size=[columns,w[1]*2,w[2]*2], color=1000.)
		AP.addObject(volum)

def fast_test_7():
	volum = Volumetric.create(layers=256, rows=256, columns=256)
	volum.set_position(x=-128.0, y=-128.0, z=-128.0)
	volum.drawBox(origin=[50,50,50], size=[150,150,150], color=1000.)
	volum.drawBox(origin=[75,75,75], size=[100,100,100], color=750.)
	volum.drawBox(origin=[100,100,100], size=[50,50,50], color=500.)
	# volum.drawSphere(origin=[256,216,256], radius=120, color=2000.)
	AP.addObject(volum)




fast_test_5(256,256,256)
