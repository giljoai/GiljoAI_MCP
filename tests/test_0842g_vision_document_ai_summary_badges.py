from decimal import Decimal

import pytest

from api.endpoints import vision_documents as vision_document_endpoints
from src.giljo_mcp.models import Product
from src.giljo_mcp.repositories.vision_document_repository import VisionDocumentRepository


@pytest.mark.asyncio
async def test_list_vision_documents_includes_ai_summary_badge_metadata(db_session, db_manager, test_tenant_key):
    product = Product(
        name="AI Summary Product",
        description="Product for AI summary badge metadata",
        tenant_key=test_tenant_key,
        is_active=True,
        product_memory={},
    )
    db_session.add(product)
    await db_session.flush()

    repo = VisionDocumentRepository(db_manager)
    document = await repo.create(
        session=db_session,
        tenant_key=test_tenant_key,
        product_id=product.id,
        document_name="product_vision_v2.md",
        content="Vision content for AI summary metadata test.",
        storage_type="inline",
        file_size=1024,
    )
    await repo.create_summary(
        session=db_session,
        tenant_key=test_tenant_key,
        document_id=document.id,
        product_id=product.id,
        source="ai",
        ratio=Decimal("0.33"),
        summary="AI light summary",
        tokens_original=12600,
        tokens_summary=4200,
    )
    await repo.create_summary(
        session=db_session,
        tenant_key=test_tenant_key,
        document_id=document.id,
        product_id=product.id,
        source="ai",
        ratio=Decimal("0.66"),
        summary="AI medium summary",
        tokens_original=12600,
        tokens_summary=10800,
    )
    await db_session.commit()

    response = await vision_document_endpoints.list_vision_documents(
        product_id=product.id,
        active_only=True,
        current_user=None,
        db=db_session,
        tenant_key=test_tenant_key,
        vision_repo=repo,
    )

    assert len(response) == 1
    assert response[0].has_ai_summaries is True
    assert response[0].ai_summary_light_tokens == 4200
    assert response[0].ai_summary_medium_tokens == 10800


@pytest.mark.asyncio
async def test_get_vision_document_includes_ai_summary_badge_metadata(db_session, db_manager, test_tenant_key):
    product = Product(
        name="AI Summary Product",
        description="Product for AI summary badge metadata",
        tenant_key=test_tenant_key,
        is_active=True,
        product_memory={},
    )
    db_session.add(product)
    await db_session.flush()

    repo = VisionDocumentRepository(db_manager)
    document = await repo.create(
        session=db_session,
        tenant_key=test_tenant_key,
        product_id=product.id,
        document_name="product_vision_v2.md",
        content="Vision content for AI summary metadata test.",
        storage_type="inline",
        file_size=1024,
    )
    await repo.create_summary(
        session=db_session,
        tenant_key=test_tenant_key,
        document_id=document.id,
        product_id=product.id,
        source="ai",
        ratio=Decimal("0.33"),
        summary="AI light summary",
        tokens_original=12600,
        tokens_summary=4200,
    )
    await repo.create_summary(
        session=db_session,
        tenant_key=test_tenant_key,
        document_id=document.id,
        product_id=product.id,
        source="ai",
        ratio=Decimal("0.66"),
        summary="AI medium summary",
        tokens_original=12600,
        tokens_summary=10800,
    )
    await db_session.commit()

    response = await vision_document_endpoints.get_vision_document(
        document_id=document.id,
        current_user=None,
        db=db_session,
        tenant_key=test_tenant_key,
        vision_repo=repo,
    )

    assert response.has_ai_summaries is True
    assert response.ai_summary_light_tokens == 4200
    assert response.ai_summary_medium_tokens == 10800
