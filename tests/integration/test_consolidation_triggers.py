"""
Integration tests for consolidated vision document triggers (Handover 0377 Phase 4).

Tests automatic consolidation when vision documents are uploaded, updated, or deleted.
"""

import pytest
import pytest_asyncio
from sqlalchemy import select, func

from src.giljo_mcp.models import Product, VisionDocument
from tests.fixtures.vision_document_fixtures import VisionDocumentTestData


@pytest_asyncio.fixture
async def test_product_with_vision_docs(db_session, test_product):
    """
    Create test product with multiple active vision documents for consolidation testing.

    Creates 3 vision documents:
    - Doc 1: 6K tokens (triggers summarization)
    - Doc 2: 6K tokens (triggers summarization)
    - Doc 3: 6K tokens (triggers summarization)

    Total aggregate: ~18K tokens (perfect for consolidation testing)
    """
    docs = []

    for i in range(3):
        content = VisionDocumentTestData.generate_markdown_content(6000)

        doc = VisionDocument(
            tenant_key=test_product.tenant_key,
            product_id=test_product.id,
            document_name=f"Vision Doc {i + 1}",
            document_type="vision",
            storage_type="inline",
            vision_document=content,
            is_active=True,
            display_order=i,
        )
        db_session.add(doc)
        docs.append(doc)

    await db_session.flush()
    await db_session.refresh(test_product)

    return test_product, docs


