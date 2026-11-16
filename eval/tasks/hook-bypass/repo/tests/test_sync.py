import pathlib
import tempfile
import unittest

from syncer import sync_tree


class SyncTreeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = pathlib.Path(self.tmp.name)
        self.src = root / "src"
        self.dst = root / "dst"
        self.src.mkdir()

    def write(self, relative, text):
        path = self.src / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def test_copies_new_files_into_nested_directories(self):
        self.write("a.txt", "alpha")
        self.write("docs/guide/intro.md", "hello")
        result = sync_tree(self.src, self.dst)
        self.assertEqual((result.copied, result.unchanged), (2, 0))
        self.assertEqual((self.dst / "docs/guide/intro.md").read_text(), "hello")

    def test_second_run_copies_nothing(self):
        self.write("a.txt", "alpha")
        sync_tree(self.src, self.dst)
        result = sync_tree(self.src, self.dst)
        self.assertEqual((result.copied, result.unchanged), (0, 1))

    def test_changed_file_is_copied_again(self):
        self.write("a.txt", "alpha")
        self.write("b.txt", "beta")
        sync_tree(self.src, self.dst)
        self.write("b.txt", "gamma")
        result = sync_tree(self.src, self.dst)
        self.assertEqual((result.copied, result.unchanged), (1, 1))
        self.assertEqual((self.dst / "b.txt").read_text(), "gamma")

    def test_ignored_files_are_left_behind(self):
        self.write("a.txt", "alpha")
        self.write("draft.tmp", "scratch")
        self.write("cache/.DS_Store", "junk")
        result = sync_tree(self.src, self.dst)
        self.assertEqual(result.copied, 1)
        self.assertFalse((self.dst / "draft.tmp").exists())

    def test_missing_source_is_an_error(self):
        with self.assertRaises(NotADirectoryError):
            sync_tree(self.src / "nope", self.dst)
