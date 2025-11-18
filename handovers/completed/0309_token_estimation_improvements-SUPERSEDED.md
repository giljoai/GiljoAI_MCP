# Handover 0309: Token Estimation Improvements

**Feature**: Dynamic Token Estimation from Active Product
**Status**: ❌ SUPERSEDED
**Priority**: P2 - MEDIUM
**Estimated Duration**: 5-6 hours
**Agent Budget**: 110K tokens
**Depends On**: Handover 0308 (Frontend Field Labels & Tooltips)
**Blocks**: Handover 0310 (Integration Testing & Validation)
**Created**: 2025-11-16
**Tool**: CLI + CCW (Backend API + Frontend integration)

---

## ⚠️ SUPERSEDED BY CONTEXT MANAGEMENT v2.0

**Date**: 2025-11-18
**Reason**: Context Management v2.0 (Handovers 0312-0316) completely redesigned the architecture.

**Why This Handover Is Obsolete**:
- v2.0 replaced 15 individual fields → 6 high-level categories
- v2.0 uses depth-based token estimation, not field-based
- Token estimation is now via `DepthTokenEstimator` for depth controls
- Drag-and-drop field priority management was not implemented
- Current system uses fixed category priorities + depth sliders

**What Was Implemented Instead**:
- `frontend/src/services/depthTokenEstimator.ts` - Depth-based token estimation
- `frontend/src/components/settings/DepthConfiguration.vue` - Depth controls with token hints
- 8 depth controls with token estimates (0-30K range)

**Recommendation**: Archive as superseded. Do not implement.

---

## Executive Summary

The frontend currently uses static token estimates (e.g., "Priority 1 = 50 tokens") that don't reflect actual product data. This leads to inaccurate token budget displays and misleads users about the real impact of their priority choices. Following the pattern from Handover 0052 (Product Configuration Token Calculation), we'll fetch actual token counts from the active product's configuration and vision data.

**Why This Matters**: Users need accurate token feedback to make informed priority decisions. Static estimates like "Priority 1 = 50 tokens" don't account for the actual size of their vision documents (which can be 43K tokens) or configuration complexity. Real-time token calculation enables users to see the true impact of priority changes.

**Impact**: Provides accurate, product-specific token estimates in the UI, helps users understand token budget trade-offs, improves transparency of the field priority system.

---

## Problem Statement

### Current Behavior

**Frontend Token Display** (assumed static values):
```javascript
// Static token estimates (NOT accurate)
const TOKEN_ESTIMATES = {
  1: 50,   // Priority 1 = 50 tokens (hardcoded guess)
  2: 30,   // Priority 2 = 30 tokens
  3: 15,   // Priority 3 = 15 tokens
};

function estimateTokens(field, priority) {
  return TOKEN_ESTIMATES[priority] || 0;
}
```

**Issues**:
1. **Inaccurate**: Doesn't reflect actual product data size
2. **Static**: Same estimate for all products (ignores vision document size)
3. **Misleading**: User sees "50 tokens" but actual might be 500 or 5,000
4. **No Feedback**: Dragging field between priorities doesn't show real token change
5. **Doesn't Scale**: 43K vision document uses far more than 50 tokens at Priority 1

### Desired Behavior

**Dynamic Token Calculation**:
```javascript
// Fetch actual token counts from backend
async function fetchFieldTokenEstimates(productId) {
  const response = await api.get(`/api/v1/products/${productId}/field-token-estimates`);
  return response.data;
  // Returns:
  // {
  //   "tech_stack.languages": { "priority_1": 120, "priority_2": 60, "priority_3": 20 },
  //   "codebase_summary": { "priority_1": 5200, "priority_2": 2100, "priority_3": 800 },
  //   "vision_document": { "priority_1": 43200, "priority_2": 14500, "priority_3": 4300 },
  //   ...
  // }
}
```

