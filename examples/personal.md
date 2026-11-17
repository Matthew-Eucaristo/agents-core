## How I want the work done

These are my choices, where tools differ by default.

- **Autonomy.** Ask before deleting anything that cannot be regenerated or restored from version control, rewriting pushed history, deploying, publishing, sending, or spending. A production migration, production data change, or deploy also needs a subagent review first, where subagents exist. Commit, push, or open a pull request only when the task or my project instructions say so. Do everything else without asking, including the check that stops a mistake from repeating.
- **Fix the cause.** Fix a fault where it starts, not where it shows, even when that is the larger change. If it starts outside this repository, report the cause. No retries, waits, catch-alls, or suppressions that hide it.
- **One way to do each thing.** When you replace code inside the repository, move its callers and delete the old code in the same change. Add no abstraction or option that nothing uses.
- **No comments.** Add none except a license header, a public API contract, or a constraint from outside the repository. No new documents unless asked; update any document your change makes wrong.
- **Proof I can check without reading code.** Start the report with the exact command you ran and the output it printed, or the screenshot or stored value.
- **Short reports.** No headings, no list of changed files, and no next steps unless I ask.
- **Current facts.** Read the current documentation before using a dependency or API that is new to the repository. Pin or override a version only with my approval.
- **Delegation.** Work directly. Use other agents only for independent parallel work, bulk reading, or that review.
- **Instruction files.** Add only what an agent cannot find in the repository, each rule as one default with a closed list of exceptions. Name the check that enforces it; mark it unchecked only when none exists.
- **No AI attribution** in commits, pull requests, comments, or any other artifact.
- **No persistent background jobs** such as launch agents, login items, or cron. Give me the command instead.
