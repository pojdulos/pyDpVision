# -*- coding: utf-8 -*-
"""
Created on Thu Nov 23 20:18:03 2023

@author: darek
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout
from enum import Enum

from .gLViewer import GLViewer
from .imageViewer import ImageViewer


class ImageViewerChild(QWidget):
    """MDI child widget that wraps an ImageViewer.
    m_widget points back to the source Image object so that the properties
    dock shows PropImage when this sub-window is activated."""

    def __init__(self, image_obj, parent=None):
        super().__init__(parent)
        self.m_widget = image_obj  # keeps properties dock in sync

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._viewer = ImageViewer(image_obj, self)
        layout.addWidget(self._viewer)


class MdiChild(QWidget):
    class Type(Enum):
        GL = 1
        Pic = 2

    class Show(Enum):
        Minimized = 0
        Normal = 1
        Maximized = 2

    def __init__(self,win,parent):
        super(MdiChild,self).__init__(parent)
        mdiChildLayout = QVBoxLayout(self)
        #mdiChildLayout.setMargin(0)
        mdiChildLayout.setSpacing(0)
        mdiChildLayout.setObjectName("mdiChildLayout")
        mdiChildLayout.setContentsMargins(0, 0, 0, 0);
        
#    	if (m_type == Type::GL)
#    	{
        self.m_widget = GLViewer(win,self)
#    	}
#    	else if (m_type == Type::Pic)
#    	{
#    		m_widget = new PicViewer(this);
#    	}
    
    	
        mdiChildLayout.addWidget( self.m_widget )
        
#    def create(self, t, mdiArea, show ):
    
    @staticmethod
    def create( win, mdiArea, show = Show.Normal ):
        child = MdiChild(win, mdiArea)

        child.setMinimumSize(400, 300)

        subWindow = mdiArea.addSubWindow( child )

# 	if (t==Type::Pic) subWindow->setWindowTitle("Image viewer");
# 	else if (t == Type::GL) subWindow->setWindowTitle("Workspace viewer");
        
        subWindow.setWindowTitle("Workspace viewer")

        match show:
            case MdiChild.Show.Minimized: 
                subWindow.showMinimized()
            case MdiChild.Show.Maximized: 
                subWindow.showMaximized()
            case MdiChild.Show.Normal:
                subWindow.showNormal()

        subWindow.update()

        return subWindow

    @staticmethod
    def create_image_viewer(image_obj, mdiArea, show=None):
        """Open a flat image viewer sub-window for *image_obj* (an Image instance)."""
        if show is None:
            show = MdiChild.Show.Normal

        child = ImageViewerChild(image_obj, mdiArea)
        child.setMinimumSize(400, 300)

        subWindow = mdiArea.addSubWindow(child)
        label = getattr(image_obj, 'label', 'Image')
        subWindow.setWindowTitle(f"Image: {label}")

        match show:
            case MdiChild.Show.Minimized:
                subWindow.showMinimized()
            case MdiChild.Show.Maximized:
                subWindow.showMaximized()
            case MdiChild.Show.Normal:
                subWindow.showNormal()

        subWindow.update()
        return subWindow
