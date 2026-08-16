---
name: kontextrevision
description: Use when the user wants to clean up, tighten, shrink, or revise agent instruction files - SOUL.md, AGENTS.md, CLAUDE.md, or a whole tree of them. Also use when they mention instruction bloat, rules duplicated across files, a rule that seems to be in the wrong file, contradictions between global and project instructions, or commands in an instruction file that no longer exist. Rewrites files in place.
---

# kontextrevision

Revise agent instruction files so they carry only the lines that change agent
behavior. These files are injected into the system prompt on every session, so a
line that does nothing bills the user forever.

## Workflow

### 1. Scan

Do not read the files first. Run the scanner and work from the digest.

```bash
python3 skills/kontextrevision/scripts/scan.py <root>
```

One scan finds everything that costs tokens on every session: instruction files
and every installed skill, agent, and command. The digest reports, per file,
role, byte size, token estimate, section headings with content hashes,
referenced commands, and referenced paths. It never contains file bodies. That
is deliberate. A tree can hold hundreds of these, and reading them all would
exhaust the context window before any work happens.

Top-level totals matter more than any single file:

- `always_on_tokens`: instruction files plus definition descriptions, paid every session
- `on_demand_tokens`: definition bodies, paid only when something is invoked
- `duplicates`: definition names appearing in more than one plugin, each paying for its description

Never compare the two tiers as though they cost the same.

Pass `--harness` to report only the definitions, without instruction files.
Superseded plugin-cache versions and cloned marketplace catalogs are excluded
from both modes, since neither is loaded.

Descriptions are triggers, not prose. Too vague and the skill never fires when it
should. Too long and it bills every session. Both are worth flagging.

### 2. Read the digest for the cheap findings

**Duplicates.** Identical section hashes across two files mean the same content
lives in both. Merge into the more specific file, remove from the other.

**Dead commands.** For each entry in `commands`, verify it exists. Read
[references/classification.md](references/classification.md) first — the
verification rules there exist because naive checking produced false accusations
against Google, OpenShift, and Exoscale during this project's own research.

**Oversize.** Compare `est_tokens` against the corpus medians in
[references/research.md](references/research.md). A file at 5,000+ tokens is in
the top decile of everything on GitHub.

### 3. Open only the files you will change

Now read the bodies. Apply
[references/classification.md](references/classification.md) to classify every
block, then the editorial filter: would the agent behave incorrectly without this
instruction? If no, remove it.

Apply [references/routing.md](references/routing.md) to decide whether a block
belongs in a different file, and to report contradictions between layers without
resolving them.

Read [references/research.md](references/research.md) before making any claim
about performance. The literature contradicts itself and this skill does not
promise a speedup.

### 4. Apply

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

### 5. Report

Print a changelog: what was removed and under which category, what was moved and
where, what contradictions were found and which side currently wins. Then the
token delta per file from the `apply.py` output.

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
- A multi-file move is not atomic. Preflight both writes with `--dry-run` before running either, and use `--rollback` if the second fails.
- Never write with Write or Edit. Always pipe through `apply.py`.
- Never resolve a cross-layer contradiction by deleting one side. Report both.
- Never pass `--force` unless the user asked for it.
- Never claim a command is dead unless you fully resolved the manifest. Silence beats a false accusation.
