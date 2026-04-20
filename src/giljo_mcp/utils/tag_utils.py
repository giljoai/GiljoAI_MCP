# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Shared tag cleanup utilities (BE-5022f).

Used by both project_closeout._extract_tags() and write_360_memory._validate_tags()
to enforce consistent tag hygiene: stopword filtering, punctuation stripping,
case-insensitive dedup, and length caps.
"""

# Stopwords to filter from auto-extracted tags
STOPWORDS: frozenset[str] = frozenset(
    {
        "from",
        "with",
        "the",
        "and",
        "for",
        "in",
        "to",
        "of",
        "a",
        "an",
        "is",
        "on",
        "at",
        "by",
        "or",
        "as",
        "it",
        "that",
        "this",
        "was",
        "are",
        "be",
        "has",
        "had",
        "not",
        "but",
        "all",
        "can",
    }
)

# Punctuation to strip from tag boundaries
STRIP_CHARS = "(),:;.!?"

# Limits
MAX_TAG_LENGTH = 50
MAX_TAGS = 15


def strip_tag_punctuation(tag: str) -> str:
    """Strip whitespace and boundary punctuation from a tag.

    Does NOT truncate. Used by _validate_tags() for agent-provided tags
    where the caller enforces its own length limit.

    Args:
        tag: Raw tag string.

    Returns:
        Cleaned tag string (may be empty if tag was all punctuation).
    """
    return tag.strip().strip(STRIP_CHARS)


def sanitize_tag(tag: str) -> str:
    """Sanitize a single tag: strip whitespace, strip boundary punctuation, truncate.

    Used by clean_tags() for auto-extracted tokens where 50-char cap applies.

    Args:
        tag: Raw tag string.

    Returns:
        Cleaned tag string (may be empty if tag was all punctuation).
    """
    tag = strip_tag_punctuation(tag)
    tag = tag[:MAX_TAG_LENGTH]
    return tag


def clean_tags(tags: list[str] | None) -> list[str]:
    """Apply full tag cleanup pipeline.

    Steps:
        1. Strip boundary punctuation from each tag
        2. Remove empty tags
        3. Filter out stopwords (case-insensitive)
        4. Case-insensitive dedup (keep first occurrence)
        5. Truncate to MAX_TAG_LENGTH chars per tag
        6. Cap at MAX_TAGS total

    Args:
        tags: List of raw tag strings, or None.

    Returns:
        Cleaned list of tags.
    """
    if not tags:
        return []

    result: list[str] = []
    seen_lower: set[str] = set()

    for tag in tags:
        cleaned = sanitize_tag(tag)

        if not cleaned:
            continue

        if cleaned.lower() in STOPWORDS:
            continue

        lower_key = cleaned.lower()
        if lower_key in seen_lower:
            continue
        seen_lower.add(lower_key)

        result.append(cleaned)

        if len(result) >= MAX_TAGS:
            break

    return result
