# -*- coding: utf-8 -*-
"""
Created on Mon Nov 27 12:58:12 2023

@author: pojdulos
"""
from PyQt5.QtCore import *
import os

class Parser(QObject):
	progressStarted = pyqtSignal(int, int, int, str)
	progressValueChanged = pyqtSignal(int)
	progressTextChanged = pyqtSignal(str)
	progressFinished = pyqtSignal()

	descr = "Generic parser"
	load_exts = []
	save_exts = []

	parsers = []

	def __init__(self):
		super( Parser, self ).__init__()

	def _emit_progress_started(self, min_value=0, max_value=100, value=0, text=""):
		self.progressStarted.emit(min_value, max_value, value, text)

	def _emit_progress_value(self, value):
		self.progressValueChanged.emit(value)

	def _emit_progress_text(self, text):
		self.progressTextChanged.emit(text)

	def _emit_progress_finished(self):
		self.progressFinished.emit()

	def supports_runtime_cancel(self):
		return True

	def _connect_worker_progress(self, worker):
		if hasattr(worker, 'progressChanged'):
			worker.progressChanged.connect(self.progressValueChanged)
		if hasattr(worker, 'statusChanged'):
			worker.statusChanged.connect(self.progressTextChanged)

	@classmethod
	def regParser(cls):
		if not cls in Parser.parsers:
			print(f"registering parser: {cls.__name__}")
			Parser.parsers.append(cls)
		else:
			print(f"parser: {cls.__name__} already registered")

	@staticmethod
	def unregParser( t ):
		if t in Parser.parsers:
			Parser.parsers.remove(t)

	@staticmethod
	def getLoadExts():
		ext = "All (*.*)"
		for parser in Parser.parsers:
			ext = parser.loadExts(ext)
		return ext

	@staticmethod	
	def check_by_content(path):
		return False

	@staticmethod	
	def get_parser_class(path):
		for p in tuple(Parser.parsers):
			if p.canLoadExt(path=path) or p.check_by_content(path=path):
				return p
		return None

	@staticmethod	
	def get_instance(path):
		parser_cls = Parser.get_parser_class(path)
		if parser_cls is None:
			print(f"File format is not supported yet: {path}")
			return None
		if parser_cls.is_not_static():
			return parser_cls(path)
		return SyncParserAdapter(path, parser_cls)

	@staticmethod	
	def load(path):
		for p in tuple(Parser.parsers):
			if p.canLoadExt(path=path) or p.check_by_content(path=path):
				obj = p.load(path)
				obj.label = os.path.basename(path)
				return obj

		print(f"File format is not supported yet: {path}")
		return None
	
	@staticmethod	
	def save(obj, path):
		fname, fext = os.path.splitext(path)
		fext = fext.lower()
		for p in Parser.parsers:
			if p.canSaveExt(fext):
				return p.save(obj, path)
		return False

	@staticmethod
	def get_save_parser_class(obj, path):
		_, fext = os.path.splitext(path)
		fext = fext.lower()
		for parser in Parser.parsers:
			if parser.canSaveExt(fext) and parser.canSaveObject(obj):
				return parser
		return None

	@staticmethod
	def getSaveParsers(obj):
		result = []
		for parser in Parser.parsers:
			if parser.canSaveObject(obj):
				result.append(parser)
		return result

	@staticmethod
	def getSaveExts(obj):
		filters = []
		for parser in Parser.getSaveParsers(obj):
			if len(parser.save_exts):
				patterns = ' '.join([f'*{ext}' for ext in parser.save_exts])
				filters.append(f"{parser.descr} ({patterns})")
		return ';;'.join(filters)
	
	@staticmethod	
	def inPlugin():
		return False
	
	###### CLASS METHODS #####
	@classmethod
	def	is_not_static(cls):
		return False

	@classmethod
	def canLoadExt(cls, path=None):
		if path:
			return path.endswith(tuple(cls.load_exts))
		return False

	@classmethod
	def canSaveExt(cls, ext):
		return ext in cls.save_exts

	@classmethod
	def canSaveObject(cls, obj):
		return False

	@classmethod
	def supports_save_progress(cls):
		return False

	@classmethod
	def loadExts(cls, ext):
		if len(cls.load_exts):
			if len(ext):
				ext = ext + ";;"
			ext = ext + cls.descr + " ("
			for e in cls.load_exts:
				ext = ext + "*" + e + ";"

			ext = ext[:-1] + ')'
		return ext


