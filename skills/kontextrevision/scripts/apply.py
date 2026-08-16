#!/usr/bin/env python3
"""The only writer. Enforces every safety guard before touching disk."""

import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from typing import Dict, List, Optional

KEEP_OPEN_RE = re.compile(r"<!--\s*kontextrevision:keep\s*-->")
KEEP_CLOSE_RE = re.compile(r"<!--\s*/kontextrevision:keep\s*-->")
KEEP_RE = re.compile(
    r"<!--\s*kontextrevision:keep\s*-->(.*?)<!--\s*/kontextrevision:keep\s*-->",
    re.DOTALL,
)

GROWTH_LIMIT = 1.10
SHRINK_FLOOR = 0.20


def estimate_tokens(text: str) -> int:
    """Rough token count. The writer imports nothing, so this is duplicated."""
    return len(text) // 4


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_protected(text: str) -> str:
    """Line endings only. Protected content is compared byte for byte otherwise.

    Collapsing whitespace would let a rewrite reindent a Python block, a YAML
    fragment or a Make recipe and still pass the guard.
    """
    return text.replace("\r\n", "\n").replace("\r", "\n").strip("\n")


def extract_keep_blocks(text: str) -> List[str]:
    """Return the content of every paired keep marker, byte-preserving."""
    return [normalize_protected(m.group(1)) for m in KEEP_RE.finditer(text)]


def unpaired_keep_markers(text: str) -> int:
    """Count keep markers that are not correctly paired in order.

    Counting opens against closes is not enough: a stray close followed by a
    stray open nets to zero while leaving a block unprotected. This walks the
    markers in document order instead.
    """
    events = []
    for m in KEEP_OPEN_RE.finditer(text):
        events.append((m.start(), 1))
    for m in KEEP_CLOSE_RE.finditer(text):
        events.append((m.start(), -1))
    events.sort()
    depth, broken = 0, 0
    for _, delta in events:
        if delta == 1:
            if depth:
                broken += 1
            depth += 1
        else:
            if depth == 0:
                broken += 1
            else:
                depth -= 1
    return broken + depth


def missing_keep_blocks(original: str, new: str) -> List[str]:
    """Keep blocks from the original that are not still keep blocks in new.

    Compares marker-wrapped blocks as a multiset, so dropping one of two
    identical protected blocks is caught.
    """
    surviving = list(extract_keep_blocks(new))
    missing = []
    for block in extract_keep_blocks(original):
        if block in surviving:
            surviving.remove(block)
        else:
            missing.append(block)
    return missing


FENCE_RE = re.compile(r"^\s*(```|~~~)")
CODE_SPAN_RE = re.compile(r"`([^`\n]{1,120})`")
COMMAND_RE = re.compile(
    r"^((?:npm|yarn|pnpm)\s+(?:run\s+)?[\w:.-]+"
    r"(?:\s+[-\w@:./=]+)*"
    r"|(?:make|composer|pytest|cargo|git|python|python3)\s+[-\w@:./=]+"
    r"(?:\s+[-\w@:./=]+)*"
    r"|docker\s+(?:compose\s+)?[-\w@:./=]+(?:\s+[-\w@:./=]+)*)$"
)

TARGET_STOPWORDS = {
    "commands", "command", "sure", "it", "the", "a", "an", "this", "that",
    "use", "your", "any", "all", "them", "these", "those", "some", "more",
    "note", "changes",
}


def _is_real_target(target: str) -> bool:
    """Reject prose and placeholders that look like command targets."""
    if not target or target.lower() in TARGET_STOPWORDS:
        return False
    if set(target) <= set(".-_:"):
        return False
    return True


def code_spans(text: str) -> List[str]:
    """Inline code spans plus fenced-block lines."""
    spans = [m.group(1).strip() for m in CODE_SPAN_RE.finditer(text)]
    in_fence = False
    for line in text.split("\n"):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence and line.strip():
            spans.append(re.sub(r"\s+#.*$", "", line).strip())
    return spans


def command_refs(text: str) -> List[str]:
    """Recognized commands named in inline code spans or fenced blocks."""
    out = []
    for raw in code_spans(text):
        span = re.sub(r"\s+", " ", raw).strip()
        match = COMMAND_RE.match(span)
        if not match:
            continue
        command = match.group(1).strip()
        parts = command.split()
        if len(parts) < 2 or (parts[1] == "run" and len(parts) < 3):
            continue
        target = parts[2] if parts[1] == "run" else parts[1]
        if _is_real_target(target) and command not in out:
            out.append(command)
    return out


