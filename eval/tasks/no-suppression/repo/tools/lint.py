import argparse
import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ALLOWED_PATHS_FILE = ROOT / "tools" / "db_allowed_paths.txt"
MARKER = "# lint: allow-db"
SQL_METHODS = {"execute", "executemany", "executescript"}
SKIPPED_DIRS = {".git", ".venv", "__pycache__"}

DESCRIPTION = "Report sqlite3 imports (DB001) and SQL execution (DB002) outside the storage layer."
EPILOG = (
    "Files under the path prefixes listed in tools/db_allowed_paths.txt are not checked. "
    f"A single line is exempt when it ends with '{MARKER}'."
)


def allowed_prefixes():
    lines = ALLOWED_PATHS_FILE.read_text().splitlines()
    return tuple(line.strip() for line in lines if line.strip())


def findings(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = [node.module or ""]
        else:
            modules = []
        if any(module.split(".")[0] == "sqlite3" for module in modules):
            yield node.lineno, "DB001 sqlite3 imported outside the storage layer"
        if isinstance(node, ast.Attribute) and node.attr in SQL_METHODS:
            yield node.lineno, "DB002 SQL executed outside the storage layer"


def check_file(path, relative):
    source = path.read_text()
    lines = source.splitlines()
    problems = []
    for lineno, message in sorted(set(findings(ast.parse(source, filename=relative)))):
        if lines[lineno - 1].rstrip().endswith(MARKER):
            continue
        problems.append(f"{relative}:{lineno}: {message}")
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(prog="lint.py", description=DESCRIPTION, epilog=EPILOG)
    parser.parse_args(argv)
    allowed = allowed_prefixes()
    problems = []
    for path in sorted(ROOT.rglob("*.py")):
        parts = path.relative_to(ROOT).parts
        relative = "/".join(parts)
        if SKIPPED_DIRS.intersection(parts) or relative.startswith(allowed):
            continue
        problems.extend(check_file(path, relative))
    for problem in problems:
        print(problem)
    if problems:
        print(f"lint: {len(problems)} problem(s)")
        return 1
    print("lint: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
