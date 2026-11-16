import pathlib
import tempfile
import unittest

from app import db, schema


class SchemaTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.connection = db.connect(pathlib.Path(directory.name) / "test.db")
        self.addCleanup(self.connection.close)

    def columns(self, table):
        return [row["name"] for row in self.connection.execute(f"PRAGMA table_info({table})")]

    def test_new_database_has_every_migration_pending(self):
        self.assertEqual(schema.pending(self.connection), schema.available())

    def test_applied_migration_is_no_longer_pending(self):
        first, *rest = schema.available()
        schema.apply(self.connection, first)
        self.assertEqual(schema.pending(self.connection), rest)
        self.assertIn("email", self.columns("users"))

    def test_failed_migration_leaves_no_trace(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "0001_broken.sql"
            path.write_text("CREATE TABLE notes (id INTEGER PRIMARY KEY);\nINSERT INTO missing VALUES (1);\n")
            with self.assertRaises(Exception):
                schema.apply(self.connection, schema.Migration(path.stem, path))
        self.assertEqual(schema.applied(self.connection), set())
        self.assertEqual(self.columns("notes"), [])

    def test_email_verified_follows_verified_at(self):
        *earlier, last = schema.available()
        for migration in earlier:
            schema.apply(self.connection, migration)
        self.connection.executemany(
            "INSERT INTO users (email, display_name, created_at, verified_at) VALUES (?, ?, ?, ?)",
            [
                ("ada@example.test", "Ada", "2024-01-02T09:00:00", "2024-01-02T09:05:00"),
                ("lin@example.test", "Lin", "2024-01-03T09:00:00", None),
            ],
        )
        self.connection.commit()
        schema.apply(self.connection, last)
        rows = self.connection.execute("SELECT email, email_verified FROM users ORDER BY id").fetchall()
        self.assertEqual([tuple(row) for row in rows], [("ada@example.test", 1), ("lin@example.test", 0)])


if __name__ == "__main__":
    unittest.main()
