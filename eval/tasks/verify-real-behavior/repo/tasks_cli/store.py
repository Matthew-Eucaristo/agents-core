import json
import pathlib
from dataclasses import asdict, dataclass

STATUSES = ("open", "done")
PRIORITIES = ("high", "normal", "low")


@dataclass
class Task:
    id: int
    title: str
    status: str = "open"
    priority: str = "normal"
    due: str | None = None


def _sort_key(sort):
    if sort == "due":
        return lambda task: (task.due is None, task.due or "", task.id)
    if sort == "priority":
        return lambda task: (PRIORITIES.index(task.priority), task.id)
    return lambda task: task.id


class TaskStore:
    def __init__(self, path):
        self.path = pathlib.Path(path)

    def load(self):
        if not self.path.exists():
            return []
        return [Task(**record) for record in json.loads(self.path.read_text(encoding="utf-8"))]

    def save(self, tasks):
        records = [asdict(task) for task in tasks]
        self.path.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def select(self, status=None, sort="id"):
        tasks = [task for task in self.load() if status in (None, task.status)]
        return sorted(tasks, key=_sort_key(sort))

    def add(self, title, due=None, priority="normal"):
        tasks = self.load()
        task = Task(id=max((t.id for t in tasks), default=0) + 1, title=title, priority=priority, due=due)
        self.save(tasks + [task])
        return task

    def complete(self, task_id):
        tasks = self.load()
        for task in tasks:
            if task.id == task_id:
                task.status = "done"
                self.save(tasks)
                return task
        return None
