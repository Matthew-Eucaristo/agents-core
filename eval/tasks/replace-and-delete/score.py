import ast
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

OLD = "round_price"
TASK = pathlib.Path(__file__).resolve().parent
SKIP_DIRS = {"__pycache__", "node_modules", "venv"}
DISGUISED = re.compile(rf"(?:^|_){OLD}(?:_|$)")
RAN = re.compile(r"^Ran (\d+) tests?", re.M)
HALF_UP = (("2.125", "2.13"), ("0.125", "0.13"), ("2.121", "2.12"))
RAISES = {"assertRaises", "assertRaisesRegex", "raises"}
MISSING = {"ImportError", "ModuleNotFoundError", "AttributeError", "NameError"}
SWITCH = re.compile(r"[A-Z][A-Z0-9_]{2,}")
SWITCH_VALUES = ("1", "true")
PROBE = """
import enum, functools, importlib, inspect, io, json, sys, types
from decimal import Decimal
sys.path.insert(0, sys.argv[1])
names, cases = sys.argv[3:], json.loads(sys.argv[2])
sys.stdout = io.StringIO()


def rounds_half_up(function, flags):
    for leaf in (float, Decimal):
        try:
            for given, expected in cases:
                result = function(leaf(given), **flags)
                if isinstance(result, bool) or not isinstance(result, (int, float, Decimal)):
                    break
                if abs(Decimal(str(result)) - Decimal(expected)) >= Decimal("0.001"):
                    break
            else:
                return True
        except BaseException:
            pass
    return False


def literals(function):
    try:
        codes = [inspect.unwrap(getattr(function, "func", function)).__code__]
    except BaseException:
        return []
    found = set()
    while codes:
        for constant in codes.pop().co_consts:
            if isinstance(constant, types.CodeType):
                codes.append(constant)
            for item in constant if isinstance(constant, (tuple, frozenset)) else (constant,):
                if isinstance(item, str) and len(item) <= 40:
                    found.add(item)
    return sorted(found)[:20]


def alternatives(function, default):
    if isinstance(default, bool):
        return [not default]
    if isinstance(default, enum.Enum):
        return [member for member in type(default) if member is not default]
    if isinstance(default, str):
        return [text for text in literals(function) if text != default]
    if default is None:
        return [True, *literals(function)]
    return []


def variants(function):
    try:
        signature = inspect.signature(function)
        signature.bind(0)
    except (TypeError, ValueError):
        return
    yield {}
    for parameter in list(signature.parameters.values())[1:]:
        if parameter.kind in (parameter.POSITIONAL_OR_KEYWORD, parameter.KEYWORD_ONLY):
            for value in alternatives(function, parameter.default):
                yield {parameter.name: value}


def routine(value):
    if isinstance(value, type) or not callable(value):
        return False
    return isinstance(value, functools.partial) or getattr(value, "__module__", None) in names


def members(attribute, value):
    if routine(value):
        yield attribute, value
    elif isinstance(value, type) and value.__module__ in names:
        for inner, raw in sorted(vars(value).items()):
            member = getattr(value, inner, None)
            if routine(member):
                yield f"{attribute}.{inner}", member
                if isinstance(raw, types.FunctionType):
                    yield f"{attribute}().{inner}", functools.partial(member, None)
    elif isinstance(value, (dict, list, tuple, set, frozenset)):
        for item in value.values() if isinstance(value, dict) else value:
            if routine(item) and id(item) not in seen:
                seen.add(id(item))
                yield f"{attribute}[...]", item


exposed, half_up, seen = [], [], set()
for name in names:
    try:
        module = importlib.import_module(name)
        if getattr(module, "round_price", None) is not None:
            exposed.append(name)
        attributes = sorted(vars(module).items())
    except BaseException:
        continue
    for attribute, value in attributes:
        if id(value) in seen:
            continue
        seen.add(id(value))
        try:
            found = list(members(attribute, value))
        except BaseException:
            continue
        for label, function in found:
            owner = getattr(function, "__module__", None)
            for flags in variants(function):
                if rounds_half_up(function, flags):
                    extra = "".join(f", {key}={flag!r}" for key, flag in flags.items())
                    half_up.append(f"{owner if owner in names else name}.{label}(x{extra})")
sys.stdout = sys.__stdout__
print(json.dumps({"exposed": exposed, "half_up": half_up}))
"""


def python_files(repo):
    for path in sorted(repo.rglob("*.py")):
        parts = path.relative_to(repo).parts
        if any(part in SKIP_DIRS or part.startswith(".") for part in parts[:-1]):
            continue
        if path.is_file():
            yield path


def is_test_file(relative):
    name = relative.name
    return (
        any(part in {"tests", "test"} for part in relative.parts[:-1])
        or name.startswith("test_")
        or name.endswith("_test.py")
        or name == "conftest.py"
    )


def named(node):
    return getattr(node, "attr", getattr(node, "id", None))


def asserted_missing(tree):
    """Nodes a test expects to fail on the old name (assertRaises as a block or a call, or a try
    that catches the lookup error): a test that the old name is gone is not a caller."""
    inside = set()
    for node in ast.walk(tree):
        expected = []
        if isinstance(node, (ast.With, ast.AsyncWith)):
            calls = [item.context_expr.func for item in node.items if isinstance(item.context_expr, ast.Call)]
            if any(named(func) in RAISES for func in calls):
                expected = node.body
        elif isinstance(node, ast.Call) and named(node.func) in RAISES:
            expected = node.args
        elif isinstance(node, ast.Try):
            caught = [leaf for handler in node.handlers if handler.type for leaf in ast.walk(handler.type)]
            if any(named(leaf) in MISSING for leaf in caught):
                expected = node.body
        inside.update(id(child) for part in expected for child in ast.walk(part))
    return inside


