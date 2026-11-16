import os
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    due_date TEXT NOT NULL,
    paid_on TEXT
);
CREATE INDEX IF NOT EXISTS invoices_customer ON invoices (customer);
"""

_path = os.environ.get("INVOICING_DB", "invoicing.db")
_connection = None


def configure(path):
    global _path
    close()
    _path = str(path)


def get_connection():
    global _connection
    if _connection is None:
        _connection = sqlite3.connect(_path)
        _connection.row_factory = sqlite3.Row
    return _connection


def init_schema():
    connection = get_connection()
    connection.executescript(SCHEMA)
    connection.commit()


def close():
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None
