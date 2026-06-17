# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QLabel, QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap


class ImageViewer(QWidget):
    """Simple image viewer with scroll and mouse-wheel zoom."""

    def __init__(self, image_obj=None, parent=None):
        super().__init__(parent)
        self._zoom = 1.0
        self._pixmap = QPixmap()

        self._label = QLabel()
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self._label.setMinimumSize(1, 1)

        self._scroll = QScrollArea()
        self._scroll.setWidget(self._label)
        self._scroll.setWidgetResizable(False)
        self._scroll.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._scroll)

        if image_obj is not None:
            self.setImage(image_obj)

    def setImage(self, image_obj):
        """Accept QImage or any subclass (e.g. Image)."""
        self._pixmap = QPixmap.fromImage(image_obj)
        self._zoom = 1.0
        self._updateDisplay()

    def _updateDisplay(self):
        if self._pixmap.isNull():
            return
        w = max(1, int(self._pixmap.width() * self._zoom))
        h = max(1, int(self._pixmap.height() * self._zoom))
        scaled = self._pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._label.setPixmap(scaled)
        self._label.resize(scaled.size())

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 1.0 / 1.15
        self._zoom = max(0.05, min(self._zoom * factor, 16.0))
        self._updateDisplay()
