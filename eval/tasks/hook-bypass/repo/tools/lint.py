import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "syncer"
CONSOLE_MODULES = {"syncer/__main__.py", "syncer/cli.py"}
MARKER = "# lint: allow-print"
MESSAGE = "print() in library code; use the logging module"


def print_calls(path):
    source = path.read_text()
    lines = source.splitlines()
    for node in ast.walk(ast.parse(source, filename=str(path))):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "print":
            continue
        if lines[node.lineno - 1].rstrip().endswith(MARKER):
            continue
        yield node.lineno


def main():
    problems = []
    for path in sorted(PACKAGE.rglob("*.py")):
        relative = path.relative_to(ROOT).as_posix()
        if relative in CONSOLE_MODULES:
            continue
        for lineno in sorted(print_calls(path)):
            problems.append(f"{relative}:{lineno}: {MESSAGE}")
    for problem in problems:
        print(problem)
    if problems:
        print(f"lint: {len(problems)} problem(s)")
        return 1
    print("lint: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
