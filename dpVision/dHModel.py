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
		super(DHLink, self).__init__(parent)

	def addChild(self, d):
		if d is None or not isinstance(d, DHJoint):
			print("DHLink: only DHJoint instances can be added as children.")
			return False
		# Link może mieć wiele jointów - brak dodatkowej walidacji
		return super(DHLink, self).addChild(d)

	def to_dict(self, urdf_like=True):
		link_dict = {
			'name': self.label if self.label else ''
		}
		return link_dict if urdf_like else None

class DHModel(Object):
	def __init__(self, parent=None):
		super(DHModel, self).__init__(parent)
		self.convention = "classical" # {"type":"string","enum":["classical","modified"]}
		# self.scheme = "urdf-like" # {"type":"string","enum":["joints-only","urdf-like"]}
		self.angle_unit = "deg" # {"type":"string","enum":["deg","rad"]}
		self.length_unit = "mm" # {"type":"string"},
		# self.version = "1.0" # {"type":"string"}


	def addChild(self, d):
		if d is None or not isinstance(d, DHLink):
			print("DHModel: only DHLink instances can be added as children.")
			return False
		return super(DHModel, self).addChild(d)
	
	def is_multi_root(self):
		return len(self.m_data) > 1
	
	def add_link(self, link, parent_joint=None):
		if link is None:
			print("DHModel: link is None.")
			return False
		
		if isinstance(link, str):
			name = link

			found = self.children_by_label(name, types=DHLink)
			if found:
				print(f"DHModel: link with name '{name}' already exists.")
				return False
			
			link = DHLink()
			link.label = name
		elif not isinstance(link, DHLink):
			print("DHModel: link must be DHLink instance or string name.")
			return False
		
		# Jeśli link już ma parenta, usuń go stamtąd
		if link.parent is not None:
			link.parent.removeChild(link)
		
		# Jeśli podano parent_joint
		if parent_joint is not None:
			# Konwersja string → DHJoint
			if isinstance(parent_joint, str):
				found = self.children_by_label(parent_joint, types=DHJoint)
				if not found:
					print(f"DHModel: parent_joint '{parent_joint}' not found.")
					return False
				parent_joint = found[0]
			elif not isinstance(parent_joint, DHJoint):
				print("DHModel: parent_joint must be DHJoint or string name.")
				return False
			
			# Sprawdź czy parent_joint należy do tego modelu
			if not self.children_by_label(parent_joint.label, types=DHJoint):
				print("DHModel: parent_joint not found in this DHModel.")
				return False
			
			return parent_joint.addChild(link)
		
		# Brak parent_joint → dodaj jako root link
		return super(DHModel, self).addChild(link)

	def add_joint(self, joint, parent_link=None):
		if joint is None:
			print("DHModel: joint is None.")
			return False
		
		if isinstance(joint, str):
			name = joint

			found = self.children_by_label(name, types=DHJoint)
			if found:
				print(f"DHModel: joint with name '{name}' already exists.")
				return False
			
			joint = DHJoint()
			joint.label = name
		elif not isinstance(joint, DHJoint):
			print("DHModel: joint must be DHJoint instance or string name.")
			return False
		
		# Jeśli joint już ma parenta, usuń go stamtąd
		if joint.parent is not None:
			joint.parent.removeChild(joint)
		
		# Jeśli podano parent_link
		if parent_link is not None:
			# Konwersja string → DHLink lub DHJoint
			if isinstance(parent_link, str):
				# Szukaj najpierw DHLink
				found = self.children_by_label(parent_link, types=DHLink)
				if found:
					parent_link = found[0]
				else:
					# Jeśli nie znaleziono DHLink, szukaj DHJoint
					found = self.children_by_label(parent_link, types=DHJoint)
					if found:
						parent_joint = found[0]
						# Sprawdź czy parent_joint już ma dziecko (link)
						existing_links = parent_joint.children_by_type(DHLink)
						if existing_links:
							# Użyj istniejącego linka
							parent_link = existing_links[0]
							print(f"DHModel: using existing link '{parent_link.label}' from joint '{parent_joint.label}'.")
						else:
							# Utwórz nowy pośredni link
							intermediate_link = DHLink()
							intermediate_link.label = f"{parent_joint.label}_to_{joint.label}_link"
							
							if not parent_joint.addChild(intermediate_link):
								print(f"DHModel: failed to add intermediate link to joint '{parent_joint.label}'.")
								return False
							
							parent_link = intermediate_link
							print(f"DHModel: created intermediate link '{intermediate_link.label}' between joints.")
					else:
						print(f"DHModel: parent_link '{parent_link}' not found.")
						return False
			elif isinstance(parent_link, DHJoint):
				# parent_link to DHJoint - sprawdź czy ma już link
				parent_joint = parent_link
				existing_links = parent_joint.children_by_type(DHLink)
				if existing_links:
					# Użyj istniejącego linka
					parent_link = existing_links[0]
					print(f"DHModel: using existing link '{parent_link.label}' from joint '{parent_joint.label}'.")
				else:
					# Utwórz nowy pośredni link
					intermediate_link = DHLink()
					intermediate_link.label = f"link_from_{parent_joint.label}"
					
					if not parent_joint.addChild(intermediate_link):
						print(f"DHModel: failed to add intermediate link to joint '{parent_joint.label}'.")
						return False
					
					parent_link = intermediate_link
					print(f"DHModel: created intermediate link '{intermediate_link.label}' between joints.")
			elif not isinstance(parent_link, DHLink):
				print("DHModel: parent_link must be DHLink, DHJoint or string name.")
				return False
			
			# Sprawdź czy parent_link należy do tego modelu
			if not self.children_by_label(parent_link.label, types=DHLink):
				print("DHModel: parent_link not found in this DHModel.")
				return False
			
			return parent_link.addChild(joint)
		
		# Brak parent_link
		if len(self.m_data) == 0:
			base_link = DHLink()
			base_link.label = "base_link"
			self.add_link( base_link )
			print("DHModel: created default 'base_link' as root link.")
		else:
			base_link = self.m_data[0]
			print(f"DHModel: using existing root link: '{base_link.label}'.")
		return base_link.addChild(joint)
	
	def subtree_to_dict(self):
		joints = []
		links = []

		def traverse(obj):
			if isinstance(obj, DHJoint):
				joint_dict = obj.to_dict(angle_unit=self.angle_unit, urdf_like=True)
				joints.append(joint_dict)
			elif isinstance(obj, DHLink):
				link_dict = obj.to_dict(urdf_like=True)
				if link_dict:
					links.append(link_dict)
			
			for child in obj.children():
				traverse(child)

		for child in self.children():
			traverse(child)
		
		result = {
			'meta' : {
				'angle_unit': self.angle_unit,
				'length_unit': self.length_unit,
				'convention': self.convention,
				'scheme': 'urdf-like',
				'version': '1.0'
			}
		}

		if len(links):
			result['links'] = links

		if len(joints):
			result['joints'] = joints

		return result
