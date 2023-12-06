from dpVision.Globals import AP
from dpVision.Transform import Transform
from dpVision.Object import Object
from PyQt5.QtGui import *
from OpenGL.GL import *
import numpy as np

class Motion(Object):
	class FrameVal:
		def __init__(self, miliseconds=0, transformation=Transform()):
			self.msec = miliseconds
			self.transform = transformation

	def __init__(self, parent=None):
		super( Motion, self ).__init__( parent )
		self.m_isPlaying = False
		self.m_currentKey = 0
		self.m_animationTimer = QTimer()
		self.m_seqlist = [] # list of FrameVal
		self.setTimer()

	def startPlaying(self):
		self.m_animationTimer.start(self.m_seqlist[self.m_currentKey].msec)
		self.m_isPlaying = True

	def stopPlaying(self):
		self.m_isPlaying = False
		self.m_animationTimer.stop()

	def isPlaying(self):
		return self.m_isPlaying

	def setKey(self, k):
		if k < 0:
			self.m_currentKey = 0
		elif k >= len(self.m_seqlist):
			self.m_currentKey = len(self.m_seqlist) - 1
		else:
			self.m_currentKey = k

	def increaseKey(self, _loop = False):
		self.m_currentKey = self.m_currentKey + 1
		if _loop:
			self.m_currentKey = self.m_currentKey % len(self.m_seqlist)
		elif self.m_currentKey >= len(self.m_seqlist):
			self.m_currentKey = len(self.m_seqlist) - 1
		return self.m_currentKey

	def currentKey(self):
		return self.m_currentKey

	def size(self):
		return len(self.m_seqlist) # liczba klatek
	
	def currentFrame(self):
		return self.m_seqlist[self.m_currentKey] # bieżąca klatka

	def frame(self, k): # klatka o wskazanym numerze
		if k < 0:
			return self.m_seqlist[0]
		elif k >= len(self.m_seqlist):
			return self.m_seqlist[-1]
		return self.m_seqlist[k]

	def setTimer(self): # wołać tylko w konstruktorze
		self.m_animationTimer.setSingleShot(True)
		self.m_animationTimer.timeout.connect(self.onTimeout)
		#QObject::connect(&m_animationTimer, &QTimer::timeout, [&]() { onTimeout(); });

	def onTimeout(self): # tu inkrenentacja licznika klatek;
		if self.m_isPlaying:
			self.m_currentKey = (self.m_currentKey + 1) % len(self.m_seqlist)
			AP.updateAllViews()
			self.m_animationTimer.start(self.m_seqlist[self.m_currentKey].msec);

	def renderKids(self):
		self.renderFrame()

	def renderFrame(self): # rysowanie bieżącej klatki
		frame = self.m_seqlist[self.m_currentKey]
		
		#for (FrameVal frame : m_seqlist)
		glPushMatrix()
		frame.t.render()

		for obj in self.m_data:
			obj.render()

		# for it in self.m_: m_annotations)
		# {
		# 	it.second->render();
		# }
		glPopMatrix()


