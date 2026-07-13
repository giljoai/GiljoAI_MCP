# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
MCP Tools: get_vision_doc and update_product_context (Handover 0842c)

Provides vision document retrieval with extraction prompt and structured
product field writing from AI analysis results.

Called by the user's AI coding agent during vision document analysis workflow.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from giljo_mcp.database import DatabaseManager
from giljo_mcp.exceptions import ResourceNotFoundError, ValidationError
from giljo_mcp.models.context import MCPContextIndex
from giljo_mcp.models.products import (
    Product,
)
from giljo_mcp.repositories.vision_document_repository import VisionDocumentRepository
from giljo_mcp.schemas.jsonb_validators import (
    validate_consolidated_vision,
    validate_vision_summaries,
)
from giljo_mcp.services.product_field_map import assemble_update_kwargs
from giljo_mcp.services.product_vision_service import ProductVisionService


logger = logging.getLogger(__name__)


VISION_EXTRACTION_PROMPT = """You are analyzing a product vision document for a software
development orchestration platform. Extract structured information and generate summaries.

RULES:
- Extract ONLY information explicitly stated in the document chunks below
- If a field cannot be determined from the document, OMIT it entirely
- Do NOT guess, invent, or infer information not present
- Keep descriptions concise and factual, not promotional
- product_description should be 2-3 sentences maximum
- testing_strategy MUST be one of: TDD, BDD, Integration-First, E2E-First, Manual, Hybrid
- target_platforms MUST be a list of: windows, linux, macos, android, ios, web, all
  Use 'web' for browser-based apps (SPA, PWA, responsive). Use 'all' alone if cross-platform.
- For summaries: preserve technical specs, architecture decisions, and constraints
- For summaries: remove marketing prose, user personas, and storytelling

After reading ALL chunks, call the update_product_context tool with all fields you were
able to extract. Summaries are passed via two parameters:

- vision_summaries: a list of {doc_id, light, medium} entries -- ONE entry per active
  vision document. The doc_id is the UUID returned alongside each chunk's content in
  the get_vision_doc response. light is a concise ~33% per-document summary; medium
  is a thorough ~66% per-document summary preserving decisions, architecture, and
  feature descriptions.
- consolidated_vision: a single {light, medium} dict aggregating ALL documents at the
  same two zoom levels.

After extracting per-doc summaries, produce a consolidated_vision aggregating all
docs at the same two zoom levels.

{custom_instructions}"""


VALID_TESTING_STRATEGIES = {"TDD", "BDD", "Integration-First", "E2E-First", "Manual", "Hybrid"}

FIELD_MAP = {
    "product_name": ("products", "name"),
    "product_description": ("products", "description"),
    "core_features": ("products", "core_features"),
    "programming_languages": ("tech_stack", "programming_languages"),
    "frontend_frameworks": ("tech_stack", "frontend_frameworks"),
    "backend_frameworks": ("tech_stack", "backend_frameworks"),
    "databases": ("tech_stack", "databases_storage"),
    "infrastructure": ("tech_stack", "infrastructure"),
    "target_platforms": ("products", "target_platforms"),
    "architecture_pattern": ("architecture", "primary_pattern"),
    "design_patterns": ("architecture", "design_patterns"),
    "api_style": ("architecture", "api_style"),
    "architecture_notes": ("architecture", "architecture_notes"),
    "coding_conventions": ("architecture", "coding_conventions"),
    "brand_guidelines": ("products", "brand_guidelines"),
    "quality_standards": ("test_config", "quality_standards"),
    "testing_strategy": ("test_config", "test_strategy"),
    "testing_frameworks": ("test_config", "testing_frameworks"),
    "test_coverage_target": ("test_config", "coverage_target"),
}

# Extraction field names grouped by target relation block. Used by the
# overwrite-protection rollback below to map a skipped block back to the
# extraction fields that didn't write. (The column->block grouping itself lives in
# the shared product-field translator, services/product_field_map.py.)
_TECH_STACK_FIELDS = {k for k, (t, _) in FIELD_MAP.items() if t == "tech_stack"}
_ARCHITECTURE_FIELDS = {k for k, (t, _) in FIELD_MAP.items() if t == "architecture"}
_TEST_CONFIG_FIELDS = {k for k, (t, _) in FIELD_MAP.items() if t == "test_config"}


