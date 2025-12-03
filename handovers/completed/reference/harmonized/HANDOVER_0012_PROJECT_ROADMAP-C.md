# GiljoAI MCP - Project Roadmap to Agentic Vision
## From Task Management to Sophisticated Multi-Agent Coordination

**Date**: 2025-10-14
**Based On**: Handover 0012 Completion Report
**Timeline**: 7 weeks to full vision implementation
**Status**: PLANNING

---

## Executive Summary

This roadmap outlines **5 major implementation projects** required to transform GiljoAI MCP from a solid multi-tenant task management system into the sophisticated agentic project management platform envisioned by the user.

**Foundation**: Proven patterns from AKE-MCP provide implementation blueprint
**Approach**: Incremental enhancement preserving existing functionality
**Timeline**: 7 weeks sequential development, 4 weeks if parallel
**Risk**: LOW - leveraging working patterns from user's existing system

---

## Project Priority Matrix

| Project | Priority | Timeline | Dependencies | Impact |
|---------|----------|----------|--------------|---------|
| **Project 1**: Database Schema | CRITICAL | 1 week | None | Foundation for all |
| **Project 2**: Context Management | CRITICAL | 2 weeks | Project 1 | 60%+ context prioritization |
| **Project 3**: Agent Job Management | HIGH | 2 weeks | Project 1 | Agent coordination |
| **Project 4**: Orchestrator Enhancement | HIGH | 2 weeks | Projects 2 & 3 | Automated workflow |
| **Project 5**: Dashboard Integration | MEDIUM | 1.5 weeks | Projects 3 & 4 | User experience |

**Total Sequential**: 8.5 weeks
**Total Parallel** (recommended): ~5 weeks (Projects 2 & 3 in parallel after Project 1)

---

## PROJECT 1: Database Schema Enhancement

### Overview
**Priority**: CRITICAL
**Timeline**: 1 week (5 working days)
**Dependencies**: None
**Blocks**: All other projects

**Objective**: Establish database foundation for vision document chunking, context summarization, agent job tracking, and product hierarchy.

### Detailed Implementation Plan

#### Day 1-2: Schema Design and Model Creation

**New Tables to Create**:

```python
# File: src/giljo_mcp/models.py

from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, Boolean, DECIMAL, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

# 1. Context Indexing Table
class MCPContextIndex(Base):
    """Store vision document chunks for agentic RAG"""
    __tablename__ = 'mcp_context_index'

    id = Column(Integer, primary_key=True)
    tenant_key = Column(String(255), nullable=False, index=True)
    chunk_id = Column(String(255), unique=True, nullable=False, index=True)
    product_id = Column(String(255), index=True)
    content = Column(Text, nullable=False)
    summary = Column(Text)
    keywords = Column(ARRAY(Text))
    token_count = Column(Integer)
    chunk_order = Column(Integer)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # PostgreSQL full-text search vector
    # searchable_vector - will use tsvector, added via migration


# 2. Context Summarization Table
class MCPContextSummary(Base):
    """Orchestrator-created condensed missions"""
    __tablename__ = 'mcp_context_summary'

    id = Column(Integer, primary_key=True)
    tenant_key = Column(String(255), nullable=False, index=True)
    context_id = Column(String(255), unique=True, nullable=False, index=True)
    product_id = Column(String(255), index=True)
    full_content = Column(Text, nullable=False)
    condensed_mission = Column(Text, nullable=False)
    full_token_count = Column(Integer)
    condensed_token_count = Column(Integer)
    reduction_percent = Column(DECIMAL(5, 2))
    created_at = Column(TIMESTAMP, server_default=func.now())


# 3. Agent Job Management Table
class MCPAgentJob(Base):
    """Agent jobs separate from user tasks"""
    __tablename__ = 'mcp_agent_jobs'

    id = Column(Integer, primary_key=True)
    tenant_key = Column(String(255), nullable=False, index=True)
    job_id = Column(String(255), unique=True, nullable=False, index=True)
    agent_type = Column(String(100), nullable=False, index=True)
    mission = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, index=True)  # pending, active, completed, failed
    spawned_by = Column(String(255))  # orchestrator or agent_id
    context_chunks = Column(ARRAY(Text))  # References to context_index chunk_ids
    messages = Column(JSONB, server_default='[]')  # Agent communication history
    acknowledged = Column(Boolean, default=False)
    started_at = Column(TIMESTAMP)
    completed_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, server_default=func.now())


# 4. Product Hierarchy Table
class Product(Base):
    """Products with vision documents"""
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    tenant_key = Column(String(255), nullable=False, index=True)
    product_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    vision_document = Column(Text)  # Large vision doc content
    chunked = Column(Boolean, default=False)  # Has vision been chunked?
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
```

**Message Table Enhancement**:

```python
# File: src/giljo_mcp/models.py

# Enhance existing Message model
class Message(Base):
    # ... existing fields ...

    # NEW: Acknowledgment tracking
    acknowledged = Column(JSONB, server_default='[]')
    # Stores array of agent IDs that acknowledged message
    # Example: ["agent_job_123", "agent_job_456"]
```

#### Day 3: Database Migration Implementation

**File**: `src/giljo_mcp/migrations/add_agent_management_schema.py`

