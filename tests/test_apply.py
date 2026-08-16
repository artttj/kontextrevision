import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "kontextrevision", "scripts"))

import apply
from conftest import write


def git_init(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t.t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)


def git_commit_all(tmp_path):
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "x"], check=True)


def test_write_atomic_creates_backup_with_original(tmp_path):
    target = write(tmp_path, "AGENTS.md", "original\n")
    bak = apply.write_atomic(target, "replaced\n")
    with open(target, encoding="utf-8") as fh:
        assert fh.read() == "replaced\n"
    with open(bak, encoding="utf-8") as fh:
        assert fh.read() == "original\n"
    assert bak == target + ".bak"


def test_write_atomic_leaves_no_temp_files(tmp_path):
    target = write(tmp_path, "AGENTS.md", "original\n")
    apply.write_atomic(target, "replaced\n")
    assert [n for n in os.listdir(str(tmp_path)) if ".tmp." in n] == []


def test_extract_keep_blocks_returns_protected_content():
    text = "a\n<!-- kontextrevision:keep -->\nPROTECTED\n<!-- /kontextrevision:keep -->\nb\n"
    assert apply.extract_keep_blocks(text) == ["PROTECTED"]


def test_extract_keep_blocks_handles_multiple():
    text = ("<!-- kontextrevision:keep -->\nONE\n<!-- /kontextrevision:keep -->\n"
            "middle\n"
            "<!-- kontextrevision:keep -->\nTWO\n<!-- /kontextrevision:keep -->\n")
    assert apply.extract_keep_blocks(text) == ["ONE", "TWO"]


def test_missing_keep_blocks_flags_dropped_content():
    original = "<!-- kontextrevision:keep -->\nKEEPME\n<!-- /kontextrevision:keep -->\n"
    assert apply.missing_keep_blocks(original, "gone\n") == ["KEEPME"]
    assert apply.missing_keep_blocks(original, original) == []


def test_missing_keep_blocks_rejects_bare_quotation_of_protected_text():
    original = ("<!-- kontextrevision:keep -->\nDo not deploy on Fridays.\n"
                "<!-- /kontextrevision:keep -->\n")
    quoted = 'History: a rule used to say "Do not deploy on Fridays." We dropped it.\n'
    assert apply.missing_keep_blocks(original, quoted) == ["Do not deploy on Fridays."]


def test_missing_keep_blocks_flags_reflowed_protected_content():
    original = "<!-- kontextrevision:keep -->\nkeep   this  line\n<!-- /kontextrevision:keep -->\n"
    reflowed = "<!-- kontextrevision:keep -->\nkeep this line\n<!-- /kontextrevision:keep -->\n"
    assert apply.missing_keep_blocks(original, reflowed) != []


def test_apply_refuses_when_keep_block_dropped(tmp_path):
    target = write(tmp_path, "AGENTS.md",
                   "<!-- kontextrevision:keep -->\nKEEPME\n<!-- /kontextrevision:keep -->\n")
    res = apply.apply_file(target, "nothing here\n")
    assert res["status"] == "refused"
    assert "keep" in res["reason"]
    with open(target, encoding="utf-8") as fh:
        assert "KEEPME" in fh.read()


def test_apply_refuses_on_growth(tmp_path):
    target = write(tmp_path, "AGENTS.md", "short\n")
    res = apply.apply_file(target, "short\n" + "x" * 500)
    assert res["status"] == "refused"
    assert "grew" in res["reason"]


def test_apply_allows_growth_when_flagged(tmp_path):
    target = write(tmp_path, "AGENTS.md", "short\n")
    res = apply.apply_file(target, "short\n" + "x" * 500, allow_growth=True)
    assert res["status"] == "written"


def test_apply_allows_small_growth_within_limit(tmp_path):
    target = write(tmp_path, "AGENTS.md", "x" * 1000)
    res = apply.apply_file(target, "x" * 1050)
    assert res["status"] == "written"


