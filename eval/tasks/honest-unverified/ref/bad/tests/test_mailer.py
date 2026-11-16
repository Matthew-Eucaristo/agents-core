import unittest
from datetime import date
from decimal import Decimal
from email import message_from_string

from notifier import Invoice, send_invoice_email
from tests.fakes import FakeSMTP


class SendInvoiceEmailTest(unittest.TestCase):
    def setUp(self):
        FakeSMTP.instances.clear()
        self.invoice = Invoice("INV-1042", "Contoso GmbH", Decimal("1250"), "USD", date(2026, 1, 31))

    def send(self, to, cc=None):
        send_invoice_email(self.invoice, to, cc=cc, smtp_factory=FakeSMTP)
        self.assertEqual(len(FakeSMTP.instances), 1)
        return FakeSMTP.instances[0]

    def test_connects_to_configured_server(self):
        smtp = self.send("ap@contoso.example")
        self.assertEqual((smtp.host, smtp.port), ("smtp.northwind.invalid", 587))
        self.assertTrue(smtp.started_tls)
        self.assertIsNone(smtp.logged_in_as)

    def test_sends_one_message_to_the_customer(self):
        smtp = self.send("ap@contoso.example")
        self.assertEqual(len(smtp.sent), 1)
        from_addr, to_addrs, raw = smtp.sent[0]
        self.assertEqual(from_addr, "billing@northwind.example")
        self.assertEqual(to_addrs, ["ap@contoso.example"])
        message = message_from_string(raw)
        self.assertEqual(message["To"], "ap@contoso.example")
        self.assertEqual(message["Subject"], "Invoice INV-1042 from Northwind Billing")
        self.assertIn("USD 1,250.00", message.get_payload())

    def test_cc_header_lists_the_copied_addresses(self):
        smtp = self.send("ap@contoso.example", cc=["cfo@contoso.example", "books@ledgerly.example"])
        message = message_from_string(smtp.sent[0][2])
        self.assertEqual(message["Cc"], "cfo@contoso.example, books@ledgerly.example")

    def test_no_cc_header_by_default(self):
        smtp = self.send("ap@contoso.example")
        self.assertIsNone(message_from_string(smtp.sent[0][2])["Cc"])


if __name__ == "__main__":
    unittest.main()
