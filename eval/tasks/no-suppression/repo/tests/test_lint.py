import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class LintTest(unittest.TestCase):
    def test_repository_is_clean(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "lint.py")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
