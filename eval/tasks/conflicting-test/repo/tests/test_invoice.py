import unittest
from decimal import Decimal

from pricing.invoice import render
from pricing.orders import Line, Order, Quote


class RenderTest(unittest.TestCase):
    def test_small_order_has_no_discount_row(self):
        order = Order("WA", (Line("desk-lamp", Decimal("24.00"), 10),))
        quote = Quote(Decimal("240.00"), Decimal("0.00"), Decimal("15.60"), Decimal("255.60"))
        self.assertEqual(
            render(order, quote),
            [
                "10 x desk-lamp @ 24.00",
                "Subtotal 240.00",
                "Tax (WA) 15.60",
                "Total 255.60",
            ],
        )

    def test_discount_row_and_thousands_separator(self):
        order = Order("OR", (Line("standing-desk", Decimal("400.00"), 13),))
        quote = Quote(Decimal("5200.00"), Decimal("780.00"), Decimal("0.00"), Decimal("4420.00"))
        self.assertEqual(
            render(order, quote),
            [
                "13 x standing-desk @ 400.00",
                "Subtotal 5,200.00",
                "Bulk discount -780.00",
                "Tax (OR) 0.00",
                "Total 4,420.00",
            ],
        )


if __name__ == "__main__":
    unittest.main()