@asynccontextmanager
async def _session_scope(
    db_manager: DatabaseManager | None,
    test_session: AsyncSession | None,
):
    """Yield the test session directly or open a new managed session."""
    if test_session is not None:
        yield test_session
    else:
        async with db_manager.get_session_async() as session:
            yield session


async def get_vision_doc(
    product_id: str,
    tenant_key: str,
    chunk: int | None = None,
    db_manager: DatabaseManager | None = None,
    websocket_manager: Any = None,
    _test_session: AsyncSession | None = None,
) -> dict[str, Any]:
    """
    Retrieve vision document content as paginated chunks with extraction instructions.

    Call with no chunk parameter to get metadata (total_chunks, extraction_instructions).
    Then call with chunk=1, chunk=2, etc. to retrieve each chunk's content.

    Args:
        product_id: Target product UUID
        tenant_key: Tenant isolation key
        chunk: 1-based chunk number to retrieve. Omit for metadata only.
        db_manager: Injected by ToolAccessor

    Returns:
        Without chunk param: metadata (total_chunks, total_tokens, extraction_instructions, etc.)
        With chunk param: single chunk content + metadata

    Raises:
        ResourceNotFoundError: If product not found or has no vision documents
    """
    if not db_manager and _test_session is None:
        raise ValueError("db_manager is required")

    async with _session_scope(db_manager, _test_session) as session:
        stmt = (
            select(Product)
            .where(Product.id == product_id, Product.tenant_key == tenant_key)
            .options(selectinload(Product.vision_documents))
        )
        result = await session.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            raise ResourceNotFoundError(
                f"Product {product_id} not found for tenant",
                context={"product_id": product_id},
            )

        # BE-6130b: the vision_documents relationship loads trashed rows too;
        # exclude soft-deleted docs (deleted_at) alongside the is_active filter.
        active_docs = [doc for doc in product.vision_documents if doc.is_active and doc.deleted_at is None]

        if not active_docs:
            raise ResourceNotFoundError(
                "No vision documents found for this product",
                context={"product_id": product_id},
            )

        # Collect vision_document_ids for chunk lookup
        doc_ids = [str(doc.id) for doc in active_docs]

        # Query pre-chunked content from mcp_context_index, ordered by chunk_order
        chunk_stmt = (
            select(MCPContextIndex)
            .where(
                MCPContextIndex.product_id == product_id,
                MCPContextIndex.tenant_key == tenant_key,
                MCPContextIndex.vision_document_id.in_(doc_ids),
            )
            .order_by(MCPContextIndex.vision_document_id, MCPContextIndex.chunk_order)
        )
        chunk_result = await session.execute(chunk_stmt)
        all_chunks = chunk_result.scalars().all()

        if not all_chunks:
            # Fallback: document exists but hasn't been chunked yet — use raw content.
            # BE-5117b: preserve per-doc identity so the agent can map chunks back
            # to vision_summaries[].doc_id when writing summaries.
            logger.warning("No chunks found for product %s, falling back to raw document", product_id)
            raw_pairs = [(str(doc.id), doc.vision_document) for doc in active_docs if doc.vision_document]
        else:
            raw_pairs = [(str(c.vision_document_id), c.content) for c in all_chunks]

        # Sub-split any chunks >25K chars so each fits within MCP tool output limits.
        max_chars = 25000
        split_pairs: list[tuple[str, str]] = []
        for doc_id_value, raw in raw_pairs:
            if len(raw) <= max_chars:
                split_pairs.append((doc_id_value, raw))
            else:
                # Split on paragraph boundaries where possible
                split_pairs.extend((doc_id_value, raw[i : i + max_chars]) for i in range(0, len(raw), max_chars))

        chunk_list = [
            {
                "chunk_order": i + 1,
                "doc_id": doc_id_value,
                "content": text,
                "token_count": len(text.split()),
            }
            for i, (doc_id_value, text) in enumerate(split_pairs)
        ]

        total_chunks = len(chunk_list)
        total_tokens = sum(c["token_count"] for c in chunk_list)

        custom_instructions = product.extraction_custom_instructions or ""
        extraction_instructions = VISION_EXTRACTION_PROMPT.replace("{custom_instructions}", custom_instructions)

        active_doc_ids = [str(doc.id) for doc in active_docs]
        base = {
            "total_chunks": total_chunks,
            "total_tokens": total_tokens,
            "extraction_instructions": extraction_instructions,
            "write_tool": "update_product_context",
            "product_id": product_id,
            "product_name": product.name,
            "doc_ids": active_doc_ids,
        }

        if chunk is not None:
            # Return a single chunk
            if chunk < 1 or chunk > total_chunks:
                raise ResourceNotFoundError(
                    f"Chunk {chunk} not found (valid range: 1-{total_chunks})",
                    context={"product_id": product_id, "chunk": chunk, "total_chunks": total_chunks},
                )
            selected = chunk_list[chunk - 1]
            base["chunk"] = chunk
            base["doc_id"] = selected["doc_id"]
            base["content"] = selected["content"]
            base["chunk_token_count"] = selected["token_count"]
        else:
            # Metadata only — no content, agent should request chunks individually
            base["usage"] = f"Call again with chunk=1 through chunk={total_chunks} to retrieve content"

        # Notify frontend that the agent has connected and started analysis
        if websocket_manager and chunk is None:
            from giljo_mcp.events.schemas import EventFactory

            event = EventFactory.tenant_envelope(
                event_type="vision:analysis_started",
                tenant_key=tenant_key,
                data={"product_id": product_id, "total_chunks": total_chunks},
            )
            await websocket_manager.broadcast_event_to_tenant(tenant_key=tenant_key, event=event)

        return base


