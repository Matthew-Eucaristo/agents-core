"""Tests for the exporter functions."""

import json
import unittest

from salesreport import exporter

ROWS = [
    {"order": "A-1001", "item": "Rye flour", "qty": 4, "total": 71.6},
    {"order": "A-1002", "item": "Sea salt", "qty": 12, "total": 30.0},
]


class ToJsonTest(unittest.TestCase):

    def test_round_trip(self):
        # Parsing the output must give back the same rows
        self.assertEqual(json.loads(exporter.to_json(ROWS)), ROWS)

    def test_keeps_column_order(self):
        text = exporter.to_json(ROWS)
        # "order" comes first in the rows, so it must come first in the text
        self.assertLess(text.index('"order"'), text.index('"item"'))
        self.assertLess(text.index('"item"'), text.index('"qty"'))

    def test_ends_with_newline(self):
        self.assertTrue(exporter.to_json(ROWS).endswith("]\n"))

    def test_no_rows(self):
        self.assertEqual(exporter.to_json([]), "[]\n")


class ToCsvTest(unittest.TestCase):

    def test_header_and_rows(self):
        expected = "order,item,qty,total\nA-1001,Rye flour,4,71.6\nA-1002,Sea salt,12,30.0\n"
        self.assertEqual(exporter.to_csv(ROWS), expected)

    def test_quoting(self):
        rows = [{"item": "Rye flour, 25 kg", "note": 'Says "flaky"\nRing twice'}]
        expected = 'item,note\n"Rye flour, 25 kg","Says ""flaky""\nRing twice"\n'
        self.assertEqual(exporter.to_csv(rows), expected)

    def test_no_rows(self):
        self.assertEqual(exporter.to_csv([]), "")


class ToTextTest(unittest.TestCase):

    def test_table(self):
        expected = (
            "order   item       qty  total\n"
            "A-1001  Rye flour  4    71.6\n"
            "A-1002  Sea salt   12   30.0\n"
        )
        self.assertEqual(exporter.to_text(ROWS), expected)

    def test_missing_cell_is_blank(self):
        # The second row has no "qty", so that cell stays empty
        rows = [{"item": "Oat milk", "qty": 24}, {"item": "Sea salt"}]
        self.assertEqual(exporter.to_text(rows), "item      qty\nOat milk  24\nSea salt\n")

    def test_line_break_in_cell(self):
        rows = [{"note": "Back door.\nRing twice."}]
        self.assertEqual(exporter.to_text(rows), "note\nBack door. Ring twice.\n")

    def test_no_rows(self):
        self.assertEqual(exporter.to_text([]), "")


if __name__ == "__main__":
    unittest.main()