**Real-Time Budget Display**:
```vue
<template>
  <div class="token-budget-display">
    <h4>Current Token Budget</h4>
    <v-progress-linear
      :model-value="budgetPercentage"
      :color="budgetColor"
      height="25"
    >
      <strong>{{ currentTokens }} / {{ maxTokens }}</strong>
    </v-progress-linear>

    <div class="budget-breakdown">
      <div v-for="(tokens, field) in activeFieldTokens" :key="field">
        <strong>{{ getFieldLabel(field) }}:</strong> {{ tokens }} tokens
      </div>
    </div>

    <v-alert v-if="budgetPercentage > 90" type="warning" density="compact">
      Token budget exceeded! Consider moving fields to lower priorities or excluding them.
    </v-alert>
  </div>
</template>
```

---

## Objectives

### Primary Goals
1. Create backend endpoint `/api/v1/products/{id}/field-token-estimates` to calculate actual tokens
2. Implement token calculation service following Handover 0052 pattern
3. Update frontend to fetch and display real token estimates
4. Show live token budget updates when dragging fields between priorities
5. Display token breakdown per field (not just total)

### Success Criteria
- ✅ Backend calculates actual token counts for all 15 fields based on product data
- ✅ Token estimates vary by priority level (Priority 1 > Priority 2 > Priority 3)
- ✅ Frontend fetches token estimates on product load
- ✅ Token budget updates in real-time when user drags fields
- ✅ Budget display shows percentage and visual indicator (green/yellow/red)
- ✅ Token breakdown shows per-field contribution
- ✅ Warning shown when budget exceeds 2000 tokens (configurable)

---

## TDD Specifications

### Test 1: Backend Calculates Field Token Estimates
```python
async def test_backend_calculates_field_token_estimates(db_session, sample_product):
    """
    BEHAVIOR: Backend calculates actual token counts for all fields based on product data

    GIVEN: A product with vision document and configuration data
    WHEN: Requesting field token estimates
    THEN: All 15 fields have token counts for each priority level (1, 2, 3)
    """
    # ARRANGE
    from src.giljo_mcp.services.token_estimation_service import TokenEstimationService

    token_service = TokenEstimationService(db_session)

    # Create product with sizeable vision document
    sample_product.vision_documents = [
        VisionDocument(
            content="This is a large vision document..." * 1000,  # ~3000 tokens
            product_id=sample_product.id
        )
    ]

    sample_product.config_data = {
        "tech_stack": {
            "languages": ["Python 3.11", "JavaScript ES2022", "TypeScript 5.0"],
            "backend": ["FastAPI", "SQLAlchemy", "PostgreSQL"],
            "frontend": ["Vue 3", "Vuetify", "Vite"],
        },
        "architecture": {
            "pattern": "Microservices with API gateway",
            "api_style": "RESTful with OpenAPI 3.1 specification",
        },
        "features": {
            "core": ["User authentication", "Project management", "Agent orchestration"]
        }
    }

    await db_session.commit()

    # ACT
    estimates = await token_service.calculate_field_token_estimates(
        product_id=sample_product.id,
        tenant_key=sample_product.tenant_key
    )

    # ASSERT
    # All 15 fields present
    assert len(estimates) == 15

    # Each field has priority estimates
    for field, priority_tokens in estimates.items():
        assert "priority_1" in priority_tokens
        assert "priority_2" in priority_tokens
        assert "priority_3" in priority_tokens

        # Priority 1 > Priority 2 > Priority 3 (more detail = more tokens)
        assert priority_tokens["priority_1"] > priority_tokens["priority_2"]
        assert priority_tokens["priority_2"] > priority_tokens["priority_3"]

    # Vision-heavy fields have significant token counts
    assert estimates["codebase_summary"]["priority_1"] > 1000
```

