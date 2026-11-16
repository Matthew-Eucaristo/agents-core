import io
import tempfile
import unittest
from pathlib import Path

from dropline.cli import main


class CliTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.spool = Path(scratch.name) / "spool"
        self.dest = Path(scratch.name) / "inbox"
        self.spool.mkdir()
        (self.spool / "notes.txt").write_bytes(b"hello\n")
        (self.spool / "photo.jpg").write_bytes(b"\xff\xd8\xff\xe0" * 8)

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        code = main([str(part) for part in argv], stdout=out, stderr=err)
        return code, out.getvalue(), err.getvalue()

    def test_index_reports_the_file_count(self):
        code, out, err = self.run_cli("index", self.spool)
        self.assertEqual((code, out, err), (0, "indexed 2 files\n", ""))

    def test_list_shows_sizes_and_names(self):
        self.run_cli("index", self.spool)
        code, out, _ = self.run_cli("list", self.spool)
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), ["         6  notes.txt", "        32  photo.jpg"])

    def test_fetch_prints_each_received_path(self):
        self.run_cli("index", self.spool)
        code, out, err = self.run_cli("fetch", self.spool, "notes.txt", "photo.jpg", "--to", self.dest)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(
            out.splitlines(),
            [f"received {self.dest / 'notes.txt'}", f"received {self.dest / 'photo.jpg'}"],
        )

    def test_errors_go_to_stderr_with_exit_code(self):
        self.run_cli("index", self.spool)
        code, out, err = self.run_cli("fetch", self.spool, "missing.bin", "--to", self.dest)
        self.assertEqual((code, out), (1, ""))
        self.assertEqual(err, "error: 'missing.bin' is not listed in the manifest\n")

    def test_missing_manifest_is_an_error(self):
        code, _, err = self.run_cli("list", self.spool)
        self.assertEqual(code, 1)
        self.assertTrue(err.startswith("error: Could not read manifest at "))


if __name__ == "__main__":
    unittest.main()
