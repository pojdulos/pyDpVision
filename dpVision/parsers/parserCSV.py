
from .. import Parser, AP, BaseObject, PointCloud, NDimCloud

import numpy as np
import os
from PyQt5.QtGui import *
from math import *
import struct
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import csv
import pandas as pd


from PyQt5.QtCore import QObject, QThread, pyqtSignal
import pandas as pd

class CSVLoaderWorker(QObject):
	progressChanged = pyqtSignal(int)	  # sygnał do aktualizacji progress bara
	loadingFinished = pyqtSignal(pd.DataFrame)  # sygnał, kiedy wszystko wczytane
	errorOccurred = pyqtSignal(str)

	def __init__(self, path, chunksize=10000, separator=';'):
		super().__init__()
		self.path = path
		self.chunksize = chunksize
		self.separator = separator
		self._is_running = True

	def stop(self):
		self._is_running = False

	def load_csv(self):
		def is_probably_header(first_row):
			def is_number(s):
				try:
					float(s)
					return True
				except ValueError:
					return False
			# jeśli większość pól NIE jest liczbami, uznajemy za nagłówek
			return not all(is_number(cell.strip('"')) for cell in first_row)

		def check_first_line(path, separator=';'):
			with open(path, encoding='utf-8') as f:
				first_line = f.readline()
				first_row = [cell.strip().strip('"') for cell in first_line.strip().split(separator)]
			return is_probably_header(first_row)

		try:
			total_rows = sum(1 for _ in open(self.path, encoding='utf-8'))  # liczba linii
			loaded_rows = 0
			df_list = []

			if check_first_line(self.path, self.separator):
				# mamy nagłówki
				df = pd.read_csv(self.path, delimiter=self.separator, chunksize=self.chunksize)
			else:
				# nie ma nagłówków
				df = pd.read_csv(self.path, delimiter=self.separator, header=None, chunksize=self.chunksize)

			for chunk in df: #pd.read_csv(self.path, header=None, delimiter=self.separator, chunksize=self.chunksize):
				if not self._is_running:
					break  # zatrzymaj jeśli trzeba
				df_list.append(chunk)
				loaded_rows += len(chunk)
				progress = int(loaded_rows / total_rows * 100)
				self.progressChanged.emit(progress)

			if self._is_running:
				final_df = pd.concat(df_list, ignore_index=True)
				self.loadingFinished.emit(final_df)
		except Exception as e:
			self.errorOccurred.emit(str(e))


class ParserCSV(Parser):
	loadingFinished = pyqtSignal(BaseObject) #pd.DataFrame)  # sygnał, kiedy wszystko wczytane
	errorOccurred = pyqtSignal() #str)

	descr = 'CSV files'
	load_exts = ['.csv']
	#save_exts = ['.csv']

	def __init__(self, path):
		super( ParserCSV, self ).__init__()
		self.path = path
		self._thread = QThread()
		self._worker = CSVLoaderWorker(path)

	def dataframe_to_object(self, dataframe):
		headers = dataframe.columns.tolist()
		rows = dataframe.values.tolist()
		
		vertices = np.array(rows, dtype=np.float32)

		if vertices.shape[1] in (1,2,3):
			if vertices.shape[1] < 3:
				vertices = np.pad(vertices, ((0, 0), (0, 3 - vertices.shape[1])), mode='constant')

			cld = PointCloud()
			cld.m_vertices = vertices
			return cld
		
		if headers is not None and len(headers):
			cld = NDimCloud(headers=headers)
		else:
			cld = NDimCloud(dims=len(rows[0]))
		cld.m_vertices = vertices

		cld.projectTo3D()
		return cld

	def on_loading_finished(self, dataframe):
		self._thread.quit()
		self._thread.wait()
		self._worker.deleteLater()
		self._thread.deleteLater()

		print("Dane załadowane!", dataframe.shape)

		print(f"pd.dataframe.columns: {dataframe.columns}, pd.dataframe.values: {dataframe.values}")
		obj = self.dataframe_to_object(dataframe)
		self.loadingFinished.emit(obj)

	def on_loading_error(self, error_message):
		self._thread.quit()
		self._thread.wait()
		self._worker.deleteLater()
		self._thread.deleteLater()

		print("Błąd podczas wczytywania:", error_message)
		self.errorOccurred.emit()

	def on_stop_loading(self):
		self._worker.stop()

		self._thread.quit()
		self._thread.wait()
		self._worker.deleteLater()
		self._thread.deleteLater()
		self.deleteLater()
		print("Przerwano wczytywanie!")


	def load_async(self, progressBar=None):
		self._worker.moveToThread(self._thread)
		self._thread.started.connect(self._worker.load_csv)
			
		if not progressBar is None:
			self._worker.progressChanged.connect(progressBar.setValue)
		
		self._worker.loadingFinished.connect(self.on_loading_finished)
		self._worker.errorOccurred.connect(self.on_loading_error)

		self._thread.start()


	@staticmethod	
	def load( path ):
		def read_csv_with_optional_header(path, sep=';'):
			def is_probably_header(row):
				def is_number(s):
					try:
						float(s)
						return True
					except ValueError:
						return False
				return not any(is_number(cell.strip('"')) for cell in row)

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
		
		headers, rows = read_csv_with_optional_header(path)
		# print(headers,rows)
		vertices = np.array(rows, dtype=np.float32)

		if vertices.shape[1] in (1,2,3):
			if vertices.shape[1] < 3:
				vertices = np.pad(vertices, ((0, 0), (0, 3 - vertices.shape[1])), mode='constant')

			cld = PointCloud()
			cld.m_vertices = vertices
			return cld
		
		if headers is not None and len(headers):
			cld = NDimCloud(headers=headers)
		else:
			cld = NDimCloud(dims=len(rows[0]))
		cld.m_vertices = vertices

		cld.projectTo3D()
		
		# print("po projekcji")
		
		return cld

	@staticmethod	
	def save( obj, path ):
		return False
	
	@staticmethod	
	def inPlugin():
		return False

	@classmethod
	def	is_not_static(cls):
		return True
		
ParserCSV.regParser()