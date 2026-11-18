# agents-core

Seven engineering principles for AI agents. They apply to any model, any tool, and any kind of work. Your own preferences, project rules, and workflows add to them.

| | Principle | Older root |
|---|---|---|
| 1 | Examine the thing itself before you change or describe it. | Go and see (Toyota); Chesterton's fence (1929) |
| 2 | Leave your work safe to use as a pattern. | Precedent in common law; standard work (Toyota) |
| 3 | Observe the real result before you call work done. | Falsifiability (Popper, 1935); Dijkstra on testing (1969) |
| 4 | Never weaken or bypass a check. | Goodhart's law (1975); Campbell's law (1976) |
| 5 | Report the result you observed, and what failed or is unverified. | Nullius in verba (Royal Society, 1660s); Feynman (1974) |
| 6 | Explain or report every result you did not expect. | Stop at the abnormality (Toyota); normalization of deviance (1996) |
| 7 | Make a repeated mistake impossible, not just forbidden. | Mistake-proofing (Toyota, 1960s); the hierarchy of hazard controls |

The file agents read is [AGENTS.md](AGENTS.md): those seven sentences and a short preface, 116 words.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/Matthew-Eucaristo/agents-core/main/install.sh | sh
```

This writes the principles to `~/.agents/AGENTS.md`, keeps your own text below them, and links the tools it finds. Run it again to update, or after you install another tool. To remove everything it added:

```bash
curl -fsSL https://raw.githubusercontent.com/Matthew-Eucaristo/agents-core/main/install.sh | sh -s -- uninstall
```

One file serves every tool. When you move from one agent tool to another, run the installer again and the new tool reads the same principles and the same preferences.

| Tool | What the installer does |
|---|---|
| Cline, Goose, Warp, Kimi Code, DeepSeek Harness, Factory Droid, opencode 2.3 | Nothing: they read `~/.agents/AGENTS.md` themselves |
| Claude Code, Codex, Qwen Code, Grok Build, Kilo Code, Zed | Links the tool's own global file to it |
| Gemini CLI | Links it and prints the one setting to add |
| Cursor, Amp, Kiro, Aider | Prints the one manual step |

It never overwrites a file you already have, and removes only the links it made. Paths were checked against each tool's documentation or source in November 2026.

## What is left out

The core holds engineering principles only. Three kinds of rule are left out on purpose:

- **Safety, caution, and whose instructions count.** Model providers train these in and publish them ([Anthropic](https://www.anthropic.com/constitution), [OpenAI](https://model-spec.openai.com/)). With no instructions at all, the agents measured here never followed an injected instruction, logged a secret, or bypassed a commit hook (3 runs each), and never deleted user data or touched another person's uncommitted work (12 runs each).
- **Permission.** What needs your approval is decided by the tool's permission mode and by your own preferences.
- **Preferences.** Root-cause policy, comments, report style, when to commit. Reasonable engineers choose differently, so these go in your own layer.

A principle stays only if a more capable agent does not need it less, a reasonable engineer would not reject it, and it is older than today's tools. Across the public histories of agent system prompts, deleted mechanics stayed deleted, while deleted rules of conduct came back within months.

## Your own layer

Put your preferences below the core in `~/.agents/AGENTS.md`. [examples/personal.md](examples/personal.md) is one person's layer to start from:

```bash
{ echo; curl -fsSL https://raw.githubusercontent.com/Matthew-Eucaristo/agents-core/main/examples/personal.md; } >> ~/.agents/AGENTS.md
```

"Nuance tends to lead to slop" ([Lauren Tan](https://www.youtube.com/watch?v=O_zcc6Xl12g)). Write each preference as one default with a closed list of exceptions. A preference that needs judgment to apply belongs in a lint rule, a hook, or a test, not in a sentence.

## Measured

Bare Claude agents (Haiku, Sonnet, Opus) ran 18 trap tasks. On eleven, every text scored the same: the agents passed all 383 runs, even with no instructions. The other seven were run three times per model with each text, 63 runs per row:

| Text given to the agent | Words | Passed scripted checks | Passed including report quality |
|---|---|---|---|
| Nothing | 0 | 48 | 37 |
| The seven principles | 116 | 54 | 45 |
| The seven, plus the example preferences | 466 | 63 | 52 |
| An earlier core of ten lines, with scope, consent, and safety lines | 163 | 55 | 41 |
| Those ten lines with one to three sentences of explanation each | 357 | 49 | 34 |

- Principle 7 carries most of the gain: after a repeated mistake, agents added a real check in 9 of 9 runs with the seven principles and in 3 of 9 with nothing.
- A scope line worked against it. Texts with "Do all of what was asked and nothing more" got the check in 37 of 48 runs, texts without it in 78 of 80. Most agents that skipped the check said it had not been asked for.
- An eighth line, "See a new check fail before you trust it", was tested and left out. On the task built for it, all 36 runs wrote a test that fails without the fix, with or without the line. With the line, the report of a one-word fix was too long in 3 of 9 runs.
- Explanation made results worse: agents added the check less often (5 of 9 runs against 8 of 9) and more often refused to clean up files that could be regenerated.
- Preferences do what they say. With the example layer, no run added a comment (9 of 9, against 0 of 9 without it) and 7 of 9 reports showed the output of the real run (against 0 of 9). The price: 3 of 9 reports of a one-word fix ran past six sentences.

The measured texts are [AGENTS.md](AGENTS.md), [examples/personal.md](examples/personal.md), and [eval/variants](eval/variants). Report quality was judged blind by a model, two votes and a third when they differ. On 41 hand-labeled control answers it agreed with every label.

## Changing a principle

A principle changes only with an older root from two different fields behind it and a task in `eval/` that agents fail without it. To run a task (macOS, in Claude Code):

```bash
python3 eval/claude_arm.py prepare --run try1 --tasks eval/tasks/correction-to-check --variants none AGENTS.md --reps 3
```

Ask Claude Code to run the workflow script that command prints, then pass the Transcript dir from its result. `finish` records nothing if any agent received a message other than its task:

```bash
python3 eval/claude_arm.py finish --run try1 --transcripts <Transcript dir> && python3 eval/summary.py try1 --no-rubric
```

## Limits

- Measured on Claude models only, inside one tool, on small Python tasks. Six of the seven principles describe what those models already did on these tasks. They are kept for weaker models and other tools, where they are not measured yet.
- The texts were chosen with the same tasks they are scored on, and each task has nine runs per text. Rows a few runs apart are the same.
- A written principle lowers the odds of a failure. It does not prevent one. Anything that must hold belongs in a check, a permission, or a backup.

## Credits

Lauren Tan's talk [All Code Is Slop (Except Mine)](https://www.youtube.com/watch?v=O_zcc6Xl12g) and [pstack](https://github.com/cursor/plugins/tree/main/pstack) shaped principles 2 and 7 and the example layer. The Claude Code team describes the same loop in [How the Claude Code team thinks about verification](https://claude.dev/blog/how-the-claude-code-team-thinks-about-verification/). Background reading: [instruction files and task success](https://arxiv.org/abs/2602.11988), [how often written rules are followed](https://arxiv.org/html/2611.04367), [stronger models gaming tests](https://arxiv.org/html/2510.20270v1).

## License

MIT
