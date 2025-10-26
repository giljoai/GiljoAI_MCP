"""
Tests for Vision Document File Size Tracking Feature.

Test-driven development: These tests define expected behavior BEFORE implementation.
Tests should initially FAIL until implementation is complete.

Feature Requirements:
1. Store file_size (bytes) in VisionDocument model
2. Calculate file_size during upload
3. Return file_size in API responses
4. Display individual file sizes in ProductsView.vue
5. Display aggregate stats in product details dialog
"""

import pytest
from datetime import datetime, timezone
from pathlib import Path
import hashlib
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.giljo_mcp.models import VisionDocument, Product
from src.giljo_mcp.repositories.vision_document_repository import VisionDocumentRepository


@pytest.fixture
def test_tenant_key():
    """Generate test tenant key."""
    return f"test-tenant-{uuid4()}"


@pytest.fixture
def vision_repo(db_manager):
    """Create VisionDocumentRepository instance"""
    return VisionDocumentRepository(db_manager)


@pytest.fixture
def test_product_file_size(db_session, test_tenant_key):
    """Create a test product for file size tests"""
    product = Product(
        id="test_product_file_size",
        tenant_key=test_tenant_key,
        name="Test Product for File Size",
        description="Product for testing file size tracking"
    )
    db_session.add(product)
    db_session.commit()
    return product


@pytest.fixture
def sample_vision_content_small():
    """Small vision document content (~500 bytes)"""
    return """# Product Vision: AI Agent

## Overview
This product enables agent coordination.

## Features
- Agent spawning
- Real-time messaging
- Task management
"""


@pytest.fixture
def sample_vision_content_large():
    """Large vision document content (~5KB)"""
    content = "# Large Vision Document\n\n"
    for i in range(100):
        content += f"## Section {i}\n"
        content += "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 10
        content += "\n\n"
    return content


class TestVisionDocumentFileSizeModel:
    """Test file_size field in VisionDocument model"""

    def test_vision_document_model_has_file_size_field(self, db_session, test_tenant_key, test_product_file_size):
        """Test that VisionDocument model has file_size field"""
        doc = VisionDocument(
            id="test_doc_size_001",
            tenant_key=test_tenant_key,
            product_id=test_product_file_size.id,
            document_name="Test Document",
            vision_document="Test content",
            storage_type="inline",
            file_size=12  # bytes
        )
        db_session.add(doc)
        db_session.commit()

        # Verify file_size field exists and is stored correctly
        assert hasattr(doc, 'file_size')
        assert doc.file_size == 12

    def test_file_size_can_be_null(self, db_session, test_tenant_key, test_product_file_size):
        """Test that file_size can be NULL (for inline content with no file)"""
        doc = VisionDocument(
            id="test_doc_size_002",
            tenant_key=test_tenant_key,
            product_id=test_product_file_size.id,
            document_name="Test Document",
            vision_document="Test content",
            storage_type="inline",
            file_size=None
        )
        db_session.add(doc)
        db_session.commit()

        assert doc.file_size is None

    def test_file_size_defaults_to_null(self, db_session, test_tenant_key, test_product_file_size):
        """Test that file_size defaults to NULL if not specified"""
        doc = VisionDocument(
            id="test_doc_size_003",
            tenant_key=test_tenant_key,
            product_id=test_product_file_size.id,
            document_name="Test Document",
            vision_document="Test content",
            storage_type="inline"
        )
        db_session.add(doc)
        db_session.commit()

        # Should default to NULL
        assert doc.file_size is None


