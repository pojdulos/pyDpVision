
from .. import Parser, AP, BaseObject, PointCloud, NDimCloud, GridData64

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


import numpy as np


def _detect_lateral_scale(step_raw, threshold=0.5):
    """
    Wykrywa skalę jednostki dla osi XY na podstawie kroku siatki.
    Krok >= threshold  → dane w µm → zwraca 0.001 (µm→mm)
    Krok <  threshold  → dane już w mm  → zwraca 1.0
    """
    return 0.001 if float(step_raw) >= threshold else 1.0


def _detect_z_scale(z, threshold=0.5):
    """
    Wykrywa skalę jednostki dla osi Z z minimalnego kroku między
    unikalnymi (skwantowanymi) wartościami Z.
    Min_step >= threshold  → dane w µm → zwraca 0.001
    Min_step <  threshold  → dane już w mm  → zwraca 1.0
    Jeśli Z jest ciągłe/nieskwantowane (min_step ≈ 0) → zwraca 1.0.
    """
    z_arr = np.asarray(z, dtype=np.float64).ravel()
    u = np.unique(z_arr[np.isfinite(z_arr)])
    if len(u) < 2:
        return 1.0
    d = np.diff(u)
    d = d[d > 1e-9]
    if len(d) == 0:
        return 1.0
    return 0.001 if float(d.min()) >= threshold else 1.0


def check_grid_steps(df, decimals=3):
    x = df.iloc[:,0].round(decimals).values
    y = df.iloc[:,1].round(decimals).values

    xs = np.unique(x)
    ys = np.unique(y)

    dx = np.unique(np.round(np.diff(xs), decimals))
    dy = np.unique(np.round(np.diff(ys), decimals))

    print("Kroki X:", dx)
    print("Kroki Y:", dy)
    return xs, ys

def is_regular_grid(df, decimals=3, tol=1e-6):
    # bierz kolumny x,y
    x = df.iloc[:,0].round(decimals).values
    y = df.iloc[:,1].round(decimals).values

    xs, ys = check_grid_steps(df, decimals)
    # xs = np.unique(x)
    # ys = np.unique(y)

    dx = np.diff(xs)
    dy = np.diff(ys)

    is_regular_x = np.allclose(dx, dx[0], rtol=tol, atol=tol)
    is_regular_y = np.allclose(dy, dy[0], rtol=tol, atol=tol)

    expected = len(xs) * len(ys)
    actual = len(df)
    complete = (expected == actual)

    return is_regular_x and is_regular_y, complete, len(xs), len(ys), expected, actual

def dataframe_to_grid(df, round_decimals=6, auto_unit=True):
    """
    Konwertuje DataFrame [x, y, z] na grid 2D.
    
    Zwraca:
        grid       - ndarray (h, w) float32 z wartościami z
        stepX,stepY- kroki (float64)
        xs, ys     - unikalne współrzędne (float64)
        unit_scale - 1.0 (brak konwersji) albo 0.001 (µm→mm)
    """
    x = df.iloc[:,0].values.astype(np.float64)
    y = df.iloc[:,1].values.astype(np.float64)
    z = df.iloc[:,2].values.astype(np.float64)

    xs = np.unique(x)
    ys = np.unique(y)

    stepX_raw = (xs[-1] - xs[0]) / (len(xs)-1)
    stepY_raw = (ys[-1] - ys[0]) / (len(ys)-1)

    unit_scale = 1.0
    if auto_unit:
        scale_xy = _detect_lateral_scale(max(stepX_raw, stepY_raw))
        scale_z  = _detect_z_scale(z)
        if scale_xy != 1.0 or scale_z != 1.0:
            print(f"[auto unit] XY: ×{scale_xy}, Z: ×{scale_z}")
        unit_scale = scale_xy
    else:
        scale_xy = scale_z = 1.0

    xs = xs * scale_xy
    ys = ys * scale_xy
    x  = x  * scale_xy
    y  = y  * scale_xy
    z  = z  * scale_z

    stepX = float(xs[-1] - xs[0]) / (len(xs)-1)
    stepY = float(ys[-1] - ys[0]) / (len(ys)-1)
    stepX = round(stepX, round_decimals)
    stepY = round(stepY, round_decimals)

    w, h = len(xs), len(ys)
    grid = np.full((h, w), np.nan, dtype=np.float64)

    x_to_idx = {v:i for i,v in enumerate(xs)}
    y_to_idx = {v:i for i,v in enumerate(ys)}

    for xi, yi, zi in zip(x, y, z):
        ix = x_to_idx[xi]
        iy = y_to_idx[yi]
        grid[iy, ix] = zi

    return grid, float(stepX), float(stepY), xs, ys, unit_scale

def vertices_to_grid(vertices, round_decimals=6, auto_unit=True):
    xs = np.unique(vertices[:,0])
    ys = np.unique(vertices[:,1])

    stepX_raw = (xs[-1] - xs[0]) / (len(xs)-1)
    stepY_raw = (ys[-1] - ys[0]) / (len(ys)-1)

    unit_scale = 1.0
    if auto_unit:
        scale_xy = _detect_lateral_scale(max(stepX_raw, stepY_raw))
        scale_z  = _detect_z_scale(vertices[:, 2])
        if scale_xy != 1.0 or scale_z != 1.0:
            print(f"[auto unit] XY: ×{scale_xy}, Z: ×{scale_z}")
        unit_scale = scale_xy
    else:
        scale_xy = scale_z = 1.0

    xs = xs * scale_xy
    ys = ys * scale_xy
    vertices = vertices.copy()
    vertices[:, 0] *= scale_xy
    vertices[:, 1] *= scale_xy
    vertices[:, 2] *= scale_z

    # stepX = round((xs[-1] - xs[0]) / (len(xs)-1), round_decimals)
    # stepY = round((ys[-1] - ys[0]) / (len(ys)-1), round_decimals)

    stepX = float(xs[-1] - xs[0]) / (len(xs)-1)
    stepY = float(ys[-1] - ys[0]) / (len(ys)-1)
    stepX = round(stepX, round_decimals)
    stepY = round(stepY, round_decimals)

    w, h = len(xs), len(ys)
    grid = np.full((h, w), np.nan, dtype=np.float32)

    x_to_idx = {v:i for i,v in enumerate(xs)}
    y_to_idx = {v:i for i,v in enumerate(ys)}

    for x,y,z in vertices:
        ix = x_to_idx[x]
        iy = y_to_idx[y]
        grid[iy, ix] = z

    # <- zwracam stepX, stepY jako Python float (64-bit),
    # a grid jako float32
    return grid, float(stepX), float(stepY), xs, ys, unit_scale


