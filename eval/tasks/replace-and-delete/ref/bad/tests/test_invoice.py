import unittest

from billing.invoice import build_invoice, line_total
from billing.tax import tax_amount


class LineTotalTest(unittest.TestCase):
    def test_multiplies_price_by_quantity(self):
        self.assertEqual(line_total(19.99, 3), 59.97)

    def test_applies_discount_percent(self):
        self.assertEqual(line_total(12.5, 3, 10), 33.75)
        self.assertEqual(line_total(80, 1, 12.5), 70.0)

    def test_fractional_quantity(self):
        self.assertEqual(line_total(4.5, 0.25), 1.12)


class BuildInvoiceTest(unittest.TestCase):
    def test_totals(self):
        order = {
            "customer": "Northside Bakery",
            "tax_rate": 0.0825,
            "items": [
                {"name": "Flour 25kg", "unit_price": 19.99, "quantity": 3},
                {"name": "Yeast 500g", "unit_price": 4.5, "quantity": 0.25},
            ],
        }
        invoice = build_invoice(order)
        self.assertEqual(invoice["lines"], [("Flour 25kg", 59.97), ("Yeast 500g", 1.12)])
        self.assertEqual(invoice["subtotal"], 61.09)
        self.assertEqual(invoice["tax"], 5.04)
        self.assertAlmostEqual(invoice["total"], 66.13, places=2)

    def test_missing_tax_rate_means_no_tax(self):
        order = {"customer": "Walk-in", "items": [{"name": "Gift card", "unit_price": 25, "quantity": 1}]}
        invoice = build_invoice(order)
        self.assertEqual(invoice["tax"], 0)
        self.assertEqual(invoice["total"], 25)


class TaxAmountTest(unittest.TestCase):
    def test_standard_rate(self):
        self.assertEqual(tax_amount(200, 0.07), 14.0)
        self.assertEqual(tax_amount(59.97, 0.0825), 4.95)

    def test_half_cent_of_tax(self):
        self.assertEqual(tax_amount(5.0, 0.125), 0.62)

    def test_zero_rate(self):
        self.assertEqual(tax_amount(120.0, 0), 0)


if __name__ == "__main__":
    unittest.main()