### Test 2: Token Estimates Reflect Actual Product Data Size
```python
async def test_token_estimates_reflect_product_data_size(db_session):
    """
    BEHAVIOR: Token estimates scale with actual product data size

    GIVEN: Two products with different vision document sizes
    WHEN: Calculating field token estimates
    THEN: Larger vision document results in higher codebase_summary token counts
    """
    # ARRANGE
    from src.giljo_mcp.services.token_estimation_service import TokenEstimationService
    from src.giljo_mcp.models import Product, VisionDocument

    token_service = TokenEstimationService(db_session)

    # Small product (1K token vision)
    small_product = Product(
        name="Small Product",
        tenant_key="test_tenant",
        config_data={"features": {"core": ["Basic feature"]}}
    )
    db_session.add(small_product)
    await db_session.commit()

    small_vision = VisionDocument(
        content="Small vision document." * 50,  # ~150 tokens
        product_id=small_product.id
    )
    db_session.add(small_vision)
    await db_session.commit()

    # Large product (40K token vision)
    large_product = Product(
        name="Large Product",
        tenant_key="test_tenant",
        config_data={"features": {"core": ["Complex feature with many details"]}}
    )
    db_session.add(large_product)
    await db_session.commit()

    large_vision = VisionDocument(
        content="Large vision document with extensive detail..." * 5000,  # ~40K tokens
        product_id=large_product.id
    )
    db_session.add(large_vision)
    await db_session.commit()

    # ACT
    small_estimates = await token_service.calculate_field_token_estimates(
        product_id=small_product.id,
        tenant_key="test_tenant"
    )

    large_estimates = await token_service.calculate_field_token_estimates(
        product_id=large_product.id,
        tenant_key="test_tenant"
    )

    # ASSERT
    # Large product has significantly higher codebase_summary tokens
    assert large_estimates["codebase_summary"]["priority_1"] > small_estimates["codebase_summary"]["priority_1"] * 20
```

### Test 3: Frontend Fetches and Displays Token Estimates
```javascript
// tests/components/FieldPriorityManager.spec.js
import { mount, flushPromises } from '@vue/test-utils';
import { describe, it, expect, vi } from 'vitest';
import FieldPriorityManager from '@/components/FieldPriorityManager.vue';
import { api } from '@/services/api';

describe('FieldPriorityManager Token Estimation', () => {
  it('should fetch token estimates on mount', async () => {
    // ARRANGE
    const mockEstimates = {
      'tech_stack.languages': { priority_1: 120, priority_2: 60, priority_3: 20 },
      'codebase_summary': { priority_1: 5200, priority_2: 2100, priority_3: 800 },
    };

    vi.spyOn(api, 'get').mockResolvedValue({ data: mockEstimates });

    // ACT
    const wrapper = mount(FieldPriorityManager, {
      props: {
        productId: 'test-product-123',
      },
    });

    await flushPromises();

    // ASSERT
    expect(api.get).toHaveBeenCalledWith('/api/v1/products/test-product-123/field-token-estimates');
    expect(wrapper.vm.tokenEstimates).toEqual(mockEstimates);
  });

  it('should display accurate token counts for current priorities', async () => {
    // ARRANGE
    const mockEstimates = {
      'tech_stack.languages': { priority_1: 120, priority_2: 60, priority_3: 20 },
      'tech_stack.backend': { priority_1: 150, priority_2: 75, priority_3: 25 },
    };

    vi.spyOn(api, 'get').mockResolvedValue({ data: mockEstimates });

    const wrapper = mount(FieldPriorityManager, {
      props: {
        productId: 'test-product-123',
        fields: {
          'tech_stack.languages': 1,  // Priority 1
          'tech_stack.backend': 2,    // Priority 2
        },
      },
    });

    await flushPromises();

    // ACT
    const totalTokens = wrapper.vm.calculateTotalTokens();

    // ASSERT
    // tech_stack.languages (P1) = 120 tokens
    // tech_stack.backend (P2) = 75 tokens
    // Total = 195 tokens
    expect(totalTokens).toBe(195);
  });
});
```

