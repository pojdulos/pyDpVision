# -*- coding: utf-8 -*-
"""Flow layout helpers for dock panels with unpredictable aspect ratios."""

from PyQt5.QtCore import QPoint, QRect, QSize, Qt
from PyQt5.QtWidgets import QLayout, QSizePolicy, QStyle


class FlowLayout(QLayout):
	"""Lay out child items left-to-right and wrap them to the next row as needed."""

	def __init__(self, parent=None, margin=0, spacing=-1):
		"""Initialize one wrapping layout with optional margins and spacing."""
		super().__init__(parent)
		self._items = []
		self.setContentsMargins(margin, margin, margin, margin)
		self.setSpacing(spacing)

	def __del__(self):
		"""Delete all layout items owned by this layout."""
		while self.count():
			self.takeAt(0)

	def addItem(self, item):
		"""Add one layout item to the wrapping flow."""
		self._items.append(item)

	def count(self):
		"""Return the number of child items."""
		return len(self._items)

	def itemAt(self, index):
		"""Return the child item at `index`, if it exists."""
		if 0 <= index < len(self._items):
			return self._items[index]
		return None

	def takeAt(self, index):
		"""Remove and return the child item at `index`, if it exists."""
		if 0 <= index < len(self._items):
			return self._items.pop(index)
		return None

	def expandingDirections(self):
		"""Report that the layout itself does not require expansion."""
		return Qt.Orientations()

	def hasHeightForWidth(self):
		"""Enable height recalculation based on the available width."""
		return True

	def heightForWidth(self, width):
		"""Return the wrapped height required for the given width."""
		return self._do_layout(QRect(0, 0, width, 0), True)

	def setGeometry(self, rect):
		"""Position child items within `rect` using wrapping rows."""
		super().setGeometry(rect)
		self._do_layout(rect, False)

	def sizeHint(self):
		"""Return the preferred size of the wrapping content."""
		return self.minimumSize()

	def minimumSize(self):
		"""Return the minimum size needed by the child widgets and margins."""
		size = QSize()
		for item in self._items:
			size = size.expandedTo(item.minimumSize())

		left, top, right, bottom = self.getContentsMargins()
		size += QSize(left + right, top + bottom)
		return size

	def _do_layout(self, rect, test_only):
		"""Lay out child items row by row and return the resulting height."""
		left, top, right, bottom = self.getContentsMargins()
		effective_rect = rect.adjusted(left, top, -right, -bottom)
		x = effective_rect.x()
		y = effective_rect.y()
		line_height = 0

		for item in self._items:
			widget = item.widget()
			style = widget.style() if widget is not None else None
			space_x = self.spacing()
			space_y = self.spacing()
			if style is not None and space_x < 0:
				space_x = style.layoutSpacing(
					QSizePolicy.PushButton,
					QSizePolicy.PushButton,
					Qt.Horizontal,
				)
			if style is not None and space_y < 0:
				space_y = style.layoutSpacing(
					QSizePolicy.PushButton,
					QSizePolicy.PushButton,
					Qt.Vertical,
				)
			if space_x < 0:
				space_x = 0
			if space_y < 0:
				space_y = 0

			next_x = x + item.sizeHint().width() + space_x
			if line_height > 0 and next_x - space_x > effective_rect.right() + 1:
				x = effective_rect.x()
				y = y + line_height + space_y
				next_x = x + item.sizeHint().width() + space_x
				line_height = 0

			if not test_only:
				item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

			x = next_x
			line_height = max(line_height, item.sizeHint().height())

		return y + line_height - rect.y() + bottom
