# Context Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct Kontextrevision's model of instruction loading and make structure analysis an explicit, truthful product capability.

**Architecture:** Extend the existing standalone scanner with scope and harness metadata while keeping recursive inventory. Harden the standalone writer with hash-bound rollback metadata. Update the existing skill, references, manifests, README, and proof document so every public claim matches tested behavior.

**Tech Stack:** Python 3.9 standard library, pytest, JSON manifests, Markdown.

## Global Constraints

- Target Python 3.9. Do not use `match`, `X | Y`, or `tomllib`.
- `scan.py` remains read-only and `apply.py` remains the only writer.
- Do not add shared imports or runtime dependencies.
- Add no code comments. Use docstrings only for purpose or non-obvious invariants.
- Every new guard needs refusal and permit tests.
- Changing `parse_sections` requires re-measuring the 250-file corpus before publication.
- Skill, hook, and CI conversion remains advisory only.

---

### Task 1: Scope and harness model

**Files:**
- Modify: `tests/test_scan.py`
- Modify: `skills/kontextrevision/scripts/scan.py`

**Interfaces:**
- Produces: `instruction_metadata(path, root, cwd) -> Dict`
- Produces: `build_digest(root, cwd=None) -> Dict`
- Produces digest fields `scope_graph`, `effective_now_tokens`, `conditionally_loaded_tokens`, `skill_description_tokens`, and `on_demand_body_tokens`.

- [ ] Write tests proving root files are effective, descendant files are conditional, path ancestors become effective under `--cwd`, harness coverage matches filenames, mirrors are counted once in the applicable tier, and an outside `--cwd` is refused.
- [ ] Run the focused scanner tests and confirm they fail for missing scope fields.
- [ ] Implement the smallest scope metadata and accounting model that passes the tests.
- [ ] Run all scanner tests.
- [ ] Commit with `feat: add scope-aware instruction accounting`.

### Task 2: Safe section hashes

**Files:**
- Modify: `tests/test_scan.py`
- Modify: `skills/kontextrevision/scripts/scan.py`

**Interfaces:**
- `parse_sections(text) -> List[Dict]` returns `exact_hash` and `normalized_hash`.

- [ ] Write tests showing whitespace changes alter `exact_hash` but not `normalized_hash`, while heading text and level affect both hashes.
- [ ] Run the focused tests and confirm the old `hash` contract fails them.
- [ ] Hash heading, level, and byte-preserved body exactly, plus normalized heading and body separately.
- [ ] Run all scanner tests.
- [ ] Commit with `fix: distinguish exact and candidate section hashes`.

### Task 3: Transaction-bound rollback

**Files:**
- Modify: `tests/test_apply.py`
- Modify: `skills/kontextrevision/scripts/apply.py`

**Interfaces:**
- `write_atomic(path, content) -> str` creates `<backup>.txn` with the post-write SHA-256 hash.
- `rollback(path) -> Dict` restores only when current content matches that hash.

- [ ] Write tests proving unchanged output permits rollback, intervening edits refuse rollback, missing metadata refuses rollback, and safe rollback restores the backup mode.
- [ ] Run the focused rollback tests and confirm the unsafe implementation fails them.
- [ ] Add sidecar creation, hash verification, mode-preserving atomic restore, and cleanup after success.
- [ ] Run all writer tests.
- [ ] Commit with `fix: bind rollback to the written revision`.

### Task 4: Native installation contracts

**Files:**
- Create: `.agents/plugins/marketplace.json`
- Modify: `tests/test_manifest.py`
- Modify: `README.md`

**Interfaces:**
- Codex marketplace name and plugin name are `kontextrevision`.
- Claude invocation is `/kontextrevision:kontextrevision`.
- Codex invocation is `$kontextrevision`.

- [ ] Read the plugin-creator instructions and current manifest schemas.
- [ ] Write manifest tests that parse the Codex marketplace source and assert complete Claude install and namespaced invocation strings.
- [ ] Run the manifest tests and confirm they fail.
- [ ] Add the Codex marketplace and correct the README commands.
- [ ] Run manifest tests and native validators available locally.
- [ ] Commit with `fix: complete native plugin installation`.

### Task 5: Routing and Structure behavior

**Files:**
- Modify: `tests/test_manifest.py`
- Modify: `skills/kontextrevision/SKILL.md`
- Modify: `skills/kontextrevision/references/routing.md`
- Modify: `skills/kontextrevision/references/classification.md`

**Interfaces:**
- Routing uses scope, delivery, and harness coverage.
- Structure identifies hierarchy, fragmentation, duplicates, contradictions, scope, delivery, coverage, load conditions, and buried constraints.

- [ ] Add documentation-contract tests rejecting semantic AGENTS/CLAUDE precedence and conversion claims while requiring the Structure pass and candidate-only hashes.
- [ ] Run the focused tests and confirm they fail.
- [ ] Rewrite routing and skill workflow to match the approved model.
- [ ] Remove the withdrawn 3.6% and 12.9% figures and limit the 5,000-token claim to the sampled corpus.
- [ ] Run manifest and scanner tests.
- [ ] Commit with `docs: define harness-aware structure analysis`.

### Task 6: README and corpus proof

**Files:**
- Modify: `README.md`
- Modify: `docs/proof/2026-08-16-corpus-findings.md`

**Interfaces:**
- README headline promises context architecture, not artifact generation.
- Proof statistics use the new `parse_sections` output.

- [ ] Update README introduction, structure capabilities, token fields, and advisory skill/hook/CI wording.
- [ ] Locate or reconstruct the dated 250-file corpus inputs used by the proof document.
- [ ] Re-run `scan.py` over the corpus and update every affected section statistic and method description.
- [ ] If the corpus cannot be reproduced exactly, remove invalidated section statistics rather than estimate them.
- [ ] Run documentation-contract tests.
- [ ] Commit with `docs: position context architecture accurately`.

### Task 7: Release verification

**Files:**
- Modify only files required by verification findings.

**Interfaces:**
- Full project verification is green with no code comments beyond shebangs.

- [ ] Run `python3 -m pytest tests/ -q`.
- [ ] Run `python3 -m py_compile skills/kontextrevision/scripts/scan.py skills/kontextrevision/scripts/apply.py`.
- [ ] Run plugin validation and isolated native install checks when the CLIs are available.
- [ ] Scan Python tokens for comments beyond shebangs.
- [ ] Run `git diff --check origin/main...HEAD` and inspect the full diff.
- [ ] Commit any verification-only corrections by explicit filename.
