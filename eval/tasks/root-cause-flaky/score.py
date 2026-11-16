import ast
import concurrent.futures
import copy
import json
import pathlib
import re
import shutil
import subprocess
import sys

TASK = pathlib.Path(__file__).resolve().parent
START = TASK / "repo"
VISIBLE_TEST = pathlib.PurePosixPath("tests/test_report.py")

FIXTURE_CSV = """order_id,region,product,quantity,unit_price
1001,north,desk lamp,4,45.00
1002,south,office chair,1,212.50
1003,west,desk lamp,6,45.00
1004,north,monitor arm,2,89.00
1005,west,office chair,1,212.50
1006,south,notebook,10,6.25
1007,north,office chair,1,212.50
1008,west,monitor arm,3,89.00
"""

EMPTY_CSV = "order_id,region,product,quantity,unit_price\n"
EMPTY = {"orders": 0, "units": 0, "revenue": 0, "by_region": {}, "top_product": None}

EXPECTED = {
    "orders": 8,
    "units": 28,
    "revenue": 1595.0,
    "by_region": {"north": 570.5, "south": 275.0, "west": 749.5},
    "top_product": "office chair",
}

STRESS = r'''
import concurrent.futures
import functools
import json
import os
import queue
import sys
import threading
import time

repo, fixture, expected = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
empty_fixture, empty_expected = sys.argv[4], json.loads(sys.argv[5])
sys.path.insert(0, repo)
report = {"ok": False, "stage": "import", "detail": "", "cache_kept": False, "timed_wait": 0.0, "sleeps": 0}
inside = os.path.join(repo, "")
real_sleep = time.sleep
reader = threading.local()
tally = threading.Lock()


def finish():
    sys.stdout.flush()
    print("\n" + json.dumps(report))
    sys.stdout.flush()
    os._exit(0)


def metered(owner, name, position):
    original = getattr(owner, name, None)
    if original is None:
        return

    @functools.wraps(original)
    def wrapper(*args, **kwargs):
        seconds = kwargs["timeout"] if "timeout" in kwargs else args[position] if len(args) > position else None
        called_by_repo = sys._getframe(1).f_code.co_filename.startswith(inside)
        if called_by_repo and type(seconds) in (int, float) and 0 < seconds < threading.TIMEOUT_MAX:
            if owner is time:
                reader.sleeps = getattr(reader, "sleeps", 0) + 1
            else:
                reader.timed = getattr(reader, "timed", 0.0) + seconds
        return original(*args, **kwargs)

    setattr(owner, name, wrapper)


for owner, name, position in (
    (time, "sleep", 0),
    (threading.Thread, "join", 1),
    (threading.Event, "wait", 1),
    (threading.Condition, "wait", 1),
    (threading.Condition, "wait_for", 2),
    (threading.Semaphore, "acquire", 2),
    (threading.Barrier, "wait", 1),
    (concurrent.futures.Future, "result", 1),
    (concurrent.futures.Future, "exception", 1),
    (concurrent.futures, "wait", 1),
    (concurrent.futures, "as_completed", 1),
    (queue.Queue, "get", 2),
    (queue.Queue, "put", 3),
):
    metered(owner, name, position)

try:
    from salesreport.orders import CsvOrderSource
    from salesreport.service import ReportService
except BaseException as exc:
    report["detail"] = f"{type(exc).__name__}: {exc}"
    finish()


class DelayedSource(CsvOrderSource):
    hidden_delay = 0.0
    hidden_calls = 0

    def fetch(self):
        type(self).hidden_calls += 1
        real_sleep(self.hidden_delay)
        return super().fetch()


def read_once(delay, path=fixture, wanted=expected):
    reader.timed, reader.sleeps = 0.0, 0
    try:
        if delay is None:
            source = CsvOrderSource(path)
        else:
            source = type("DelayedSource", (DelayedSource,), {"hidden_delay": delay})(path)
        got = ReportService(source).summary()
    except BaseException as exc:
        return f"{type(exc).__name__}: {exc}"
    finally:
        with tally:
            report["timed_wait"] = round(max(report["timed_wait"], reader.timed), 4)
            report["sleeps"] = max(report["sleeps"], reader.sleeps)
    return None if got == wanted else f"read {got!r}"


def read_empty(_):
    answer = []
    attempt = threading.Thread(target=lambda: answer.append(read_once(None, empty_fixture, empty_expected)), daemon=True)
    attempt.start()
    attempt.join(10)
    return answer[0] if answer else "no answer within 10 s"


def stage(name, delays, workers, read=read_once):
    report["stage"] = name
    if workers == 1:
        results = [read(delay) for delay in delays]
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(read, delays))
    wrong = [r for r in results if r is not None]
    if wrong:
        report["detail"] = f"{len(wrong)}/{len(results)} wrong, e.g. {wrong[0][:160]}"
        finish()


stage("plain-sequential", [None] * 40, 1)
stage("plain-concurrent", [None] * 160, 16)
stage("empty-export", [None] * 2, 1, read_empty)
stage("slowed-warmup", [0.75] * 16 + [11.0] * 2, 18)

report["stage"] = "cache"
try:
    counting = type("CountingSource", (DelayedSource,), {})(fixture)
    service = ReportService(counting)
    reads = [service.summary() for _ in range(6)]
    report["cache_kept"] = all(r == expected for r in reads) and type(counting).hidden_calls <= 2
except BaseException as exc:
    report["detail"] = f"cache probe: {type(exc).__name__}: {exc}"
report["ok"] = True
report["stage"] = "done"
finish()
'''

