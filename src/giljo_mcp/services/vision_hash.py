# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Derived ``vision_inputs_hash`` helper (BE-5122).

Computes a stable SHA-256 fingerprint of the *current* vision-document inputs
for a product. The hash is **derived**, never persisted:
``ProductResponse.vision_inputs_hash`` is compared against
``Product.consolidated_vision_hash`` (which IS persisted -- the hash of the
inputs at the last consolidation run) to detect drift.

The CTX project_type orchestrator uses the equality of these two values as a
self-close signal: equal => aggregates are already fresh, no work needed.

Canonical encoding (MUST stay in lock-step with
:class:`giljo_mcp.services.consolidation_service.ConsolidatedVisionService`):

* Filter to ``is_active`` documents only (and exclude soft-deleted/trashed, BE-6130b).
* Sort by ``display_order`` ascending.
* Concatenate ``"# {document_name}\\n\\n{vision_document}"`` per doc, joined
  by ``"\\n\\n"``.
* SHA-256 the UTF-8 encoding of the result.
* The derived field carries a ``sha256:`` prefix; the persisted column stores
  raw hex (no prefix). Comparison strips the prefix.
* Empty input set (or no active docs) => ``VISION_INPUTS_HASH_EMPTY``
  (``"sha256:empty"``). The empty sentinel never matches a real hash.

The shared aggregate-text builder, :func:`build_vision_aggregate`, is the
single source of truth for this algorithm. ``ConsolidationService._build_aggregate``
delegates to it so the derived and persisted hashes are computed identically.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from typing import Any


__all__ = [
    "VISION_INPUTS_HASH_EMPTY",
    "build_vision_aggregate",
    "compute_vision_inputs_hash",
    "vision_inputs_hash_matches_consolidated",
]

VISION_INPUTS_HASH_EMPTY = "sha256:empty"
_PREFIX = "sha256:"


def _active_sorted_docs(vision_documents: Iterable[Any] | None) -> list[Any]:
    if not vision_documents:
        return []
    # BE-6130b: a soft-deleted (trashed) doc must NOT contribute to the
    # consolidated-vision aggregate or its hash — it is excluded alongside
    # is_active here, the single source of truth both callers share.
    active = [
        doc for doc in vision_documents if getattr(doc, "is_active", True) and getattr(doc, "deleted_at", None) is None
    ]
    return sorted(active, key=lambda d: getattr(d, "display_order", 0))


def build_vision_aggregate(
    vision_documents: Iterable[Any] | None,
) -> tuple[str, list[Any], str]:
    """Return ``(aggregate_text, source_doc_ids, raw_hex_hash)``.

    Single source of truth for the consolidated-vision aggregate algorithm.
    Both the persisted ``Product.consolidated_vision_hash`` and the derived
    ``vision_inputs_hash`` are computed from this output.

    Empty input (or zero active docs) yields ``("", [], "")``.
    """
    sorted_docs = _active_sorted_docs(vision_documents)
    if not sorted_docs:
        return "", [], ""

    parts: list[str] = []
    source_doc_ids: list[Any] = []
    for doc in sorted_docs:
        name = getattr(doc, "document_name", "") or ""
        body = getattr(doc, "vision_document", "") or ""
        parts.append(f"# {name}\n\n{body}")
        source_doc_ids.append(getattr(doc, "id", None) if hasattr(doc, "id") else name)

    aggregate_text = "\n\n".join(parts)
    raw_hex = hashlib.sha256(aggregate_text.encode("utf-8")).hexdigest()
    return aggregate_text, source_doc_ids, raw_hex


def compute_vision_inputs_hash(vision_documents: Iterable[Any] | None) -> str:
    """Return ``sha256:<hex>`` for the given vision documents (BE-5122).

    The hex digest is identical to the value
    ``ConsolidationService._build_aggregate`` would store on the product after
    consolidation, so equality with the persisted ``consolidated_vision_hash``
    (after stripping the ``sha256:`` prefix) means the aggregates are fresh.

    Empty or all-inactive inputs return :data:`VISION_INPUTS_HASH_EMPTY`.
    """
    _aggregate_text, _ids, raw_hex = build_vision_aggregate(vision_documents)
    if not raw_hex:
        return VISION_INPUTS_HASH_EMPTY
    return f"{_PREFIX}{raw_hex}"


def vision_inputs_hash_matches_consolidated(
    vision_inputs_hash: str | None,
    consolidated_vision_hash: str | None,
) -> bool:
    """True iff the derived inputs hash equals the persisted consolidated hash.

    The derived value carries a ``sha256:`` prefix; the persisted column stores
    raw hex. The empty sentinel never matches a real consolidated hash.
    """
    if not vision_inputs_hash or not consolidated_vision_hash:
        return False
    if vision_inputs_hash == VISION_INPUTS_HASH_EMPTY:
        return False
    if not vision_inputs_hash.startswith(_PREFIX):
        return vision_inputs_hash == consolidated_vision_hash
    return vision_inputs_hash[len(_PREFIX) :] == consolidated_vision_hash