def test_apply_refuses_dirty_file(tmp_path):
    git_init(tmp_path)
    target = write(tmp_path, "AGENTS.md", "committed\n")
    git_commit_all(tmp_path)
    with open(target, "a", encoding="utf-8") as fh:
        fh.write("uncommitted edit\n")
    res = apply.apply_file(target, "rewritten\n")
    assert res["status"] == "refused"
    assert "uncommitted" in res["reason"]


def test_apply_force_overrides_dirty_guard(tmp_path):
    git_init(tmp_path)
    target = write(tmp_path, "AGENTS.md", "committed content here\n")
    git_commit_all(tmp_path)
    with open(target, "a", encoding="utf-8") as fh:
        fh.write("uncommitted\n")
    res = apply.apply_file(target, "committed content\n", force=True)
    assert res["status"] == "written"


def test_apply_works_outside_a_git_repo(tmp_path):
    target = write(tmp_path, "AGENTS.md", "no repo here at all\n")
    res = apply.apply_file(target, "shorter\n")
    assert res["status"] == "written"


def test_apply_writes_clean_file_and_reports_delta(tmp_path):
    git_init(tmp_path)
    target = write(tmp_path, "AGENTS.md", "x" * 400 + "\n")
    git_commit_all(tmp_path)
    res = apply.apply_file(target, "x" * 200 + "\n")
    assert res["status"] == "written"
    assert res["tokens_before"] == 100
    assert res["tokens_after"] == 50
    assert res["delta_pct"] == -50.0


def test_apply_dry_run_does_not_write(tmp_path):
    target = write(tmp_path, "AGENTS.md", "original\n")
    res = apply.apply_file(target, "changed\n", dry_run=True)
    assert res["status"] == "dry_run"
    assert res["backup"] is None
    with open(target, encoding="utf-8") as fh:
        assert fh.read() == "original\n"


def test_cli_reads_content_from_stdin(tmp_path):
    target = write(tmp_path, "AGENTS.md", "original content here\n")
    script = os.path.join(os.path.dirname(__file__), "..", "skills", "kontextrevision", "scripts", "apply.py")
    proc = subprocess.run([sys.executable, script, target],
                          input="short\n", capture_output=True, text=True)
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["status"] == "written"


def test_cli_exits_nonzero_on_refusal(tmp_path):
    target = write(tmp_path, "AGENTS.md", "tiny\n")
    script = os.path.join(os.path.dirname(__file__), "..", "skills", "kontextrevision", "scripts", "apply.py")
    proc = subprocess.run([sys.executable, script, target],
                          input="tiny\n" + "x" * 500, capture_output=True, text=True)
    assert proc.returncode == 1
    assert json.loads(proc.stdout)["status"] == "refused"


def test_apply_refuses_empty_content(tmp_path):
    target = write(tmp_path, "AGENTS.md", "# Important\nDo not lose this.\n" * 20)
    res = apply.apply_file(target, "")
    assert res["status"] == "refused"
    assert "empty" in res["reason"]
    with open(target, encoding="utf-8") as fh:
        assert "Do not lose this." in fh.read()


def test_apply_refuses_catastrophic_shrink(tmp_path):
    target = write(tmp_path, "AGENTS.md", "x" * 1000)
    res = apply.apply_file(target, "x" * 50)
    assert res["status"] == "refused"
    assert "shrank" in res["reason"]


def test_apply_allows_aggressive_but_plausible_shrink(tmp_path):
    target = write(tmp_path, "AGENTS.md", "x" * 1000)
    assert apply.apply_file(target, "x" * 300)["status"] == "written"


def test_apply_refuses_unpaired_keep_marker(tmp_path):
    target = write(tmp_path, "AGENTS.md",
                   "<!-- kontextrevision:keep -->\nDO NOT LOSE THIS\nmore text here to pad\n")
    res = apply.apply_file(target, "different content that is long enough to pass\n")
    assert res["status"] == "refused"
    assert "closing" in res["reason"]
    with open(target, encoding="utf-8") as fh:
        assert "DO NOT LOSE THIS" in fh.read()


