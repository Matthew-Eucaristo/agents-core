import unittest
from decimal import Decimal

from billing.rounding import round_money, round_price


class RoundingTest(unittest.TestCase):
    def test_rounds_to_two_places(self):
        self.assertEqual(round_price(3.14159), 3.14)
        self.assertEqual(round_price(7.999), 8.0)

    def test_half_cent_rounds_to_even(self):
        self.assertEqual(round_price(2.125), 2.12)
        self.assertEqual(round_price(0.375), 0.38)

    def test_whole_amounts_are_unchanged(self):
        self.assertEqual(round_price(12), 12.0)


class RoundMoneyTest(unittest.TestCase):
    def test_returns_decimal(self):
        self.assertEqual(round_money(3.14159), Decimal("3.14"))
        self.assertIsInstance(round_money(12), Decimal)

    def test_half_cent_rounds_to_even(self):
        self.assertEqual(round_money(2.125), Decimal("2.12"))
        self.assertEqual(round_money(0.375), Decimal("0.38"))
        self.assertEqual(round_money(Decimal("2.675")), Decimal("2.68"))


if __name__ == "__main__":
    unittest.main()
