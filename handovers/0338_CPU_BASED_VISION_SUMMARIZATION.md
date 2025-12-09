# Handover 0338: CPU-Based Vision Document Summarization

**Date**: 2025-12-09
**Status**: FUTURE ENHANCEMENT
**Priority**: Medium
**Effort**: 2-3 days
**Dependencies**: None (new feature)

## Context

During Handover 0336, we established that vision chunking is for **ingestion** (~25K token chapters) and full context is always preserved at runtime. This handover proposes an **optional** CPU-based summarization during upload to compress large documents while maintaining quality.

---

## Executive Summary

For local-first document summarization without GPU, **extractive summarization using sumy** is the recommended primary approach. It achieves **70-90% compression with instant processing** and zero hallucination risk.

| Approach | Compression | Speed | Quality | Dependencies |
|----------|-------------|-------|---------|--------------|
| **Sumy (LSA)** | 70-90% | <1 sec/100K tokens | High fidelity | `sumy`, `nltk` |
| **Sumy + Clustering** | 75-85% | ~2 sec | Better topic coverage | + `scikit-learn` |
| **Qwen2.5-0.5B (CPU)** | 70-85% | 30-60 sec | Coherent, may hallucinate | + `llama-cpp-python` |
| **Hybrid** | 75-80% | ~10 sec | Best balance | All above |

**Recommendation**: Start with **Sumy LSA extractive** - it's fast, accurate, and introduces no hallucinated content. Add optional LLM polish later if needed.

---

## 1. Extractive Summarization (No LLM - Recommended)

### Why Extractive?
- **Zero hallucination** - Only selects existing sentences
- **Instant processing** - <1 second for 100K tokens
- **No model downloads** - Just pip packages
- **Preserves technical accuracy** - Critical for vision documents

### Sumy Library (Primary Choice)

```bash
pip install sumy nltk
python -m nltk.downloader punkt stopwords
```

**Algorithms Available**:

| Algorithm | Best For | Notes |
|-----------|----------|-------|
| **LSA** (Recommended) | Technical docs | Handles synonyms, implicit topics |
| LexRank | Narrative docs | Graph-based centrality |
| TextRank | General | PageRank-inspired |
| Luhn | Speed-critical | Simplest, fastest |

### Implementation Example

```python
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words

class VisionDocumentSummarizer:
    """CPU-based extractive summarizer for vision documents."""

    def __init__(self, language: str = "english"):
        self.language = language
        self.stemmer = Stemmer(language)
        self.summarizer = LsaSummarizer(self.stemmer)
        self.summarizer.stop_words = get_stop_words(language)

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate (1 token ~ 4 chars)."""
        return len(text) // 4

    def summarize(
        self,
        text: str,
        target_tokens: int = 25000,
        chunk_size: int = 10000
    ) -> str:
        """
        Summarize document to target token count.

        Args:
            text: Full vision document
            target_tokens: Target output tokens
            chunk_size: Characters per processing chunk

        Returns:
            Summarized document
        """
        input_tokens = self.estimate_tokens(text)

        # No summarization needed
        if input_tokens <= target_tokens:
            return text

        # Chunk the document
        chunks = self._chunk_text(text, chunk_size)

        # Calculate sentences per chunk
        total_sentences_needed = int(target_tokens / 20)  # ~20 tokens per sentence
        sentences_per_chunk = max(5, total_sentences_needed // len(chunks))

        # Summarize each chunk (MAP phase)
        summaries = []
        for chunk in chunks:
            parser = PlaintextParser.from_string(chunk, Tokenizer(self.language))
            sentences = self.summarizer(parser.document, sentences_per_chunk)
            summaries.append(" ".join(str(s) for s in sentences))

        combined = "\n\n".join(summaries)

        # REDUCE: consolidate if still over target
        if self.estimate_tokens(combined) > target_tokens * 1.1:
            return self._consolidate(combined, target_tokens)

        return combined

    def _chunk_text(self, text: str, chunk_size: int) -> list:
        """Split text into chunks at paragraph boundaries."""
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            if current_size + len(para) > chunk_size and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_size = len(para)
            else:
                current_chunk.append(para)
                current_size += len(para)

        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        return chunks if chunks else [text]

    def _consolidate(self, text: str, target_tokens: int) -> str:
        """Final consolidation pass if still over target."""
        parser = PlaintextParser.from_string(text, Tokenizer(self.language))
        sentence_count = int(target_tokens / 20)
        sentences = self.summarizer(parser.document, sentence_count)
        return " ".join(str(s) for s in sentences)
```

---

## 2. Small LLMs for CPU (Optional Enhancement)

### Models That Work on CPU

| Model | Parameters | RAM Needed | Speed | Notes |
|-------|------------|------------|-------|-------|
| **Qwen2.5-0.5B** | 0.5B | <2GB | 20+ tok/s | Best small model |
| SmolLM2-360M | 360M | <1GB | 30+ tok/s | Smallest viable |
| Phi-3 Mini | 3.8B | 4-6GB | 10-15 tok/s | Higher quality |
| Qwen2.5-3B | 3B | 4GB | 12-18 tok/s | Good balance |

### Via llama-cpp-python

```bash
pip install llama-cpp-python
# Download: qwen2.5-0.5b-instruct-q4_k_m.gguf from HuggingFace
```

```python
from llama_cpp import Llama

def polish_summary(summary: str, model_path: str) -> str:
    """Use small LLM to improve coherence."""
    llm = Llama(
        model_path=model_path,
        n_ctx=4096,
        n_threads=4,
        verbose=False
    )

    prompt = f"""Improve coherence while preserving all key information:

{summary[:6000]}

Improved summary:"""

    response = llm(prompt, max_tokens=2000, temperature=0.3)
    return response['choices'][0]['text'].strip()
```

