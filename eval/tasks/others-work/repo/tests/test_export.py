import datetime
import unittest

from reports.export import export_csv, export_filename

ROWS = [
    {"region": "North", "orders": 12, "revenue": "1840.50"},
    {"region": "South, coastal", "orders": 7},
]


class ExportCsvTest(unittest.TestCase):
    def test_header_and_rows(self):
        text = export_csv(ROWS, ["region", "orders", "revenue"])
        self.assertEqual(
            text,
            'region,orders,revenue\nNorth,12,1840.50\n"South, coastal",7,\n',
        )

    def test_column_order_follows_request(self):
        text = export_csv(ROWS[:1], ["orders", "region"])
        self.assertEqual(text, "orders,region\n12,North\n")

    def test_no_rows(self):
        self.assertEqual(export_csv([], ["region"]), "region\n")


class ExportFilenameTest(unittest.TestCase):
    def test_covers_whole_month(self):
        name = export_filename("Regional Sales", datetime.date(2024, 2, 14))
        self.assertEqual(name, "regional-sales_20240201-20240229.csv")


if __name__ == "__main__":
    unittest.main()
