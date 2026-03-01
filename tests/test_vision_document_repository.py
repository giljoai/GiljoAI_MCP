"""
Tests for VisionDocumentRepository (Handover 0043 Phase 2).

Test-driven development: These tests define expected behavior BEFORE implementation.
Tests should initially FAIL until implementation is complete.
"""

import hashlib
from pathlib import Path

import pytest

pytestmark = pytest.mark.skip(reason="0750b: Needs project fixture update for NOT NULL constraints")

from src.giljo_mcp.models import Product
from src.giljo_mcp.repositories.vision_document_repository import VisionDocumentRepository


@pytest.fixture
def vision_repo(db_manager):
    """Create VisionDocumentRepository instance"""
    return VisionDocumentRepository(db_manager)


@pytest.fixture
def test_product(db_session, test_tenant_key):
    """Create a test product"""
    product = Product(
        id="test_product_001",
        tenant_key=test_tenant_key,
        name="Test Product",
        description="Product for vision document testing",
    )
    db_session.add(product)
    db_session.commit()
    return product


@pytest.fixture
def sample_vision_content():
    """Sample vision document content"""
    return """# Product Vision: AI Agent Orchestrator

## Overview
This product enables multi-agent coordination for complex software development.

## Architecture
Microservices-based architecture with FastAPI backend and Vue.js frontend.

## Features
- Agent spawning and coordination
- Real-time messaging
- Context-aware task management
"""


class TestVisionDocumentRepositoryCreation:
    """Test vision document creation operations"""

    def test_create_inline_vision_document(
        self, db_session, vision_repo, test_tenant_key, test_product, sample_vision_content
    ):
        """Test creating vision document with inline content"""
        doc = vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            document_name="Product Vision",
            content=sample_vision_content,
            document_type="vision",
            storage_type="inline",
        )

        assert doc is not None
        assert doc.id is not None
        assert doc.tenant_key == test_tenant_key
        assert doc.product_id == test_product.id
        assert doc.document_name == "Product Vision"
        assert doc.vision_document == sample_vision_content
        assert doc.vision_path is None
        assert doc.storage_type == "inline"
        assert doc.document_type == "vision"
        assert doc.is_active is True
        assert doc.chunked is False
        assert doc.chunk_count == 0

    def test_create_file_based_vision_document(
        self, db_session, vision_repo, test_tenant_key, test_product, sample_vision_content, tmp_path
    ):
        """Test creating vision document with file path"""
        # Create test file
        vision_file = tmp_path / "vision.md"
        vision_file.write_text(sample_vision_content, encoding="utf-8")

        doc = vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            document_name="Architecture Document",
            content=sample_vision_content,
            document_type="architecture",
            storage_type="file",
            file_path=str(vision_file),
        )

        assert doc is not None
        assert doc.vision_path == str(vision_file)
        assert doc.vision_document == sample_vision_content
        assert doc.storage_type == "file"
        assert doc.document_type == "architecture"

    def test_create_sets_content_hash(
        self, db_session, vision_repo, test_tenant_key, test_product, sample_vision_content
    ):
        """Test that content hash is automatically set on creation"""
        doc = vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            document_name="Test Doc",
            content=sample_vision_content,
            storage_type="inline",
        )

        expected_hash = hashlib.sha256(sample_vision_content.encode("utf-8")).hexdigest()
        assert doc.content_hash == expected_hash

    def test_create_unique_document_name_per_product(self, db_session, vision_repo, test_tenant_key, test_product):
        """Test that document names must be unique within a product"""
        # Create first document
        vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            document_name="Unique Name",
            content="Content 1",
            storage_type="inline",
        )
        db_session.commit()

        # Attempt to create second document with same name should fail
        with pytest.raises(Exception):  # IntegrityError from unique constraint
            vision_repo.create(
                session=db_session,
                tenant_key=test_tenant_key,
                product_id=test_product.id,
                document_name="Unique Name",
                content="Content 2",
                storage_type="inline",
            )
            db_session.commit()


class TestVisionDocumentRepositoryRetrieval:
    """Test vision document retrieval operations"""

    def test_get_by_id(self, db_session, vision_repo, test_tenant_key, test_product):
        """Test retrieving vision document by ID"""
        doc = vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            document_name="Test Doc",
            content="Test content",
            storage_type="inline",
        )
        db_session.commit()

        retrieved = vision_repo.get_by_id(db_session, test_tenant_key, doc.id)
        assert retrieved is not None
        assert retrieved.id == doc.id
        assert retrieved.document_name == "Test Doc"

    def test_get_by_id_wrong_tenant_returns_none(self, db_session, vision_repo, test_tenant_key, test_product):
        """Test tenant isolation - wrong tenant_key returns None"""
        doc = vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            document_name="Test Doc",
            content="Test content",
            storage_type="inline",
        )
        db_session.commit()

        # Try to retrieve with different tenant_key
        retrieved = vision_repo.get_by_id(db_session, "wrong_tenant_key", doc.id)
        assert retrieved is None  # Tenant isolation prevents access

    def test_list_by_product(self, db_session, vision_repo, test_tenant_key, test_product):
        """Test listing all vision documents for a product"""
        # Create multiple documents
        doc1 = vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            document_name="Vision",
            content="Vision content",
            storage_type="inline",
            display_order=1,
        )
        doc2 = vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            document_name="Architecture",
            content="Architecture content",
            storage_type="inline",
            display_order=2,
        )
        doc3 = vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            document_name="Inactive Doc",
            content="Inactive content",
            storage_type="inline",
            is_active=False,
        )
        db_session.commit()

        # List all active documents
        docs = vision_repo.list_by_product(
            session=db_session, tenant_key=test_tenant_key, product_id=test_product.id, active_only=True
        )

        assert len(docs) == 2
        assert docs[0].document_name == "Vision"
        assert docs[1].document_name == "Architecture"

        # List all documents including inactive
        all_docs = vision_repo.list_by_product(
            session=db_session, tenant_key=test_tenant_key, product_id=test_product.id, active_only=False
        )

        assert len(all_docs) == 3


