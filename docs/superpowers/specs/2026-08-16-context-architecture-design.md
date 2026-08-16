# Context Architecture Design

## Goal

Make Kontextrevision describe and analyze the instruction system that each
harness actually loads. The release will correct routing, token accounting,
duplicate detection, installation, corpus wording, and rollback safety. It will
also add a Structure analysis pass that recommends delivery changes without
creating skills, hooks, or CI configuration.

## Scope

This change includes all seven correctness findings from the review:

1. Treat `AGENTS.md` and `CLAUDE.md` as parallel harness-native instruction
   mechanisms rather than semantic precedence layers.
2. Report scope-aware instruction costs instead of describing the whole
   recursive tree as always active.
3. Separate exact section hashes from normalized duplicate candidates and
   require inspection before any merge.
4. Make the documented Claude Code and Codex installation flows complete and
   test their manifests and namespaced invocations.
5. Describe skill, hook, and CI destinations as recommendations rather than
   transformations.
6. Remove withdrawn corpus percentages and limit percentile claims to the
   sampled corpus.
7. Refuse rollback when the current file no longer matches the version written
   by the transaction, while preserving the backup mode when restoration is
   safe.

The Structure pass examines heading hierarchy, fragmented rules, scope
boundaries, exact and possible duplicates, contradictions, delivery, harness
coverage, load conditions, and important constraints buried in explanatory
prose.

Generating or modifying skills, hooks, hook scripts, settings, or CI workflows
is out of scope. Those operations require harness-specific semantics and a
multi-file transaction design beyond this correction release.

## Routing Model

Every instruction is evaluated along three independent dimensions:

- **Scope:** global, project, or subtree.
- **Delivery:** persistent instruction, on-demand skill, deterministic hook, or
  CI enforcement.
- **Harness coverage:** Claude Code, Codex, OpenCode, or another named harness.

`AGENTS.md` and `CLAUDE.md` are delivery adapters for different harnesses. They
can contain the same kinds of project information. A rule must not move between
them solely because it concerns commands, workflow, architecture, or policy.
Routing may move a rule to a more accurate scope within the same harness. A
cross-harness move is permitted only when coverage is deliberately preserved.

Contradictions are evaluated within the precedence model of each harness. The
tool reports both sources and the applicable scope. It does not claim that an
`AGENTS.md` file overrides a `CLAUDE.md` file because a single harness does not
generally treat those names as one precedence chain.

## Scope-Aware Scanner Output

The scanner keeps recursive discovery so it can review the complete instruction
tree. It adds load semantics instead of collapsing every file into one always-on
total.

Each instruction file reports:

- `scope`: `global`, `project`, or `subtree`.
- `scope_path`: the directory whose work activates the instruction.
- `harnesses`: the harnesses known to consume the filename.
- `load_condition`: `effective_now` or `conditional` for the selected working
  directory.

The digest reports:

- `effective_now_tokens`: instruction tokens active for the selected working
  directory, with deliberate mirrored coverage counted once.
- `conditionally_loaded_tokens`: descendant instruction tokens that become
  active only when work enters their scope.
- `skill_description_tokens`: definition descriptions exposed as triggers.
- `on_demand_body_tokens`: definition bodies loaded on invocation.

The existing broad totals remain only as compatibility aliases when their
meaning is unambiguous. No field or documentation calls the whole recursive
instruction inventory always-on.

The default selected working directory is the scan root. A `--cwd <path>`
option selects another directory within the scan root. The scanner refuses a
working directory outside the scanned tree because its scope graph would be
incomplete.

Claude Code subtree instructions are conditional until Claude accesses that
subtree. Codex `AGENTS.md` files are effective when they lie on the path from
the project root to the selected working directory. OpenCode coverage is
reported from its documented filename support without inventing precedence that
the scanner cannot establish.

## Section Identity

Every parsed section reports two hashes:

- `exact_hash` hashes the heading text, heading level, and byte-preserved body.
- `normalized_hash` hashes normalized heading and body text for candidate
  discovery.

