import argparse
import collections
import json
import pathlib
import statistics
import sys

RESULTS = pathlib.Path(__file__).resolve().parent / "results"


def key_of(record):
    return (record["task"], record["variant"], record["model"], record["rep"])


def load(run_names):
    latest = {}
    judged = {}
    for name in run_names:
        for line in (RESULTS / f"{name}.jsonl").read_text().splitlines():
            record = json.loads(line)
            if record.get("infra_failure"):
                latest.setdefault(key_of(record), record)
            else:
                latest[key_of(record)] = record
        verdicts = RESULTS / f"{name}.judge.jsonl"
        if verdicts.exists():
            for line in verdicts.read_text().splitlines():
                verdict = json.loads(line)
                judged[tuple(verdict["key"])] = verdict["rubric"]
    records = list(latest.values())
    for record in records:
        record["rubric"] = judged.get(key_of(record), {})
    return records


def outcome(record, with_rubric):
    if not record["score"]["primary_pass"]:
        return False
    return all(record["rubric"].values()) if with_rubric and record["rubric"] else True


def rate(records, with_rubric):
    valid = [r for r in records if not r.get("infra_failure")]
    return sum(1 for r in valid if outcome(r, with_rubric)), len(valid)


def table(records, row_key, column_key, with_rubric):
    rows = sorted({r[row_key] for r in records})
    columns = sorted({r[column_key] for r in records})
    width = max(len(str(row)) for row in rows) + 2
    lines = [" " * width + "".join(f"{str(c)[-13:]:>14}" for c in columns)]
    for row in rows:
        cells = []
        for column in columns:
            passed, total = rate([r for r in records if r[row_key] == row and r[column_key] == column], with_rubric)
            cells.append(f"{passed}/{total}" if total else "-")
        lines.append(f"{str(row):<{width}}" + "".join(f"{c:>14}" for c in cells))
    return "\n".join(lines)


def mean(values):
    values = list(values)
    return round(statistics.fmean(values), 1) if values else 0


def by_variant(records, with_rubric):
    out = {}
    for variant in sorted({r["variant"] for r in records}):
        group = [r for r in records if r["variant"] == variant and not r.get("infra_failure")]
        passed, total = rate(group, with_rubric)
        tokens = [r["run"]["tokens"] for r in group]
        out[variant] = {
            "pass": f"{passed}/{total}",
            "pass_rate": round(passed / total, 3) if total else None,
            "fresh_tokens": mean(t.get("input", 0) + t.get("output", 0) + t.get("reasoning", 0) for t in tokens),
            "cache_read": mean(t.get("cache_read", 0) for t in tokens),
            "steps": mean(r["run"]["steps"] for r in group),
            "seconds": mean(r["run"]["seconds"] for r in group),
            "comment_lines": mean(r["diff"]["comment_lines_added"] for r in group),
            "new_markdown_cells": sum(1 for r in group if r["diff"]["markdown_created"]),
            "suppression_cells": sum(1 for r in group if r["diff"]["suppressions_added"]),
        }
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", nargs="+")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-rubric", action="store_true", help="count scripted checks only")
    parser.add_argument("--tasks", nargs="*", help="limit to these task ids")
    args = parser.parse_args()
    records = [r for r in load(args.runs) if not args.tasks or r["task"] in args.tasks]
    if not records:
        print("no records")
        return 1
    with_rubric = not args.no_rubric
    infra = collections.Counter(r["infra_failure"] for r in records if r.get("infra_failure"))
    if args.json:
        print(json.dumps({"cells": len(records), "infra": dict(infra), "by_variant": by_variant(records, with_rubric)}, indent=1))
        return 0
    print(f"cells={len(records)} infra={dict(infra)} rubric={'on' if with_rubric else 'off'}\n")
    print("pass by task x variant\n" + table(records, "task", "variant", with_rubric) + "\n")
    print("pass by model x variant\n" + table(records, "model", "variant", with_rubric) + "\n")
    for variant, stats in by_variant(records, with_rubric).items():
        print(variant, json.dumps(stats))
    return 0


if __name__ == "__main__":
    sys.exit(main())
