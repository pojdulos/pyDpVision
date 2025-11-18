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
			name = link # we should first check if this name already exists in structure
			
			link = DHLink()
			link.label = name
		elif not isinstance(link, DHLink):
			print("DHModel: only DHLink instances can be added as links.")
			return False
			
		if parent_joint is not None:
			if isinstance(parent_joint, DHJoint):
				if parent_joint.parent is None or parent_joint.parent not in self.m_data:
					# it should works with infinite recursion...
					print("DHModel: parent_joint does not belong to this DHModel.")
					return False
				else:
					parent_joint.addChild( link )

			elif isinstance(parent_joint, str):
				# find joint by name
				found = False
				for link_candidate in self.m_data:
					for joint_candidate in link_candidate.children():
						if joint_candidate.name == parent_joint:
							parent_joint = joint_candidate
							found = True
							break
					if found:
						break
				if not found:
					print(f"DHModel: parent_joint with name '{parent_joint}' not found.")
					return False
			else:
				print("DHModel: parent_joint should be DHJoint instance or its name (string).")
				return False
			

			parent_link = parent_joint.parent
			if parent_link is None or not isinstance(parent_link, DHLink):
				print("DHModel: parent_joint does not belong to a valid DHLink.")
				return False
			if parent_link not in self.m_data:
				print("DHModel: parent_link is not part of this DHModel.")
				return False
			parent_link.addChild( link )
			return True	
		return super( DHModel, self ).addChild( link )