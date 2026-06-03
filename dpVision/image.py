from PyQt5.QtGui import QImage
from OpenGL.GL import *
from OpenGL.GLUT import *
import numpy as np

from .object import Object


class Image(Object, QImage):
    """Represent one 2D raster image rendered in the 3D scene as a textured quad."""

    def __init__(self, parent=None, path=None, image=None):
        """Create one image object and defer OpenGL texture allocation until rendering time."""
        Object.__init__(self, parent)
        QImage.__init__(self)
        self.texture_id = None
        self.imageRGBA = self.convertToFormat(QImage.Format_RGBA8888).mirrored()
        self.width = self.imageRGBA.width()
        self.height = self.imageRGBA.height()
        self.ratio = float(self.height) / self.width if self.width else 1.0
        self.w2 = self.width / 200.0
        self.h2 = self.height / 200.0
        self.image_data = None

        if path is not None:
            self.load(path)
        elif image is not None:
            self.setImage(image)

    def load(self, path):
        """Load one raster file and rebuild CPU-side image buffers without touching OpenGL state."""
        QImage.load(self, path)
        self._refresh_image_buffers()

    def setImage(self, image):
        """Replace the underlying QImage data and rebuild CPU-side buffers for later texture upload."""
        self.swap(image.copy())
        self._refresh_image_buffers()

    def _refresh_image_buffers(self):
        """Recompute converted image data and geometry cached for 2D rendering."""
        self.imageRGBA = self.convertToFormat(QImage.Format_RGBA8888).mirrored()
        self.width = self.imageRGBA.width()
        self.height = self.imageRGBA.height()
        self.ratio = float(self.height) / self.width if self.width else 1.0
        self.w2 = self.width / 200.0
        self.h2 = self.height / 200.0

        if self.width <= 0 or self.height <= 0:
            self.image_data = None
            return

        ptr = self.imageRGBA.constBits()
        ptr.setsize(self.height * self.width * 4)
        self.image_data = np.frombuffer(ptr, np.uint8).reshape((self.height, self.width, 4))

    def save(self, path):
        """Save the image using the inherited Qt implementation."""
        super().save(path)

    def getCopy(self):
        """Return one detached copy of this image scene object."""
        return Image(self)

    # def copy(self, x, y, w, h):
    #     return Image(super().copy(x, y, w, h))

    def toQImage(self):
        """Return the image as a plain Qt image object."""
        return self

    def sizeInBytes(self):
        """Return the approximate image size as reported by Qt."""
        return super().sizeInBytes()

    def fill(self, color):
        """Fill the image with one solid color."""
        super().fill(color)
        self._refresh_image_buffers()

    def setColor(self, i, argb):
        """Forward indexed color changes to Qt."""
        super().setColor(i, argb)

    def pixel(self, x, y):
        """Return the pixel value at the given coordinates."""
        return super().pixel(x, y)

    def setPixel(self, x, y, pixel):
        """Set the pixel value at the given coordinates and refresh CPU-side buffers."""
        super().setPixel(x, y, pixel)
        self._refresh_image_buffers()

    def format(self):
        """Return the underlying Qt image format."""
        return super().format()

    def renderSelf(self):
        """Upload the image lazily as an OpenGL texture and render one textured quad."""
        if self.hidden or self.image_data is None:
            return

        if self.texture_id is None:
            self.texture_id = glGenTextures(1)

        glPushMatrix()
        glPushAttrib(GL_ALL_ATTRIB_BITS)

        glEnable(GL_TEXTURE_2D)
        glEnable(GL_COLOR_MATERIAL)

        glBindTexture(GL_TEXTURE_2D, self.texture_id)

        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.width, self.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, self.image_data)

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        glBegin(GL_QUADS)
        glTexCoord2f(0, 0)
        glVertex2f(-self.w2, -self.h2)
        glTexCoord2f(1, 0)
        glVertex2f(self.w2, -self.h2)
        glTexCoord2f(1, 1)
        glVertex2f(self.w2, self.h2)
        glTexCoord2f(0, 1)
        glVertex2f(-self.w2, self.h2)
        glEnd()

        glDisable(GL_TEXTURE_2D)
        glDisable(GL_COLOR_MATERIAL)

        glPopAttrib()
        glPopMatrix()

    def infoRow(self):
        """Placeholder kept for compatibility with other scene object panels."""
        pass
