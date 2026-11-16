import unittest
from datetime import date
from decimal import Decimal

from notifier import Invoice
from notifier.config import load_settings
from notifier.message import build_invoice_message


class BuildInvoiceMessageTest(unittest.TestCase):
    def setUp(self):
        self.settings = load_settings()
        self.invoice = Invoice("INV-1042", "Contoso GmbH", Decimal("1250"), "USD", date(2026, 1, 31))

    def test_headers(self):
        message = build_invoice_message(self.invoice, self.settings, "ap@contoso.example")
        self.assertEqual(message["To"], "ap@contoso.example")
        self.assertEqual(message["From"], "Northwind Billing <billing@northwind.example>")
        self.assertEqual(message["Subject"], "Invoice INV-1042 from Northwind Billing")

    def test_body_lists_amount_and_due_date(self):
        message = build_invoice_message(self.invoice, self.settings, "ap@contoso.example")
        body = message.get_content()
        self.assertIn("Dear Contoso GmbH,", body)
        self.assertIn("Amount due: USD 1,250.00", body)
        self.assertIn("Due date:   2026-01-31", body)


if __name__ == "__main__":
    unittest.main()
