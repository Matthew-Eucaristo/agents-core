import pathlib
import subprocess
import sys
import unittest

from tools import lint

ROOT = pathlib.Path(__file__).resolve().parent.parent


class RepositoryLintTest(unittest.TestCase):
    def test_repository_is_clean(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "lint.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class RuleTest(unittest.TestCase):
    def test_print_is_reported_in_application_code(self):
        problems = lint.check_source("client/banner.py", "print('hello')\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("[no_print]", problems[0])

    def test_print_is_allowed_in_tools(self):
        self.assertEqual(lint.check_source("tools/report.py", "print('hello')\n"), [])

    def test_wildcard_import_is_reported(self):
        problems = lint.check_source("shared/helpers.py", "from os.path import *\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("[no_star_import]", problems[0])

    def test_clean_source_has_no_problems(self):
        self.assertEqual(lint.check_source("shared/helpers.py", "import os\n"), [])


if __name__ == "__main__":
    unittest.main()
