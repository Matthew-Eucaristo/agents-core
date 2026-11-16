import unittest
from decimal import Decimal

from pricing.tax import rate_for, sales_tax


class TaxTest(unittest.TestCase):
    def test_rate_for_known_region(self):
        self.assertEqual(rate_for("TX"), Decimal("0.0625"))

    def test_region_without_sales_tax(self):
        self.assertEqual(sales_tax(Decimal("199.99"), "OR"), Decimal("0.00"))

    def test_unknown_region_is_rejected(self):
        with self.assertRaises(ValueError):
            rate_for("ZZ")

    def test_sales_tax_rounds_to_the_cent(self):
        self.assertEqual(sales_tax(Decimal("19.99"), "CA"), Decimal("1.45"))


if __name__ == "__main__":
    unittest.main()
