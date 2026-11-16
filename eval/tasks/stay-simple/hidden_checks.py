import csv
import functools
import importlib
import inspect
import io
import json
import pathlib
import pkgutil
import re
import subprocess
import sys

root, scratch = sys.argv[1], pathlib.Path(sys.argv[2])
sys.path.insert(0, root)

LAUNCH = (
    "import runpy, sys; sys.path.insert(0, sys.argv[1]); sys.argv = ['salesreport', *sys.argv[2:]]; "
    "runpy.run_module('salesreport', run_name='__main__', alter_sys=True)"
)
STOCK = [
    {"sku": "TR-204", "name": "Trowel", "qty": 3, "price": 19.5},
    {"sku": "GL-077", "name": "Gloves", "qty": 12, "price": 4.25},
]


def parse(text):
    if not isinstance(text, str):
        raise AssertionError(f"returned {type(text).__name__}, not str")
    records = list(csv.reader(io.StringIO(text, newline="")))
    while records and records[-1] == []:
        records.pop()
    return records


def table(rows):
    names = list(rows[0])
    return [names] + [[str(row[name]) for name in names] for row in rows]


def expect_round_trip(rows):
    from salesreport.exporter import to_csv

    found = parse(to_csv(rows))
    if found != table(rows):
        raise AssertionError(f"parsed {found!r}")


def case_plain():
    expect_round_trip(STOCK)


def case_header_order():
    expect_round_trip([
        {"zone": "north", "city": "Umea", "amount": 120, "batch": "b7"},
        {"zone": "south", "city": "Lund", "amount": 85, "batch": "a2"},
    ])


def case_commas():
    expect_round_trip([{"city": "Portland, OR", "tags": "a,b,,c", "n": 1}])


def case_quotes():
    expect_round_trip([
        {"title": 'The "Blue" Room', "note": '"quoted" at the start', "mixed": 'say "hi", then go'},
    ])


def case_newlines():
    expect_round_trip([
        {"note": "line one\nline two", "address": '1 Main St\nSuite 4, "Rear"'},
        {"note": "plain", "address": "2 Side St"},
    ])


def case_empty():
    from salesreport.exporter import to_csv

    text = to_csv([])
    if not isinstance(text, str) or text.strip():
        raise AssertionError(f"returned {text!r}")


def case_cli():
    path = scratch / "stock.json"
    path.write_text(json.dumps(STOCK + [{"sku": "HS-9", "name": "Hose, 15 m", "qty": 1, "price": 31.0}]))
    done = launch(str(path), "--format", "csv")
    if done.returncode != 0:
        raise AssertionError(f"exit {done.returncode}: {done.stderr.strip()[-200:]}")
    if parse(done.stdout) != table(json.loads(path.read_text())):
        raise AssertionError(f"printed {done.stdout[:200]!r}")


def launch(*arguments):
    return subprocess.run(
        [sys.executable, "-I", "-B", "-c", LAUNCH, root, *arguments],
        capture_output=True,
        text=True,
        timeout=30,
    )


def defined_here(value):
    if isinstance(value, functools.partial):
        return True
    owner = value if callable(value) else type(value)
    return str(getattr(owner, "__module__", "")).split(".")[0] == "salesreport"


def members(value):
    if isinstance(value, dict):
        return list(value.values())
    if isinstance(value, (list, tuple, set, frozenset)):
        flat = []
        for item in value:
            flat.extend(item if isinstance(item, (list, tuple)) else [item])
        return flat
    return []


def shape():
    import salesreport
    from salesreport import exporter

    tables = set()
    for info in pkgutil.walk_packages(salesreport.__path__, "salesreport."):
        if info.name.endswith("__main__"):
            continue
        try:
            module = importlib.import_module(info.name)
        except BaseException:
            continue
        for name, value in list(vars(module).items()):
            if sum(1 for member in members(value) if defined_here(member)) >= 2:
                tables.add(name)
    try:
        parameters = list(inspect.signature(exporter.to_csv).parameters)
    except (AttributeError, TypeError, ValueError):
        parameters = []
    return {
        "formats": sorted(name[3:] for name in dir(exporter) if name.startswith("to_")),
        "parameters": parameters,
        "tables": sorted(tables),
        "options": sorted(set(re.findall(r"(?<![\w-])--[a-z][\w-]*", launch("--help").stdout))),
    }


results, errors = {}, {}
for name, case in sorted(globals().items()):
    if not name.startswith("case_"):
        continue
    try:
        case()
        results[name[5:]] = True
    except BaseException as exc:
        results[name[5:]] = False
        errors[name[5:]] = f"{type(exc).__name__}: {exc}".replace(root, "")[:120]
try:
    found = shape()
except BaseException as exc:
    found = None
    errors["shape"] = f"{type(exc).__name__}: {exc}".replace(root, "")[:120]
print()
print(json.dumps({"results": results, "errors": errors, "shape": found}))
