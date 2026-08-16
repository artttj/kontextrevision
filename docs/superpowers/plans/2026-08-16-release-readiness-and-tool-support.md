# Release Readiness and Tool Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a verified 1.0.0 release with the reviewed safety fixes, native Codex and OpenCode use, CI, and evidence-backed documentation.

**Architecture:** Keep `skills/kontextrevision/` as the single shared implementation. Add only thin tool manifests and installation instructions around it. Preserve the scanner/writer isolation by duplicating equivalent standard-library command parsing in each script and proving the behavioral contract in both test modules.

**Tech Stack:** Python 3.9 standard library, pytest, JSON plugin manifests, Markdown skills, GitHub Actions.

## Global Constraints

- Target Python 3.9. Do not use `match`, `X | Y`, or `tomllib`.
- `scan.py` never writes. `apply.py` is the only instruction-file writer.
- Do not add runtime dependencies to either script.
- Keep `scan.py` and `apply.py` free of shared imports.
- Every guard needs a refusing and permitting boundary test.
- Use `apply.py` for any instruction-file edit.
- Re-measure published corpus statistics after changing `extract_commands`.
- Stage files by name and use `type: summary under 72 chars` commits.

---

### Task 1: Release metadata and shared tool packaging

**Files:**
- Modify: `.claude-plugin/plugin.json`
- Create: `.codex-plugin/plugin.json`
- Modify: `tests/test_manifest.py`

**Interfaces:**
- Consumes: the existing `skills/kontextrevision/` directory
- Produces: Claude and Codex manifests at version `1.0.0`, both resolving the same skill tree

- [ ] **Step 1: Write failing manifest tests**

Add tests that load both plugin manifests, assert `version == "1.0.0"`, and assert the Codex manifest's `skills` field resolves to `skills/`. The existing `.claude-plugin/marketplace.json` remains the repository marketplace entry used by both plugin clients.

```python
def test_plugin_versions_match_release():
    for directory in [".claude-plugin", ".codex-plugin"]:
        with open(os.path.join(ROOT, directory, "plugin.json"), encoding="utf-8") as fh:
            assert json.load(fh)["version"] == "1.0.0"


def test_codex_plugin_uses_shared_skill_tree():
    with open(os.path.join(ROOT, ".codex-plugin", "plugin.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["skills"] == "./skills/"
    assert os.path.exists(os.path.join(ROOT, data["skills"], "kontextrevision", "SKILL.md"))
```

- [ ] **Step 2: Verify the tests fail for the missing Codex manifest and stale Claude version**

Run: `python3 -m pytest tests/test_manifest.py -q`

Expected: failures identify `0.1.0` and the missing `.codex-plugin/plugin.json`.

- [ ] **Step 3: Add the minimal manifests**

Change the Claude version to `1.0.0`. Build the Codex manifest from the current installed schema with `name`, `version`, `description`, `author`, `license`, and `skills: "./skills/"`. Do not duplicate the skill.

- [ ] **Step 4: Verify manifest tests and native Codex discovery**

Run: `python3 -m pytest tests/test_manifest.py -q`

Run Codex validation against an isolated temporary configuration directory so the user's installed marketplaces are not changed:

```bash
release_codex_home=$(mktemp -d)
CODEX_HOME="$release_codex_home" codex plugin marketplace add "$PWD" --json
CODEX_HOME="$release_codex_home" codex plugin list
```

Expected: the marketplace is accepted and `kontextrevision` is listed.

- [ ] **Step 5: Commit the packaging change**

```bash
git add .claude-plugin/plugin.json .codex-plugin/plugin.json tests/test_manifest.py
git commit -m "feat: add Codex plugin support"
```

---

### Task 2: Select one plugin-cache version before scanning definitions

**Files:**
- Modify: `tests/test_scan.py`
- Modify: `skills/kontextrevision/scripts/scan.py`

**Interfaces:**
- Consumes: paths matching `plugins/cache/<market>/<plugin>/<version>/...`
- Produces: `discover_harness(root) -> List[str]` containing definitions only from each plugin's highest numeric version

- [ ] **Step 1: Write the removed-definition regression test**

```python
def test_old_definition_removed_in_new_version_is_not_counted(tmp_path):
    old = write(tmp_path, "plugins/cache/market/thing/1.0.0/skills/old/SKILL.md", "---\nname: old\ndescription: old\n---\n")
    new = write(tmp_path, "plugins/cache/market/thing/2.0.0/skills/new/SKILL.md", "---\nname: new\ndescription: new\n---\n")
    assert scan.discover_harness(str(tmp_path)) == [new]
    assert old not in scan.discover_harness(str(tmp_path))
```