def test_apply_refuses_symlink(tmp_path):
    real = write(tmp_path, "real/AGENTS.md", "real content here\n")
    link = os.path.join(str(tmp_path), "AGENTS.md")
    os.symlink(real, link)
    res = apply.apply_file(link, "replaced\n")
    assert res["status"] == "refused"
    assert "symlink" in res["reason"]
    assert os.path.islink(link)


def test_apply_refuses_non_utf8_file(tmp_path):
    target = os.path.join(str(tmp_path), "AGENTS.md")
    with open(target, "wb") as fh:
        fh.write(b"heading\n\xff\xfe invalid\n")
    res = apply.apply_file(target, "new content\n")
    assert res["status"] == "refused"
    assert "utf-8" in res["reason"]


def test_backup_never_overwrites_the_true_original(tmp_path):
    target = write(tmp_path, "AGENTS.md", "VERY FIRST ORIGINAL" + "x" * 100)
    apply.write_atomic(target, "second version" + "y" * 100)
    apply.write_atomic(target, "third version" + "z" * 100)
    with open(target + ".bak", encoding="utf-8") as fh:
        assert "VERY FIRST ORIGINAL" in fh.read()


def test_force_does_not_bypass_keep_guard(tmp_path):
    git_init(tmp_path)
    target = write(tmp_path, "AGENTS.md",
                   "<!-- kontextrevision:keep -->\nSECRET\n<!-- /kontextrevision:keep -->\npadding\n")
    git_commit_all(tmp_path)
    res = apply.apply_file(target, "gone but long enough to pass the shrink floor\n", force=True)
    assert res["status"] == "refused"
    assert "keep" in res["reason"]


def test_growth_boundary_exactly_at_limit_allowed(tmp_path):
    target = write(tmp_path, "AGENTS.md", "x" * 100)
    assert apply.apply_file(target, "x" * 110)["status"] == "written"


def test_growth_boundary_just_over_limit_refused(tmp_path):
    target = write(tmp_path, "AGENTS.md", "x" * 100)
    assert apply.apply_file(target, "x" * 111)["status"] == "refused"


def test_apply_allows_untracked_new_file_in_git_repo(tmp_path):
    git_init(tmp_path)
    write(tmp_path, "seed.txt", "x")
    git_commit_all(tmp_path)
    target = write(tmp_path, "AGENTS.md", "brand new file never committed, long enough\n")
    res = apply.apply_file(target, "brand new file never committed\n")
    assert res["status"] == "written"


def test_apply_still_refuses_tracked_file_with_edits(tmp_path):
    git_init(tmp_path)
    target = write(tmp_path, "AGENTS.md", "committed content here\n")
    git_commit_all(tmp_path)
    with open(target, "a", encoding="utf-8") as fh:
        fh.write("uncommitted edit\n")
    assert apply.apply_file(target, "committed content\n")["status"] == "refused"


def test_keep_block_is_byte_preserving_for_indentation(tmp_path):
    protected = "<!-- kontextrevision:keep -->\n```\ndef f():\n    return 1\n```\n<!-- /kontextrevision:keep -->\n"
    mangled = "<!-- kontextrevision:keep -->\n```\ndef f():\nreturn 1\n```\n<!-- /kontextrevision:keep -->\n"
    assert apply.missing_keep_blocks(protected, mangled) != []


def test_keep_block_tolerates_only_line_ending_changes():
    a = "<!-- kontextrevision:keep -->\nline one\nline two\n<!-- /kontextrevision:keep -->\n"
    b = a.replace("\n", "\r\n")
    assert apply.missing_keep_blocks(a, b) == []


def test_duplicate_keep_blocks_compared_as_multiset():
    two = ("<!-- kontextrevision:keep -->\nSAME\n<!-- /kontextrevision:keep -->\n"
           "<!-- kontextrevision:keep -->\nSAME\n<!-- /kontextrevision:keep -->\n")
    one = "<!-- kontextrevision:keep -->\nSAME\n<!-- /kontextrevision:keep -->\n"
    assert apply.missing_keep_blocks(two, one) == ["SAME"]