def _build_update_kwargs(
    fields: dict[str, Any],
    fields_written: list[str],
) -> dict[str, Any]:
    """Build kwargs dict for ProductService.update_product() from extracted fields.

    Translates each extracted vision field to its canonical product column via
    FIELD_MAP, then groups the columns into update_product blocks through the shared
    product-field translator (services/product_field_map.py) -- the same translator the
    context-tuning writer uses. Mutates fields_written in place to track which extraction
    fields will be written. Relation blocks are written as partial dicts;
    ProductRepository.update_config_relations merges them per-field, so only the provided
    columns are overwritten.
    """
    column_values: dict[str, Any] = {}
    for field_name, (_table, column_name) in FIELD_MAP.items():
        if field_name in fields:
            column_values[column_name] = fields[field_name]
            fields_written.append(field_name)
    return assemble_update_kwargs(column_values)


async def update_product_fields(
    product_id: str,
    tenant_key: str,
    db_manager: DatabaseManager | None = None,
    websocket_manager: Any = None,
    _test_session: AsyncSession | None = None,
    force: bool = False,
    **fields: Any,
) -> dict[str, Any]:
    """
    Write product fields extracted from vision document analysis.

    Performs merge-write: only updates fields that are explicitly provided.
    Creates child table rows (tech_stack, architecture, test_config) on first write.

    Args:
        product_id: Target product UUID
        tenant_key: Tenant isolation key
        db_manager: Injected by ToolAccessor
        websocket_manager: Injected by ToolAccessor for event emission
        **fields: Extracted field key-value pairs

    Returns:
        Dict with success, fields_written count, and fields list

    Raises:
        ResourceNotFoundError: If product not found for tenant
    """
    if not db_manager and _test_session is None:
        raise ValueError("db_manager is required")

    # BE-5117b: legacy summary fields were the parallel write path into
    # vision_document_summaries. That table is gone and only the column
    # path (vision_summaries / consolidated_vision) is valid. Silent no-op
    # would mask agent-prompt drift -- raise loudly so the caller sees it.
    _legacy_summary_fields = {"summary_33", "summary_66"}
    _legacy_passed = _legacy_summary_fields.intersection(fields)
    if _legacy_passed:
        raise ValidationError(
            message=(
                f"Unknown fields: {sorted(_legacy_passed)}. "
                "summary_33 / summary_66 were removed in BE-5117b. Use "
                "vision_summaries=[{doc_id, light, medium}] for per-document "
                "summaries and consolidated_vision={light, medium} for the "
                "product-level aggregate."
            ),
            context={"unknown_fields": sorted(_legacy_passed)},
        )

    # -- Input validation before any DB access --
    if "testing_strategy" in fields:
        strategy = fields["testing_strategy"]
        if strategy not in VALID_TESTING_STRATEGIES:
            valid_list = ", ".join(sorted(VALID_TESTING_STRATEGIES))
            raise ValidationError(
                message=f"Invalid testing_strategy '{strategy}'. Valid values: {valid_list}",
                context={"testing_strategy": strategy},
            )

    if "test_coverage_target" in fields:
        target = fields["test_coverage_target"]
        if not isinstance(target, int) or not (0 <= target <= 100):
            raise ValidationError(
                message=f"test_coverage_target must be an integer between 0 and 100, got {target!r}",
                context={"test_coverage_target": target},
            )

    # BE-5117: agent-supplied vision summaries (per-doc + aggregate) are
    # validated at the MCP tool boundary BEFORE reaching the service layer.
    # Type, shape, length caps, and doc_id UUID format are enforced here so
    # invalid input produces a clean 422-style ValidationError instead of a
    # DB constraint 500.
    vision_summaries_payload: list[dict] | None = None
    consolidated_vision_payload: dict | None = None
    if "vision_summaries" in fields:
        raw = fields.pop("vision_summaries")
        try:
            vision_summaries_payload = validate_vision_summaries(raw)
        except (PydanticValidationError, TypeError, ValueError) as exc:
            raise ValidationError(
                message=f"Invalid vision_summaries payload: {exc}",
                context={"product_id": product_id},
            ) from exc
    if "consolidated_vision" in fields:
        raw = fields.pop("consolidated_vision")
        try:
            consolidated_vision_payload = validate_consolidated_vision(raw)
        except (PydanticValidationError, TypeError, ValueError) as exc:
            raise ValidationError(
                message=f"Invalid consolidated_vision payload: {exc}",
                context={"product_id": product_id},
            ) from exc

    fields_written: list[str] = []
    fields_skipped: list[dict[str, str]] = []

    async with _session_scope(db_manager, _test_session) as session:
        stmt = (
            select(Product)
            .where(Product.id == product_id, Product.tenant_key == tenant_key)
            .options(
                selectinload(Product.tech_stack),
                selectinload(Product.architecture),
                selectinload(Product.test_config),
                selectinload(Product.vision_documents),
            )
        )
        result = await session.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            raise ResourceNotFoundError(
                f"Product {product_id} not found for tenant",
                context={"product_id": product_id},
            )

        kwargs = _build_update_kwargs(fields, fields_written)

        # -- Route writes through ProductService (the validated single write path) --
        # Track skipped fields explicitly so the agent can see what didn't write
        # and why (instead of having to diff fields_written against their input).
        if kwargs:
            from giljo_mcp.services.product_service import ProductService

            product_service = ProductService(
                db_manager=db_manager,
                tenant_key=tenant_key,
                test_session=_test_session,
            )
            try:
                await product_service.update_product(product_id, force=force, **kwargs)
            except ValidationError as exc:
                # Overwrite-protection error: surface as structured skip rather than raise.
                # ProductService raises with context={"populated_fields": [...]} when
                # JSONB blocks (tech_stack/architecture/test_config) are populated and
                # force=False. Other ValidationError causes still propagate.
                populated = (exc.context or {}).get("populated_fields") if hasattr(exc, "context") else None
                if not populated:
                    raise
                # Roll back fields_written: any field belonging to a skipped block didn't write.
                block_field_map = {
                    "tech_stack": _TECH_STACK_FIELDS,
                    "architecture": _ARCHITECTURE_FIELDS,
                    "test_config": _TEST_CONFIG_FIELDS,
                }
                for block in populated:
                    block_fields = block_field_map.get(block, set())
                    for field_name in list(fields_written):
                        if field_name in block_fields:
                            fields_written.remove(field_name)
                            fields_skipped.append(
                                {
                                    "field": field_name,
                                    "reason": f"{block} already populated",
                                    "hint": "Pass force=True to overwrite.",
                                }
                            )
                # Re-attempt with the skipped blocks stripped out, so non-conflicting
                # fields (other blocks + direct product fields) still write.
                safe_kwargs = {k: v for k, v in kwargs.items() if k not in populated}
                if safe_kwargs:
                    await product_service.update_product(product_id, force=force, **safe_kwargs)

        # -- BE-5117: per-doc vision_summaries + aggregate consolidated_vision --
        # Both payloads are persisted via owning services (VisionDocumentRepository
        # for per-doc, ProductService.update_product for aggregate) so the post-0962
        # owning-service routing rule holds. The completion flag is then re-evaluated
        # inside the same session/transaction.
        if vision_summaries_payload is not None:
            await _write_vision_summaries(
                vision_summaries_payload,
                tenant_key,
                session,
                product_id,
                db_manager,
                fields_written,
            )
        if consolidated_vision_payload is not None:
            await _write_consolidated_vision(
                consolidated_vision_payload,
                tenant_key,
                product_id,
                db_manager,
                _test_session,
                fields_written,
                force=force,
            )
        if vision_summaries_payload is not None or consolidated_vision_payload is not None:
            vision_service = ProductVisionService(
                db_manager=db_manager,
                tenant_key=tenant_key,
                test_session=_test_session,
            )
            await vision_service.evaluate_vision_analysis_complete(session, product_id)

    # WebSocket emission (after commit via context manager)
    if websocket_manager and fields_written:
        from giljo_mcp.events.schemas import EventFactory

        event = EventFactory.tenant_envelope(
            event_type="vision:analysis_complete",
            tenant_key=tenant_key,
            data={
                "product_id": product_id,
                "fields_written": len(fields_written),
                "fields": fields_written,
            },
        )
        await websocket_manager.broadcast_event_to_tenant(tenant_key=tenant_key, event=event)

    return {
        "success": True,
        "fields_written": len(fields_written),
        "fields": fields_written,
        "fields_skipped": fields_skipped,
    }