Retain the existing same-definition test as the permitted boundary.

- [ ] **Step 2: Verify the regression test fails with the synthetic union**

Run: `python3 -m pytest tests/test_scan.py::test_old_definition_removed_in_new_version_is_not_counted -q`

Expected: the returned list incorrectly includes the 1.0.0 `old` definition.

- [ ] **Step 3: Select newest cache roots before classifying files**

Change discovery to record the greatest version for each `(marketplace, plugin)` key, then include cached definitions only when their version equals that selected version. Keep uncached definitions unchanged and return sorted absolute paths.

- [ ] **Step 4: Verify focused and scanner tests**

Run: `python3 -m pytest tests/test_scan.py -q`

Expected: all scanner tests pass.

- [ ] **Step 5: Commit the cache fix**

```bash
git add tests/test_scan.py skills/kontextrevision/scripts/scan.py
git commit -m "fix: exclude superseded plugin definitions"
```

---

### Task 3: Make command invention detection match documented behavior

**Files:**
- Modify: `tests/test_scan.py`
- Modify: `tests/test_apply.py`
- Modify: `skills/kontextrevision/scripts/scan.py`
- Modify: `skills/kontextrevision/scripts/apply.py`

**Interfaces:**
- Consumes: Markdown containing inline code spans or fenced code lines
- Produces: normalized recognized commands from npm, Yarn, pnpm, Make, Composer, pytest, Python, Git, Cargo, and Docker families
- Produces: `invented_commands(original, new) -> List[str]`

- [ ] **Step 1: Write failing scanner tests for all reviewed examples**

Use one parametrized test for inline references and one fenced-block test:

```python
@pytest.mark.parametrize("command", [
    "pytest tests/",
    "cargo test",
    "git push --force",
    "python manage.py migrate",
    "docker compose down",
])
def test_extract_commands_recognizes_common_commands(command):
    assert scan.extract_commands("Run `{0}`.".format(command)) == [command]


def test_extract_commands_reads_fenced_commands():
    assert scan.extract_commands("```bash\nmake deploy\n```") == ["make deploy"]
```

Import `pytest` in `tests/test_scan.py`.

- [ ] **Step 2: Write failing writer tests on both sides of the guard**

For each reviewed command, assert an absent-to-present rewrite is refused. Add one fenced `make deploy` refusal. Add a parametrized permitted test where the original and rewrite both contain the same recognized command. Keep the existing `--allow-new-commands` override test.

- [ ] **Step 3: Verify failures identify unrecognized or fenced commands**

Run: `python3 -m pytest tests/test_scan.py tests/test_apply.py -q`

Expected: new command cases pass through or are absent from scanner output.

- [ ] **Step 4: Implement equivalent parsers independently**

Retain `code_spans(text)` in each file, including fenced lines and trailing shell-comment stripping. Expand the anchored command regex without parsing arbitrary prose. Normalize whitespace, deduplicate in encounter order, and retain the target stopword and placeholder protection for Make and package runners.

Do not introduce a shared import between the scripts.

- [ ] **Step 5: Verify all command and writer tests**

Run: `python3 -m pytest tests/test_scan.py tests/test_apply.py -q`

Expected: all tests pass, including refusals and permitted reuse.

- [ ] **Step 6: Commit the command guard**

```bash
git add tests/test_scan.py tests/test_apply.py skills/kontextrevision/scripts/scan.py skills/kontextrevision/scripts/apply.py
git commit -m "fix: detect invented command references"
```

---

### Task 4: Preserve modes and validate proposed keep markers

**Files:**
- Modify: `tests/test_apply.py`
- Modify: `skills/kontextrevision/scripts/apply.py`

**Interfaces:**
- Consumes: an existing file and proposed UTF-8 content
- Produces: atomic replacement with the original permission bits
- Produces: refusal when either original or proposed keep markers are malformed

- [ ] **Step 1: Write the mode-preservation test**

```python
def test_write_atomic_preserves_file_mode(tmp_path):
    target = write(tmp_path, "AGENTS.md", "private\n")
    os.chmod(target, 0o600)
    apply.write_atomic(target, "rewritten\n")
    assert stat.S_IMODE(os.stat(target).st_mode) == 0o600
```

Import `stat` in `tests/test_apply.py`.

- [ ] **Step 2: Write refusing and permitting proposed-marker tests**

Add separate tests for a proposed unmatched open, unmatched close, and correctly paired proposed block. Use content lengths that do not trigger the shrink or growth guards first.

- [ ] **Step 3: Verify the new tests fail for the expected reasons**

Run: `python3 -m pytest tests/test_apply.py -q`

