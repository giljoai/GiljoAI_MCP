"""
Test fixtures for vision document chunking tests.
Provides realistic test data, mocks, and utilities for testing async vision document operations.
"""

import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, Dict, List

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import MCPContextIndex, Product, VisionDocument


class VisionDocumentTestData:
    """Test data generator for vision documents"""

    @staticmethod
    def generate_markdown_content(size_tokens: int = 1000) -> str:
        """
        Generate realistic markdown content for testing.

        Args:
            size_tokens: Approximate number of tokens to generate (~4 chars per token)

        Returns:
            Markdown formatted string
        """
        # ~4 characters per token
        target_chars = size_tokens * 4

        content = "# Vision Document\n\n"
        content += "## Product Overview\n\n"
        content += "This is a comprehensive product vision document for testing purposes. " * 5
        content += "\n\n"

        section_count = 0
        while len(content) < target_chars:
            section_count += 1
            content += f"## Section {section_count}\n\n"
            content += f"### Subsection {section_count}.1\n\n"
            content += (
                "This section contains detailed information about the product features, "
                "architecture, and implementation details that will be used by AI agents "
                "to understand the system and generate appropriate code. " * 3
            )
            content += "\n\n"
            content += "### Subsection {}.2\n\n".format(section_count)
            content += "- Bullet point 1: Important detail\n"
            content += "- Bullet point 2: Another critical aspect\n"
            content += "- Bullet point 3: Implementation consideration\n"
            content += "\n\n"

            if section_count % 3 == 0:
                content += "```python\n"
                content += "# Example code block\n"
                content += "def example_function():\n"
                content += '    """Example docstring"""\n'
                content += "    return 'test'\n"
                content += "```\n\n"

        return content[:target_chars]

    @staticmethod
    def create_edge_case_documents() -> Dict[str, str]:
        """Create edge case documents for testing"""
        return {
            "empty": "",
            "single_line": "Single line document without newline",
            "only_whitespace": "   \n\n\t\t\n   ",
            "very_long_line": "A" * 10000,  # Single line with 10K characters
            "special_chars": "Test with special chars: 日本語 émojis 🎉 symbols @#$%^&*()",
            "unicode": "Unicode test: Ǣ Ƿ Ȝ ƿ ǧ Ƿ Ȝ ǧ ǣ",
            "windows_line_endings": "Line 1\r\nLine 2\r\nLine 3\r\n",
            "mixed_line_endings": "Line 1\nLine 2\r\nLine 3\rLine 4\n",
        }


@pytest_asyncio.fixture
async def test_product(db_session: AsyncSession, tenant_manager) -> Product:
    """
    Create test product for vision document tests.

    Args:
        db_session: Async database session with transaction rollback
        tenant_manager: Tenant manager for creating tenant keys

    Returns:
        Test product instance
    """
    from tests.helpers.test_factories import ProductFactory

    tenant_key = await tenant_manager.create_tenant("test-vision-tenant")

    product = ProductFactory.create(
        tenant_key=tenant_key,
        name="Test Vision Product",
        description="Product for vision document chunking tests",
    )

    db_session.add(product)
    await db_session.flush()

    return product


