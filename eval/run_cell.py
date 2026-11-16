import argparse
import json
import pathlib
import sys

import kit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--variant", required=True, help="path to an instruction file, or 'none'")
    parser.add_argument("--model", required=True)
    parser.add_argument("--cell", required=True)
    parser.add_argument("--timeout", type=int, default=None)
    args = parser.parse_args()

    task = kit.load_task(args.task)
    variant = None if args.variant == "none" else pathlib.Path(args.variant).resolve()
    cell = kit.build_cell(task, args.cell, variant_file=variant)
    run = kit.run_opencode(cell, args.model, task["prompt"], args.timeout or task.get("timeout_s", 900))
    diff = kit.diff_metrics(cell)
    score = kit.score_cell(task, cell)
    record = {
        "task": task["id"],
        "variant": "none" if variant is None else variant.stem,
        "model": args.model,
        "run": run,
        "diff": diff,
        "score": score,
    }
    (cell / "out" / "record.json").write_text(json.dumps(record, indent=1))
    print(json.dumps({k: record[k] for k in ("task", "variant", "model")} | {
        "primary_pass": score["primary_pass"],
        "checks": score.get("checks"),
        "seconds": run["seconds"],
        "steps": run["steps"],
        "tokens": run["tokens"],
        "exit": run["exit"],
        "timed_out": run["timed_out"],
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
