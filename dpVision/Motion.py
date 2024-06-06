from PyQt5.QtGui import *
from PyQt5.QtCore import *
from OpenGL.GL import *
import numpy as np

from .globals import AP
from .transform import Transform
from .object import Object
from .k3RigidToScrew import *

class Motion(Object):
	class FrameVal:
		def __init__(self, miliseconds=0, transformation=Transform()):
			self.msec = miliseconds
			self.transform = transformation

	def __init__(self, seq=[], parent=None):
		super( Motion, self ).__init__( parent )
		self.m_isPlaying = False
		self.m_currentKey = 0
		self.m_animationTimer = QTimer()
		self.m_seqlist = seq # list of FrameVal
		self.setTimer()

	def startPlaying(self):
		self.m_animationTimer.start(self.currentFrame().msec)
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

	def onTimeout(self): # tu inkrenentacja licznika klatek;
		if self.m_isPlaying:
			self.m_currentKey = (self.m_currentKey + 1) % len(self.m_seqlist)
			AP.updateAllViews()
			AP.mainWin.dock["properties"].updateProperties()
			self.m_animationTimer.start(self.currentFrame().msec)

	def renderKids(self):
		self.renderFrame()

	def renderFrame(self): # rysowanie bieżącej klatki
		frame = self.currentFrame()
		
		if self.m_currentKey>0:
			currTrans = frame.transform
			prevTrans = self.m_seqlist[self.m_currentKey-1].transform
			tr = Transform()
			tr.fromNumPy( np.dot(currTrans.toNumPy(), prevTrans.invertedMatrix()) )
			tr.renderScrew()
			#del tr
		
		frame.transform.renderScrew(r=1., g=0., b=1.)

		glPushMatrix()
		frame.transform.renderSelf()
		for obj in self.m_data:
			obj.render()
		glPopMatrix()

	def getGlobalTransformation(self):
		return self.currentFrame().transform.matrix if self.m_parent is None \
			else self.currentFrame().transform.matrix * self.m_parent.getGlobalTransformation()