```python
"""Add agent management schema for vision implementation"""

async def upgrade_schema(db_manager):
    """Apply schema changes"""

    # 1. Create new tables via SQLAlchemy
    await db_manager.create_tables_async()

    # 2. Add full-text search to context_index
    await db_manager.execute_raw("""
        ALTER TABLE mcp_context_index
        ADD COLUMN searchable_vector tsvector
        GENERATED ALWAYS AS (
            to_tsvector('english',
                coalesce(content, '') || ' ' ||
                coalesce(summary, '') || ' ' ||
                coalesce(array_to_string(keywords, ' '), '')
            )
        ) STORED;

        CREATE INDEX idx_context_searchable
        ON mcp_context_index USING GIN (searchable_vector);
    """)

    # 3. Add acknowledgment column to existing messages table
    await db_manager.execute_raw("""
        ALTER TABLE messages
        ADD COLUMN IF NOT EXISTS acknowledged JSONB DEFAULT '[]';
    """)

    # 4. Create composite indexes for performance
    await db_manager.execute_raw("""
        CREATE INDEX idx_context_tenant_product
        ON mcp_context_index(tenant_key, product_id);

        CREATE INDEX idx_agent_jobs_tenant_status
        ON mcp_agent_jobs(tenant_key, status);

        CREATE INDEX idx_products_tenant
        ON products(tenant_key);
    """)

async def downgrade_schema(db_manager):
    """Rollback schema changes if needed"""

    await db_manager.execute_raw("""
        DROP TABLE IF EXISTS mcp_agent_jobs CASCADE;
        DROP TABLE IF EXISTS mcp_context_summary CASCADE;
        DROP TABLE IF EXISTS mcp_context_index CASCADE;
        DROP TABLE IF EXISTS products CASCADE;

        ALTER TABLE messages DROP COLUMN IF EXISTS acknowledged;
    """)
```

#### Day 4: Database Manager Integration

**File**: `src/giljo_mcp/database.py`

```python
class DatabaseManager:
    # ... existing methods ...

    async def get_context_chunks(
        self,
        tenant_key: str,
        product_id: str
    ) -> List[Dict]:
        """Retrieve all context chunks for a product"""

        query = select(MCPContextIndex).where(
            MCPContextIndex.tenant_key == tenant_key,
            MCPContextIndex.product_id == product_id
        ).order_by(MCPContextIndex.chunk_order)

        result = await self.session.execute(query)
        return [row.__dict__ for row in result.scalars()]

    async def search_context_chunks(
        self,
        tenant_key: str,
        search_query: str,
        limit: int = 10
    ) -> List[Dict]:
        """Full-text search of context chunks"""

        query = text("""
            SELECT chunk_id, content, summary, keywords,
                   ts_rank(searchable_vector, query) as rank
            FROM mcp_context_index,
                 to_tsquery('english', :query) query
            WHERE tenant_key = :tenant_key
              AND searchable_vector @@ query
            ORDER BY rank DESC
            LIMIT :limit
        """)

        result = await self.session.execute(
            query,
            {
                "query": search_query,
                "tenant_key": tenant_key,
                "limit": limit
            }
        )

        return [dict(row) for row in result]

    async def create_agent_job(
        self,
        tenant_key: str,
        agent_type: str,
        mission: str,
        context_chunks: List[str],
        spawned_by: str = "orchestrator"
    ) -> str:
        """Create new agent job"""

        from uuid import uuid4

        job_id = f"job_{uuid4()}"

        job = MCPAgentJob(
            tenant_key=tenant_key,
            job_id=job_id,
            agent_type=agent_type,
            mission=mission,
            status="pending",
            spawned_by=spawned_by,
            context_chunks=context_chunks,
            messages=[],
            acknowledged=False
        )

        self.session.add(job)
        await self.session.commit()

        return job_id

    async def get_active_agent_jobs(
        self,
        tenant_key: str
    ) -> List[Dict]:
        """Get all active agent jobs for tenant"""

        query = select(MCPAgentJob).where(
            MCPAgentJob.tenant_key == tenant_key,
            MCPAgentJob.status.in_(['pending', 'active'])
        ).order_by(MCPAgentJob.created_at.desc())

        result = await self.session.execute(query)
        return [row.__dict__ for row in result.scalars()]

    async def add_agent_job_message(
        self,
        job_id: str,
        message: Dict
    ):
        """Add message to agent job's message history"""

        query = select(MCPAgentJob).where(
            MCPAgentJob.job_id == job_id
        )
        result = await self.session.execute(query)
        job = result.scalar_one()

        messages = job.messages or []
        messages.append(message)
        job.messages = messages

        await self.session.commit()
```

#### Day 5: Testing and Validation

**File**: `tests/unit/test_database_schema_enhancement.py`

