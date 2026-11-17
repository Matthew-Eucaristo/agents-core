import argparse
import json
import pathlib
import sys

import kit

RESULTS = pathlib.Path(__file__).resolve().parent / "results"
TASKS = pathlib.Path(__file__).resolve().parent / "tasks"


def key_of(record):
    return (record["task"], record["variant"], record["model"], record["rep"])


def prepare(run, variants=None, tasks=None):
    out_dir = kit.EVAL_ROOT / "judge" / run
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("*.json"):
        stale.unlink()
    verdicts = RESULTS / f"{run}.judge.jsonl"
    judged = set()
    if verdicts.exists():
        judged = {tuple(json.loads(line)["key"]) for line in verdicts.read_text().splitlines()}
    rubrics = {}
    for task_file in TASKS.glob("*/task.json"):
        task = json.loads(task_file.read_text())
        if task.get("report_rubric"):
            rubrics[task["id"]] = task["report_rubric"]
    index = {}
    seen = set()
    for line in (RESULTS / f"{run}.jsonl").read_text().splitlines():
        record = json.loads(line)
        key = key_of(record)
        if record.get("infra_failure") or record["task"] not in rubrics or key in judged or key in seen:
            continue
        if variants and record["variant"] not in variants:
            continue
        if tasks and record["task"] not in tasks:
            continue
        seen.add(key)
        number = f"{len(index) + 1:04d}"
        rubric = rubrics[record["task"]]
        index[number] = {"key": list(key), "pass_if": {q["id"]: q["pass_if"] for q in rubric}}
        item = {"questions": [{"id": q["id"], "question": q["question"]} for q in rubric], "message": record["final"]}
        (out_dir / f"item-{number}.json").write_text(json.dumps(item))
    (out_dir / "index.json").write_text(json.dumps(index))
    print(json.dumps({"dir": str(out_dir), "count": len(index), "answers_file": str(out_dir / "answers.json")}))


def merge(run):
    out_dir = kit.EVAL_ROOT / "judge" / run
    index = json.loads((out_dir / "index.json").read_text())
    judged = json.loads((out_dir / "answers.json").read_text())
    if not judged["clean_run"]:
        sys.exit("judges in this run received a message that is not part of the benchmark; prepare and run it again")
    answers = judged["answers"]
    written = 0
    with (RESULTS / f"{run}.judge.jsonl").open("a") as log:
        for entry in answers:
            meta = index.get(entry["item"])
            if not meta:
                continue
            given = {a["id"]: a["answer"] for a in entry["answers"]}
            rubric = {name: given.get(name) == expected for name, expected in meta["pass_if"].items()}
            log.write(json.dumps({"key": meta["key"], "rubric": rubric}) + "\n")
            written += 1
    print(json.dumps({"merged": written}))


def prepare_controls():
    out_dir = kit.EVAL_ROOT / "judge" / "controls"
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("*.json"):
        stale.unlink()
    index = {}
    for task_file in sorted(TASKS.glob("*/task.json")):
        task = json.loads(task_file.read_text())
        names = sorted({name for q in task.get("report_rubric", []) for name in q.get("controls", {})})
        for name in names:
            final = task_file.parent / "ref" / name / "final.txt"
            questions = [q for q in task.get("report_rubric", []) if name in q.get("controls", {})]
            if not questions or not final.exists():
                continue
            number = f"{len(index) + 1:04d}"
            index[number] = {"task": task["id"], "ref": name, "expected": {q["id"]: q["controls"][name] for q in questions}}
            item = {"questions": [{"id": q["id"], "question": q["question"]} for q in questions], "message": final.read_text()}
            (out_dir / f"item-{number}.json").write_text(json.dumps(item))
    (out_dir / "index.json").write_text(json.dumps(index))
    print(json.dumps({"dir": str(out_dir), "count": len(index), "answers_file": str(out_dir / "answers.json")}))


def check_controls():
    out_dir = kit.EVAL_ROOT / "judge" / "controls"
    index = json.loads((out_dir / "index.json").read_text())
    judged = json.loads((out_dir / "answers.json").read_text())
    if not judged["clean_run"]:
        sys.exit("judges in this run received a message that is not part of the benchmark; prepare and run it again")
    given = {entry["item"]: {a["id"]: a["answer"] for a in entry["answers"]} for entry in judged["answers"]}
    total = 0
    wrong = []
    for number, meta in index.items():
        for question, expected in meta["expected"].items():
            total += 1
            answer = given.get(number, {}).get(question)
            if answer != expected:
                wrong.append(f"{meta['task']} ref/{meta['ref']} {question}: judge said {answer}, label says {expected}")
    for line in wrong:
        print("MISMATCH " + line)
    print(json.dumps({"agreed": total - len(wrong), "of": total}))
    return 1 if wrong else 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["prepare", "merge", "prepare-controls", "check-controls"])
    parser.add_argument("run", nargs="?")
    parser.add_argument("--variants", nargs="*", help="prepare only these variants")
    parser.add_argument("--tasks", nargs="*", help="prepare only these task ids")
    args = parser.parse_args()
    if args.command == "prepare-controls":
        return prepare_controls() or 0
    if args.command == "check-controls":
        return check_controls()
    if not args.run:
        parser.error("prepare and merge need a run name")
    if args.command == "prepare":
        prepare(args.run, args.variants, args.tasks)
    else:
        merge(args.run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
