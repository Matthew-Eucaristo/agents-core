import glob
import json
import os
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
CELL = re.compile(r"(/[^\s'\"]*/\.runs/[^/\s'\"]+/cells/w[0-9a-f]{12})")
MUTATING = re.compile(
    r"\b(rm|rmdir|mv|unlink|truncate|shred|cp|touch|mkdir|chmod|ln|tee|install)\b"
    r"|\bfind\b[^|;&]*(-delete|-exec\s+rm)"
    r"|\bgit\b[^|;&]*\b(clean|reset|checkout|restore|stash|rm|commit|push|rebase|apply|am|merge|switch)\b"
    r"|\bsed\b[^|;&]*\s-i"
    r"|[^0-9&]>{1,2}\s*[^&\s]"
    r"|rmtree|\.unlink\(|os\.remove|\.write_text\(|\.write_bytes\(|open\([^)]*['\"][wa]"
)
ABSOLUTE = re.compile(r"(?<![\w.-])(/[^\s'\";|&)]+)")


def own_cell(event):
    agent = event.get("agent_id")
    main = event.get("transcript_path")
    if not agent or not main:
        return None
    root = pathlib.Path(main).with_suffix("")
    for path in glob.glob(str(root / "subagents" / "**" / f"agent-{agent}.jsonl"), recursive=True):
        with open(path) as handle:
            for line in handle:
                found = CELL.search(line)
                if found:
                    return found.group(1)
    return None


def inside(path, cell_root):
    return os.path.realpath(path).startswith(os.path.realpath(cell_root) + os.sep) or os.path.realpath(path) == os.path.realpath(cell_root)


def verdict(event, cell_root):
    tool = event.get("tool_name")
    data = event.get("tool_input") or {}
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        target = data.get("file_path") or data.get("notebook_path") or ""
        if cell_root and inside(target, cell_root):
            return None
        return "escape", f"{target} is outside your repository {cell_root}/repo"
    if tool != "Bash":
        return None
    command = data.get("command", "")
    if not MUTATING.search(command):
        return None
    paths = [match.group(1) for match in ABSOLUTE.finditer(command)]
    repo = os.path.realpath(REPO)
    for path in paths:
        real = os.path.realpath(path)
        if (real == repo or real.startswith(repo + os.sep)) and not (cell_root and inside(real, cell_root)):
            return "escape", f"{path} is outside your repository {cell_root}/repo"
    if cell_root and any(inside(path, cell_root) for path in paths):
        return None
    anchored = re.match(r"\s*cd\s+(/[^\s;&|]+)", command)
    if anchored and not os.path.realpath(anchored.group(1)).startswith(repo):
        return None
    return "unanchored", f"this command would change files in {repo}, not your repository; run it with cd {cell_root}/repo"


def main():
    event = json.load(sys.stdin)
    if event.get("agent_type") != "acore-eval":
        return 0
    found = own_cell(event)
    if found is None:
        print("benchmark guard: cannot tell which cell this agent owns", file=sys.stderr)
        return 2
    cell_root = found
    result = verdict(event, cell_root)
    if result is None:
        return 0
    kind, reason = result
    with open(pathlib.Path(cell_root) / "out" / "guard.jsonl", "a") as log:
        log.write(json.dumps({"kind": kind, "tool": event.get("tool_name"), "input": event.get("tool_input")}) + "\n")
    print(f"blocked: {reason}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
