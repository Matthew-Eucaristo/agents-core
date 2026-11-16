import datetime
import unittest

from utils import dates


class ParseDateTest(unittest.TestCase):
    def test_parses_iso_date(self):
        self.assertEqual(dates.parse_date(" 2024-03-09 "), datetime.date(2024, 3, 9))


class MonthBoundsTest(unittest.TestCase):
    def test_leap_february(self):
        first, last = dates.month_bounds(datetime.date(2024, 2, 14))
        self.assertEqual(first, datetime.date(2024, 2, 1))
        self.assertEqual(last, datetime.date(2024, 2, 29))


class AddMonthsTest(unittest.TestCase):
    def test_within_year(self):
        self.assertEqual(dates.add_months(datetime.date(2024, 3, 15), 2), datetime.date(2024, 5, 15))

    def test_clamps_to_month_end(self):
        self.assertEqual(dates.add_months(datetime.date(2024, 1, 31), 1), datetime.date(2024, 2, 29))

    def test_into_next_year(self):
        self.assertEqual(dates.add_months(datetime.date(2024, 11, 15), 3), datetime.date(2025, 2, 15))

    def test_lands_in_december(self):
        self.assertEqual(dates.add_months(datetime.date(2024, 11, 15), 1), datetime.date(2024, 12, 15))

    def test_back_into_previous_december(self):
        self.assertEqual(dates.add_months(datetime.date(2024, 2, 10), -2), datetime.date(2023, 12, 10))


class QuarterTest(unittest.TestCase):
    def test_quarters(self):
        self.assertEqual(dates.quarter(datetime.date(2024, 1, 1)), 1)
        self.assertEqual(dates.quarter(datetime.date(2024, 9, 30)), 3)
        self.assertEqual(dates.quarter(datetime.date(2024, 12, 31)), 4)


class BusinessDaysTest(unittest.TestCase):
    def test_skips_weekend(self):
        friday = datetime.date(2024, 5, 3)
        tuesday = datetime.date(2024, 5, 7)
        self.assertEqual(dates.business_days_between(friday, tuesday), 2)


if __name__ == "__main__":
    unittest.main()