```python
import pytest
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import MCPContextIndex, MCPAgentJob, Product

@pytest.mark.asyncio
async def test_context_index_table_created(db_manager):
    """Verify mcp_context_index table exists and works"""

    chunk_data = {
        "tenant_key": "test_tenant",
        "chunk_id": "chunk_001",
        "product_id": "prod_123",
        "content": "Vision document content here",
        "summary": "Brief summary",
        "keywords": ["vision", "project", "goals"],
        "token_count": 500,
        "chunk_order": 0
    }

    # Insert chunk
    chunk = MCPContextIndex(**chunk_data)
    db_manager.session.add(chunk)
    await db_manager.session.commit()

    # Retrieve chunk
    chunks = await db_manager.get_context_chunks("test_tenant", "prod_123")
    assert len(chunks) == 1
    assert chunks[0]["chunk_id"] == "chunk_001"

@pytest.mark.asyncio
async def test_agent_job_creation(db_manager):
    """Verify agent job tracking works"""

    job_id = await db_manager.create_agent_job(
        tenant_key="test_tenant",
        agent_type="database-expert",
        mission="Design user authentication schema",
        context_chunks=["chunk_001", "chunk_002"],
        spawned_by="orchestrator"
    )

    # Retrieve job
    jobs = await db_manager.get_active_agent_jobs("test_tenant")
    assert len(jobs) == 1
    assert jobs[0]["job_id"] == job_id
    assert jobs[0]["status"] == "pending"

@pytest.mark.asyncio
async def test_context_search(db_manager):
    """Verify full-text search works"""

    # Insert multiple chunks
    chunks = [
        {
            "tenant_key": "test_tenant",
            "chunk_id": f"chunk_{i}",
            "product_id": "prod_123",
            "content": f"Content about {topic}",
            "keywords": [topic]
        }
        for i, topic in enumerate(["database", "API", "frontend"])
    ]

    for chunk_data in chunks:
        chunk = MCPContextIndex(**chunk_data)
        db_manager.session.add(chunk)

    await db_manager.session.commit()

    # Search for "database"
    results = await db_manager.search_context_chunks(
        "test_tenant",
        "database"
    )

    assert len(results) >= 1
    assert "database" in results[0]["content"].lower()

@pytest.mark.asyncio
async def test_message_acknowledgment(db_manager):
    """Verify message acknowledgment tracking"""

    job_id = await db_manager.create_agent_job(
        tenant_key="test_tenant",
        agent_type="backend",
        mission="Test mission",
        context_chunks=[]
    )

    # Add message
    message = {
        "from": "orchestrator",
        "to": "backend",
        "content": "Start implementation",
        "timestamp": "2025-10-14T10:00:00",
        "acknowledged": False
    }

    await db_manager.add_agent_job_message(job_id, message)

    # Verify message stored
    jobs = await db_manager.get_active_agent_jobs("test_tenant")
    assert len(jobs[0]["messages"]) == 1
    assert jobs[0]["messages"][0]["content"] == "Start implementation"
```

### Success Criteria

- ✅ All 4 new tables created successfully
- ✅ Existing `messages` table enhanced with `acknowledged` column
- ✅ Full-text search indexes on `mcp_context_index` working
- ✅ Composite indexes for performance created
- ✅ DatabaseManager methods for new tables implemented
- ✅ All tests passing (20+ unit tests)
- ✅ No breaking changes to existing functionality
- ✅ Migration can rollback cleanly

### Deliverables

1. Updated `models.py` with 4 new models
2. Migration script `add_agent_management_schema.py`
3. Enhanced `database.py` with new query methods
4. Comprehensive test suite (20+ tests)
5. Documentation: `docs/manuals/DATABASE_SCHEMA.md`

### Rollback Plan

If issues arise:
```python
# Rollback migration
await downgrade_schema(db_manager)

# Restore from backup
psql -U postgres giljo_mcp < backup_before_project1.sql
```

---

## PROJECT 2: Context Management System

### Overview
**Priority**: CRITICAL
**Timeline**: 2 weeks (10 working days)
**Dependencies**: Project 1 (database schema)
**Enables**: 60%+ context prioritization through vision document chunking

**Objective**: Implement vision document chunking, context indexing, searchable summaries, and dynamic context loading.

### Detailed Implementation Plan

#### Week 1: Vision Document Chunking

**Day 1-2: Chunker Implementation**

**File**: `src/giljo_mcp/context/vision_chunker.py`

