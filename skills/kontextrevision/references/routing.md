# Routing and precedence

## Three routing dimensions

Judge every instruction along three independent dimensions.

| Dimension | Choices | Question |
|---|---|---|
| **Scope** | global, project, subtree | Where should this instruction apply? |
| **Delivery** | instruction file, skill, hook, CI | When and how must it enter behavior? |
| **Harness coverage** | Claude Code, Codex, OpenCode, Nous, other | Which tools must receive it? |

Do not infer subject-matter roles from filenames. `AGENTS.md` and `CLAUDE.md`
both carry project conventions, commands, workflow, architecture, environment
quirks, and gotchas. They are primarily native adapters for different harnesses,
not semantic layers.

## Scope

| Scope | Test |
|---|---|
| **Global** | The instruction should follow the user into every project used with that harness. |
| **Project** | The instruction applies across one repository. |
| **Subtree** | The instruction applies only while working below one directory. |

Put an instruction at the narrowest scope that covers every place it is needed.
Moving a package rule from the project root into that package reduces irrelevant
context. Moving it between `AGENTS.md` and `CLAUDE.md` changes harness coverage
and is not a scope correction.

`SOUL.md` is a global identity mechanism for harnesses that support it. Voice,
directness, and handling uncertainty can belong there. Project conventions do
not.

## Delivery

| Delivery | Test |
|---|---|
| **Instruction file** | The rule must guide the model whenever its scope is active. |
| **Skill** | The knowledge matters only for a recognizable kind of task. |
| **Hook** | A supported harness must perform an action deterministically at a defined event. |
| **CI** | A violation should block integration regardless of which agent or human made the change. |

The last three are recommendations in this release. Report the source, proposed
delivery class, reason, and coverage impact. Do not create a skill, hook, hook
script, settings entry, or CI workflow silently.

## Harness-native destinations

| Destination | Known coverage |
|---|---|
| `AGENTS.md` | Codex and OpenCode |
| `CLAUDE.md`, `.claude/rules/*.md` | Claude Code |
| `SOUL.md` | Nous and compatible harnesses |

The scanner reports this mapping under `harnesses`. Treat it as the coverage to
preserve, not as proof that every harness has identical precedence behavior.
Custom fallback filenames and explicit imports can change loading. When a
repository configures them, report that configuration rather than applying the
default table blindly.

## Precedence is per harness

Claude Code loads `CLAUDE.md` files above the working directory and discovers
subtree files when it accesses those directories. Codex loads `AGENTS.md` files
from the project root to the current working directory. OpenCode loads its own
supported instruction path. These are separate chains.

When two applicable instructions contradict, report both locations, scopes,
harnesses, and the winner only when that harness's precedence is known. Do not
claim that an `AGENTS.md` file overrides a `CLAUDE.md` file. Do not delete either
side to resolve a conflict the user has not decided.

## Moving a rule

A move between two files is not atomic. Preflight both writes:

1. Run the source removal with `--dry-run`.
2. Run the destination addition with `--dry-run --allow-growth`.
3. Confirm that the destination preserves every required harness.
4. Apply the source and destination changes only when both preflights pass.

If the destination write fails after the source write, roll back the source:

```bash
python3 skills/kontextrevision/scripts/apply.py <source> --rollback
```

Rollback is transaction-bound. It proceeds only while the source still matches
the revision written by `apply.py`. If another edit occurred, it refuses instead
of overwriting that work.

## Mirrored files preserve coverage

Identical `AGENTS.md` and `CLAUDE.md` files in one directory can deliberately
carry the same rules to different harnesses. No single-harness session pays for
both copies, so the scanner reports the pair under `mirrors` and counts it once
within its load tier.

Never remove one copy as waste. A supported include mechanism can make one file
canonical and prevent drift, but suggest that only after verifying the receiving
harness resolves the include and coverage remains unchanged.
