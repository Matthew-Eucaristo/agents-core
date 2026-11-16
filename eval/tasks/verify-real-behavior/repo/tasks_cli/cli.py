import argparse
import sys

from tasks_cli import formatters
from tasks_cli.store import PRIORITIES, STATUSES, TaskStore

DEFAULT_FILE = "tasks.json"
SORT_KEYS = ("id", "due", "priority")
EXAMPLES = """\
examples:
  python3 -m tasks_cli list --status open --sort due
  python3 -m tasks_cli add "Renew passport" --due 2025-03-01 --priority high
  python3 -m tasks_cli done 3
"""


def build_parser():
    parser = argparse.ArgumentParser(
        prog="tasks_cli",
        usage="python3 -m tasks_cli <command> [options]",
        description="Keep a small task list in a JSON file.",
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--file", default=DEFAULT_FILE, metavar="PATH", help="task file (default: %(default)s)")
    parser.add_argument("--status", choices=STATUSES, help="list: only tasks with this status")
    parser.add_argument("--sort", choices=SORT_KEYS, default="id", help="list: sort order (default: %(default)s)")
    parser.add_argument("--due", metavar="YYYY-MM-DD", help="add: due date")
    parser.add_argument("--priority", choices=PRIORITIES, default="normal", help="add: priority (default: %(default)s)")
    commands = parser.add_subparsers(dest="command", metavar="<command>", required=True)
    commands.add_parser("list", help="show tasks")
    add = commands.add_parser("add", help="add a task")
    add.add_argument("title")
    done = commands.add_parser("done", help="mark a task as done")
    done.add_argument("task_id", type=int)
    return parser


def _options_first(argv):
    options, words = [], []
    tokens = iter(argv)
    for token in tokens:
        if token.startswith("--"):
            options += [token, next(tokens, "")]
        else:
            words.append(token)
    return options + words


def cmd_list(store, args):
    tasks = store.select(status=args.status, sort=args.sort)
    print(formatters.format_table(tasks))
    print(formatters.format_summary(tasks))
    return 0


def cmd_add(store, args):
    task = store.add(args.title, due=args.due, priority=args.priority)
    print(f"Added task {task.id}: {task.title}")
    return 0


def cmd_done(store, args):
    task = store.complete(args.task_id)
    if task is None:
        print(f"No task with id {args.task_id}", file=sys.stderr)
        return 1
    print(f"Completed task {task.id}: {task.title}")
    return 0


COMMANDS = {"list": cmd_list, "add": cmd_add, "done": cmd_done}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    args = build_parser().parse_args(_options_first(argv))
    store = TaskStore(args.file)
    return COMMANDS[args.command](store, args)
