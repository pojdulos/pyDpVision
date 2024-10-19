# -*- coding: utf-8 -*-
"""
Created on Thu Nov 23 20:04:44 2023

@author: darek
"""
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

import numpy as np

from math import tan, pi
from enum import Enum

from .. import AP, Transform

class Camera:
	positionChanged = pyqtSignal(list)
	directionChanged = pyqtSignal(list)

	def __init__(self):
		self.pos = [0.0, 0.0, 200.0]
		self.dir = [0.0, 0.0, -1.0]
		self.up = [0.0, 1.0, 0.0]

	# @pyqtProperty(list, notify=positionChanged)
	# def position(self):
	# 	return self._pos

	# @position.setter
	# def position(self, pos):
	# 	if self._pos != pos:
	# 		self._pos = pos
	# 		self.positionChanged.emit(pos)

	# @pyqtProperty(list, notify=directionChanged)
	# def direction(self):
	# 	return self._dir

	# @position.setter
	# def direction(self, dir):
	# 	if self._pos != dir:
	# 		self._pos = dir
	# 		self.directionChanged.emit(dir)


	# def reset(self):
	# 	self.position = [0.0, 0.0, 200.0]
	# 	self.direction = [0.0, 0.0, -1.0]
	# 	self._up = [0.0, 1.0, 0.0]



class GLViewer(QOpenGLWidget):
	class Projection(Enum):
		PERSPECTIVE = 0
		ORTHOGONAL = 128
	
	transformChanged = pyqtSignal(QObject)

	mouseMovedSignal = pyqtSignal(tuple)
	
	def __init__( self, win, parent = None ):
		super( GLViewer, self ).__init__( parent )
		
		self.mainWindow = win
		
		self.setAttribute(Qt.WA_DeleteOnClose)
		
		self.transform = Transform()
		
		self.lastPos = None
		
		self._camera = Camera()

		self._fBgColor = QColor(78, 78, 78)
		
		self._dViewingAngle = 50
		self._dOrthoViewSize = 90
	
		self._near = 0.1
		self._far = 100000.1
	
		self._projection = GLViewer.Projection.PERSPECTIVE

		self.transformChanged.connect(self.mainWindow.onCurrentObjectUpdated)
		self.mouseMovedSignal.connect(AP.mainApp.onMouseMoveSlot)


	# def resetGeometry(self):
	# 	m_transform.translation() = CVector3d(0.0, 0.0, 0.0);
	# 	m_transform.scale() = CPoint3d(1.0, 1.0, 1.0);
	# 	m_transform.rotation().setIdentity();
	
	# 	cam.reset();
	
	# 	update();


	def initializeGL(self):
		#QOpenGLWidget.initializeGL(self)
		print("initializeGL")
		
		format = QSurfaceFormat()

		format.setDepthBufferSize(24) # Włącz bufor głębokości z rozmiarem 24 bity
		format.setRenderableType(QSurfaceFormat.OpenGL) # Używa OpenGL (zamiast np. OpenGLES)
		format.setStencilBufferSize(8)
		format.setVersion(3, 3)
		format.setProfile(QSurfaceFormat.CoreProfile)