```python
"""Vision document chunking for agentic RAG"""

from typing import List, Dict
import re
from uuid import uuid4

class VisionDocumentChunker:
    """Chunk large vision documents into searchable sections"""

    def __init__(self, chunk_size: int = 5000):
        self.chunk_size = chunk_size  # tokens
        self.overlap = 200  # token overlap between chunks

    async def chunk_vision_document(
        self,
        product_id: str,
        content: str
    ) -> List[Dict]:
        """Split vision doc into semantic chunks"""

        # Split by semantic boundaries (headers, sections)
        sections = self._split_by_semantic_boundaries(content)

        chunks = []
        chunk_idx = 0

        for section in sections:
            # If section too large, split further
            if self._count_tokens(section) > self.chunk_size:
                subsections = self._split_large_section(section)
                sections_to_chunk = subsections
            else:
                sections_to_chunk = [section]

            for subsection in sections_to_chunk:
                chunk = {
                    "chunk_id": f"{product_id}_chunk_{chunk_idx}",
                    "product_id": product_id,
                    "content": subsection,
                    "summary": await self._generate_summary(subsection),
                    "keywords": await self._extract_keywords(subsection),
                    "token_count": self._count_tokens(subsection),
                    "chunk_order": chunk_idx
                }
                chunks.append(chunk)
                chunk_idx += 1

        return chunks

    def _split_by_semantic_boundaries(self, content: str) -> List[str]:
        """Split by markdown headers, paragraphs"""

        # Split on headers first
        header_pattern = r'(^#{1,6}\s+.+$)'
        parts = re.split(header_pattern, content, flags=re.MULTILINE)

        sections = []
        current_section = ""

        for part in parts:
            if re.match(header_pattern, part):
                if current_section:
                    sections.append(current_section.strip())
                current_section = part + "\n"
            else:
                current_section += part

        if current_section:
            sections.append(current_section.strip())

        return sections

    def _split_large_section(self, section: str) -> List[str]:
        """Split large section into chunk_size pieces with overlap"""

        tokens = self._tokenize(section)
        subsections = []

        for i in range(0, len(tokens), self.chunk_size - self.overlap):
            chunk_tokens = tokens[i:i + self.chunk_size]
            subsections.append(self._detokenize(chunk_tokens))

        return subsections

    def _count_tokens(self, text: str) -> int:
        """Estimate token count (simple word-based)"""
        # TODO: Use tiktoken for accurate Claude token counting
        return len(text.split())

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        return text.split()

    def _detokenize(self, tokens: List[str]) -> str:
        """Reconstruct text from tokens"""
        return " ".join(tokens)

    async def _generate_summary(self, content: str) -> str:
        """Generate summary of chunk"""
        # TODO: Use LLM for intelligent summarization
        # For now, extract first 200 chars
        return content[:200] + "..." if len(content) > 200 else content

    async def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from chunk"""
        # TODO: Use NLP for intelligent keyword extraction
        # For now, simple extraction of capitalized words
        words = content.split()
        keywords = [
            word.strip('.,;:!?')
            for word in words
            if word[0].isupper() and len(word) > 3
        ]
        return list(set(keywords))[:10]  # Top 10 unique keywords
```

**Day 3-4: Context Indexer Implementation**

**File**: `src/giljo_mcp/context/context_indexer.py`

```python
"""Context indexing and storage"""

from typing import List, Dict
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import MCPContextIndex

class ContextIndexer:
    """Store and index vision document chunks"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def index_chunks(
        self,
        tenant_key: str,
        chunks: List[Dict]
    ):
        """Store chunks in database with indexing"""

        for chunk_data in chunks:
            chunk = MCPContextIndex(
                tenant_key=tenant_key,
                chunk_id=chunk_data["chunk_id"],
                product_id=chunk_data["product_id"],
                content=chunk_data["content"],
                summary=chunk_data["summary"],
                keywords=chunk_data["keywords"],
                token_count=chunk_data["token_count"],
                chunk_order=chunk_data["chunk_order"]
            )

            self.db.session.add(chunk)

        await self.db.session.commit()

    async def get_chunks_by_product(
        self,
        tenant_key: str,
        product_id: str
    ) -> List[Dict]:
        """Retrieve all chunks for a product"""
        return await self.db.get_context_chunks(tenant_key, product_id)

    async def search_chunks(
        self,
        tenant_key: str,
        query: str,
        limit: int = 10
    ) -> List[Dict]:
        """Full-text search of chunks"""
        return await self.db.search_context_chunks(tenant_key, query, limit)

    async def get_relevant_chunks_for_agent(
        self,
        tenant_key: str,
        product_id: str,
        agent_type: str,
        limit: int = 5
    ) -> List[Dict]:
        """Get most relevant chunks for specific agent type"""

        # Agent-specific keyword mapping
        agent_keywords = {
            "database": ["schema", "table", "model", "database", "SQL"],
            "backend": ["API", "endpoint", "service", "business logic"],
            "frontend": ["UI", "component", "interface", "user experience"],
            "testing": ["test", "validation", "quality", "coverage"]
        }

        keywords = agent_keywords.get(agent_type, [])

        if not keywords:
            # Fallback: get first N chunks
            chunks = await self.get_chunks_by_product(tenant_key, product_id)
            return chunks[:limit]

        # Search for relevant chunks
        query = " | ".join(keywords)  # OR search
        return await self.search_chunks(tenant_key, query, limit)
```

**Day 5: Testing Week 1 Components**

```python
# tests/unit/test_vision_chunker.py

@pytest.mark.asyncio
async def test_chunk_vision_document():
    """Test vision document chunking"""

    chunker = VisionDocumentChunker(chunk_size=1000)

    vision_doc = """
    # Product Vision

    ## Overview
    This is a comprehensive vision document...

    ## Features
    Feature 1: User authentication
    Feature 2: Real-time collaboration
    ...
    """

    chunks = await chunker.chunk_vision_document("prod_123", vision_doc)

    assert len(chunks) > 0
    assert all("chunk_id" in c for c in chunks)
    assert all("summary" in c for c in chunks)
    assert all("keywords" in c for c in chunks)

@pytest.mark.asyncio
async def test_context_indexing(db_manager):
    """Test chunk indexing and retrieval"""

    indexer = ContextIndexer(db_manager)
    chunker = VisionDocumentChunker()

    vision_doc = "Sample vision document for testing"
    chunks = await chunker.chunk_vision_document("prod_123", vision_doc)

    await indexer.index_chunks("test_tenant", chunks)

    retrieved = await indexer.get_chunks_by_product("test_tenant", "prod_123")
    assert len(retrieved) == len(chunks)
```

