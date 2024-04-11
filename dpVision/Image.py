from PyQt5.QtGui import QImage
from dpVision.Object import Object
from OpenGL.GL import *
from OpenGL.GLUT import *
import numpy as np

class Image(Object, QImage):
    def __init__(self, parent=None, path=None, image=None):
        Object.__init__( self, parent )
        QImage.__init__(self)
        self.texture_id = None
        if path is not None:
            self.load(path)
        elif image is not None:
            self.swap(image.copy())
            self.imageRGBA = self.convertToFormat(QImage.Format_RGBA8888).mirrored()

            self.texture_id = glGenTextures(1)

            self.width = self.imageRGBA.width()
            self.height = self.imageRGBA.height()

            ptr = self.imageRGBA.constBits()
            ptr.setsize(self.height * self.width * 4)
            self.image_data = np.frombuffer(ptr, np.uint8).reshape((self.height, self.width, 4))  # konwersja na tablicę numpy
        else:
            self.imageRGBA = self.convertToFormat(QImage.Format_RGBA8888).mirrored()
            self.width = self.imageRGBA.width()
            self.height = self.imageRGBA.height()

    def load(self, path):
        QImage.load(self, path)
        
        self.imageRGBA = self.convertToFormat(QImage.Format_RGBA8888).mirrored()

        self.texture_id = glGenTextures(1)

        self.width = self.imageRGBA.width()
        self.height = self.imageRGBA.height()
        self.ratio = float(self.height) / self.width

        ptr = self.imageRGBA.constBits()
        ptr.setsize(self.height * self.width * 4)
        self.image_data = np.frombuffer(ptr, np.uint8).reshape((self.height, self.width, 4))  # konwersja na tablicę numpy

    def save(self, path):
        super().save(path)

    def getCopy(self):
        return Image(self)

    # def copy(self, x, y, w, h):
    #     return Image(super().copy(x, y, w, h))

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
        if self.m_showSelf and self.texture_id is not None:
            glPushMatrix()
            glPushAttrib(GL_ALL_ATTRIB_BITS)

            glEnable(GL_TEXTURE_2D)
            glEnable(GL_COLOR_MATERIAL)

            glBindTexture(GL_TEXTURE_2D, self.texture_id)

            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.width, self.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, self.image_data)

            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

            glBegin(GL_QUADS)
            glTexCoord2f(0, 0); glVertex2f(-1.0, -self.ratio)
            glTexCoord2f(1, 0); glVertex2f( 1.0, -self.ratio)
            glTexCoord2f(1, 1); glVertex2f( 1.0,  self.ratio)
            glTexCoord2f(0, 1); glVertex2f(-1.0,  self.ratio)
            glEnd()

            glDisable(GL_TEXTURE_2D)
            glDisable(GL_COLOR_MATERIAL)

            glPopAttrib()
            glPopMatrix()

    def infoRow(self):
        pass  # Implement this method as needed
