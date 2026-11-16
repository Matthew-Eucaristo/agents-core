import contextlib
import io
import pathlib
import unittest

from billing.cli import main

ORDERS = pathlib.Path(__file__).resolve().parent.parent / "orders"


class CliTest(unittest.TestCase):
    def run_cli(self, name):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = main([str(ORDERS / name)])
        self.assertEqual(code, 0)
        return buffer.getvalue().splitlines()

    def test_prints_invoice_for_sample_order(self):
        lines = self.run_cli("harbor_street.json")
        self.assertEqual(
            lines,
            [
                "Invoice for Harbor Street Cafe",
                "Espresso beans 1kg               75.00",
                "Cane sugar per kg                 5.63",
                "Paper cups x50                   65.28",
                "Subtotal                        145.91",
                "Tax                              12.04",
                "Total                           157.95",
                "Installments: 52.65, 52.65, 52.65",
            ],
        )


if __name__ == "__main__":
    unittest.main()
