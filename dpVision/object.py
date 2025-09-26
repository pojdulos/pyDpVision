# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 13:15:53 2023

@author: darek
"""

from .baseObject import BaseObject

class Object(BaseObject):
	def __init__(self, parent=None):
		super( Object, self ).__init__( parent )
		self.m_data = []
		self._dirty = True
		self._cached_bb = None
		self._cached_midpoint = None


	def children(self):
		return self.m_data
	
	def children_by_type(self, types):
		# Jeśli to pojedynczy typ (np. GridData64)
		if isinstance(types, type):
			types = (types,)
		# Jeśli to list/set/numpy array itp. → rzutuj na tuple
		elif not isinstance(types, tuple):
			try:
				types = tuple(types)
			except TypeError:
				# np. jak poda ktoś int albo obiekt nieiterowalny
				types = (types,)

		return [kid for kid in self.m_data if isinstance(kid, types)]


	def addChild(self, d):
		if d is None or not issubclass(type(d), BaseObject):
			return False

		if d.parent is not None:
			d.parent.removeChild(d)
		d.parent = self
		self.m_data.append( d )

		return True

	def removeChild(self, child=None):
		if child is None and len(self.m_data):
			self.m_data.remove(self.m_data[0])
		elif child in self.m_data:
			self.m_data.remove(child)

	def renderKids(self):
		for child in self.m_data:
			child.render()
			
	def getBB(self):
		return False, None, None
		if not self._dirty and self._cached_bb is not None:
			return self._cached_bb

		_b = False
		_min, _max = None, None

		for kid in self.m_data:
			kid_b, kid_min, kid_max = kid.getBB()
			if kid_b:
				if _min is None:
					_min, _max = kid_min, kid_max
				else:
					_min = [min(m1, m2) for m1, m2 in zip(_min, kid_min)]
					_max = [max(m1, m2) for m1, m2 in zip(_max, kid_max)]
				_b = True

		self._cached_bb = (_b, _min, _max)
		self._dirty = False
		return self._cached_bb

	def getMidpoint(self):
		if not self._dirty and self._cached_midpoint is not None:
			return self._cached_midpoint

		_b, _min, _max = self.getBB()
		if not _b:
			return [0.0,0.0,0.0]

		ctr = [(m1 + m2) / 2 for m1, m2 in zip(_min, _max)]
		self._cached_midpoint = ctr
		return ctr