The existing `hash` field is removed rather than left with an ambiguous
contract. Exact hash matches indicate byte-identical section structures.
Normalized matches indicate only a possible duplicate. The skill must open both
blocks, including headings and surrounding hierarchy, before merging either
kind. Hashes narrow inspection but never authorize unattended deletion.

Full-file mirror detection continues to use full normalized file content because
its purpose is recognizing deliberate cross-tool copies, not proving that two
Markdown sections are interchangeable.

Changing `parse_sections` invalidates published corpus measurements under the
project rules. The 250-file corpus will be re-measured before documentation is
published, and the proof document will record the new method and date.

## Structure Analysis Pass

Structure becomes an explicit step in `SKILL.md`, performed after reading the
scope graph and before rewriting content. It checks:

- heading levels that skip or flatten meaningful hierarchy;
- related rules fragmented across distant sections;
- exact and normalized duplicate candidates;
- contradictions at the same scope or across applicable scopes;
- instructions placed at a broader scope than their use;
- harness coverage that would be lost by a proposed move;
- occasional knowledge better delivered by an on-demand skill;
- deterministic requirements better enforced by a hook or CI;
- important constraints buried inside explanatory prose.

The pass may reorganize content inside an instruction file and may recommend a
different scope or delivery mechanism. It does not generate a skill, hook, or CI
change. Recommendations state the source, proposed destination class, harness
coverage impact, and reason.

## Installation

Claude Code documentation will show both required operations:

```text
/plugin marketplace add artttj/kontextrevision
/plugin install kontextrevision@kontextrevision
```

The documented plugin invocation is
`/kontextrevision:kontextrevision`, matching Claude Code plugin namespacing.

Codex distribution will include `.agents/plugins/marketplace.json` alongside
`.codex-plugin/plugin.json`. Its plugin entry will point at the repository plugin
root and use the same plugin name and version. Tests will parse the manifest and
assert that the README commands and invocation agree with it. The native Codex
flow will be exercised in an isolated configuration when the CLI is available.

OpenCode remains a native skill-directory installation because this repository
does not claim a marketplace mechanism that OpenCode does not provide.

## Rollback Safety

Each successful write records the post-write content hash in a sidecar associated
with its backup. Rollback proceeds only when the current file hash equals that
recorded post-write hash. If another edit occurred, rollback refuses without
changing either the file or backup.

Safe rollback restores the backup through a temporary file, applies the backup's
original permission mode, atomically replaces the target, and removes the backup
and sidecar only after success. Legacy backups without a sidecar are not restored
automatically because ownership of the current content cannot be proven.

Both rollback boundaries receive tests: unchanged post-write content permits
restoration, while intervening edits refuse it. Mode preservation receives a
separate regression test.

## Documentation Positioning

The README will lead with context architecture rather than compression:

> **Unattended reviser for agent instruction stacks.** Removes dead context,
> sharpens the rules that matter, and puts each instruction where it belongs.

It will explain that Kontextrevision reviews content and structure, then list
the implemented analysis: duplicated rules, contradictions, actionable
rewrites, scope, delivery recommendations, harness coverage, and guarded
write-back.

The positioning line is:

> **Token reduction is a consequence. Better context architecture is the goal.**

The README and skill will say Kontextrevision finds rules suited to skills,
hooks, or CI. They will not claim those artifacts are generated.

Withdrawn missing-command percentages will be removed from
`classification.md`. The 5,000-token comparison will be limited to approximately
the p90 of the dated sampled corpus rather than all repositories on GitHub.

## Testing and Verification

Changes follow test-driven development. Scanner tests cover both sides of load
boundaries, exact and normalized hash distinctions, mirror accounting, and an
out-of-root `--cwd`. Writer tests cover safe rollback, refusal after an
intervening edit, mode restoration, and missing transaction metadata.

Manifest tests parse both marketplace formats and assert installation and
invocation contracts. Documentation tests reject withdrawn statistics and
unsupported conversion claims.

Final verification includes the full Python 3.9-compatible test suite, Python
compilation, plugin validation, native install checks where the CLIs are
available, corpus re-measurement, a scan for code comments beyond shebangs, and
`git diff --check`.
