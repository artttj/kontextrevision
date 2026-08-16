import json
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")
SKILL_DIR = os.path.join(ROOT, "skills", "kontextrevision")


def test_plugin_manifest_is_valid_json_with_required_keys():
    with open(os.path.join(ROOT, ".claude-plugin", "plugin.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["name"] == "kontextrevision"
    assert data["version"]
    assert data["description"]


def test_plugin_versions_match_release():
    for directory in [".claude-plugin", ".codex-plugin"]:
        with open(os.path.join(ROOT, directory, "plugin.json"), encoding="utf-8") as fh:
            assert json.load(fh)["version"] == "1.0.0"


def test_codex_plugin_uses_shared_skill_tree():
    with open(os.path.join(ROOT, ".codex-plugin", "plugin.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["skills"] == "./skills/"
    assert os.path.exists(os.path.join(ROOT, data["skills"], "kontextrevision", "SKILL.md"))


def test_marketplace_manifest_lists_the_plugin():
    with open(os.path.join(ROOT, ".claude-plugin", "marketplace.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["name"] == "kontextrevision"
    assert "kontextrevision" in [p["name"] for p in data["plugins"]]


def test_skill_has_frontmatter_with_name_and_description():
    with open(os.path.join(SKILL_DIR, "SKILL.md"), encoding="utf-8") as fh:
        text = fh.read()
    assert text.startswith("---\n")
    head = text.split("---", 2)[1]
    assert "name: kontextrevision" in head
    assert "description:" in head


def test_skill_references_all_resolve():
    with open(os.path.join(SKILL_DIR, "SKILL.md"), encoding="utf-8") as fh:
        text = fh.read()
    for ref in ["references/classification.md", "references/routing.md", "references/research.md"]:
        assert ref in text, "SKILL.md does not link " + ref
        assert os.path.exists(os.path.join(SKILL_DIR, ref)), "missing file " + ref


def test_skill_scripts_exist_at_documented_paths():
    for script in ["scripts/scan.py", "scripts/apply.py"]:
        assert os.path.exists(os.path.join(SKILL_DIR, script))


def test_keep_marker_in_skill_matches_the_writer():
    import sys
    sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))
    import apply
    with open(os.path.join(SKILL_DIR, "SKILL.md"), encoding="utf-8") as fh:
        text = fh.read()
    sample = "<!-- kontextrevision:keep -->\nX\n<!-- /kontextrevision:keep -->"
    assert "kontextrevision:keep" in text
    assert apply.extract_keep_blocks(sample) == ["X"]


def test_ci_runs_documented_python_39_suite():
    workflow = os.path.join(ROOT, ".github", "workflows", "tests.yml")
    with open(workflow, encoding="utf-8") as fh:
        text = fh.read()
    assert 'python-version: "3.9"' in text
    assert "python3 -m pytest tests/ -q" in text


def test_readme_documents_supported_tool_installation():
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
        text = fh.read()
    assert "actions/workflows/tests.yml/badge.svg" in text
    assert "### Claude Code" in text
    assert "### Codex" in text
    assert "codex plugin marketplace add artttj/kontextrevision" in text
    assert "### OpenCode" in text
    assert "~/.config/opencode/skills/kontextrevision" in text
    assert "/kontextrevision" in text
