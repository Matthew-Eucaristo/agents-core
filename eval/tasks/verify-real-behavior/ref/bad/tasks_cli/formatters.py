import json
from dataclasses import asdict

COLUMNS = "{id:>3}  {status:<6}  {priority:<8}  {due:<10}  {title}"


def format_row(task):
    return COLUMNS.format(
        id=task.id,
        status=task.status,
        priority=task.priority,
        due=task.due or "-",
        title=task.title,
    )


def format_table(tasks):
    header = COLUMNS.format(id="ID", status="STATUS", priority="PRIORITY", due="DUE", title="TITLE")
    return "\n".join([header, *(format_row(task) for task in tasks)])


def format_summary(tasks):
    done = sum(1 for task in tasks if task.status == "done")
    return f"{len(tasks) - done} open, {done} done"


def format_json(tasks):
    return json.dumps([asdict(task) for task in tasks], indent=2)
