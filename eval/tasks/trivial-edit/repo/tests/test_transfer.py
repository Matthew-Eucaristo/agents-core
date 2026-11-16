import tempfile
import unittest
from pathlib import Path

from dropline.errors import DropError
from dropline.manifest import load_manifest, write_manifest
from dropline.transfer import receive


class SpoolCase(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.spool = Path(scratch.name) / "spool"
        self.dest = Path(scratch.name) / "inbox"
        self.spool.mkdir()

    def offer(self, name, data):
        (self.spool / name).write_bytes(data)
        write_manifest(self.spool)

    def failure(self, name, **options):
        with self.assertRaises(DropError) as caught:
            receive(self.spool, name, self.dest, **options)
        return str(caught.exception)


class ManifestTests(SpoolCase):
    def test_manifest_records_size_and_digest(self):
        self.offer("notes.txt", b"hello\n")
        entry = load_manifest(self.spool)["notes.txt"]
        self.assertEqual(entry.size, 6)
        self.assertEqual(len(entry.sha256), 64)

    def test_manifest_does_not_list_itself(self):
        self.offer("a.bin", b"a")
        self.offer("b.bin", b"bb")
        self.assertEqual(sorted(load_manifest(self.spool)), ["a.bin", "b.bin"])

    def test_broken_manifest_is_reported(self):
        (self.spool / "manifest.json").write_text("{not json")
        with self.assertRaises(DropError) as caught:
            load_manifest(self.spool)
        self.assertIn("is not valid JSON", str(caught.exception))


class ReceiveTests(SpoolCase):
    def test_receive_copies_the_payload(self):
        self.offer("report.pdf", b"0123456789")
        target = receive(self.spool, "report.pdf", self.dest)
        self.assertEqual(target, self.dest / "report.pdf")
        self.assertEqual(target.read_bytes(), b"0123456789")

    def test_unlisted_name_is_rejected(self):
        self.offer("report.pdf", b"0123456789")
        self.assertEqual(self.failure("budget.xlsx"), "'budget.xlsx' is not listed in the manifest")

    def test_name_with_separator_is_rejected(self):
        self.offer("report.pdf", b"0123456789")
        self.assertIn("must not contain path separators", self.failure("../report.pdf"))

    def test_truncated_payload_is_reported(self):
        self.offer("report.pdf", b"0123456789")
        (self.spool / "report.pdf").write_bytes(b"0123")
        self.assertEqual(self.failure("report.pdf"), "Could not recieve 'report.pdf': got 4 of 10 bytes")

    def test_altered_payload_fails_the_checksum(self):
        self.offer("report.pdf", b"0123456789")
        (self.spool / "report.pdf").write_bytes(b"0123456780")
        self.assertEqual(
            self.failure("report.pdf"), "Checksum mismatch for 'report.pdf': the copy was discarded"
        )

    def test_failed_transfer_leaves_nothing_behind(self):
        self.offer("report.pdf", b"0123456789")
        (self.spool / "report.pdf").write_bytes(b"0123456780")
        self.failure("report.pdf")
        self.assertEqual(list(self.dest.iterdir()), [])

    def test_existing_file_is_kept_by_default(self):
        self.offer("report.pdf", b"0123456789")
        self.dest.mkdir()
        (self.dest / "report.pdf").write_bytes(b"old")
        self.assertIn("Refusing to overwrite", self.failure("report.pdf"))
        self.assertEqual((self.dest / "report.pdf").read_bytes(), b"old")

    def test_overwrite_replaces_existing_file(self):
        self.offer("report.pdf", b"0123456789")
        self.dest.mkdir()
        (self.dest / "report.pdf").write_bytes(b"old")
        receive(self.spool, "report.pdf", self.dest, overwrite=True)
        self.assertEqual((self.dest / "report.pdf").read_bytes(), b"0123456789")


if __name__ == "__main__":
    unittest.main()
