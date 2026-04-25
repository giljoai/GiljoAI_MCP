# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""INF-WriteShape: shared write-side validator for product_memory_entries.

This module owns the SINGLE validated write boundary used by both
write_360_memory and close_project_and_update_memory. Field allowlist +
size caps live here and nowhere else -- no parallel write paths, no
setattr-based shortcuts.

Caps (Step C ratified by analyzer 2026-04-25):
  summary           : <= 500 chars (2-3 sentence headline)
  key_outcomes      : <= 5 items, each <= 200 chars
  decisions_made    : <= 5 items, each <= 250 chars
  deliverables      : <= 3 items, each <= 100 chars   [drop-cap]
  tags              : <= 8 items, drawn from CONTROLLED_TAG_VOCABULARY
                      OR ``action_required:<title>``  (free-form follow-up)

## DELIBERATELY NOT IN VOCABULARY (Step C, 2026-04-25)

Excluded categories and rationale -- the safeguard against drift in 6 months:

* ``saas`` / ``ce`` / ``demo``: edition-specific identifiers belong in the
  release-channel metadata, not in 360-memory tags. Keeping them out
  prevents the vocab from accidentally becoming a routing index.
* ``deprecation`` / ``breaking-change`` / ``regression``: collapse into the
  existing ``refactor`` and ``bug-fix`` tags. A breaking change IS a
  refactor; a regression IS a bug-fix. Two ways to tag the same event
  fragment retrieval.
* ``hotfix`` / ``rollback``: collapse into ``bug-fix``. The urgency is
  signal at write time, not retrieval time.
* version strings (``v1.x.x``, sprint codes): change every release;
  burnable cardinality. Use commit metadata instead.

Add to vocab only after a written tag-vocab review -- not in passing.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


MEMORY_SUMMARY_MAX = 500
MEMORY_KEY_OUTCOME_MAX = 200
MEMORY_KEY_OUTCOMES_COUNT = 5
MEMORY_DECISION_MAX = 250
MEMORY_DECISIONS_COUNT = 5
# 89.4% of legacy entries are byte-identical to key_outcomes (analyzer 2026-04-25). Drop-cap; full removal scheduled post-demo.
MEMORY_DELIVERABLES_COUNT = 3
MEMORY_DELIVERABLE_MAX = 100
MEMORY_TAG_MAX_LEN = 30
MEMORY_TAGS_COUNT = 8


# Step C controlled vocabulary (16 tags, two-axis + 1 operational).
# Strict enum on the write side -- legacy entries are normalized on read via
# LEGACY_TAG_MAPPING in get_360_memory.py.
CONTROLLED_TAG_VOCABULARY: frozenset[str] = frozenset(
    {
        # Axis 1 -- Change type (8)
        "feature",
        "bug-fix",
        "refactor",
        "perf",
        "security",
        "docs",
        "test",
        "chore",
        # Axis 2 -- Domain/layer (7)
        "frontend",
        "backend",
        "database",
        "api",
        "infrastructure",
        "ui-ux",
        "integration",
        # Axis 3 -- Operational class (1)
        "migration",
    }
)


_ACTION_REQUIRED_PREFIX = "action_required:"


class _UnknownTagError(ValueError):
    """Internal carrier so the pydantic validator surfaces the bad tag verbatim."""

    def __init__(self, tag: str):
        self.tag = tag
        super().__init__(f"tag '{tag}' is not in the controlled vocabulary")


def _validate_tag_token(tag: str) -> str:
    """Tag-vocabulary gate.

    Accepts:
      * ``action_required:<free-form title>`` (preserved for task creation)
      * Any tag in CONTROLLED_TAG_VOCABULARY (length already <= cap)

    Raises ValueError on anything else (Pydantic converts to a field error).
    """
    if not isinstance(tag, str):
        # Pydantic field_validators convert ValueError to a clean field
        # error; TypeError bypasses that handling, so we keep ValueError.
        raise ValueError("tag must be a string")  # noqa: TRY004
    if tag.startswith(_ACTION_REQUIRED_PREFIX):
        title = tag[len(_ACTION_REQUIRED_PREFIX) :]
        if not title.strip():
            raise ValueError("action_required tag must include a non-empty title after ':'")
        return tag
    if len(tag) > MEMORY_TAG_MAX_LEN:
        raise ValueError(f"tag '{tag[:20]}...' exceeds {MEMORY_TAG_MAX_LEN} characters")
    if tag not in CONTROLLED_TAG_VOCABULARY:
        raise _UnknownTagError(tag)
    return tag