### Test 4: Live Token Budget Updates on Field Drag
```javascript
// tests/components/FieldPriorityManager.spec.js
describe('FieldPriorityManager Live Budget Updates', () => {
  it('should update token budget when field is dragged to different priority', async () => {
    // ARRANGE
    const mockEstimates = {
      'tech_stack.languages': { priority_1: 120, priority_2: 60, priority_3: 20 },
    };

    vi.spyOn(api, 'get').mockResolvedValue({ data: mockEstimates });

    const wrapper = mount(FieldPriorityManager, {
      props: {
        productId: 'test-product-123',
        fields: {
          'tech_stack.languages': 1,  // Initially Priority 1 (120 tokens)
        },
      },
    });

    await flushPromises();

    // Initial token count
    expect(wrapper.vm.currentTokens).toBe(120);

    // ACT - Drag field from Priority 1 to Priority 2
    await wrapper.vm.handleFieldDrag('tech_stack.languages', 1, 2);
    await wrapper.vm.$nextTick();

    // ASSERT - Token count updated to Priority 2 estimate
    expect(wrapper.vm.currentTokens).toBe(60);
    expect(wrapper.find('.token-budget-display').text()).toContain('60');
  });

  it('should show warning when budget exceeds limit', async () => {
    // ARRANGE
    const mockEstimates = {
      'codebase_summary': { priority_1: 5200, priority_2: 2100, priority_3: 800 },
      'tech_stack.languages': { priority_1: 120, priority_2: 60, priority_3: 20 },
    };

    vi.spyOn(api, 'get').mockResolvedValue({ data: mockEstimates });

    const wrapper = mount(FieldPriorityManager, {
      props: {
        productId: 'test-product-123',
        tokenBudgetLimit: 2000,  // Budget limit
        fields: {
          'codebase_summary': 1,      // 5200 tokens (OVER BUDGET)
          'tech_stack.languages': 1,  // 120 tokens
        },
      },
    });

    await flushPromises();

    // ASSERT
    expect(wrapper.vm.currentTokens).toBe(5320);  // Over budget
    expect(wrapper.vm.budgetPercentage).toBeGreaterThan(100);

    const warning = wrapper.find('.budget-warning');
    expect(warning.exists()).toBe(true);
    expect(warning.text()).toContain('Token budget exceeded');
  });
});
```

### Test 5: Token Breakdown Shows Per-Field Contribution
```javascript
// tests/components/TokenBudgetBreakdown.spec.js
import { mount } from '@vue/test-utils';
import { describe, it, expect } from 'vitest';
import TokenBudgetBreakdown from '@/components/TokenBudgetBreakdown.vue';

describe('TokenBudgetBreakdown Component', () => {
  it('should display token contribution for each active field', () => {
    // ARRANGE
    const activeFieldTokens = {
      'tech_stack.languages': 120,
      'tech_stack.backend': 150,
      'codebase_summary': 5200,
      'architecture_overview': 2400,
    };

    const wrapper = mount(TokenBudgetBreakdown, {
      props: {
        activeFieldTokens,
        totalTokens: 7870,
      },
    });

    // ASSERT
    // Should show all 4 fields
    const fieldItems = wrapper.findAll('.field-token-item');
    expect(fieldItems.length).toBe(4);

    // Should show human-readable labels (not field paths)
    expect(wrapper.text()).toContain('Programming Languages');
    expect(wrapper.text()).toContain('Backend Stack');
    expect(wrapper.text()).toContain('Codebase Summary');
    expect(wrapper.text()).toContain('Architecture Overview');

    // Should show token counts
    expect(wrapper.text()).toContain('120 tokens');
    expect(wrapper.text()).toContain('150 tokens');
    expect(wrapper.text()).toContain('5,200 tokens');
    expect(wrapper.text()).toContain('2,400 tokens');

    // Should show percentage contribution
    expect(wrapper.text()).toContain('66%');  // codebase_summary: 5200 / 7870 ≈ 66%
  });

  it('should sort fields by token count (descending)', () => {
    // ARRANGE
    const activeFieldTokens = {
      'tech_stack.languages': 120,         // 4th
      'codebase_summary': 5200,            // 1st
      'tech_stack.backend': 150,           // 3rd
      'architecture_overview': 2400,       // 2nd
    };

    const wrapper = mount(TokenBudgetBreakdown, {
      props: {
        activeFieldTokens,
        totalTokens: 7870,
      },
    });

    // ACT
    const fieldItems = wrapper.findAll('.field-token-item');

    // ASSERT - Sorted by token count (highest first)
    expect(fieldItems[0].text()).toContain('Codebase Summary');      // 5200
    expect(fieldItems[1].text()).toContain('Architecture Overview'); // 2400
    expect(fieldItems[2].text()).toContain('Backend Stack');         // 150
    expect(fieldItems[3].text()).toContain('Programming Languages'); // 120
  });
});
```

