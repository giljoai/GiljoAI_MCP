from __future__ import annotations

from pathlib import Path


SKIP_DIR_NAMES = {".git", "__pycache__", "venv", "venv_devtools", ".mypy_cache", ".pytest_cache"}


def should_skip(path: Path) -> bool:
    """Return True if this path should be skipped from scrubbing."""
    parts = set(path.parts)
    if parts & SKIP_DIR_NAMES:
        return True
    return False


def scrub_text(content: str) -> str:
    """Scrub legacy token-reduction marketing language from a text blob.

    The goal is to remove the old \"context prioritization\" framing and replace it
    with the current context-prioritization / orchestration framing, without
    changing any functional code.
    """
    updated = content

    # Strongest legacy claim (keep this first where it appears verbatim).
    updated = updated.replace(
        "context prioritization and orchestration",
        "context prioritization and orchestration",
    )

    # Generic phrase used across docs/tests.
    updated = updated.replace(
        "context prioritization",
        "context prioritization",
    )

    # Common capitalized variant, if present.
    updated = updated.replace(
        "Context prioritization",
        "Context prioritization",
    )

    return updated


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    changed_files: list[Path] = []

    for path in root.rglob("*"):
        # Skip system/virtualenv/cache dirs early.
        if should_skip(path):
            continue

        # Some paths (e.g., under .uv-cache on Windows) can raise OSError
        # even when calling is_file/stat. Guard those and skip on failure.
        try:
            if not path.is_file():
                continue
        except OSError:
            continue

        try:
            original = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            # Skip non-text/binary or inaccessible files.
            continue

        updated = scrub_text(original)
        if updated != original:
            try:
                path.write_text(updated, encoding="utf-8")
            except OSError:
                # If we can't write this particular path, move on.
                continue
            changed_files.append(path)

    if changed_files:
        print("Scrubbed token-reduction language in:")
        for p in sorted(changed_files):
            print(f" - {p}")
    else:
        print("No token-reduction language found to scrub.")


if __name__ == "__main__":
    main()