@pytest_asyncio.fixture
async def vision_document_with_file(
    db_session: AsyncSession, test_product: Product, tmp_path: Path
) -> VisionDocument:
    """
    Create vision document with file storage for testing.

    Args:
        db_session: Async database session
        test_product: Test product fixture
        tmp_path: Pytest temporary directory

    Returns:
        VisionDocument instance with file storage
    """
    # Create vision content
    content = VisionDocumentTestData.generate_markdown_content(5000)

    # Create file on disk
    vision_dir = tmp_path / "products" / test_product.id / "vision"
    vision_dir.mkdir(parents=True, exist_ok=True)

    vision_file = vision_dir / "test_vision.md"
    vision_file.write_text(content, encoding="utf-8")

    # Use forward slashes for cross-platform compatibility
    normalized_path = str(vision_file).replace("\\", "/")

    # Create database record
    doc = VisionDocument(
        id=str(uuid.uuid4()),
        tenant_key=test_product.tenant_key,
        product_id=test_product.id,
        document_name="Test Vision Document",
        document_type="vision",
        storage_type="file",
        vision_path=normalized_path,
        chunked=False,
        chunk_count=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db_session.add(doc)
    await db_session.flush()

    return doc


@pytest_asyncio.fixture
async def vision_document_with_inline_content(
    db_session: AsyncSession, test_product: Product
) -> VisionDocument:
    """
    Create vision document with inline content for testing.

    Args:
        db_session: Async database session
        test_product: Test product fixture

    Returns:
        VisionDocument instance with inline content
    """
    content = VisionDocumentTestData.generate_markdown_content(3000)

    doc = VisionDocument(
        id=str(uuid.uuid4()),
        tenant_key=test_product.tenant_key,
        product_id=test_product.id,
        document_name="Inline Vision Document",
        document_type="vision",
        storage_type="inline",
        vision_document=content,
        chunked=False,
        chunk_count=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db_session.add(doc)
    await db_session.flush()

    return doc


@pytest_asyncio.fixture
async def vision_document_with_chunks(
    db_session: AsyncSession, vision_document_with_file: VisionDocument
) -> tuple[VisionDocument, List[MCPContextIndex]]:
    """
    Create vision document with pre-existing chunks.

    Useful for testing re-chunking scenarios.

    Args:
        db_session: Async database session
        vision_document_with_file: Vision document fixture

    Returns:
        Tuple of (VisionDocument, List of chunks)
    """
    doc = vision_document_with_file

    # Create 3 test chunks
    chunks = []
    for i in range(3):
        chunk = MCPContextIndex(
            chunk_id=str(uuid.uuid4()),
            tenant_key=doc.tenant_key,
            product_id=doc.product_id,
            vision_document_id=doc.id,
            content=f"Chunk {i + 1} content for testing",
            keywords=["test", "chunk", f"section{i}"],
            token_count=100,
            chunk_order=i,
        )
        chunks.append(chunk)
        db_session.add(chunk)

    # Update document metadata
    doc.chunked = True
    doc.chunk_count = 3
    doc.total_tokens = 300
    doc.chunked_at = datetime.now(timezone.utc)

    await db_session.flush()

    return doc, chunks


@pytest_asyncio.fixture
async def vision_document_with_backslash_path(
    db_session: AsyncSession, test_product: Product, tmp_path: Path
) -> VisionDocument:
    """
    Create vision document with Windows-style backslash path (legacy data).

    Tests path normalization for backwards compatibility.

    Args:
        db_session: Async database session
        test_product: Test product fixture
        tmp_path: Pytest temporary directory

    Returns:
        VisionDocument with backslash path
    """
    content = VisionDocumentTestData.generate_markdown_content(1000)

    # Create file
    vision_dir = tmp_path / "products" / test_product.id / "vision"
    vision_dir.mkdir(parents=True, exist_ok=True)

    vision_file = vision_dir / "legacy_vision.md"
    vision_file.write_text(content, encoding="utf-8")

    # Store with backslashes (simulating legacy Windows data)
    windows_path = str(vision_file).replace("/", "\\")

    doc = VisionDocument(
        id=str(uuid.uuid4()),
        tenant_key=test_product.tenant_key,
        product_id=test_product.id,
        document_name="Legacy Windows Path Document",
        document_type="vision",
        storage_type="file",
        vision_path=windows_path,  # Backslashes
        chunked=False,
        chunk_count=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db_session.add(doc)
    await db_session.flush()

    return doc


@pytest_asyncio.fixture
async def multiple_vision_documents(
    db_session: AsyncSession, test_product: Product, tmp_path: Path
) -> List[VisionDocument]:
    """
    Create multiple vision documents for multi-tenant isolation testing.

    Args:
        db_session: Async database session
        test_product: Test product fixture
        tmp_path: Pytest temporary directory

    Returns:
        List of VisionDocument instances
    """
    docs = []

    for i in range(3):
        content = VisionDocumentTestData.generate_markdown_content(2000 + i * 1000)

        vision_dir = tmp_path / "products" / test_product.id / "vision"
        vision_dir.mkdir(parents=True, exist_ok=True)

        vision_file = vision_dir / f"vision_{i}.md"
        vision_file.write_text(content, encoding="utf-8")

        doc = VisionDocument(
            id=str(uuid.uuid4()),
            tenant_key=test_product.tenant_key,
            product_id=test_product.id,
            document_name=f"Vision Document {i + 1}",
            document_type="vision",
            storage_type="file",
            vision_path=str(vision_file).replace("\\", "/"),
            chunked=False,
            chunk_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        db_session.add(doc)
        docs.append(doc)

    await db_session.flush()

    return docs


@pytest.fixture
def large_vision_content() -> str:
    """Generate large vision document for performance testing (50K tokens)"""
    return VisionDocumentTestData.generate_markdown_content(50000)


@pytest.fixture
def xlarge_vision_content() -> str:
    """Generate extra-large vision document for stress testing (100K tokens)"""
    return VisionDocumentTestData.generate_markdown_content(100000)