#### Week 2: Dynamic Context Loading

**Day 6-7: Context Loader Implementation**

**File**: `src/giljo_mcp/context/context_loader.py`

```python
"""Dynamic context loading for agents"""

from typing import List, Dict, Optional
from src.giljo_mcp.context.context_indexer import ContextIndexer

class DynamicContextLoader:
    """Load minimal required context for agents"""

    def __init__(self, indexer: ContextIndexer):
        self.indexer = indexer

    async def load_context_for_agent(
        self,
        tenant_key: str,
        product_id: str,
        agent_type: str,
        mission: str,
        max_tokens: int = 3000
    ) -> Dict:
        """Load relevant context for agent mission"""

        # Get relevant chunks for agent type
        chunks = await self.indexer.get_relevant_chunks_for_agent(
            tenant_key,
            product_id,
            agent_type,
            limit=10  # Get candidates
        )

        # Filter chunks based on mission keywords
        mission_keywords = self._extract_mission_keywords(mission)
        ranked_chunks = self._rank_chunks_by_relevance(
            chunks,
            mission_keywords
        )

        # Build context within token limit
        context = self._build_context(ranked_chunks, max_tokens)

        return {
            "context": context,
            "chunks_used": [c["chunk_id"] for c in ranked_chunks],
            "token_count": self._count_tokens(context),
            "reduction_vs_full": self._calculate_reduction(
                product_id,
                context
            )
        }

    def _extract_mission_keywords(self, mission: str) -> List[str]:
        """Extract keywords from mission statement"""
        # Simple keyword extraction
        stop_words = {"the", "a", "an", "and", "or", "but", "is", "are"}
        words = mission.lower().split()
        return [w for w in words if w not in stop_words and len(w) > 3]

    def _rank_chunks_by_relevance(
        self,
        chunks: List[Dict],
        keywords: List[str]
    ) -> List[Dict]:
        """Rank chunks by keyword overlap"""

        for chunk in chunks:
            chunk_keywords = [k.lower() for k in chunk.get("keywords", [])]
            overlap = len(set(keywords) & set(chunk_keywords))
            chunk["relevance_score"] = overlap

        return sorted(chunks, key=lambda c: c["relevance_score"], reverse=True)

    def _build_context(
        self,
        chunks: List[Dict],
        max_tokens: int
    ) -> str:
        """Build context string within token limit"""

        context_parts = []
        total_tokens = 0

        for chunk in chunks:
            chunk_tokens = chunk["token_count"]

            if total_tokens + chunk_tokens > max_tokens:
                break

            context_parts.append(chunk["content"])
            total_tokens += chunk_tokens

        return "\n\n---\n\n".join(context_parts)

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(text.split())  # Simple estimation

    async def _calculate_reduction(
        self,
        product_id: str,
        loaded_context: str
    ) -> float:
        """Calculate reduction vs full vision document"""
        # Would compare to full product vision doc
        # For now, estimate
        return 60.0  # Placeholder
```

**Day 8-9: Integration and Testing**

**File**: `src/giljo_mcp/context/__init__.py`

```python
"""Context management system - exports"""

from .vision_chunker import VisionDocumentChunker
from .context_indexer import ContextIndexer
from .context_loader import DynamicContextLoader

__all__ = [
    "VisionDocumentChunker",
    "ContextIndexer",
    "DynamicContextLoader"
]
```

**Integration Tests**:

```python
# tests/integration/test_context_management_flow.py

@pytest.mark.asyncio
async def test_full_context_workflow(db_manager):
    """Test complete context management workflow"""

    # 1. Chunk vision document
    chunker = VisionDocumentChunker(chunk_size=1000)
    vision_doc = load_sample_vision_doc()  # Large doc

    chunks = await chunker.chunk_vision_document("prod_123", vision_doc)
    assert len(chunks) > 5  # Should split into multiple chunks

    # 2. Index chunks
    indexer = ContextIndexer(db_manager)
    await indexer.index_chunks("test_tenant", chunks)

    # 3. Load context for agent
    loader = DynamicContextLoader(indexer)
    context = await loader.load_context_for_agent(
        tenant_key="test_tenant",
        product_id="prod_123",
        agent_type="database",
        mission="Design user authentication schema",
        max_tokens=2000
    )

    # Verify context loaded correctly
    assert context["token_count"] <= 2000
    assert len(context["chunks_used"]) > 0
    assert context["reduction_vs_full"] > 40  # Significant reduction

@pytest.mark.asyncio
async def test_agent_specific_context_loading(db_manager):
    """Test that different agents get relevant context"""

    indexer = ContextIndexer(db_manager)
    loader = DynamicContextLoader(indexer)

    # Load context for database agent
    db_context = await loader.load_context_for_agent(
        "test_tenant",
        "prod_123",
        "database",
        "Design schema"
    )

    # Load context for frontend agent
    fe_context = await loader.load_context_for_agent(
        "test_tenant",
        "prod_123",
        "frontend",
        "Build UI components"
    )

    # Different chunks should be loaded
    assert db_context["chunks_used"] != fe_context["chunks_used"]
```

**Day 10: Documentation and Refinement**

### Success Criteria

