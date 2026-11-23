import argparse
import sys

from todo import store


def main(argv=None):
    parser = argparse.ArgumentParser(prog="todo", description="Keep a short list of tasks.")
    parser.add_argument("--file", default=store.default_path(), help="task file (default: $TODO_FILE or todo.json)")
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add", help="add a task")
    add.add_argument("title")
    commands.add_parser("list", help="list the tasks")
    remove = commands.add_parser("remove", help="remove a task")
    remove.add_argument("id", type=int)
    options = parser.parse_args(argv)

    tasks = store.load(options.file)
    if options.command == "add":
        title = options.title.strip()
        if not title:
            sys.stderr.write("error: the title is empty\n")
            return 1
        task = store.add(tasks, title)
        store.save(options.file, tasks)
        print(f"added {task['id']}: {task['title']}")
    elif options.command == "remove":
        task = store.remove(tasks, options.id)
        if task is None:
            sys.stderr.write(f"error: no task {options.id}\n")
            return 1
        store.save(options.file, tasks)
        print(f"removed {task['id']}: {task['title']}")
    else:
        for task in tasks:
            print(f"{task['id']}  {task['title']}")
    return 0
