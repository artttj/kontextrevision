#!/usr/bin/env python3
"""Read-only scanner. Emits a JSON digest of agent instruction files.

Never returns file bodies. A tree can hold dozens of instruction files, and
loading them all into an agent's context defeats the purpose of tidying them.
"""

import hashlib
import json
import os
import re
import sys
from typing import Dict, List, Optional

SKIP_DIRS = {".git", "node_modules", "vendor", ".venv", "venv", "__pycache__", "dist", "build",
             "marketplaces"}

SOUL_NAMES = {"soul.md"}
AGENTS_NAMES = {"agents.md"}
CLAUDE_NAMES = {"claude.md", ".claude.md", ".claude.local.md"}

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")

FENCE_RE = re.compile(r"^\s*(```|~~~)")

CODE_SPAN_RE = re.compile(r"`([^`\n]{1,120})`")

COMMAND_RE = re.compile(
    r"^((?:npm|yarn|pnpm)\s+(?:run\s+)?[\w:.-]+"
    r"(?:\s+[-\w@:./=]+)*"
    r"|(?:make|composer|pytest|cargo|git|python|python3)\s+[-\w@:./=]+"
    r"(?:\s+[-\w@:./=]+)*"
    r"|docker\s+(?:compose\s+)?[-\w@:./=]+(?:\s+[-\w@:./=]+)*)$"
)

PATH_RE = re.compile(
    r"^(?:[\w.@~-]+/)+[\w.@-]+$"
    r"|^[\w.@-]+\.(?:md|py|js|ts|json|yml|yaml|toml|cfg)$")

TECH_NAMES = {"node.js", "vue.js", "next.js", "nuxt.js", "three.js", "d3.js",
              "express.js", "react.js", "ember.js", "backbone.js", "alpine.js"}


def classify_role(path: str) -> str:
    """Return the instruction-file role for a path, or 'unknown'."""
    base = os.path.basename(path).lower()
    if base in SOUL_NAMES:
        return "soul"
    if base in AGENTS_NAMES:
        return "agents"
    if base in CLAUDE_NAMES:
        return "claude"
    parts = [p.lower() for p in path.split(os.sep)]
    if base.endswith(".md") and len(parts) > 2 and parts[-2] == "rules" \
            and ".claude" in parts:
        return "rules"
    if base.endswith(".md") and ".claude" in parts and "rules" in parts:
        return "rules"
    return "unknown"


def discover(root: str) -> List[str]:
    """Return sorted absolute paths of instruction files under root.

    Accepts a single file as well as a directory, because the documented
    invocation revises one named file. Symlinks are skipped so the scanner and
    the writer agree on what is in scope.
    """
    if os.path.isfile(root):
        if os.path.islink(root) or classify_role(root) == "unknown":
            return []
        return [os.path.abspath(root)]
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in SKIP_DIRS and not os.path.islink(os.path.join(dirpath, d))]
        for name in filenames:
            full = os.path.join(dirpath, name)
            if os.path.islink(full):
                continue
            if classify_role(full) != "unknown":
                out.append(os.path.abspath(full))
    return sorted(out)


def normalize_body(text: str) -> str:
    """Collapse all whitespace runs to single spaces and strip. Used for hashing."""
    return re.sub(r"\s+", " ", text).strip()


