import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "kontextrevision", "scripts"))

import scan
from conftest import write


def test_classify_role_by_basename():
    assert scan.classify_role("/x/SOUL.md") == "soul"
    assert scan.classify_role("/x/AGENTS.md") == "agents"
    assert scan.classify_role("/x/CLAUDE.md") == "claude"
    assert scan.classify_role("/x/.claude.local.md") == "claude"
    assert scan.classify_role("/x/.claude/rules/web/design.md") == "rules"
    assert scan.classify_role("/repo/eslint-plugin/lib/rules/no-console.md") == "unknown"
    assert scan.classify_role("/x/README.md") == "unknown"


def test_discover_finds_instruction_files_only(tmp_path):
    write(tmp_path, "AGENTS.md", "# a")
    write(tmp_path, "SOUL.md", "# s")
    write(tmp_path, "README.md", "# nope")
    write(tmp_path, "sub/CLAUDE.md", "# c")
    found = scan.discover(str(tmp_path))
    names = sorted(os.path.basename(p) for p in found)
    assert names == ["AGENTS.md", "CLAUDE.md", "SOUL.md"]


def test_discover_skips_vendor_dirs(tmp_path):
    write(tmp_path, "AGENTS.md", "# a")
    write(tmp_path, "node_modules/pkg/AGENTS.md", "# skip")
    write(tmp_path, ".git/AGENTS.md", "# skip")
    found = scan.discover(str(tmp_path))
    assert len(found) == 1


def test_parse_sections_splits_on_headings():
    text = "intro line\n\n# One\nbody one\n\n## Two\nbody two\n"
    secs = scan.parse_sections(text)
    assert [s["heading"] for s in secs] == [None, "One", "Two"]
    assert [s["level"] for s in secs] == [0, 1, 2]
    assert secs[1]["line"] == 3


def test_parse_sections_normalized_hash_ignores_whitespace_differences():
    a = scan.parse_sections("# H\nsame   body\n")
    b = scan.parse_sections("# H\n\n  same body  \n\n")
    assert a[0]["normalized_hash"] == b[0]["normalized_hash"]
    assert a[0]["exact_hash"] != b[0]["exact_hash"]


def test_parse_sections_different_content_differs():
    a = scan.parse_sections("# H\nalpha\n")
    b = scan.parse_sections("# H\nbeta\n")
    assert a[0]["exact_hash"] != b[0]["exact_hash"]
    assert a[0]["normalized_hash"] != b[0]["normalized_hash"]


def test_parse_sections_hashes_include_heading_and_level():
    heading_a = scan.parse_sections("# Python\nsame body\n")[0]
    heading_b = scan.parse_sections("# Rust\nsame body\n")[0]
    level_b = scan.parse_sections("## Python\nsame body\n")[0]
    assert heading_a["exact_hash"] != heading_b["exact_hash"]
    assert heading_a["normalized_hash"] != heading_b["normalized_hash"]
    assert heading_a["exact_hash"] != level_b["exact_hash"]
    assert heading_a["normalized_hash"] != level_b["normalized_hash"]


def test_digest_file_exact_hash_preserves_line_endings(tmp_path):
    lf = os.path.join(str(tmp_path), "lf", "AGENTS.md")
    crlf = os.path.join(str(tmp_path), "crlf", "AGENTS.md")
    os.makedirs(os.path.dirname(lf))
    os.makedirs(os.path.dirname(crlf))
    with open(lf, "wb") as fh:
        fh.write(b"# Rules\nbody\n")
    with open(crlf, "wb") as fh:
        fh.write(b"# Rules\r\nbody\r\n")
    lf_section = scan.digest_file(lf)["sections"][0]
    crlf_section = scan.digest_file(crlf)["sections"][0]
    assert lf_section["exact_hash"] != crlf_section["exact_hash"]
    assert lf_section["normalized_hash"] == crlf_section["normalized_hash"]


def test_parse_sections_no_preamble_when_file_starts_with_heading():
    secs = scan.parse_sections("# Only\nbody\n")
    assert len(secs) == 1
    assert secs[0]["heading"] == "Only"


