import tempfile
import unittest
from pathlib import Path

from churnboard import store


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.connection = store.connect(Path(self.tmp.name) / "nested" / "customers.db")
        self.addCleanup(self.connection.close)

    def test_notes_come_back_in_order(self):
        store.add_note(self.connection, "C9", "lee", "Second call", "2024-03-02T09:00:00")
        store.add_note(self.connection, "C9", "lee", "Intro call", "2024-03-01T09:00:00")
        store.add_note(self.connection, "C8", "sam", "Other account", "2024-03-01T12:00:00")
        bodies = [body for _, _, body in store.notes_for(self.connection, "C9")]
        self.assertEqual(bodies, ["Intro call", "Second call"])
        self.assertEqual(store.note_counts(self.connection), {"C9": 2, "C8": 1})

    def test_assigning_an_owner_twice_keeps_the_latest(self):
        store.assign_owner(self.connection, "C9", "Lee Okafor", "mid-market", "2025-01-31")
        store.assign_owner(self.connection, "C9", "Sam Rivera", "enterprise")
        self.assertEqual(store.owners(self.connection), {"C9": "Sam Rivera"})
