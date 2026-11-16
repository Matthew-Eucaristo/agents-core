import sqlite3

from server_only.secrets import DATABASE_PATH, DISPLAY_NAME_MAX_LENGTH
from shared.limits import BIO_MAX_LENGTH

SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    user_id INTEGER PRIMARY KEY,
    display_name TEXT NOT NULL,
    bio TEXT NOT NULL DEFAULT ''
)
"""


def connect(path=DATABASE_PATH):
    connection = sqlite3.connect(path)
    connection.execute(SCHEMA)
    return connection


def save_profile(connection, user_id, display_name, bio=""):
    if not display_name or len(display_name) > DISPLAY_NAME_MAX_LENGTH:
        raise ValueError("invalid display name")
    if len(bio) > BIO_MAX_LENGTH:
        raise ValueError("bio is too long")
    connection.execute(
        "INSERT INTO profiles (user_id, display_name, bio) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET display_name = excluded.display_name, bio = excluded.bio",
        (user_id, display_name, bio),
    )
    connection.commit()


def load_profile(connection, user_id):
    row = connection.execute(
        "SELECT display_name, bio FROM profiles WHERE user_id = ?", (user_id,)
    ).fetchone()
    if row is None:
        return None
    return {"display_name": row[0], "bio": row[1]}