def detect_decimals_in_csv_xy(path, sep=';', sample_rows=100):
    max_decimals = 0
    with open(path, encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= sample_rows:
                break
            cells = line.strip().split(sep)
            if len(cells) < 2:
                continue
            for c in cells[:2]:
                c = c.strip().strip('"')
                if '.' in c:
                    try:
                        float(c)  # upewnij się że to liczba
                        right = c.split('.', 1)[1].strip()
                        decimals = len(right)
                        max_decimals = max(max_decimals, decimals)
                    except ValueError:
                        continue
    return max_decimals if max_decimals > 0 else 6



class CSVLoaderWorker(QObject):
	progressChanged = pyqtSignal(int)	  # sygnał do aktualizacji progress bara
	loadingFinished = pyqtSignal(pd.DataFrame)  # sygnał, kiedy wszystko wczytane
	errorOccurred = pyqtSignal(str)

	def __init__(self, path, chunksize=10000, separator=r'[;,\t ]+'):#';'):
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
				df = pd.read_csv(self.path, engine='python', delimiter=self.separator, chunksize=self.chunksize)
			else:
				# nie ma nagłówków
				df = pd.read_csv(self.path, engine='python', delimiter=self.separator, header=None, chunksize=self.chunksize)

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
	load_exts = ['.csv','.dat','.txt']
	#save_exts = ['.csv']

	def __init__(self, path):
		super( ParserCSV, self ).__init__()
		self.path = path
		self.round_decimals = detect_decimals_in_csv_xy(path)
		self._thread = QThread()
		self._worker = CSVLoaderWorker(path)

	def looks_like_grid(self, df, tol=1e-3, frac_threshold=0.95, completeness_threshold=0.5):
		x = df.iloc[:,0].round(self.round_decimals).values
		y = df.iloc[:,1].round(self.round_decimals).values

		xs = np.unique(x)
		ys = np.unique(y)

		if len(xs) < 2 or len(ys) < 2:
			return False, None, None, len(xs), len(ys), 0.0

		dx = np.round(np.diff(xs), self.round_decimals)
		dy = np.round(np.diff(ys), self.round_decimals)

		stepX = np.median(dx)
		stepY = np.median(dy)

		frac_x = np.mean(dx == stepX)
		frac_y = np.mean(dy == stepY)

		is_regular_x = frac_x >= frac_threshold
		is_regular_y = frac_y >= frac_threshold

		completeness = len(df) / (len(xs) * len(ys))

		is_grid = (is_regular_x and is_regular_y and completeness >= completeness_threshold)

		print(f"stepX: {stepX}, stepY: {stepY}, frac_x={frac_x:.6f}, frac_y={frac_y:.6f}, completeness={completeness:.3f}, is_grid={is_grid}")

		return is_grid, stepX, stepY, len(xs), len(ys), completeness



	def dataframe_to_grid(self, df, auto_unit=True):
		"""
		Konwertuje DataFrame [x, y, z] na grid 2D.
		
		Zwraca:
			grid       - ndarray (h, w) float32 z wartościami z
			stepX,stepY- kroki (float64)
			xs, ys     - unikalne współrzędne (float64)
			unit_scale - 1.0 (brak konwersji) albo 0.001 (µm→mm)
		"""
		x = df.iloc[:,0].values.astype(np.float64)
		y = df.iloc[:,1].values.astype(np.float64)
		z = df.iloc[:,2].values.astype(np.float64)

		# Zaokrąglamy do wykrytej liczby miejsc (self.round_decimals)
		x = np.round(x, self.round_decimals)
		y = np.round(y, self.round_decimals)

		xs = np.unique(x)
		ys = np.unique(y)

		xs = np.round(xs, self.round_decimals)
		ys = np.round(ys, self.round_decimals)

		# typowe kroki w osi X i Y
		stepX_raw = np.median(np.diff(xs))
		stepY_raw = np.median(np.diff(ys))

		unit_scale = 1.0
		if auto_unit:
			scale_xy = _detect_lateral_scale(max(stepX_raw, stepY_raw))
			scale_z  = _detect_z_scale(z)
			if scale_xy != 1.0 or scale_z != 1.0:
				print(f"[auto unit] XY: ×{scale_xy}, Z: ×{scale_z}")
			unit_scale = scale_xy
		else:
			scale_xy = scale_z = 1.0

		xs = xs * scale_xy
		ys = ys * scale_xy
		x  = x  * scale_xy
		y  = y  * scale_xy
		z  = z  * scale_z

		stepX = np.median(np.diff(xs))
		stepY = np.median(np.diff(ys))
		stepX = round(stepX, self.round_decimals)
		stepY = round(stepY, self.round_decimals)

		w, h = len(xs), len(ys)
		grid = np.full((h, w), np.nan, dtype=np.float32)

		x_to_idx = {v:i for i,v in enumerate(xs)}
		y_to_idx = {v:i for i,v in enumerate(ys)}

		for xi, yi, zi in zip(x, y, z):
			ix = x_to_idx[xi]
			iy = y_to_idx[yi]
			grid[iy, ix] = zi

		return grid, float(stepX), float(stepY), xs, ys, unit_scale

	def dataframe_to_pointcloud(self, vertices):
		ndims = vertices.shape[1]
		if ndims in (1,2,3):
			if ndims < 3:
				vertices = np.pad(vertices, ((0, 0), (0, 3 - ndims)), mode='constant')

			col = 0
			x = vertices[:, col].astype(float)
			x = x[np.isfinite(x)]          # opcjonalnie: usuń NaN/Inf

			u = np.unique(x)  # unikalne + posortowane
			if u.size < 2:
				min_nonzero = np.inf
			else:
				d = np.diff(u)
				eps = 1e-9
				# minimalna różnica większa od eps; jeśli brak, wyjdzie inf
				min_nonzero = d[d > eps].min(initial=np.inf)

			# typical_scale = np.median(np.abs(vertices[:, col]))
			# print(typical_scale)

			if np.isfinite(min_nonzero) and min_nonzero > eps and min_nonzero >= 0.5:
				print(f"[auto unit] XY min_step={round(min_nonzero,4)} → µm, konwertuję do mm")
				vertices[:, 0] *= 0.001
				vertices[:, 1] *= 0.001
				scale_z = _detect_z_scale(vertices[:, 2])
				if scale_z != 1.0:
					print(f"[auto unit] Z: ×{scale_z}")
				vertices[:, 2] *= scale_z
			else:
				# XY wydaje się być w mm, sprawdź Z osobno
				scale_z = _detect_z_scale(vertices[:, 2])
				if scale_z != 1.0:
					print(f"[auto unit] XY w mm, Z: ×{scale_z} (µm→mm)")
				vertices[:, 2] *= scale_z

			cld = PointCloud()
			cld.m_vertices = vertices
			return cld

	def dataframe_to_object(self, dataframe):
		ncols = dataframe.shape[1]
		headers = dataframe.columns.tolist()

		# --- przypadek 1: wielowymiarowe dane ---
		if ncols > 3 or (headers is not None and len(headers) > 0 and ncols > 3):
			print("Dane wyglądają na wielowymiarowe -> NDimCloud")
			if headers:
				cld = NDimCloud(headers=headers)
			else:
				cld = NDimCloud(dims=ncols)
			cld.m_vertices = dataframe.values.astype(np.float32)
			cld.projectTo3D()
			return cld

		# --- przypadek 2: kandydat na grid / chmurę punktów ---
		ok, stepX, stepY, nx, ny, cpl = self.looks_like_grid(dataframe, tol=1e-3)

		if ok:
			print(f"To wygląda na grid {nx}×{ny}, stepX={stepX}, stepY={stepY}")
			grid, stepX, stepY, xs, ys, scale = self.dataframe_to_grid(dataframe)
			
			if scale != 1.0:
				print(f"[INFO] Dane w mm, przeskalowano do µm (unit_scale={scale})")

			return GridData64(grid, stepX=stepX, stepY=stepY, offsetX=float(xs[0]), offsetY=float(ys[0]))

		# --- przypadek 3: zwykła chmura punktów ---
		print("To nie jest regularny grid -> PointCloud")
		vertices = dataframe.values.astype(np.float32)
		return self.dataframe_to_pointcloud(vertices)


	def on_loading_finished(self, dataframe):
		self._thread.quit()
		self._thread.wait()
		self._worker.deleteLater()
		self._thread.deleteLater()

		print("Dane załadowane!", dataframe.shape)

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

		ndims = vertices.shape[1]
		if ndims in (1,2,3):
			if ndims < 3:
				vertices = np.pad(vertices, ((0, 0), (0, 3 - ndims)), mode='constant')

			if ndims > 1:
				grid, stepX, stepY, xs, ys, unit_scale = vertices_to_grid(vertices)
				cld = GridData64(grid, stepX=stepX, stepY=stepY)
			else:
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