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
	mousePressedSignal = pyqtSignal(tuple)
	
	def __init__( self, win, parent = None ):
		super( GLViewer, self ).__init__( parent )
		
		self.mainWindow = win
		
		self.setAttribute(Qt.WA_DeleteOnClose)
		
		self.transform = Transform()
		
		self.lastPos = None
		
		self.m_drawAxes = True

		self._camera = Camera()

		self._fBgColor = QColor(78, 78, 78)
		
		self._dViewingAngle = 50
		self._dOrthoViewSize = 90
	
		self._near = 0.1
		self._far = 100000.1

		# Bazowy rozmiar przestrzeni zainteresowania (w jednostkach świata).
		# Steruje pozycją kamery, near/far i skalą ortho.
		# setViewScale(200) → odtwarza domyślne ustawienia 1:1.
		self._dDefaultViewSize = 200.0
		self._dCurrentViewSize = 200.0

		# Jednostka wyświetlania — obiekty przechowują dane w µm (Surface),
		# a viewer skaluje do wybranej jednostki świata.
		# Mapowanie: nazwa → współczynnik (ile µm = 1 jednostka docelowa)
		self._UNIT_SCALES = {
			'nm':  0.001,
			'µm':  1.0,
			'mm':  1_000.0,
			'cm':  10_000.0,
			'm':   1_000_000.0,
		}
		self.display_unit = 'mm'  # domyślna jednostka świata viewera

		# _fAspect potrzebny przez recalcView(); właściwa wartość ustawiana w resizeGL
		self._fAspect = 1.0

		self._projection = GLViewer.Projection.PERSPECTIVE

		# Zastosuj domyślną skalę — ustawia kamerę, near/far, orthoViewSize
		self.setViewScale(self._dCurrentViewSize)
		
		# Selection area mode
		self.selection_mode = False
		self.selection_pixmap = QPixmap()
		self.selection_path = QPainterPath()
		self.is_drawing_selection = False
		self.brush_size = 5  # Grubość pędzla
		self.cursor_pos = QPoint()  # Pozycja kursora dla rysowania kółka

		self.transformChanged.connect(self.mainWindow.onCurrentObjectUpdated)
		self.mouseMovedSignal.connect(AP.mainApp.onMouseMoveSlot)
		self.mousePressedSignal.connect(AP.mainApp.onMousePressSlot)
		

	@property
	def unit_scale(self) -> float:
		"""Współczynnik skali µm → jednostka viewera (do wbudowania w MVP)."""
		return 1.0 / self._UNIT_SCALES.get(self.display_unit, 1_000.0)

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

	def setViewScale(self, size):
		"""Dopasowuje widok kamery do sceny o podanym rozmiarze.

		Parametry są dobrane tak, że setViewScale(200) odtwarza dokładnie
		domyślne ustawienia, więc zmiana nie psuje istniejącego zachowania.

		size : float
		    Przybliżona średnica / bok obszaru zainteresowania w jednostkach
		    świata.  Przykłady:
		      • skan głowy (~250 mm)  → setViewScale(250)
		      • próbka 10×10 mm       → setViewScale(10)
		      • dane w skali [0,1]    → setViewScale(1)
		"""
		size = float(size)
		self._dCurrentViewSize = size
		self._camera.pos = [0.0, 0.0, size]          # kamera w odległości = size od środka
		self._near       = max(0.001, size * 0.0005)  # 0.1   przy size=200
		self._far        = size * 500.0               # 100000 przy size=200
		self._dOrthoViewSize = max(1, round(size * 0.45))  # 90 przy size=200
		self.recalcView()
		self.update()

	def resetView(self):
		"""Przywraca kamerę i transformację sceny do stanu domyślnego."""
		self.transform.reset()
		self.setViewScale(self._dDefaultViewSize)

	def pan_to_bounding_box(self, bb_min, bb_max):
		"""Przesuwa scenę (pan) tak by środek AABB znalazł się w punkcie [0,0,0]
		widoku — bez zmiany odległości kamery ani skali.

		bb_min, bb_max – współrzędne w jednostkach danych obiektów (np. m dla E57).
		"""
		s = 1000.0 / self._UNIT_SCALES[self.display_unit]
		cx = (bb_min[0] + bb_max[0]) / 2.0 * s
		cy = (bb_min[1] + bb_max[1]) / 2.0 * s
		cz = (bb_min[2] + bb_max[2]) / 2.0 * s
		self.transform.reset()
		self.transform.setTranslation(-cx, -cy, -cz)
		self.update()


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
		import time
		t_paint_start = time.perf_counter()
		
		painter = QPainter()
		painter.begin(self)
	
		t_before_3d = time.perf_counter()
		self.draw3Dcontent()	
		t_after_3d = time.perf_counter()
		
		# if (m_redraw3d)
		# {
		# 	draw3Dcontent();
		# }
		# else
		# {
		# 	painter.drawImage(0, 0, m_im);
		# }
	
		# drawOverlays(painter);
		
		# Rysuj warstwę zaznaczenia jeśli aktywna
		if self.selection_mode:
			if not self.selection_pixmap.isNull():
				painter.drawPixmap(0, 0, self.selection_pixmap)
			
			# Rysuj kółko kursora pokazujące rozmiar pędzla
			painter.setRenderHint(QPainter.Antialiasing)
			pen = QPen(QColor(0, 255, 255, 128), 2, Qt.SolidLine)
			painter.setPen(pen)
			painter.setBrush(Qt.NoBrush)
			radius = self.brush_size / 2.0
			painter.drawEllipse(self.cursor_pos, radius, radius)
			
			# Rysuj krzyżyk w środku
			cross_size = 3
			painter.drawLine(self.cursor_pos.x() - cross_size, self.cursor_pos.y(), 
			                 self.cursor_pos.x() + cross_size, self.cursor_pos.y())
			painter.drawLine(self.cursor_pos.x(), self.cursor_pos.y() - cross_size,
			                 self.cursor_pos.x(), self.cursor_pos.y() + cross_size)
	
		t_before_end = time.perf_counter()
		painter.end()
		t_after_end = time.perf_counter()
		
		# Profilowanie paintGL
		t_paint_end = time.perf_counter()
		paint_total = t_paint_end - t_paint_start
		draw3d_time = t_after_3d - t_before_3d
		painter_end_time = t_after_end - t_before_end
		other_time = paint_total - draw3d_time - painter_end_time
		
		# Wyświetl co 30 klatek
		if not hasattr(self, '_paint_frame_count'):
			self._paint_frame_count = 0
			self._paint_total = 0.0
			self._paint_min = float('inf')
			self._paint_max = 0.0
			# print("\n=== PAINTGL PROFILING ===")
		
		self._paint_frame_count += 1
		self._paint_total += paint_total
		self._paint_min = min(self._paint_min, paint_total)
		self._paint_max = max(self._paint_max, paint_total)
		
		if self._paint_frame_count % 30 == 0:
			avg = self._paint_total / 30
			# print(f"[paintGL {self._paint_frame_count:4d}] Avg: {avg*1000:6.2f}ms | Min: {self._paint_min*1000:6.2f}ms | Max: {self._paint_max*1000:6.2f}ms")
			# print(f"  Latest breakdown: draw3D={draw3d_time*1000:.2f}ms, painter.end={painter_end_time*1000:.2f}ms, other={other_time*1000:.2f}ms")
			self._paint_total = 0.0
			self._paint_min = float('inf')
			self._paint_max = 0.0

	def switchBB(self):
		self.m_drawAxes = not self.m_drawAxes
	
	def enableSelectionMode(self):
		"""Włącza tryb zaznaczania obszaru"""
		self.selection_mode = True
		self.selection_pixmap = QPixmap(self.size())
		self.selection_pixmap.fill(Qt.transparent)
		self.selection_path = QPainterPath()
		self.is_drawing_selection = False
		self.update()
	
	def disableSelectionMode(self):
		"""Wyłącza tryb zaznaczania i czyści zaznaczenie"""
		self.selection_mode = False
		self.is_drawing_selection = False
		self.selection_pixmap = QPixmap()
		self.selection_path = QPainterPath()
		self.update()

	def applyProjection(self, projection=None):
		if projection is not None:
			self._projection = projection

		if not ( self._projection == GLViewer.Projection.ORTHOGONAL ):
			# //gluPerspective( _dViewingAngle, _fAspect, _near, _far );
			glFrustum( self._left, self._right, self._bottom, self._top, self._near, self._far )
		else:
			glOrtho( self._left, self._right, self._bottom, self._top, self._near, self._far )


	def rotate_object(self, obj:Transform, xAngle, yAngle, zAngle=0.0):
		lck = obj.locked
		# print('rotate_object: locked' if lck else 'rotate_object: unlocked')
		if lck:
			return
		
		midpoint = obj.getMidpoint()
		p1 = obj.toNumPy().dot(np.array([*midpoint, 1.0]))[:3]

		inv_rot = self.transform.m_rotation.inv()

		# osie ekranu → world space
		xAxis = inv_rot.apply([1.0, 0.0, 0.0])
		yAxis = inv_rot.apply([0.0, 1.0, 0.0])
		zAxis = inv_rot.apply([0.0, 0.0, 1.0])

		obj.rotate(xAngle, xAxis, origin=p1)
		obj.rotate(yAngle, yAxis, origin=p1)
		obj.rotate(zAngle, zAxis, origin=p1)


	def rotate_scene(self, xAngle, yAngle, zAngle=0.0):
		self.transform.rotate(xAngle, [1.0, 0.0, 0.0])
		self.transform.rotate(yAngle, [0.0, 1.0, 0.0])
		self.transform.rotate(zAngle, [0.0, 0.0, 1.0])


	def rotate(self, dx, dy, dz=0.0):
		# przeliczenie pikseli na stopnie
		xAngle = (dy / self.height()) * 180.0
		yAngle = (dx / self.width())  * 180.0
		# zAngle = (dz / min(self.width(), self.height())) * 180.0  # np. obrót "skrętny"
		zAngle = (dz / self.width()) * 180.0

		# obj = self.mainWindow.workspace.m_currentObject
		objs = self.mainWindow.dock["workspace"].getSelectedObjects()
		obj = objs[0] if len(objs) == 1 else None

		if obj is not None and isinstance(obj, Transform):
			self.rotate_object(obj, xAngle, yAngle, zAngle)
			self.transformChanged.emit(obj)
		else:
			self.rotate_scene(xAngle, yAngle, zAngle)
			self.transformChanged.emit(self)

		self.update()
		self.mainWindow.dock["properties"].updateProperties()

	def translate(self, dx, dy, dz=0.0):
		dist = np.linalg.norm(self._camera.pos)  # odległość kamery od środka sceny
		scale = dist * 0.75                       # współczynnik czułości
		stepX = scale * dx / self.width()
		stepY = scale * dy / self.height()
		stepZ = scale * dz / self.height()

		# --- osie ekranu z kamery ---
		forward = np.array(self._camera.dir, dtype=float)   # Z ekranu
		forward /= np.linalg.norm(forward)

		up = np.array(self._camera.up, dtype=float)         # Y ekranu
		up /= np.linalg.norm(up)

		right = np.cross(forward, up)                       # X ekranu
		right /= np.linalg.norm(right)

		obj = self.mainWindow.workspace.m_currentObject

		if obj is None:
			# --- przesuwanie kamery ---
			# używamy czystych osi kamery → typowy screen-space
			move = stepX * right + stepY * up + stepZ * forward
			self.transform.translate(*move)
			self.transformChanged.emit(self)
			#print("translacja KAMERY:", move)
		elif isinstance(obj, Transform) and not obj.locked:
			# --- przesuwanie obiektu ---
			# osie kamery przekształcone do układu Workspace (uwzględniają obrót sceny)
			inv_rot = self.transform.m_rotation.inv()
			right_ws = inv_rot.apply(right)
			up_ws = inv_rot.apply(up)
			forward_ws = inv_rot.apply(forward)

			move = stepX * right_ws + stepY * up_ws + stepZ * forward_ws
			obj.translate(*move)
			self.transformChanged.emit(obj)
			#print("translacja OBIEKTU:", move)

		self.update()

	def drawSelectionPath(self, pos=None):
		if self.selection_mode:
			painter = QPainter(self.selection_pixmap)
			painter.setRenderHint(QPainter.Antialiasing)
			# Użyj CompositionMode_Source aby nie sumować alfa przy nakładaniu
			painter.setCompositionMode(QPainter.CompositionMode_Source)
			pen = QPen(QColor(0, 255, 255, 64), self.brush_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
			painter.setPen(pen)
			if pos is not None:
				if self.lastPos is not None:
					painter.drawLine(self.lastPos, pos)
				else:
					painter.drawPoint(pos)
			painter.end()
				
	def mouseMoveEvent(self, event):
		# Zapisz pozycję kursora (dla rysowania kółka)
		self.cursor_pos = event.pos()
		
		if self.selection_mode and self.is_drawing_selection:
			# Rysowanie ścieżki zaznaczenia
			if self.lastPos is not None:
				self.drawSelectionPath(event.pos())
				
				# Dodaj do ścieżki
				if self.selection_path.isEmpty():
					self.selection_path.moveTo(self.lastPos)
				self.selection_path.lineTo(event.pos())
				
				self.update()
			self.lastPos = event.pos()
		elif self.selection_mode:
			# W trybie zaznaczania, ale nie rysujemy - odświeżamy dla kółka kursora
			self.update()
		elif self.lastPos is not None:
			dx = float(event.pos().x()) - float(self.lastPos.x())
			dy = float(event.pos().y()) - float(self.lastPos.y())

			if event.buttons() & Qt.MouseButton.LeftButton:
				modifiers = QApplication.keyboardModifiers()
				if modifiers == Qt.ShiftModifier:
					# zoom (przód/tył wzdłuż osi kamery)
					self.translate(0.0, 0.0, -dy)
				elif modifiers == Qt.ControlModifier:
					# przesuwanie w płaszczyźnie ekranu
					self.translate(dx, -dy, 0.0)
				elif modifiers == Qt.AltModifier:
					# obrót "skrętny" wokół osi Z
					self.rotate(0.0, 0.0, dx)
				else:	
					# obrót
					self.rotate(dx, dy, 0.0)

			elif event.buttons() & Qt.MouseButton.RightButton:
				obj = self.mainWindow.workspace.m_currentObject
				if obj is not None:
					obj.on_mouse_move(dx, dy)

			self.lastPos = event.pos()
		
		self.mouseMovedSignal.emit((self, event))
		

	def mousePressEvent(self, event ):
		if self.selection_mode and event.button() == Qt.MouseButton.LeftButton:
			self.is_drawing_selection = True
			self.lastPos = None
			self.drawSelectionPath(event.pos())
			self.lastPos = event.pos()
			self.update()
		else:
			AP.mouse_key_pressed = True
			self.lastPos = event.pos()
		self.mousePressedSignal.emit((self,event))

	def mouseReleaseEvent(self, event ):
		if self.selection_mode and event.button() == Qt.MouseButton.LeftButton:
			self.is_drawing_selection = False
			self.lastPos = None
		else:
			AP.mouse_key_pressed = False
		self.update()

	def wheelEvent(self, event):
		if self.selection_mode:
			# W trybie zaznaczania - zmień grubość pędzla
			dy = float(event.angleDelta().y())
			if dy > 0:
				self.brush_size = min(self.brush_size + 1, 300)  # Maksymalnie 50
			else:
				self.brush_size = max(self.brush_size - 1, 1)   # Minimalnie 1
			self.update()
		else:
			# Normalny zoom
			dy = float(event.angleDelta().y())
			self.translate( 0.0, 0.0, -dy )

	def _drainGLAttribStack(self):
		"""Opróżnia stos atrybutów GL w przypadku niesparowanych Push/Pop
		z poprzednich klatek (np. po wyjątkach w renderSelf obiektów)."""
		while True:
			try:
				glPopAttrib()
			except Exception:
				break

	def draw3Dcontent(self):
		glClearColor(
			self._fBgColor.redF(),
			self._fBgColor.greenF(),
			self._fBgColor.blueF(),
			self._fBgColor.alphaF() )

		glClear( GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
	
		# Wyczyść stos atrybutów GL przed każdą klatką
		# (zabezpieczenie przed wyciekami stosu z poprzednich klatek)
		self._drainGLAttribStack()

		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		
		self.render()

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


		if self.m_drawAxes:
			self.rysujOsie()
		
		# Skalowanie świata: obiekty trzymają dane w mm (world unit);
		# viewer skaluje mm → jednostkę wyświetlania jednym glScalef.
		# GridData64 sam konwertuje µm→mm przez własny MVP — modelview które odczytuje
		# zawiera już tę skalę, więc jest obsłużony automatycznie.
		s_mm = 1000.0 / self._UNIT_SCALES[self.display_unit]  # mm → viewer unit
		glPushMatrix()
		if s_mm != 1.0:
			glScalef(s_mm, s_mm, s_mm)
		try:
			wboit_reinit = False
			cam_pos = list(self._camera.pos)
			view_dir = [
				self._camera.dir[0] - self._camera.pos[0],
				self._camera.dir[1] - self._camera.pos[1],
				self._camera.dir[2] - self._camera.pos[2],
			]
			ws = self.mainWindow.workspace

			# Pass 1: normalny render dla obiektów nieprzezroczystych.
			# Renderuje opaque geometry i zapełnia depth buffer.
			ws.render(opaque_only=True, camera_pos=cam_pos, view_dir=view_dir)

			# Pass 2 (opcjonalnie): WBOIT dla przezroczystych obiektów.
			# Uruchamiamy tylko jeśli scena ma przezroczyste obiekty.
			if ws.has_transparent():
				# Zainicjuj WBOIT resources jeśli potrzeba
				w, h = self.width(), self.height()
				if (getattr(self, '_wboit_fbo', None) is None or
					getattr(self, '_wboit_w', 0) != w or
					getattr(self, '_wboit_h', 0) != h):
					self._init_wboit_resources(w, h)
					wboit_reinit = True

				if getattr(self, '_wboit_fbo', None) is not None:
					# Zapamiętaj bieżący FBO (może być Qt-internal FBO, nie 0)
					prev_fb = glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING)
					prev_read_fb = glGetIntegerv(GL_READ_FRAMEBUFFER_BINDING)
					prev_draw_buffer = glGetIntegerv(GL_DRAW_BUFFER)
					prev_read_buffer = glGetIntegerv(GL_READ_BUFFER)
					viewport = glGetIntegerv(GL_VIEWPORT)
					vx, vy, vw, vh = map(int, viewport)

					glBindFramebuffer(GL_READ_FRAMEBUFFER, prev_fb)
					glBindFramebuffer(GL_DRAW_FRAMEBUFFER, self._wboit_fbo)
					glBlitFramebuffer(
						vx, vy, vx + vw, vy + vh,
						vx, vy, vx + vw, vy + vh,
						GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT,
						GL_NEAREST
					)

					glBindFramebuffer(GL_FRAMEBUFFER, self._wboit_fbo)

					glDrawBuffer(GL_COLOR_ATTACHMENT0)
					glClearColor(0.0, 0.0, 0.0, 0.0)
					glClear(GL_COLOR_BUFFER_BIT)

					glDrawBuffer(GL_COLOR_ATTACHMENT1)
					glClearColor(1.0, 1.0, 1.0, 1.0)
					glClear(GL_COLOR_BUFFER_BIT)

					# Pass 0: accum (blend: GL_ONE, GL_ONE)
					glDrawBuffer(GL_COLOR_ATTACHMENT0)
					glDepthMask(GL_FALSE)
					glEnable(GL_DEPTH_TEST)
					glDepthFunc(GL_LEQUAL)
					glEnable(GL_BLEND)
					glBlendFunc(GL_ONE, GL_ONE)
					ws.render_transparent_wboit(0, camera_pos=cam_pos, view_dir=view_dir)

					# Pass 1: reveal (blend: GL_ZERO, GL_ONE_MINUS_SRC_COLOR)
					glDrawBuffer(GL_COLOR_ATTACHMENT1)
					glDepthMask(GL_FALSE)
					glEnable(GL_DEPTH_TEST)
					glDepthFunc(GL_LEQUAL)
					glBlendFunc(GL_ZERO, GL_ONE_MINUS_SRC_COLOR)
					ws.render_transparent_wboit(1, camera_pos=cam_pos, view_dir=view_dir)

					# Composite: nałóż WBOIT transparent na główny bufor
					glBindFramebuffer(GL_FRAMEBUFFER, prev_fb)
					glDrawBuffer(prev_draw_buffer)
					glReadBuffer(prev_read_buffer)
					glDepthMask(GL_TRUE)
					glDisable(GL_DEPTH_TEST)
					glEnable(GL_BLEND)
					glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
					glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
					self._composite_wboit()
					glEnable(GL_DEPTH_TEST)
					glDepthFunc(GL_LEQUAL)
					glBindFramebuffer(GL_READ_FRAMEBUFFER, prev_read_fb)
					glBindFramebuffer(GL_DRAW_FRAMEBUFFER, prev_fb)

					glClearColor(
						self._fBgColor.redF(),
						self._fBgColor.greenF(),
						self._fBgColor.blueF(),
						self._fBgColor.alphaF())
		finally:
			glPopMatrix()
			# Upewnij się że stos attribs jest czysty po renderowaniu obiektów
			self._drainGLAttribStack()
			if wboit_reinit and not getattr(self, '_wboit_refresh_pending', False):
				self._wboit_refresh_pending = True
				QTimer.singleShot(0, self._trigger_wboit_refresh)
	
		# //rysujGimbal();
	
		glDisable(GL_LIGHTING)
		glDisable( GL_DEPTH_TEST )
	
		glDisable(GL_BLEND);

	# ---------- WBOIT helpers ----------

	def _trigger_wboit_refresh(self):
		self._wboit_refresh_pending = False
		self.update()

	def _init_wboit_resources(self, w, h):
		"""Tworzy FBO + tekstury dla WBOIT i kompiluje shader composite."""
		from ..shaders import load_and_compile_shader as _lcs
		# Zwolnij stare zasoby (jeśli są)
		if getattr(self, '_wboit_fbo', None) is not None:
			glDeleteFramebuffers(1, [self._wboit_fbo])
			glDeleteTextures(1, [self._wboit_accum_tex])
			glDeleteTextures(1, [self._wboit_reveal_tex])
			glDeleteRenderbuffers(1, [self._wboit_depth_rb])
			self._wboit_fbo = None

		try:
			fbo = glGenFramebuffers(1)
			glBindFramebuffer(GL_FRAMEBUFFER, fbo)

			# Attachment 0: RGBA32F – akumulacja ważonych kolorów
			accum_tex = glGenTextures(1)
			glBindTexture(GL_TEXTURE_2D, accum_tex)
			glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA32F, w, h, 0, GL_RGBA, GL_FLOAT, None)
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
			glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
			                       GL_TEXTURE_2D, accum_tex, 0)

			# Attachment 1: RGBA8 – produkt (1-alpha)
			reveal_tex = glGenTextures(1)
			glBindTexture(GL_TEXTURE_2D, reveal_tex)
			glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
			glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT1,
			                       GL_TEXTURE_2D, reveal_tex, 0)

			# Depth+stencil renderbuffer – musi być GL_DEPTH24_STENCIL8 aby format
			# zgadzał się z Qt FBO (Qt ustawia stencilBufferSize=8), dzięki czemu
			# glBlitFramebuffer dla depth nie generuje GL_INVALID_OPERATION.
			depth_rb = glGenRenderbuffers(1)
			glBindRenderbuffer(GL_RENDERBUFFER, depth_rb)
			glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH24_STENCIL8, w, h)
			glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT,
			                          GL_RENDERBUFFER, depth_rb)

			status = glCheckFramebufferStatus(GL_FRAMEBUFFER)
			if status != GL_FRAMEBUFFER_COMPLETE:
				print(f"WBOIT FBO niekompletny: 0x{status:X}")
				glBindFramebuffer(GL_FRAMEBUFFER, 0)
				glDeleteFramebuffers(1, [fbo])
				glDeleteTextures(1, [accum_tex])
				glDeleteTextures(1, [reveal_tex])
				glDeleteRenderbuffers(1, [depth_rb])
				self._wboit_fbo = None
				return

			self._wboit_fbo        = fbo
			self._wboit_accum_tex  = accum_tex
			self._wboit_reveal_tex = reveal_tex
			self._wboit_depth_rb   = depth_rb
			self._wboit_w          = w
			self._wboit_h          = h
			glBindFramebuffer(GL_FRAMEBUFFER, 0)
			print(f"WBOIT FBO zainicjowany: {w}x{h}")

		except Exception as e:
			print(f"WBOIT FBO błąd inicjalizacji: {e}")
			self._wboit_fbo = None
			return

		# Kompiluj shader composite (tylko raz)
		if getattr(self, '_wboit_composite_prog', None) is None:
			try:
				vs   = _lcs('wboit_composite.vert', GL_VERTEX_SHADER)
				fs   = _lcs('wboit_composite.frag', GL_FRAGMENT_SHADER)
				prog = glCreateProgram()
				glAttachShader(prog, vs)
				glAttachShader(prog, fs)
				glLinkProgram(prog)
				if not glGetProgramiv(prog, GL_LINK_STATUS):
					print(glGetProgramInfoLog(prog))
					glDeleteProgram(prog)
					self._wboit_composite_prog = None
				else:
					glDeleteShader(vs)
					glDeleteShader(fs)
					self._wboit_composite_prog  = prog
					self._wboit_accum_loc  = glGetUniformLocation(prog, 'u_accum')
					self._wboit_reveal_loc = glGetUniformLocation(prog, 'u_reveal')
			except Exception as e:
				print(f"WBOIT composite shader błąd: {e}")
				self._wboit_composite_prog = None

		# Pusty VAO dla fullscreen triangle (gl_VertexID trick)
		if getattr(self, '_wboit_empty_vao', None) is None:
			self._wboit_empty_vao = glGenVertexArrays(1)

	def _composite_wboit(self):
		"""Rysuje fullscreen quad łącząc WBOIT accum+reveal z tłem opaque."""
		if getattr(self, '_wboit_composite_prog', None) is None:
			return

		# Tymczasowo wyzeruj macierze (shader używa gl_VertexID, nie zależy od GL matrix)
		glMatrixMode(GL_PROJECTION)
		glPushMatrix()
		glLoadIdentity()
		glMatrixMode(GL_MODELVIEW)
		glPushMatrix()
		glLoadIdentity()

		glUseProgram(self._wboit_composite_prog)

		glActiveTexture(GL_TEXTURE0)
		glBindTexture(GL_TEXTURE_2D, self._wboit_accum_tex)
		glUniform1i(self._wboit_accum_loc, 0)

		glActiveTexture(GL_TEXTURE1)
		glBindTexture(GL_TEXTURE_2D, self._wboit_reveal_tex)
		glUniform1i(self._wboit_reveal_loc, 1)

		glBindVertexArray(self._wboit_empty_vao)
		glDrawArrays(GL_TRIANGLES, 0, 3)
		glBindVertexArray(0)

		glUseProgram(0)
		glActiveTexture(GL_TEXTURE0)

		# Przywróć macierze
		glMatrixMode(GL_PROJECTION)
		glPopMatrix()
		glMatrixMode(GL_MODELVIEW)
		glPopMatrix()

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
	
		# Skala osi proporcjonalna do rozmiaru sceny
		# przy _defaultViewSize=200 → mnożnik=1.0 (zachowane oryginalne rozmiary)
		axis_scale = self._dCurrentViewSize / self._dDefaultViewSize
		glPushMatrix()
		glScalef(axis_scale, axis_scale, axis_scale)
		self.triad3D( 0.1, 45.0, 0.4, 5.0, True )
		glPopMatrix()
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

	def calculate_ortho_matrix(self, left, right, bottom, top, near, far):
		# Inicjalizacja macierzy 4x4 zerami
		ortho_matrix = np.zeros((4, 4), dtype=np.float32)
		
		# Wypełnianie wartościami zgodnie ze wzorem dla macierzy ortogonalnej
		ortho_matrix[0, 0] = 2.0 / (right - left)
		ortho_matrix[1, 1] = 2.0 / (top - bottom)
		ortho_matrix[2, 2] = -2.0 / (far - near)
		
		ortho_matrix[0, 3] = -(right + left) / (right - left)
		ortho_matrix[1, 3] = -(top + bottom) / (top - bottom)
		ortho_matrix[2, 3] = -(far + near) / (far - near)
		
		ortho_matrix[3, 3] = 1.0
		
		return ortho_matrix

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
			if self._projection == GLViewer.Projection.PERSPECTIVE:
				projection_matrix = self.calculate_frustum_matrix(self._left, self._right, self._bottom, self._top, self._near, self._far)
			else:
				projection_matrix = self.calculate_ortho_matrix(self._left, self._right, self._bottom, self._top, self._near, self._far)


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
