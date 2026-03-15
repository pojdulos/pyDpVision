from .taskManager import TaskManager, ParserLoadTaskRunner


class LoadTaskManager(TaskManager):
	def start_load(self, file_path, on_success=None, on_error=None):
		runner = ParserLoadTaskRunner(file_path, parent=self)
		if runner.parser is None:
			return False
		task = self.start_runner(
			runner,
			on_success=on_success,
			on_error=on_error,
			kind="load",
			label=runner.label,
		)
		return task is not None
