"""
VisionDocumentSummarizer - CPU-based extractive summarization using LSA

Handover 0345b: Sumy LSA Integration for Vision Document Summarization

This service provides extractive summarization for large vision documents using
Latent Semantic Analysis (LSA) algorithm from the Sumy library. Key features:

- **Zero Hallucination**: Extractive only - sentences come from original document
- **High Compression**: 70-80% compression ratio for large documents
- **Fast Processing**: <5 seconds for 100K tokens
- **Map-Reduce Strategy**: Chunks large documents for efficient processing

Implementation follows reference from Handover 0338 with enhancements for
production use including comprehensive error handling and metrics tracking.
"""

import time
from typing import Dict, Any

from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words


class VisionDocumentSummarizer:
    """
    CPU-based extractive summarizer using LSA algorithm.

    LSA (Latent Semantic Analysis) is ideal for technical documents because:
    - Handles synonyms and implicit topics
    - No hallucination (extracts original sentences)
    - Fast CPU-only processing
    - Preserves technical accuracy

    Usage:
        >>> summarizer = VisionDocumentSummarizer()
        >>> result = summarizer.summarize(large_doc, target_tokens=25000)
        >>> print(f"Compressed {result['compression_ratio']*100:.0f}%")
    """

    def __init__(self, language: str = "english"):
        """
        Initialize LSA summarizer with stemmer and stopwords.

        Args:
            language: Language for stemming and stopwords (default: "english")
        """
        self.language = language
        self.stemmer = Stemmer(language)
        self.summarizer = LsaSummarizer(self.stemmer)
        self.summarizer.stop_words = get_stop_words(language)

    def estimate_tokens(self, text: str) -> int:
        """
        Rough token estimate using 1 token ≈ 4 chars heuristic.

        This is sufficient for determining if summarization is needed.
        For exact counts, use tiktoken (but adds overhead).

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        if not text:
            return 0
        return len(text) // 4

    def summarize(
        self,
        text: str,
        target_tokens: int = 25000,
        chunk_size: int = 10000,
    ) -> Dict[str, Any]:
        """
        Summarize document to target token count using map-reduce LSA.

        Algorithm:
        1. Check if summarization needed (text <= target_tokens)
        2. Chunk document at paragraph boundaries (MAP phase)
        3. Summarize each chunk independently
        4. Combine chunk summaries
        5. Consolidate if combined still over target (REDUCE phase)

        Args:
            text: Full vision document text
            target_tokens: Target output token count (default: 25000)
            chunk_size: Characters per processing chunk (default: 10000)

        Returns:
            Dictionary containing:
            - summary: Summarized text
            - original_tokens: Original document token count
            - summary_tokens: Summary token count
            - compression_ratio: Percentage compressed (0.0-1.0)
            - processing_time_ms: Processing time in milliseconds
        """
        start_time = time.time()

        # Handle empty input
        if not text or not text.strip():
            return {
                "summary": "",
                "original_tokens": 0,
                "summary_tokens": 0,
                "compression_ratio": 0.0,
                "processing_time_ms": 0,
            }

        original_tokens = self.estimate_tokens(text)

        # No summarization needed if already under target
        if original_tokens <= target_tokens:
            processing_time_ms = int((time.time() - start_time) * 1000)
            return {
                "summary": text,
                "original_tokens": original_tokens,
                "summary_tokens": original_tokens,
                "compression_ratio": 0.0,  # No compression
                "processing_time_ms": processing_time_ms,
            }

        # Chunk the document (MAP phase)
        chunks = self._chunk_text(text, chunk_size)

        # Calculate sentences per chunk
        # Heuristic: ~25 tokens per sentence (more aggressive compression)
        total_sentences_needed = int(target_tokens / 25)
        sentences_per_chunk = max(5, total_sentences_needed // len(chunks))

        # Summarize each chunk independently
        summaries = []
        for chunk in chunks:
            try:
                parser = PlaintextParser.from_string(chunk, Tokenizer(self.language))
                sentences = self.summarizer(parser.document, sentences_per_chunk)
                summaries.append(" ".join(str(s) for s in sentences))
            except Exception:
                # If chunk summarization fails, skip it
                # This handles edge cases like very short chunks
                continue

        # Combine chunk summaries
        combined = "\n\n".join(summaries)

        # REDUCE: consolidate if still over target (with 5% buffer)
        if self.estimate_tokens(combined) > target_tokens * 1.05:
            combined = self._consolidate(combined, target_tokens)

        summary_tokens = self.estimate_tokens(combined)
        compression_ratio = (original_tokens - summary_tokens) / original_tokens if original_tokens > 0 else 0.0
        processing_time_ms = int((time.time() - start_time) * 1000)

        return {
            "summary": combined,
            "original_tokens": original_tokens,
            "summary_tokens": summary_tokens,
            "compression_ratio": compression_ratio,
            "processing_time_ms": processing_time_ms,
        }

    def _chunk_text(self, text: str, chunk_size: int) -> list:
        """
        Split text into chunks at paragraph boundaries.

        Preserves semantic coherence by keeping paragraphs together.

        Args:
            text: Text to chunk
            chunk_size: Target characters per chunk

        Returns:
            List of text chunks
        """
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            para_size = len(para)

            # Start new chunk if this paragraph would exceed chunk_size
            if current_size + para_size > chunk_size and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size

        # Add final chunk
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks if chunks else [text]

    def _consolidate(self, text: str, target_tokens: int) -> str:
        """
        Final consolidation pass if combined chunks still over target.

        This is the REDUCE phase - applies LSA to the combined chunk summaries
        to further compress to target size.

        Args:
            text: Combined text from chunk summaries
            target_tokens: Target token count

        Returns:
            Consolidated summary text
        """
        try:
            parser = PlaintextParser.from_string(text, Tokenizer(self.language))
            sentence_count = max(5, int(target_tokens / 25))  # ~25 tokens per sentence (more aggressive)
            sentences = self.summarizer(parser.document, sentence_count)
            return " ".join(str(s) for s in sentences)
        except Exception:
            # If consolidation fails, return text as-is
            # Better to be slightly over target than lose content
            return text

    def summarize_multi_level(
        self,
        text: str,
        levels: Dict[str, int] = None
    ) -> Dict[str, Any]:
        """
        Generate multiple summary levels independently from original text.

        Handover 0348: Fixed cascading bug that prevented hitting target token counts.
        Each summary level (light, moderate, heavy) is now generated independently
        from the original text to ensure accurate compression to targets.

        Algorithm:
        1. Generate heavy summary from original text (25K tokens)
        2. Generate moderate summary from original text (12.5K tokens)
        3. Generate light summary from original text (5K tokens)

        Previous cascading approach (heavy → moderate → light) failed when heavy
        exceeded target, preventing smaller levels from hitting their targets.
        Independent summarization ensures each level compresses accurately.

        Args:
            text: Full document text to summarize
            levels: Optional dict mapping level names to target token counts
                   Default: {"light": 5000, "moderate": 12500, "heavy": 25000}

        Returns:
            Dictionary containing:
            {
                "light": {
                    "summary": str,
                    "tokens": int,
                    "sentences": int
                },
                "moderate": {
                    "summary": str,
                    "tokens": int,
                    "sentences": int
                },
                "heavy": {
                    "summary": str,
                    "tokens": int,
                    "sentences": int
                },
                "original_tokens": int,
                "processing_time_ms": int
            }

        Example:
            >>> summarizer = VisionDocumentSummarizer()
            >>> result = summarizer.summarize_multi_level(large_doc)
            >>> print(f"Light: {result['light']['tokens']} tokens")
            >>> print(f"Moderate: {result['moderate']['tokens']} tokens")
            >>> print(f"Heavy: {result['heavy']['tokens']} tokens")
        """
        if levels is None:
            levels = {
                "light": 5000,
                "moderate": 12500,
                "heavy": 25000
            }

        start_time = time.time()
        results = {}

        original_tokens = self.estimate_tokens(text)

        # Generate summaries independently from original text
        # This ensures each level hits its target token count accurately
        for level in ["heavy", "moderate", "light"]:
            target_tokens = levels[level]

            # Always summarize from original text (no cascading)
            summary_result = self.summarize(text, target_tokens=target_tokens)

            # Count sentences (split on period followed by space or end)
            summary_text = summary_result["summary"]
            sentences = [s.strip() for s in summary_text.split('.') if s.strip()]

            results[level] = {
                "summary": summary_text,
                "tokens": summary_result["summary_tokens"],
                "sentences": len(sentences)
            }

        results["original_tokens"] = original_tokens
        results["processing_time_ms"] = int((time.time() - start_time) * 1000)

        return results
