import json
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")
SKILL_DIR = os.path.join(ROOT, "skills", "kontextrevision")


def test_plugin_manifest_is_valid_json_with_required_keys():
    with open(os.path.join(ROOT, ".claude-plugin", "plugin.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["name"] == "kontextrevision"
    assert data["version"]
    assert data["description"]
    assert data["author"] == {
        "name": "Artem Iagovdik",
        "email": "artyom.yagovdik@gmail.com",
        "url": "https://github.com/artttj",
    }


def test_plugin_versions_match_release():
    """Compared against each other, not a literal, so a bump touches two files."""
    versions = []
    for directory in [".claude-plugin", ".codex-plugin"]:
        with open(os.path.join(ROOT, directory, "plugin.json"), encoding="utf-8") as fh:
            versions.append(json.load(fh)["version"])
    assert len(set(versions)) == 1
    assert re.match(r"^\d+\.\d+\.\d+$", versions[0])


def test_plugin_authors_share_contact_email():
    for directory in [".claude-plugin", ".codex-plugin"]:
        with open(os.path.join(ROOT, directory, "plugin.json"), encoding="utf-8") as fh:
            assert json.load(fh)["author"]["email"] == "artyom.yagovdik@gmail.com"


def test_codex_plugin_uses_shared_skill_tree():
    with open(os.path.join(ROOT, ".codex-plugin", "plugin.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["skills"] == "./skills/"
    assert os.path.exists(os.path.join(ROOT, data["skills"], "kontextrevision", "SKILL.md"))


def test_codex_marketplace_points_to_repository_plugin():
    path = os.path.join(ROOT, ".agents", "plugins", "marketplace.json")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["name"] == "kontextrevision"
    assert data["interface"]["displayName"] == "Kontextrevision"
    assert data["plugins"] == [{
        "name": "kontextrevision",
        "source": {"source": "local", "path": "./"},
        "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        "category": "Developer Tools",
    }]


def test_marketplace_manifest_lists_the_plugin():
    with open(os.path.join(ROOT, ".claude-plugin", "marketplace.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["name"] == "kontextrevision"
    assert data["description"]
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
    assert "/plugin marketplace add artttj/kontextrevision" in text
    assert "/plugin install kontextrevision@kontextrevision" in text
    assert "/kontextrevision:kontextrevision" in text
    assert "### Codex" in text
    assert "codex plugin marketplace add artttj/kontextrevision" in text
    assert "### OpenCode" in text
    assert "~/.config/opencode/skills/kontextrevision" in text
    assert "/kontextrevision" in text