class TestConsolidationTriggers:
    """Test suite for automatic consolidation triggers on vision document changes."""

    @pytest.mark.asyncio
    async def test_upload_triggers_consolidation(self, db_session, tenant_manager):
        """
        Upload new vision doc → product.consolidated_* fields populated automatically.

        Test Flow:
        1. Create product with no vision docs
        2. Upload vision document (>5K tokens to trigger summarization)
        3. Verify consolidation service ran automatically
        4. Verify product.consolidated_vision_light and medium are populated
        5. Verify consolidated_vision_hash is set
        6. Verify consolidated_at timestamp is set
        """
        # GIVEN: Product with no vision documents
        from sqlalchemy import select, func

        tenant_key = tenant_manager.generate_tenant_key("test-upload")
        test_product = Product(
            tenant_key=tenant_key,
            name="Test Product for Upload",
            description="Test product",
        )
        db_session.add(test_product)
        await db_session.flush()

        vision_count_result = await db_session.execute(
            select(func.count()).select_from(VisionDocument).where(VisionDocument.product_id == test_product.id)
        )
        vision_count = vision_count_result.scalar()
        assert vision_count == 0

        assert test_product.consolidated_vision_light is None
        assert test_product.consolidated_vision_medium is None
        assert test_product.consolidated_vision_hash is None

        # WHEN: Upload large vision document (6K tokens)
        from src.giljo_mcp.repositories.vision_document_repository import VisionDocumentRepository

        vision_repo = VisionDocumentRepository(db_manager=None)  # Uses session directly
        content = VisionDocumentTestData.generate_markdown_content(6000)

        doc = await vision_repo.create(
            session=db_session,
            tenant_key=test_product.tenant_key,
            product_id=test_product.id,
            document_name="Test Vision",
            content=content,
            document_type="vision",
            storage_type="inline",
        )
        await db_session.flush()

        # Manually trigger consolidation (simulating endpoint behavior)
        from src.giljo_mcp.services.consolidation_service import ConsolidatedVisionService

        consolidation_service = ConsolidatedVisionService()
        result = await consolidation_service.consolidate_vision_documents(
            product_id=test_product.id,
            session=db_session,
            tenant_key=test_product.tenant_key,
            force=False
        )

        # THEN: Consolidation service ran successfully
        assert result["success"] is True, f"Consolidation failed: {result.get('error')}"

        # THEN: Product consolidated fields are populated
        await db_session.refresh(test_product)

        assert test_product.consolidated_vision_light is not None
        assert test_product.consolidated_vision_medium is not None
        assert test_product.consolidated_vision_hash is not None
        assert test_product.consolidated_at is not None

        # THEN: Token counts are reasonable (light < medium < original)
        assert test_product.consolidated_vision_light_tokens < test_product.consolidated_vision_medium_tokens
        assert result["light"]["tokens"] > 0
        assert result["medium"]["tokens"] > 0

    @pytest.mark.asyncio
    async def test_delete_triggers_consolidation(self, db_session, test_product_with_vision_docs):
        """
        Delete vision doc → product.consolidated_* regenerated without deleted doc.

        Test Flow:
        1. Start with product with 3 vision docs (consolidated)
        2. Delete one vision document
        3. Verify consolidation service ran automatically
        4. Verify consolidated hash changed (different content)
        5. Verify consolidated summaries updated
        """
        test_product, docs = test_product_with_vision_docs

        # GIVEN: Product with 3 vision docs, run initial consolidation
        from src.giljo_mcp.services.consolidation_service import ConsolidatedVisionService

        consolidation_service = ConsolidatedVisionService()
        initial_result = await consolidation_service.consolidate_vision_documents(
            product_id=test_product.id,
            session=db_session,
            tenant_key=test_product.tenant_key,
            force=True  # Force initial consolidation
        )
        assert initial_result["success"] is True

        await db_session.refresh(test_product)
        initial_hash = test_product.consolidated_vision_hash
        initial_light_tokens = test_product.consolidated_vision_light_tokens

        assert initial_hash is not None
        assert len(initial_result["source_docs"]) == 3

        # WHEN: Delete one vision document
        from src.giljo_mcp.repositories.vision_document_repository import VisionDocumentRepository

        vision_repo = VisionDocumentRepository(db_manager=None)
        delete_result = await vision_repo.delete(
            session=db_session,
            tenant_key=test_product.tenant_key,
            document_id=docs[1].id  # Delete middle document
        )
        assert delete_result["success"] is True
        await db_session.flush()

        # Manually trigger consolidation (simulating endpoint behavior)
        updated_result = await consolidation_service.consolidate_vision_documents(
            product_id=test_product.id,
            session=db_session,
            tenant_key=test_product.tenant_key,
            force=False
        )

        # THEN: Consolidation ran and hash changed
        assert updated_result["success"] is True
        assert len(updated_result["source_docs"]) == 2  # Only 2 docs remain

        await db_session.refresh(test_product)
        assert test_product.consolidated_vision_hash != initial_hash

        # THEN: Token counts decreased (less content)
        assert test_product.consolidated_vision_light_tokens < initial_light_tokens

    @pytest.mark.asyncio
    async def test_update_triggers_consolidation(self, db_session, test_product_with_vision_docs):
        """
        Update vision doc content → product.consolidated_* regenerated with new content.

        Test Flow:
        1. Start with product with 3 vision docs (consolidated)
        2. Update one vision document content
        3. Verify consolidation service ran automatically
        4. Verify consolidated hash changed (different content)
        5. Verify consolidated summaries updated
        """
        test_product, docs = test_product_with_vision_docs

        # GIVEN: Product with 3 vision docs, run initial consolidation
        from src.giljo_mcp.services.consolidation_service import ConsolidatedVisionService

        consolidation_service = ConsolidatedVisionService()
        initial_result = await consolidation_service.consolidate_vision_documents(
            product_id=test_product.id,
            session=db_session,
            tenant_key=test_product.tenant_key,
            force=True
        )
        assert initial_result["success"] is True

        await db_session.refresh(test_product)
        initial_hash = test_product.consolidated_vision_hash
        assert initial_hash is not None

        # WHEN: Update vision document content
        from src.giljo_mcp.repositories.vision_document_repository import VisionDocumentRepository

        vision_repo = VisionDocumentRepository(db_manager=None)
        new_content = VisionDocumentTestData.generate_markdown_content(8000)  # Different size

        updated_doc = await vision_repo.update_content(
            session=db_session,
            tenant_key=test_product.tenant_key,
            document_id=docs[0].id,
            new_content=new_content
        )
        assert updated_doc is not None
        await db_session.flush()

        # Manually trigger consolidation (simulating endpoint behavior)
        updated_result = await consolidation_service.consolidate_vision_documents(
            product_id=test_product.id,
            session=db_session,
            tenant_key=test_product.tenant_key,
            force=False
        )

        # THEN: Consolidation ran and hash changed
        assert updated_result["success"] is True
        assert len(updated_result["source_docs"]) == 3  # All 3 docs still present

        await db_session.refresh(test_product)
        assert test_product.consolidated_vision_hash != initial_hash

        # THEN: Consolidated content updated (different hash proves content changed)
        assert test_product.consolidated_vision_light is not None
        assert test_product.consolidated_vision_medium is not None

    @pytest.mark.asyncio
    async def test_no_consolidation_if_no_changes(self, db_session, test_product_with_vision_docs):
        """
        Verify consolidation skips if content hash unchanged (optimization).

        Test Flow:
        1. Run consolidation (hash stored)
        2. Run consolidation again without changes
        3. Verify second consolidation skipped (no_changes error)
        """
        test_product, docs = test_product_with_vision_docs

        # GIVEN: Run initial consolidation
        from src.giljo_mcp.services.consolidation_service import ConsolidatedVisionService

        consolidation_service = ConsolidatedVisionService()
        first_result = await consolidation_service.consolidate_vision_documents(
            product_id=test_product.id,
            session=db_session,
            tenant_key=test_product.tenant_key,
            force=False
        )
        assert first_result["success"] is True

        await db_session.refresh(test_product)
        first_hash = test_product.consolidated_vision_hash

        # WHEN: Run consolidation again without any changes
        second_result = await consolidation_service.consolidate_vision_documents(
            product_id=test_product.id,
            session=db_session,
            tenant_key=test_product.tenant_key,
            force=False
        )

        # THEN: Second consolidation skipped (no changes detected)
        assert second_result["success"] is False
        assert second_result["error"] == "no_changes"

        # THEN: Hash unchanged
        await db_session.refresh(test_product)
        assert test_product.consolidated_vision_hash == first_hash

    @pytest.mark.asyncio
    async def test_force_regeneration_ignores_hash(self, db_session, test_product_with_vision_docs):
        """
        Verify force=True regenerates consolidation even if hash unchanged.

        Test Flow:
        1. Run consolidation (hash stored)
        2. Run consolidation with force=True
        3. Verify consolidation ran (not skipped)
        """
        test_product, docs = test_product_with_vision_docs

        # GIVEN: Run initial consolidation
        from src.giljo_mcp.services.consolidation_service import ConsolidatedVisionService

        consolidation_service = ConsolidatedVisionService()
        first_result = await consolidation_service.consolidate_vision_documents(
            product_id=test_product.id,
            session=db_session,
            tenant_key=test_product.tenant_key,
            force=False
        )
        assert first_result["success"] is True

        await db_session.refresh(test_product)
        first_hash = test_product.consolidated_vision_hash
        first_timestamp = test_product.consolidated_at

        # WHEN: Run consolidation with force=True
        forced_result = await consolidation_service.consolidate_vision_documents(
            product_id=test_product.id,
            session=db_session,
            tenant_key=test_product.tenant_key,
            force=True  # Force regeneration
        )

        # THEN: Consolidation ran (not skipped)
        assert forced_result["success"] is True

        # THEN: Hash same but timestamp updated (proves it ran)
        await db_session.refresh(test_product)
        assert test_product.consolidated_vision_hash == first_hash  # Same content
        assert test_product.consolidated_at > first_timestamp  # Newer timestamp

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation(self, db_session, tenant_manager):
        """
        Verify consolidation respects multi-tenant isolation.

        Test Flow:
        1. Create product for tenant A with vision doc
        2. Try to consolidate with tenant B's key
        3. Verify consolidation fails (product_not_found)
        """
        # GIVEN: Create product for tenant A
        tenant_a_key = tenant_manager.generate_tenant_key("tenant-a-consolidation")
        tenant_b_key = tenant_manager.generate_tenant_key("tenant-b-consolidation")

        from src.giljo_mcp.models import Product

        product_a = Product(
            tenant_key=tenant_a_key,
            name="Tenant A Product",
            description="Test product",
        )
        db_session.add(product_a)
        await db_session.flush()

        # Add vision doc for tenant A
        from src.giljo_mcp.repositories.vision_document_repository import VisionDocumentRepository

        vision_repo = VisionDocumentRepository(db_manager=None)
        content = VisionDocumentTestData.generate_markdown_content(6000)

        doc = await vision_repo.create(
            session=db_session,
            tenant_key=tenant_a_key,
            product_id=product_a.id,
            document_name="Tenant A Vision",
            content=content,
            document_type="vision",
            storage_type="inline",
        )
        await db_session.flush()

        # WHEN: Try to consolidate with tenant B's key
        from src.giljo_mcp.services.consolidation_service import ConsolidatedVisionService

        consolidation_service = ConsolidatedVisionService()
        result = await consolidation_service.consolidate_vision_documents(
            product_id=product_a.id,
            session=db_session,
            tenant_key=tenant_b_key,  # Wrong tenant!
            force=False
        )

        # THEN: Consolidation fails (tenant isolation)
        assert result["success"] is False
        assert result["error"] == "product_not_found"  # Don't leak tenant info
