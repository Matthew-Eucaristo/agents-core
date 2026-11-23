import argparse
import concurrent.futures
import hashlib
import itertools
import json
import pathlib
import sys
import threading
import time

import kit

RESULTS = pathlib.Path(__file__).resolve().parent / "results"
INFRA_MARKERS = ("no-route", "rate", "overload", "unavailable", "credential", "quota", "econn", "free-limit")
EXHAUSTED = set()
LOCK = threading.Lock()


def key_of(record):
    return (record["task"], record["variant"], record["model"], record["rep"])


def classify(run):
    text = " ".join(run["errors"]).lower()
    if "free-limit" in text or "quota" in text:
        return "exhausted"
    if run["steps"] == 0 or any(marker in text for marker in INFRA_MARKERS):
        return "infra"
    return None


def run_one(job, run_root, timeout, attempts):
    task = kit.load_task(job["task"])
    variant = None if job["variant"] == "none" else pathlib.Path(job["variant"]).resolve()
    base = {
        "task": task["id"],
        "variant": "none" if variant is None else variant.stem,
        "model": job["model"],
        "rep": job["rep"],
    }
    opaque = hashlib.sha1(json.dumps(base, sort_keys=True).encode()).hexdigest()[:12]
    cell = run_root / "cells" / f"w{opaque}"
    record = {**base, "infra_failure": "exhausted"}
    for attempt in range(attempts):
        with LOCK:
            if job["model"] in EXHAUSTED:
                return record
        kit.build_cell(task, cell, variant_file=variant)
        run = kit.run_opencode(cell, job["model"], task["prompt"], timeout or task.get("timeout_s", 900))
        record = {
            **base,
            "run": run,
            "final": (cell / "out" / "final.txt").read_text()[:8000],
            "diff": kit.diff_metrics(cell),
            "score": kit.score_cell(task, cell),
            "infra_failure": classify(run),
        }
        if record["infra_failure"] == "exhausted":
            with LOCK:
                EXHAUSTED.add(job["model"])
            return record
        if not record["infra_failure"]:
            return record
        time.sleep(30 * (attempt + 1))
    return record


def interleave(jobs):
    by_model = {}
    for job in jobs:
        by_model.setdefault(job["model"], []).append(job)
    rounds = itertools.zip_longest(*by_model.values())
    return [job for group in rounds for job in group if job is not None]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, help="run name; results go to eval/results/<run>.jsonl")
    parser.add_argument("--tasks", nargs="+", required=True)
    parser.add_argument("--variants", nargs="+", required=True)
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--reps", type=int, default=1)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument("--attempts", type=int, default=2)
    args = parser.parse_args()

    RESULTS.mkdir(exist_ok=True)
    log_path = RESULTS / f"{args.run}.jsonl"
    done_keys = set()
    if log_path.exists():
        for line in log_path.read_text().splitlines():
            record = json.loads(line)
            if not record.get("infra_failure"):
                done_keys.add(key_of(record))
    run_root = kit.EVAL_ROOT / "runs" / args.run
    run_root.mkdir(parents=True, exist_ok=True)
    jobs = []
    task_ids = {task: kit.load_task(task)["id"] for task in args.tasks}
    for rep in range(args.reps):
        for task in args.tasks:
            for variant in args.variants:
                name = "none" if variant == "none" else pathlib.Path(variant).stem
                for model in args.models:
                    if (task_ids[task], name, model, rep) not in done_keys:
                        jobs.append({"task": task, "variant": variant, "model": model, "rep": rep})
    jobs = interleave(jobs)
    print(f"{len(jobs)} cells to run, {len(done_keys)} already recorded", flush=True)
    finished = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool, log_path.open("a") as log:
        for record in pool.map(lambda job: run_one(job, run_root, args.timeout, args.attempts), jobs):
            finished += 1
            log.write(json.dumps(record) + "\n")
            log.flush()
            if record.get("infra_failure"):
                state = record["infra_failure"].upper()
            else:
                state = "pass" if record["score"]["primary_pass"] else "FAIL"
            seconds = record.get("run", {}).get("seconds", 0)
            print(f"[{finished}/{len(jobs)}] {state:9} {record['task']:24} {record['variant']:12} {record['model']:38} {seconds:5.0f}s", flush=True)
    if EXHAUSTED:
        print("models out of free quota:", sorted(EXHAUSTED), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