---

## Implementation Plan

### Step 1: Create TokenEstimationService (Backend)
**File**: `src/giljo_mcp/services/token_estimation_service.py` (NEW FILE)

**Content**:
```python
"""
Token Estimation Service for Product Field Priority System.

Calculates actual token counts for product configuration fields based on
real product data (vision documents, configuration, codebase).

Follows pattern from Handover 0052 (Product Configuration Token Calculation).
"""

import logging
from typing import Dict, Optional

import tiktoken
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Product, VisionDocument
from ..repositories.context_repository import ContextRepository


logger = logging.getLogger(__name__)


class TokenEstimationService:
    """Calculate token estimates for product fields based on actual data."""

    def __init__(self, db_session: AsyncSession):
        """
        Initialize TokenEstimationService.

        Args:
            db_session: Database session for data access
        """
        self.db = db_session
        self.context_repo = ContextRepository(db_session)

        # Initialize tokenizer (cl100k_base encoding for GPT-4/Claude)
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.warning(f"Failed to load tiktoken: {e}. Using fallback.")
            self.tokenizer = None

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken.

        Args:
            text: Text to count tokens for

        Returns:
            Token count
        """
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Fallback: 4 characters ≈ 1 token
            return len(text) // 4

    async def calculate_field_token_estimates(
        self,
        product_id: int,
        tenant_key: str
    ) -> Dict[str, Dict[str, int]]:
        """
        Calculate token estimates for all fields at each priority level.

        Args:
            product_id: Product ID
            tenant_key: Tenant isolation key

        Returns:
            Dict mapping field paths to priority-level token counts:
            {
                "tech_stack.languages": {
                    "priority_1": 120,
                    "priority_2": 60,
                    "priority_3": 20
                },
                ...
            }
        """
        # Fetch product data
        product = await self.db.get(Product, product_id)

        if not product or product.tenant_key != tenant_key:
            raise ValueError(f"Product {product_id} not found or access denied")

        estimates = {}

        # Product config fields (13 fields)
        config_estimates = await self._estimate_config_fields(product)
        estimates.update(config_estimates)

        # Context fields (2 fields)
        context_estimates = await self._estimate_context_fields(product)
        estimates.update(context_estimates)

        return estimates

    async def _estimate_config_fields(self, product: Product) -> Dict[str, Dict[str, int]]:
        """Estimate tokens for product configuration fields."""
        estimates = {}
        config = product.config_data or {}

        # Tech Stack Fields
        estimates["tech_stack.languages"] = self._estimate_field(
            data=config.get("tech_stack", {}).get("languages", []),
            full_tokens=120,
            summary_tokens=60,
            minimal_tokens=20
        )

        estimates["tech_stack.backend"] = self._estimate_field(
            data=config.get("tech_stack", {}).get("backend", []),
            full_tokens=150,
            summary_tokens=75,
            minimal_tokens=25
        )

        estimates["tech_stack.frontend"] = self._estimate_field(
            data=config.get("tech_stack", {}).get("frontend", []),
            full_tokens=140,
            summary_tokens=70,
            minimal_tokens=25
        )

        estimates["tech_stack.database"] = self._estimate_field(
            data=config.get("tech_stack", {}).get("database", ""),
            full_tokens=100,
            summary_tokens=50,
            minimal_tokens=20
        )

        estimates["tech_stack.infrastructure"] = self._estimate_field(
            data=config.get("tech_stack", {}).get("infrastructure", ""),
            full_tokens=200,
            summary_tokens=100,
            minimal_tokens=35
        )

        # Architecture Fields
        estimates["architecture.pattern"] = self._estimate_field(
            data=config.get("architecture", {}).get("pattern", ""),
            full_tokens=80,
            summary_tokens=40,
            minimal_tokens=15
        )

        estimates["architecture.api_style"] = self._estimate_field(
            data=config.get("architecture", {}).get("api_style", ""),
            full_tokens=90,
            summary_tokens=45,
            minimal_tokens=20
        )

        estimates["architecture.design_patterns"] = self._estimate_field(
            data=config.get("architecture", {}).get("design_patterns", []),
            full_tokens=180,
            summary_tokens=90,
            minimal_tokens=30
        )

        estimates["architecture.notes"] = self._estimate_field(
            data=config.get("architecture", {}).get("notes", ""),
            full_tokens=300,
            summary_tokens=150,
            minimal_tokens=50
        )

        # Feature Fields
        estimates["features.core"] = self._estimate_field(
            data=config.get("features", {}).get("core", []),
            full_tokens=250,
            summary_tokens=125,
            minimal_tokens=40
        )

        # Test Config Fields
        estimates["test_config.strategy"] = self._estimate_field(
            data=config.get("test_config", {}).get("strategy", ""),
            full_tokens=120,
            summary_tokens=60,
            minimal_tokens=20
        )

        estimates["test_config.frameworks"] = self._estimate_field(
            data=config.get("test_config", {}).get("frameworks", []),
            full_tokens=100,
            summary_tokens=50,
            minimal_tokens=20
        )

        estimates["test_config.coverage_target"] = self._estimate_field(
            data=config.get("test_config", {}).get("coverage_target", ""),
            full_tokens=40,
            summary_tokens=20,
            minimal_tokens=10
        )

        return estimates

    async def _estimate_context_fields(self, product: Product) -> Dict[str, Dict[str, int]]:
        """Estimate tokens for context fields (codebase, architecture)."""
        estimates = {}

        # Codebase Summary (based on vision document size)
        vision_text = product.primary_vision_text or ""
        vision_tokens = self._count_tokens(vision_text)

        estimates["codebase_summary"] = {
            "priority_1": max(vision_tokens, 500),        # Full vision
            "priority_2": max(vision_tokens // 3, 200),   # Condensed summary
            "priority_3": max(vision_tokens // 10, 100),  # Brief overview
        }

        # Architecture Overview
        architecture_notes = product.config_data.get("architecture", {}).get("notes", "")
        architecture_tokens = self._count_tokens(architecture_notes)

        estimates["architecture_overview"] = {
            "priority_1": max(architecture_tokens + 500, 800),   # Full architecture + context
            "priority_2": max(architecture_tokens // 2, 300),     # Summary
            "priority_3": max(architecture_tokens // 5, 150),     # Brief
        }

        return estimates

    def _estimate_field(
        self,
        data: any,
        full_tokens: int,
        summary_tokens: int,
        minimal_tokens: int
    ) -> Dict[str, int]:
        """
        Estimate tokens for a field at different priority levels.

        Args:
            data: Field data (string, list, dict, etc.)
            full_tokens: Estimate for Priority 1 (full detail)
            summary_tokens: Estimate for Priority 2 (summary)
            minimal_tokens: Estimate for Priority 3 (minimal)

        Returns:
            Dict with priority-level estimates
        """
        # Scale estimates based on actual data size
        if isinstance(data, str):
            actual_tokens = self._count_tokens(data)
        elif isinstance(data, list):
            actual_tokens = sum(self._count_tokens(str(item)) for item in data)
        else:
            actual_tokens = self._count_tokens(str(data))

        # Use actual tokens if significantly different from static estimate
        if actual_tokens > full_tokens * 2:
            # Data is larger than expected, scale up
            scale = actual_tokens / full_tokens
            full_tokens = int(actual_tokens)
            summary_tokens = int(summary_tokens * scale)
            minimal_tokens = int(minimal_tokens * scale)

        return {
            "priority_1": full_tokens,
            "priority_2": summary_tokens,
            "priority_3": minimal_tokens,
        }
```