class ThreadedParser(Parser):
	loadingFinished = pyqtSignal(object)
	errorOccurred = pyqtSignal()

	def __init__(self, path, worker, worker_method_name, progress_text=""):
		super().__init__()
		self.path = path
		self._thread = QThread()
		self._worker = worker
		self._worker_method_name = worker_method_name
		self._progress_text = progress_text or "Wczytywanie pliku"
		self._cancel_requested = False
		self._completion_emitted = False

	def _cleanup_thread(self):
		if self._thread is not None:
			self._thread.quit()
			self._thread.wait()
		if self._worker is not None:
			self._worker.deleteLater()
		if self._thread is not None:
			self._thread.deleteLater()
		self._worker = None
		self._thread = None

	def _transform_loaded_data(self, data):
		return data

	def _error_prefix(self):
		return self.__class__.__name__

	def on_loading_finished(self, data):
		if self._completion_emitted:
			return
		self._completion_emitted = True
		obj = self._transform_loaded_data(data)
		self._cleanup_thread()
		self._emit_progress_finished()
		self.loadingFinished.emit(obj)

	def on_loading_error(self, msg):
		if self._completion_emitted:
			return
		self._completion_emitted = True
		self._cleanup_thread()
		self._emit_progress_finished()
		if msg != "Przerwano":
			print(f"{self._error_prefix()}: {msg}")
		self.errorOccurred.emit()

	def _on_thread_finished(self):
		if self._completion_emitted:
			return
		if self._cancel_requested:
			self.on_loading_error("Przerwano")
		else:
			self.on_loading_error("Watek zakonczyl sie bez wyniku")

	def on_stop_loading(self):
		if self._worker is not None and hasattr(self._worker, 'stop'):
			self._worker.stop()
		self._cancel_requested = True
		self._emit_progress_text("Cancelling... Please wait...")
		if self._thread is not None:
			self._thread.quit()

	def load_async(self, progressBar=None):
		self._cancel_requested = False
		self._completion_emitted = False
		self._emit_progress_started(0, 100, 0, self._progress_text)
		self._connect_worker_progress(self._worker)
		self._worker.moveToThread(self._thread)
		self._thread.started.connect(getattr(self._worker, self._worker_method_name))
		self._thread.finished.connect(self._on_thread_finished)
		self._worker.loadingFinished.connect(self.on_loading_finished)
		self._worker.errorOccurred.connect(self.on_loading_error)
		self._thread.start()


class SyncLoadWorker(QObject):
	loadingFinished = pyqtSignal(object)
	errorOccurred = pyqtSignal(str)
	statusChanged = pyqtSignal(str)

	def __init__(self, parser_cls, path):
		super().__init__()
		self._parser_cls = parser_cls
		self._path = path
		self._is_running = True

	def stop(self):
		self._is_running = False

	def run(self):
		try:
			self.statusChanged.emit(f"Wczytywanie {self._parser_cls.descr}")
			obj = self._parser_cls.load(self._path)
			if not self._is_running:
				self.errorOccurred.emit("Przerwano")
				return
			if obj is None:
				raise ValueError("Parser zwrocil pusty wynik")
			self.loadingFinished.emit(obj)
		except Exception as exc:
			self.errorOccurred.emit(str(exc))


class SyncParserAdapter(ThreadedParser):
	def __init__(self, path, parser_cls):
		self._parser_cls = parser_cls
		super().__init__(
			path,
			SyncLoadWorker(parser_cls, path),
			'run',
			f"Wczytywanie {parser_cls.descr}",
		)

	def load_async(self, progressBar=None):
		self._cancel_requested = False
		self._completion_emitted = False
		self._emit_progress_started(0, 0, 0, self._progress_text)
		self._connect_worker_progress(self._worker)
		self._worker.moveToThread(self._thread)
		self._thread.started.connect(getattr(self._worker, self._worker_method_name))
		self._thread.finished.connect(self._on_thread_finished)
		self._worker.loadingFinished.connect(self.on_loading_finished)
		self._worker.errorOccurred.connect(self.on_loading_error)
		self._thread.start()

	def _error_prefix(self):
		return f"{self._parser_cls.__name__}"

	def supports_runtime_cancel(self):
		return False