# 		format.setStereo(True) # Włącz buforowanie stereo
# 		format.setSwapBehavior(QSurfaceFormat.DoubleBuffer) # Włącz podwójne buforowanie
# 		format.setRedBufferSize(8) # Ustaw rozmiar bufora czerwieni na 8 bitów (dla formatu RGBA)
# 		format.setGreenBufferSize(8) # Ustaw rozmiar bufora zieleni na 8 bitów
# 		format.setBlueBufferSize(8) # Ustaw rozmiar bufora niebieskiego na 8 bitów
# 		format.setAlphaBufferSize(8) # Ustaw rozmiar bufora alfa na 8 bitów
	
		self.context().setFormat(format)
		#QOpenGLContext.currentContext().setFormat(format)

		#self.glClearColor(_fBgColor.fR(), _fBgColor.fG(), _fBgColor.fB(), 0.0f)
	
		#self.glSetFont();
	
		#glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
		glEnable(GL_DEPTH_TEST)
	
		# Włączenie normalizacji wektorów normalnych
		glEnable(GL_NORMALIZE)

		self.setMouseTracking(True)

	def recalcView(self):
		if (self._fAspect >= 1.0):
			if (self._projection == GLViewer.Projection.ORTHOGONAL):
				self._top = self._dOrthoViewSize
			else:
				self._top = self._near * tan(pi * self._dViewingAngle / 360.0)

			self._right = self._fAspect * self._top
		else:
			if (self._projection == GLViewer.Projection.ORTHOGONAL):
				self._right = self._dOrthoViewSize
			else:
				self._right = self._near * tan(pi * self._dViewingAngle / 360.0)
			
			self._top = self._right / self._fAspect
	
		self._bottom = -self._top
		self._left = -self._right


	def resizeGL( self, w, h):
		QOpenGLWidget.resizeGL(self, w, h)
	
		glMatrixMode( GL_PROJECTION )
		glLoadIdentity()

		# sL=sB=0;
		# sW=w;
		# sH=h;
	
		glViewport( 0, 0, w, h )
		glScissor( 0, 0, w, h )
	
		self._fAspect = float(w) / h
	
		self.recalcView()
	
		glMatrixMode( GL_MODELVIEW )
	
		# if (m_selectionMode != 0)
		# {
		# 	//double scale = ((double)this->height()) / m_mask.height();
		# 	//m_mask = m_mask.scaled(scale*m_mask.width(),this->height());
		# 	m_mask = m_mask.scaled(this->size());
		# }

	def paintGL(self):
		painter = QPainter()
		painter.begin(self)
	
		self.draw3Dcontent()	
		# if (m_redraw3d)
		# {
		# 	draw3Dcontent();
		# }
		# else
		# {
		# 	painter.drawImage(0, 0, m_im);
		# }
	
		# drawOverlays(painter);
	
		painter.end()


	def applyProjection(self):
		if not ( self._projection == GLViewer.Projection.ORTHOGONAL ):
			# //gluPerspective( _dViewingAngle, _fAspect, _near, _far );
			glFrustum( self._left, self._right, self._bottom, self._top, self._near, self._far )
		else:
			glOrtho( self._left, self._right, self._bottom, self._top, self._near, self._far )


	def rotate(self,dx,dy):
		xAngle = dy * 0.4
		yAngle = dx * 0.4
		# zAngle = 0.0

		invrot = self.transform.invertedMatrix()

		obj = self.mainWindow.workspace.m_currentObject
		if obj is None:
			xAxis = np.dot(invrot, np.array([1.0, 0.0, 0.0, 0.0]))
			yAxis = np.dot(invrot, np.array([0.0, 1.0, 0.0, 0.0]))
			self.transform.rotate( yAngle, yAxis )
			self.transform.rotate( xAngle, xAxis )
			self.update()
			self.transformChanged.emit(self)
		elif obj.__class__.__name__ == 'Transform':
			invrot = np.dot(obj.invertedMatrix(),invrot)
			xAxis = np.dot(invrot, np.array([1.0, 0.0, 0.0, 0.0]))
			yAxis = np.dot(invrot, np.array([0.0, 1.0, 0.0, 0.0]))
			obj.rotate2( yAngle, yAxis )
			obj.rotate2( xAngle, xAxis )
			self.update()
			self.transformChanged.emit(obj)

	def translate(self,dx,dy,dz=0.0):
		invrot = self.transform.invertedMatrix()
		obj = self.mainWindow.workspace.m_currentObject
		if obj is None:
			move = np.dot(invrot, np.array([dx, dy, dz, 0.0 ]))
			self.transform.translate(move[0],move[1],move[2])
			self.transformChanged.emit(self)
		elif obj.__class__.__name__ == 'Transform':	
			invrot = np.dot(obj.invertedMatrix(), invrot)
			move = np.dot(invrot, np.array([dx, dy, dz, 0.0 ]))
			obj.translate(move[0],move[1],move[2])
			self.transformChanged.emit(obj)
		self.update()
		
	
	def mouseMoveEvent(self, event):
		if not (self.lastPos is None):
			dx = float(event.pos().x()) - float(self.lastPos.x())
			dy = float(event.pos().y()) - float(self.lastPos.y())

			# if event.buttons() & Qt.MouseButton.LeftButton:
			# 	self.rotate(dx, dy)
			# elif event.buttons() & Qt.MouseButton.RightButton:
			# 	self.translate( dx/5, -dy/5, 0.0 )
		
			if event.buttons() & Qt.MouseButton.LeftButton:
				modifiers = QApplication.keyboardModifiers()
				if modifiers == Qt.ShiftModifier:
					self.translate( 0.0, 0.0, -dy/5 )
					#print('Shift+MouseMove')
				elif modifiers == Qt.ControlModifier:
					self.translate( dx/5, -dy/5, 0.0 )
					#print('Control+MouseMove')
				else:
					self.rotate(dx, dy)
					#print('MouseMove')
			elif event.buttons() & Qt.MouseButton.RightButton:
				obj = self.mainWindow.workspace.m_currentObject
				if obj is not None:
					obj.on_mouse_move(dx, dy)

		#x_angle, y_angle, z_angle = self.transform.getEulerAnglesDeg()
		#print("Kąty Eulera:", x_angle, y_angle, z_angle)
		#print("Wektor translacji:", self.transform.getTranslation())
		#print("Wektor skali:", self.transform.getScale())
		
		self.lastPos = event.pos()
		#self.mainWindow.dock["properties"].m_widget.updateProperties()
		self.mouseMovedSignal.emit((self,event))
		

	def mousePressEvent(self, event ):
		AP.mouse_key_pressed = True
		self.lastPos = event.pos()

	def mouseReleaseEvent(self, event ):
		AP.mouse_key_pressed = False
		self.update()

	def wheelEvent(self, event):
		d = -float(event.angleDelta().y())
		self.translate( 0.0, 0.0, d/25 )

	def draw3Dcontent(self):
		glMatrixMode(GL_MODELVIEW)
		glPushMatrix()

		glClearColor(
			self._fBgColor.redF(),
			self._fBgColor.greenF(),
			self._fBgColor.blueF(),
			self._fBgColor.alphaF() )

		glClear( GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
	
		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		
		self.render()
	
		glMatrixMode(GL_MODELVIEW)
		glPopMatrix()

	def render(self):
		self.applyProjection()
	
		glMatrixMode(GL_MODELVIEW)
		glLoadIdentity()
	
		glInitNames()
		glPushName( 0 )
	
		self.renderSceneMono()
		# if ( ! bStereo )
		# {
		# 	RenderSceneMono();
		# }
		# else if ( STEREO_QUADBUFF == iStereoMode )
		# 	RenderSceneQuadBuff();
		# else if ( STEREO_INTERLACED == iStereoMode )
		# 	RenderSceneInterlaced();
		# else if ( STEREO_COLUMNINTERLACED == iStereoMode )
		# 	RenderSceneColumnInterlaced();
		# else if ( STEREO_SIDEBYSIDE == iStereoMode )
		# 	RenderSceneSideBySide();
		# else if ( STEREO_ABOVEBELOW == iStereoMode )
		# 	RenderSceneAboveBelow();
		# else
		# {
		# 	RenderSceneAnaglyph();
		# }
	
		glPopName()

	def renderSceneMono(self):
		#glDrawBuffer(GL_BACK)
		glClear(GL_DEPTH_BUFFER_BIT)
		self.renderScene()

	def renderScene(self):
		glEnable (GL_BLEND);
		glBlendFunc (GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
	
		glEnable(GL_DEPTH_TEST)
		glDepthMask(GL_TRUE)
		glDepthFunc(GL_LEQUAL)
	
		glShadeModel( GL_SMOOTH )
	
		glEnable(GL_NORMALIZE)
		glEnable(GL_RESCALE_NORMAL)
	
		glEnable(GL_SCISSOR_TEST)
	
		glEnable(GL_LIGHTING)
	
		glMatrixMode( GL_MODELVIEW )
		glLoadIdentity()
	
		gluLookAt(
			self._camera.pos[0], self._camera.pos[1], self._camera.pos[2], \
			self._camera.dir[0], self._camera.dir[1], self._camera.dir[2], \
			self._camera.up[0], self._camera.up[1], self._camera.up[2] )
		#gluLookAt(0.0, 0.0, 200, 0.0, 0.0, -1.0, 0.0, 1.0, 0.0)
	
		#self.renderLights( False )
		self.renderLights( True )
	
		# // OPCJONALNIE TU MOZNA WYSWIETLAC OBRAZEK TLA
		# // NP. AP::mainApp().GetBGplaneRef().Render( SINGLE_IMAGE ); 
	
		glMultMatrixf(self.transform.toGLMatrix())
		# cameraTransformations();


		# if (m_drawAxes) rysujOsie();
		self.rysujOsie()
		
		# AP::getWorkspace()->render();
		self.mainWindow.workspace.render()
	
		# //rysujGimbal();
	
		glDisable(GL_LIGHTING)
		glDisable( GL_DEPTH_TEST )
	
		glDisable(GL_BLEND);

	def renderLights(self, perm ):
		if perm:
			#glDisable( GL_LIGHT0 )
			glLightfv( GL_LIGHT0, GL_AMBIENT, [ 0.3, 0.3, 0.3, 1.0 ] )
			glLightfv( GL_LIGHT0, GL_DIFFUSE, [ 0.3, 0.3, 0.3, 1.0 ] )
			glLightfv( GL_LIGHT0, GL_SPECULAR, [ 0.0, 0.0, 0.0, 1.0 ] )
			glLightfv( GL_LIGHT0, GL_POSITION, [0.0, 0.0, 200.0, 0.0] )
			#glLightfv( GL_LIGHT0, GL_SPOT_DIRECTION, [-5.0, -20.0, -100.0] )
			#glLightfv( GL_LIGHT0, GL_SPOT_DIRECTION, [0.0,-0.4472,-0.8944] )
			glLightfv( GL_LIGHT0, GL_SPOT_DIRECTION, [0.0,0.0,-1.0] )
			glLightf( GL_LIGHT0, GL_SPOT_CUTOFF, 60.0 );
			glEnable( GL_LIGHT0 )
# 		else:
# 			glDisable( GL_LIGHT1 )
# 			glLightfv( GL_LIGHT1, GL_AMBIENT, [ 0.2, 0.2, 0.2, 1.0 ] )
# 			glLightfv( GL_LIGHT1, GL_DIFFUSE, [ 0.4, 0.4, 0.4, 1.0 ] )
# 			glLightfv( GL_LIGHT1, GL_SPECULAR, [ 0.6, 0.6, 0.6, 1.0 ] )
# 			glLightfv( GL_LIGHT1, GL_POSITION, [20.0, 0.0, -20.0, 1.0] )
# 			glLightfv( GL_LIGHT1, GL_SPOT_DIRECTION, [-20.0, 0.0, 20.0] )
# 			glLightf( GL_LIGHT1, GL_SPOT_CUTOFF, 60.0 );
# 			glEnable( GL_LIGHT1 )


	def rysujOsie(self):
		zCol = [ 0.2, 0.2, 0.8 ]
		yCol = [ 0.2, 0.8, 0.2 ]
		xCol = [ 0.8, 0.2, 0.2 ]
	
		glPushAttrib(GL_ALL_ATTRIB_BITS)
	
		g0 = 0.5
		g1 = 1.0
		a = 1.0
		s0 = 32
	
		glDisable(GL_TEXTURE_2D);
		glEnable(GL_COLOR_MATERIAL);
	
		glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE);
	
		glEnable(GL_LINE_SMOOTH);
	
		self.triad3D( 0.1, 45.0, 0.4, 5.0, True )
		# if (m_drawAxes == AxesStyle_ARROWS)
		# {
		# 	triad3D( 0.1, 45.0, 0.4, 5.0, (AP::WORKSPACE::getCurrentModelId() < 0) );
		# }
		# else if (m_drawAxes == AxesStyle_PLANES)
		# {
		# 	bool active = (AP::WORKSPACE::getCurrentModelId() < 0);
	
		# 	glColor3f(0.2f, 0.2f, 0.2f);
	
		# 	// X
		# 	if (active) glColor3fv(xCol);
	
		# 	glLineWidth(0.3);
		# 	glBegin(GL_LINES);
		# 	for (auto n = -100; n < 101; n += 10)
		# 	{
		# 		glVertex3f(-100, 0, n); glVertex3f(100, 0, n);
		# 	}
		# 	glEnd();
	
		# 	glLineWidth(3);
		# 	glBegin(GL_LINES);
		# 	glVertex3f(-1000, 0, 0); glVertex3f(1000, 0, 0);
		# 	glEnd();
	
		# 	// Y
		# 	if (active) glColor3fv(yCol);
	
		# 	glLineWidth(3);
		# 	glBegin(GL_LINES);
		# 	glVertex3f(0, -1000, 0); glVertex3f(0, 1000, 0);
		# 	glEnd();
	
		# 	// Z
		# 	if (active) glColor3fv(zCol);
	
		# 	glLineWidth(0.3);
		# 	glBegin(GL_LINES);
		# 	for (auto n = -100; n < 101; n += 10)
		# 	{
		# 		glVertex3f(n, 0, -100); glVertex3f(n, 0, 100);
		# 	}
		# 	glEnd();
	
		# 	glLineWidth(3);
		# 	glBegin(GL_LINES);
		# 	glVertex3f(0, 0, -1000); glVertex3f(0, 0, 1000);
		# 	glEnd();
	
		# }
		# else if (m_drawAxes == AxesStyle_LINES)
		# {
		# 	bool active = (AP::WORKSPACE::getCurrentModelId() < 0);
	
		# 	glColor3f(0.2f, 0.2f, 0.2f);
		# 	glLineWidth(1);
		# 	glBegin(GL_LINES);
	
		# 	// X
		# 	if (active) glColor3fv(xCol);
		# 	glVertex3f(-10000, 0, 0); glVertex3f(10000, 0, 0);
	
		# 	// Y
		# 	if (active) glColor3fv(yCol);
		# 	glVertex3f(0, -10000, 0); glVertex3f(0, 10000, 0);
	
		# 	// Z
		# 	if (active) glColor3fv(zCol);
		# 	glVertex3f(0, 0, -10000); glVertex3f(0, 0, 10000);
	
		# 	glEnd();
		# }
	
		glDisable(GL_COLOR_MATERIAL)
	
		glPopAttrib()

	def triad3D(self,  W1, L1, W2, L2, active):
		zCol = [ 0.2, 0.2, 0.8 ]
		yCol = [ 0.2, 0.8, 0.2 ]
		xCol = [ 0.8, 0.2, 0.2 ]
	
		glColor3f( 0.2, 0.2, 0.2 )
	
		if (active):
			glColor3fv( zCol ) # Z axis in red.
		self.axis3D( W1, L1, W2, L2)
	
		if (active):
			glColor3fv( yCol ) # Y axis is green.
		glPushMatrix()
		glRotatef(-90, 1, 0, 0)
		self.axis3D(W1, L1, W2, L2)
		glPopMatrix()
	
		if (active):
			glColor3fv( xCol ) # X axis is blue.
		glPushMatrix()
		glRotatef(90, 0, 1, 0)
		self.axis3D(W1, L1, W2, L2)
		glPopMatrix()
	
		# //GLUquadric* sph = gluNewQuadric();
		if (active):
			glColor3f( 0.7, 0.7, 0.7 )
		# //gluSphere(sph, W2, 16, 16);
		# //gluDeleteQuadric(sph);
	
		glEnable(GL_POINT_SMOOTH)
		glPointSize(5)
		glBegin(GL_POINTS)
		glVertex3f(0, 0, 0)
		glEnd()

	def drawLine(self, width, start, end):
		glLineWidth(width)
		glBegin(GL_LINES)
		glVertex3f(0, 0, start)
		glVertex3f(0, 0, end)
		glEnd()

	def axis3D(self, W1, L1, W2, L2 ):
		self.drawLine( 1, 0, 47)
		self.drawLine(11, 47, 47.5)
		self.drawLine( 9, 47.5, 48)
		self.drawLine( 7, 48, 48.5)
		self.drawLine( 5, 48.5, 49)
		self.drawLine( 3, 49, 49.5)
		self.drawLine( 1, 49.5, 50)

	def calculate_frustum_matrix(self, left, right, bottom, top, near, far):
		# Inicjalizacja macierzy 4x4 zerami
		frustum_matrix = np.zeros((4, 4), dtype=np.float32)
		
		# Wypełnianie wartościami zgodnie ze wzorem dla macierzy perspektywy
		frustum_matrix[0, 0] = 2 * near / (right - left)
		frustum_matrix[1, 1] = 2 * near / (top - bottom)
		frustum_matrix[0, 2] = (right + left) / (right - left)
		frustum_matrix[1, 2] = (top + bottom) / (top - bottom)
		frustum_matrix[2, 2] = -(far + near) / (far - near)
		frustum_matrix[3, 2] = -1
		frustum_matrix[2, 3] = -(2 * far * near) / (far - near)
		
		return frustum_matrix

	def look_at(self, eye, center, up):
		f = np.array(center) - np.array(eye)
		f = f / np.linalg.norm(f)

		u = np.array(up)
		u = u / np.linalg.norm(u)

		s = np.cross(f, u)
		u = np.cross(s, f)

		m = np.identity(4, dtype=np.float32)
		m[0, :3] = s
		m[1, :3] = u
		m[2, :3] = -f
		m[3, 3] = 1.0

		translation = np.identity(4, dtype=np.float32)
		translation[:3, 3] = -np.array(eye)

		return np.dot(m, translation)

	def get_mouse_ray(self, x, y):
			w = self.width()
			h = self.height()

			win_x = float(x) / w
			win_y = float(h - y) / h  # Inwersja osi Y

			# Get the normalized device coordinates (NDC)
			near_ndc = np.array([win_x * 2 - 1, win_y * 2 - 1, -1.0, 1.0], dtype=np.float32)
			far_ndc = np.array([win_x * 2 - 1, win_y * 2 - 1,  1.0, 1.0], dtype=np.float32)

			# Obliczenie macierzy modelview dla kamery
			center = [0, 0, 0]  # Punkt patrzenia
			view_matrix = self.look_at(self._camera.pos, center, self._camera.up)

			model_matrix = self.transform.toNumPy()

			# Obliczenie macierzy projekcji
			projection_matrix = self.calculate_frustum_matrix(self._left, self._right, self._bottom, self._top, self._near, self._far)


			# Calculate the combined MVP matrix
			mvp_matrix = np.dot( np.dot( projection_matrix, view_matrix ), model_matrix )

			mvp_inv = np.linalg.inv(mvp_matrix)

			# Convert NDC to world space coordinates
			near_ray = np.dot(mvp_inv, near_ndc)
			far_ray = np.dot(mvp_inv, far_ndc)

			# Normalize the rays
			near_ray = near_ray / near_ray[3]
			far_ray = far_ray / far_ray[3]

			return near_ray, far_ray