def test_estimate_tokens_is_quarter_of_length():
    assert scan.estimate_tokens("a" * 400) == 100
    assert scan.estimate_tokens("") == 0


def test_extract_commands_finds_runners():
    text = "Run `npm run build` then `make lint`.\n\n```\ncomposer install\n```\n"
    cmds = scan.extract_commands(text)
    assert "npm run build" in cmds
    assert "make lint" in cmds
    assert "composer install" in cmds


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


def test_extract_commands_deduplicates():
    text = "`make lint` and again `make lint`"
    assert scan.extract_commands(text) == ["make lint"]


def test_extract_paths_finds_backticked_paths():
    text = "See `src/app/main.py` and `docs/guide.md` and `notacommand`."
    paths = scan.extract_paths(text)
    assert "src/app/main.py" in paths
    assert "docs/guide.md" in paths
    assert "notacommand" not in paths


def test_build_digest_shape(tmp_path):
    write(tmp_path, "AGENTS.md", "# Build\nRun `make lint`.\n")
    d = scan.build_digest(str(tmp_path))
    assert d["root"] == str(tmp_path)
    assert len(d["files"]) == 1
    f = d["files"][0]
    assert f["role"] == "agents"
    assert f["est_tokens"] > 0
    assert f["sections"][0]["heading"] == "Build"
    assert "make lint" in f["commands"]
    assert d["total_tokens"] == f["est_tokens"]


