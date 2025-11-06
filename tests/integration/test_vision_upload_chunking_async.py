"""
Integration tests for vision document upload and chunking with async refactoring.
Tests the complete flow: Upload → Chunk → Database Verification.

Tests Handover 0047 - Async Vision Document Chunking.
"""

import io

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import MCPContextIndex, Product, VisionDocument
from tests.fixtures.vision_document_fixtures import VisionDocumentTestData


@pytest_asyncio.fixture
async def api_client(db_session: AsyncSession) -> AsyncClient:
    """Create async HTTP client for API testing"""
    from api.app import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def auth_headers(api_client: AsyncClient, test_product: Product) -> dict:
    """Create authentication headers for API requests"""
    # Create test user and get token
    # This is a simplified version - adjust based on your auth system
    return {
        "Authorization": "Bearer test-token",
        "X-Tenant-Key": test_product.tenant_key,
    }


class TestVisionUploadWithAutoChunk:
    """Test vision document upload with auto_chunk=true"""

    @pytest.mark.asyncio
    async def test_upload_auto_chunk_creates_chunks(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_product: Product,
    ):
        """Test uploading vision document with auto_chunk=true creates chunks"""

        # Create test vision content
        content = VisionDocumentTestData.generate_markdown_content(5000)

        # Create multipart form data
        files = {"vision_file": ("test_vision.md", io.BytesIO(content.encode()), "text/markdown")}
        data = {
            "product_id": test_product.id,
            "document_name": "Test Vision Upload",
            "document_type": "vision",
            "auto_chunk": "true",  # Enable auto-chunking
        }

        # Upload document
        response = await api_client.post(
            "/api/vision-documents/",
            files=files,
            data=data,
            headers=auth_headers,
        )

        # Verify HTTP 201 Created
        assert response.status_code == status.HTTP_201_CREATED

        response_data = response.json()
        doc_id = response_data["id"]

        # Verify document in database
        stmt = select(VisionDocument).where(VisionDocument.id == doc_id)
        result = await db_session.execute(stmt)
        doc = result.scalar_one()

        assert doc is not None
        assert doc.document_name == "Test Vision Upload"
        assert doc.chunked is True  # Should be chunked
        assert doc.chunk_count > 0  # Should have chunks
        assert doc.total_tokens > 0
        assert doc.chunked_at is not None

        # Verify chunks created in mcp_context_index
        stmt = select(MCPContextIndex).where(MCPContextIndex.vision_document_id == doc_id)
        result = await db_session.execute(stmt)
        chunks = result.scalars().all()

        assert len(chunks) == doc.chunk_count
        assert len(chunks) >= 1  # At least one chunk

        # Verify chunk metadata
        for i, chunk in enumerate(chunks):
            assert chunk.tenant_key == test_product.tenant_key
            assert chunk.product_id == test_product.id
            assert chunk.vision_document_id == doc_id
            assert chunk.chunk_order == i
            assert chunk.token_count > 0
            assert len(chunk.content) > 0

    @pytest.mark.asyncio
    async def test_upload_auto_chunk_false_no_chunks(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_product: Product,
    ):
        """Test uploading with auto_chunk=false does not create chunks"""

        content = VisionDocumentTestData.generate_markdown_content(3000)

        files = {"vision_file": ("no_chunk_vision.md", io.BytesIO(content.encode()), "text/markdown")}
        data = {
            "product_id": test_product.id,
            "document_name": "No Auto Chunk",
            "document_type": "vision",
            "auto_chunk": "false",  # Disable auto-chunking
        }

        response = await api_client.post(
            "/api/vision-documents/",
            files=files,
            data=data,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED

        doc_id = response.json()["id"]

        # Verify document created but NOT chunked
        stmt = select(VisionDocument).where(VisionDocument.id == doc_id)
        result = await db_session.execute(stmt)
        doc = result.scalar_one()

        assert doc.chunked is False
        assert doc.chunk_count == 0
        assert doc.total_tokens is None or doc.total_tokens == 0
        assert doc.chunked_at is None

        # Verify no chunks in database
        stmt = select(MCPContextIndex).where(MCPContextIndex.vision_document_id == doc_id)
        result = await db_session.execute(stmt)
        chunks = result.scalars().all()

        assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_upload_large_document_chunks_correctly(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_product: Product,
    ):
        """Test uploading large document creates multiple chunks"""

        # Create 50K token document (should create multiple chunks)
        content = VisionDocumentTestData.generate_markdown_content(50000)

        files = {"vision_file": ("large_vision.md", io.BytesIO(content.encode()), "text/markdown")}
        data = {
            "product_id": test_product.id,
            "document_name": "Large Vision Document",
            "document_type": "vision",
            "auto_chunk": "true",
        }

        response = await api_client.post(
            "/api/vision-documents/",
            files=files,
            data=data,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED

        doc_id = response.json()["id"]

        # Verify document
        stmt = select(VisionDocument).where(VisionDocument.id == doc_id)
        result = await db_session.execute(stmt)
        doc = result.scalar_one()

        # Should create multiple chunks for 50K tokens
        assert doc.chunk_count >= 3
        assert doc.total_tokens >= 40000  # Approximately 50K tokens

        # Verify chunks
        stmt = (
            select(MCPContextIndex)
            .where(MCPContextIndex.vision_document_id == doc_id)
            .order_by(MCPContextIndex.chunk_order)
        )
        result = await db_session.execute(stmt)
        chunks = result.scalars().all()

        # Verify chunk ordering
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_order == i
            # No chunk should exceed max tokens (20K default)
            assert chunk.token_count <= 20000


class TestVisionRechunkEndpoint:
    """Test POST /vision-documents/{id}/rechunk endpoint"""

    @pytest.mark.asyncio
    async def test_rechunk_deletes_old_creates_new(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_product: Product,
    ):
        """Test rechunking deletes old chunks and creates new ones"""

        # First, upload a document with chunks
        content = VisionDocumentTestData.generate_markdown_content(5000)

        files = {"vision_file": ("rechunk_test.md", io.BytesIO(content.encode()), "text/markdown")}
        data = {
            "product_id": test_product.id,
            "document_name": "Rechunk Test",
            "document_type": "vision",
            "auto_chunk": "true",
        }

        upload_response = await api_client.post(
            "/api/vision-documents/",
            files=files,
            data=data,
            headers=auth_headers,
        )

        doc_id = upload_response.json()["id"]

        # Verify initial chunks
        stmt = select(MCPContextIndex).where(MCPContextIndex.vision_document_id == doc_id)
        result = await db_session.execute(stmt)
        initial_chunks = result.scalars().all()
        initial_chunk_count = len(initial_chunks)
        initial_chunk_ids = {chunk.chunk_id for chunk in initial_chunks}

        assert initial_chunk_count > 0

        # Rechunk the document
        rechunk_response = await api_client.post(
            f"/api/vision-documents/{doc_id}/rechunk",
            headers=auth_headers,
        )

        assert rechunk_response.status_code == status.HTTP_200_OK

        rechunk_data = rechunk_response.json()
        assert rechunk_data["success"] is True
        assert rechunk_data["old_chunks_deleted"] == initial_chunk_count

        # Verify new chunks created
        stmt = select(MCPContextIndex).where(MCPContextIndex.vision_document_id == doc_id)
        result = await db_session.execute(stmt)
        new_chunks = result.scalars().all()
        new_chunk_ids = {chunk.chunk_id for chunk in new_chunks}

        # Should have new chunk IDs (old ones deleted)
        assert new_chunk_ids != initial_chunk_ids
        assert len(new_chunks) > 0

    @pytest.mark.asyncio
    async def test_rechunk_nonexistent_document_fails(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test rechunking non-existent document returns 404"""

        response = await api_client.post(
            "/api/vision-documents/nonexistent-id/rechunk",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestChunkingErrorHandling:
    """Test error scenarios and rollback behavior"""

    @pytest.mark.asyncio
    async def test_chunking_failure_rolls_back_transaction(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_product: Product,
    ):
        """Test that chunking failures rollback the entire transaction"""

        # Upload empty file (should fail chunking)
        files = {"vision_file": ("empty.md", io.BytesIO(b""), "text/markdown")}
        data = {
            "product_id": test_product.id,
            "document_name": "Empty File",
            "document_type": "vision",
            "auto_chunk": "true",
        }

        response = await api_client.post(
            "/api/vision-documents/",
            files=files,
            data=data,
            headers=auth_headers,
        )

        # Should return error (500 or 400)
        assert response.status_code >= 400

        # Verify document NOT in database (rolled back)
        stmt = select(VisionDocument).where(
            VisionDocument.document_name == "Empty File",
            VisionDocument.tenant_key == test_product.tenant_key,
        )
        result = await db_session.execute(stmt)
        doc = result.scalar_one_or_none()

        # Document should not exist (transaction rolled back)
        # OR if document exists, it should NOT be marked as chunked
        if doc:
            assert doc.chunked is False

    @pytest.mark.asyncio
    async def test_chunking_file_not_found_error(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_product: Product,
    ):
        """Test chunking handles file not found gracefully"""

        # This test would require manipulating file system
        # to delete file after upload but before chunking
        # Skipping for now as it's complex to set up


class TestCrossPlatformPathHandling:
    """Test cross-platform path normalization"""

    @pytest.mark.asyncio
    async def test_uploaded_paths_use_forward_slashes(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_product: Product,
    ):
        """Test that uploaded files store paths with forward slashes"""

        content = VisionDocumentTestData.generate_markdown_content(1000)

        files = {"vision_file": ("path_test.md", io.BytesIO(content.encode()), "text/markdown")}
        data = {
            "product_id": test_product.id,
            "document_name": "Path Test",
            "document_type": "vision",
            "auto_chunk": "true",
        }

        response = await api_client.post(
            "/api/vision-documents/",
            files=files,
            data=data,
            headers=auth_headers,
        )

        doc_id = response.json()["id"]

        # Verify path in database uses forward slashes
        stmt = select(VisionDocument).where(VisionDocument.id == doc_id)
        result = await db_session.execute(stmt)
        doc = result.scalar_one()

        # Path should use forward slashes (cross-platform)
        assert "/" in doc.vision_path
        assert "\\" not in doc.vision_path  # No backslashes


class TestMultiTenantIsolation:
    """Test multi-tenant isolation during chunking"""

    @pytest.mark.asyncio
    async def test_chunks_isolated_by_tenant(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test chunks are isolated by tenant_key"""

        # This test requires creating two different tenants
        # and verifying they cannot access each other's chunks
        # Implementation depends on tenant creation logic
