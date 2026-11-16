import datetime
import pathlib
import tempfile
import unittest

import services
from storage import database


class BillingTest(unittest.TestCase):
    def setUp(self):
        workdir = tempfile.TemporaryDirectory()
        self.addCleanup(workdir.cleanup)
        database.configure(pathlib.Path(workdir.name) / "invoicing.db")
        self.addCleanup(database.close)
        database.init_schema()
        self.today = datetime.date(2024, 5, 20)

    def test_create_invoice_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            services.create_invoice("Acme", 0, self.today)
        with self.assertRaises(ValueError):
            services.create_invoice("  ", 1200, self.today)

    def test_status_follows_due_date_and_payment(self):
        late = services.create_invoice("Acme", 1200, datetime.date(2024, 5, 19))
        due_today = services.create_invoice("Acme", 800, self.today)
        settled = services.create_invoice("Birch", 500, datetime.date(2024, 5, 1))
        services.record_payment(settled, datetime.date(2024, 5, 10))
        self.assertEqual(services.invoice_status(late, self.today), "overdue")
        self.assertEqual(services.invoice_status(due_today, self.today), "open")
        self.assertEqual(services.invoice_status(settled, self.today), "paid")

    def test_record_payment_checks_the_invoice(self):
        invoice_id = services.create_invoice("Acme", 1200, self.today)
        services.record_payment(invoice_id, self.today)
        with self.assertRaises(ValueError):
            services.record_payment(invoice_id, self.today)
        with self.assertRaises(services.InvoiceNotFound):
            services.record_payment(invoice_id + 1, self.today)

    def test_totals_only_include_unpaid_invoices(self):
        services.create_invoice("Acme", 1200, self.today)
        services.create_invoice("Birch", 300, self.today)
        paid = services.create_invoice("Acme", 500, self.today)
        services.record_payment(paid, self.today)
        self.assertEqual(services.outstanding_total(), 1500)
        self.assertEqual(services.customer_balance("Acme"), 1200)
        self.assertEqual(services.customer_balance("Cedar"), 0)


if __name__ == "__main__":
    unittest.main()