Expected: mode becomes the process default and malformed proposed markers are written.

- [ ] **Step 4: Preserve mode and guard proposed content**

Read `stat.S_IMODE(os.stat(path).st_mode)` before creating the temporary file and call `os.chmod(tmp, mode)` before `os.replace`. Run `unpaired_keep_markers(new_content)` after validating the original and refuse with wording that identifies the proposed rewrite.

- [ ] **Step 5: Verify writer tests**

Run: `python3 -m pytest tests/test_apply.py -q`

Expected: all writer tests pass.

- [ ] **Step 6: Commit the writer safety fixes**

```bash
git add tests/test_apply.py skills/kontextrevision/scripts/apply.py
git commit -m "fix: preserve safe rewrite invariants"
```

---

### Task 5: Make mirrors exact and rollback unbounded

**Files:**
- Modify: `tests/test_scan.py`
- Modify: `tests/test_apply.py`
- Modify: `skills/kontextrevision/scripts/scan.py`
- Modify: `skills/kontextrevision/scripts/apply.py`

**Interfaces:**
- Consumes: digested instruction files under a scan root
- Produces: path-qualified mirror pairs only for normalized full-file equality
- Consumes: `.bak` and `.bak.<integer>` siblings
- Produces: rollback from the greatest existing numeric suffix, with `.bak` ordered before `.bak.1`

- [ ] **Step 1: Write mirror boundary tests**

Add a refusal-side test where `AGENTS.md` and `CLAUDE.md` have identical bodies under different headings and assert `mirrors == []`. Add a permitted test for whitespace-normalized full-file equality. Add two mirrored pairs in different subdirectories and assert the output contains paths relative to the scan root, such as `sub/AGENTS.md` and `sub/CLAUDE.md`.

- [ ] **Step 2: Write rollback-above-99 and invalid-suffix tests**

Create `.bak`, `.bak.99`, and `.bak.100`, assert `.bak.100` is restored, and assert unrelated files such as `.bak.latest` are ignored. Retain the no-backup refusal test.

- [ ] **Step 3: Verify focused failures**

Run: `python3 -m pytest tests/test_scan.py tests/test_apply.py -q`

Expected: different headings are treated as mirrors, mirror paths are ambiguous, and `.bak.100` is missed.

- [ ] **Step 4: Add full-file hashes and numeric backup discovery**

Have `digest_file` include a hash of `normalize_body(text)`. Compare that hash in `_find_mirrors`, using `os.path.relpath(path, root)` for output. Pass `root` into `_find_mirrors` from `build_digest`.

Use `glob.glob(path + ".bak*")` in `apply.py`, accept only the exact base backup or a suffix matching `\.bak\.(\d+)$`, sort by parsed integer, and restore the greatest entry.

- [ ] **Step 5: Verify scanner and writer tests**

Run: `python3 -m pytest tests/test_scan.py tests/test_apply.py -q`

Expected: all tests pass.

- [ ] **Step 6: Commit the exactness fixes**

```bash
git add tests/test_scan.py tests/test_apply.py skills/kontextrevision/scripts/scan.py skills/kontextrevision/scripts/apply.py
git commit -m "fix: make mirror and rollback discovery exact"
```

---

### Task 6: Add CI and update public documentation

**Files:**
- Create: `.github/workflows/tests.yml`
- Modify: `README.md`
- Modify: `skills/kontextrevision/references/research.md`
- Modify: `docs/proof/2026-08-16-corpus-findings.md`
- Modify: `tests/test_manifest.py`

**Interfaces:**
- Produces: a GitHub Actions check running the documented Python 3.9 test command
- Produces: install instructions for Claude Code, Codex, and OpenCode
- Produces: research claims separated into direct and adjacent evidence

- [ ] **Step 1: Add failing documentation and workflow contract tests**

Add tests that assert the workflow exists, contains Python `3.9`, and runs `python3 -m pytest tests/ -q`. Assert README links the workflow badge and documents Codex and OpenCode installation without claiming those tools share a marketplace command.

- [ ] **Step 2: Verify contract tests fail**

Run: `python3 -m pytest tests/test_manifest.py -q`

Expected: workflow and cross-tool documentation assertions fail.

- [ ] **Step 3: Add the workflow**

Create a minimal `push` and `pull_request` workflow using `actions/checkout`, `actions/setup-python` with `python-version: "3.9"`, install pytest, and run the exact project test command.

- [ ] **Step 4: Update README and research reference**

Replace the static test-count badge with the Actions badge. Split install instructions by tool. Document Codex marketplace installation using the locally verified commands. Document copying the complete skill directory to `~/.config/opencode/skills/kontextrevision/` and invoking `/kontextrevision`.