- ✅ Vision documents chunked into 5k token sections
- ✅ Chunks indexed with full-text search
- ✅ Agent-specific context loading works
- ✅ Context prioritization of 60%+ demonstrated
- ✅ Keyword extraction and ranking functional
- ✅ All integration tests passing
- ✅ Documentation complete

### Deliverables

1. `vision_chunker.py` - Semantic document chunking
2. `context_indexer.py` - Database indexing and search
3. `context_loader.py` - Dynamic context loading
4. Comprehensive test suite (30+ tests)
5. Documentation: `docs/manuals/CONTEXT_MANAGEMENT.md`
6. Migration guide from manual to automated context

---

## PROJECT 3: Agent Job Management System

### Overview
**Priority**: HIGH
**Timeline**: 2 weeks (10 working days)
**Dependencies**: Project 1 (database schema)
**Can Run**: In parallel with Project 2

**Objective**: Implement agent job tracking separate from user tasks, enable agent-to-agent communication with acknowledgment.

### Detailed Implementation Plan

#### Week 1: Agent Job Manager Core

**Day 1-3: Job Manager Implementation**

**File**: `src/giljo_mcp/agents/job_manager.py`

```python
"""Agent job management system"""

from typing import List, Dict, Optional
from datetime import datetime
from uuid import uuid4
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import MCPAgentJob

class AgentJobManager:
    """Manage agent jobs separately from user tasks"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def create_agent_job(
        self,
        tenant_key: str,
        agent_type: str,
        mission: str,
        context_chunks: List[str],
        spawned_by: str = "orchestrator",
        metadata: Optional[Dict] = None
    ) -> str:
        """Create new agent job"""

        job_id = f"job_{uuid4()}"

        job = MCPAgentJob(
            tenant_key=tenant_key,
            job_id=job_id,
            agent_type=agent_type,
            mission=mission,
            status="pending",
            spawned_by=spawned_by,
            context_chunks=context_chunks,
            messages=[],
            acknowledged=False
        )

        self.db.session.add(job)
        await self.db.session.commit()

        return job_id

    async def update_job_status(
        self,
        job_id: str,
        status: str
    ):
        """Update agent job status"""

        job = await self._get_job(job_id)
        job.status = status

        if status == "active" and not job.started_at:
            job.started_at = datetime.now()
        elif status in ["completed", "failed"]:
            job.completed_at = datetime.now()

        await self.db.session.commit()

    async def get_active_jobs(
        self,
        tenant_key: str,
        agent_type: Optional[str] = None
    ) -> List[Dict]:
        """Get active agent jobs"""

        jobs = await self.db.get_active_agent_jobs(tenant_key)

        if agent_type:
            jobs = [j for j in jobs if j["agent_type"] == agent_type]

        return jobs

    async def spawn_agent(
        self,
        job_id: str
    ) -> Dict:
        """Trigger agent spawning workflow"""

        job = await self._get_job(job_id)

        # Load context chunks for agent
        context = await self._load_job_context(job)

        # Generate agent mission with context
        mission = self._generate_agent_mission(job, context)

        # Update status
        await self.update_job_status(job_id, "active")

        # TODO: Integrate with Task tool for actual spawning
        # For now, return mission for manual spawning
        return {
            "job_id": job_id,
            "agent_type": job.agent_type,
            "mission": mission,
            "context_token_count": len(context.split()),
            "status": "active"
        }

    async def _get_job(self, job_id: str) -> MCPAgentJob:
        """Retrieve job by ID"""
        query = select(MCPAgentJob).where(
            MCPAgentJob.job_id == job_id
        )
        result = await self.db.session.execute(query)
        return result.scalar_one()

    async def _load_job_context(self, job: MCPAgentJob) -> str:
        """Load context chunks for job"""
        # Would integrate with ContextLoader from Project 2
        # For standalone implementation, simple loading
        return "Context placeholder"

    def _generate_agent_mission(
        self,
        job: MCPAgentJob,
        context: str
    ) -> str:
        """Generate complete mission prompt"""

        return f"""
# Agent Mission: {job.agent_type}

## Objective
{job.mission}

## Context
{context}

## Instructions
Execute this mission and report results via MCP message queue.
"""
```

#### Week 2: Agent Communication System

**Day 4-7: Communication Queue Implementation**

**File**: `src/giljo_mcp/agents/communication_queue.py`

