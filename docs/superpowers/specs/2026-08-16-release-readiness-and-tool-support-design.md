# Release Readiness and Tool Support Design

## Goal

Prepare the 1.0.0 release by fixing the verified safety and discovery defects,
adding native Codex and OpenCode installation and invocation, and tightening the
public claims around repository instruction research.

## Scope

The release fixes the eight reviewed issues:

- align the plugin manifest with version 1.0.0
- select the newest plugin-cache version before scanning its definitions
- detect recognized commands in inline spans and fenced blocks across common
  development and destructive command families
- preserve the target file's permission mode during atomic replacement
- refuse rewritten content with malformed keep-marker structure
- identify mirrors by normalized full-file content and report relative paths
- allow rollback to find any numbered backup created by the writer
- run the Python 3.9 test suite in GitHub Actions and use its status badge

The README will retain four case studies plus the VS Code counterexample,
shorten the scanner description, and reduce the research discussion to the
claim supported by the evidence.

## Shared Tool Package

`skills/kontextrevision/` remains the only implementation. Claude Code, Codex,
and OpenCode load the same `SKILL.md`, scripts, and references so safety logic
does not diverge between tools.

Claude Code continues to use `.claude-plugin/`. Codex gains a
`.codex-plugin/plugin.json` manifest that points at the existing skill tree and
can be installed through the repository marketplace. The manifest carries the
same release version as the Claude manifest.

OpenCode installs the complete `skills/kontextrevision/` directory under
`~/.config/opencode/skills/kontextrevision/`. OpenCode V2 exposes installed
skills in its slash-command catalog, giving native `/kontextrevision`
invocation without a second prompt definition. The README documents this
installation separately because OpenCode does not consume the repository's
Claude or Codex marketplace manifests.

## Scanner and Writer Behavior

The scanner first groups cache entries by marketplace and plugin, selects the
highest numeric version, and scans definitions only within that directory.
Definitions removed by a newer release therefore disappear from the reported
harness instead of surviving in a synthetic union.

`scan.py` and `apply.py` keep separate standard-library-only command extractors,
but use equivalent parsing rules and boundary tests. Both read inline code and
fenced block lines. Recognition covers package runners and common commands that
can mutate, deploy, test, or publish a repository, including `pytest`, Python,
Git, Cargo, Docker, and the existing npm, Yarn, pnpm, Make, and Composer
families. The writer refuses only a newly recognized command reference, and
`--allow-new-commands` remains the explicit override.

Atomic writes capture the original permission bits and apply them to the
temporary file before replacement. Keep-marker structure is validated on both
the original and proposed content. Rollback discovers backup names without a
numeric ceiling and chooses the highest valid suffix.

Mirror detection hashes normalized full-file content, including headings, and
reports paths relative to the scan root. Only truly identical files are counted
once.

## Research Claims

The detailed reference will distinguish direct repository-instruction studies
from adjacent long-context and prompt-compression work.

Direct studies currently disagree. Lulla et al. report lower runtime and output
token use with `AGENTS.md`. Gloaguen et al. find no statistically significant
completion improvement and higher cost. McMillan finds no detectable adherence
effect from the tested file-structure variables. Shepard and Albrecht show a
gain from probe-refined repository guidance in one model and benchmark setting.
Khatri finds no measurable correctness effect in a smaller two-agent ablation.

Long-context retrieval, instruction adherence, and prompt-compression papers
provide supporting mechanisms, not proof that rewriting an instruction file
improves coding outcomes. They remain clearly labeled as adjacent evidence.

The README claim is therefore limited to preserving specific operational
knowledge while removing redundant or ineffective context. It will not claim
that shorter files make agents smarter or guarantee faster execution.

## Tests and Verification

Every new guard receives tests on both sides of its boundary. Regression tests
cover removed definitions in old plugin versions, each newly recognized command
form and a permitted reuse, mode preservation, malformed proposed markers and
valid markers, unequal headings and exact mirrors, path-qualified mirror output,
and backup suffixes above 99.

Manifest tests assert both plugin formats use version 1.0.0 and reference the
shared skill. CI runs `python3 -m pytest tests/ -q` on Python 3.9. Local release
verification runs the same full suite, validates both JSON manifests, installs
the Codex marketplace from the local checkout, checks the OpenCode package
layout, and opens the rendered README in a browser.

Changes to command extraction and section hashing invalidate published corpus
statistics. The 250-file corpus must be re-scanned before the README or proof
document keeps any affected totals.