def test_cli_emits_valid_json(tmp_path):
    write(tmp_path, "SOUL.md", "# Voice\nBe direct.\n")
    script = os.path.join(os.path.dirname(__file__), "..", "skills", "kontextrevision", "scripts", "scan.py")
    proc = subprocess.run(
        [sys.executable, script, str(tmp_path)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["files"][0]["role"] == "soul"


def test_extract_commands_rejects_prose_targets():
    text = "Please `make sure` everything works and `make commands` are documented."
    assert scan.extract_commands(text) == []


def test_extract_commands_rejects_placeholder_targets():
    assert scan.extract_commands("`npm run ...`") == []


def test_extract_commands_still_accepts_real_targets():
    text = "`make lint` and `npm run build:prod`"
    cmds = scan.extract_commands(text)
    assert "make lint" in cmds
    assert "npm run build:prod" in cmds


def test_parse_sections_ignores_headings_inside_fenced_code():
    text = "# Setup\n\n```bash\n# export API_KEY=sk-live-secret\ncurl x | bash\n```\n\n## Usage\nrun it\n"
    secs = scan.parse_sections(text)
    assert [s["heading"] for s in secs] == ["Setup", "Usage"]
    assert all("API_KEY" not in (s["heading"] or "") for s in secs)


def test_extract_commands_ignores_prose_outside_code_spans():
    assert scan.extract_commands("This change should make sense to reviewers.") == []
    assert scan.extract_commands("We should make progress on this soon.") == []
    assert scan.extract_commands("The pytest suite passed with zero errors.") == []


def test_extract_commands_accepts_bare_npm_subcommands():
    cmds = scan.extract_commands("`npm test` and `yarn build`")
    assert "npm test" in cmds
    assert "yarn build" in cmds


def test_extract_paths_rejects_prose_containing_slashes():
    t = "See `notes: the meeting is at 3/4 past the hour and nobody remembered it`."
    assert scan.extract_paths(t) == []


def test_extract_paths_rejects_technology_names():
    assert scan.extract_paths("Built with `Node.js` and `Vue.js`.") == []


def test_build_digest_survives_a_broken_symlink(tmp_path):
    import os as _os
    write(tmp_path, "AGENTS.md", "# Real\nbody\n")
    _os.symlink(_os.path.join(str(tmp_path), "missing.md"), _os.path.join(str(tmp_path), "CLAUDE.md"))
    d = scan.build_digest(str(tmp_path))
    assert len(d["files"]) == 1


def test_extract_commands_handles_runner_with_no_target():
    assert scan.extract_commands("`npm run`") == []
    assert scan.extract_commands("`make`") == []
    assert scan.extract_commands("`npm`") == []


def test_extract_commands_strips_trailing_comments_in_code_blocks():
    text = "```bash\nnpm run test:e2e            # E2E tests\nmake lint  # linting\n```\n"
    cmds = scan.extract_commands(text)
    assert "npm run test:e2e" in cmds
    assert "make lint" in cmds


def test_discover_harness_finds_definitions(tmp_path):
    write(tmp_path, "skills/alpha/SKILL.md", "---\nname: alpha\ndescription: does alpha\n---\nbody\n")
    write(tmp_path, "agents/beta.md", "---\nname: beta\ndescription: does beta\n---\nbody\n")
    write(tmp_path, "commands/gamma.md", "---\ndescription: does gamma\n---\nbody\n")
    write(tmp_path, "README.md", "not a definition")
    found = scan.discover_harness(str(tmp_path))
    assert sorted(os.path.basename(p) for p in found) == ["SKILL.md", "beta.md", "gamma.md"]


def test_digest_definition_splits_always_on_from_on_demand(tmp_path):
    p = write(tmp_path, "skills/alpha/SKILL.md",
              "---\nname: alpha\ndescription: " + "d" * 400 + "\n---\n" + "b" * 800 + "\n")
    d = scan.digest_definition(p)
    assert d["kind"] == "skill"
    assert d["name"] == "alpha"
    assert d["always_on_tokens"] == 100
    assert d["on_demand_tokens"] > 100


def test_digest_definition_handles_missing_frontmatter(tmp_path):
    p = write(tmp_path, "commands/plain.md", "no frontmatter here at all\n")
    d = scan.digest_definition(p)
    assert d["kind"] == "command"
    assert d["always_on_tokens"] == 0


def test_build_harness_digest_totals_and_duplicates(tmp_path):
    write(tmp_path, "a/skills/dup/SKILL.md", "---\nname: dup\ndescription: " + "x" * 200 + "\n---\nbody\n")
    write(tmp_path, "b/skills/dup/SKILL.md", "---\nname: dup\ndescription: " + "y" * 200 + "\n---\nbody\n")
    write(tmp_path, "a/skills/solo/SKILL.md", "---\nname: solo\ndescription: only one\n---\nbody\n")
    h = scan.build_harness_digest(str(tmp_path))
    assert h["definition_count"] == 3
    assert h["always_on_tokens"] > 0
    assert "skill:dup" in h["duplicates"]
    assert h["duplicates"]["skill:dup"] == 2
    assert "skill:solo" not in h["duplicates"]


def test_discover_harness_keeps_only_newest_cached_plugin_version(tmp_path):
    for v in ["1.0.0", "1.2.0", "0.9.0"]:
        write(tmp_path, "plugins/cache/mkt/thing/{0}/skills/x/SKILL.md".format(v),
              "---\nname: x\ndescription: d\n---\nbody\n")
    found = scan.discover_harness(str(tmp_path))
    assert len(found) == 1
    assert "1.2.0" in found[0]


def test_old_definition_removed_in_new_version_is_not_counted(tmp_path):
    old = write(tmp_path, "plugins/cache/market/thing/1.0.0/skills/old/SKILL.md",
                "---\nname: old\ndescription: old\n---\n")
    new = write(tmp_path, "plugins/cache/market/thing/2.0.0/skills/new/SKILL.md",
                "---\nname: new\ndescription: new\n---\n")
    assert scan.discover_harness(str(tmp_path)) == [new]
    assert old not in scan.discover_harness(str(tmp_path))


def test_discover_harness_keeps_all_versions_of_different_plugins(tmp_path):
    write(tmp_path, "plugins/cache/mkt/alpha/1.0.0/skills/a/SKILL.md", "---\nname: a\ndescription: d\n---\n")
    write(tmp_path, "plugins/cache/mkt/beta/1.0.0/skills/b/SKILL.md", "---\nname: b\ndescription: d\n---\n")
    assert len(scan.discover_harness(str(tmp_path))) == 2


def test_discover_harness_skips_marketplace_catalogs(tmp_path):
    write(tmp_path, "plugins/cache/mkt/thing/1.0.0/skills/x/SKILL.md", "---\nname: x\ndescription: d\n---\n")
    write(tmp_path, "plugins/marketplaces/mkt/thing/skills/x/SKILL.md", "---\nname: x\ndescription: d\n---\n")
    found = scan.discover_harness(str(tmp_path))
    assert len(found) == 1
    assert "marketplaces" not in found[0]


def test_build_digest_includes_harness_by_default(tmp_path):
    write(tmp_path, "AGENTS.md", "# A\nbody\n")
    write(tmp_path, "skills/x/SKILL.md", "---\nname: x\ndescription: " + "d" * 80 + "\n---\nbody\n")
    write(tmp_path, "agents/y.md", "---\nname: y\ndescription: yy\n---\nbody\n")
    d = scan.build_digest(str(tmp_path))
    assert len(d["files"]) == 1
    assert len(d["definitions"]) == 2
    assert d["instruction_tokens"] > 0
    assert d["description_tokens"] > 0
    assert d["always_on_tokens"] == d["effective_now_tokens"] + d["skill_description_tokens"]
    assert d["on_demand_tokens"] > 0


def test_build_digest_reports_duplicate_definitions(tmp_path):
    write(tmp_path, "a/skills/dup/SKILL.md", "---\nname: dup\ndescription: d\n---\n")
    write(tmp_path, "b/skills/dup/SKILL.md", "---\nname: dup\ndescription: d\n---\n")
    d = scan.build_digest(str(tmp_path))
    assert d["duplicates"].get("skill:dup") == 2


def test_build_digest_works_with_no_definitions(tmp_path):
    write(tmp_path, "AGENTS.md", "# A\nbody\n")
    d = scan.build_digest(str(tmp_path))
    assert d["definitions"] == []
    assert d["description_tokens"] == 0
    assert d["always_on_tokens"] == d["effective_now_tokens"]


def test_classify_definition_requires_conventional_location():
    assert scan.classify_definition("/x/.claude/agents/beta.md") == "agent"
    assert scan.classify_definition("/x/plugins/cache/m/p/1.0.0/agents/beta.md") == "agent"
    assert scan.classify_definition("/repo/docs/agents/overview.md") == "unknown"
    assert scan.classify_definition("/repo/docs/commands/reference.md") == "unknown"


def test_duplicates_keep_skills_and_agents_separate(tmp_path):
    write(tmp_path, "s1/skills/dup/SKILL.md", "---\nname: dup\ndescription: d\n---\n")
    write(tmp_path, "s2/skills/dup/SKILL.md", "---\nname: dup\ndescription: d\n---\n")
    for n in "abc":
        write(tmp_path, "{0}/.claude/agents/dup.md".format(n), "---\nname: dup\ndescription: d\n---\n")
    h = scan.build_harness_digest(str(tmp_path))
    assert h["duplicates"]["skill:dup"] == 2
    assert h["duplicates"]["agent:dup"] == 3


def test_digest_definition_strips_yaml_block_scalar_marker(tmp_path):
    p = write(tmp_path, "skills/a/SKILL.md",
              "---\nname: a\ndescription: >-\n  the real text\n---\nbody\n")
    assert scan.digest_definition(p)["description"] == "the real text"


def test_mirrored_agents_and_claude_counted_once(tmp_path):
    body = "# Guide\n" + ("rule line\n" * 40)
    write(tmp_path, "AGENTS.md", body)
    write(tmp_path, "CLAUDE.md", body)
    d = scan.build_digest(str(tmp_path))
    single = scan.estimate_tokens(body)
    assert d["instruction_tokens"] == single
    assert d["mirrors"] == [["AGENTS.md", "CLAUDE.md"]]


def test_same_body_under_different_headings_is_not_a_mirror(tmp_path):
    body = "same body\n" * 40
    write(tmp_path, "AGENTS.md", "# Python\n" + body)
    write(tmp_path, "CLAUDE.md", "# Rust\n" + body)
    assert scan.build_digest(str(tmp_path))["mirrors"] == []


def test_mirror_hash_ignores_whitespace_differences(tmp_path):
    write(tmp_path, "AGENTS.md", "# Guide\nsame   body\n" * 20)
    write(tmp_path, "CLAUDE.md", "# Guide\n\n  same body  \n\n" * 20)
    assert scan.build_digest(str(tmp_path))["mirrors"] == [["AGENTS.md", "CLAUDE.md"]]


def test_mirror_paths_are_relative_to_scan_root(tmp_path):
    for directory in ["api", "web"]:
        body = "# Guide\n" + "rule line\n" * 40
        write(tmp_path, "{0}/AGENTS.md".format(directory), body)
        write(tmp_path, "{0}/CLAUDE.md".format(directory), body)
    assert scan.build_digest(str(tmp_path))["mirrors"] == [
        ["api/AGENTS.md", "api/CLAUDE.md"],
        ["web/AGENTS.md", "web/CLAUDE.md"],
    ]


def test_different_agents_and_claude_counted_separately(tmp_path):
    write(tmp_path, "AGENTS.md", "# A\n" + ("alpha\n" * 40))
    write(tmp_path, "CLAUDE.md", "# C\n" + ("beta\n" * 40))
    d = scan.build_digest(str(tmp_path))
    assert d["instruction_tokens"] == sum(f["est_tokens"] for f in d["files"])
    assert d["mirrors"] == []


def test_pointer_file_is_not_treated_as_a_mirror(tmp_path):
    write(tmp_path, "AGENTS.md", "# A\n" + ("rule\n" * 40))
    write(tmp_path, "CLAUDE.md", "@AGENTS.md\n")
    d = scan.build_digest(str(tmp_path))
    assert d["mirrors"] == []


def test_scan_accepts_a_single_file_path(tmp_path):
    f = write(tmp_path, "AGENTS.md", "# A\nRun `make lint`.\n")
    assert scan.discover(f) == [os.path.abspath(f)]
    d = scan.build_digest(f)
    assert len(d["files"]) == 1
    assert d["files"][0]["role"] == "agents"


def test_scan_rejects_a_single_file_with_no_role(tmp_path):
    f = write(tmp_path, "README.md", "# nope\n")
    assert scan.discover(f) == []


def test_scan_skips_symlinked_instruction_files(tmp_path):
    real = write(tmp_path, "outside/AGENTS.md", "# Secret\nrun `make deploy`\n")
    tree = os.path.join(str(tmp_path), "tree")
    os.makedirs(tree)
    os.symlink(real, os.path.join(tree, "AGENTS.md"))
    assert scan.discover(tree) == []


def test_frontmatter_description_stops_at_hyphenated_key(tmp_path):
    p = write(tmp_path, "skills/x/SKILL.md",
              "---\nname: x\ndescription: short desc\nallowed-tools: Bash, Read\n---\nbody\n")
    d = scan.digest_definition(p)
    assert d["description"] == "short desc"
    assert "allowed-tools" not in d["description"]


def test_frontmatter_description_stops_at_dotted_and_underscored_keys(tmp_path):
    p = write(tmp_path, "skills/y/SKILL.md",
              "---\ndescription: just this\nmodel_name: opus\n---\nbody\n")
    assert scan.digest_definition(p)["description"] == "just this"


def test_root_instructions_are_effective_and_descendants_are_conditional(tmp_path):
    root = write(tmp_path, "AGENTS.md", "# Root\n" + "root rule\n" * 20)
    child = write(tmp_path, "packages/api/AGENTS.md", "# API\n" + "api rule\n" * 20)
    d = scan.build_digest(str(tmp_path))
    by_path = {f["path"]: f for f in d["files"]}
    assert by_path[root]["scope"] == "project"
    assert by_path[root]["load_condition"] == "effective_now"
    assert by_path[root]["harnesses"] == ["codex", "opencode"]
    assert by_path[child]["scope"] == "subtree"
    assert by_path[child]["scope_path"] == "packages/api"
    assert by_path[child]["load_condition"] == "conditional"
    assert d["effective_now_tokens"] == by_path[root]["est_tokens"]
    assert d["conditionally_loaded_tokens"] == by_path[child]["est_tokens"]


def test_cwd_activates_instruction_files_on_its_path(tmp_path):
    root = write(tmp_path, "AGENTS.md", "# Root\nroot\n")
    package = write(tmp_path, "packages/AGENTS.md", "# Packages\npackages\n")
    api = write(tmp_path, "packages/api/AGENTS.md", "# API\napi\n")
    other = write(tmp_path, "packages/web/AGENTS.md", "# Web\nweb\n")
    cwd = os.path.join(str(tmp_path), "packages", "api", "src")
    os.makedirs(cwd)
    d = scan.build_digest(str(tmp_path), cwd=cwd)
    by_path = {f["path"]: f for f in d["files"]}
    assert by_path[root]["load_condition"] == "effective_now"
    assert by_path[package]["load_condition"] == "effective_now"
    assert by_path[api]["load_condition"] == "effective_now"
    assert by_path[other]["load_condition"] == "conditional"
    assert d["scope_graph"][2]["parents"]["codex"] == "packages/AGENTS.md"


def test_instruction_roles_report_harness_coverage(tmp_path):
    write(tmp_path, "SOUL.md", "# Voice\nDirect.\n")
    write(tmp_path, "AGENTS.md", "# Project\nRules.\n")
    write(tmp_path, "CLAUDE.md", "# Claude\nRules.\n")
    write(tmp_path, ".claude/rules/web.md", "# Web\nRules.\n")
    d = scan.build_digest(str(tmp_path))
    coverage = {f["role"]: f["harnesses"] for f in d["files"]}
    assert coverage == {
        "agents": ["codex", "opencode"],
        "claude": ["claude-code"],
        "rules": ["claude-code"],
        "soul": ["nous"],
    }


def test_digest_reports_tokens_per_harness(tmp_path):
    agents = "# Agents\n" + "agent rule\n" * 20
    claude = "# Claude\n" + "claude rule\n" * 30
    child = "# Child\n" + "child rule\n" * 10
    write(tmp_path, "AGENTS.md", agents)
    write(tmp_path, "CLAUDE.md", claude)
    write(tmp_path, "sub/AGENTS.md", child)
    d = scan.build_digest(str(tmp_path))
    assert d["harness_tokens"] == {
        "claude-code": {
            "effective_now_tokens": scan.estimate_tokens(claude),
            "conditionally_loaded_tokens": 0,
        },
        "codex": {
            "effective_now_tokens": scan.estimate_tokens(agents),
            "conditionally_loaded_tokens": scan.estimate_tokens(child),
        },
        "opencode": {
            "effective_now_tokens": scan.estimate_tokens(agents),
            "conditionally_loaded_tokens": scan.estimate_tokens(child),
        },
    }


def test_mirror_tokens_are_counted_once_in_scope_tiers(tmp_path):
    body = "# Shared\n" + "same rule\n" * 20
    write(tmp_path, "AGENTS.md", body)
    write(tmp_path, "CLAUDE.md", body)
    write(tmp_path, "sub/AGENTS.md", body)
    write(tmp_path, "sub/CLAUDE.md", body)
    d = scan.build_digest(str(tmp_path))
    tokens = scan.estimate_tokens(body)
    assert d["effective_now_tokens"] == tokens
    assert d["conditionally_loaded_tokens"] == tokens


def test_build_digest_rejects_cwd_outside_scan_root(tmp_path):
    root = os.path.join(str(tmp_path), "repo")
    outside = os.path.join(str(tmp_path), "outside")
    os.makedirs(root)
    os.makedirs(outside)
    write(root, "AGENTS.md", "# Rules\n")
    with pytest.raises(ValueError, match="inside the scan root"):
        scan.build_digest(root, cwd=outside)


def test_cli_cwd_selects_effective_scope(tmp_path):
    write(tmp_path, "AGENTS.md", "# Root\nroot\n")
    write(tmp_path, "sub/AGENTS.md", "# Sub\nsub\n")
    script = os.path.join(os.path.dirname(__file__), "..", "skills", "kontextrevision", "scripts", "scan.py")
    proc = subprocess.run(
        [sys.executable, script, str(tmp_path), "--cwd", os.path.join(str(tmp_path), "sub")],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert all(f["load_condition"] == "effective_now" for f in payload["files"])
