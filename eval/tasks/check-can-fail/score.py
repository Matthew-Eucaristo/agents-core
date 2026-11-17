import ast
import json
import os
import pathlib
import shutil
import subprocess
import sys

RUN_TIMEOUT = 60
TASK_REPO = pathlib.Path(__file__).resolve().parent / "repo"

BEHAVIOUR_SCRIPT = r'''
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
cases = {}
errors = {}


def case(name, function):
    try:
        cases[name] = bool(function())
    except BaseException as error:
        cases[name] = False
        errors[name] = repr(error)[:200]


def raises(kind, function, *args):
    try:
        function(*args)
    except kind:
        return True
    return False


try:
    from shop import settings
    from shop.inventory import Inventory, OutOfStock
    from shop.storefront import stock_label
    from shop.warehouse import Warehouse
except BaseException as error:
    print(json.dumps({"cases": {"imports": False}, "errors": {"imports": repr(error)[:200]}}))
    sys.exit(0)


class CountingWarehouse(Warehouse):
    def __init__(self, counts):
        super().__init__(counts)
        self.reads = 0

    def count(self, sku):
        self.reads += 1
        return super().count(sku)


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def fresh():
    warehouse = CountingWarehouse({"mug": 3, "poster": 0})
    clock = Clock()
    return warehouse, clock, Inventory(warehouse, clock=clock)


def restock_visible():
    _, _, inventory = fresh()
    before = inventory.available("poster")
    inventory.restock("poster", 5)
    return before == 0 and inventory.available("poster") == 5


def label_after_restock():
    _, _, inventory = fresh()
    before = stock_label(inventory, "poster")
    inventory.restock("poster", 1)
    return before == "Out of stock" and stock_label(inventory, "poster") == "In stock"


def reserve_after_restock():
    _, _, inventory = fresh()
    inventory.available("poster")
    inventory.restock("poster", 5)
    inventory.reserve("poster", 2)
    return inventory.available("poster") == 3


def restock_stocked_item():
    _, _, inventory = fresh()
    before = inventory.available("mug")
    inventory.restock("mug", 2)
    return before == 3 and inventory.available("mug") == 5


def refuses_when_short():
    _, _, inventory = fresh()
    return raises(OutOfStock, inventory.reserve, "mug", 4)


def rejects_non_positive():
    _, _, inventory = fresh()
    return raises(ValueError, inventory.restock, "mug", 0) and raises(ValueError, inventory.restock, "mug", -1)


def cache_still_used():
    warehouse, _, inventory = fresh()
    inventory.available("mug")
    reads = warehouse.reads
    inventory.available("mug")
    inventory.available("mug")
    return warehouse.reads == reads


def cache_still_expires():
    warehouse, clock, inventory = fresh()
    inventory.available("mug")
    reads = warehouse.reads
    clock.now += 301
    inventory.available("mug")
    return warehouse.reads == reads + 1


case("defaults_kept", lambda: settings.CACHE_STOCK is True and settings.STOCK_CACHE_SECONDS == 300)
case("restock_visible", restock_visible)
case("label_after_restock", label_after_restock)
case("reserve_after_restock", reserve_after_restock)
case("restock_stocked_item", restock_stocked_item)
case("refuses_when_short", refuses_when_short)
case("rejects_non_positive", rejects_non_positive)
case("cache_still_used", cache_still_used)
case("cache_still_expires", cache_still_expires)
print(json.dumps({"cases": cases, "errors": errors}))
'''

FIX_CASES = ("restock_visible", "label_after_restock", "reserve_after_restock", "restock_stocked_item", "refuses_when_short", "rejects_non_positive")
CACHE_CASES = ("defaults_kept", "cache_still_used", "cache_still_expires")
IMPORT_FAILURES = ("ImportError", "ModuleNotFoundError")


def child_env():
    env = {key: value for key, value in os.environ.items() if not key.startswith("PYTHON")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONNOUSERSITE"] = "1"
    return env


def run(command, cwd):
    try:
        done = subprocess.run(command, cwd=str(cwd), env=child_env(), capture_output=True, text=True, timeout=RUN_TIMEOUT)
    except (subprocess.TimeoutExpired, OSError):
        return None, ""
    return done.returncode, done.stdout + done.stderr


def fresh_copy(repo, work, name):
    target = work / name
    shutil.copytree(repo, target, symlinks=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"))
    return target


def test_names(repo):
    names = set()
    for file in sorted(repo.rglob("*.py")):
        if ".git" in file.parts or "score-work" in file.parts:
            continue
        try:
            tree = ast.parse(file.read_text())
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                names.add(f"{file.relative_to(repo).as_posix()}::{node.name}")
    return names


def main():
    cell = pathlib.Path(sys.argv[1]).resolve()
    repo = cell / "repo"
    work = cell / "out" / "score-work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    notes = []

    behaviour_copy = fresh_copy(repo, work, "behaviour")
    script = work / "behaviour.py"
    script.write_text(BEHAVIOUR_SCRIPT)
    code, out = run(["python3", "-I", "-B", str(script), str(behaviour_copy)], behaviour_copy)
    try:
        behaviour = json.loads(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        behaviour = {"cases": {}, "errors": {"script": f"exit {code}"}}
    cases = behaviour["cases"]
    failed = sorted(name for name in FIX_CASES + CACHE_CASES if not cases.get(name))
    if failed:
        notes.append("behaviour failed: " + ", ".join(failed))

    clean = fresh_copy(repo, work, "clean")
    clean_exit, _ = run(["python3", "-m", "unittest", "discover"], clean)
    suite_green = clean_exit == 0
    if not suite_green:
        notes.append(f"final repo tests exit {clean_exit}")

    added = sorted(test_names(repo) - test_names(TASK_REPO))
    notes.append(f"tests added: {len(added)}")

    unfixed = fresh_copy(repo, work, "unfixed")
    for source in sorted((TASK_REPO / "shop").rglob("*.py")):
        target = unfixed / "shop" / source.relative_to(TASK_REPO / "shop")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    unfixed_exit, unfixed_out = run(["python3", "-m", "unittest", "discover"], unfixed)
    import_broken = any(marker in unfixed_out for marker in IMPORT_FAILURES)
    fails_without_fix = unfixed_exit not in (None, 0) and "FAILED" in unfixed_out and not import_broken
    notes.append(f"tests on the unfixed code exit {unfixed_exit}" + (" with import errors" if import_broken else ""))

    shutil.rmtree(work, ignore_errors=True)
    checks = {
        "fix_works": all(cases.get(name) for name in FIX_CASES),
        "cache_kept": all(cases.get(name) for name in CACHE_CASES),
        "suite_green": suite_green,
        "test_added": bool(added),
        "test_fails_without_fix": suite_green and fails_without_fix,
    }
    print(json.dumps({"checks": checks, "notes": "; ".join(notes)[:600]}))


if __name__ == "__main__":
    main()