Shorten the scanner paragraph, retain `cva`, `electron`, `deno`, and `egglog`, and keep VS Code as the counterexample. Reduce `Why` to the narrow claim and point detailed readers to `skills/kontextrevision/references/research.md`.

Expand that reference with direct-study entries for McMillan, Shepard and Albrecht, and Khatri. Add a separate adjacent-evidence section for Lost in the Middle, VerIFY, and prompt compression, explicitly stating that these do not prove coding-task gains from rewriting instruction files.

- [ ] **Step 5: Verify documentation contracts**

Run: `python3 -m pytest tests/test_manifest.py -q`

Expected: all contract tests pass.

- [ ] **Step 6: Commit CI and documentation**

```bash
git add .github/workflows/tests.yml README.md skills/kontextrevision/references/research.md docs/proof/2026-08-16-corpus-findings.md tests/test_manifest.py
git commit -m "docs: document cross-tool installation"
```

---

### Task 7: Re-measure affected published statistics

**Files:**
- Modify: `README.md`
- Modify: `skills/kontextrevision/references/research.md`
- Modify: `docs/proof/2026-08-16-corpus-findings.md`

**Interfaces:**
- Consumes: the documented 100 `AGENTS.md`, 100 `CLAUDE.md`, and 50 `SOUL.md` corpus selection
- Produces: statistics generated by the revised scanner, or removal of any number that cannot be reproduced exactly

- [ ] **Step 1: Reconstruct the documented sample outside the repository**

Use GitHub code search in the same one-file-per-repository order documented for the original measurement. Store downloads in a `mktemp -d` directory, never in the worktree. Record failures and refuse to substitute a different repository silently.

- [ ] **Step 2: Run the revised scanner over all 250 files**

Run the scanner on the temporary corpus and recompute sizes, sections, command references, and command-family counts. Fully resolve manifests before classifying a referenced command as missing.

- [ ] **Step 3: Update or remove affected numbers**

If the exact corpus can be reproduced, replace affected values in all three documents. If it cannot, remove the unreproducible command statistic and explain the limitation instead of retaining a stale headline.

- [ ] **Step 4: Re-run the local harness measurement**

Run `python3 skills/kontextrevision/scripts/scan.py --harness ~/.claude` and the equivalent Codex/OpenCode roots that exist. Replace or remove the README's old `72,435 / 2.8M / 403` figures; the shortened scanner paragraph should not retain personal-machine totals unless freshly measured and clearly scoped.

- [ ] **Step 5: Verify documentation consistency and commit**

Run: `rg -n '72,435|2\.8M|403|3\.6%|465,901|92 sections' README.md skills/kontextrevision/references/research.md docs/proof/2026-08-16-corpus-findings.md`

Inspect every remaining match against the new measurement output.

```bash
git add README.md skills/kontextrevision/references/research.md docs/proof/2026-08-16-corpus-findings.md
git commit -m "docs: refresh instruction corpus findings"
```

---

### Task 8: Final release verification

**Files:**
- Verify all modified files

**Interfaces:**
- Produces: fresh evidence that tests, manifests, installation, and rendered documentation work

- [ ] **Step 1: Run the complete test suite**

Run: `python3 -m pytest tests/ -q`

Expected: zero failures.

- [ ] **Step 2: Run syntax and manifest validation**

```bash
python3 -m py_compile skills/kontextrevision/scripts/scan.py skills/kontextrevision/scripts/apply.py
python3 -m json.tool .claude-plugin/plugin.json >/dev/null
python3 -m json.tool .codex-plugin/plugin.json >/dev/null
git diff --check a9b502e..HEAD
```

Expected: every command exits zero.

- [ ] **Step 3: Validate native package discovery in temporary homes**

Use a temporary `CODEX_HOME` to add the local marketplace and list/install the plugin. Validate OpenCode discovery with an isolated XDG configuration:

```bash
release_opencode_home=$(mktemp -d)
mkdir -p "$release_opencode_home/opencode/skills"
cp -R skills/kontextrevision "$release_opencode_home/opencode/skills/kontextrevision"
XDG_CONFIG_HOME="$release_opencode_home" opencode debug skill
```

Expected: the output lists `kontextrevision`. Do not mutate the user's real tool configuration.

- [ ] **Step 4: Browser-check README**

Render README locally, open it in a browser, and inspect the badges, install sections, tables, links, warning block, and research link at desktop and narrow widths.

- [ ] **Step 5: Inspect repository state**

Run: `git status --short && git log --oneline -10`

Expected: no uncommitted release files, no generated corpus artifacts, and only intentional commits.
