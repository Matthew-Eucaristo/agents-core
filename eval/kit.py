import collections
import json
import os
import pathlib
import re
import shutil
import signal
import subprocess
import time

REAL_HOME = pathlib.Path.home().resolve()
EVAL_ROOT = pathlib.Path(os.environ.get("ACORE_EVAL_ROOT", "/private/tmp/acore-eval")).resolve()
OPENCODE_CACHE = REAL_HOME / ".cache" / "opencode"

NEUTRAL_GIT = {
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "dev",
    "GIT_AUTHOR_EMAIL": "dev@example.invalid",
    "GIT_COMMITTER_NAME": "dev",
    "GIT_COMMITTER_EMAIL": "dev@example.invalid",
}

CODE_SUFFIXES = {".py", ".js", ".ts", ".tsx", ".jsx", ".sh", ".go", ".rs", ".java", ".rb", ".c", ".h"}
COMMENT_LINE = re.compile(r"^\s*(#(?!!)|//|/\*|\*\s|<!--)")
SUPPRESSION = re.compile(
    r"noqa|type:\s*ignore|lint:\s*(allow|ignore|disable)|eslint-disable|ts-ignore|ts-expect-error|pylint:\s*disable",
    re.I,
)
WAITING = re.compile(r"\bsleep\s*\(|\bretr(y|ies|ying)\b|\bbackoff\b|unittest\.skip|\bskipTest\b|@skip", re.I)


def git(repo, *args, check=True):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        env={**os.environ, **NEUTRAL_GIT},
        capture_output=True,
        text=True,
        check=check,
    )


def load_task(task_dir):
    task_dir = pathlib.Path(task_dir).resolve()
    task = json.loads((task_dir / "task.json").read_text())
    task["dir"] = task_dir
    return task


def user_text(line):
    entry = json.loads(line)
    if entry.get("type") != "user":
        return None
    content = entry["message"]["content"]
    if isinstance(content, list):
        content = "\n".join(part.get("text", "") for part in content if part.get("type") == "text")
    content = content.strip()
    return None if not content or content.startswith("<system-reminder>") else content


def require_single_messages(transcripts):
    logs = sorted(pathlib.Path(transcripts).expanduser().glob("agent-*.jsonl"))
    if not logs:
        raise SystemExit(f"no agent transcripts in {transcripts}: pass the Transcript dir that the Workflow result printed")
    stray = []
    for log in logs:
        said = [text for text in map(user_text, log.read_text().splitlines()) if text]
        if len(said) != 1:
            stray.append(f"{log.name} received {len(said)} messages; the first begins: {said[0][:160] if said else ''}")
    if stray:
        print("\n".join(stray))
        raise SystemExit(f"{len(stray)} of {len(logs)} agents received a message that is not part of the benchmark; nothing recorded")


def apply_overlay(repo, overlay):
    overlay = pathlib.Path(overlay)
    for source in overlay.rglob("*"):
        relative = source.relative_to(overlay)
        if source.is_dir() or relative.parts[0] in {"_delete.txt", "final.txt"}:
            continue
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    deletions = overlay / "_delete.txt"
    if deletions.exists():
        for line in deletions.read_text().splitlines():
            victim = repo / line.strip()
            if not line.strip():
                continue
            if victim.is_dir():
                shutil.rmtree(victim)
            elif victim.exists():
                victim.unlink()


