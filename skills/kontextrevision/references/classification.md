# Block classification

Grounded in [Anthropic's Claude Code best practices](https://code.claude.com/docs/en/best-practices),
which publishes an explicit include/exclude table for `CLAUDE.md`. Taxonomy
adapted from [agent-slimmer](https://github.com/mheadd/agent-slimmer) (MIT).

## The official table

| Include | Exclude |
|---|---|
| Bash commands Claude cannot guess | Anything Claude can figure out by reading code |
| Code style rules that differ from defaults | Standard language conventions Claude already knows |
| Testing instructions and preferred test runners | Detailed API documentation, link to it instead |
| Repository etiquette, branch naming, PR conventions | Information that changes frequently |
| Architectural decisions specific to your project | Long explanations or tutorials |
| Developer environment quirks, required env vars | File-by-file descriptions of the codebase |
| Common gotchas or non-obvious behaviors | Self-evident practices like "write clean code" |

Anthropic's stated filter is the same one this skill uses: *"For each line, ask:
would removing this cause Claude to make mistakes? If not, cut it."*

**The strongest argument for cutting is not cost.** Anthropic states it directly:
*"Bloated CLAUDE.md files cause Claude to ignore your actual instructions."* A
long file does not simply cost more, it makes the rules that matter less likely
to be followed. Report that, not just the token delta.

Classify every block in the file. A block is a section, or a paragraph when the
file has no headings.

## Remove

| Category | What it looks like |
|---|---|
| Redundant with repo | Restates the README, a config file, or the directory structure |
| Discoverable by exploration | File locations, module purposes, language and framework in use |
| Generic best practice | "write clean code", "follow existing patterns", "add tests" |
| Vague behavioral guidance | "be careful with the database", "consider performance" |

Vague guidance is a rewrite candidate first and a deletion candidate second. If
you can recover what the author meant, rewrite it into something the agent can
pass or fail. Only delete when the intent is unrecoverable.

A rewrite is finished when you can answer: how would an agent know it complied?
"Be careful with the database" fails that test.

**A rewrite may sharpen wording. It may not invent procedure.** If the original
never named a command, a tool, or a step, the rewrite must not introduce one.
Turning "be careful with the database" into "run `make db-migrate-dry` first"
invents a workflow that may not exist in this project, and the author never
asked for it. `apply.py` refuses any rewrite that names a command the original
did not, unless `--allow-new-commands` is passed explicitly.

**The writer cannot enforce this alone.** Its invention guard compares command
references, so it refuses a rewrite that introduces `make deploy` from nowhere.
It cannot detect an invented *requirement* that names no command: turning
"consider regressions" into "run the full test suite and state which tests you
ran" adds two obligations the author never wrote, and passes every guard. That
judgment is yours, not the writer's.

The safe rewrite states the same requirement as a directive. "Consider how a fix
might affect existing features" becomes "Do not introduce a regression to
existing features." An agent can pass or fail the second. Nothing was added.

Two legitimate ways to sharpen a vague rule:

- **Ground it in what the file already says.** If the same file elsewhere names
  `make migrate`, a database rule may reference `make migrate`.
- **Propose it instead of writing it.** When the intent is real but the specifics
  are not recoverable from the repository, report the rule and your suggested
  wording, and let the user decide. Do not write it.

Deleting a rule whose intent you cannot recover is honest. Replacing it with a
procedure you made up is not.

## Keep

| Category | What it looks like |
|---|---|
| Specific tool or process requirement | "use `uv` for dependencies", "run `make lint` before committing" |
| Behavioral constraint not inferable from code | "flag ambiguous requirements rather than guessing", "migrations must be reversible" |
| Unique project knowledge | Local auth setup, known broken areas, undocumented external dependencies |

## The editorial filter

For every block classified Keep, ask one question:

> Would the agent behave incorrectly without this instruction?

If no, remove it. The bar is changing behavior, not confirming it.

## Dead commands

The digest lists every command the file references. Check each one against the
repo before keeping it. A rule pointing at a command that does not exist is
worse than no rule, because the agent will try it.

Verify carefully, because naive checking produced false accusations during the
corpus study:

- **Follow `include` directives recursively.** Makefiles routinely split targets
  across included files, and includes nest. A target missing from the root
  Makefile is usually present two levels down.
- **Skip npm workspace monorepos.** When `package.json` has a `workspaces` key,
  a script may live in any workspace. Do not judge it.
- **Refuse to judge what you cannot fully resolve.** If an include path lives
  inside a git submodule, or is built from a variable or glob, say nothing about
  that file's commands.

The invalidated measurement mixed a narrower command extractor with incomplete
manifest resolution. It was withdrawn rather than reused after the extractor
changed. Say nothing rather than accuse a real project on incomplete evidence.

## Merging

Two rules saying the same thing in different words are a common defect in files
edited by several people. Hashes only identify candidates. `exact_hash` includes
the heading, level, and byte-preserved body. `normalized_hash` tolerates
formatting differences. Open both blocks with their surrounding hierarchy,
confirm that scope and meaning match, then merge into the stronger wording.

## Two destinations that are not deletion

Anthropic's guidance names two places a rule can go instead of being removed.
Prefer these over deletion when they apply.

**Recommend a hook.** *"If Claude already does something correctly without the
instruction, delete it or convert it to a hook."* Hooks are deterministic while
instruction files are advisory: *"Unlike CLAUDE.md instructions which are
advisory, hooks are deterministic and guarantee the action happens."* A rule
that must hold every time without exception belongs in `.claude/settings.json`,
not in prose that the model may or may not follow.

If a violation would fail CI, the rule belongs in CI. An instruction file is not
a substitute for automated enforcement.

**Recommend a skill.** *"For domain knowledge or workflows that are only relevant
sometimes, use skills instead. Claude loads them on demand without bloating
every conversation."* This is the highest-value move available: a block that
only matters for one kind of task is paying on every session for value it
delivers on a few. Moving it to `.claude/skills/` converts an always-on cost
into an on-demand one.

Suggest these moves. Never perform them silently, because both change where the
user has to look for their own rules.

## Never invent

Only remove, merge, move, or tighten content that already exists. Adding an
instruction the user did not write is out of scope, which is why `apply.py`
refuses any rewrite that grows a file by more than 10%.
