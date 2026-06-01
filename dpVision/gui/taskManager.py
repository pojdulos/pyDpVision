from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout

from .. import Parser
from .progressIndicator import ProgressIndicator

import os


class TaskPanel(QWidget):
	def __init__(self, parent=None):
		super().__init__(parent)
		self._layout = QVBoxLayout(self)
		self._layout.setContentsMargins(0, 0, 0, 0)
		self._layout.setSpacing(2)
		self.hide()

	def add_indicator(self, indicator):
		self._layout.addWidget(indicator)
		self.show()

	def remove_indicator(self, indicator):
		self._layout.removeWidget(indicator)
		indicator.setParent(None)
		indicator.deleteLater()
		if self._layout.count() == 0:
			self.hide()


class BaseTaskRunner(QObject):
	progressStarted = pyqtSignal(int, int, int, str)
	progressValueChanged = pyqtSignal(int)
	progressTextChanged = pyqtSignal(str)
	progressFinished = pyqtSignal()
	finished = pyqtSignal(object)
	failed = pyqtSignal(object)

	def __init__(self, label="", kind="generic", supports_runtime_cancel=False, parent=None):
		super().__init__(parent)
		self.label = label
		self.kind = kind
		self._supports_runtime_cancel = supports_runtime_cancel

	def supports_runtime_cancel(self):
		return self._supports_runtime_cancel

	def start(self):
		raise NotImplementedError

	def cancel(self):
		pass


class ParserLoadTaskRunner(BaseTaskRunner):
	def __init__(self, file_path, parser=None, parent=None):
		parser = parser or Parser.get_instance(file_path)
		label = os.path.basename(file_path)
		super().__init__(
			label=label,
			kind="load",
			supports_runtime_cancel=(parser.supports_runtime_cancel() if parser is not None and hasattr(parser, "supports_runtime_cancel") else True),
			parent=parent,
		)
		self.file_path = file_path
		self.parser = parser
		if self.parser is not None:
			self.parser.progressStarted.connect(self.progressStarted)
			self.parser.progressValueChanged.connect(self.progressValueChanged)
			self.parser.progressTextChanged.connect(self.progressTextChanged)
			self.parser.progressFinished.connect(self.progressFinished)
			self.parser.loadingFinished.connect(self._on_finished)
			self.parser.errorOccurred.connect(self._on_failed)

	def start(self):
		if self.parser is None:
			self.failed.emit("Nie znaleziono parsera")
			return
		self.parser.load_async()

	def cancel(self):
		if self.parser is not None and hasattr(self.parser, "on_stop_loading"):
			self.parser.on_stop_loading()

	def cleanup(self):
		if self.parser is None:
			return
		try:
			self.parser.progressStarted.disconnect(self.progressStarted)
			self.parser.progressValueChanged.disconnect(self.progressValueChanged)
			self.parser.progressTextChanged.disconnect(self.progressTextChanged)
			self.parser.progressFinished.disconnect(self.progressFinished)
			self.parser.loadingFinished.disconnect(self._on_finished)
			self.parser.errorOccurred.disconnect(self._on_failed)
		except TypeError:
			pass
		self.parser.deleteLater()
		self.parser = None

	def _on_finished(self, result):
		self.finished.emit(result)

	def _on_failed(self):
		self.failed.emit(None)


class _ParserSaveWorker(QObject):
	finished = pyqtSignal(object)
	failed = pyqtSignal(object)
	progressStarted = pyqtSignal(int, int, int, str)
	progressChanged = pyqtSignal(int)
	statusChanged = pyqtSignal(str)

	def __init__(self, parser_cls, obj, path):
		super().__init__()
		self._parser_cls = parser_cls
		self._obj = obj
		self._path = path

	def run(self):
		try:
			self.statusChanged.emit(f"Zapisywanie {self._parser_cls.descr}")
			if hasattr(self._parser_cls, "supports_save_progress") and self._parser_cls.supports_save_progress():
				self.progressStarted.emit(0, 100, 0, f"Zapisywanie {self._parser_cls.descr}")
				result = self._parser_cls.save(
					self._obj,
					self._path,
					progress_cb=self.progressChanged.emit,
					status_cb=self.statusChanged.emit,
				)
			else:
				result = self._parser_cls.save(self._obj, self._path)
			if result:
				self.finished.emit(self._path)
			else:
				self.failed.emit(f"Nie udalo sie zapisac pliku: {self._path}")
		except Exception as exc:
			self.failed.emit(exc)