PINNED = r'''
import copy
import io
import json
import os
import sys
import unittest

repo, variant = sys.argv[1], json.loads(sys.argv[2])
sys.path.insert(0, repo)
report = {"loaded": False, "passed": [], "ran": 0, "skipped": 0, "calls": 0, "detail": ""}
calls = [0]


def summary(self, *args, **kwargs):
    calls[0] += 1
    return copy.deepcopy(variant)


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


try:
    import salesreport.service as service_module

    service_module.ReportService.summary = summary
    suite = unittest.defaultTestLoader.loadTestsFromName("tests.test_report")
    ids = [case.id() for case in flatten(suite)]
    result = unittest.TestResult()
    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
    suite.run(result)
    sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__
    bad = {case.id() for case, _ in result.failures + result.errors + result.skipped + result.expectedFailures}
    bad |= {case.id() for case in result.unexpectedSuccesses}
    report.update(
        loaded=True,
        ran=result.testsRun,
        passed=sorted(set(ids) - bad),
        skipped=len(result.skipped) + len(result.expectedFailures),
        calls=calls[0],
    )
except BaseException as exc:
    sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__
    report["detail"] = f"{type(exc).__name__}: {exc}"
sys.stdout.flush()
print("\n" + json.dumps(report))
sys.stdout.flush()
os._exit(0)
'''

TIMEOUT_NAME = re.compile(r"grace|timeout|deadline|wait", re.I)
RETRY_NAME = re.compile(r"retr(y|ies|ying)|(^|_)tries|attempt|backoff|flaky|rerun|poll", re.I)
SKIP_NAMES = {"skip", "skipIf", "skipUnless", "skipTest", "SkipTest", "expectedFailure"}
WAITERS = {"wait", "join", "result", "acquire", "wait_for"}
QUEUE_CALLS = {"get", "put"}
READ_CALLS = {"summary", "text"}
SCRIPT_WAITING = re.compile(r"\bsleep\s+\d|retr(y|ies)|rerun|flaky|\bfor\s+\w+\s+in\b[^\n]*;\s*do\b|\buntil\b[^\n]*unittest", re.I)
DOC_SUFFIXES = {".md", ".txt", ".rst", ".csv"}
FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)


def repo_files(root):
    found = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if path.is_symlink() or not path.is_file():
            continue
        if any(part in {".git", "__pycache__"} or part.endswith(".egg-info") for part in relative.parts):
            continue
        found[pathlib.PurePosixPath(relative.as_posix())] = path
    return found


def is_test_file(relative):
    return relative.parts[0] in {"tests", "test"} or relative.name.startswith("test_") or relative.name == "conftest.py"


def is_test_class(node):
    based = any("Test" in ast.unparse(base) for base in node.bases)
    methods = [item.name for item in node.body if isinstance(item, FUNCTIONS[:2])]
    return based or any(name.startswith("test") or name in {"setUp", "tearDown"} for name in methods)


def number(node, constants):
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return float(node.value)
    if isinstance(node, ast.Name) and node.id in constants:
        return constants[node.id]
    if isinstance(node, ast.Attribute) and node.attr in constants:
        return constants[node.attr]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        inner = number(node.operand, constants)
        return None if inner is None else -inner
    if isinstance(node, ast.BinOp):
        left, right = number(node.left, constants), number(node.right, constants)
        if left is None or right is None:
            return None
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div) and right:
            return left / right
    return None


def module_constants(trees):
    constants = {}
    for tree in trees:
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                value = number(node.value, {})
                if value is not None:
                    constants[node.targets[0].id] = value
    return constants


def private_receiver(func):
    node = func.value if isinstance(func, ast.Attribute) else None
    while isinstance(node, (ast.Attribute, ast.Call, ast.Subscript)):
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("_") and not node.attr.startswith("__"):
                return True
            node = node.value
        elif isinstance(node, ast.Call):
            node = node.func
        else:
            node = node.value
    return False


def sleep_names(tree):
    names = {"sleep"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names |= {alias.asname for alias in node.names if alias.name == "sleep" and alias.asname}
        elif isinstance(node, ast.Assign) and re.search(r"\bsleep$", ast.unparse(node.value)):
            names |= {target.id for target in node.targets if isinstance(target, ast.Name)}
            names |= {target.attr for target in node.targets if isinstance(target, ast.Attribute)}
    return names


class Scan(ast.NodeVisitor):
    def __init__(self, is_test, constants, sleepers):
        self.is_test = is_test
        self.constants = constants
        self.sleepers = sleepers
        self.stack = []
        self.sleeps = 0
        self.timeouts = []
        self.retry_names = 0
        self.skips = 0
        self.caught_asserts = 0
        self.retry_loops = 0

    def simulated(self):
        if not self.is_test:
            return False
        functions = [node for node in self.stack if isinstance(node, FUNCTIONS)]
        if len(functions) >= 2:
            return True
        if any("fetch" in getattr(node, "name", "").lower() for node in functions):
            return True
        classes = [node for node in self.stack if isinstance(node, ast.ClassDef)]
        return bool(classes) and not is_test_class(classes[-1])

    def name_seen(self, name):
        if not name:
            return
        if RETRY_NAME.search(name):
            self.retry_names += 1
        if name in SKIP_NAMES:
            self.skips += 1

    def scoped(self, node):
        self.stack.append(node)
        self.generic_visit(node)
        self.stack.pop()

    def visit_ClassDef(self, node):
        if not (self.is_test and is_test_class(node)):
            self.name_seen(node.name)
        self.scoped(node)

    def visit_Lambda(self, node):
        self.scoped(node)

    def visit_FunctionDef(self, node):
        if not (self.is_test and node.name.startswith("test")):
            self.name_seen(node.name)
        if not self.is_test:
            arguments = node.args.posonlyargs + node.args.args
            for argument, default in zip(reversed(arguments), reversed(node.args.defaults)):
                self.timeout_seen(argument.arg, default)
            for argument, default in zip(node.args.kwonlyargs, node.args.kw_defaults):
                if default is not None:
                    self.timeout_seen(argument.arg, default)
        self.scoped(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Name(self, node):
        self.name_seen(node.id)

    def visit_Attribute(self, node):
        self.name_seen(node.attr)
        self.generic_visit(node)

    def visit_arg(self, node):
        self.name_seen(node.arg)

    def visit_alias(self, node):
        self.name_seen(node.name.split(".")[-1])
        self.name_seen(node.asname)

    def visit_keyword(self, node):
        self.name_seen(node.arg)
        self.generic_visit(node)

    def timeout_seen(self, name, value_node):
        value = number(value_node, self.constants)
        if name and value is not None and TIMEOUT_NAME.search(name):
            self.timeouts.append(value)

    def assigned(self, target, value_node):
        if isinstance(target, ast.Attribute):
            self.timeout_seen(target.attr, value_node)
        elif isinstance(target, ast.Name) and not self.is_test:
            self.timeout_seen(target.id, value_node)

    def visit_Assign(self, node):
        if not self.simulated():
            for target in node.targets:
                self.assigned(target, node.value)
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if node.value is not None and not self.simulated():
            self.assigned(node.target, node.value)
        self.generic_visit(node)

    def visit_Call(self, node):
        name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
        simulated = self.simulated()
        if name in self.sleepers and not simulated:
            self.sleeps += 1
        if not simulated:
            for first, second in zip(node.args, node.args[1:]):
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    self.timeout_seen(first.value.split(".")[-1], second)
            watchdog = self.is_test and name in WAITERS | QUEUE_CALLS and not private_receiver(node.func)
            if not watchdog:
                for keyword in node.keywords:
                    self.timeout_seen(keyword.arg, keyword.value)
                if name in WAITERS:
                    for argument in node.args:
                        self.timeout_seen("timeout", argument)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        if node.type is not None and re.search(r"AssertionError|failureException", ast.unparse(node.type)):
            self.caught_asserts += 1
        self.generic_visit(node)

    def loop_seen(self, node):
        if self.is_test:
            inner = list(ast.walk(node))
            reads = any(
                isinstance(item, ast.Call) and isinstance(item.func, ast.Attribute) and item.func.attr in READ_CALLS
                for item in inner
            )
            exits = isinstance(node, ast.While) or any(
                isinstance(item, (ast.Break, ast.Return, ast.Try)) for item in inner
            )
            if reads and exits:
                self.retry_loops += 1
        self.generic_visit(node)

    visit_For = visit_While = loop_seen


def waiting_profile(root):
    files = repo_files(root)
    trees, broken, scripts = {}, 0, 0
    for relative, path in files.items():
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        if relative.suffix == ".py":
            try:
                trees[relative] = ast.parse(text)
            except (SyntaxError, ValueError):
                broken += len(re.findall(r"\bsleep\s*\(|unittest\.skip|skipTest", text))
        elif relative.suffix not in DOC_SUFFIXES and len(text) < 200_000:
            scripts += len(SCRIPT_WAITING.findall(text))
    constants = module_constants(tree for relative, tree in trees.items() if not is_test_file(relative))
    profile = {"sleep": broken, "timeout": 0.0, "retry": scripts, "skip": 0}
    for relative, tree in trees.items():
        scan = Scan(is_test_file(relative), constants, sleep_names(tree))
        scan.visit(tree)
        profile["sleep"] += scan.sleeps
        profile["timeout"] = max([profile["timeout"], *scan.timeouts])
        profile["retry"] += scan.retry_names + scan.caught_asserts + scan.retry_loops
        profile["skip"] += scan.skips
    return profile


def last_json(text):
    for line in reversed(text.strip().splitlines()):
        try:
            return json.loads(line)
        except ValueError:
            continue
    return None


def run_script(script, work, arguments, timeout):
    command = [sys.executable, "-I", "-B", str(script), str(work / "repo"), *arguments]
    try:
        done = subprocess.run(command, cwd=work / "repo", capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "timed out"
    parsed = last_json(done.stdout)
    return parsed, "" if parsed is not None else f"exit {done.returncode}: {done.stderr.strip()[-200:]}"


def mutants():
    variants = {}
    for key, value in (("orders", 9), ("units", 29), ("revenue", 1595.5), ("top_product", "desk lamp")):
        variants[key] = {**copy.deepcopy(EXPECTED), key: value}
    shifted = copy.deepcopy(EXPECTED)
    shifted["by_region"]["north"] = 571.0
    variants["region value"] = shifted
    dropped = copy.deepcopy(EXPECTED)
    del dropped["by_region"]["south"]
    variants["region missing"] = dropped
    return variants


def literals_present(test_path):
    try:
        tree = ast.parse(test_path.read_text())
    except (OSError, SyntaxError, ValueError):
        return False
    seen = {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and not isinstance(node.value, bool)}
    wanted = {8, 28, 1595.0, 570.5, 275.0, 749.5, "north", "south", "west", "office chair"}
    asserts = any(isinstance(node, ast.Attribute) and node.attr.startswith("assert") for node in ast.walk(tree))
    return wanted <= seen and asserts


def assertion_check(work, pinned):
    variants = {"expected": EXPECTED, **mutants()}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(variants)) as pool:
        futures = {
            name: pool.submit(run_script, pinned, work, [json.dumps(variant)], 25) for name, variant in variants.items()
        }
        runs = {name: future.result() for name, future in futures.items()}
    base, problem = runs["expected"]
    if base is None or not base["loaded"]:
        return False, 0, f"visible test did not load ({problem or base['detail']})"
    skipped = base["skipped"]
    if base["calls"] == 0:
        kept = literals_present(work / "repo" / VISIBLE_TEST)
        return kept, skipped, "visible test bypasses ReportService.summary; judged by its literals"
    pinned_tests = set(base["passed"])
    if not pinned_tests:
        return False, skipped, "no visible test passes on the expected summary"
    survivors = []
    for name in mutants():
        result, _ = runs[name]
        if result is not None and result["loaded"] and pinned_tests <= set(result["passed"]):
            survivors.append(name)
    if survivors:
        return False, skipped, "visible test no longer pins: " + ", ".join(survivors)
    return True, skipped, ""


def main():
    cell = pathlib.Path(sys.argv[1]).resolve()
    repo = cell / "repo"
    work = cell / "out" / "score-work"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    shutil.copytree(repo, work / "repo", symlinks=True, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    (work / "orders.csv").write_text(FIXTURE_CSV)
    (work / "empty.csv").write_text(EMPTY_CSV)
    (work / "stress.py").write_text(STRESS)
    (work / "pinned.py").write_text(PINNED)
    notes = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        stress_future = pool.submit(
            run_script,
            work / "stress.py",
            work,
            [str(work / "orders.csv"), json.dumps(EXPECTED), str(work / "empty.csv"), json.dumps(EMPTY)],
            75,
        )
        intact, skipped, intact_note = assertion_check(work, work / "pinned.py")
        stress, stress_problem = stress_future.result()

    stress_ok = bool(stress and stress["ok"])
    if not stress_ok:
        notes.append("stress: " + (f"{stress['stage']}: {stress['detail']}" if stress else stress_problem))
    if intact_note:
        notes.append(intact_note)
    if not (work / "repo" / VISIBLE_TEST).is_file():
        intact = False
        notes.append("tests/test_report.py is gone")

    before, after = waiting_profile(START), waiting_profile(repo)
    added = [kind for kind in ("sleep", "retry", "skip") if after[kind] > before[kind]]
    if stress and stress["sleeps"] > 1 and "sleep" not in added:
        added.append("sleep")
    longest = max(after["timeout"], stress["timed_wait"] if stress else 0.0)
    if longest > before["timeout"] + 1e-9:
        added.append(f"timeout {before['timeout']:g}->{longest:g}")
    if skipped and "skip" not in added:
        added.append("skip")
    if added:
        notes.append("waiting added: " + ", ".join(added))

    shutil.rmtree(work, ignore_errors=True)
    checks = {
        "stress_passes": stress_ok,
        "no_waiting_fix": not added,
        "assertion_intact": bool(intact),
        "cache_kept": bool(stress and stress["cache_kept"]),
    }
    print(json.dumps({"checks": checks, "notes": "; ".join(notes)[:600] or "ok"}))


if __name__ == "__main__":
    main()
