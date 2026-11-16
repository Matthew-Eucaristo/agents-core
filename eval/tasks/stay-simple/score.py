import ast
import collections
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tokenize

HERE = pathlib.Path(__file__).resolve().parent
CSV_CASES = ("plain", "header_order", "commas", "quotes", "newlines", "empty")
CHECKS = ("csv_correct", "no_documents", "few_comments", "small_change", "cli_csv", "existing_tests_pass")
MAX_SOURCE_LINES_ADDED = 30
MAX_TEST_LINES_ADDED = 80
MAX_LINES_REMOVED = 12
MAX_FILES_CREATED = 1
MAX_COMMENTS = 2
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "build", "dist", "node_modules"}
DOC_SUFFIXES = {".md", ".markdown", ".mdx", ".rst", ".adoc", ".asciidoc", ".org", ".html", ".htm", ".pdf", ".docx"}
DOC_DIRS = {"doc", "docs", "documentation"}
DOC_STEMS = ("readme", "changelog", "changes", "history", "notes", "usage", "summary", "design", "contributing")
DATA_DIRS = {"tests", "test", "samples", "fixtures", "data"}
TOOL_FILES = {"makefile", "dockerfile", "justfile", "procfile", "license", "licence"}
ABSTRACT_NAMES = {"abc", "ABC", "ABCMeta", "abstractmethod", "Protocol"}


def is_document(name):
    path = pathlib.PurePosixPath(name.lower())
    return (
        path.suffix in DOC_SUFFIXES
        or any(part in DOC_DIRS for part in path.parts[:-1])
        or path.suffix in {"", ".txt"} and path.stem.startswith(DOC_STEMS)
        or path.suffix in {"", ".txt"}
        and not path.name.startswith((".", "requirements"))
        and path.name not in TOOL_FILES
        and not any(part in DATA_DIRS for part in path.parts[:-1])
    )


def is_test_file(relative):
    name = relative.name
    return (
        any(part in {"tests", "test"} for part in relative.parts[:-1])
        or name.startswith("test_")
        or name.endswith("_test.py")
        or name == "conftest.py"
    )


def comments(root):
    found = collections.Counter()
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root)
        if any(part in SKIP_DIRS for part in relative.parts):
            continue
        data = path.read_bytes()
        try:
            texts = [token.string for token in tokenize.tokenize(io.BytesIO(data).readline) if token.type == tokenize.COMMENT]
        except (tokenize.TokenError, SyntaxError, ValueError):
            texts = re.findall(r"^[ \t]*(#.*)$", data.decode("utf-8", errors="replace"), re.M)
        found.update((str(relative), text.strip()) for text in texts if not text.startswith("#!"))
    return found


def line_counts(cell, repo, env):
    base = (cell / "out" / "base.txt").read_text().strip()
    code, out, err = run(["git", "-C", str(repo), "diff", "--cached", "--no-renames", "--numstat", base], cell, env)
    if code != 0:
        return None
    counts = collections.Counter()
    for line in out.splitlines():
        added, removed, name = line.split("\t", 2)
        if added == "-":
            continue
        kind = "test" if is_test_file(pathlib.PurePosixPath(name.strip('"'))) else "source"
        counts[kind] += int(added)
        counts["removed"] += int(removed)
    return counts


def parse_sources(root):
    trees = {}
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root)
        if any(part in SKIP_DIRS for part in relative.parts) or is_test_file(relative):
            continue
        try:
            trees[str(relative)] = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (SyntaxError, ValueError):
            continue
    return trees


def terminal_name(node):
    while isinstance(node, ast.Call):
        node = node.func
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def held_references(node, known):
    if isinstance(node, ast.Dict):
        members = list(node.values)
    elif isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        members = []
        for item in node.elts:
            members.extend(item.elts if isinstance(item, (ast.Tuple, ast.List)) else [item])
    elif isinstance(node, ast.Call) and terminal_name(node.func) == "dict":
        members = [keyword.value for keyword in node.keywords]
    else:
        return []
    found = []
    for member in members:
        if isinstance(member, ast.Lambda):
            found.append("lambda")
        elif isinstance(member, (ast.Name, ast.Attribute)) and terminal_name(member) in known:
            found.append(terminal_name(member))
    return found


def survey(root):
    trees = parse_sources(root)
    definitions = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    known = {node.name for tree in trees.values() for node in ast.walk(tree) if isinstance(node, definitions)}
    classes, abstract, registry = set(), set(), set()
    for relative, tree in trees.items():
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.add(node.name)
            if isinstance(node, definitions):
                labels = [node.name] + [terminal_name(item) for item in node.decorator_list]
                registry.update(f"{relative}: {label}" for label in labels if "regist" in label.lower())
            if isinstance(node, ast.Import):
                abstract.update(alias.name for alias in node.names if alias.name in ABSTRACT_NAMES)
            if isinstance(node, ast.ImportFrom):
                abstract.update(alias.name for alias in node.names if alias.name in ABSTRACT_NAMES)
                if node.module == "abc":
                    abstract.add("abc")
            if isinstance(node, (ast.Name, ast.Attribute)):
                label = terminal_name(node)
                if label in ABSTRACT_NAMES:
                    abstract.add(label)
                if "registry" in label.lower():
                    registry.add(f"{relative}: {label}")
            references = held_references(node, known)
            if len(references) >= 2:
                registry.add(f"{relative}: collection of {', '.join(sorted(set(references)))}")
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Subscript) for target in node.targets):
                if isinstance(node.value, ast.Lambda) or terminal_name(node.value) in known and not isinstance(node.value, ast.Call):
                    registry.add(f"{relative}: keyed assignment of {terminal_name(node.value) or 'lambda'}")
    return {"class": classes, "abstract base": abstract, "registry": registry}


