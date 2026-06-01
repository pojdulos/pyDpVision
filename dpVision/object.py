# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 13:15:53 2023

@author: darek
"""

from .baseObject import BaseObject


class Object(BaseObject):
	def __init__(self, parent=None):
		super(Object, self).__init__(parent)
		self.m_data = []
		self._dirty = True
		self._cached_bb = None
		self._cached_midpoint = None

	def children(self):
		return self.m_data
	
	def types_to_tuple(self, types):
		# Jeżeli to pojedynczy typ (np. GridData64)
		if isinstance(types, type):
			types = (types,)
		# Jeżeli to list/set/numpy array itp. -> rzutuj na tuple
		elif not isinstance(types, tuple):
			try:
				types = tuple(types)
			except TypeError:
				# np. jak poda ktoś int albo obiekt nieiterowalny
				types = (types,)

		return types
	
	def children_by_type(self, types):
		types = self.types_to_tuple(types)
		return [kid for kid in self.m_data if isinstance(kid, types)]

	def children_by_label(self, label, case_sensitive=True, types=None):
		label = label.lower() if not case_sensitive else label
		results = []
		for kid in self.m_data:
			kid_label = kid.label.lower() if not case_sensitive else kid.label
			if kid_label == label:
				results.append(kid)

			if isinstance(kid, Object):
				results.extend(kid.children_by_label(label, case_sensitive, types))

		if types:
			types = self.types_to_tuple(types)
			results = [kid for kid in results if isinstance(kid, types)]

		return results

	def addChild(self, d):
		if d is None or not issubclass(type(d), BaseObject):
			return False

		if d.parent is not None:
			d.parent.removeChild(d)
		d.parent = self
		self.m_data.append(d)
		self.invalidate_bb()
		return True

	def removeChild(self, child=None):
		if child is None and len(self.m_data):
			self.m_data.remove(self.m_data[0])
			self.invalidate_bb()
		elif child in self.m_data:
			self.m_data.remove(child)
			self.invalidate_bb()

	def renderKids(self):
		for child in self.m_data:
			child.render()
			
	def invalidate_bb(self):
		"""Unieważnia cache BB tego węzła i propaguje do rodzica."""
		self._dirty = True
		self._cached_bb = None
		self._cached_midpoint = None
		super().invalidate_bb()

	@staticmethod
	def _merge_bb(current, other):
		if other is None:
			return current

		other_b, other_min, other_max = other
		if not other_b or other_min is None or other_max is None:
			return current

		if current is None:
			return True, list(other_min), list(other_max)

		_, current_min, current_max = current
		merged_min = [min(m1, m2) for m1, m2 in zip(current_min, other_min)]
		merged_max = [max(m1, m2) for m1, m2 in zip(current_max, other_max)]
		return True, merged_min, merged_max

	def getLocalBB(self):
		return False, None, None

	def getHierarchyBB(self):
		if not self._dirty and self._cached_bb is not None:
			return self._cached_bb

		bb = self._merge_bb(None, self.getLocalBB())

		for kid in self.m_data:
			bb = self._merge_bb(bb, kid.getHierarchyBBInParentSpace())

		if bb is None:
			bb = (False, None, None)

		self._cached_bb = bb
		self._dirty = False
		return self._cached_bb

	# def getBB(self):
	# 	return self.getHierarchyBB()

	def getMidpoint(self):
		if not self._dirty and self._cached_midpoint is not None:
			return self._cached_midpoint

		_b, _min, _max = self.getHierarchyBB()
		if not _b:
			return [0.0, 0.0, 0.0]

		ctr = [(m1 + m2) / 2 for m1, m2 in zip(_min, _max)]
		self._cached_midpoint = ctr
		return ctr