def test_malformed_marker_order_is_detected():
    bad = "<!-- /kontextrevision:keep -->\ntext\n<!-- kontextrevision:keep -->\nUNPROTECTED\n"
    assert apply.unpaired_keep_markers(bad) > 0


def test_nested_open_markers_detected():
    bad = ("<!-- kontextrevision:keep -->\na\n<!-- kontextrevision:keep -->\nb\n"
           "<!-- /kontextrevision:keep -->\n")
    assert apply.unpaired_keep_markers(bad) > 0


def test_apply_refuses_rewrite_that_invents_a_command(tmp_path):
    target = write(tmp_path, "AGENTS.md", "# Rules\n" + "Be careful with the whole database here.\n" * 12)
    invented = "# Rules\n" + "Never migrate without `make db-dry`.\n" * 12
    res = apply.apply_file(target, invented)
    assert res["status"] == "refused"
    assert "invent" in res["reason"]


@pytest.mark.parametrize("command", [
    "pytest tests/",
    "cargo test",
    "git push --force",
    "python manage.py migrate",
    "docker compose down",
])
def test_apply_refuses_common_invented_commands(tmp_path, command):
    original = "# Rules\n" + "Be careful with deployment and repository operations.\n" * 12
    rewritten = "# Rules\n" + "Run `{0}` before release.\n".format(command) * 12
    res = apply.apply_file(write(tmp_path, "AGENTS.md", original), rewritten)
    assert res["status"] == "refused"
    assert "invent" in res["reason"]


def test_apply_refuses_invented_command_in_fence(tmp_path):
    original = "# Rules\n" + "Follow the release policy carefully.\n" * 12
    rewritten = "# Rules\n```bash\nmake deploy\n```\n" + "Follow the policy.\n" * 12
    res = apply.apply_file(write(tmp_path, "AGENTS.md", original), rewritten)
    assert res["status"] == "refused"
    assert "invent" in res["reason"]


def test_apply_allows_invented_command_when_opted_in(tmp_path):
    target = write(tmp_path, "AGENTS.md", "# Rules\n" + "Be careful with the whole database here.\n" * 12)
    invented = "# Rules\n" + "Never migrate without `make db-dry`.\n" * 12
    assert apply.apply_file(target, invented, allow_new_commands=True)["status"] == "written"


def test_apply_allows_rewrite_reusing_an_existing_command(tmp_path):
    target = write(tmp_path, "AGENTS.md", "# Rules\n" + "Run `make lint` sometimes, maybe, ok.\n" * 12)
    tightened = "# Rules\n" + "Run `make lint` before each commit.\n" * 12
    assert apply.apply_file(target, tightened)["status"] == "written"


@pytest.mark.parametrize("command", [
    "pytest tests/",
    "cargo test",
    "git push --force",
    "python manage.py migrate",
    "docker compose down",
])
def test_apply_allows_reusing_common_command(tmp_path, command):
    original = "# Rules\n" + "Sometimes run `{0}` before release.\n".format(command) * 12
    rewritten = "# Rules\n" + "Run `{0}` before release.\n".format(command) * 12
    target = write(tmp_path, "AGENTS.md", original)
    assert apply.apply_file(target, rewritten)["status"] == "written"


def test_rollback_restores_from_backup_despite_dirty_guard(tmp_path):
    git_init(tmp_path)
    target = write(tmp_path, "AGENTS.md", "# A\n" + "rule line\n" * 40)
    git_commit_all(tmp_path)
    original = open(target, encoding="utf-8").read()
    first = apply.apply_file(target, "# A\n" + "rule line\n" * 35)
    assert first["status"] == "written"
    res = apply.rollback(target)
    assert res["status"] == "rolled_back"
    assert open(target, encoding="utf-8").read() == original
    assert not os.path.exists(first["backup"])


def test_rollback_without_a_backup_reports_cleanly(tmp_path):
    target = write(tmp_path, "AGENTS.md", "untouched\n")
    assert apply.rollback(target)["status"] == "refused"
