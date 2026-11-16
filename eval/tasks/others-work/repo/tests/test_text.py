import unittest

from utils import text


class SlugifyTest(unittest.TestCase):
    def test_lowercases_and_joins(self):
        self.assertEqual(text.slugify("Regional Sales (Q3)"), "regional-sales-q3")


class TruncateTest(unittest.TestCase):
    def test_short_text_unchanged(self):
        self.assertEqual(text.truncate("north", 10), "north")

    def test_long_text_gets_ellipsis(self):
        self.assertEqual(text.truncate("north and south", 10), "north a...")

    def test_tiny_width(self):
        self.assertEqual(text.truncate("north", 2), "no")


if __name__ == "__main__":
    unittest.main()
