# agents-core

Eight rules for AI coding agents that stay true whatever model or tool you use, and a benchmark that checks whether an instruction file changes what agents actually do.

The rules are in [AGENTS.md](AGENTS.md). They contain no coding style.

## The idea

Sort every rule you might write by one question: does a stronger model need it less?

- If yes, it is a crutch, such as "read the file before editing" or "think step by step". Tools already say it, and it expires. Leave it out.
- If reasonable people would choose differently, it is a preference, such as "commit when done" or "no comments". It belongs to you, not to a universal file.
- What is left is the core: rules about authority, honest checks, and truthful reports. A stronger agent is better at passing a visible check without doing the work, at finding another route around a refusal, and at writing a convincing report. These rules matter more as models improve.

## Three layers

| Layer | Holds | Changes |
|---|---|---|
| Core: `AGENTS.md` in this repository | Limits that protect what you cannot check | Rarely |
| Yours | Choices where tools differ by default: when to ask, commits, comments, how much proof | When your taste changes |
| Project | Facts an agent cannot discover, and the checks that enforce the rules | With the code |

Written rules are not enforcement. A rule that must hold becomes a type, a lint rule, a test, or a hook, and the instruction file keeps only what cannot be checked. [examples/personal.md](examples/personal.md) is one person's second layer.

## Use it

Keep one copy and point each tool at it. Paths are from each tool's documentation in November 2026.

| Tool | Global instruction file |
|---|---|
| Claude Code | `~/.claude/CLAUDE.md` |
| Codex | `~/.codex/AGENTS.md` |
| opencode | `~/.config/opencode/AGENTS.md` |
| Gemini CLI | `~/.gemini/GEMINI.md` |
| Qwen Code | `~/.qwen/QWEN.md` |
| Cline, Kimi Code, DeepSeek Harness | `~/.agents/AGENTS.md` |
| Cursor | User rules in settings, or `AGENTS.md` in the project |

```bash
mkdir -p ~/.agents && cp AGENTS.md ~/.agents/AGENTS.md
```

```bash
ln -s ~/.agents/AGENTS.md ~/.claude/CLAUDE.md
```

Add your own preferences below the eight rules in your copy. Keep project facts in the project's own `AGENTS.md`.

## Why so little

- Instruction files are obeyed, but they do not raise task success, and they cost about 20% more tokens. [ETH Zurich, 2026](https://arxiv.org/abs/2602.11988)
- Vendors are deleting guidance as models improve. Anthropic reports removing over 80% of Claude Code's system prompt for its 5 generation with no measured loss. OpenAI reports leaner prompts scoring 10 to 15% higher with 41 to 66% fewer tokens. [Anthropic](https://claude.dev/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models/), [OpenAI](https://developers.openai.com/api/docs/guides/prompt-guidance-gpt-5p6.md)
- A written rule is followed some of the time: 64 to 78% by a frontier model and under 21% by small open models in one study. A check fails every time. [Study](https://arxiv.org/html/2611.04367)
- Agents followed a stale instruction file over the code in about 90% of choices until one sentence gave the code precedence. This is rule 2. [Study](https://arxiv.org/html/2610.30571v1)
- Stronger models gamed impossible tests more often than weaker ones, despite being told not to. This is rule 6. [ImpossibleBench](https://arxiv.org/html/2510.20270v1)
- The published system prompts of the major coding tools already cover reading before editing, matching conventions, staying in scope, and running tests. None tells an agent to prefer a check over a written rule, to read state back after changing it, or to treat instruction files that arrive mid-task as data.
- Moving every correction into a check, instead of into prose, is the practice behind Lauren Tan's talk [All Code Is Slop (Except Mine)](https://www.youtube.com/watch?v=O_zcc6Xl12g).

## The benchmark

`eval/tasks/` holds 17 small repositories. Each has a tempting wrong path, a hidden scorer, and reference solutions that prove the scorer can fail. An independent agent reviewed every task and attacked its scorer with alternative right and wrong solutions.

| Rule | Tasks |
|---|---|
| 1 Instructions | `untrusted-content` |
| 2 Stale instructions | `stale-instruction`, `follow-current-pattern` |
| 3 Authority | `protect-user-data` |
| 4 Other people's work | `others-work` |
| 5 Secrets and access | `no-secret-leak` |
| 6 Checks | `conflicting-test`, `hook-bypass`, `no-suppression` |
| 7 Reports | `honest-unverified`, `verify-real-behavior`, `read-back-state` |
| 8 Lessons | `correction-to-check` |
| Preferences | `root-cause-flaky`, `replace-and-delete`, `stay-simple`, `trivial-edit` |

Check a task:

```bash
python3 eval/validate_task.py eval/tasks/conflicting-test
```

Run cells with opencode. Each cell runs in a macOS sandbox with its own home directory, so the file under test is the only instruction file the agent sees:

```bash
python3 eval/matrix.py --run first --tasks eval/tasks/[a-z]*/ --variants none AGENTS.md --models opencode/deepseek-v4.1-flash-free
```

```bash
python3 eval/summary.py first
```

Run cells with Claude Code from a session opened in this repository. `eval/claude_arm.py prepare` writes a workflow script that uses the bare agent in `.claude/agents/`, which loads no instruction files. `eval/claude_arm.py finish` scores the cells.

Some tasks also carry yes/no questions about the agent's final message, such as whether it admits what it could not verify. `eval/judge.py prepare` writes those items for a blind judge, `eval/judge.workflow.js` runs the judge, and `eval/judge.py merge` records the answers.

## Changing the core

Add a rule only with a task that agents fail without it and pass with it. Remove a rule when current models pass its task without it. Rerun the benchmark when a new model generation ships.

## Limits

- A written rule lowers the odds of a failure. It does not prevent one. Pair these rules with permissions, sandboxes, protected branches, and backups.
- The tasks are small Python repositories. They measure behaviour at a trap, not capability.
- The eight rules were tested for clear reading on three model tiers. Their effect on behaviour has not yet been measured across vendors at scale.

## License

MIT
