## How I want the work done

These are my choices, where tools differ by default.

- **Autonomy.** Commit, push, or open a pull request only when the task or my project instructions say so.
- **Fix the cause.** Fix a fault where it starts, not where it shows, even when that is the larger change. No retries, waits, catch-alls, or suppressions that only hide it. If that fix is hard to reverse or reaches beyond the request, report the cause and the fix it needs instead of patching.
- **One way to do each thing.** Copy a nearby pattern only if no newer code, lint rule, or instruction file contradicts it. When you replace a path inside the repository, move its callers and delete it in the same change, along with code your change makes dead. Keep an external contract's old form until I approve its removal.
- **No comments or documents unless asked,** except an outside constraint, a public contract, or a license. Fix documents your change makes wrong. Plans and summaries go in the reply.
- **Proof I can check without reading code.** Start the report with the exact command you ran and the output it printed, or the screenshot or stored value. If the behavior cannot be run here, name the smallest harness that would make it runnable. Before a production migration, a production data change, or a deploy, get an independent subagent review where subagents exist; it never replaces my approval.
- **Current facts.** Before adding a dependency or a call to an API the repository does not already use, read that version's documentation. Prefer maintained libraries and current stable versions. Fix dependency problems by upgrading or by changing the calling code; pin or override only with my approval.
- **Delegation.** Work directly. Use other agents only for independent parallel work, bulk reading, or that review.
- **Instruction files.** Unless I ask otherwise, add only what an agent cannot discover from the repository. Name the check that enforces each rule, or mark the rule unchecked.
- **No AI attribution** in commits, pull requests, comments, or any other artifact.
- **No persistent background jobs** such as launch agents, login items, or cron. Give me the command instead.
