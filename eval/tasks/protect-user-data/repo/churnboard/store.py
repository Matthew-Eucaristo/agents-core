import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    customer_id TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    tier TEXT NOT NULL,
    renewal_date TEXT
);
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY,
    customer_id TEXT NOT NULL,
    author TEXT NOT NULL,
    created_at TEXT NOT NULL,
    body TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS notes_by_customer ON notes (customer_id);
"""


def connect(path, readonly=False):
    if readonly:
        return sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.executescript(SCHEMA)
    return connection


def assign_owner(connection, customer_id, owner, tier, renewal_date=None):
    connection.execute(
        "INSERT INTO accounts (customer_id, owner, tier, renewal_date) VALUES (?, ?, ?, ?) "
        "ON CONFLICT (customer_id) DO UPDATE SET owner = excluded.owner, tier = excluded.tier, "
        "renewal_date = excluded.renewal_date",
        (customer_id, owner, tier, renewal_date),
    )
    connection.commit()


def add_note(connection, customer_id, author, body, created_at):
    cursor = connection.execute(
        "INSERT INTO notes (customer_id, author, created_at, body) VALUES (?, ?, ?, ?)",
        (customer_id, author, created_at, body),
    )
    connection.commit()
    return cursor.lastrowid


def notes_for(connection, customer_id):
    return connection.execute(
        "SELECT created_at, author, body FROM notes WHERE customer_id = ? ORDER BY created_at, id",
        (customer_id,),
    ).fetchall()


def owners(connection):
    return dict(connection.execute("SELECT customer_id, owner FROM accounts"))


def note_counts(connection):
    return dict(connection.execute("SELECT customer_id, COUNT(*) FROM notes GROUP BY customer_id"))
