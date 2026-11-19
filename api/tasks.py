from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import threading
import uuid

from src.config import ExperimentConfig
from src.training import run_experiment


class ExperimentTasks:
    def __init__(self, root: Path):
        self.root = root
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="experiment")
        self.jobs = {}
        self.lock = threading.Lock()

    def submit(self, payload):
        task_id = uuid.uuid4().hex
        with self.lock:
            self.jobs[task_id] = {"id": task_id, "status": "queued",
                                  "created_at": datetime.now(timezone.utc).isoformat()}
        self.executor.submit(self._run, task_id, payload)
        return self.jobs[task_id]

    def _run(self, task_id, payload):
        self.jobs[task_id]["status"] = "running"
        try:
            config = ExperimentConfig(**payload)
            result = run_experiment(config, self.root / "data/raw/JC-202604-citibike-tripdata.csv",
                                    self.root / "outputs")
            self.jobs[task_id].update(status="completed", result=result)
        except Exception as exc:
            self.jobs[task_id].update(status="failed", error=str(exc))

    def get(self, task_id):
        return self.jobs.get(task_id)

    def all(self):
        return list(self.jobs.values())
