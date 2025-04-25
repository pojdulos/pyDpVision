
from .. import Parser, AP, PointCloud, NDimCloud

import numpy as np
import os
from PyQt5.QtGui import *
from math import *
import struct
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import csv
import pandas as pd

def is_probably_header(row):
    def is_number(s):
        try:
            float(s)
            return True
        except ValueError:
            return False
    return not any(is_number(cell.strip('"')) for cell in row)

def read_csv_with_optional_header(path, sep=';'):
    # najpierw wczytujemy tylko pierwszy wiersz
    with open(path, encoding='utf-8') as f:
        first_line = f.readline()
        first_row = [cell.strip().strip('"') for cell in first_line.strip().split(sep)]

    if is_probably_header(first_row):
        # plik zawiera nagłówki
        df = pd.read_csv(path, sep=sep, quotechar='"')
        header = df.columns.tolist()
    else:
        # brak nagłówków – generujemy własne
        df = pd.read_csv(path, sep=sep, header=None, quotechar='"')
        header = None

    return header, df.values


class ParserCSV(Parser):
	updateProgress = pyqtSignal()

	descr = 'CSV files'
	load_exts = ['.csv']
	#save_exts = ['.stl']
	cnt = 0

	def __init__(self):
		super( ParserCSV, self ).__init__()
		self.solids = []
		self.path = ''

	@staticmethod	
	def load( path ):
		headers, rows = read_csv_with_optional_header(path)
		print(headers,rows)
		vertices = np.array(rows, dtype=np.float32)
		# if vertices.shape[1] in (1,2,3):
		# 	if vertices.shape[1] < 3:
		# 		vertices = np.pad(vertices, ((0, 0), (0, 3 - vertices.shape[1])), mode='constant')

		# 	cld = PointCloud()
		# 	cld.m_vertices = vertices
		# 	return cld
		
		if headers is not None and len(headers):
			cld = NDimCloud(headers=headers)
		else:
			cld = NDimCloud(dims=len(rows[0]))
		cld.m_vertices = vertices

		cld.projectTo3D()
		
		print("po projekcji")
		
		return cld

	@staticmethod	
	def save( obj, path ):
		return False
	
	@staticmethod	
	def inPlugin():
		return False
		
ParserCSV.regParser()