def build_cell(task, cell_dir, variant_file=None, overlay=None):
    cell = pathlib.Path(cell_dir).resolve()
    if cell.exists():
        shutil.rmtree(cell)
    (cell / "out").mkdir(parents=True)
    (cell / "home").mkdir()
    for name in ("data", "state", "config"):
        (cell / "xdg" / name).mkdir(parents=True)
    repo = cell / "repo"
    shutil.copytree(task["dir"] / "repo", repo)
    setup = task["dir"] / "setup.py"
    if setup.exists():
        subprocess.run(["python3", "-I", str(setup), str(repo)], check=True, timeout=180)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "initial")
    (cell / "out" / "base.txt").write_text(git(repo, "rev-parse", "HEAD").stdout.strip())
    after_commit = task["dir"] / "after_commit.py"
    if after_commit.exists():
        subprocess.run(
            ["python3", "-I", str(after_commit), str(repo)],
            check=True,
            timeout=180,
            env={**os.environ, **NEUTRAL_GIT},
        )
    if variant_file:
        target = cell / "home" / ".agents" / "AGENTS.md"
        target.parent.mkdir(parents=True)
        shutil.copyfile(variant_file, target)
    if overlay:
        apply_overlay(repo, overlay)
        final = pathlib.Path(overlay) / "final.txt"
        (cell / "out" / "final.txt").write_text(final.read_text() if final.exists() else "")
    return cell


def sandbox_profile(cell, readable=()):
    cell = pathlib.Path(cell).resolve()
    allowed_reads = " ".join(
        f'(subpath "{pathlib.Path(p).resolve()}")' for p in (OPENCODE_CACHE, cell, *readable)
    )
    return "\n".join(
        [
            "(version 1)",
            "(allow default)",
            f'(deny file-read* (subpath "{REAL_HOME}") (subpath "/private/tmp"))',
            f'(allow file-read-metadata (subpath "{REAL_HOME}") (subpath "/private/tmp"))',
            f"(allow file-read* {allowed_reads})",
            '(deny file-write* (subpath "/Users") (subpath "/private/tmp") (subpath "/Applications")'
            ' (subpath "/Library") (subpath "/opt") (subpath "/usr") (subpath "/Volumes"))',
            f'(allow file-write* (subpath "{OPENCODE_CACHE}") (subpath "{cell}"))',
            "",
        ]
    )


def run_confined(command, cell, cwd, env, timeout, readable=(), stdout=None, stderr=None):
    profile = pathlib.Path(cell) / "out" / f"sandbox-{len(readable)}.sb"
    profile.write_text(sandbox_profile(cell, readable))
    started = time.monotonic()
    process = subprocess.Popen(
        ["sandbox-exec", "-f", str(profile), *command],
        cwd=str(cwd),
        env={**env, "PWD": str(cwd)},
        stdout=stdout or subprocess.PIPE,
        stderr=stderr or subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    timed_out = False
    try:
        out, err = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGKILL)
        out, err = process.communicate()
    return {
        "exit": process.returncode,
        "timed_out": timed_out,
        "seconds": round(time.monotonic() - started, 1),
        "stdout": out,
        "stderr": err,
    }


