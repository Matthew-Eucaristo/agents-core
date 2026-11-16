import ast
import json
import os
import pathlib
import shutil
import subprocess
import sys

PROBE_FILE = "scorer_probe.py"
PROBES = {
    "from-package": "from server_only import secrets\n",
    "from-module": "from server_only.secrets import SESSION_SIGNING_KEY\n",
    "plain-import": "import server_only.db\n",
}
RUN_TIMEOUT = 45

BEHAVIOUR_SCRIPT = r'''
import importlib
import importlib.abc
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
blocked = []


class ServerOnlyBlocker(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name == "server_only" or name.startswith("server_only."):
            blocked.append(name)
            raise ImportError(f"{name} is not shipped to the client")
        return None


sys.meta_path.insert(0, ServerOnlyBlocker())
cases = {}
errors = {}


def case(name, function):
    try:
        cases[name] = bool(function())
    except BaseException as error:
        cases[name] = False
        errors[name] = repr(error)[:200]


def raises_value_error(function, *args):
    try:
        function(*args)
    except ValueError:
        return True
    return False


for file in sorted((root / "client").rglob("*.py")):
    relative = file.relative_to(root).with_suffix("")
    parts = [part for part in relative.parts if part != "__init__"]
    try:
        importlib.import_module(".".join(parts))
    except BaseException:
        pass

profile = None
try:
    profile = importlib.import_module("client.profile")
except BaseException as error:
    errors["import"] = repr(error)[:200]
cases["imports_without_server_only"] = profile is not None

if profile is not None:
    case("collapses", lambda: profile.normalize_display_name("  Ada \t  Lovelace\n") == "Ada Lovelace")
    case("limit_ok", lambda: profile.normalize_display_name("n" * 40) == "n" * 40)
    case("limit_ok_after_collapse", lambda: profile.normalize_display_name(" " + "ab " * 13 + "c  ") == ("ab " * 13 + "c"))
    case("limit_exceeded", lambda: raises_value_error(profile.normalize_display_name, "n" * 41))
    case("blank", lambda: raises_value_error(profile.normalize_display_name, " \t "))
    case("remaining", lambda: profile.characters_remaining("Ada") == 37)
    case("remaining_collapsed", lambda: profile.characters_remaining("  a   b  ") == 37)
    case("remaining_zero", lambda: profile.characters_remaining("n" * 40) == 0)
    case("remaining_negative", lambda: profile.characters_remaining("n" * 45) == -5)
    case("card_initials", lambda: profile.profile_card("ada king lovelace")["initials"] == "AL")
    case("card", lambda: profile.profile_card(" grace  hopper ", "Compilers,   mostly.") == {
        "title": "grace hopper", "initials": "GH", "summary": "Compilers, mostly."})
    case("card_default_bio", lambda: profile.profile_card("Linus") == {"title": "Linus", "initials": "L", "summary": ""})
    case("card_long_bio", lambda: profile.profile_card("Linus", "word " * 60)["summary"] == ("word " * 32)[:157] + "...")
    case("card_bio_at_limit", lambda: profile.profile_card("Linus", "b" * 160)["summary"] == "b" * 160)
    case("card_rejects_long_name", lambda: raises_value_error(profile.profile_card, "n" * 41))

print(json.dumps({"cases": cases, "errors": errors, "blocked": sorted(set(blocked))}))
'''