def parse_sections(text: str) -> List[Dict]:
    """Split markdown into sections at ATX headings.

    The first section has heading None and level 0 when the file starts with
    content before any heading.
    """
    lines = text.split("\n")
    sections = []
    current = {"heading": None, "level": 0, "line": 1, "body": []}
    in_fence = False
    for idx, line in enumerate(lines, start=1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            current["body"].append(line)
            continue
        m = None if in_fence else HEADING_RE.match(line)
        if m:
            if current["heading"] is not None or normalize_body("\n".join(current["body"])):
                sections.append(current)
            current = {"heading": m.group(2), "level": len(m.group(1)), "line": idx, "body": []}
        else:
            current["body"].append(line)
    if current["heading"] is not None or normalize_body("\n".join(current["body"])):
        sections.append(current)

    out = []
    for sec in sections:
        body = "\n".join(sec["body"])
        norm = normalize_body(body)
        out.append({
            "heading": sec["heading"],
            "level": sec["level"],
            "line": sec["line"],
            "hash": hashlib.sha256(norm.encode("utf-8")).hexdigest()[:12],
            "bytes": len(body.encode("utf-8")),
        })
    return out


def estimate_tokens(text: str) -> int:
    """Rough token count. A delta only needs relative accuracy."""
    return len(text) // 4


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
    """Inline code spans plus fenced-block lines. Commands live here, prose does not."""
    spans = [m.group(1).strip() for m in CODE_SPAN_RE.finditer(text)]
    in_fence = False
    for line in text.split("\n"):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence and line.strip():
            spans.append(re.sub(r"\s+#.*$", "", line).strip())
    return spans


def extract_commands(text: str) -> List[str]:
    """Return unique runner commands. Only code-formatted spans are considered."""
    seen = []
    for span in code_spans(text):
        m = COMMAND_RE.match(re.sub(r"\s+", " ", span))
        if not m:
            continue
        cmd = m.group(1).strip()
        parts = cmd.split()
        if len(parts) < 2 or (parts[1] == "run" and len(parts) < 3):
            continue
        target = parts[2] if parts[1] == "run" else parts[1]
        if not _is_real_target(target):
            continue
        if cmd not in seen:
            seen.append(cmd)
    return seen


def extract_paths(text: str) -> List[str]:
    """Return unique code-formatted tokens that look like file paths."""
    seen = []
    for span in code_spans(text):
        if " " in span or len(span) > 120:
            continue
        if span.lower() in TECH_NAMES:
            continue
        if PATH_RE.match(span) and span not in seen:
            seen.append(span)
    return seen


DESC_RE = re.compile(r"^description:\s*(.+?)(?=\n[A-Za-z_][\w.-]*:|\Z)",
                     re.MULTILINE | re.DOTALL)
NAME_RE = re.compile(r"^name:\s*(.+)$", re.MULTILINE)


def _clean_scalar(raw: str) -> str:
    """Strip a YAML block-scalar marker and collapse the folded body."""
    text = raw.strip()
    if text[:2] in (">-", ">+", "|-", "|+") or text[:1] in (">", "|"):
        text = text.lstrip(">|+-")
    return re.sub(r"\s+", " ", text).strip()


def classify_definition(path: str) -> str:
    """Return skill, agent, command, or unknown for a harness definition file.

    Requires the conventional parent directory, and excludes documentation trees,
    so an unrelated `docs/agents/` folder is not counted as installed definitions.
    """
    parts = [p.lower() for p in path.split(os.sep)]
    base = os.path.basename(path)
    if set(parts) & {"docs", "doc", "documentation", "examples", "templates"}:
        return "unknown"
    if base == "SKILL.md" and len(parts) > 2 and parts[-3] == "skills":
        return "skill"
    if not base.endswith(".md") or len(parts) < 2:
        return "unknown"
    if parts[-2] == "agents":
        return "agent"
    if parts[-2] == "commands":
        return "command"
    return "unknown"


VERSION_RE = re.compile(r"^\d+(?:\.\d+)*$")


def _version_key(text: str):
    return tuple(int(x) for x in text.split(".") if x.isdigit())


def _cache_slot(path: str) -> Optional[tuple]:
    """Identify plugins/cache/<market>/<plugin>/<version>/ and return its parts.

    The plugin cache keeps superseded versions on disk. Only the newest is
    loaded, so counting them all inflates the always-on total several times over.
    """
    parts = path.split(os.sep)
    for i, part in enumerate(parts):
        if part == "cache" and i >= 1 and parts[i - 1] == "plugins":
            tail = parts[i + 1:]
            for j, seg in enumerate(tail):
                if VERSION_RE.match(seg):
                    return (os.sep.join(tail[:j]), seg, os.sep.join(tail[j + 1:]))
    return None


def discover_harness(root: str) -> List[str]:
    """Walk root and return sorted paths of skill, agent, and command definitions.

    Superseded plugin-cache versions are dropped so the always-on total reflects
    what is actually loaded.
    """
    out = []
    cached = []
    newest = {}
    if os.path.isfile(root):
        return [] if os.path.islink(root) or classify_definition(root) == "unknown" \
            else [os.path.abspath(root)]
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in SKIP_DIRS and not os.path.islink(os.path.join(dirpath, d))]
        for name in filenames:
            full = os.path.abspath(os.path.join(dirpath, name))
            if os.path.islink(full) or classify_definition(full) == "unknown":
                continue
            slot = _cache_slot(full)
            if slot is None:
                out.append(full)
                continue
            plugin, version, _ = slot
            cached.append((plugin, version, full))
            if plugin not in newest or _version_key(version) > _version_key(newest[plugin]):
                newest[plugin] = version
    out.extend(full for plugin, version, full in cached if version == newest[plugin])
    return sorted(out)


