import unittest

from salesreport.orders import Order
from salesreport.summary import render, summarize


class SummarizeTest(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(
            summarize([]),
            {"orders": 0, "units": 0, "revenue": 0, "by_region": {}, "top_product": None},
        )

    def test_totals_per_region(self):
        orders = [
            Order("1", "north", "desk lamp", 2, 45.0),
            Order("2", "south", "notebook", 4, 6.25),
            Order("3", "north", "notebook", 1, 6.25),
        ]
        summary = summarize(orders)
        self.assertEqual(summary["orders"], 3)
        self.assertEqual(summary["units"], 7)
        self.assertEqual(summary["revenue"], 121.25)
        self.assertEqual(summary["by_region"], {"north": 96.25, "south": 25.0})
        self.assertEqual(summary["top_product"], "desk lamp")

    def test_top_product_tie_is_alphabetical(self):
        orders = [
            Order("1", "north", "notebook", 8, 6.25),
            Order("2", "north", "binder", 10, 5.0),
        ]
        self.assertEqual(summarize(orders)["top_product"], "binder")


class RenderTest(unittest.TestCase):
    def test_lists_each_region(self):
        text = render(summarize([Order("1", "west", "desk lamp", 2, 45.0)]))
        self.assertIn("Orders:      1", text)
        self.assertIn("Revenue:     90.00", text)
        self.assertIn("west", text.splitlines()[-1])


if __name__ == "__main__":
    unittest.main()
