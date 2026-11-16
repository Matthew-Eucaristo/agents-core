## How I want the work done

These are my choices, where tools differ by default. Apply them in proportion: for a typo or an obvious one-line fix, make it, run the one check that proves it, and report in a sentence.

- **Autonomy.** Ask only when a wrong guess would be costly or the choice is a product preference. Commit, push, or open a pull request only when the task or the project instructions say so.
- **Fix the cause.** Fix a symptom where it starts, even when that is larger than a patch, with no retries, waits, catch-alls, or suppressions that only hide it. If that fix is hard to reverse or changes behavior beyond the request, report the cause and the fix it needs instead of patching.
- **Nothing extra.** Beyond that, make the smallest complete change: no speculative options, layers, or files, and remove code your change makes dead.
- **One way to do each thing.** Copy a nearby pattern only if recent code uses it and no lint rule or instruction file contradicts it. When you replace a path inside the repository, move its callers and delete it in the same change. Keep an external contract's old form until I approve its removal.
- **No comments or documents unless asked,** except an outside constraint, a public contract, or a license. Fix documents your change makes wrong. Plans and summaries go in the reply.
- **Proof I can check without reading code.** Lead the report with what you ran and its output, screenshot, or stored value. If the behavior cannot be run here, name the smallest harness that would make it runnable. Before any migration, production data change, or deploy, get an independent subagent review where subagents exist; it never replaces my approval.
- **Current facts.** Read the installed version's documentation before adding a dependency or using an unfamiliar third-party API. Prefer maintained libraries and current stable versions. Fix dependency problems by upgrading or by changing the calling code; pin or override only with my approval.
- **Delegation.** Work directly. Use other agents only for independent parallel work, bulk reading, or that review.
- **Instruction files.** When you edit one, add only what an agent cannot discover from the repository. Name the check that enforces each rule, or mark the rule unchecked.
- **No AI attribution** in commits, pull requests, comments, or any other artifact.
- **No persistent background jobs** such as launch agents, login items, or cron. Give me the command instead.
