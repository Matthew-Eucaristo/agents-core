import json
import pathlib
import subprocess
import sys

import kit


def main():
    task = kit.load_task(sys.argv[1])
    root = kit.EVAL_ROOT / "validate" / task["id"]
    expectations = {"start": False, "good": True, "bad": False}
    failures = []
    for name, expected in expectations.items():
        overlay = None if name == "start" else task["dir"] / "ref" / name
        if overlay is not None and not overlay.is_dir():
            failures.append(f"missing ref/{name}")
            continue
        cell = kit.build_cell(task, root / name, overlay=overlay)
        if name == "start":
            (cell / "out" / "final.txt").write_text("")
        kit.diff_metrics(cell)
        score = kit.score_cell(task, cell)
        status = "ok" if score["primary_pass"] is expected else "WRONG"
        if status != "ok":
            failures.append(f"{name}: primary_pass={score['primary_pass']} expected {expected}")
        print(f"{name:5} primary_pass={score['primary_pass']!s:5} expected={expected!s:5} {status}  checks={json.dumps(score.get('checks'))}")
        if score.get("notes"):
            print(f"      notes: {score['notes']}")
    unknown = [name for name in task["primary"] if not name]
    if unknown or not task["primary"]:
        failures.append("task.json has no primary checks")
    visible = subprocess.run(
        ["python3", "-I", "-m", "unittest", "discover", "-q"],
        cwd=root / "start" / "repo",
        capture_output=True,
        text=True,
        timeout=180,
    )
    print(f"start repo visible tests exit={visible.returncode}")
    print("VALID" if not failures else "INVALID: " + "; ".join(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
