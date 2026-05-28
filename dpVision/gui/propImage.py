# -*- coding: utf-8 -*-

from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QSizePolicy

from .. import AP
from .propWidget import PropWidget
from .propBaseObject import PropBaseObject
import weakref


class PropImage(PropWidget):
    def __init__(self, _obj, parent=None):
        super(PropImage, self).__init__(parent)
        AP.loadUi('propImage.ui', self)
        self.obj_ref = weakref.ref(_obj)

    @staticmethod
    def create(m, parent=0):
        return PropWidget.build([PropBaseObject(m), PropImage(m)], parent)

    def updateProperties(self):
        obj = self.obj_ref()
        if obj is None:
            return

        w = getattr(obj, 'width', 0)
        h = getattr(obj, 'height', 0)
        self.infoLabel.setText(f"{w} \u00d7 {h} px")

        pixmap = QPixmap.fromImage(obj)
        if not pixmap.isNull():
            thumb = pixmap.scaled(
                self.thumbnailLabel.width(),
                self.thumbnailLabel.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.thumbnailLabel.setPixmap(thumb)
        else:
            self.thumbnailLabel.setText("brak podglądu")

    @pyqtSlot()
    def on_show_window_button(self):
        obj = self.obj_ref()
        if obj is None:
            return
        from .mdiChild import MdiChild
        MdiChild.create_image_viewer(obj, AP.mainWin.mdiArea)

    @pyqtSlot()
    def on_save_png_button(self):
        from PyQt5.QtWidgets import QFileDialog
        obj = self.obj_ref()
        if obj is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Zapisz obraz", "", "PNG (*.png)")
        if path:
            if not path.lower().endswith('.png'):
                path += '.png'
            obj.save(path)