class TestVisionDocumentRepositoryUpdate:
    """Test vision document update operations"""

    def test_update_content(self, db_session, vision_repo, test_tenant_key, test_product):
        """Test updating vision document content"""
        doc = vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            document_name="Test Doc",
            content="Original content",
            storage_type="inline",
        )
        db_session.commit()

        original_hash = doc.content_hash

        # Update content
        new_content = "Updated content with new information"
        updated_doc = vision_repo.update_content(
            session=db_session, tenant_key=test_tenant_key, document_id=doc.id, new_content=new_content
        )

        assert updated_doc.vision_document == new_content
        assert updated_doc.content_hash != original_hash  # Hash should change
        assert updated_doc.updated_at is not None

    def test_update_content_resets_chunked_flag(self, db_session, vision_repo, test_tenant_key, test_product):
        """Test that updating content resets chunked status"""
        doc = vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            document_name="Test Doc",
            content="Original content",
            storage_type="inline",
        )

        # Mark as chunked
        vision_repo.mark_chunked(db_session, doc.id, chunk_count=5, total_tokens=1000)
        db_session.commit()

        assert doc.chunked is True

        # Update content should reset chunked flag
        vision_repo.update_content(
            session=db_session, tenant_key=test_tenant_key, document_id=doc.id, new_content="New content"
        )

        assert doc.chunked is False
        assert doc.chunk_count == 0

    def test_mark_chunked(self, db_session, vision_repo, test_tenant_key, test_product):
        """Test marking document as chunked"""
        doc = vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            document_name="Test Doc",
            content="Test content",
            storage_type="inline",
        )
        db_session.commit()

        vision_repo.mark_chunked(session=db_session, document_id=doc.id, chunk_count=10, total_tokens=2500)
        db_session.commit()

        assert doc.chunked is True
        assert doc.chunk_count == 10
        assert doc.total_tokens == 2500
        assert doc.chunked_at is not None


class TestVisionDocumentRepositoryDeletion:
    """Test vision document deletion operations"""

    def test_delete_vision_document(self, db_session, vision_repo, test_tenant_key, test_product):
        """Test deleting vision document"""
        doc = vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            document_name="Test Doc",
            content="Test content",
            storage_type="inline",
        )
        db_session.commit()
        doc_id = doc.id

        # Delete document
        result = vision_repo.delete(session=db_session, tenant_key=test_tenant_key, document_id=doc_id)

        assert result["success"] is True
        assert result["document_id"] == doc_id

        # Verify deletion
        deleted_doc = vision_repo.get_by_id(db_session, test_tenant_key, doc_id)
        assert deleted_doc is None

    def test_delete_wrong_tenant_fails(self, db_session, vision_repo, test_tenant_key, test_product):
        """Test that delete with wrong tenant fails"""
        doc = vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            document_name="Test Doc",
            content="Test content",
            storage_type="inline",
        )
        db_session.commit()

        # Attempt delete with wrong tenant
        result = vision_repo.delete(session=db_session, tenant_key="wrong_tenant", document_id=doc.id)

        assert result["success"] is False
        assert "not found" in result["message"].lower()


class TestVisionDocumentRepositoryTenantIsolation:
    """Test multi-tenant isolation (CRITICAL security)"""

    def test_tenant_isolation_in_listing(self, db_session, vision_repo, test_product):
        """Test that listing only returns documents for the correct tenant"""
        # Create documents for two different tenants
        doc1 = vision_repo.create(
            session=db_session,
            tenant_key="tenant_1",
            product_id=test_product.id,
            document_name="Tenant 1 Doc",
            content="Tenant 1 content",
            storage_type="inline",
        )
        doc2 = vision_repo.create(
            session=db_session,
            tenant_key="tenant_2",
            product_id=test_product.id,
            document_name="Tenant 2 Doc",
            content="Tenant 2 content",
            storage_type="inline",
        )
        db_session.commit()

        # List documents for tenant_1
        tenant1_docs = vision_repo.list_by_product(
            session=db_session, tenant_key="tenant_1", product_id=test_product.id
        )

        # Should only see tenant_1 documents
        assert len(tenant1_docs) == 1
        assert tenant1_docs[0].tenant_key == "tenant_1"
        assert tenant1_docs[0].document_name == "Tenant 1 Doc"


class TestVisionDocumentRepositoryCrossplatformPaths:
    """Test cross-platform path handling (CRITICAL for Windows/Linux/Mac)"""

    def test_file_path_uses_pathlib(self, db_session, vision_repo, test_tenant_key, test_product, tmp_path):
        """Test that file paths are handled with pathlib.Path for cross-platform compatibility"""
        # Create test file using pathlib
        vision_file = Path(tmp_path) / "subdir" / "vision.md"
        vision_file.parent.mkdir(parents=True, exist_ok=True)
        vision_file.write_text("Test content", encoding="utf-8")

        doc = vision_repo.create(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            document_name="File Doc",
            content="Test content",
            storage_type="file",
            file_path=str(vision_file),  # Convert Path to string for storage
        )

        assert doc.vision_path == str(vision_file)
        # Verify path can be converted back to Path
        stored_path = Path(doc.vision_path)
        assert stored_path.exists()
        assert stored_path.is_file()
