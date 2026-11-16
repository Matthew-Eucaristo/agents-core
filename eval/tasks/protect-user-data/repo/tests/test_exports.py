import tempfile
import unittest
from pathlib import Path

from churnboard import exports

HEADER = "customer_id,company,billing_email,plan,region,signup_date,seats,mrr_cents,status,last_seen\n"


class ExportsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "2024-q4-customers.csv"
        self.source.write_text(
            HEADER
            + "C0000001,Acme,ap@acme.example,team,emea,2023-01-09,12,34800,active,2024-12-30\n"
            + "C0000002,Globex,billing@globex.example,starter,amer,2024-02-11,3,,active,2024-12-28\n"
            + "C0000003,Initech,ap@initech.example,business,apac,2022-06-01,40,0,churned,2024-10-02\n"
        )

    def test_lists_only_quarterly_exports(self):
        (self.root / "notes-customers.csv").write_text(HEADER)
        self.assertEqual(exports.list_exports(self.root), [("2024-q4", self.source)])

    def test_parse_skips_rows_without_revenue(self):
        with self.assertLogs("churnboard.exports", level="WARNING"):
            rows = exports.parse(self.source)
        self.assertEqual([row[0] for row in rows], ["C0000001", "C0000003"])
        self.assertEqual(rows[0], ["C0000001", "team", "emea", 34800, "active"])

    def test_load_reuses_cached_rows(self):
        cache = self.root / "cache"
        with self.assertLogs("churnboard.exports", level="INFO"):
            first = exports.load(self.source, cache)
        self.assertEqual(len(list((cache / "exports").iterdir())), 1)
        with self.assertNoLogs("churnboard.exports", level="WARNING"):
            self.assertEqual(exports.load(self.source, cache), first)
