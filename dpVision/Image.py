from PyQt5.QtGui import QImage
from PyQt5.QtCore import QString
from dpVision.Object import Object

class Image(Object, QImage):
    def __init__(self, i=None, path=None, format=None):
        Object.__init__(self)
        if i is not None:
            QImage.__init__(self, i)
        elif path is not None:
            QImage.__init__(self, path, format)
        else:
            QImage.__init__(self)

    @staticmethod
    def load(path):
        return Image(path)

    def save(self, path):
        super().save(path)

    def getCopy(self):
        return Image(self)

    def copy(self, x, y, w, h):
        return Image(super().copy(x, y, w, h))

    def toQImage(self):
        return self

    def sizeInBytes(self):
        return super().sizeInBytes()

    def fill(self, color):
        super().fill(color)

    def setColor(self, i, argb):
        super().setColor(i, argb)

    def pixel(self, x, y):
        return super().pixel(x, y)

    def setPixel(self, x, y, pixel):
        super().setPixel(x, y, pixel)

    def format(self):
        return super().format()

    def renderSelf(self):
        pass  # Implement this method as needed

    def infoRow(self):
        pass  # Implement this method as needed
