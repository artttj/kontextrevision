# Routing and precedence

## Which destination a rule belongs in

| Destination | Test |
|---|---|
| `SOUL.md` | Follows you everywhere. Voice, directness, how to handle uncertainty. True in every project you will ever open. |
| `AGENTS.md` | Belongs to this project. Conventions, workflow, domain constraints. |
| `CLAUDE.md` | Repo mechanics. Commands, entry points, gotchas. |
| **A skill** (`.claude/skills/`) | Only relevant for one kind of task. Loading it every session pays a permanent cost for occasional value. |
| **A hook** (`.claude/settings.json`) | Must happen every time with no exceptions. Instructions are advisory, hooks are deterministic. |
| **CI** | A violation should block a merge. An instruction file is not a substitute for automated enforcement. |

The last three come from [Anthropic's best practices](https://code.claude.com/docs/en/best-practices)
and are the moves most people miss. Deleting a rule loses it. Moving it to a
skill or a hook keeps it and stops paying for it on every session.

Nous states the first two directly: if it should follow you everywhere it belongs
in `SOUL.md`, if it belongs to a project it belongs in `AGENTS.md`.

`SOUL.md` is injected at slot #1 of the system prompt, ahead of tools, memory,
and project context. A repo convention parked there costs identity-slot tokens in
every project you open, so misrouting into `SOUL.md` is the most expensive
mistake in the stack. Check that file first.

## Precedence when layers conflict

Most specific wins. A project `AGENTS.md` overrides a global `CLAUDE.md`.

When two layers contradict, report both locations with line numbers and state
which one currently wins. **Do not resolve the conflict by deleting one side.**
The user wrote both rules and only they know which one they meant. Silently
picking a winner is how a tool destroys work it does not understand.

## Moving a rule

A move is two edits against two files, and the pair is not atomic. Once the
source is rewritten it becomes git-dirty, so a second `apply.py` call to put it
back would hit the dirty-file guard and refuse. Preflight both writes before
changing anything:

1. `--dry-run` the removal from the source.
2. `--dry-run` the addition to the destination, with `--allow-growth`.
3. Only if **both** report `dry_run` rather than `refused`, run them for real in
   the same order.

If the destination write still fails after a successful preflight, roll the
source back from its backup:

```bash
python3 skills/kontextrevision/scripts/apply.py <source> --rollback
```

`--rollback` restores the most recent backup and deletes it. It bypasses the
guards on purpose, because restoring a known-good backup cannot lose work.

Never leave a half-move in place. A rule that exists in neither file is the one
outcome worse than a rule in the wrong file.

## What routing is not

Do not reorganize a file that is already correctly scoped just because you can
see a tidier arrangement. Routing moves a rule when it is in the wrong file, not
when it is in an unfamiliar order.

## Mirrored files are not duplication

A repository that ships an `AGENTS.md` and a `CLAUDE.md` with identical content
is doing cross-tool compatibility on purpose. Codex and several other harnesses
read `AGENTS.md`, Claude Code reads `CLAUDE.md`. No session loads both, so the
pair costs what one file costs.

Never report a mirrored pair as wasted tokens, and never propose deleting one
side. The digest reports these under `mirrors` and already counts them once.

The one improvement worth suggesting: replace the non-canonical copy with a
one-line import so the two cannot drift apart. That is a maintenance argument,
not a token argument, and the user may reasonably decline it.
