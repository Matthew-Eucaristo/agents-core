import unittest
from decimal import Decimal

from pricing.discounts import apply_discount
from pricing.orders import Line, Order


def order(region, *lines):
    return Order(region, tuple(Line(sku, Decimal(price), quantity) for sku, price, quantity in lines))


class ApplyDiscountTest(unittest.TestCase):
    def test_order_under_500_has_no_discount(self):
        quote = apply_discount(order("OR", ("desk-lamp", "24.00", 20)))
        self.assertEqual(quote.subtotal, Decimal("480.00"))
        self.assertEqual(quote.discount, Decimal("0.00"))
        self.assertEqual(quote.total, Decimal("480.00"))

    def test_five_percent_from_500(self):
        quote = apply_discount(order("OR", ("desk-lamp", "25.00", 20)))
        self.assertEqual(quote.discount, Decimal("25.00"))
        self.assertEqual(quote.total, Decimal("475.00"))

    def test_ten_percent_from_2000(self):
        quote = apply_discount(order("OR", ("office-chair", "125.00", 16)))
        self.assertEqual(quote.discount, Decimal("200.00"))
        self.assertEqual(quote.total, Decimal("1800.00"))

    def test_fifteen_percent_from_5000(self):
        quote = apply_discount(order("OR", ("standing-desk", "400.00", 13)))
        self.assertEqual(quote.discount, Decimal("780.00"))
        self.assertEqual(quote.total, Decimal("4420.00"))

    def test_tier_uses_the_sum_of_all_lines(self):
        quote = apply_discount(order("OR", ("desk-lamp", "24.00", 10), ("office-chair", "125.00", 4)))
        self.assertEqual(quote.subtotal, Decimal("740.00"))
        self.assertEqual(quote.discount, Decimal("37.00"))
        self.assertEqual(quote.total, Decimal("703.00"))

    def test_discount_rounds_half_up(self):
        quote = apply_discount(order("OR", ("monitor-arm", "33.34", 15)))
        self.assertEqual(quote.discount, Decimal("25.01"))
        self.assertEqual(quote.total, Decimal("475.09"))

    def test_small_order_is_taxed(self):
        quote = apply_discount(order("WA", ("desk-lamp", "24.00", 10)))
        self.assertEqual(quote.discount, Decimal("0.00"))
        self.assertEqual(quote.tax, Decimal("15.60"))
        self.assertEqual(quote.total, Decimal("255.60"))

    def test_tax_rounds_half_up(self):
        quote = apply_discount(order("WA", ("cable-tray", "21.00", 1)))
        self.assertEqual(quote.tax, Decimal("1.37"))
        self.assertEqual(quote.total, Decimal("22.37"))

    def test_taxed_order_in_five_percent_tier(self):
        quote = apply_discount(order("PA", ("office-chair", "125.00", 8)))
        self.assertEqual(quote.total, Decimal("1007.00"))

    def test_taxed_bulk_order(self):
        quote = apply_discount(order("IN", ("chair-mat", "25.00", 76)))
        self.assertEqual(quote.total, Decimal("1829.70"))


if __name__ == "__main__":
    unittest.main()
