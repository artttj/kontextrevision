---
name: kontextrevision
description: Use when the user wants to clean up, tighten, shrink, structure, or revise SOUL.md, AGENTS.md, CLAUDE.md, or a whole instruction tree. Also use for instruction bloat, duplicate or fragmented rules, misplaced scope, cross-harness coverage, contradictions, buried constraints, or command references that may no longer exist.
---

# kontextrevision

Revise agent instruction stacks so their content, scope, delivery, and harness
coverage make important rules easy to apply. Token reduction is a consequence.
Better context architecture is the goal.

## Workflow

### 1. Scan

Do not read the files first. Run the scanner and work from the digest.

```bash
python3 skills/kontextrevision/scripts/scan.py <root>
```

One scan inventories the complete recursive instruction tree plus installed
skills, agents, and commands. The digest reports each file's scope, harnesses,
load condition, byte size, token estimate, section headings with exact and
normalized hashes, referenced commands, and referenced paths. It never contains
file bodies. A tree can hold hundreds of these, and reading them all before
triage would exhaust the context window.

Read the load tiers separately:

- `effective_now_tokens`: instruction files active for the selected working directory
- `conditionally_loaded_tokens`: descendant instructions activated only in their scope
- `harness_tokens`: the same instruction tiers separated by receiving harness
- `skill_description_tokens`: definition triggers exposed to the harness
- `on_demand_body_tokens`: definition bodies loaded only on invocation
- `duplicates`: definition names appearing in more than one plugin, each paying for its description

Use `--cwd <path>` to analyze another working directory inside the scanned tree.
Never describe the whole recursive inventory as context paid by every session.

Pass `--harness` to report only the definitions, without instruction files.
Superseded plugin-cache versions and cloned marketplace catalogs are excluded
from both modes, since neither is loaded.

Descriptions are triggers, not prose. Too vague and the skill never fires when it
should. Too long and it bills every session. Both are worth flagging.

### 2. Read the digest for the cheap findings

**Duplicate candidates.** `exact_hash` includes heading, level, and the
byte-preserved body. `normalized_hash` tolerates formatting differences. A match
in either narrows inspection but never authorizes deletion. Open both blocks,
including their headings and surrounding hierarchy, before deciding they express
the same instruction.

**Dead commands.** For each entry in `commands`, verify it exists. Read
[references/classification.md](references/classification.md) first — the
verification rules there exist because naive checking produced false accusations
against Google, OpenShift, and Exoscale during this project's own research.

**Oversize.** Compare `est_tokens` against the corpus medians in
[references/research.md](references/research.md). A file at 5,000+ tokens is
around the p90 of the dated 250-repository sample, not a permanent estimate of
all repositories.

### 3. Open only the files you will change

Now read the bodies. Apply
[references/classification.md](references/classification.md) to classify every
block, then the editorial filter: would the agent behave incorrectly without this
instruction? If no, remove it.

Apply [references/routing.md](references/routing.md) along three dimensions:
scope, delivery, and harness coverage. Report contradictions within each
harness's applicable scope without resolving them.

### 4. Structure

Review the architecture before rewriting prose:

- heading hierarchy that skips levels or flattens distinct concerns;
- related rules fragmented across distant sections;
- exact and normalized duplicate candidates;
- contradictions within or across applicable scopes;
- rules loaded more broadly than their use requires;
- harness coverage a proposed move would lose;
- occasional knowledge better delivered by a skill;
- deterministic requirements better enforced by a hook or CI;
- important constraints buried inside explanatory prose.

You may reorganize content within an instruction file and recommend another
scope or delivery class. Do not create or modify skills, hooks, settings, hook
scripts, or CI workflows. State the source, proposed destination class, reason,
and coverage impact.

Read [references/research.md](references/research.md) before making any claim
about performance. The literature contradicts itself and this skill does not
promise a speedup.

### 5. Apply

Pipe the new content to the writer. **Never use Write or Edit on these files.**
The guards live in `apply.py`, and bypassing it bypasses them.

```bash
printf '%s' "$NEW_CONTENT" | python3 skills/kontextrevision/scripts/apply.py <path>
```

| Flag | When |
|---|---|
| `--dry-run` | Report without writing |
| `--allow-growth` | Required when a routing move adds content *to* this file |
| `--force` | Overrides the git-dirty guard. Only when the user asks. |
| `--allow-new-commands` | Permits a rewrite to name a command the original did not. Only when the user asks. |
| `--rollback` | Restores the most recent backup and deletes it. Use after a failed multi-file move. |

Keep markers are **paired**. A block is protected only when it sits between
`<!-- kontextrevision:keep -->` and `<!-- /kontextrevision:keep -->`. An opening
tag alone protects nothing, which is why the writer refuses to run against a file
that has one.

The writer refuses in seven cases. Every refusal is correct:

| Refusal | What it means |
|---|---|
| uncommitted changes | The file is tracked and has uncommitted edits. Ask the user to commit. Do not pass `--force` on their behalf. Untracked new files are allowed through. |
| keep block dropped | Content between `<!-- kontextrevision:keep -->` and `<!-- /kontextrevision:keep -->` is no longer inside those markers in your rewrite. Restore it, markers included, and retry. |
| unpaired keep marker | The original has an opening marker with no closing `<!-- /kontextrevision:keep -->`. Tell the user, do not guess where the block ends. |
| empty content | Your rewrite was blank. Never retry blindly, something upstream truncated. |
| content shrank | Output fell below 20% of the original. Check you did not drop half the file by accident. |
| content grew | You added something. Only remove, merge, move, or tighten. If this is a routing move, pass `--allow-growth`. |
| rewrite invents commands | Your rewrite names a command the original never mentioned. Propose it to the user rather than writing it. |

### 6. Report

Print a changelog: what was removed and under which category, what was moved and
where, what structural findings remain, what delivery changes were recommended,
what coverage each move preserves, and what contradictions were found. Name a
winner only when the applicable harness precedence is known. Then print the token
delta per file from the `apply.py` output.

## Modes

| Invocation | Behavior |
|---|---|
| `/kontextrevision` | Current repo. Writes. |
| `/kontextrevision <path>` | One file. Writes. |
| `/kontextrevision --all` | Global plus `~/.claude` plus every project. **Dry-run, always.** |
| `/kontextrevision --dry-run` | Report and diffs only. |

`--all` never writes on the first pass. One bad judgment there propagates across
every project at once. Show the user the full plan and require a second explicit
confirmation before applying any of it.

## Hard rules

- Never invent instructions. Remove, merge, move, tighten. Nothing else. Sharpening wording is allowed. Inventing a procedure the author never wrote is not, and the writer enforces this.
- A multi-file move is not atomic. Preflight both writes with `--dry-run` before running either, and use `--rollback` if the second fails. Rollback refuses after an intervening edit.
- Never write with Write or Edit. Always pipe through `apply.py`.
- Never resolve a contradiction by deleting one side. Report both with their scopes and harnesses.
- Never move a rule between harness-native files unless required coverage is deliberately preserved.
- Recommend skill, hook, or CI delivery. Do not generate those artifacts in this release.
- Never pass `--force` unless the user asked for it.
- Never claim a command is dead unless you fully resolved the manifest. Silence beats a false accusation.