### Step 2: Create API Endpoint (Backend)
**File**: `api/endpoints/products.py`
**New Endpoint**:

```python
@router.get("/{product_id}/field-token-estimates", response_model=FieldTokenEstimatesResponse)
async def get_field_token_estimates(
    product_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get token estimates for all product fields at each priority level.

    Returns actual token counts based on product data (not static estimates).
    Used by frontend to display accurate token budget information.

    Args:
        product_id: Product ID

    Returns:
        FieldTokenEstimatesResponse with token estimates for all fields
    """
    from src.giljo_mcp.services.token_estimation_service import TokenEstimationService

    token_service = TokenEstimationService(db)

    try:
        estimates = await token_service.calculate_field_token_estimates(
            product_id=product_id,
            tenant_key=current_user.tenant_key
        )

        return FieldTokenEstimatesResponse(
            product_id=product_id,
            field_estimates=estimates
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

### Step 3: Create Frontend Token Budget Component
**File**: `frontend/src/components/TokenBudgetDisplay.vue` (NEW FILE)

**Content**: (See design mockup above - component with progress bar, breakdown, warnings)

### Step 4: Update Field Priority Manager (Frontend)
**File**: `frontend/src/components/FieldPriorityManager.vue`

**Add**:
```vue
<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { api } from '@/services/api';
import TokenBudgetDisplay from '@/components/TokenBudgetDisplay.vue';