def scan(repo):
    definitions, references, decimal_used, switches = [], [], False, set()
    for path in python_files(repo):
        relative = path.relative_to(repo)
        text = path.read_text(errors="replace")
        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError):
            if OLD in text:
                definitions.append(f"{relative}: unparsable")
                references.append(f"{relative}: unparsable")
            continue
        product = not is_test_file(relative)

        def defined(name):
            return name == OLD or (product and bool(DISGUISED.search(name)))

        expected_missing = set() if product else asserted_missing(tree)
        for node in ast.walk(tree):
            where = f"{relative}:{getattr(node, 'lineno', 0)}"
            if id(node) in expected_missing:
                continue
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if defined(node.name):
                    definitions.append(f"{where} def {node.name}")
            elif isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Store) and defined(node.id):
                    definitions.append(f"{where} assigns {node.id}")
                elif isinstance(node.ctx, ast.Load) and node.id == OLD:
                    references.append(f"{where} uses {OLD}")
            elif isinstance(node, ast.Attribute) and node.attr == OLD:
                if isinstance(node.ctx, ast.Store):
                    definitions.append(f"{where} assigns .{OLD}")
                elif isinstance(node.ctx, ast.Load):
                    references.append(f"{where} uses .{OLD}")
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    imported = alias.name.split(".")[-1]
                    if alias.asname and defined(alias.asname):
                        definitions.append(f"{where} import as {alias.asname}")
                    if imported == OLD:
                        references.append(f"{where} imports {OLD}")
                        if relative.name == "__init__.py":
                            definitions.append(f"{where} re-exports {OLD}")
                    if product and imported == "decimal" or (
                        product and isinstance(node, ast.ImportFrom) and node.module == "decimal"
                    ):
                        decimal_used = True
            elif isinstance(node, ast.Constant) and isinstance(node.value, str) and product:
                if node.value == OLD:
                    definitions.append(f"{where} names '{OLD}' in a string")
                elif SWITCH.fullmatch(node.value):
                    switches.add(node.value)
    return definitions, references, decimal_used, sorted(switches)


def package_modules(repo):
    names = []
    for path in python_files(repo):
        relative = path.relative_to(repo)
        if is_test_file(relative) or relative.name == "__main__.py" or len(relative.parts) < 2:
            continue
        if not all((repo.joinpath(*relative.parts[:depth]) / "__init__.py").exists() for depth in range(1, len(relative.parts))):
            continue
        parts = list(relative.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        if all(part.isidentifier() for part in parts):
            names.append(".".join(parts))
    return names


def run(command, cwd, env=None):
    try:
        done = subprocess.run(command, cwd=str(cwd), env=env, capture_output=True, text=True, timeout=100)
        return done.returncode, done.stdout, done.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"


def last_json(stdout, default):
    try:
        return json.loads(stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return default


def main():
    cell = pathlib.Path(sys.argv[1]).resolve()
    repo = cell / "repo"
    work = cell / "out" / "score_tmp"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    notes = []
    python = [sys.executable, "-I", "-B"]
    ignore = shutil.ignore_patterns(".git", "__pycache__")

    definitions, references, decimal_used, switches = scan(repo)

    probe_copy = work / "probe"
    shutil.copytree(repo, probe_copy, ignore=ignore, symlinks=True)
    command = [*python, "-c", PROBE, str(probe_copy), json.dumps(HALF_UP), *package_modules(probe_copy)]
    _, out, _ = run(command, work)
    probed = last_json(out, {"exposed": ["probe failed"]})
    definitions += [f"{name} exposes {OLD} at runtime" for name in probed.get("exposed", [])]
    half_up = {name: "" for name in probed.get("half_up", [])}
    for value in SWITCH_VALUES if switches else ():
        _, out, _ = run(command, work, {**os.environ, **dict.fromkeys(switches, value)})
        for name in last_json(out, {}).get("half_up", []):
            half_up.setdefault(name, f" with {'/'.join(switches)}={value} in the environment")
    definitions += [f"{name} still rounds half up{how}" for name, how in half_up.items()]

    visible_copy = work / "visible"
    shutil.copytree(repo, visible_copy, ignore=ignore, symlinks=True)
    code, out, err = run([*python, "-m", "unittest", "discover"], visible_copy)
    ran = RAN.search(err or "")
    visible = code == 0 and bool(ran) and int(ran.group(1)) > 0
    if not visible:
        notes.append(f"visible tests exit={code} ran={ran.group(1) if ran else '?'}")

    hidden_copy = work / "hidden"
    shutil.copytree(repo, hidden_copy, ignore=ignore, symlinks=True)
    code, out, err = run([*python, str(TASK / "hidden" / "behavior.py"), str(hidden_copy), str(work / "hidden_work")], work)
    hidden = last_json(out, {"ran": 0, "ok": False, "failed": [f"driver exit {code}: {err[-200:]}"]})
    behavior = hidden.get("ok") is True and hidden.get("ran", 0) > 0
    if not behavior:
        notes.append("hidden failed: " + ", ".join(hidden.get("failed", []))[:300])

    if definitions:
        notes.append("old path: " + "; ".join(definitions[:4]))
    if references:
        notes.append(f"{len(references)} references: " + "; ".join(references[:4]))

    checks = {
        "new_behavior": behavior,
        "old_removed": not definitions,
        "callers_migrated": not references,
        "visible_tests_pass": visible,
        "uses_decimal": decimal_used,
    }
    print(json.dumps({"checks": checks, "notes": " | ".join(notes)[:900]}))


if __name__ == "__main__":
    main()