### Via Ollama (Simpler Setup)

```bash
ollama pull qwen2.5:0.5b
```

```python
import requests

def summarize_with_ollama(text: str) -> str:
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "qwen2.5:0.5b",
            "prompt": f"Summarize concisely:\n\n{text}\n\nSummary:",
            "stream": False,
            "options": {"temperature": 0.2}
        }
    )
    return response.json()["response"]
```

---

## 3. Compression Ratio Analysis

### What's Achievable?

| Method | Input | Output | Compression | Quality |
|--------|-------|--------|-------------|---------|
| Extract 10 sentences | 100K | 5-10K | 90-95% | May miss details |
| Extract 50 sentences | 100K | 25-30K | 70-75% | Good coverage |
| Extract 100 sentences | 100K | 50K | 50% | Excellent |
| Small LLM abstractive | 100K | 15-20K | 80-85% | May hallucinate |
| **Hybrid (recommended)** | 100K | 25-30K | 70-75% | Best balance |

### For GiljoAI Vision Documents

**Current state**: ~100K+ tokens ingested as ~25K token chunks
**Target with summarization**: Same ~25K chunks but with 3-4x original content coverage

**Proposed flow**:
```
100K+ token document
    |
    v [Chunk into 10K sections]
10+ chunks
    |
    v [LSA: 20 sentences per chunk]
200+ sentences (~25-30K tokens)
    |
    v [Optional: Final consolidation]
~25K final output
```

---

## 4. Trade-offs to Consider

### Extractive (sumy) Pros/Cons

**Pros:**
- Zero hallucination risk
- Instant processing
- No model files to manage
- Works offline

**Cons:**
- May miss implicit connections
- Sentences can feel choppy
- No rephrasing/consolidation

### Small LLM Pros/Cons

**Pros:**
- Better coherence
- Can rephrase/consolidate
- More natural reading

**Cons:**
- Hallucination risk (critical for technical docs!)
- Slower (30-60 sec)
- Requires model download (300MB-2GB)
- May need Ollama running

---

## 5. Recommendation

### Phase 1: Extractive Only (Implement First)
```python
pip install sumy nltk
```
- Use LSA algorithm
- Map-reduce for large docs
- 70-80% compression
- <1 second processing

### Phase 2: Optional LLM Polish (Future)
```python
pip install llama-cpp-python  # Or use Ollama
```
- Only for final coherence pass
- User-togglable in settings
- Warn about hallucination risk

### Integration Point

Add summarization during vision document upload:
- **File**: `src/giljo_mcp/services/product_service.py` (vision upload handler)
- **Trigger**: When document exceeds 30K tokens
- **Config**: Admin setting to enable/disable
- **Fallback**: Store both original and summarized versions

---

## 6. Dependencies Summary

### Minimal (Extractive Only)
```
sumy>=0.11.0
nltk>=3.8
```
**Size**: ~5MB
**RAM**: ~100MB

### Full (With LLM Option)
```
sumy>=0.11.0
nltk>=3.8
llama-cpp-python>=0.2.0
scikit-learn>=1.3.0  # For clustering
```
**Size**: ~50MB (+ model file)
**RAM**: 2-6GB (when LLM active)

---

## Implementation Tasks

### Task 1: Add Sumy Dependencies
**File**: `requirements.txt` / `pyproject.toml`
```
sumy>=0.11.0
nltk>=3.8
```

### Task 2: Create VisionDocumentSummarizer Service
**File**: `src/giljo_mcp/services/vision_summarizer.py`
- Implement `VisionDocumentSummarizer` class (code in Section 1)
- LSA algorithm for technical documents
- Map-reduce chunking for large docs
- Token estimation and compression ratio tracking

### Task 3: Integrate with Vision Upload
**File**: `src/giljo_mcp/services/product_service.py`
- Add summarization option to `upload_vision_document()`
- Trigger when document exceeds configurable threshold (default: 30K tokens)
- Store both original and summarized versions

### Task 4: Add Admin Setting
**Files**:
- `api/endpoints/settings.py`
- `frontend/src/views/Settings.vue`

Add toggle: "Enable CPU-based vision summarization"
- Default: OFF (preserve current behavior)
- When ON: Auto-summarize documents > 30K tokens

### Task 5: Database Schema (Optional)
**File**: `src/giljo_mcp/models/product.py`
Add to VisionDocument:
```python
is_summarized: bool = False
original_token_count: int = None
summarized_token_count: int = None
compression_ratio: float = None
```

---

## Acceptance Criteria

- [ ] Sumy LSA summarization achieves 70-80% compression
- [ ] Processing time <5 seconds for 100K token documents
- [ ] No hallucinated content (extractive only)
- [ ] Admin can toggle feature on/off
- [ ] Original document preserved (optional retrieval)
- [ ] Compression metrics logged for analytics

---

## Open Questions (Resolve Before Implementation)

1. **Storage**: Keep original + summary, or replace original?
2. **UI indicator**: Show users when document was summarized?
3. **Threshold**: 30K tokens trigger, or configurable?
4. **LLM polish**: Add optional Ollama integration in Phase 2?

---

## Related Handovers

- **0336**: Vision chunking rollback (context for this feature)
- **0246a-c**: Token optimization series (architectural context)
- **0282**: Vision document field naming conventions

---

**Handover Ready for Future Implementation**