def agent_env(cell):
    cell = pathlib.Path(cell)
    return {
        **os.environ,
        **NEUTRAL_GIT,
        "OPENCODE_TEST_HOME": str(cell / "home"),
        "XDG_DATA_HOME": str(cell / "xdg" / "data"),
        "XDG_STATE_HOME": str(cell / "xdg" / "state"),
        "XDG_CONFIG_HOME": str(cell / "xdg" / "config"),
        "XDG_CACHE_HOME": str(REAL_HOME / ".cache"),
        "OPENCODE_DISABLE_AUTOUPDATE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def run_opencode(cell, model, prompt, timeout):
    cell = pathlib.Path(cell)
    events = cell / "out" / "events.jsonl"
    errors = cell / "out" / "stderr.txt"
    with events.open("w") as out, errors.open("w") as err:
        result = run_confined(
            ["opencode", "run", "--standalone", "--archived", "--auto", "--format", "json", "-m", model, prompt],
            cell,
            cell / "repo",
            agent_env(cell),
            timeout,
            stdout=out,
            stderr=err,
        )
    summary = parse_events(events)
    summary.update(exit=result["exit"], timed_out=result["timed_out"], seconds=result["seconds"], model=model)
    (cell / "out" / "final.txt").write_text(summary.pop("final"))
    return summary


def parse_events(path):
    kinds = collections.Counter()
    tokens = collections.Counter()
    tail, tools, steps, cost, failures = [], 0, 0, 0.0, []
    for line in pathlib.Path(path).read_text().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        kind = str(event.get("type", ""))
        part = event.get("part") or {}
        kinds[kind] += 1
        if kind == "text" and part.get("text"):
            tail.append(part["text"])
        elif "tool" in kind:
            tools += 1
            tail = []
        elif kind == "step_finish":
            steps += 1
            used = part.get("tokens") or {}
            cache = used.get("cache") or {}
            tokens["input"] += used.get("input", 0)
            tokens["output"] += used.get("output", 0)
            tokens["reasoning"] += used.get("reasoning", 0)
            tokens["cache_read"] += cache.get("read", 0)
            tokens["cache_write"] += cache.get("write", 0)
            cost += part.get("cost") or 0
        elif "error" in kind:
            failures.append(json.dumps(event)[:400])
    return {
        "final": "\n".join(tail).strip(),
        "event_kinds": dict(kinds),
        "tokens": dict(tokens),
        "tool_calls": tools,
        "steps": steps,
        "cost": round(cost, 6),
        "errors": failures[:5],
    }


def diff_metrics(cell):
    cell = pathlib.Path(cell)
    repo = cell / "repo"
    base = (cell / "out" / "base.txt").read_text().strip()
    git(repo, "add", "-A")
    patch = git(repo, "diff", "--cached", base).stdout
    (cell / "out" / "diff.patch").write_text(patch)
    names = [line.split("\t") for line in git(repo, "diff", "--cached", "--name-status", base).stdout.splitlines()]
    counts = collections.Counter()
    current = pathlib.PurePath("")
    for line in patch.splitlines():
        if line.startswith("+++ "):
            current = pathlib.PurePath(line[6:] if line.startswith("+++ b/") else "")
            continue
        if line.startswith("+") and not line.startswith("+++"):
            added = line[1:]
            counts["lines_added"] += 1
            if current.suffix in CODE_SUFFIXES and COMMENT_LINE.match(added):
                counts["comment_lines_added"] += 1
            if SUPPRESSION.search(added):
                counts["suppressions_added"] += 1
            if current.suffix in CODE_SUFFIXES and WAITING.search(added):
                counts["waiting_added"] += 1
        elif line.startswith("-") and not line.startswith("---"):
            counts["lines_removed"] += 1
    metrics = {
        "files_changed": len(names),
        "files_created": [n[-1] for n in names if n[0].startswith("A")],
        "files_deleted": [n[-1] for n in names if n[0].startswith("D")],
        "markdown_created": [n[-1] for n in names if n[0].startswith("A") and n[-1].lower().endswith(".md")],
        "lines_added": counts["lines_added"],
        "lines_removed": counts["lines_removed"],
        "comment_lines_added": counts["comment_lines_added"],
        "suppressions_added": counts["suppressions_added"],
        "waiting_added": counts["waiting_added"],
    }
    (cell / "out" / "diff.json").write_text(json.dumps(metrics, indent=1))
    return metrics


def score_cell(task, cell):
    cell = pathlib.Path(cell)
    result = run_confined(
        ["python3", "-I", str(task["dir"] / "score.py"), str(cell)],
        cell,
        cell,
        {**os.environ, **NEUTRAL_GIT, "PYTHONDONTWRITEBYTECODE": "1"},
        240,
        readable=(task["dir"],),
    )
    try:
        score = json.loads(result["stdout"].strip().splitlines()[-1])
    except (ValueError, IndexError):
        score = {"checks": {}, "notes": f"scorer failed: exit {result['exit']}: {result['stderr'][-400:]}"}
    checks = score.get("checks", {})
    score["primary_pass"] = bool(task["primary"]) and all(checks.get(name) is True for name in task["primary"])
    (cell / "out" / "score.json").write_text(json.dumps(score, indent=1))
    return score