class ParserSaveTaskRunner(BaseTaskRunner):
	def __init__(self, obj, path, parser_cls=None, parent=None):
		parser_cls = parser_cls or Parser.get_save_parser_class(obj, path)
		label = os.path.basename(path)
		descr = parser_cls.descr if parser_cls is not None else "pliku"
		super().__init__(label=label, kind="save", supports_runtime_cancel=False, parent=parent)
		self.obj = obj
		self.path = path
		self.parser_cls = parser_cls
		self._progress_text = f"Zapisywanie {descr}"
		self._thread = None
		self._worker = None

	def start(self):
		if self.parser_cls is None:
			self.failed.emit("Nie znaleziono parsera zapisu")
			return
		if not (hasattr(self.parser_cls, "supports_save_progress") and self.parser_cls.supports_save_progress()):
			self.progressStarted.emit(0, 0, 0, self._progress_text)
		self._thread = QThread()
		self._worker = _ParserSaveWorker(self.parser_cls, self.obj, self.path)
		self._worker.moveToThread(self._thread)
		self._worker.progressStarted.connect(self.progressStarted)
		self._worker.progressChanged.connect(self.progressValueChanged)
		self._worker.statusChanged.connect(self.progressTextChanged)
		self._thread.started.connect(self._worker.run)
		self._worker.finished.connect(self._on_finished)
		self._worker.failed.connect(self._on_failed)
		self._thread.start()

	def cleanup(self):
		if self._thread is not None:
			self._thread.quit()
			self._thread.wait()
			self._thread.deleteLater()
		if self._worker is not None:
			self._worker.deleteLater()
		self._thread = None
		self._worker = None

	def _on_finished(self, result):
		self.progressFinished.emit()
		self.cleanup()
		self.finished.emit(result)

	def _on_failed(self, error):
		self.progressFinished.emit()
		self.cleanup()
		self.failed.emit(error)


class _FunctionWorker(QObject):
	finished = pyqtSignal(object)
	failed = pyqtSignal(object)
	progressStarted = pyqtSignal(int, int, int, str)
	progressChanged = pyqtSignal(int)
	statusChanged = pyqtSignal(str)

	def __init__(self, fn, args, kwargs, progress_text=None, inject_progress=False):
		super().__init__()
		self._fn = fn
		self._args = args
		self._kwargs = kwargs
		self._progress_text = progress_text
		self._inject_progress = inject_progress

	def run(self):
		try:
			call_kwargs = dict(self._kwargs)
			if self._inject_progress:
				if self._progress_text is not None:
					self.progressStarted.emit(0, 100, 0, self._progress_text)
				call_kwargs["progress_cb"] = self.progressChanged.emit
				call_kwargs["status_cb"] = self.statusChanged.emit
			self.finished.emit(self._fn(*self._args, **call_kwargs))
		except Exception as exc:
			self.failed.emit(exc)


class FunctionTaskRunner(BaseTaskRunner):
	def __init__(self, fn, *args, label="Task", kind="compute", progress_text=None, inject_progress=False, parent=None, **kwargs):
		super().__init__(label=label, kind=kind, supports_runtime_cancel=False, parent=parent)
		self._fn = fn
		self._args = args
		self._kwargs = kwargs
		self._progress_text = progress_text or label
		self._inject_progress = inject_progress
		self._thread = None
		self._worker = None

	def start(self):
		self._thread = QThread()
		self._worker = _FunctionWorker(
			self._fn,
			self._args,
			self._kwargs,
			progress_text=self._progress_text,
			inject_progress=self._inject_progress,
		)
		self._worker.moveToThread(self._thread)
		if self._inject_progress:
			self._worker.progressStarted.connect(self.progressStarted)
			self._worker.progressChanged.connect(self.progressValueChanged)
			self._worker.statusChanged.connect(self.progressTextChanged)
		else:
			self.progressStarted.emit(0, 0, 0, self._progress_text)
		self._thread.started.connect(self._worker.run)
		self._worker.finished.connect(self._on_finished)
		self._worker.failed.connect(self._on_failed)
		self._thread.start()

	def cleanup(self):
		if self._thread is not None:
			self._thread.quit()
			self._thread.wait()
			self._thread.deleteLater()
		if self._worker is not None:
			self._worker.deleteLater()
		self._thread = None
		self._worker = None

	def _on_finished(self, result):
		self.progressFinished.emit()
		self.cleanup()
		self.finished.emit(result)

	def _on_failed(self, error):
		self.progressFinished.emit()
		self.cleanup()
		self.failed.emit(error)