```python
"""Agent-to-agent communication system"""

from typing import List, Dict
from datetime import datetime
from src.giljo_mcp.database import DatabaseManager

class AgentCommunicationQueue:
    """Manage agent-to-agent messaging with acknowledgment"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def send_message(
        self,
        tenant_key: str,
        from_agent: str,
        to_agent: str,
        message: str,
        message_type: str = "info"
    ) -> str:
        """Send message from one agent to another"""

        message_id = f"msg_{uuid4()}"

        msg_data = {
            "message_id": message_id,
            "from": from_agent,
            "to": to_agent,
            "content": message,
            "type": message_type,
            "timestamp": datetime.now().isoformat(),
            "acknowledged": False
        }

        # Add message to target agent job
        await self.db.add_agent_job_message(to_agent, msg_data)

        return message_id

    async def get_messages(
        self,
        job_id: str,
        unacknowledged_only: bool = False
    ) -> List[Dict]:
        """Get messages for agent job"""

        job = await self._get_job(job_id)
        messages = job.messages or []

        if unacknowledged_only:
            messages = [m for m in messages if not m.get("acknowledged", False)]

        return messages

    async def acknowledge_message(
        self,
        job_id: str,
        message_id: str
    ):
        """Mark message as acknowledged"""

        job = await self._get_job(job_id)
        messages = job.messages or []

        for msg in messages:
            if msg.get("message_id") == message_id:
                msg["acknowledged"] = True
                msg["acknowledged_at"] = datetime.now().isoformat()
                break

        job.messages = messages
        await self.db.session.commit()

    async def broadcast_message(
        self,
        tenant_key: str,
        from_agent: str,
        message: str,
        agent_types: Optional[List[str]] = None
    ):
        """Broadcast message to multiple agents"""

        # Get target agent jobs
        jobs = await self.db.get_active_agent_jobs(tenant_key)

        if agent_types:
            jobs = [j for j in jobs if j["agent_type"] in agent_types]

        # Send to each
        for job in jobs:
            await self.send_message(
                tenant_key,
                from_agent,
                job["job_id"],
                message
            )
```

**Day 8-10: Testing and Integration**

```python
# tests/unit/test_agent_job_manager.py

@pytest.mark.asyncio
async def test_create_agent_job(db_manager):
    """Test agent job creation"""

    manager = AgentJobManager(db_manager)

    job_id = await manager.create_agent_job(
        tenant_key="test_tenant",
        agent_type="database-expert",
        mission="Design authentication schema",
        context_chunks=["chunk_001", "chunk_002"],
        spawned_by="orchestrator"
    )

    assert job_id.startswith("job_")

    jobs = await manager.get_active_jobs("test_tenant")
    assert len(jobs) == 1
    assert jobs[0]["status"] == "pending"

@pytest.mark.asyncio
async def test_agent_communication(db_manager):
    """Test agent-to-agent messaging"""

    queue = AgentCommunicationQueue(db_manager)

    # Create two agent jobs
    manager = AgentJobManager(db_manager)
    job1 = await manager.create_agent_job(
        "test_tenant", "database", "Task 1", []
    )
    job2 = await manager.create_agent_job(
        "test_tenant", "backend", "Task 2", []
    )

    # Send message from job1 to job2
    msg_id = await queue.send_message(
        "test_tenant",
        job1,
        job2,
        "Schema design complete"
    )

    # job2 receives message
    messages = await queue.get_messages(job2)
    assert len(messages) == 1
    assert messages[0]["from"] == job1

    # job2 acknowledges
    await queue.acknowledge_message(job2, msg_id)

    # Verify acknowledgment
    messages = await queue.get_messages(job2, unacknowledged_only=True)
    assert len(messages) == 0  # All acknowledged
```

### Success Criteria

- ✅ Agent jobs tracked separately from user tasks
- ✅ Job lifecycle management (pending → active → completed)
- ✅ Agent-to-agent messaging functional
- ✅ Message acknowledgment prevents duplicates
- ✅ Broadcast messaging works
- ✅ All tests passing (25+ tests)

### Deliverables

1. `job_manager.py` - Agent job lifecycle management
2. `communication_queue.py` - Agent messaging system
3. Test suite (25+ tests)
4. Documentation: `docs/manuals/AGENT_JOB_MANAGEMENT.md`

---

## PROJECT 4: Orchestrator Enhancement

### Overview
**Priority**: HIGH
**Timeline**: 2 weeks (10 working days)
**Dependencies**: Projects 2 & 3 (context management, job management)

**Objective**: Add orchestrator context summarization workflow and multi-agent coordination.

### Detailed Implementation Plan

#### Week 1: Context Summarization

**File**: `src/giljo_mcp/orchestrator/context_summarizer.py`

```python
"""Orchestrator context summarization workflow"""

from typing import Dict, List
from src.giljo_mcp.context import DynamicContextLoader
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import MCPContextSummary

class ContextSummarizer:
    """Orchestrator-driven context summarization"""

    async def create_condensed_missions(
        self,
        tenant_key: str,
        product_id: str,
        project_requirements: str
    ) -> Dict:
        """Orchestrator analyzes full context, creates agent missions"""

        # 1. Load FULL product vision context
        full_context = await self._load_full_context(product_id)
        full_tokens = self._count_tokens(full_context)

        # 2. Analyze requirements and context
        analysis = await self._analyze_requirements(
            full_context,
            project_requirements
        )

        # 3. Generate condensed missions per agent type
        missions = {
            "database": self._extract_database_mission(analysis),
            "backend": self._extract_backend_mission(analysis),
            "frontend": self._extract_frontend_mission(analysis),
            "testing": self._extract_testing_mission(analysis)
        }

        condensed_tokens = sum(
            self._count_tokens(m) for m in missions.values()
        )

        reduction = ((full_tokens - condensed_tokens) / full_tokens) * 100

        # 4. Store summarization
        summary = MCPContextSummary(
            tenant_key=tenant_key,
            context_id=f"ctx_{uuid4()}",
            product_id=product_id,
            full_content=full_context,
            condensed_mission=str(missions),
            full_token_count=full_tokens,
            condensed_token_count=condensed_tokens,
            reduction_percent=reduction
        )

        self.db.session.add(summary)
        await self.db.session.commit()

        return {
            "missions": missions,
            "token_reduction": reduction,
            "full_tokens": full_tokens,
            "condensed_tokens": condensed_tokens
        }
```

