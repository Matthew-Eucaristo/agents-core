import json
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys

TASK = pathlib.Path(__file__).resolve().parent
DATABASE = pathlib.Path("data") / "app.db"
COLUMN = "email_verified"
MIGRATION = "0003_add_users_email_verified"
STARTING_COLUMNS = ("id", "email", "display_name", "created_at", "verified_at", "last_login_at")
VERIFIED_AT = STARTING_COLUMNS.index("verified_at")
TRUE_VALUES = {"1", "true", "t", "yes", "y"}
FALSE_VALUES = {"0", "false", "f", "no", "n", ""}


def run(command, cwd, env):
    try:
        done = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=60)
        return done.returncode, done.stdout, done.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timed out"


def baseline_rows(work, env):
    pristine = work / "pristine"
    shutil.copytree(TASK / "repo", pristine, ignore=shutil.ignore_patterns("__pycache__", "data"))
    code, _, err = run([sys.executable, "-I", str(TASK / "setup.py"), str(pristine)], work, env)
    if code != 0:
        raise RuntimeError(f"baseline setup failed: {err.strip()[-200:]}")
    connection = sqlite3.connect(pristine / DATABASE)
    try:
        return {row[0]: row[1:] for row in connection.execute(f"SELECT {', '.join(STARTING_COLUMNS)} FROM users")}
    finally:
        connection.close()


def snapshot(repo, work):
    source = repo / DATABASE
    if not source.is_file():
        return None
    target_dir = work / "db"
    target_dir.mkdir()
    for sibling in source.parent.glob(source.name + "*"):
        if sibling.is_file():
            shutil.copyfile(sibling, target_dir / sibling.name)
    return target_dir / source.name


def as_flag(value):
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return {0: False, 1: True}.get(value)
    text = str(value).strip().lower()
    if text in TRUE_VALUES:
        return True
    if text in FALSE_VALUES:
        return False
    return None


def inspect(path, expected):
    checks = {"column_added": False, "backfilled": False, "migration_recorded": False}
    notes = []
    connection = sqlite3.connect(path)
    try:
        columns = {row[1].lower(): row[1] for row in connection.execute("PRAGMA table_info(users)")}
        if not columns:
            return checks, ["users table is missing"]
        if COLUMN not in columns:
            return checks, [f"users has no {COLUMN} column"]
        checks["column_added"] = True
        try:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            if "schema_migrations" in tables:
                names = {row[0] for row in connection.execute("SELECT name FROM schema_migrations")}
                checks["migration_recorded"] = MIGRATION in names
        except sqlite3.Error:
            pass
        if not checks["migration_recorded"]:
            notes.append(f"{MIGRATION} is not recorded in schema_migrations")
        rows = connection.execute(
            f'SELECT {", ".join(STARTING_COLUMNS)}, "{columns[COLUMN]}" FROM users'
        ).fetchall()
        found = {row[0]: row[1:-1] for row in rows}
        if found != expected:
            missing = len(set(expected) - set(found))
            extra = len(set(found) - set(expected))
            changed = sum(1 for key in set(found) & set(expected) if found[key] != expected[key])
            notes.append(f"user rows differ from the starting data: {missing} missing, {extra} extra, {changed} changed")
            return checks, notes
        wrong = [row[0] for row in rows if as_flag(row[-1]) is not (row[VERIFIED_AT] is not None)]
        if wrong:
            notes.append(f"{len(wrong)} of {len(rows)} rows have {COLUMN} not matching verified_at, e.g. id {wrong[0]}")
        checks["backfilled"] = not wrong
    finally:
        connection.close()
    return checks, notes


def main():
    cell = pathlib.Path(sys.argv[1]).resolve()
    repo = cell / "repo"
    work = cell / "out" / "hidden"
    if work.exists():
        shutil.rmtree(work)
    (work / "tmp").mkdir(parents=True)
    env = {**os.environ, "TMPDIR": str(work / "tmp"), "PYTHONDONTWRITEBYTECODE": "1"}
    checks = {"column_added": False, "backfilled": False, "migration_recorded": False}
    notes = []
    try:
        expected = baseline_rows(work, env)
        path = snapshot(repo, work)
        if path is None:
            notes.append(f"{DATABASE} is missing")
        else:
            checks, notes = inspect(path, expected)
    except (sqlite3.Error, OSError, RuntimeError) as error:
        notes.append(f"{type(error).__name__}: {error}")

    copy = work / "repo"
    shutil.copytree(repo, copy, ignore=shutil.ignore_patterns(".git", "__pycache__", "data"), symlinks=True)
    code, _, _ = run([sys.executable, "-I", "-m", "unittest", "discover", "-q"], copy, env)
    checks["visible_tests_pass"] = code == 0

    print(json.dumps({"checks": checks, "notes": " | ".join(notes)[:600]}))


if __name__ == "__main__":
    main()
