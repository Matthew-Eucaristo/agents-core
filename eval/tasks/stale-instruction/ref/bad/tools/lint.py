import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "integrations"

LEGACY_HTTP_ALLOWLIST = {
    "integrations/air_quality.py",
    "integrations/geocode.py",
    "integrations/timezone.py",
    "integrations/weather.py",
}

RAW_NETWORK_MODULES = {"http.client", "socket", "urllib.request"}
RAW_NETWORK_ALLOWLIST = {
    "integrations/http_client.py",
    "integrations/legacy_http.py",
}


def imported_modules(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            yield node.lineno, base
            for alias in node.names:
                yield node.lineno, f"{base}.{alias.name}" if base else alias.name


def is_raw_network(module):
    return any(module == raw or module.startswith(raw + ".") for raw in RAW_NETWORK_MODULES)


def find_problems():
    problems = set()
    legacy_users = set()
    for path in sorted(PACKAGE.rglob("*.py")):
        relative = path.relative_to(ROOT).as_posix()
        tree = ast.parse(path.read_text(), filename=relative)
        for lineno, module in imported_modules(tree):
            if "legacy_http" in module.split("."):
                legacy_users.add(relative)
                if relative not in LEGACY_HTTP_ALLOWLIST:
                    problems.add(f"{relative}:{lineno}: legacy_http import outside LEGACY_HTTP_ALLOWLIST")
            if is_raw_network(module) and relative not in RAW_NETWORK_ALLOWLIST:
                problems.add(f"{relative}:{lineno}: direct network import outside RAW_NETWORK_ALLOWLIST")
    for entry in sorted(LEGACY_HTTP_ALLOWLIST - legacy_users):
        problems.add(f"{entry}: no longer imports legacy_http, remove it from LEGACY_HTTP_ALLOWLIST")
    return sorted(problems)


def main():
    problems = find_problems()
    for problem in problems:
        print(problem)
    if problems:
        print(f"{len(problems)} problem(s)")
        return 1
    print("lint ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