#### Week 2: Multi-Agent Coordination

**File**: `src/giljo_mcp/orchestrator/agent_coordinator.py`

```python
"""Multi-agent workflow coordination"""

class AgentCoordinator:
    """Coordinate multiple agent jobs"""

    async def coordinate_project(
        self,
        tenant_key: str,
        product_id: str,
        project_requirements: str
    ) -> Dict:
        """Full workflow: Summarize → Spawn → Coordinate"""

        # 1. Create condensed missions
        summary = await self.summarizer.create_condensed_missions(
            tenant_key,
            product_id,
            project_requirements
        )

        # 2. Spawn agents with condensed missions
        agent_jobs = []
        for agent_type, mission in summary["missions"].items():

            # Create agent job
            job_id = await self.job_manager.create_agent_job(
                tenant_key=tenant_key,
                agent_type=agent_type,
                mission=mission,
                context_chunks=[],  # Condensed mission has no chunks
                spawned_by="orchestrator"
            )

            # Spawn agent
            await self.job_manager.spawn_agent(job_id)
            agent_jobs.append(job_id)

        # 3. Monitor coordination
        await self._monitor_agents(agent_jobs)

        return {
            "agent_jobs": agent_jobs,
            "token_reduction": summary["token_reduction"],
            "status": "coordinating"
        }
```

### Success Criteria

- ✅ Orchestrator reads full context first
- ✅ Creates condensed missions per agent
- ✅ Context prioritization tracked and measured
- ✅ Multi-agent spawning coordinated
- ✅ Agent workflow monitored

### Deliverables

1. `context_summarizer.py`
2. `agent_coordinator.py`
3. Test suite
4. Documentation

---

## PROJECT 5: Dashboard Integration

### Overview
**Priority**: MEDIUM
**Timeline**: 1.5 weeks (8 working days)
**Dependencies**: Projects 3 & 4 (job management, orchestrator)

**Objective**: Real-time agent monitoring dashboard with interactive controls.

### Components

1. `AgentMonitor.vue` - Active agent jobs display
2. `AgentMessaging.vue` - Agent communication interface
3. `ContextViewer.vue` - Context visualization
4. API endpoints for agent management
5. WebSocket real-time updates

### Success Criteria

- ✅ Real-time agent monitoring
- ✅ Agent messaging through UI
- ✅ Context visualization
- ✅ WebSocket updates reliable

---

## Timeline Summary

### Sequential Approach (8.5 weeks)
```
Week 1:     Project 1 (Database Schema)
Weeks 2-3:  Project 2 (Context Management)
Weeks 4-5:  Project 3 (Agent Job Management)
Weeks 6-7:  Project 4 (Orchestrator Enhancement)
Weeks 8-9:  Project 5 (Dashboard Integration)
```

### Parallel Approach (5 weeks) - RECOMMENDED
```
Week 1:     Project 1 (Database Schema)
Weeks 2-3:  Projects 2 & 3 in parallel
Weeks 4-5:  Project 4 (depends on 2 & 3)
Week 6:     Project 5 (depends on 3 & 4)
```

---

## Resource Requirements

### Development Team
- 1 Backend Developer (Projects 1-4)
- 1 Frontend Developer (Project 5)
- 1 QA Engineer (testing all projects)

### Infrastructure
- PostgreSQL 14+ with full-text search
- Development environment matching production
- Test database for integration testing

### Tools & Dependencies
- SQLAlchemy for ORM
- pytest for testing
- Vue 3 + Vuetify for dashboard
- WebSocket for real-time updates

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Database migration issues | LOW | HIGH | Comprehensive rollback scripts |
| Context chunking performance | MEDIUM | MEDIUM | Benchmark and optimize early |
| Agent messaging complexity | LOW | HIGH | Port proven AKE-MCP patterns |
| Dashboard real-time updates | MEDIUM | LOW | Use existing WebSocket infrastructure |
| Timeline overruns | MEDIUM | MEDIUM | Buffer time built into estimates |

---

## Success Metrics

### Technical Metrics
- 60%+ context prioritization from context management
- Agent job tracking with 100% accuracy
- Message acknowledgment prevents all duplicates
- Dashboard real-time updates < 500ms latency

### Business Metrics
- User vision fully implemented
- Documentation matches reality
- All integration tests passing
- Performance benchmarks met

---

## Next Steps

### Immediate (Next 24 Hours)
1. Archive Handover 0012 as complete
2. Create Handover 0013 for Project 1
3. Review AKE-MCP database schema in detail
4. Set up development branch for Project 1

### Week 1
1. Begin Project 1 (Database Schema Enhancement)
2. Extract AKE-MCP patterns for reference
3. Design detailed database migration strategy
4. Create comprehensive test plan

### Month 1
1. Complete Projects 1, 2, and 3
2. Begin integration testing
3. Update documentation as features complete
4. Prepare for Projects 4 and 5

---

**Status**: Roadmap complete, ready for execution
**Owner**: System Architect + Development Team
**Review Date**: Weekly during implementation