def invented_commands(original: str, new: str) -> List[str]:
    """Commands the rewrite names that the original never mentioned.

    Turning "be careful with the database" into "run `make db-migrate-dry`"
    invents a procedure. It may not exist, and it is not what the author wrote.
    """
    before = set(command_refs(original))
    return [c for c in command_refs(new) if c not in before]


def in_git_repo(directory: str) -> bool:
    try:
        proc = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"],
                              cwd=directory, capture_output=True, text=True)
    except OSError:
        return False
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def is_git_dirty(path: str) -> Optional[bool]:
    """True if the file has uncommitted edits, False if clean, None if git has no version of it.

    An untracked file has no committed version to protect, and the backup covers
    it, so it is not treated as dirty. A tracked file with edits is.

    Returns True on any git failure inside a repository. A guard that cannot
    read the repository state must not conclude the file is safe to overwrite.
    """
    directory = os.path.dirname(os.path.realpath(path)) or "."
    if not in_git_repo(directory):
        return None
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain", "--", os.path.basename(os.path.realpath(path))],
            cwd=directory, capture_output=True, text=True)
    except OSError:
        return True
    if proc.returncode != 0:
        return True
    status = proc.stdout.strip()
    if not status:
        return False
    if status.startswith("??"):
        return None
    return True


def backup_path(path: str) -> str:
    """First free backup name, so the true original is never overwritten."""
    candidate = path + ".bak"
    if not os.path.exists(candidate):
        return candidate
    n = 1
    while os.path.exists("{0}.bak.{1}".format(path, n)):
        n += 1
    return "{0}.bak.{1}".format(path, n)


