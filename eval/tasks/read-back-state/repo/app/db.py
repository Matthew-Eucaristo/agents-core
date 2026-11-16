import pathlib
import sqlite3

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_PATH = ROOT / "data" / "app.db"


def connect(path=DEFAULT_PATH):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection
