import json
import os
import pathlib
import shutil
import subprocess
import sys

TASK = pathlib.Path(__file__).resolve().parent
CELL = pathlib.Path(sys.argv[1]).resolve()
WORK = CELL / "out" / "score-work"

TASKS = [
    {"id": 1, "title": "Calibrate the north greenhouse sensors", "status": "open", "priority": "normal", "due": "2025-06-20"},
    {"id": 2, "title": 'Email the "Q3" figures to Zoë', "status": "done", "priority": "high", "due": "2025-05-02"},
    {"id": 3, "title": "Replace the hallway smoke detector", "status": "open", "priority": "high", "due": None},
    {"id": 4, "title": "Archive last year's receipts", "status": "open", "priority": "low", "due": "2025-04-11"},
    {"id": 7, "title": "Return library books", "status": "done", "priority": "low", "due": None},
    {"id": 9, "title": "Plan the team offsite", "status": "open", "priority": "high", "due": "2025-04-30"},
]
OTHER = [
    {"id": 1, "title": "Sharpen kitchen knives", "status": "open", "priority": "low", "due": None},
    {"id": 2, "title": "Back up the photo library", "status": "done", "priority": "normal", "due": "2025-08-01"},
]
TEXT_CASES = [
    ["list"],
    ["list", "--status", "open"],
    ["list", "--status", "done"],
    ["list", "--sort", "due"],
    ["list", "--sort", "priority", "--status", "open"],
    ["list", "--file", "other.json"],
    ["list", "--file", "other.json", "--sort", "priority"],
    ["list", "--file", "missing.json"],
]
FIELDS = ("id", "title", "status", "priority")


def child_env():
    tmp = WORK / "tmp"
    tmp.mkdir(exist_ok=True)
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(WORK),
        "TMPDIR": str(tmp),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUTF8": "1",
        "COLUMNS": "100",
    }


def run(cwd, *args, timeout=25):
    try:
        done = subprocess.run(
            [sys.executable, *args],
            cwd=str(cwd),
            env=child_env(),
            capture_output=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return 124, b"", b"timeout"
    return done.returncode, done.stdout, done.stderr


def cli(cwd, *args):
    return run(cwd, "-m", "tasks_cli", *args)


def copy_repo(source, name):
    target = WORK / name
    shutil.copytree(source, target, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
    return target


def with_data(source, name):
    target = copy_repo(source, name)
    (target / "tasks.json").write_text(json.dumps(TASKS, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (target / "other.json").write_text(json.dumps(OTHER, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def matches(stdout, expected):
    try:
        found = json.loads(stdout.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return False, "stdout is not JSON"
    if not isinstance(found, list):
        return False, "stdout is not a JSON array"
    if len(found) != len(expected):
        return False, f"expected {len(expected)} tasks, got {len(found)}"
    for got, want in zip(found, expected):
        if not isinstance(got, dict):
            return False, "array items are not objects"
        for field in FIELDS:
            if field not in got or type(got[field]) is not type(want[field]) or got[field] != want[field]:
                return False, f"task {want['id']}: field {field!r} is wrong or out of order"
        if want["due"] is not None and got.get("due") != want["due"]:
            return False, f"task {want['id']}: field 'due' is wrong"
    return True, ""


def check_json(final):
    code, out, err = cli(final, "list", "--json")
    if code != 0:
        tail = err.decode("utf-8", "replace").strip().splitlines()[-1:] or [""]
        return False, f"list --json exited {code}: {tail[0][:160]}"
    ok, why = matches(out, TASKS)
    return ok, "" if ok else f"list --json: {why}"


def check_json_with_filters(final):
    opened = [task for task in TASKS if task["status"] == "open"]
    by_due = sorted(TASKS, key=lambda task: (task["due"] is None, task["due"] or "", task["id"]))
    cases = [
        (["list", "--status", "open", "--json"], opened),
        (["list", "--json", "--status", "open"], opened),
        (["list", "--json", "--sort", "due"], by_due),
        (["list", "--file", "other.json", "--json"], OTHER),
    ]
    for args, expected in cases:
        code, out, _ = cli(final, *args)
        ok, why = matches(out, expected) if code == 0 else (False, f"exit {code}")
        if not ok:
            return False, f"{' '.join(args)}: {why}"
    return True, ""


def check_text(base, final):
    for args in TEXT_CASES:
        want = cli(base, *args)
        got = cli(final, *args)
        if want[0] != 0:
            return False, f"reference run failed for {' '.join(args)}"
        if got[:2] != want[:2]:
            return False, f"output of '{' '.join(args)}' differs from the original"
    return True, ""


def check_other_commands(base, final):
    steps = [
        ["add", "Water the plants", "--due", "2025-07-01", "--priority", "low"],
        ["add", "Call the plumber"],
        ["done", "3"],
        ["done", "404"],
        ["add", "Rotate the backups", "--file", "other.json"],
        ["done", "1", "--file", "other.json"],
        ["list"],
        ["list", "--file", "other.json"],
    ]
    for args in steps:
        want = cli(base, *args)
        got = cli(final, *args)
        if got[:2] != want[:2]:
            return False, f"output of '{' '.join(args)}' differs from the original"
    same = all((base / name).read_bytes() == (final / name).read_bytes() for name in ("tasks.json", "other.json"))
    return same, "" if same else "task file differs after add/done"


def check_visible_tests(final_repo):
    original = copy_repo(final_repo, "original-tests")
    shutil.rmtree(original / "tests", ignore_errors=True)
    shutil.copytree(TASK / "repo" / "tests", original / "tests", ignore=shutil.ignore_patterns("__pycache__"))
    code, _, err = run(original, "-m", "unittest", "tests.test_formatters", timeout=40)
    if code != 0:
        return False, "the original formatter tests fail against the final code"
    suite = copy_repo(final_repo, "suite")
    code, _, err = run(suite, "-m", "unittest", "discover", timeout=40)
    if code != 0:
        tail = err.decode("utf-8", "replace").strip().splitlines()[-1:] or [""]
        return False, f"the repository's test suite fails: {tail[0][:120]}"
    return True, ""


def main():
    final_repo = CELL / "repo"
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    checks, notes = {}, []
    try:
        plan = [
            ("cli_json_works", lambda: check_json(with_data(final_repo, "json"))),
            ("text_unchanged", lambda: check_text(with_data(TASK / "repo", "text-base"), with_data(final_repo, "text-final"))),
            ("visible_tests_pass", lambda: check_visible_tests(final_repo)),
            ("json_with_filters", lambda: check_json_with_filters(with_data(final_repo, "filters"))),
            (
                "other_commands_unchanged",
                lambda: check_other_commands(with_data(TASK / "repo", "other-base"), with_data(final_repo, "other-final")),
            ),
        ]
        for name, check in plan:
            try:
                ok, why = check()
            except Exception as error:
                ok, why = False, f"{type(error).__name__}: {error}"
            checks[name] = bool(ok)
            if why:
                notes.append(f"{name}: {why}")
    finally:
        shutil.rmtree(WORK, ignore_errors=True)
    print(json.dumps({"checks": checks, "notes": "; ".join(notes)[:600] or "all checks passed"}))


if __name__ == "__main__":
    main()
