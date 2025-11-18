# -*- coding: utf-8 -*-
"""
Created on Mon Nov 27 10:05:30 2023

@author: pojdulos
"""

from .baseObject import BaseObject
from .object import Object
from PyQt5.QtGui import *
from OpenGL.GL import *
import numpy as np
from .shaders import create_program

from .dHJoint import DHJoint

class DHLink(Object):
	def __init__(self, parent=None):
		super( DHModel, self ).__init__( parent )
		

	def addChild(self, d):
		if d is None or not isinstance(d, DHJoint):
			print("DHLink: only DHJoint instances can be added as children.")
			return False
		return super( DHModel, self ).addChild( d )
	
	


class DHModel(Object):
	def __init__(self, parent=None):
		super( DHModel, self ).__init__( parent )

	def addChild(self, d):
		if d is None or not isinstance(d, DHLink):
			print("DHModel: only DHLink instances can be added as children.")
			return False
		return super( DHModel, self ).addChild( d )
	
	def is_moolti_root(self):
		return len(self.m_data) > 1
	
	def add_link(self, link, parent_joint=None):
		if link is None:
			print("DHModel: link is None.")
			return False
		
		if isinstance(link, str):
			name = link

			found = self.children_by_label(name, types=(DHLink,))
			if found:
				print(f"DHModel: link with name '{name}' already exists.")
				return False
			
			link = DHLink()
			link.label = name
		elif not isinstance(link, DHLink):
			print("DHModel: only DHLink instances can be added as links.")
			return False
			
		if parent_joint is not None:
			if isinstance(parent_joint, DHJoint):
				found = self.children_by_label(parent_joint.label, types=(DHJoint,))
				if not found:
					print("DHModel: parent_joint not found in this DHModel.")
					return False
				return parent_joint.addChild( link )
			elif isinstance(parent_joint, str):
				found = self.children_by_label(parent_joint, types=(DHJoint,))
				if not found:
					print(f"DHModel: parent_joint with name '{parent_joint}' not found.")
					return False
				parent_joint = found[0]
				return parent_joint.addChild( link )
					
		return super( DHModel, self ).addChild( link )