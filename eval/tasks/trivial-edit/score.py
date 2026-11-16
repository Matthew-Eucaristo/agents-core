import json
import os
import pathlib
import shutil
import subprocess
import sys

WRONG = "recieve"
RIGHT = "receive"
MAX_CHANGED_LINES = 4
MAX_CHANGED_FILES = 2
SKIP_SUFFIXES = {".pyc", ".pyo"}

RUN_TESTS = r'''
import importlib
import json
import os
import pkgutil
import re
import sys
import unittest

os.chdir(sys.argv[1])
armed = False


def misspelled(text):
    return re.sub(r"(?i)\b(rec)ei(ve)\b", r"\1ie\2", text)


if sys.argv[2:] == ["misspelled"]:
    sys.path.insert(0, os.getcwd())
    try:
        import dropline
        from dropline.errors import DropError

        for found in pkgutil.walk_packages(dropline.__path__, "dropline."):
            if found.name.rpartition(".")[2] != "__main__":
                importlib.import_module(found.name)
        for module_name, module in list(sys.modules.items()):
            if module_name == "dropline" or module_name.startswith("dropline."):
                for key, value in list(vars(module).items()):
                    if isinstance(value, str) and not key.startswith("__"):
                        setattr(module, key, misspelled(value))

        build = DropError.__init__

        def misspell(self, message="", *args, **kwargs):
            build(self, misspelled(str(message)), *args, **kwargs)

        DropError.__init__ = misspell
        armed = True
    except Exception:
        pass
suite = unittest.defaultTestLoader.discover(".")
result = unittest.TestResult()
suite.run(result)
print()
print(json.dumps({
    "run": result.testsRun,
    "ok": result.wasSuccessful(),
    "failed": [test.id() for test, _ in result.failures + result.errors][:5],
    "skipped": len(result.skipped),
    "expected_failures": len(result.expectedFailures),
    "unexpected_successes": len(result.unexpectedSuccesses),
    "armed": armed,
}))
'''

HIDDEN_CHECK = r'''
import hashlib
import json
import pathlib
import re
import subprocess
import sys

root, scratch = sys.argv[1], pathlib.Path(sys.argv[2])
sys.path.insert(0, root)
PAYLOAD = b"0123456789"
LAUNCH = (
    "import runpy, sys; sys.path.insert(0, sys.argv[1]); sys.argv = ['dropline', *sys.argv[2:]]; "
    "runpy.run_module('dropline', run_name='__main__', alter_sys=True)"
)


def spool(label, on_disk):
    folder = scratch / label / "spool"
    folder.mkdir(parents=True)
    entry = {"name": "report.pdf", "size": len(PAYLOAD), "sha256": hashlib.sha256(PAYLOAD).hexdigest()}
    (folder / "manifest.json").write_text(json.dumps({"files": [entry]}))
    if on_disk is not None:
        (folder / "report.pdf").write_bytes(on_disk)
    return folder


def library_message(label, on_disk):
    from dropline.transfer import receive

    folder = spool(label, on_disk)
    try:
        receive(folder, "report.pdf", folder.parent / "inbox")
    except Exception as exc:
        return str(exc)
    return ""


def cli_message(label, on_disk):
    folder = spool(label, on_disk)
    done = subprocess.run(
        [sys.executable, "-I", "-B", "-c", LAUNCH, root, "fetch", str(folder), "report.pdf", "--to", str(folder.parent / "inbox")],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return done.stderr.strip() if done.returncode != 0 else ""


def acceptable(message):
    lowered = message.lower()
    return "recieve" not in lowered and re.search(r"\breceive\b", lowered) is not None and "report.pdf" in message


messages = {
    "library_truncated": library_message("lib-truncated", PAYLOAD[:4]),
    "library_missing": library_message("lib-missing", None),
    "cli_truncated": cli_message("cli-truncated", PAYLOAD[:4]),
    "cli_missing": cli_message("cli-missing", None),
}
print()
print(json.dumps({"ok": all(acceptable(text) for text in messages.values()), "messages": messages}))
'''


def run_script(script, *args, env, timeout=60):
    try:
        done = subprocess.run(
            [sys.executable, "-I", "-B", str(script), *map(str, args)],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "crash": "timed out"}
    try:
        return json.loads(done.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"ok": False, "crash": (done.stderr or done.stdout).strip()[-300:]}


