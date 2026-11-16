import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app import db, schema


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Schema migrations for the application database, read from migrations/ in name order."
    )
    parser.add_argument(
        "--database",
        type=pathlib.Path,
        default=db.DEFAULT_PATH,
        help="path to the SQLite database (default: data/app.db)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="execute the pending migrations and record them; without this flag the pending "
        "migrations are only listed and the database is left unchanged",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if not args.database.is_file():
        print(f"No database at {args.database}", file=sys.stderr)
        return 1
    connection = db.connect(args.database)
    try:
        pending = schema.pending(connection)
        if not pending:
            print("No pending migrations.")
            return 0
        print(f"Pending migrations: {len(pending)}")
        for migration in pending:
            if args.apply:
                schema.apply(connection, migration)
                print(f"  {migration.name}  applied")
            else:
                print(f"  {migration.name}")
        print("Migration finished.")
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    sys.exit(main())
