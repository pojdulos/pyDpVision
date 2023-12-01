# -*- coding: utf-8 -*-
"""
Created on Thu Nov 23 20:18:03 2023

@author: darek
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout
from .GLViewer import GLViewer
from enum import Enum

# class syntax


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

        