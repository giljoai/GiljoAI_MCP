"""
Vision Document Chunker with tiktoken-based accurate token counting.

Handover 0018: Production-grade chunking for agentic vision documents.

Features:
- Accurate token counting using tiktoken (cl100k_base encoding)
- Semantic boundary detection via EnhancedChunker
- TF-based keyword extraction
- Summary generation
- Multi-tenant isolation via product_id

Target chunk size: 5000 tokens with semantic boundaries.
"""

import logging
import re
from typing import Any, Dict, List

import tiktoken

from giljo_mcp.tools.chunking import EnhancedChunker


logger = logging.getLogger(__name__)


class VisionDocumentChunker:
    """
    Vision document chunker with tiktoken integration.

    Uses tiktoken for accurate token counting and EnhancedChunker
    for semantic boundary detection. Extracts keywords and generates
    summaries for each chunk.
    """

    def __init__(self, target_chunk_size: int = 5000):
        """
        Initialize VisionDocumentChunker.

        Args:
            target_chunk_size: Target tokens per chunk (default 5000)
        """
        self.target_chunk_size = target_chunk_size

        # Initialize tiktoken encoder (cl100k_base for GPT-4/GPT-3.5)
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.error(f"Failed to initialize tiktoken encoding: {e}")
            raise

        # Initialize EnhancedChunker for boundary detection
        # Convert token target to approximate character count
        # EnhancedChunker uses 1:4 token-to-char ratio
        max_tokens_for_enhanced = target_chunk_size
        self.enhanced_chunker = EnhancedChunker(max_tokens=max_tokens_for_enhanced)

        logger.info(
            f"VisionDocumentChunker initialized with target size: {target_chunk_size} tokens"
        )

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
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            # Fallback to character-based estimation
            return len(text) // 4

    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
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
            "Vision", "Mission", "Architecture", "Implementation",
            "Testing", "Deployment", "Security", "Performance",
            "Scalability", "Integration", "Configuration"
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
        sentence_ends = ['.', '!', '?', '\n']
        last_sentence = -1

        for end_char in sentence_ends:
            pos = truncated.rfind(end_char)
            if pos > last_sentence:
                last_sentence = pos

        if last_sentence > 0:
            return truncated[:last_sentence + 1].strip()

        # Fallback: break at word boundary
        last_space = truncated.rfind(' ')
        if last_space > 0:
            return truncated[:last_space].strip() + "..."

        return truncated.strip() + "..."

    def chunk_document(
        self, content: str, product_id: str
    ) -> List[Dict[str, Any]]:
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
        enhanced_chunks = self.enhanced_chunker.chunk_content(
            content, document_name=f"product_{product_id}"
        )

        if not enhanced_chunks:
            return []

        # Process each chunk to add accurate token counts and metadata
        processed_chunks = []

        for i, chunk in enumerate(enhanced_chunks):
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