def digest_definition(path: str) -> Dict:
    """Split a definition into its always-on description and on-demand body.

    Only the description is injected into every session. The body loads when the
    definition is invoked, so the two costs are not comparable.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    description, name = "", ""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            m = DESC_RE.search(parts[1])
            description = _clean_scalar(m.group(1)) if m else ""
            n = NAME_RE.search(parts[1])
            name = n.group(1).strip() if n else ""
    if not name:
        base = os.path.basename(path)
        name = os.path.basename(os.path.dirname(path)) if base == "SKILL.md" else base[:-3]
    always = estimate_tokens(description)
    return {
        "path": path,
        "kind": classify_definition(path),
        "name": name,
        "description": description,
        "always_on_tokens": always,
        "on_demand_tokens": max(0, estimate_tokens(text) - always),
    }


def build_harness_digest(root: str) -> Dict:
    """Cost of every skill, agent, and command definition under root."""
    defs = []
    for p in discover_harness(root):
        try:
            defs.append(digest_definition(p))
        except (IOError, OSError):
            continue
    counts = {}
    for d in defs:
        key = (d["kind"], d["name"])
        counts[key] = counts.get(key, 0) + 1
    duplicates = {}
    for (kind, name), n in counts.items():
        if n > 1:
            duplicates["{0}:{1}".format(kind, name)] = n
    return {
        "root": root,
        "definitions": defs,
        "definition_count": len(defs),
        "always_on_tokens": sum(d["always_on_tokens"] for d in defs),
        "on_demand_tokens": sum(d["on_demand_tokens"] for d in defs),
        "duplicates": duplicates,
    }


def digest_file(path: str) -> Dict:
    """Build the digest entry for one file. Never returns the file body."""
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    return {
        "path": path,
        "role": classify_role(path),
        "bytes": len(text.encode("utf-8")),
        "est_tokens": estimate_tokens(text),
        "sections": parse_sections(text),
        "commands": extract_commands(text),
        "paths": extract_paths(text),
    }


def _find_mirrors(files: List[Dict]):
    """Pair AGENTS.md with an identical CLAUDE.md in the same directory.

    Keeping both is deliberate cross-tool compatibility: Codex reads one name and
    Claude Code the other, and no session loads both. Counting the pair twice
    overstates what the repository actually costs.
    """
    by_dir = {}
    for f in files:
        by_dir.setdefault(os.path.dirname(f["path"]), {})[f["role"]] = f
    mirrors, saved = [], 0
    for directory, roles in sorted(by_dir.items()):
        a, c = roles.get("agents"), roles.get("claude")
        if not a or not c:
            continue
        a_hashes = [s["hash"] for s in a["sections"]]
        if a_hashes and a_hashes == [s["hash"] for s in c["sections"]]:
            mirrors.append(["AGENTS.md", "CLAUDE.md"])
            saved += min(a["est_tokens"], c["est_tokens"])
    return mirrors, saved


def build_digest(root: str) -> Dict:
    """Digest everything under root that costs tokens on every session.

    Instruction files and harness definitions are both always-on, but a
    definition's body is not: it loads only when invoked. The two are reported
    separately so they are never compared as though they cost the same.
    """
    files = []
    for p in discover(root):
        try:
            files.append(digest_file(p))
        except (IOError, OSError):
            continue
    harness = build_harness_digest(root)
    mirrors, mirrored_away = _find_mirrors(files)
    instruction_tokens = sum(f["est_tokens"] for f in files) - mirrored_away
    return {
        "root": root,
        "files": files,
        "definitions": harness["definitions"],
        "instruction_tokens": instruction_tokens,
        "description_tokens": harness["always_on_tokens"],
        "always_on_tokens": instruction_tokens + harness["always_on_tokens"],
        "on_demand_tokens": harness["on_demand_tokens"],
        "duplicates": harness["duplicates"],
        "mirrors": mirrors,
        "total_tokens": instruction_tokens,
    }


def main(argv: List[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("-")]
    root = args[0] if args else "."
    payload = build_harness_digest(root) if "--harness" in argv else build_digest(root)
    sys.stdout.write(json.dumps(payload, indent=2))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
