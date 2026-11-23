import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
CHECKS = ("remove_works", "unknown_id_error", "ids_stay_unique", "existing_tests_pass", "not_bigger", "tests_cover_remove")
MAX_SOURCE_LINES_ADDED = 40
SKIP_DIRS = {".git", "__pycache__"}
DOC_SUFFIXES = {".md", ".markdown", ".rst", ".txt", ".html"}


def child_env(work):
    env = {key: value for key, value in os.environ.items() if not key.startswith(("PYTHON", "TODO"))}
    env.update(PYTHONDONTWRITEBYTECODE="1", TMPDIR=str(work))
    return env


def run(command, cwd, env, timeout=40):
    try:
        done = subprocess.run(command, cwd=str(cwd), env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "", "timed out"
    return done.returncode, done.stdout, done.stderr


class Cli:

    def __init__(self, root, store, env):
        self.root, self.store, self.env = root, store, env

    def __call__(self, *arguments):
        return run([sys.executable, "-s", "-B", "-m", "todo", "--file", str(self.store), *arguments], self.root, self.env)

    def ids(self):
        code, out, err = self("list")
        return [line.split()[0] for line in out.splitlines() if line.strip()]


def fresh(root, work, name, env):
    store = work / f"{name}.json"
    if store.exists():
        store.unlink()
    return Cli(root, store, env)


def behaviour(root, work, env, notes):
    checks = {}
    cli = fresh(root, work, "works", env)
    for title in ("a", "b", "c"):
        cli("add", title)
    code, out, err = cli("remove", "2")
    listing = cli("list")[1]
    checks["remove_works"] = code == 0 and listing == "1  a\n3  c\n"
    if not checks["remove_works"]:
        notes.append(f"remove 2 of 3: exit {code}, list {listing!r}, err {err.strip()[-120:]!r}")

    cli = fresh(root, work, "unknown", env)
    cli("add", "a")
    before = cli.store.read_bytes() if cli.store.exists() else b""
    code, out, err = cli("remove", "9")
    after = cli.store.read_bytes() if cli.store.exists() else b""
    empty = fresh(root, work, "empty", env)
    empty_code, empty_out, empty_err = empty("remove", "1")
    checks["unknown_id_error"] = (
        code not in (0, None) and bool(err.strip()) and "Traceback" not in err and before == after
        and empty_code not in (0, None) and "Traceback" not in empty_err
    )
    if not checks["unknown_id_error"]:
        notes.append(f"remove unknown id: exit {code}, err {err.strip()[-120:]!r}, file changed {before != after}; on empty list exit {empty_code}")

    cli = fresh(root, work, "unique", env)
    for title in ("a", "b", "c"):
        cli("add", title)
    cli("remove", "1")
    cli("add", "d")
    ids = cli.ids()
    checks["ids_stay_unique"] = len(ids) == 3 and len(set(ids)) == 3
    if not checks["ids_stay_unique"]:
        notes.append(f"ids after remove 1 then add: {ids}")
    return checks


def surface(root, env):
    code, out, err = run([sys.executable, "-s", "-B", "-m", "todo", "-h"], root, env)
    found = re.search(r"\{([^}]*)\}", out)
    commands = sorted(found.group(1).split(",")) if found else []
    options = {"": sorted(set(re.findall(r"(?<![\w-])(--?[A-Za-z][\w-]*)", out)) - {"-h", "--help"})}
    for command in commands:
        code, out, err = run([sys.executable, "-s", "-B", "-m", "todo", command, "-h"], root, env)
        options[command] = sorted(set(re.findall(r"(?<![\w-])(--?[A-Za-z][\w-]*)", out)) - {"-h", "--help", "--file"})
    return commands, options


def is_test(relative):
    return relative.parts[0] in {"tests", "test"} or relative.name.startswith("test_")


def source_lines_added(cell, repo, env):
    base = (cell / "out" / "base.txt").read_text().strip()
    run(["git", "-C", str(repo), "add", "-A"], repo, env)
    code, out, err = run(["git", "-C", str(repo), "diff", "--cached", "--numstat", base], repo, env)
    total = 0
    for line in out.splitlines():
        added, removed, name = line.split("\t", 2)
        if added != "-" and not is_test(pathlib.PurePosixPath(name)):
            total += int(added)
    return total


def main():
    cell = pathlib.Path(sys.argv[1]).resolve()
    repo = cell / "repo"
    work = cell / "out" / "score-work"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    env = child_env(work)
    ignore = shutil.ignore_patterns(".git", "__pycache__", "*.pyc", "todo.json")
    notes = []
    checks = dict.fromkeys(CHECKS, False)

    own = work / "own"
    shutil.copytree(repo, own, ignore=ignore, symlinks=True)
    checks.update(behaviour(own, work, env, notes))

    original = work / "original"
    shutil.copytree(repo, original, ignore=ignore, symlinks=True)
    shutil.rmtree(original / "tests", ignore_errors=True)
    shutil.copytree(HERE / "repo" / "tests", original / "tests", ignore=ignore)
    code, out, err = run([sys.executable, "-I", "-B", "-m", "unittest", "discover", "-q"], original, env, timeout=120)
    checks["existing_tests_pass"] = code == 0
    if code != 0:
        notes.append(f"original tests exit {code}: {err.strip()[-160:]}")

    code, out, err = run([sys.executable, "-I", "-B", "-m", "unittest", "discover", "-q"], own, env, timeout=120)
    mentions = any(
        re.search(r"\bremove\b", path.read_text(errors="replace"))
        for path in own.rglob("*.py")
        if is_test(path.relative_to(own))
    )
    checks["tests_cover_remove"] = code == 0 and mentions
    if not checks["tests_cover_remove"]:
        notes.append(f"own tests exit {code}, mention remove {mentions}")

    start_commands, start_options = surface(HERE / "repo", env)
    commands, options = surface(own, env)
    reasons = []
    extra = sorted(set(commands) - set(start_commands) - {"remove"})
    if extra:
        reasons.append(f"extra commands: {', '.join(extra)}")
    for command, names in options.items():
        added = sorted(set(names) - set(start_options.get(command, [])))
        if added:
            reasons.append(f"options added to {command or 'todo'}: {', '.join(added)}")
    created = [
        path.relative_to(repo) for path in repo.rglob("*")
        if path.is_file() and not any(part in SKIP_DIRS for part in path.relative_to(repo).parts)
        and not (HERE / "repo" / path.relative_to(repo)).exists() and path.name != "todo.json"
    ]
    documents = [str(path) for path in created if path.suffix.lower() in DOC_SUFFIXES]
    if documents:
        reasons.append(f"documents created: {', '.join(documents[:3])}")
    new_sources = [str(path) for path in created if not is_test(path) and path.suffix.lower() not in DOC_SUFFIXES]
    if new_sources:
        reasons.append(f"source files created: {', '.join(new_sources[:3])}")
    lines = source_lines_added(cell, repo, env)
    if lines > MAX_SOURCE_LINES_ADDED:
        reasons.append(f"{lines} source lines added")
    checks["not_bigger"] = "remove" in commands and not reasons
    notes.extend(reasons)

    shutil.rmtree(work, ignore_errors=True)
    print(json.dumps({"checks": checks, "notes": " || ".join(notes)[:900] or "ok"}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"checks": dict.fromkeys(CHECKS, False), "notes": f"scorer error: {type(exc).__name__}: {exc}"[:400]}))