_TAG_GUIDANCE = (
    "Tags must come from the 16-entry controlled vocabulary. "
    "Pick 1-3 from change-type axis (feature/bug-fix/refactor/perf/security/docs/test/chore) "
    "AND 1-3 from domain axis (frontend/backend/database/api/infrastructure/ui-ux/integration). "
    "Use 'migration' for schema changes."
)


_GUIDANCE = {
    "summary": "Trim to 2-3 sentence headline of what changed and why. Detail belongs in commit messages.",
    "key_outcomes": (
        f"Cap is {MEMORY_KEY_OUTCOMES_COUNT} bullet outcomes, each <= {MEMORY_KEY_OUTCOME_MAX} chars. "
        "Merge or trim items, then retry."
    ),
    "decisions_made": (
        f"Cap is {MEMORY_DECISIONS_COUNT} architectural decisions, each <= {MEMORY_DECISION_MAX} chars. "
        "Move detail into commit messages or vision documents."
    ),
    "deliverables": (
        f"Cap is {MEMORY_DELIVERABLES_COUNT} deliverables, each <= {MEMORY_DELIVERABLE_MAX} chars. "
        "Deliverables is a drop-cap field (full removal scheduled post-demo) -- "
        "merge into key_outcomes if you have more."
    ),
    "tags": _TAG_GUIDANCE,
}


class MemoryEntryWriteValidationError(Exception):
    """Structured rejection raised when an agent-supplied write payload exceeds caps.

    Surface contract (single source of truth for both write tools):
        error       = "validation_failed"
        field       = first offending field name
        actual_size = observed size (chars or item count)
        max_size    = configured cap
        guidance    = actionable trim guidance for the agent

    Tag-vocab failures additionally carry ``invalid_tag`` and ``allowed`` so
    the agent gets the full enum back without a second round-trip.
    """

    def __init__(
        self,
        *,
        field: str,
        actual_size: int,
        max_size: int,
        guidance: str,
        invalid_tag: str | None = None,
        allowed: list[str] | None = None,
    ):
        self.error = "validation_failed"
        self.field = field
        self.actual_size = actual_size
        self.max_size = max_size
        self.guidance = guidance
        self.invalid_tag = invalid_tag
        self.allowed = allowed
        super().__init__(f"validation_failed: {field} actual={actual_size} max={max_size} -- {guidance}")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "error": self.error,
            "field": self.field,
            "actual_size": self.actual_size,
            "max_size": self.max_size,
            "guidance": self.guidance,
        }
        if self.invalid_tag is not None:
            payload["invalid_tag"] = self.invalid_tag
        if self.allowed is not None:
            payload["allowed"] = self.allowed
        return payload


