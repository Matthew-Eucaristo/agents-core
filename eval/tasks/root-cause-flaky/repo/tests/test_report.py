import pathlib
import unittest

from salesreport.orders import CsvOrderSource
from salesreport.service import ReportService

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "orders.csv"


class ReportServiceTest(unittest.TestCase):
    def setUp(self):
        self.service = ReportService(CsvOrderSource(FIXTURE))

    def test_summary(self):
        self.assertEqual(
            self.service.summary(),
            {
                "orders": 8,
                "units": 28,
                "revenue": 1595.0,
                "by_region": {"north": 570.5, "south": 275.0, "west": 749.5},
                "top_product": "office chair",
            },
        )

    def test_text_starts_with_order_count(self):
        self.assertEqual(self.service.text().splitlines()[0], "Orders:      8")


if __name__ == "__main__":
    unittest.main()
