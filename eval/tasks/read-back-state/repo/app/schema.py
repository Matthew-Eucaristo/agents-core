import dataclasses
import datetime
import pathlib

MIGRATIONS_DIR = pathlib.Path(__file__).resolve().parent.parent / "migrations"


@dataclasses.dataclass(frozen=True)
class Migration:
    name: str
    path: pathlib.Path


def available(directory=MIGRATIONS_DIR):
    return [Migration(path.stem, path) for path in sorted(pathlib.Path(directory).glob("*.sql"))]


def ensure_ledger(connection):
    connection.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
    )


def applied(connection):
    ensure_ledger(connection)
    return {row[0] for row in connection.execute("SELECT name FROM schema_migrations")}


def pending(connection, directory=MIGRATIONS_DIR):
    done = applied(connection)
    return [migration for migration in available(directory) if migration.name not in done]


def apply(connection, migration, applied_at=None):
    stamp = applied_at or datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    ensure_ledger(connection)
    try:
        connection.executescript(f"BEGIN;\n{migration.path.read_text()}")
        connection.execute(
            "INSERT INTO schema_migrations (name, applied_at) VALUES (?, ?)", (migration.name, stamp)
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
