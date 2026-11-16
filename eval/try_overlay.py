import json
import pathlib
import sys

import kit


def main():
    task = kit.load_task(sys.argv[1])
    overlay = pathlib.Path(sys.argv[2]).resolve()
    cell = kit.build_cell(task, kit.EVAL_ROOT / "try" / task["id"] / overlay.name, overlay=overlay)
    metrics = kit.diff_metrics(cell)
    score = kit.score_cell(task, cell)
    print(json.dumps({"primary_pass": score["primary_pass"], "checks": score.get("checks"), "notes": score.get("notes"), "diff": metrics}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