def write_atomic(path: str, content: str) -> str:
    """Back up the original, then replace it atomically. Returns backup path."""
    mode = stat.S_IMODE(os.stat(path).st_mode)
    backup = backup_path(path)
    shutil.copy2(path, backup)
    tmp = "{0}.tmp.{1}".format(path, os.getpid())
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(content)
    os.chmod(tmp, mode)
    os.replace(tmp, path)
    with open(backup + ".txn", "w", encoding="utf-8") as fh:
        json.dump({"post_write_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()}, fh)
        fh.write("\n")
    return backup


def _result(status, reason, before, after, backup=None):
    delta = 0.0 if before == 0 else round((after - before) / float(before) * 100, 1)
    return {
        "status": status,
        "reason": reason,
        "tokens_before": before,
        "tokens_after": after,
        "delta_pct": delta,
        "backup": backup,
    }


def rollback(path):
    """Restore the newest backup only when the written revision is unchanged."""
    base = path + ".bak"
    existing = []
    for candidate in glob.glob(base + "*"):
        if candidate == base:
            existing.append((0, candidate))
            continue
        match = re.match(r"^{0}\.(\d+)$".format(re.escape(base)), candidate)
        if match:
            existing.append((int(match.group(1)), candidate))
    if not existing:
        return _result("refused", "no backup found for {0}".format(path), 0, 0)
    backup = max(existing, key=lambda item: item[0])[1]
    transaction = backup + ".txn"
    try:
        with open(transaction, "r", encoding="utf-8") as fh:
            expected = json.load(fh)["post_write_sha256"]
    except (IOError, OSError, KeyError, TypeError, ValueError):
        return _result("refused", "backup has no valid transaction metadata", 0, 0)
    try:
        with open(path, "rb") as fh:
            current = hashlib.sha256(fh.read()).hexdigest()
    except (IOError, OSError):
        return _result("refused", "cannot read current file before rollback", 0, 0)
    if current != expected:
        return _result("refused", "file changed since the guarded write; rollback would lose edits",
                       0, 0)
    with open(backup, "rb") as fh:
        content = fh.read()
    mode = stat.S_IMODE(os.stat(backup).st_mode)
    tmp = "{0}.tmp.{1}".format(path, os.getpid())
    with open(tmp, "wb") as fh:
        fh.write(content)
    os.chmod(tmp, mode)
    os.replace(tmp, path)
    os.remove(backup)
    os.remove(transaction)
    return _result("rolled_back", None, 0, estimate_tokens(content.decode("utf-8")))


def apply_file(path, new_content, force=False, allow_growth=False, dry_run=False,
               allow_new_commands=False):
    """Run every guard, then write. Returns a JSON-serializable result."""
    if os.path.islink(path):
        return _result("refused",
                       "refusing to write through a symlink; pass the real path",
                       0, estimate_tokens(new_content))

    try:
        with open(path, "r", encoding="utf-8") as fh:
            original = fh.read()
    except UnicodeDecodeError:
        return _result("refused", "file is not valid utf-8", 0,
                       estimate_tokens(new_content))
    except (IOError, OSError) as exc:
        return _result("refused", "cannot read file: {0}".format(exc), 0,
                       estimate_tokens(new_content))

    before = estimate_tokens(original)
    after = estimate_tokens(new_content)

    if not force:
        dirty = is_git_dirty(path)
        if dirty is True:
            return _result("refused",
                           "file has uncommitted changes; commit them or pass --force",
                           before, after)

    if not new_content.strip():
        return _result("refused",
                       "refusing to write empty content over a file with {0} tokens".format(before),
                       before, after)

    unpaired = unpaired_keep_markers(original)
    if unpaired > 0:
        return _result("refused",
                       "{0} keep marker(s) have no closing tag; fix the markers "
                       "before revising".format(unpaired),
                       before, after)

    proposed_unpaired = unpaired_keep_markers(new_content)
    if proposed_unpaired > 0:
        return _result("refused",
                       "{0} keep marker(s) in the proposed rewrite are unpaired; "
                       "fix the markers before revising".format(proposed_unpaired),
                       before, after)

    dropped = missing_keep_blocks(original, new_content)
    if dropped:
        return _result("refused",
                       "keep block dropped: {0!r}".format(dropped[0][:60]),
                       before, after)

    if len(original) and len(new_content) < len(original) * SHRINK_FLOOR:
        lost = (1 - len(new_content) / float(len(original))) * 100
        return _result("refused",
                       "content shrank {0:.0f}%, past the {1:.0f}% floor; this "
                       "looks like a truncated response".format(
                           lost, (1 - SHRINK_FLOOR) * 100),
                       before, after)

    if not allow_new_commands:
        invented = invented_commands(original, new_content)
        if invented:
            return _result("refused",
                           "rewrite would invent commands the original never named: "
                           "{0!r}; propose this to the user instead, or pass "
                           "--allow-new-commands".format(invented[:3]),
                           before, after)

    if not allow_growth and len(new_content) > len(original) * GROWTH_LIMIT:
        grew = (len(new_content) / float(max(1, len(original))) - 1) * 100
        return _result("refused",
                       "content grew {0:.0f}% over original; pass --allow-growth "
                       "for routing moves".format(grew),
                       before, after)

    if dry_run:
        return _result("dry_run", None, before, after)

    try:
        with open(path, "r", encoding="utf-8") as fh:
            if fh.read() != original:
                return _result("refused",
                               "file changed on disk while guards were running",
                               before, after)
    except (IOError, OSError, UnicodeDecodeError):
        return _result("refused", "file became unreadable before write", before, after)

    return _result("written", None, before, after, write_atomic(path, new_content))


def main(argv):
    parser = argparse.ArgumentParser(
        description="Apply revised content to an instruction file. Reads new content from stdin.")
    parser.add_argument("path", help="File to rewrite")
    parser.add_argument("--force", action="store_true",
                        help="Write even if the file has uncommitted changes")
    parser.add_argument("--allow-growth", action="store_true",
                        help="Permit growth past 10%%, for routing moves into this file")
    parser.add_argument("--dry-run", action="store_true", help="Report without writing")
    parser.add_argument("--allow-new-commands", action="store_true",
                        help="Permit a rewrite to name commands the original did not")
    parser.add_argument("--rollback", action="store_true",
                        help="Restore the most recent backup and exit")
    args = parser.parse_args(argv[1:])

    if args.rollback:
        result = rollback(args.path)
        sys.stdout.write(json.dumps(result, indent=2) + "\n")
        return 1 if result["status"] == "refused" else 0

    result = apply_file(args.path, sys.stdin.read(),
                        force=args.force, allow_growth=args.allow_growth,
                        dry_run=args.dry_run,
                        allow_new_commands=args.allow_new_commands)
    sys.stdout.write(json.dumps(result, indent=2) + "\n")
    return 1 if result["status"] == "refused" else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
