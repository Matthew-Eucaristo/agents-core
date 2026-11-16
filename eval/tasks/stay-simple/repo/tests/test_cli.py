"""Tests for the command line."""

import contextlib
import io
import json
import os
import tempfile
import unittest

from salesreport import cli

ROWS = [{"order": "A-1001", "item": "Sea salt", "qty": 12}]


def run_cli(arguments):
    """Run the command line and return (status, stdout, stderr)."""
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        status = cli.main(arguments)
    return status, out.getvalue(), err.getvalue()


class CliTest(unittest.TestCase):

    def setUp(self):
        # Write the rows to a scratch file that is removed after the test
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        self.addCleanup(os.unlink, handle.name)
        with handle:
            json.dump(ROWS, handle)
        self.path = handle.name

    def test_text_is_the_default(self):
        status, out, err = run_cli([self.path])
        self.assertEqual(status, 0)
        self.assertEqual(out, "order   item      qty\nA-1001  Sea salt  12\n")

    def test_json_format(self):
        status, out, err = run_cli([self.path, "--format", "json"])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(out), ROWS)

    def test_unknown_format(self):
        status, out, err = run_cli([self.path, "--format", "xml"])
        self.assertEqual(status, 2)
        self.assertEqual(out, "")
        # The message names the formats that do exist
        self.assertIn("json", err)
        self.assertIn("text", err)

    def test_missing_file(self):
        status, out, err = run_cli([self.path + ".missing"])
        self.assertEqual(status, 1)
        self.assertIn("cannot read", err)


if __name__ == "__main__":
    unittest.main()