async def _write_vision_summaries(
    payload: list[dict],
    tenant_key: str,
    session: AsyncSession,
    product_id: str,
    db_manager: DatabaseManager | None,
    fields_written: list[str],
) -> None:
    """Persist agent-supplied per-document light/medium summaries (BE-5117).

    Routes through VisionDocumentRepository (the owning repo for vision
    documents). Per-doc tenant scoping is enforced inside ``update_summaries``.
    Docs that do not belong to this tenant/product are silently skipped --
    the agent learns from ``fields_written`` which docs landed.
    """
    repo = VisionDocumentRepository(db_manager=db_manager)
    landed: list[str] = []
    for entry in payload:
        updated = await repo.update_summaries(
            session=session,
            tenant_key=tenant_key,
            document_id=entry["doc_id"],
            light=entry["light"],
            medium=entry["medium"],
        )
        if updated is not None and str(updated.product_id) == str(product_id):
            landed.append(entry["doc_id"])
        else:
            logger.warning(
                "vision_summaries.skip: doc_id=%s not found for tenant or product mismatch",
                entry["doc_id"],
            )
    if landed:
        fields_written.append("vision_summaries")


async def _write_consolidated_vision(
    payload: dict,
    tenant_key: str,
    product_id: str,
    db_manager: DatabaseManager | None,
    test_session: AsyncSession | None,
    fields_written: list[str],
    *,
    force: bool,
) -> None:
    """Persist agent-supplied aggregate consolidated_vision via ProductService."""
    from giljo_mcp.services.product_service import ProductService

    product_service = ProductService(
        db_manager=db_manager,
        tenant_key=tenant_key,
        test_session=test_session,
    )
    light = payload["light"]
    medium = payload["medium"]
    await product_service.update_product(
        product_id,
        force=force,
        consolidated_vision_light=light,
        consolidated_vision_light_tokens=len(light.split()),
        consolidated_vision_medium=medium,
        consolidated_vision_medium_tokens=len(medium.split()),
    )
    fields_written.append("consolidated_vision")
