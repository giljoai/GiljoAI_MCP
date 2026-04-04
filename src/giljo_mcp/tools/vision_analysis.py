"""
MCP Tools: gil_get_vision_doc and gil_write_product (Handover 0842c)

Provides vision document retrieval with extraction prompt and structured
product field writing from AI analysis results.

Called by the user's AI coding agent during vision document analysis workflow.
"""

import logging
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import ResourceNotFoundError
from src.giljo_mcp.models.context import MCPContextIndex
from src.giljo_mcp.models.products import (
    Product,
    ProductArchitecture,
    ProductTechStack,
    ProductTestConfig,
)
from src.giljo_mcp.repositories.vision_document_repository import VisionDocumentRepository


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
- For summaries: preserve technical specs, architecture decisions, and constraints
- For summaries: remove marketing prose, user personas, and storytelling

After reading ALL chunks, call the gil_write_product tool with all fields you were
able to extract. Include summary_33 (concise ~33% executive summary focusing on what
a developer needs to build this) and summary_66 (thorough ~66% technical summary
preserving decisions, architecture, and feature descriptions).

{custom_instructions}"""


# CROSS-REFERENCE: Two independent code paths write to these product fields.
# If you modify fields here, you MUST also check the tuning writer:
#   ProductTuningService._apply_value_to_product() in
#   src/giljo_mcp/services/product_tuning_service.py (SECTION_FIELD_MAP, line ~36)
# The tuning path writes one field at a time (per-section accept).
# This path writes in bulk with merge semantics.
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

# Group field names by target table for dispatch
_PRODUCT_FIELDS = {k for k, (t, _) in FIELD_MAP.items() if t == "products"}
_TECH_STACK_FIELDS = {k for k, (t, _) in FIELD_MAP.items() if t == "tech_stack"}
_ARCHITECTURE_FIELDS = {k for k, (t, _) in FIELD_MAP.items() if t == "architecture"}
_TEST_CONFIG_FIELDS = {k for k, (t, _) in FIELD_MAP.items() if t == "test_config"}
_SUMMARY_FIELDS = {"summary_33", "summary_66"}


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


async def gil_get_vision_doc(
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

        active_docs = [doc for doc in product.vision_documents if doc.is_active]

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
            # Fallback: document exists but hasn't been chunked yet — use raw content
            logger.warning("No chunks found for product %s, falling back to raw document", product_id)
            raw_content = "\n\n".join(doc.vision_document or "" for doc in active_docs if doc.vision_document)
            raw_chunks = [raw_content]
        else:
            raw_chunks = [c.content for c in all_chunks]

        # Sub-split any chunks >25K chars so each fits within MCP tool output limits
        max_chars = 25000
        chunk_list = []
        for raw in raw_chunks:
            if len(raw) <= max_chars:
                chunk_list.append(raw)
            else:
                # Split on paragraph boundaries where possible
                for i in range(0, len(raw), max_chars):
                    segment = raw[i : i + max_chars]
                    chunk_list.append(segment)

        chunk_list = [
            {"chunk_order": i + 1, "content": c, "token_count": len(c.split())} for i, c in enumerate(chunk_list)
        ]

        total_chunks = len(chunk_list)
        total_tokens = sum(c["token_count"] for c in chunk_list)

        custom_instructions = product.extraction_custom_instructions or ""
        extraction_instructions = VISION_EXTRACTION_PROMPT.replace("{custom_instructions}", custom_instructions)

        base = {
            "total_chunks": total_chunks,
            "total_tokens": total_tokens,
            "extraction_instructions": extraction_instructions,
            "write_tool": "gil_write_product",
            "product_id": product_id,
            "product_name": product.name,
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
            base["content"] = selected["content"]
            base["chunk_token_count"] = selected["token_count"]
        else:
            # Metadata only — no content, agent should request chunks individually
            base["usage"] = f"Call again with chunk=1 through chunk={total_chunks} to retrieve content"

        # Notify frontend that the agent has connected and started analysis
        if websocket_manager and chunk is None:
            from api.events.schemas import EventFactory

            event = EventFactory.tenant_envelope(
                event_type="vision:analysis_started",
                tenant_key=tenant_key,
                data={"product_id": product_id, "total_chunks": total_chunks},
            )
            await websocket_manager.broadcast_event_to_tenant(tenant_key=tenant_key, event=event)

        return base


async def gil_write_product(
    product_id: str,
    tenant_key: str,
    db_manager: DatabaseManager | None = None,
    websocket_manager: Any = None,
    _test_session: AsyncSession | None = None,
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

    fields_written: list[str] = []

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

        # -- Product direct fields --
        _write_product_fields(product, fields, fields_written)

        # -- Tech stack fields (get-or-create, merge-update) --
        _write_tech_stack_fields(product, tenant_key, session, fields, fields_written)

        # -- Architecture fields (get-or-create, merge-update) --
        _write_architecture_fields(product, tenant_key, session, fields, fields_written)

        # -- Test config fields (get-or-create, merge-update) --
        _write_test_config_fields(product, tenant_key, session, fields, fields_written)

        # -- Summaries --
        await _write_summaries(product, tenant_key, session, fields, fields_written, db_manager)

        await session.flush()

    # WebSocket emission (after commit via context manager)
    if websocket_manager and fields_written:
        from api.events.schemas import EventFactory

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
    }


def _write_product_fields(
    product: Product,
    fields: dict[str, Any],
    fields_written: list[str],
) -> None:
    """Apply direct product fields (name, description, core_features, target_platforms)."""
    # See CROSS-REFERENCE note on FIELD_MAP — tuning also writes these fields.
    for field_name in _PRODUCT_FIELDS:
        if field_name not in fields:
            continue
        _, column_name = FIELD_MAP[field_name]
        setattr(product, column_name, fields[field_name])
        fields_written.append(field_name)


def _write_tech_stack_fields(
    product: Product,
    tenant_key: str,
    session: Any,
    fields: dict[str, Any],
    fields_written: list[str],
) -> None:
    """Get-or-create ProductTechStack and merge-update only provided fields."""
    # See CROSS-REFERENCE note on FIELD_MAP — tuning also writes these fields.
    provided = {k: fields[k] for k in _TECH_STACK_FIELDS if k in fields}
    if not provided:
        return

    tech_stack = product.tech_stack
    if not tech_stack:
        tech_stack = ProductTechStack(
            product_id=product.id,
            tenant_key=tenant_key,
        )
        session.add(tech_stack)
        product.tech_stack = tech_stack

    for field_name, value in provided.items():
        _, column_name = FIELD_MAP[field_name]
        setattr(tech_stack, column_name, value)
        fields_written.append(field_name)


def _write_architecture_fields(
    product: Product,
    tenant_key: str,
    session: Any,
    fields: dict[str, Any],
    fields_written: list[str],
) -> None:
    """Get-or-create ProductArchitecture and merge-update only provided fields."""
    # See CROSS-REFERENCE note on FIELD_MAP — tuning also writes these fields.
    provided = {k: fields[k] for k in _ARCHITECTURE_FIELDS if k in fields}
    if not provided:
        return

    arch = product.architecture
    if not arch:
        arch = ProductArchitecture(
            product_id=product.id,
            tenant_key=tenant_key,
        )
        session.add(arch)
        product.architecture = arch

    for field_name, value in provided.items():
        _, column_name = FIELD_MAP[field_name]
        setattr(arch, column_name, value)
        fields_written.append(field_name)


def _write_test_config_fields(
    product: Product,
    tenant_key: str,
    session: Any,
    fields: dict[str, Any],
    fields_written: list[str],
) -> None:
    """Get-or-create ProductTestConfig and merge-update only provided fields."""
    # See CROSS-REFERENCE note on FIELD_MAP — tuning also writes these fields.
    provided = {k: fields[k] for k in _TEST_CONFIG_FIELDS if k in fields}
    if not provided:
        return

    test_cfg = product.test_config
    if not test_cfg:
        test_cfg = ProductTestConfig(
            product_id=product.id,
            tenant_key=tenant_key,
        )
        session.add(test_cfg)
        product.test_config = test_cfg

    for field_name, value in provided.items():
        _, column_name = FIELD_MAP[field_name]
        setattr(test_cfg, column_name, value)
        fields_written.append(field_name)


async def _write_summaries(
    product: Product,
    tenant_key: str,
    session: Any,
    fields: dict[str, Any],
    fields_written: list[str],
    db_manager: DatabaseManager,
) -> None:
    """Write summary_33 and summary_66 to vision_document_summaries table."""
    summary_33 = fields.get("summary_33")
    summary_66 = fields.get("summary_66")

    if not summary_33 and not summary_66:
        return

    active_docs = [doc for doc in product.vision_documents if doc.is_active]
    if not active_docs:
        logger.warning(
            "Cannot write summaries: no active vision documents for product %s",
            product.id,
        )
        return

    first_doc = active_docs[0]
    repo = VisionDocumentRepository(db_manager)

    if summary_33:
        token_count = len(summary_33.split())
        await repo.create_summary(
            session=session,
            tenant_key=tenant_key,
            document_id=str(first_doc.id),
            product_id=str(product.id),
            source="ai",
            ratio=Decimal("0.33"),
            summary=summary_33,
            tokens_original=token_count,
            tokens_summary=token_count,
        )
        fields_written.append("summary_33")

    if summary_66:
        token_count = len(summary_66.split())
        await repo.create_summary(
            session=session,
            tenant_key=tenant_key,
            document_id=str(first_doc.id),
            product_id=str(product.id),
            source="ai",
            ratio=Decimal("0.66"),
            summary=summary_66,
            tokens_original=token_count,
            tokens_summary=token_count,
        )
        fields_written.append("summary_66")