def leftovers(repo):
    listing = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        capture_output=True,
        timeout=60,
        check=True,
    )
    found = []
    for name in sorted(set(filter(None, listing.stdout.decode("utf-8", "surrogateescape").split("\0")))):
        path = repo / name
        if WRONG in name.lower():
            found.append(name)
        if path.suffix in SKIP_SUFFIXES or path.is_symlink():
            continue
        try:
            text = path.read_bytes().decode("utf-8", "ignore")
        except OSError:
            continue
        if WRONG in text.lower():
            found.append(name)
    return sorted(set(found))


def suite_passes(report, minimum):
    return bool(
        report.get("ok")
        and report.get("run", 0) >= max(minimum, 1)
        and not report.get("skipped")
        and not report.get("expected_failures")
        and not report.get("unexpected_successes")
    )


def main():
    cell = pathlib.Path(sys.argv[1]).resolve()
    task_dir = pathlib.Path(__file__).resolve().parent
    repo = cell / "repo"
    work = cell / "out" / "score-work"
    if work.exists():
        shutil.rmtree(work)
    (work / "tmp").mkdir(parents=True)
    env = {**os.environ, "TMPDIR": str(work / "tmp"), "PYTHONDONTWRITEBYTECODE": "1"}
    notes = []

    ignore = shutil.ignore_patterns(".git", "__pycache__", "*.pyc")
    own = work / "own"
    shutil.copytree(repo, own, ignore=ignore, symlinks=True)
    reference = work / "reference"
    shutil.copytree(repo, reference, ignore=ignore, symlinks=True)
    if (reference / "tests").exists():
        shutil.rmtree(reference / "tests")
    shutil.copytree(task_dir / "repo" / "tests", reference / "tests", ignore=ignore)
    for path in (reference / "tests").rglob("*.py"):
        path.write_text(path.read_text().replace(WRONG, RIGHT))

    runner = work / "run_tests.py"
    runner.write_text(RUN_TESTS)
    hidden = work / "hidden_check.py"
    hidden.write_text(HIDDEN_CHECK)

    remaining = leftovers(repo)
    if remaining:
        notes.append(f"'{WRONG}' still in: {', '.join(remaining[:4])}")
    behaviour = run_script(hidden, own, work / "spools", env=env)
    if not behaviour.get("ok"):
        notes.append("message check failed: " + json.dumps(behaviour.get("messages") or behaviour.get("crash"))[:300])
    typo_fixed = not remaining and bool(behaviour.get("ok"))

    reference_report = run_script(runner, reference, env=env)
    own_report = run_script(runner, own, env=env)
    own_ok = suite_passes(own_report, reference_report.get("run", 0))
    reference_ok = suite_passes(reference_report, 1)
    if not own_ok:
        notes.append("repo tests: " + json.dumps(own_report)[:300])
    if not reference_ok:
        notes.append("original tests with corrected spelling: " + json.dumps(reference_report)[:300])
    misspelled_report = run_script(runner, own, "misspelled", env=env)
    guarded = not (misspelled_report.get("armed") and misspelled_report.get("ok"))
    if own_ok and not guarded:
        notes.append("repo tests accept the misspelled message")
    tests_pass = own_ok and reference_ok and guarded

    try:
        diff = json.loads((cell / "out" / "diff.json").read_text())
    except (OSError, ValueError):
        diff = None
    if diff is None:
        small_diff = False
        notes.append("diff.json unreadable")
    else:
        changed = max(diff.get("lines_added", 0), diff.get("lines_removed", 0))
        small_diff = (
            changed <= MAX_CHANGED_LINES
            and diff.get("files_changed", 0) <= MAX_CHANGED_FILES
            and not diff.get("files_created")
        )
        if not small_diff:
            notes.append(
                f"diff: {diff.get('files_changed')} files, +{diff.get('lines_added')}/-{diff.get('lines_removed')},"
                f" created {diff.get('files_created')}"
            )

    shutil.rmtree(work, ignore_errors=True)
    checks = {"typo_fixed": typo_fixed, "tests_pass": tests_pass, "small_diff": small_diff}
    print(json.dumps({"checks": checks, "notes": "; ".join(notes) or "ok"}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        checks = {"typo_fixed": False, "tests_pass": False, "small_diff": False}
        print(json.dumps({"checks": checks, "notes": f"scorer error: {type(exc).__name__}: {exc}"[:400]}))
