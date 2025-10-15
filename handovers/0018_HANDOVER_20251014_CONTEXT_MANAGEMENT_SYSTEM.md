# Handover 0018: Context Management System for Token Reduction

**Handover ID**: 0018
**Creation Date**: 2025-10-14
**Target Date**: 2025-10-28 (2 week timeline)
**Priority**: CRITICAL
**Type**: IMPLEMENTATION
**Status**: Not Started
**Dependencies**: Handover 0017 (Database Schema) must be completed first

---

## 1. Context and Background

**Based On**: Handover 0012 identified that GiljoAI MCP needs a sophisticated context management system to achieve the promised 70% token reduction. This system will chunk large vision documents, create searchable indexes, and enable dynamic context loading.

**AKE-MCP Proven Patterns**:
- Vision documents chunked into 5K token sections
- Semantic boundary detection for meaningful chunks
- Keyword extraction and summary generation
- Full-text search with PostgreSQL
- Dynamic context loading based on agent needs

**Current State**:
- Role-based config filtering (~40% reduction)
- No vision document chunking
- No context indexing or search
- Full context loaded for every request

**Target State**:
- Vision documents automatically chunked
- Searchable context index with keywords
- Agent-specific context loading
- 60%+ token reduction achieved
- Agentic RAG for dynamic discovery

---

## 2. Detailed Requirements

### Core Components to Build

#### Component 1: Vision Document Chunker

**Purpose**: Split large vision documents into manageable, searchable chunks

```python
class VisionDocumentChunker:
    """Intelligent document chunking with semantic boundaries"""

    def __init__(self, chunk_size: int = 5000):
        self.chunk_size = chunk_size
        self.tokenizer = self._initialize_tokenizer()

    async def chunk_document(
        self,
        product_id: str,
        content: str,
        tenant_key: str
    ) -> List[Dict]:
        """
        Split document into chunks with:
        - Semantic boundary detection
        - Keyword extraction
        - Summary generation
        - Token counting
        """

    def _identify_sections(self, content: str) -> List[str]:
        """Identify natural document sections"""

    def _split_at_semantic_boundaries(self, text: str) -> List[str]:
        """Split text at paragraph/section boundaries"""

    async def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from chunk"""

    async def _generate_summary(self, text: str) -> str:
        """Generate concise summary of chunk"""

    def _count_tokens(self, text: str) -> int:
        """Count tokens using appropriate tokenizer"""
```

#### Component 2: Context Indexer

**Purpose**: Store and index chunks for efficient retrieval

```python
class ContextIndexer:
    """Manage context index in database"""

    async def index_chunks(
        self,
        chunks: List[Dict],
        tenant_key: str
    ) -> bool:
        """Store chunks in mcp_context_index table"""

    async def create_search_vectors(
        self,
        chunks: List[Dict]
    ) -> None:
        """Create PostgreSQL full-text search vectors"""

    async def search_context(
        self,
        query: str,
        tenant_key: str,
        limit: int = 10
    ) -> List[Dict]:
        """Search context using full-text search"""

    async def get_chunks_for_agent(
        self,
        agent_type: str,
        mission: str,
        tenant_key: str
    ) -> List[str]:
        """Get relevant chunks for specific agent"""
```

#### Component 3: Dynamic Context Loader

**Purpose**: Load only necessary context for agents

```python
class DynamicContextLoader:
    """Smart context loading based on needs"""

    async def load_context_for_agent(
        self,
        agent_type: str,
        mission: str,
        product_id: str,
        tenant_key: str
    ) -> Dict:
        """
        Load minimal required context:
        - Role-specific configuration
        - Relevant vision chunks
        - Referenced dependencies
        """

    def _determine_required_sections(
        self,
        agent_type: str,
        mission: str
    ) -> List[str]:
        """Determine what context sections are needed"""

    async def _load_vision_chunks(
        self,
        product_id: str,
        keywords: List[str],
        tenant_key: str
    ) -> List[str]:
        """Load relevant vision document chunks"""

    def _filter_by_relevance(
        self,
        chunks: List[Dict],
        mission: str
    ) -> List[Dict]:
        """Filter chunks by relevance to mission"""
```

#### Component 4: Context Summarizer

**Purpose**: Create condensed missions from full context