class Task(QObject):
	finished = pyqtSignal(object)
	failed = pyqtSignal(object)
	cancelled = pyqtSignal()

	def __init__(self, runner, indicator, kind=None, label=None, parent=None):
		super().__init__(parent)
		self.runner = runner
		self.indicator = indicator
		self.kind = kind or getattr(runner, "kind", "generic")
		self.label = label or getattr(runner, "label", self.kind)
		self.state = "queued"
		self._runtime_cancel_supported = runner.supports_runtime_cancel() if hasattr(runner, "supports_runtime_cancel") else True

		self.runner.progressStarted.connect(self._on_progress_started)
		self.runner.progressValueChanged.connect(self.indicator.setValue)
		self.runner.progressTextChanged.connect(self._on_progress_text)
		self.runner.progressFinished.connect(self.indicator.finish)
		self.runner.finished.connect(self._on_finished)
		self.runner.failed.connect(self._on_failed)
		self.indicator.cancel_button_pressed.connect(self.cancel)

	def start(self):
		self.state = "running"
		self.indicator.start(0, 0, 0, self._format_text("Starting..."))
		self.indicator.setCancelVisible(self._runtime_cancel_supported)
		self.runner.start()

	def queue(self):
		self.state = "queued"
		self.indicator.start(0, 0, 0, self._format_text("Queued..."))
		self.indicator.setCancelVisible(True)

	def cancel(self):
		if self.state == "queued":
			self.state = "cancelled"
			self.indicator.setText(self._format_text("Cancelled"))
			self.cancelled.emit()
			return
		self.state = "cancelling"
		self.indicator.setText(self._format_text("Cancelling... Please wait..."))
		self.indicator.setCancelVisible(False)
		self.runner.cancel()

	def cleanup(self):
		try:
			self.runner.progressStarted.disconnect(self._on_progress_started)
			self.runner.progressValueChanged.disconnect(self.indicator.setValue)
			self.runner.progressTextChanged.disconnect(self._on_progress_text)
			self.runner.progressFinished.disconnect(self.indicator.finish)
			self.runner.finished.disconnect(self._on_finished)
			self.runner.failed.disconnect(self._on_failed)
		except TypeError:
			pass
		try:
			self.indicator.cancel_button_pressed.disconnect()
		except TypeError:
			pass
		if hasattr(self.runner, "cleanup"):
			self.runner.cleanup()

	def _format_text(self, text):
		return f"{self.label}: {text}" if text else self.label

	def _on_progress_started(self, min_value, max_value, value, text):
		self.indicator.start(min_value, max_value, value, self._format_text(text))
		self.indicator.setCancelVisible(self.state == "queued" or self._runtime_cancel_supported)

	def _on_progress_text(self, text):
		self.indicator.setText(self._format_text(text))

	def _on_finished(self, result):
		self.finished.emit(result)

	def _on_failed(self, error):
		self.failed.emit(error)


class TaskManager(QObject):
	def __init__(self, main_window, kind_limits=None):
		super().__init__(main_window)
		self.main_window = main_window
		self.panel = TaskPanel(main_window.statusBar)
		self.main_window.statusBar.addPermanentWidget(self.panel, 0)
		self._tasks = []
		self._queue = []
		self._active_by_kind = {}
		self._kind_limits = {
			"load": 1,
			"save": 1,
			"compute": 2,
			"generic": 1,
		}
		if kind_limits:
			self._kind_limits.update(kind_limits)

	def set_kind_limit(self, kind, limit):
		self._kind_limits[kind] = int(limit)
		self._start_queued_tasks()

	def start_runner(self, runner, on_success=None, on_error=None, on_cancelled=None, kind=None, label=None):
		if runner is None:
			return None

		task_kind = kind or getattr(runner, "kind", "generic")
		task_label = label or getattr(runner, "label", task_kind)
		indicator = ProgressIndicator(self.panel, self.panel)
		task = Task(runner, indicator, kind=task_kind, label=task_label, parent=self)
		self._tasks.append(task)
		self.panel.add_indicator(indicator)

		def handle_success(result):
			self._finalize_task(task)
			if on_success:
				on_success(result)

		def handle_error(error):
			self._finalize_task(task)
			if on_error:
				on_error(error)

		def handle_cancelled():
			self._finalize_task(task)
			if on_cancelled:
				on_cancelled()

		task.finished.connect(handle_success)
		task.failed.connect(handle_error)
		task.cancelled.connect(handle_cancelled)

		if self._can_start(task.kind):
			self._register_active(task)
			task.start()
		else:
			self._queue.append(task)
			task.queue()

		return task

	def _limit_for_kind(self, kind):
		return self._kind_limits.get(kind, self._kind_limits.get("generic", 1))

	def _can_start(self, kind):
		limit = self._limit_for_kind(kind)
		active = len(self._active_by_kind.get(kind, []))
		return active < limit

	def _register_active(self, task):
		self._active_by_kind.setdefault(task.kind, []).append(task)

	def _unregister_active(self, task):
		active = self._active_by_kind.get(task.kind)
		if not active:
			return
		if task in active:
			active.remove(task)
		if not active:
			self._active_by_kind.pop(task.kind, None)

	def _finalize_task(self, task):
		task.cleanup()
		if task in self._tasks:
			self._tasks.remove(task)
		if task in self._queue:
			self._queue.remove(task)
		self._unregister_active(task)
		self.panel.remove_indicator(task.indicator)
		task.deleteLater()
		self._start_queued_tasks()

	def _start_queued_tasks(self):
		progress = True
		while progress:
			progress = False
			for task in list(self._queue):
				if not self._can_start(task.kind):
					continue
				self._queue.remove(task)
				self._register_active(task)
				task.start()
				progress = True
				break
