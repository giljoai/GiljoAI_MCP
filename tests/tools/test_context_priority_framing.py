from uuid import uuid4

import pytest

from src.giljo_mcp.models.auth import User
from src.giljo_mcp.models.context import MCPContextIndex
from src.giljo_mcp.models.products import Product, VisionDocument
from src.giljo_mcp.tools.context_tools.framing_helpers import (
    build_framed_context_response,
    get_user_priority,
    inject_priority_framing,
)
from src.giljo_mcp.tools.context_tools.get_product_context import get_product_context
from src.giljo_mcp.tools.context_tools.get_vision_document import get_vision_document


def test_inject_priority_framing_critical():
    framed = inject_priority_framing("Important content", 1, "product_core")

    assert "## CRITICAL: Product Core" in framed
    assert framed.count("## CRITICAL") >= 2
    assert "Important content" in framed


def test_inject_priority_framing_exclude():
    framed = inject_priority_framing("Skip me", 4, "git_history")

    assert framed == ""


@pytest.mark.asyncio
async def test_get_user_priority(db_session, db_manager):
    tenant_key = "tenant_priority"
    username = f"priority_user_{uuid4().hex[:6]}"
    user = User(
        id=str(uuid4()),
        username=username,
        tenant_key=tenant_key,
        field_priority_config={"version": "2.0", "priorities": {"product_core": 2}},
    )
    async with db_manager.get_session_async() as session:
        session.add(user)
        await session.commit()

    priority = await get_user_priority("product_core", tenant_key, user.id, db_manager)

    assert priority == 2


@pytest.mark.asyncio
async def test_product_context_includes_framing(db_session, db_manager):
    tenant_key = "tenant_product"
    product = Product(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name="Framed Product",
        description="Framing description",
    )
    async with db_manager.get_session_async() as session:
        session.add(product)
        await session.commit()

    raw = await get_product_context(product.id, tenant_key, False, db_manager)
    framed = await build_framed_context_response(raw, "product_core", tenant_key, None, db_manager)

    assert framed["metadata"]["priority"] == 1
    assert "## CRITICAL" in framed["framed_content"]
    assert "Framed Product" in framed["framed_content"]


@pytest.mark.asyncio
async def test_vision_document_includes_framing(db_session, db_manager):
    tenant_key = "tenant_vision"
    product = Product(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name="Vision Product",
        description="Vision description",
    )
    vision_doc = VisionDocument(
        id=str(uuid4()),
        tenant_key=tenant_key,
        product_id=product.id,
        document_name="Primary Vision",
        document_type="vision",
        storage_type="inline",
        vision_document="Full vision content",
        chunked=True,
        chunk_count=1,
        is_active=True,
        display_order=0,
    )
    chunk = MCPContextIndex(
        tenant_key=tenant_key,
        product_id=product.id,
        vision_document_id=vision_doc.id,
        content="Chunked vision context",
        chunk_order=1,
    )
    product.vision_documents.append(vision_doc)

    async with db_manager.get_session_async() as session:
        session.add_all([product, vision_doc, chunk])
        await session.commit()

    raw = await get_vision_document(product.id, tenant_key, "light", 0, None, db_manager)
    framed = await build_framed_context_response(raw, "vision_documents", tenant_key, None, db_manager)

    assert framed["metadata"]["priority"] == 2
    assert "## IMPORTANT" in framed["framed_content"]
    assert "Chunked vision context" in framed["framed_content"]
