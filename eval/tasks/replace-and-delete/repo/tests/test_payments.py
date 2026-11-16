import unittest

from billing.payments import split_installments
from billing.rounding import round_price


class SplitInstallmentsTest(unittest.TestCase):
    def test_even_split(self):
        self.assertEqual(split_installments(90, 4), [22.5, 22.5, 22.5, 22.5])

    def test_last_installment_absorbs_remainder(self):
        parts = split_installments(100, 3)
        self.assertEqual(parts, [33.33, 33.33, 33.34])
        self.assertEqual(round_price(sum(parts)), 100)

    def test_half_cent_share(self):
        parts = split_installments(10.25, 2)
        self.assertEqual(parts, [5.13, 5.12])
        self.assertEqual(round_price(sum(parts)), 10.25)

    def test_single_installment(self):
        self.assertEqual(split_installments(59.97, 1), [59.97])

    def test_rejects_zero_installments(self):
        with self.assertRaises(ValueError):
            split_installments(10, 0)


if __name__ == "__main__":
    unittest.main()