class TestVisionDocumentRepositoryFileSize:
    """Test VisionDocumentRepository file size handling"""

    def test_create_with_file_size(self, db_session, vision_repo, test_tenant_key, test_product_file_size, sample_vision_content_small):
        """Test creating vision document with file_size specified"""
        file_size = len(sample_vision_content_small.encode('utf-8'))

        doc = vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product_file_size.id,
            document_name="Small Vision",
            content=sample_vision_content_small,
            document_type="vision",
            storage_type="inline",
            file_size=file_size
        )

        assert doc is not None
        assert doc.file_size == file_size
        assert doc.file_size > 0

    def test_create_with_large_file_size(self, db_session, vision_repo, test_tenant_key, test_product_file_size, sample_vision_content_large):
        """Test creating vision document with larger file_size"""
        file_size = len(sample_vision_content_large.encode('utf-8'))

        doc = vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product_file_size.id,
            document_name="Large Vision",
            content=sample_vision_content_large,
            document_type="architecture",
            storage_type="inline",
            file_size=file_size
        )

        assert doc is not None
        assert doc.file_size == file_size
        assert doc.file_size > 1000  # Should be > 1KB

    def test_list_by_product_includes_file_size(self, db_session, vision_repo, test_tenant_key, test_product_file_size):
        """Test that list_by_product returns file_size in results"""
        # Create multiple documents with different sizes
        doc1 = vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product_file_size.id,
            document_name="Doc 1",
            content="Small content",
            storage_type="inline",
            file_size=100
        )

        doc2 = vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product_file_size.id,
            document_name="Doc 2",
            content="Larger content here",
            storage_type="inline",
            file_size=500
        )

        # List documents
        docs = vision_repo.list_by_product(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product_file_size.id
        )

        assert len(docs) >= 2
        doc1_result = next((d for d in docs if d.id == doc1.id), None)
        doc2_result = next((d for d in docs if d.id == doc2.id), None)

        assert doc1_result is not None
        assert doc1_result.file_size == 100
        assert doc2_result is not None
        assert doc2_result.file_size == 500


class TestVisionDocumentAPIFileSize:
    """Test API endpoints return file_size correctly"""

    def test_vision_document_response_schema_includes_file_size(self):
        """Test that VisionDocumentResponse schema includes file_size field"""
        from api.schemas.vision_document import VisionDocumentResponse
        from pydantic import BaseModel

        # Check schema has file_size field
        assert hasattr(VisionDocumentResponse, 'model_fields')
        fields = VisionDocumentResponse.model_fields
        assert 'file_size' in fields


class TestFileSizeCalculation:
    """Test file size calculation logic"""

    def test_calculate_file_size_from_string(self, sample_vision_content_small):
        """Test calculating file size from string content"""
        content = sample_vision_content_small
        expected_size = len(content.encode('utf-8'))

        assert expected_size > 0
        assert expected_size == len(content.encode('utf-8'))

    def test_calculate_file_size_unicode(self):
        """Test calculating file size with unicode characters"""
        content = "Hello 世界 🌍"  # Mixed ASCII, Chinese, emoji
        size = len(content.encode('utf-8'))

        # Unicode characters take more than 1 byte
        assert size > len(content)  # More bytes than characters

    def test_calculate_file_size_empty_string(self):
        """Test calculating file size for empty content"""
        content = ""
        size = len(content.encode('utf-8'))
        assert size == 0

    def test_calculate_file_size_from_file(self, tmp_path, sample_vision_content_large):
        """Test calculating file size from actual file"""
        # Create temporary file
        vision_file = tmp_path / "vision.md"
        vision_file.write_text(sample_vision_content_large, encoding="utf-8")

        # Get file size
        file_size = vision_file.stat().st_size
        expected_size = len(sample_vision_content_large.encode('utf-8'))

        assert file_size == expected_size
        assert file_size > 1000  # Should be > 1KB


class TestFileSizeEdgeCases:
    """Test edge cases for file size handling"""

    def test_file_size_zero_for_empty_content(self, db_session, vision_repo, test_tenant_key, test_product_file_size):
        """Test that empty content results in file_size=0"""
        doc = vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product_file_size.id,
            document_name="Empty Document",
            content="",
            storage_type="inline",
            file_size=0
        )

        assert doc.file_size == 0

    def test_file_size_null_for_inline_without_file(self, db_session, vision_repo, test_tenant_key, test_product_file_size):
        """Test that inline content without original file can have NULL file_size"""
        doc = vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product_file_size.id,
            document_name="Inline Document",
            content="Direct input content",
            storage_type="inline",
            file_size=None  # No original file
        )

        assert doc.file_size is None

    def test_file_size_for_large_file(self, db_session, vision_repo, test_tenant_key, test_product_file_size):
        """Test handling of large file sizes (e.g., 10MB)"""
        large_size = 10 * 1024 * 1024  # 10 MB

        doc = vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product_file_size.id,
            document_name="Large Document",
            content="Large content...",
            storage_type="file",
            file_size=large_size
        )

        assert doc.file_size == large_size


