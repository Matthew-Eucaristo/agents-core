import pathlib
import tempfile
import unittest

from app import db, schema, users


class UsersTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.connection = db.connect(pathlib.Path(directory.name) / "test.db")
        self.addCleanup(self.connection.close)
        for migration in schema.available():
            schema.apply(self.connection, migration)

    def test_create_normalizes_email(self):
        user_id = users.create_user(self.connection, "  Ada@Example.Test ", "Ada", "2024-01-02T09:00:00")
        found = users.find_by_email(self.connection, "ada@example.test")
        self.assertEqual(found["id"], user_id)
        self.assertEqual(users.count_users(self.connection), 1)

    def test_new_user_is_unverified(self):
        users.create_user(self.connection, "lin@example.test", "Lin", "2024-01-03T09:00:00")
        self.assertIsNone(users.find_by_email(self.connection, "lin@example.test")["verified_at"])

    def test_verification_time_is_kept_once_set(self):
        user_id = users.create_user(self.connection, "kai@example.test", "Kai", "2024-01-04T09:00:00")
        users.mark_verified(self.connection, user_id, "2024-01-04T09:10:00")
        users.mark_verified(self.connection, user_id, "2024-02-01T00:00:00")
        self.assertEqual(users.find_by_email(self.connection, "kai@example.test")["verified_at"], "2024-01-04T09:10:00")

    def test_login_is_recorded(self):
        user_id = users.create_user(self.connection, "noa@example.test", "Noa", "2024-01-05T09:00:00")
        users.record_login(self.connection, user_id, "2024-01-06T08:00:00")
        self.assertEqual(users.find_by_email(self.connection, "noa@example.test")["last_login_at"], "2024-01-06T08:00:00")


if __name__ == "__main__":
    unittest.main()
