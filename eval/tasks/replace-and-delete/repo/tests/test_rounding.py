import unittest

from billing.rounding import round_price


class RoundingTest(unittest.TestCase):
    def test_rounds_to_two_places(self):
        self.assertEqual(round_price(3.14159), 3.14)
        self.assertEqual(round_price(7.999), 8.0)

    def test_half_cent_rounds_up(self):
        self.assertEqual(round_price(2.125), 2.13)
        self.assertEqual(round_price(0.375), 0.38)

    def test_whole_amounts_are_unchanged(self):
        self.assertEqual(round_price(12), 12.0)


if __name__ == "__main__":
    unittest.main()
