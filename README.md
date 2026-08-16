# ✂️ kontextrevision

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)](#)
[![Tests](https://github.com/artttj/kontextrevision/actions/workflows/tests.yml/badge.svg)](https://github.com/artttj/kontextrevision/actions/workflows/tests.yml)
[![Claude Code](https://img.shields.io/badge/claude%20code-plugin-8A63D2.svg)](https://claude.com/claude-code)

> **Guarded reviser for agent instruction stacks.** Removes dead context, sharpens the rules that matter, and puts each instruction where it belongs.

Kontextrevision is not a minifier. It reviews the architecture of agent context:

- merges duplicated and overlapping rules
- surfaces contradictions across scopes and tools
- rewrites vague guidance into actionable constraints without inventing procedures
- identifies instructions better delivered by on-demand skills
- finds requirements better enforced by hooks or CI
- preserves cross-tool coverage while routing rules to the correct scope
- writes through git, keep-marker, growth, invention, and backup guards

Persistent instruction files consume model context whenever their scope is active. The problem is not simply token count. Important rules compete with discoverable facts, instructions load at the wrong scope, guidance is duplicated across tools, and requirements get buried in prose.

```console
$ /kontextrevision:kontextrevision AGENTS.md

  Merged   2 rules → 1        near-identical, lines 204 and 211
  Rewrote  "Consider how a fix might affect existing features and
            avoid any regression or breaking change."
        →  "Do not introduce a regression or a breaking change to
            existing features."
  Removed  Version Types      236 tok   already in CONTRIBUTING.md
  Kept     Required Checks              names real commands

  AGENTS.md  1,969 → 1,676 tokens  (-14.9%)
```

Real `--dry-run` output from [PaloAltoNetworks/docusaurus-openapi-docs](https://github.com/PaloAltoNetworks/docusaurus-openapi-docs). An agent cannot pass or fail "consider how". It can pass or fail "do not introduce". Same requirement, now checkable, and nothing was invented to get there.

The name combines the German *Kontext* and *Revision*: a revision pass over the context.

## Quick install

Run the commands for your tool, or ask your agent to install `artttj/kontextrevision`.

### Claude Code

```text
/plugin marketplace add artttj/kontextrevision
/plugin install kontextrevision@kontextrevision
```

### Codex

```bash
codex plugin marketplace add artttj/kontextrevision
codex plugin add kontextrevision@kontextrevision
```

### OpenCode

```bash
git clone https://github.com/artttj/kontextrevision ~/.local/share/kontextrevision
mkdir -p ~/.config/opencode/skills
ln -s ~/.local/share/kontextrevision/skills/kontextrevision ~/.config/opencode/skills/kontextrevision
```

See [Install](#install) for native invocation forms.

## Case studies

Real `--dry-run` revisions from 2026-08-16. Token counts are estimates. No upstream repository was modified.

| Repository | Estimated change | What changed and why |
|---|---:|---|
| [joe-bell/cva](https://github.com/joe-bell/cva) ⭐ 6.9k | 8,176 → 5,372 (**−34%**) | Removed 1,828 tokens that duplicated installed skill guidance already available to the harness |
| [electron/electron](https://github.com/electron/electron) ⭐ 122k | 2,688 → 2,256 (**−16%**) | Removed discoverable project-overview, directory-tree, and key-file summaries |
| [denoland/deno](https://github.com/denoland/deno) ⭐ 108k | 2,965 → 2,651 (**−11%**) | Removed a hand-maintained table of contents that duplicated the document's heading structure |
| [egraphs-good/egglog](https://github.com/egraphs-good/egglog) ⭐ 817 | 408 → 272 (**−33%**) | Removed a directory inventory the agent can recover directly from the repository tree |

These are context-revision results, not claims about task-completion quality or model performance. The full methodology and limitations are documented in [the corpus findings](docs/proof/2026-08-16-corpus-findings.md).

For contrast, [microsoft/vscode](https://github.com/microsoft/vscode) ⭐ 189k ships a **67-token** `AGENTS.md` with nothing to cut. A mirrored `AGENTS.md` and `CLAUDE.md` pair is detected as cross-tool compatibility, not waste, and counted once within its load tier.

## Install

### Claude Code

```bash
/plugin marketplace add artttj/kontextrevision
/plugin install kontextrevision@kontextrevision
```

Invoke it with `/kontextrevision:kontextrevision`.

### Codex

```bash
codex plugin marketplace add artttj/kontextrevision
codex plugin add kontextrevision@kontextrevision
```

Invoke it with `$kontextrevision`.

### OpenCode

```bash
git clone https://github.com/artttj/kontextrevision ~/.local/share/kontextrevision
mkdir -p ~/.config/opencode/skills
ln -s ~/.local/share/kontextrevision/skills/kontextrevision ~/.config/opencode/skills/kontextrevision
```

Invoke it with `/kontextrevision`.

## Usage

Claude Code:

```bash
/kontextrevision:kontextrevision --dry-run
/kontextrevision:kontextrevision AGENTS.md
```

Codex and OpenCode use their native invocation forms:

```text
$kontextrevision --dry-run
/kontextrevision --dry-run
```

Start with `--dry-run`. By default it finds instruction files plus every installed skill, agent and command. No file list, no flags.

The scanner also runs standalone with no install:

```bash
python3 skills/kontextrevision/scripts/scan.py .
python3 skills/kontextrevision/scripts/scan.py ~/.claude
```

It reports the cross-tool instruction inventory as `effective_now_tokens` and descendant `conditionally_loaded_tokens`, then breaks both down per tool under `harness_tokens`. `skill_description_tokens` and `on_demand_body_tokens` keep trigger cost separate from invoked bodies. The scope graph shows which harness receives each file, where that file applies, and what activates it.

## What it does

| Operation | When |
|---|---|
| **Structure** | Hierarchy, scope, loading, coverage, contradictions, or important rules are hard to follow |
| **Remove** | Generic advice, repo facts the agent can discover, duplicated documentation |
| **Rewrite** | The intent matters but the wording is not actionable |
| **Merge** | Several rules express the same requirement |
| **Route** | The rule belongs at a narrower or broader scope without losing harness coverage |
| **Recommend delivery** | A rule belongs in an on-demand skill, deterministic hook, or CI check |

**Token reduction is a consequence. Better context architecture is the goal.**

This release identifies better delivery targets but does not create skills, hooks, settings, or CI workflows. Those changes need harness-specific validation and explicit user control.

## Safety

This rewrites files that govern agent behavior, so every write passes code-enforced guards.

| Guard | Refuses when |
|---|---|
| **Git** | A tracked file already has uncommitted edits |
| **Empty** | The proposed rewrite is blank |
| **Shrink** | Output falls below 20% of the original |
| **Keep markers** | Protected content was removed or altered |
| **Growth** | Output grows by more than 10% |
| **Invention** | A new recognized command reference appears in the rewrite |

Backups are written before every change and never overwritten. Symlinks and non-UTF-8 files are refused. Mark anything the reviser must not touch:

```html
<!-- kontextrevision:keep -->
This survives byte for byte.
<!-- /kontextrevision:keep -->
```

> [!WARNING]
> The invention guard compares command references, so it catches a rewrite that introduces `make deploy` out of nowhere. It cannot detect an invented *requirement* that names no command. Sharpening wording is safe to run unattended. Turning a vague rule into a specific procedure is a judgment call, and the skill is instructed to propose those rather than write them.

## How it compares

| Tool | Difference |
|---|---|
| [agents-md-polish](https://github.com/legendtkl/agents-md-polish) | Audits instruction files and leaves the edits to you |
| [agnix](https://github.com/agent-sh/agnix) | Validates that config is well-formed, not that instructions earn their place |
| [AgentLint](https://github.com/0xmariowu/AgentLint) | Audits the environment around the agent, not the instructions |
| [agent-slimmer](https://github.com/mheadd/agent-slimmer) | Classifies one file and suggests cuts, without rewriting or routing |

This one reviews the instruction system around the agent, then continues through guarded rewrite, scope-aware routing, and write-back.

## Why

Anthropic's [best-practices guide](https://code.claude.com/docs/en/best-practices) names one failure mode directly: *"Bloated CLAUDE.md files cause Claude to ignore your actual instructions."*

The evidence is mixed: repository instructions can change cost, exploration, and task success, but shorter files are not inherently better. The claim here stays narrow: preserve specific operational knowledge, remove context that does no work, and make what remains easier to follow. The direct studies and adjacent long-context research are summarized in [the research reference](skills/kontextrevision/references/research.md).