```python
class ContextSummarizer:
    """Orchestrator-driven summarization"""

    async def create_condensed_mission(
        self,
        full_context: str,
        project_requirements: str,
        tenant_key: str
    ) -> Dict:
        """
        Orchestrator reads full context, creates missions:
        - Analyze full context
        - Extract role-specific requirements
        - Generate condensed missions
        - Track token reduction
        """

    async def _analyze_requirements(
        self,
        context: str,
        requirements: str
    ) -> Dict:
        """Analyze and categorize requirements"""

    def _extract_role_requirements(
        self,
        analysis: Dict,
        role: str
    ) -> str:
        """Extract requirements for specific role"""

    async def _generate_mission(
        self,
        role: str,
        requirements: str,
        max_tokens: int = 1000
    ) -> str:
        """Generate condensed mission for agent"""

    def _calculate_reduction(
        self,
        original_tokens: int,
        condensed_tokens: int
    ) -> float:
        """Calculate token reduction percentage"""
```

---

## 3. Implementation Plan

### Phase 1: Document Chunking (Days 1-3)

1. **Implement VisionDocumentChunker class**
   - Semantic boundary detection
   - Chunk size optimization
   - Keyword extraction
   - Summary generation

2. **Create chunking utilities**
   - Markdown parser for structure
   - Token counter (tiktoken or similar)
   - Text splitter with overlap

3. **Test with sample documents**
   - Test various document sizes
   - Verify chunk quality
   - Measure token counts

### Phase 2: Context Indexing (Days 4-6)

1. **Implement ContextIndexer class**
   - Database storage layer
   - Full-text search setup
   - Vector generation

2. **PostgreSQL configuration**
   ```sql
   -- Configure full-text search
   ALTER TABLE mcp_context_index
   ADD COLUMN search_vector tsvector
   GENERATED ALWAYS AS (
       to_tsvector('english',
           coalesce(content, '') || ' ' ||
           coalesce(summary, '') || ' ' ||
           coalesce(array_to_string(keywords, ' '), '')
       )
   ) STORED;

   CREATE INDEX idx_search_vector
   ON mcp_context_index
   USING GIN (search_vector);
   ```

3. **Search functionality**
   - Keyword search
   - Relevance ranking
   - Performance optimization

### Phase 3: Dynamic Loading (Days 7-9)

1. **Implement DynamicContextLoader**
   - Role-based filtering
   - Chunk selection logic
   - Context assembly

2. **Agent-specific patterns**
   ```python
   AGENT_CONTEXT_PATTERNS = {
       "database": {
           "required": ["schema", "migrations", "models"],
           "keywords": ["database", "sql", "table", "query"],
           "max_chunks": 10
       },
       "backend": {
           "required": ["api", "endpoints", "business_logic"],
           "keywords": ["api", "endpoint", "service", "logic"],
           "max_chunks": 15
       },
       # ... more patterns
   }
   ```

3. **Caching layer**
   - Cache frequently accessed chunks
   - TTL-based expiration
   - Memory management

### Phase 4: Summarization System (Days 10-12)

1. **Implement ContextSummarizer**
   - Full context analysis
   - Mission generation
   - Token tracking

2. **Integration with orchestrator**
   - Hook into orchestrator workflow
   - Mission assignment flow
   - Progress tracking

3. **Token reduction metrics**
   - Measure actual reduction
   - Track per-agent usage
   - Generate reports

### Phase 5: Integration & Testing (Days 13-14)

1. **API endpoints**
   ```python
   @router.post("/products/{product_id}/chunk-vision")
   async def chunk_vision_document(product_id: str):
       """Chunk and index vision document"""

   @router.get("/context/search")
   async def search_context(query: str, limit: int = 10):
       """Search context index"""

   @router.post("/context/load-for-agent")
   async def load_agent_context(agent_type: str, mission: str):
       """Load context for specific agent"""
   ```

2. **Comprehensive testing**
   - Unit tests for each component
   - Integration tests for full flow
   - Performance benchmarking

3. **Documentation**
   - API documentation
   - Usage examples
   - Performance metrics

---

## 4. Testing Requirements

### Unit Tests

```python
# tests/unit/test_vision_chunker.py
async def test_chunk_size_consistency():
    """Verify chunks stay within size limits"""

async def test_semantic_boundaries():
    """Ensure chunks break at meaningful points"""

async def test_keyword_extraction():
    """Validate keyword extraction quality"""

# tests/unit/test_context_indexer.py
async def test_search_accuracy():
    """Test search result relevance"""

async def test_multi_tenant_isolation():
    """Verify tenant isolation in searches"""

# tests/unit/test_dynamic_loader.py
async def test_role_based_loading():
    """Test role-specific context loading"""

async def test_chunk_relevance():
    """Verify relevant chunks are selected"""
```

### Integration Tests

