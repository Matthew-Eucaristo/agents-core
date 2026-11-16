import unittest
from decimal import Decimal

from billing.payments import split_installments


def amounts(*values):
    return [Decimal(value) for value in values]


class SplitInstallmentsTest(unittest.TestCase):
    def test_even_split(self):
        self.assertEqual(split_installments(90, 4), amounts("22.50", "22.50", "22.50", "22.50"))

    def test_last_installment_absorbs_remainder(self):
        parts = split_installments(100, 3)
        self.assertEqual(parts, amounts("33.33", "33.33", "33.34"))
        self.assertEqual(sum(parts), 100)

    def test_half_cent_share(self):
        parts = split_installments(10.25, 2)
        self.assertEqual(parts, amounts("5.12", "5.13"))
        self.assertEqual(sum(parts), Decimal("10.25"))

    def test_single_installment(self):
        self.assertEqual(split_installments(59.97, 1), amounts("59.97"))

    def test_rejects_zero_installments(self):
        with self.assertRaises(ValueError):
            split_installments(10, 0)


if __name__ == "__main__":
    unittest.main()