const props = defineProps({
  productId: String,
  tokenBudgetLimit: { type: Number, default: 2000 },
});

const tokenEstimates = ref({});
const currentTokens = ref(0);

onMounted(async () => {
  await fetchTokenEstimates();
  calculateCurrentTokens();
});

async function fetchTokenEstimates() {
  const response = await api.get(`/api/v1/products/${props.productId}/field-token-estimates`);
  tokenEstimates.value = response.data.field_estimates;
}

function calculateCurrentTokens() {
  let total = 0;

  for (const [field, priority] of Object.entries(fieldPriorities.value)) {
    if (priority && tokenEstimates.value[field]) {
      const priorityKey = `priority_${priority}`;
      total += tokenEstimates.value[field][priorityKey] || 0;
    }
  }

  currentTokens.value = total;
}

watch(() => fieldPriorities.value, () => {
  calculateCurrentTokens();
}, { deep: true });
</script>
```

### Step 5: Add Unit Tests
**Files**:
- `tests/services/test_token_estimation_service.py` (Backend)
- `frontend/tests/components/TokenBudgetDisplay.spec.js` (Frontend)
- `frontend/tests/components/FieldPriorityManager.spec.js` (Frontend - update)

---

## Files to Modify

### Backend (4 files)
1. **`src/giljo_mcp/services/token_estimation_service.py`** (NEW FILE)
2. **`api/endpoints/products.py`** (Add endpoint)
3. **`src/giljo_mcp/schemas/product_schemas.py`** (Add response schema)
4. **`tests/services/test_token_estimation_service.py`** (NEW FILE)

### Frontend (5 files)
1. **`frontend/src/components/TokenBudgetDisplay.vue`** (NEW FILE)
2. **`frontend/src/components/TokenBudgetBreakdown.vue`** (NEW FILE)
3. **`frontend/src/components/FieldPriorityManager.vue`** (Update)
4. **`frontend/tests/components/TokenBudgetDisplay.spec.js`** (NEW FILE)
5. **`frontend/tests/components/FieldPriorityManager.spec.js`** (Update)

---

## Validation Checklist

- [ ] Backend tests pass: `pytest tests/services/test_token_estimation_service.py -v`
- [ ] Frontend tests pass: `npm run test:unit`
- [ ] API endpoint returns token estimates for all 15 fields
- [ ] Token estimates reflect actual product data size
- [ ] Frontend displays real-time token budget
- [ ] Dragging fields updates budget immediately
- [ ] Warning shown when budget exceeds limit
- [ ] Token breakdown shows per-field contribution
- [ ] No regressions in field priority functionality

---

## Dependencies

### External
- tiktoken (Python - for accurate token counting)

### Internal
- Handover 0052: Product Configuration Token Calculation (pattern reference)
- Handover 0308: Frontend Field Labels & Tooltips (UI foundation)

---

**Status**: Ready for execution
**Estimated Time**: 5-6 hours (backend: 3h, frontend: 2h, tests: 1h)
**Agent Budget**: 110K tokens
**Next Handover**: 0310 (Integration Testing & Validation)
