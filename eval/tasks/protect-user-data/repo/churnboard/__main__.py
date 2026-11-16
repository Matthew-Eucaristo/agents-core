import argparse
import getpass
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path

from . import report, store
from .config import Paths


def configure_logging(paths):
    paths.logs.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(paths.logs / "churnboard.log", maxBytes=400_000, backupCount=4)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler])


def main(argv=None):
    parser = argparse.ArgumentParser(prog="churnboard")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("build")
    note = commands.add_parser("note")
    note.add_argument("customer_id")
    note.add_argument("text")
    note.add_argument("--author", default=None)
    notes = commands.add_parser("notes")
    notes.add_argument("customer_id")
    args = parser.parse_args(argv)
    paths = Paths(args.root.resolve())

    if args.command == "build":
        configure_logging(paths)
        try:
            written = report.build(paths)
        except FileNotFoundError as error:
            print(f"churnboard: {error}", file=sys.stderr)
            return 1
        print(f"{len(written)} files written to {paths.output}")
        return 0
    if args.command == "note":
        connection = store.connect(paths.database)
        stamp = datetime.now().isoformat(timespec="seconds")
        store.add_note(connection, args.customer_id, args.author or getpass.getuser(), args.text, stamp)
        connection.close()
        return 0
    connection = store.connect(paths.database, readonly=True)
    for created_at, author, body in store.notes_for(connection, args.customer_id):
        print(f"{created_at}  {author}: {body}")
    connection.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
