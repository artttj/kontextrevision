# ✂️ kontextrevision

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)](#)
[![Tests](https://github.com/artttj/kontextrevision/actions/workflows/tests.yml/badge.svg)](https://github.com/artttj/kontextrevision/actions/workflows/tests.yml)
[![Claude Code](https://img.shields.io/badge/claude%20code-plugin-8A63D2.svg)](https://claude.com/claude-code)

> Unattended reviser for agent instruction files. Cuts the dead weight and sharpens what stays.

Your `AGENTS.md` goes into the system prompt on every session. Some of it does nothing, some repeats what the agent can already discover, and some is too vague to act on.

Anthropic's [best-practices guide](https://code.claude.com/docs/en/best-practices) states the cost directly: *"Bloated CLAUDE.md files cause Claude to ignore your actual instructions."* The problem is not the tokens, it is the rules you care about getting lost among the ones you do not.

```console
$ /kontextrevision AGENTS.md

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

*Kontextrevision* is German for a revision pass over the context.

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

```bash
/kontextrevision --dry-run     # show changes, write nothing
/kontextrevision AGENTS.md     # revise one file
/kontextrevision               # revise this repo's whole instruction stack
```

Start with `--dry-run`. By default it finds instruction files plus every installed skill, agent and command. No file list, no flags.

The scanner also runs standalone with no install:

```bash
python3 skills/kontextrevision/scripts/scan.py .
python3 skills/kontextrevision/scripts/scan.py ~/.claude
```

It separates always-on descriptions from on-demand bodies and reports duplicate definitions across plugins.

## What it does

| Operation | When |
|---|---|
| **Remove** | Generic advice, repo facts the agent can discover, duplicated documentation |
| **Rewrite** | The intent matters but the wording is not actionable |
| **Merge** | Several rules express the same requirement |
| **Move** | The rule belongs at a different scope, such as `SOUL.md` |
| **Move to a skill** | The knowledge matters only for one kind of task |
| **Convert to a hook** | The requirement must hold every time, deterministically |

Token reduction is a consequence, not the goal. The filter is the one Anthropic states: **would removing this cause the agent to make mistakes?** If not, it should not be always-on context.

The last two operations come from the same guide. Occasional domain knowledge belongs in a skill, and a requirement that must always hold belongs in a hook rather than in advisory prose.

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

## Case studies

Real `--dry-run` passes, 2026-08-16. No upstream repository was modified.

| Repo | Result | What it found |
|---|---|---|
| [joe-bell/cva](https://github.com/joe-bell/cva) ⭐ 6.9k | 8,176 → 5,372 (**−34%**) | 1,828 tokens re-describing skills the harness already injects |
| [electron/electron](https://github.com/electron/electron) ⭐ 122k | 2,688 → 2,256 (**−16%**) | `Project Overview`, `Directory Structure` and `Key Files` |
| [denoland/deno](https://github.com/denoland/deno) ⭐ 108k | 2,965 → 2,651 (**−11%**) | A hand-written table of contents, in a file no human scrolls |
| [egraphs-good/egglog](https://github.com/egraphs-good/egglog) ⭐ 817 | 408 → 272 (**−33%**) | A third of the file was a directory listing |

For contrast, [microsoft/vscode](https://github.com/microsoft/vscode) ⭐ 189k ships a **67-token** `AGENTS.md` with nothing to cut. A mirrored `AGENTS.md` and `CLAUDE.md` pair is detected as cross-tool compatibility, not waste, and counted once. Corpus method across 250 repos, and the measurement bugs fixed before publishing any of it, are in [docs/proof](docs/proof/2026-08-16-corpus-findings.md).

## How it compares

| Tool | Difference |
|---|---|
| [agents-md-polish](https://github.com/legendtkl/agents-md-polish) | Audits instruction files and leaves the edits to you |
| [agnix](https://github.com/agent-sh/agnix) | Validates that config is well-formed, not that instructions earn their place |
| [AgentLint](https://github.com/0xmariowu/AgentLint) | Audits the environment around the agent, not the instructions |
| [agent-slimmer](https://github.com/mheadd/agent-slimmer) | Classifies one file and suggests cuts, without rewriting or routing |

This one continues through the part the others leave manual: rewrite, routing, and write-back.

## Why

The evidence is mixed: repository instructions can change cost, exploration, and task success, but shorter files are not inherently better. The claim here stays narrow: preserve specific operational knowledge, remove context that does no work, and make what remains easier to follow. The direct studies and adjacent long-context research are summarized in [the research reference](skills/kontextrevision/references/research.md).
