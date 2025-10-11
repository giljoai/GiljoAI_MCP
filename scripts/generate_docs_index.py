#!/usr/bin/env python3
import os
import re
import sys
import subprocess
from pathlib import Path


DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"
INDEX_FILE = DOCS_DIR / "index.md"


EXCLUDE_NAMES = {
    "index.md",
    "index_files.md",
    "CHANGELOG.md",
}

EXCLUDE_PATTERNS = [
    re.compile(r"(^|/)README\.md$", re.IGNORECASE),
    re.compile(r"\.(png|jpg|jpeg|gif|svg|webp|ico)$", re.IGNORECASE),
]


def should_exclude(path: Path) -> bool:
    name = path.name
    if name in EXCLUDE_NAMES:
        return True
    p_str = str(path).replace("\\", "/")
    for pat in EXCLUDE_PATTERNS:
        if pat.search(p_str):
            return True
    return False


def words_from_filename(path: Path) -> str:
    base = path.stem
    # remove trailing existing tag like __OUTDATED etc
    base = re.sub(r"__(OUTDATED|FRAGMENTED|DELETE|URGENT)$", "", base, flags=re.IGNORECASE)
    # normalize separators
    base = base.replace("_", " ").replace("-", " ")
    # remove extra tokens
    base = re.sub(r"\b(v\d+|final|report|guide|readme|doc|documentation)\b", " ", base, flags=re.IGNORECASE)
    # collapse spaces
    base = re.sub(r"\s+", " ", base).strip()
    return base or path.stem


def describe(path: Path) -> str:
    topic = words_from_filename(path)
    # 20-word concise description using topic and folder context
    parts = []
    parts.append(f"{topic} documentation for GiljoAI MCP")
    # folder hint
    parent = path.parent.name
    if parent and parent != "docs":
        parts.append(f"({parent})")
    parts.append("purpose, usage, and context for maintainers and agents.")
    text = " ".join(parts)
    # limit to ~20 words
    words = text.split()
    return " ".join(words[:20])


def classify(path: Path) -> str:
    p = str(path).lower().replace("\\", "/")
    name = path.name.lower()

    # Highly relevant, needs small updates
    urgent_dirs = [
        "/implementation/",
        "/guides/",
        "/manuals/",
        "/installer",
        "/install_project/",
        "/testing/",
        "/tests/",
        "/security/",
        "/diagrams/",
        "/architecture/",
    ]

    # Mostly obsolete buckets
    fragmented_dirs = [
        "/archive/",
        "/v2_archive/",
        "/oct9/",
        "/reports/",
        "/research/",
        "/adr/",
        "/agents/",
        "/agent_templates/",
        "/projects/",
        "/code_cleaning/",
    ]

    # Dev logs remain useful context but not canonical
    if "/devlog/" in p or "/devlogs/" in p:
        return "OUTDATED"

    if "installation_flow" in name:
        return "URGENT"
    if "v3" in name:
        return "URGENT"
    if any(d in p for d in urgent_dirs):
        return "URGENT"
    if any(d in p for d in fragmented_dirs):
        return "FRAGMENTED"
    if "v2" in name or "_v2" in name:
        return "FRAGMENTED"
    if any(k in name for k in ["migration", "legacy", "old", "archive"]):
        return "FRAGMENTED"
    if any(k in name for k in ["proposal", "vision", "roadmap"]):
        return "URGENT"

    # Default: still relevant but may need update
    return "OUTDATED"


def append_tag_to_filename(path: Path, tag: str) -> Path:
    stem = path.stem
    # Remove any existing terminal tag
    stem = re.sub(r"__(OUTDATED|FRAGMENTED|DELETE|URGENT)$", "", stem, flags=re.IGNORECASE)
    new_name = f"{stem}__{tag}{path.suffix}"
    return path.with_name(new_name)


def git_mv(old: Path, new: Path):
    subprocess.check_call(["git", "mv", str(old), str(new)])


def collect_files(root: Path):
    files = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            path = Path(dirpath) / fn
            if should_exclude(path):
                continue
            files.append(path)
    return sorted(files, key=lambda p: str(p).lower())


def main(argv):
    do_rename = True
    if "--no-rename" in argv:
        do_rename = False

    files = collect_files(DOCS_DIR)

    entries = []
    rename_pairs = []
    for f in files:
        tag = classify(f)
        # Allow explicit delete for very old archives
        if any(x in str(f).lower() for x in ["_final_", "cleanup", "handoff"]) and ("archive" in str(f).lower() or "v2" in str(f).lower()):
            tag = "DELETE"
        desc = describe(f)
        new_path = append_tag_to_filename(f, tag)
        entries.append((new_path if do_rename else f, tag, desc))
        if do_rename and new_path != f:
            rename_pairs.append((f, new_path))

    # Perform renames first so index reflects new names
    if do_rename:
        for old, new in rename_pairs:
            new.parent.mkdir(parents=True, exist_ok=True)
            if not new.exists():
                git_mv(old, new)

    # Write index
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    with INDEX_FILE.open("w", encoding="utf-8") as f:
        f.write("# Documentation Index\n\n")
        f.write("This index inventories all documentation files under `docs/`, with a brief description and curation tag.\n\n")
        f.write("Tags: `URGENT` (80% relevancy, minor updates), `OUTDATED` (relevant, needs refresh), `FRAGMENTED` (partially obsolete), `DELETE` (no longer relevant).\n\n")

        for path, tag, desc in entries:
            rel = path.relative_to(DOCS_DIR)
            f.write(f"- `{rel.as_posix()}` — {desc} — Tag: {tag}\n")

    print(f"Wrote {INDEX_FILE}")
    print(f"Indexed {len(entries)} files. Renamed {len(rename_pairs)} files.")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
