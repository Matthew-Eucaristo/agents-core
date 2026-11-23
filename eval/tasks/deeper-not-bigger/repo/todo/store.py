import json
import os


def default_path():
    return os.environ.get("TODO_FILE", "todo.json")


def load(path):
    try:
        with open(path) as handle:
            return json.load(handle)
    except FileNotFoundError:
        return []


def save(path, tasks):
    with open(path, "w") as handle:
        json.dump(tasks, handle, indent=1)


def add(tasks, title):
    task = {"id": len(tasks) + 1, "title": title}
    tasks.append(task)
    return task
