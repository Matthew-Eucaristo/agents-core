import argparse
import json
import pathlib
import sys

import kit

RESULTS = pathlib.Path(__file__).resolve().parent / "results"
TASKS = pathlib.Path(__file__).resolve().parent / "tasks"


def key_of(record):
    return (record["task"], record["variant"], record["model"], record["rep"])


def prepare(run):
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
    answers = json.loads((out_dir / "answers.json").read_text())
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["prepare", "merge"])
    parser.add_argument("run")
    args = parser.parse_args()
    (prepare if args.command == "prepare" else merge)(args.run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