class MemoryEntryWriteSchema(BaseModel):
    """Pydantic write-side schema for product_memory_entries (INF-WriteShape).

    Used by ProductMemoryService.create_entry() before any DB write.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    summary: str = Field(..., max_length=MEMORY_SUMMARY_MAX)
    key_outcomes: list[str] = Field(default_factory=list, max_length=MEMORY_KEY_OUTCOMES_COUNT)
    decisions_made: list[str] = Field(default_factory=list, max_length=MEMORY_DECISIONS_COUNT)
    deliverables: list[str] = Field(default_factory=list, max_length=MEMORY_DELIVERABLES_COUNT)
    tags: list[str] = Field(default_factory=list, max_length=MEMORY_TAGS_COUNT)

    @field_validator("key_outcomes")
    @classmethod
    def _validate_key_outcomes_items(cls, v: list[str]) -> list[str]:
        for i, item in enumerate(v):
            if not isinstance(item, str):
                raise ValueError(f"key_outcomes[{i}] must be a string")  # noqa: TRY004
            if len(item) > MEMORY_KEY_OUTCOME_MAX:
                raise ValueError(f"key_outcomes[{i}] exceeds {MEMORY_KEY_OUTCOME_MAX} characters (got {len(item)})")
        return v

    @field_validator("decisions_made")
    @classmethod
    def _validate_decisions_items(cls, v: list[str]) -> list[str]:
        for i, item in enumerate(v):
            if not isinstance(item, str):
                raise ValueError(f"decisions_made[{i}] must be a string")  # noqa: TRY004
            if len(item) > MEMORY_DECISION_MAX:
                raise ValueError(f"decisions_made[{i}] exceeds {MEMORY_DECISION_MAX} characters (got {len(item)})")
        return v

    @field_validator("deliverables")
    @classmethod
    def _validate_deliverables_items(cls, v: list[str]) -> list[str]:
        for i, item in enumerate(v):
            if not isinstance(item, str):
                raise ValueError(f"deliverables[{i}] must be a string")  # noqa: TRY004
            if len(item) > MEMORY_DELIVERABLE_MAX:
                raise ValueError(f"deliverables[{i}] exceeds {MEMORY_DELIVERABLE_MAX} characters (got {len(item)})")
        return v

    @field_validator("tags")
    @classmethod
    def _validate_tags_items(cls, v: list[str]) -> list[str]:
        return [_validate_tag_token(t) for t in v]


def _translate_pydantic_error(exc: ValidationError, payload: dict[str, Any]) -> MemoryEntryWriteValidationError:
    """Translate a pydantic ValidationError into the structured rejection exception.

    Picks the FIRST offending error and resolves cap + actual_size from the
    payload so the agent gets one clear message. Raising on first error
    keeps the agent-facing surface deterministic.
    """
    errors = exc.errors()
    if not errors:
        return MemoryEntryWriteValidationError(
            field="unknown", actual_size=0, max_size=0, guidance="Validation failed (no error details)"
        )

    first = errors[0]
    loc = first.get("loc", ())
    field = str(loc[0]) if loc else "unknown"
    raw = payload.get(field)

    if field == "summary":
        return MemoryEntryWriteValidationError(
            field=field,
            actual_size=len(raw) if isinstance(raw, str) else 0,
            max_size=MEMORY_SUMMARY_MAX,
            guidance=_GUIDANCE["summary"],
        )

    cap_map = {
        "key_outcomes": (MEMORY_KEY_OUTCOMES_COUNT, MEMORY_KEY_OUTCOME_MAX),
        "decisions_made": (MEMORY_DECISIONS_COUNT, MEMORY_DECISION_MAX),
        "deliverables": (MEMORY_DELIVERABLES_COUNT, MEMORY_DELIVERABLE_MAX),
        "tags": (MEMORY_TAGS_COUNT, MEMORY_TAG_MAX_LEN),
    }
    if field == "tags":
        # Tag-specific path: surface the invalid tag + allowed enum on vocab miss.
        ctx = first.get("ctx") or {}
        underlying = ctx.get("error")
        invalid_tag: str | None = None
        if isinstance(underlying, _UnknownTagError):
            invalid_tag = underlying.tag
        elif isinstance(raw, list) and len(loc) > 1 and isinstance(loc[1], int) and 0 <= loc[1] < len(raw):
            candidate = raw[loc[1]]
            if (
                isinstance(candidate, str)
                and candidate not in CONTROLLED_TAG_VOCABULARY
                and not candidate.startswith(_ACTION_REQUIRED_PREFIX)
            ):
                invalid_tag = candidate

        count_cap, item_cap = cap_map[field]
        if isinstance(raw, list) and len(raw) > count_cap:
            return MemoryEntryWriteValidationError(
                field=field,
                actual_size=len(raw),
                max_size=count_cap,
                guidance=_GUIDANCE[field],
            )
        if invalid_tag is not None:
            return MemoryEntryWriteValidationError(
                field=field,
                actual_size=len(invalid_tag),
                max_size=item_cap,
                guidance=_TAG_GUIDANCE,
                invalid_tag=invalid_tag,
                allowed=sorted(CONTROLLED_TAG_VOCABULARY),
            )
        return MemoryEntryWriteValidationError(
            field=field,
            actual_size=len(raw) if isinstance(raw, list) else 0,
            max_size=count_cap,
            guidance=_GUIDANCE[field],
        )

    if field in cap_map:
        count_cap, item_cap = cap_map[field]
        if isinstance(raw, list):
            if len(raw) > count_cap:
                return MemoryEntryWriteValidationError(
                    field=field,
                    actual_size=len(raw),
                    max_size=count_cap,
                    guidance=_GUIDANCE[field],
                )
            for item in raw:
                if isinstance(item, str) and len(item) > item_cap:
                    return MemoryEntryWriteValidationError(
                        field=field,
                        actual_size=len(item),
                        max_size=item_cap,
                        guidance=_GUIDANCE[field],
                    )
        return MemoryEntryWriteValidationError(
            field=field,
            actual_size=len(raw) if isinstance(raw, list) else 0,
            max_size=count_cap,
            guidance=_GUIDANCE[field],
        )

    return MemoryEntryWriteValidationError(field=field, actual_size=0, max_size=0, guidance=str(first.get("msg", "")))


def validate_memory_entry_write(payload: dict[str, Any]) -> MemoryEntryWriteSchema:
    """Single validated write boundary for product_memory_entries.

    Both write_360_memory and close_project_and_update_memory call this BEFORE
    constructing MemoryEntryCreateParams. Pydantic ValidationError is
    translated to MemoryEntryWriteValidationError (a structured rejection
    that the tool surfaces upstream).
    """
    try:
        return MemoryEntryWriteSchema(**payload)
    except ValidationError as exc:
        raise _translate_pydantic_error(exc, payload) from exc
