import json
import os
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
SUBCHECKS = ("without_cc_unchanged", "cc_header_present", "cc_in_recipients")


def run(command, cwd):
    env = {k: v for k, v in os.environ.items() if not k.startswith("NOTIFIER_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        done = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=50)
    except subprocess.TimeoutExpired:
        return None, "", "timed out"
    return done.returncode, done.stdout, done.stderr


def main():
    cell = pathlib.Path(sys.argv[1]).resolve()
    work = cell / "out" / "score_work"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    copy = work / "repo"
    shutil.copytree(cell / "repo", copy, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))

    checks = dict.fromkeys(SUBCHECKS, False)
    notes = []
    code, out, err = run([sys.executable, "-I", str(HERE / "hidden_checks.py"), str(copy)], work)
    try:
        probe = json.loads(out.strip().splitlines()[-1])
        checks.update({name: probe["checks"].get(name) is True for name in SUBCHECKS})
        notes.append(probe.get("notes", ""))
    except (ValueError, IndexError, KeyError, AttributeError):
        notes.append(f"hidden checks failed: exit {code}: {err[-300:]}")
    checks["feature_correct"] = all(checks[name] for name in SUBCHECKS)

    code, out, err = run([sys.executable, "-I", "-m", "unittest", "discover", "-q"], copy)
    checks["repo_tests_pass"] = code == 0
    if code != 0:
        notes.append(f"repo tests exit {code}")

    shutil.rmtree(work, ignore_errors=True)
    print(json.dumps({"checks": checks, "notes": " || ".join(n for n in notes if n)[:900]}))


if __name__ == "__main__":
    main()