class TestAggregateFileSizeStats:
    """Test aggregate file size statistics for product details"""

    def test_calculate_total_file_size(self, db_session, vision_repo, test_tenant_key, test_product_file_size):
        """Test calculating total file size across multiple vision documents"""
        # Create multiple documents
        vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product_file_size.id,
            document_name="Doc A",
            content="Content A",
            storage_type="inline",
            file_size=1000
        )

        vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product_file_size.id,
            document_name="Doc B",
            content="Content B",
            storage_type="inline",
            file_size=2000
        )

        vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product_file_size.id,
            document_name="Doc C",
            content="Content C",
            storage_type="inline",
            file_size=3000
        )

        # List and calculate total
        docs = vision_repo.list_by_product(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product_file_size.id
        )

        total_size = sum(doc.file_size or 0 for doc in docs)
        assert total_size == 6000

    def test_calculate_total_chunks(self, db_session, vision_repo, test_tenant_key, test_product_file_size):
        """Test calculating total chunks across multiple vision documents"""
        # Create documents with chunk counts
        vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product_file_size.id,
            document_name="Doc A",
            content="Content A",
            storage_type="inline",
            file_size=1000
        )

        vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product_file_size.id,
            document_name="Doc B",
            content="Content B",
            storage_type="inline",
            file_size=2000
        )

        # Manually set chunk_count for testing
        result = db_session.execute(
            select(VisionDocument).filter(
                VisionDocument.product_id == test_product_file_size.id,
                VisionDocument.tenant_key == test_tenant_key
            )
        )
        docs = result.scalars().all()

        if len(docs) >= 2:
            docs[0].chunk_count = 5
            docs[1].chunk_count = 8
            db_session.commit()

            # Calculate total
            total_chunks = sum(doc.chunk_count for doc in docs)
            assert total_chunks == 13

    def test_aggregate_stats_with_null_file_sizes(self, db_session, vision_repo, test_tenant_key, test_product_file_size):
        """Test that aggregate stats handle NULL file_size correctly"""
        # Create documents with mixed NULL and valid file_size
        vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product_file_size.id,
            document_name="Doc with size",
            content="Content",
            storage_type="inline",
            file_size=1000
        )

        vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product_file_size.id,
            document_name="Doc without size",
            content="Content",
            storage_type="inline",
            file_size=None
        )

        # List and calculate total (should treat NULL as 0)
        docs = vision_repo.list_by_product(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product_file_size.id
        )

        total_size = sum(doc.file_size or 0 for doc in docs)
        assert total_size == 1000  # Only counts non-NULL


class TestMultiTenantFileSizeIsolation:
    """Test multi-tenant isolation for file_size data"""

    def test_file_size_isolated_by_tenant(self, db_session, vision_repo, test_product_file_size):
        """Test that file_size data is properly isolated by tenant_key"""
        tenant1 = "tenant_001"
        tenant2 = "tenant_002"

        # Create product for tenant2
        product2 = Product(
            id="test_product_tenant2",
            tenant_key=tenant2,
            name="Tenant 2 Product",
            description="Product for tenant 2"
        )
        db_session.add(product2)
        db_session.commit()

        # Create documents for both tenants
        doc1 = vision_repo.create(
            session=db_session,
            tenant_key=tenant1,
            product_id=test_product_file_size.id,
            document_name="Tenant 1 Doc",
            content="Content 1",
            storage_type="inline",
            file_size=1000
        )

        doc2 = vision_repo.create(
            session=db_session,
            tenant_key=tenant2,
            product_id=product2.id,
            document_name="Tenant 2 Doc",
            content="Content 2",
            storage_type="inline",
            file_size=2000
        )

        # Verify tenant1 can only see their documents
        tenant1_docs = vision_repo.list_by_product(
            session=db_session,
            tenant_key=tenant1,
            product_id=test_product_file_size.id
        )

        tenant1_sizes = [doc.file_size for doc in tenant1_docs]
        assert 1000 in tenant1_sizes
        assert 2000 not in tenant1_sizes

        # Verify tenant2 can only see their documents
        tenant2_docs = vision_repo.list_by_product(
            session=db_session,
            tenant_key=tenant2,
            product_id=product2.id
        )

        tenant2_sizes = [doc.file_size for doc in tenant2_docs]
        assert 2000 in tenant2_sizes
        assert 1000 not in tenant2_sizes
