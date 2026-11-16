import unittest
from decimal import Decimal

from billing.rounding import round_money


class RoundingTest(unittest.TestCase):
    def test_rounds_to_two_places(self):
        self.assertEqual(round_money(3.14159), Decimal("3.14"))
        self.assertEqual(round_money(7.999), Decimal("8.00"))

    def test_half_cent_rounds_to_even(self):
        self.assertEqual(round_money(2.125), Decimal("2.12"))
        self.assertEqual(round_money(0.375), Decimal("0.38"))
        self.assertEqual(round_money(Decimal("2.675")), Decimal("2.68"))
        self.assertEqual(round_money(Decimal("2.665")), Decimal("2.66"))

    def test_whole_amounts_are_unchanged(self):
        self.assertEqual(round_money(12), Decimal("12.00"))

    def test_returns_decimal_with_two_places(self):
        result = round_money(12)
        self.assertIsInstance(result, Decimal)
        self.assertEqual(str(result), "12.00")


if __name__ == "__main__":
    unittest.main()