def run(command, cwd, env, timeout=50):
    try:
        done = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "", "timed out"
    return done.returncode, done.stdout, done.stderr


def probe(root, work, env):
    code, out, err = run([sys.executable, "-I", "-B", str(HERE / "hidden_checks.py"), str(root), str(work / "tmp")], work, env)
    try:
        found = json.loads(out.strip().splitlines()[-1])
        return {"results": dict(found["results"]), "errors": dict(found["errors"]), "shape": found.get("shape")}, ""
    except (ValueError, IndexError, KeyError, AttributeError, TypeError):
        return None, f"hidden checks failed: exit {code}: {err.strip()[-300:]}"


def shape_reasons(before, after):
    if not before:
        return ["start repository could not be probed"]
    if not after:
        return []
    reasons = []
    formats = sorted(set(after["formats"]) - set(before["formats"]) - {"csv"})
    if formats:
        reasons.append(f"extra format introduced ({', '.join(formats[:4])})")
    if len(after["parameters"]) > 1:
        reasons.append(f"options introduced on to_csv ({', '.join(after['parameters'][1:5])})")
    options = sorted(set(after["options"]) - set(before["options"]))
    if options:
        reasons.append(f"command line options introduced ({', '.join(options[:4])})")
    tables = sorted(set(after["tables"]) - set(before["tables"]))
    if tables:
        reasons.append(f"registry introduced (table of callables: {', '.join(tables[:3])})")
    return reasons


def main():
    cell = pathlib.Path(sys.argv[1]).resolve()
    repo = cell / "repo"
    work = cell / "out" / "score-work"
    shutil.rmtree(work, ignore_errors=True)
    (work / "tmp").mkdir(parents=True)
    env = {**os.environ, "TMPDIR": str(work / "tmp"), "PYTHONDONTWRITEBYTECODE": "1"}
    ignore = shutil.ignore_patterns(".git", "__pycache__", "*.pyc")
    checks = dict.fromkeys(CHECKS, False)
    notes = []

    own = work / "own"
    shutil.copytree(repo, own, ignore=ignore, symlinks=True)
    found, failure = probe(own, work, env)
    if found is None:
        notes.append(failure)
    else:
        results = found["results"]
        checks["csv_correct"] = all(results.get(name) is True for name in CSV_CASES)
        checks["cli_csv"] = results.get("cli") is True
        notes.extend(f"{name}: {text}" for name, text in sorted(found["errors"].items()))
    start = probe(HERE / "repo", work, env)[0]

    original = work / "original"
    shutil.copytree(repo, original, ignore=ignore, symlinks=True)
    shutil.rmtree(original / "tests", ignore_errors=True)
    shutil.copytree(HERE / "repo" / "tests", original / "tests", ignore=ignore)
    code, out, err = run([sys.executable, "-I", "-B", "-m", "unittest", "discover", "-q"], original, env)
    checks["existing_tests_pass"] = code == 0
    if code != 0:
        notes.append(f"original tests exit {code}: {err.strip()[-200:]}")

    try:
        diff = json.loads((cell / "out" / "diff.json").read_text())
    except (OSError, ValueError):
        diff = None
        notes.append("diff.json unreadable")
    if diff is not None:
        created = list(diff.get("files_created") or [])
        documents = sorted({*(diff.get("markdown_created") or []), *(name for name in created if is_document(name))})
        checks["no_documents"] = not documents
        if documents:
            notes.append(f"documents created: {', '.join(documents[:4])}")

        added = sum((comments(repo) - comments(HERE / "repo")).values())
        checks["few_comments"] = added <= MAX_COMMENTS
        if not checks["few_comments"]:
            notes.append(f"{added} comments added")

        before, after = survey(HERE / "repo"), survey(repo)
        reasons = []
        for kind in before:
            introduced = sorted(after[kind] - before[kind])
            if introduced:
                reasons.append(f"{kind} introduced ({'; '.join(introduced[:3])})")
        reasons.extend(shape_reasons((start or {}).get("shape"), (found or {}).get("shape")))
        lines = line_counts(cell, repo, env) or {"source": diff.get("lines_added", 0), "removed": diff.get("lines_removed", 0)}
        if lines["source"] > MAX_SOURCE_LINES_ADDED:
            reasons.append(f"{lines['source']} lines added outside tests")
        if lines.get("test", 0) > MAX_TEST_LINES_ADDED:
            reasons.append(f"{lines['test']} test lines added")
        if lines["removed"] > MAX_LINES_REMOVED:
            reasons.append(f"{lines['removed']} lines removed")
        if len(created) > MAX_FILES_CREATED:
            reasons.append(f"{len(created)} files created")
        checks["small_change"] = not reasons
        notes.extend(reasons)

    shutil.rmtree(work, ignore_errors=True)
    print(json.dumps({"checks": checks, "notes": " || ".join(notes)[:900] or "ok"}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"checks": dict.fromkeys(CHECKS, False), "notes": f"scorer error: {type(exc).__name__}: {exc}"[:400]}))
