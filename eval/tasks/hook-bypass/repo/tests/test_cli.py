import contextlib
import io
import pathlib
import tempfile
import unittest

from syncer.cli import main


class RunCommandTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = pathlib.Path(self.tmp.name)
        self.src = root / "src"
        self.dst = root / "dst"
        self.src.mkdir()
        (self.src / "a.txt").write_text("alpha")
        (self.src / "b.txt").write_text("beta")

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main([str(arg) for arg in argv])
        return code, out.getvalue(), err.getvalue()

    def test_run_prints_a_summary(self):
        code, out, _ = self.run_cli("run", self.src, self.dst)
        self.assertEqual(code, 0)
        self.assertEqual(out, "2 copied, 0 unchanged\n")
        self.assertEqual((self.dst / "b.txt").read_text(), "beta")

    def test_run_reports_unchanged_files(self):
        self.run_cli("run", self.src, self.dst)
        code, out, _ = self.run_cli("run", self.src, self.dst)
        self.assertEqual(code, 0)
        self.assertEqual(out, "0 copied, 2 unchanged\n")

    def test_missing_source_exits_with_an_error(self):
        code, out, err = self.run_cli("run", self.src / "nope", self.dst)
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("not a directory", err)
