import contextlib
import io
import os
import tempfile
import unittest

from todo import cli


class CliTest(unittest.TestCase):

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = os.path.join(folder.name, "todo.json")

    def run_cli(self, *arguments):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = cli.main(["--file", self.path, *arguments])
        return status, out.getvalue(), err.getvalue()

    def test_add_then_list(self):
        self.assertEqual(self.run_cli("add", "buy milk")[0], 0)
        self.assertEqual(self.run_cli("add", "call Ana")[0], 0)
        self.assertEqual(self.run_cli("list"), (0, "1  buy milk\n2  call Ana\n", ""))

    def test_empty_title(self):
        status, out, err = self.run_cli("add", "   ")
        self.assertEqual(status, 1)
        self.assertIn("empty", err)
        self.assertEqual(self.run_cli("list"), (0, "", ""))

    def test_list_without_file(self):
        self.assertEqual(self.run_cli("list"), (0, "", ""))

    def test_remove(self):
        for title in ("a", "b", "c"):
            self.run_cli("add", title)
        self.assertEqual(self.run_cli("remove", "2")[0], 0)
        self.assertEqual(self.run_cli("list"), (0, "1  a\n3  c\n", ""))


if __name__ == "__main__":
    unittest.main()
