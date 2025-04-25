
from .. import Parser, AP, NDimCloud

import numpy as np
import os
from PyQt5.QtGui import *
from math import *
import struct
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import csv

def is_probably_header(row):
    def is_number(s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    return not any(is_number(cell) for cell in row)


def test_header(row):
	headers, rows = [], []

	print(row)
	cells = row[0].split(";")
	print(cells)

	return headers, rows


def read_csv_with_optional_header(path):
	header = None
	rows = []

	with open(path, newline='') as csvfile:
		reader = csv.reader(csvfile, delimiter=';')

		try:
			first_row = next(reader)
		except StopIteration:
			return None, []  # pusty plik

        # Prosty sposób na sprawdzenie, czy to nagłówek: wszystkie pola to teksty
		# if all(cell.isalpha() for cell in first_row):
		# 	header = first_row
		# else:
		# 	rows.append(first_row)  # nie był to nagłówek – zachowujemy jako dane

		# test_header(first_row)
		if is_probably_header(first_row):
			header = first_row
		else:
			rows.append(first_row)


        # pozostałe wiersze
		for row in reader:
			rows.append(row)

	return header, rows

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
        
		print("wczytane")

		if headers is not None and len(headers):
			cld = NDimCloud(headers=headers)
		else:
			cld = NDimCloud(dims=len(rows[0]))
		cld.m_vertices = np.array(rows, dtype=np.float32)

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