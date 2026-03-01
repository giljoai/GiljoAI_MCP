"""
Vision Document Chunker with tiktoken-based accurate token counting.

Handover 0018: Production-grade chunking for agentic vision documents.

Features:
- Accurate token counting using tiktoken (cl100k_base encoding)
- Semantic boundary detection via EnhancedChunker
- TF-based keyword extraction
- Summary generation
- Multi-tenant isolation via product_id

Target chunk size: 24000 tokens (VISION_DELIVERY_BUDGET) with semantic boundaries.
"""

import logging
from typing import Any

import tiktoken

from src.giljo_mcp.exceptions import ContextError, GiljoFileNotFoundError
from src.giljo_mcp.tools.chunking import VISION_DELIVERY_BUDGET, EnhancedChunker


logger = logging.getLogger(__name__)


class VisionDocumentChunker:
    """
    Vision document chunker with tiktoken integration.

    Uses tiktoken for accurate token counting and EnhancedChunker
    for semantic boundary detection. Extracts keywords and generates
    summaries for each chunk.
    """

    def __init__(self, target_chunk_size: int = VISION_DELIVERY_BUDGET):
        """
        Initialize VisionDocumentChunker.

        Args:
            target_chunk_size: Target tokens per chunk (default VISION_DELIVERY_BUDGET)
        """
        self.target_chunk_size = target_chunk_size

        # Initialize tiktoken encoder (cl100k_base for GPT-4/GPT-3.5)
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except (ValueError, KeyError, ImportError):
            logger.exception("Failed to initialize tiktoken encoding")
            raise

        # Initialize EnhancedChunker for boundary detection
        # Convert token target to approximate character count
        # EnhancedChunker uses 1:4 token-to-char ratio
        max_tokens_for_enhanced = target_chunk_size
        self.enhanced_chunker = EnhancedChunker(max_tokens=max_tokens_for_enhanced)

        logger.info(f"VisionDocumentChunker initialized with target size: {target_chunk_size} tokens")

    def count_tokens(self, text: str) -> int:
        """
        Count tokens using tiktoken for accurate measurement.

        Args:
            text: Text to count tokens for

        Returns:
            Exact token count
        """
        if not text:
            return 0

        try:
            tokens = self.encoding.encode(text)
            return len(tokens)
        except (ValueError, KeyError, ImportError):
            logger.exception("Error counting tokens")
            # Fallback to character-based estimation
            return len(text) // 4

    def extract_keywords(self, text: str, max_keywords: int = 10) -> list[str]:
        """
        Extract keywords using simple term frequency approach.

        Leverages EnhancedChunker's keyword extraction and adds
        additional technical term detection.

        Args:
            text: Text to extract keywords from
            max_keywords: Maximum keywords to extract

        Returns:
            List of keyword strings
        """
        if not text or not text.strip():
            return []

        # Use EnhancedChunker's keyword extraction as base
        base_keywords = self.enhanced_chunker.extract_keywords(text, max_keywords)

        # Additional technical terms specific to our domain
        additional_terms = [
            "Vision",
            "Mission",
            "Architecture",
            "Implementation",
            "Testing",
            "Deployment",
            "Security",
            "Performance",
            "Scalability",
            "Integration",
            "Configuration",
        ]

        # Add additional matches not in base keywords
        text_lower = text.lower()
        for term in additional_terms:
            if term.lower() in text_lower and term not in base_keywords:
                base_keywords.append(term)
                if len(base_keywords) >= max_keywords:
                    break

        return base_keywords[:max_keywords]

    def generate_summary(self, text: str, max_length: int = 200) -> str:
        """
        Generate simple summary from text.

        For Phase 1, uses first N characters. Can be enhanced with
        LLM-based summarization in future phases.

        Args:
            text: Text to summarize
            max_length: Maximum summary length in characters

        Returns:
            Summary string
        """
        if not text:
            return ""

        # Clean whitespace
        text = text.strip()

        # If text is shorter than max length, return as-is
        if len(text) <= max_length:
            return text

        # Take first max_length chars and find last complete sentence
        truncated = text[:max_length]

        # Try to break at sentence boundary
        sentence_ends = [".", "!", "?", "\n"]
        last_sentence = -1

        for end_char in sentence_ends:
            pos = truncated.rfind(end_char)
            last_sentence = max(last_sentence, pos)

        if last_sentence > 0:
            return truncated[: last_sentence + 1].strip()

        # Fallback: break at word boundary
        last_space = truncated.rfind(" ")
        if last_space > 0:
            return truncated[:last_space].strip() + "..."

        return truncated.strip() + "..."

    def chunk_document(self, content: str, product_id: str) -> list[dict[str, Any]]:
        """
        Chunk document into semantic chunks with metadata.

        Uses EnhancedChunker for boundary detection and adds:
        - Accurate token counting via tiktoken
        - Keyword extraction
        - Summary generation
        - Product ID for multi-tenant isolation

        Args:
            content: Document content to chunk
            product_id: Product ID for multi-tenant isolation

        Returns:
            List of chunk dictionaries with metadata
        """
        if not content or not content.strip():
            return []

        # Use EnhancedChunker to get initial chunks with boundary detection
        enhanced_chunks = self.enhanced_chunker.chunk_content(content, document_name=f"product_{product_id}")

        if not enhanced_chunks:
            return []

        # Process each chunk to add accurate token counts and metadata
        processed_chunks = []

        for _, chunk in enumerate(enhanced_chunks):
            chunk_content = chunk["content"]

            # Skip empty chunks
            if not chunk_content.strip():
                continue

            # Count tokens accurately with tiktoken
            token_count = self.count_tokens(chunk_content)

            # Extract keywords
            keywords = self.extract_keywords(chunk_content, max_keywords=10)

            # Generate summary
            summary = self.generate_summary(chunk_content, max_length=200)

            # Create processed chunk with all metadata
            processed_chunk = {
                "chunk_number": len(processed_chunks) + 1,
                "total_chunks": len(enhanced_chunks),  # Will update after filtering
                "content": chunk_content,
                "tokens": token_count,
                "keywords": keywords,
                "summary": summary,
                "product_id": product_id,
            }

            processed_chunks.append(processed_chunk)

        # Update total_chunks after filtering empty chunks
        total_chunks = len(processed_chunks)
        for chunk in processed_chunks:
            chunk["total_chunks"] = total_chunks

        logger.info(
            f"Chunked document for product {product_id}: "
            f"{total_chunks} chunks, "
            f"{sum(c['tokens'] for c in processed_chunks)} total tokens"
        )

        return processed_chunks

    async def chunk_vision_document(self, session, tenant_key: str, vision_document_id: str) -> dict[str, Any]:
        """
        Chunk a specific vision document with selective re-chunking.

        Handover 0043 Phase 3: Multi-vision document chunking support.
        Handover 0047: Converted to async for proper async/await propagation.

        Steps:
        1. Get vision document from repository (async)
        2. Delete existing chunks for this document only (async)
        3. Chunk content using semantic boundaries
        4. Create new chunk records with vision_document_id link
        5. Update vision document metadata (chunked status, counts) (async)

        This enables selective re-chunking - only the updated document
        is re-chunked, not the entire product's vision content.

        Args:
            session: SQLAlchemy async database session
            tenant_key: Tenant key for multi-tenant isolation
            vision_document_id: Vision document ID to chunk

        Returns:
            Dictionary with chunking results:
            {
                "success": bool,
                "document_id": str,
                "document_name": str,
                "chunks_created": int,
                "total_tokens": int,
                "old_chunks_deleted": int,
                "error": str (if failed)
            }
        """
        from pathlib import Path

        # Import repositories
        try:
            from giljo_mcp.models import MCPContextIndex
            from giljo_mcp.repositories.context_repository import ContextRepository
            from giljo_mcp.repositories.vision_document_repository import VisionDocumentRepository
        except ImportError as e:
            logger.exception("Failed to import repositories")
            raise ContextError(f"Import error: {e}") from e

        vision_repo = VisionDocumentRepository(db_manager=None)
        context_repo = ContextRepository(db_manager=None)

        # Get vision document with tenant isolation (async)
        doc = await vision_repo.get_by_id(session, tenant_key, vision_document_id)
        if not doc:
            error_msg = f"Vision document {vision_document_id} not found for tenant {tenant_key}"
            logger.error(error_msg)
            raise ContextError(error_msg)

        # Get content based on storage type
        content = ""
        try:
            if doc.storage_type in ("file", "hybrid") and doc.vision_path:
                # IMPORTANT: Normalize path to handle legacy backslash paths
                # (prevents escape sequence bugs like \v being interpreted as vertical tab)
                normalized_path = doc.vision_path.replace("\\", "/")
                file_path = Path(normalized_path)

                if file_path.exists():
                    content += file_path.read_text(encoding="utf-8")
                else:
                    logger.warning(f"File path {normalized_path} does not exist for document {vision_document_id}")
                    if doc.storage_type == "file":
                        # For file-only storage, this is an error
                        raise GiljoFileNotFoundError(f"File not found: {normalized_path}")

            if doc.storage_type in ("inline", "hybrid") and doc.vision_document:
                content += doc.vision_document

        except (ValueError, KeyError, OSError) as e:
            error_msg = f"Error reading content for document {vision_document_id}: {e}"
            logger.exception(error_msg)
            raise ContextError(error_msg) from e

        if not content or not content.strip():
            error_msg = f"Document {vision_document_id} has no content to chunk"
            logger.error(error_msg)
            raise ContextError(error_msg)

        # Delete existing chunks for this document (selective deletion, async)
        deleted_count = await context_repo.delete_chunks_by_vision_document(session, tenant_key, vision_document_id)

        logger.info(f"Deleted {deleted_count} existing chunks for document {vision_document_id}")

        # Chunk content using existing chunk_document method
        # This uses EnhancedChunker with semantic boundaries
        chunks = self.chunk_document(content, doc.product_id)

        if not chunks:
            error_msg = f"No chunks generated for document {vision_document_id}"
            logger.warning(error_msg)
            return {
                "document_id": vision_document_id,
                "document_name": doc.document_name,
                "chunks_created": 0,
                "total_tokens": 0,
                "old_chunks_deleted": deleted_count,
            }

        # Create chunk records with vision_document_id link
        total_tokens = 0
        for idx, chunk_data in enumerate(chunks):
            chunk_record = MCPContextIndex(
                tenant_key=tenant_key,
                product_id=doc.product_id,
                vision_document_id=vision_document_id,  # Link to vision document
                content=chunk_data["content"],
                keywords=chunk_data.get("keywords", []),
                token_count=chunk_data.get("tokens", 0),
                chunk_order=idx,
                summary=chunk_data.get("summary", None),
            )
            session.add(chunk_record)
            total_tokens += chunk_data.get("tokens", 0)

        await session.flush()

        # Update vision document metadata (async)
        await vision_repo.mark_chunked(session, vision_document_id, len(chunks), total_tokens)

        logger.info(
            f"Successfully chunked document {vision_document_id}: "
            f"{len(chunks)} chunks, {total_tokens} tokens, "
            f"{deleted_count} old chunks deleted"
        )

        return {
            "document_id": vision_document_id,
            "document_name": doc.document_name,
            "chunks_created": len(chunks),
            "total_tokens": total_tokens,
            "old_chunks_deleted": deleted_count,
        }
