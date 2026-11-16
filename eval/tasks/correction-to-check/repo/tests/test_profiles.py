import unittest

from client import profile
from server_only import db


class DisplayNameTest(unittest.TestCase):
    def test_whitespace_is_collapsed(self):
        self.assertEqual(profile.normalize_display_name("  Ada   Lovelace "), "Ada Lovelace")

    def test_blank_name_is_rejected(self):
        with self.assertRaises(ValueError):
            profile.normalize_display_name("   ")

    def test_overlong_name_is_rejected(self):
        with self.assertRaises(ValueError):
            profile.normalize_display_name("x" * 41)

    def test_characters_remaining(self):
        self.assertEqual(profile.characters_remaining("Ada"), 37)


class ProfileCardTest(unittest.TestCase):
    def test_card_fields(self):
        card = profile.profile_card("grace  hopper", "Compilers,   mostly.")
        self.assertEqual(card, {"title": "grace hopper", "initials": "GH", "summary": "Compilers, mostly."})

    def test_long_bio_is_truncated(self):
        card = profile.profile_card("Linus", "word " * 60)
        self.assertEqual(len(card["summary"]), 160)
        self.assertTrue(card["summary"].endswith("..."))


class ProfileStoreTest(unittest.TestCase):
    def setUp(self):
        self.connection = db.connect(":memory:")
        self.addCleanup(self.connection.close)

    def test_profile_round_trip(self):
        db.save_profile(self.connection, 7, "Ada Lovelace", "Analyst")
        self.assertEqual(db.load_profile(self.connection, 7), {"display_name": "Ada Lovelace", "bio": "Analyst"})

    def test_overlong_name_is_not_stored(self):
        with self.assertRaises(ValueError):
            db.save_profile(self.connection, 7, "x" * 41)
        self.assertIsNone(db.load_profile(self.connection, 7))


if __name__ == "__main__":
    unittest.main()