```python
# tests/integration/test_context_flow.py
async def test_end_to_end_flow():
    """
    Test complete flow:
    1. Upload vision document
    2. Chunk and index
    3. Search context
    4. Load for agent
    5. Verify token reduction
    """

async def test_token_reduction_metrics():
    """Measure actual token reduction achieved"""

async def test_concurrent_operations():
    """Test system under concurrent load"""
```

### Performance Benchmarks

- Chunk 50K token document in < 5 seconds
- Search 10,000 chunks in < 100ms
- Load agent context in < 500ms
- Achieve 60%+ token reduction

---

## 5. Rollback Strategy

If issues arise:

1. **Feature flag context management**
   ```python
   ENABLE_CONTEXT_MANAGEMENT = config.get("enable_context_management", False)
   ```

2. **Fallback to full context loading**
   - Keep existing context loading as fallback
   - Switch via configuration

3. **Data preservation**
   - Chunked data remains in database
   - Can be re-processed if needed

4. **Gradual rollout**
   - Test with single tenant first
   - Monitor performance metrics
   - Expand gradually

---

## 6. Success Criteria

### Functional Success
- [ ] Vision documents chunk successfully
- [ ] Context search returns relevant results
- [ ] Agent-specific loading works
- [ ] Token reduction achieved
- [ ] Multi-tenant isolation maintained

### Performance Success
- [ ] 60%+ token reduction measured
- [ ] Search performance < 100ms
- [ ] Chunking performance acceptable
- [ ] No memory leaks identified

### Quality Success
- [ ] Chunks are semantically meaningful
- [ ] Keywords accurately extracted
- [ ] Summaries are useful
- [ ] Context relevance high

---

## 7. Handoff Deliverables

Upon completion, provide:

1. **Context management module** (`src/giljo_mcp/context_management/`)
2. **Chunking utilities** with tests
3. **Search implementation** with benchmarks
4. **API endpoints** for context operations
5. **Performance report** showing token reduction
6. **Integration guide** for orchestrator
7. **Updated documentation** including examples

---

## 8. Dependencies and Blockers

### Dependencies
- **Handover 0017 completion** (database schema required)
- PostgreSQL full-text search
- Token counting library (tiktoken or equivalent)
- Text processing libraries

### Blockers
- Must wait for database schema (Handover 0017)

### Risks
- **Chunk quality**: Mitigated by semantic boundary detection
- **Search performance**: Mitigated by proper indexing
- **Token counting accuracy**: Use proven library

---

## 9. Related Documentation

### Must Read
- `/docs/Vision/TOKEN_REDUCTION_ARCHITECTURE.md` - Token strategy
- `/handovers/0017_HANDOVER_20251014_DATABASE_SCHEMA_ENHANCEMENT.md` - Database schema
- AKE-MCP chunking implementation (if accessible)

### Reference
- PostgreSQL full-text search documentation
- Token counting best practices
- Text chunking strategies

---

## 10. Notes for Implementation Agent

### Key Algorithms

**Semantic Boundary Detection**:
```python
def find_semantic_boundaries(text: str) -> List[int]:
    """Find natural break points in text"""
    boundaries = []

    # Look for paragraph breaks
    # Look for section headers
    # Look for topic changes
    # Avoid breaking mid-sentence

    return boundaries
```

**Relevance Scoring**:
```python
def score_chunk_relevance(chunk: str, mission: str) -> float:
    """Score how relevant a chunk is to mission"""

    # Keyword overlap
    # Semantic similarity
    # Topic alignment

    return score
```

### Getting Started

1. Review Handover 0017 to understand database schema
2. Study AKE-MCP chunking patterns if available
3. Set up PostgreSQL full-text search locally
4. Create feature branch: `feature/0018-context-management`
5. Start with VisionDocumentChunker implementation

### Performance Tips

- Use PostgreSQL's built-in full-text search (fast!)
- Cache frequently accessed chunks
- Process chunks in parallel where possible
- Monitor memory usage during chunking

---

## Agent Instructions

When picking up this handover:

1. **Verify Handover 0017 is complete** - need database tables
2. **Update status** in `/handovers/README.md`
3. **Review token reduction architecture** document
4. **Create comprehensive tests** as you build
5. **Measure actual token reduction** - prove it works!
6. **Document performance metrics** for future reference

This component is critical for achieving the 70% token reduction promise!

---

**Handover Status**: Ready for implementation (after 0017)
**Estimated Effort**: 80 hours (2 weeks)
**Enables**: Projects 0019-0021 benefit from token reduction