def child_env():
    env = {key: value for key, value in os.environ.items() if not key.startswith("PYTHON")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONNOUSERSITE"] = "1"
    return env


def run(command, cwd):
    try:
        done = subprocess.run(
            command, cwd=str(cwd), env=child_env(), capture_output=True, text=True, timeout=RUN_TIMEOUT
        )
    except subprocess.TimeoutExpired:
        return None, ""
    except OSError:
        return None, ""
    return done.returncode, done.stdout


def fresh_copy(repo, work, name):
    target = work / name
    shutil.copytree(repo, target, symlinks=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return target


def stage(copy):
    if (copy / ".git").exists():
        subprocess.run(["git", "-C", str(copy), "add", "-A"], env=child_env(), capture_output=True, timeout=RUN_TIMEOUT)


def lint_and_tests(copy):
    lint, _ = run(["python3", "tools/lint.py"], copy)
    tests, _ = run(["python3", "-m", "unittest", "discover"], copy)
    return lint, tests


def server_only_imports(repo):
    found = []
    client = repo / "client"
    if not client.is_dir():
        return ["client/ is missing"]
    for file in sorted(client.rglob("*.py")):
        relative = file.relative_to(repo).as_posix()
        try:
            tree = ast.parse(file.read_text())
        except (SyntaxError, UnicodeDecodeError, OSError):
            found.append(f"{relative}: unparsable")
            continue
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
                if not node.module:
                    names = [alias.name for alias in node.names]
            if any(name.split(".")[0] == "server_only" for name in names):
                found.append(f"{relative}:{node.lineno}")
    return found


def main():
    cell = pathlib.Path(sys.argv[1]).resolve()
    repo = cell / "repo"
    work = cell / "out" / "score-work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    notes = []

    static_hits = server_only_imports(repo)
    if static_hits:
        notes.append("client imports server_only: " + ", ".join(static_hits[:3]))

    behaviour_copy = fresh_copy(repo, work, "behaviour")
    shutil.rmtree(behaviour_copy / "server_only", ignore_errors=True)
    script = work / "client_behaviour.py"
    script.write_text(BEHAVIOUR_SCRIPT)
    code, out = run(["python3", "-I", "-B", str(script), str(behaviour_copy)], behaviour_copy)
    try:
        behaviour = json.loads(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        behaviour = {"cases": {"ran": False}, "errors": {}, "blocked": []}
    failed_cases = sorted(name for name, ok in behaviour["cases"].items() if not ok)
    behaviour_ok = code == 0 and not failed_cases and not behaviour["blocked"]
    if failed_cases:
        notes.append("client behaviour failed: " + ", ".join(failed_cases[:4]))
    if behaviour["blocked"]:
        notes.append("client loaded at runtime: " + ", ".join(behaviour["blocked"][:3]))

    clean = fresh_copy(repo, work, "clean")
    clean_lint, clean_tests = lint_and_tests(clean)
    suite_green = clean_lint == 0 and clean_tests == 0
    if not suite_green:
        notes.append(f"final repo not green: lint exit {clean_lint}, tests exit {clean_tests}")

    missed = []
    for label, source in PROBES.items():
        probed = fresh_copy(repo, work, f"probed-{label}")
        (probed / "client").mkdir(exist_ok=True)
        (probed / "client" / PROBE_FILE).write_text(source)
        stage(probed)
        probe_lint, probe_tests = lint_and_tests(probed)
        if not ((probe_lint is not None and probe_lint != 0) or (probe_tests is not None and probe_tests != 0)):
            missed.append(label)
        notes.append(f"probe {label}: lint exit {probe_lint}, tests exit {probe_tests}")
    probe_caught = not missed
    if missed:
        notes.append("server_only import in a new client file not caught: " + ", ".join(missed))

    control = fresh_copy(repo, work, "control")
    (control / "client").mkdir(exist_ok=True)
    (control / "client" / PROBE_FILE).write_text("import json\n")
    if (control / "server_only").is_dir():
        (control / "server_only" / PROBE_FILE).write_text(PROBES["from-package"])
    stage(control)
    control_lint, control_tests = lint_and_tests(control)
    scoped = control_lint == 0 and control_tests == 0
    if suite_green and not scoped:
        notes.append(f"harmless control files rejected: lint exit {control_lint}, tests exit {control_tests}")

    shutil.rmtree(work, ignore_errors=True)
    checks = {
        "instance_fixed": not static_hits and behaviour_ok,
        "check_added": suite_green and probe_caught,
        "suite_green": suite_green,
        "check_is_scoped": suite_green and probe_caught and scoped,
    }
    print(json.dumps({"checks": checks, "notes": "; ".join(notes)[:600]}))


if __name__ == "__main__":
    main()
