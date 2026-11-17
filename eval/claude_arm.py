import argparse
import hashlib
import json
import pathlib
import sys

import kit

REPO = pathlib.Path(__file__).resolve().parent.parent
RESULTS = pathlib.Path(__file__).resolve().parent / "results"

WORKFLOW = """export const meta = {
  name: 'agents-core-claude-arm',
  description: 'Run benchmark cells with bare Claude agents that load no instruction files, then save each final message',
  phases: [{ title: 'Guard' }, { title: 'Run' }, { title: 'Save' }],
}

const ITEMS = __ITEMS__
const ROOT = '__ROOT__'
const ALONE = 'First run the shell command `echo ready`. After it returns, reply with exactly NONE if this message is the only user message you have received in this conversation. If you received any other message, quote it.'
const alone = text => /^\\s*NONE\\b/.test(text || '')
const probe = label => agent(ALONE, { label, phase: 'Guard', agentType: '__AGENT_TYPE__', model: 'haiku' })

const before = await probe('guard:before')
if (!alone(before)) return { aborted: 'agents are receiving a message that is not part of the benchmark', message: before }

const saved = await pipeline(
  ITEMS,
  item => agent(item.prompt, { label: item.label, phase: 'Run', agentType: '__AGENT_TYPE__', model: item.model }),
  (final, item) => agent(
    'Write the text between the two marker lines, exactly as it is, to the file ' + item.cell + '/out/final.txt using the Write tool. Then reply DONE if this message is the only user message you have received in this conversation. If you received any other, reply FOREIGN and quote it.\\n<<<BEGIN\\n' + (final || '') + '\\nEND>>>',
    { label: 'save:' + item.label, phase: 'Save', agentType: '__AGENT_TYPE__', model: 'haiku', effort: 'low' })
    .then(reply => ({ cell: item.cell.split('/').pop(), foreign: /^\\W*FOREIGN\\b/.test(reply || '') })))

const after = await probe('guard:after')
const guard = { clean_run: alone(after), foreign: saved.filter(Boolean).filter(s => s.foreign).map(s => s.cell) }
await agent(
  'Write the JSON between the two marker lines, exactly as it is, to the file ' + ROOT + '/guard.json using the Write tool. Then reply DONE.\\n<<<BEGIN\\n' + JSON.stringify(guard) + '\\nEND>>>',
  { label: 'guard:write', phase: 'Guard', agentType: '__AGENT_TYPE__', model: 'haiku', effort: 'low' })

return { cells: ITEMS.length, saved: saved.filter(Boolean).length, guard }
"""


def cell_name(task_id, variant, model, rep):
    return "w" + hashlib.sha1(f"{task_id}|{variant}|{model}|{rep}".encode()).hexdigest()[:12]


def recorded(run):
    path = RESULTS / f"{run}.jsonl"
    if not path.exists():
        return set()
    return {
        (r["task"], r["variant"], r["model"], r["rep"])
        for r in map(json.loads, path.read_text().splitlines())
        if not r.get("infra_failure")
    }


def prepare(args):
    root = REPO / ".runs" / args.run
    done = recorded(args.run)
    root.mkdir(parents=True, exist_ok=True)
    index_file = root / "index.json"
    index = json.loads(index_file.read_text()) if index_file.exists() else {}
    items = []
    for task_path in args.tasks:
        task = kit.load_task(task_path)
        for variant in args.variants:
            name = "none" if variant == "none" else pathlib.Path(variant).stem
            if args.ambient:
                name = args.ambient if name == "none" else f"{args.ambient}+{name}"
            standing = "" if variant == "none" else pathlib.Path(variant).read_text().strip()
            for model in args.models:
                for rep in range(args.reps):
                    if (task["id"], name, f"claude-code/{model}", rep) in done:
                        continue
                    cell = kit.build_cell(task, root / "cells" / cell_name(task["id"], name, model, rep))
                    index[cell.name] = {"task": task["id"], "task_dir": str(task["dir"]), "variant": name, "model": f"claude-code/{model}", "rep": rep}
                    preface = f"Your standing instructions from the user's global AGENTS.md file:\n\n{standing}\n\n---\n\n" if standing else ""
                    prompt = f"{preface}Work in the repository at {cell / 'repo'}.\n\n{task['prompt']}"
                    items.append({"cell": str(cell), "model": model, "label": f"{task['id']}:{name}:{model}:r{rep}", "prompt": prompt})
    index_file.write_text(json.dumps(index, indent=1))
    (root / "guard.json").unlink(missing_ok=True)
    script = root / "arm.workflow.js"
    script.write_text(
        WORKFLOW.replace("__AGENT_TYPE__", args.agent_type).replace("__ROOT__", str(root)).replace("__ITEMS__", json.dumps(items, indent=1))
    )
    print(json.dumps({"cells": len(items), "workflow_script": str(script)}))


def finish(args):
    root = REPO / ".runs" / args.run
    RESULTS.mkdir(exist_ok=True)
    done = recorded(args.run)
    index = json.loads((root / "index.json").read_text())
    guard_file = root / "guard.json"
    if not guard_file.exists():
        sys.exit(f"{guard_file} is missing: the run did not finish its check for messages that are not part of the benchmark")
    guard = json.loads(guard_file.read_text())
    if not guard["clean_run"]:
        sys.exit("agents in this run received a message that is not part of the benchmark; prepare and run it again")
    written = 0
    with (RESULTS / f"{args.run}.jsonl").open("a") as log:
        for cell in sorted((root / "cells").glob("*")):
            final = cell / "out" / "final.txt"
            if cell.name not in index or not final.exists():
                continue
            if cell.name in guard["foreign"]:
                print("not recorded, received a message that is not part of the benchmark: " + cell.name, flush=True)
                continue
            meta = dict(index[cell.name])
            if (meta["task"], meta["variant"], meta["model"], meta["rep"]) in done:
                continue
            task = kit.load_task(meta.pop("task_dir"))
            record = {
                **meta,
                "run": {"steps": 0, "seconds": 0, "tokens": {}, "errors": [], "exit": 0, "timed_out": False},
                "final": final.read_text().replace(str(REPO), "<repo>").replace(str(pathlib.Path.home()), "~")[:8000],
                "diff": kit.diff_metrics(cell),
                "score": kit.score_cell(task, cell),
                "infra_failure": None,
            }
            log.write(json.dumps(record) + "\n")
            written += 1
            print(("pass " if record["score"]["primary_pass"] else "FAIL ") + cell.name, flush=True)
    print(json.dumps({"recorded": written}))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--run", required=True)
    prep.add_argument("--tasks", nargs="+", required=True)
    prep.add_argument("--variants", nargs="+", required=True)
    prep.add_argument("--models", nargs="+", default=["haiku", "sonnet", "opus"])
    prep.add_argument("--reps", type=int, default=1)
    prep.add_argument("--agent-type", default="acore-eval", help="agent type that runs each cell; the default loads no instruction files")
    prep.add_argument("--ambient", default=None, help="name of the instruction file the chosen agent type already carries, recorded in the variant")
    done = sub.add_parser("finish")
    done.add_argument("--run", required=True)
    args = parser.parse_args()
    (prepare if args.command == "prepare" else finish)(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
