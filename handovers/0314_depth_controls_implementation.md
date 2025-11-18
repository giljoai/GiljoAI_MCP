# Handover 0314: Depth Controls Implementation

**Status**: Not Started
**Tool**: Claude Code (CLI) - Requires backend + frontend implementation
**Created**: 2025-11-17
**Dependencies**: 0312 (v2.0 Design), 0313 (Priority System)
**Next**: 0315 (MCP Thin Client)

---

## Objective

Add depth configuration UI and database schema. Implement token calculator for real-time estimation of token usage per depth setting. Give developers fine-grained control over HOW MUCH detail to fetch per context source.

---

## Scope

### Backend Changes

1. **Add Database Column**:
   ```sql
   -- Migration script
   ALTER TABLE users ADD COLUMN depth_config JSONB DEFAULT '{
     "vision_chunking": "moderate",
     "memory_last_n_projects": 3,
     "git_commits": 25,
     "agent_template_detail": "standard",
     "tech_stack_sections": "all",
     "architecture_depth": "overview"
   }'::jsonb;
   ```

2. **Update User Model**:
   ```python
   # src/giljo_mcp/models.py
   class User(Base):
       # ... existing fields ...
       depth_config = Column(JSONB, nullable=False, default={
           "vision_chunking": "moderate",
           "memory_last_n_projects": 3,
           "git_commits": 25,
           "agent_template_detail": "standard",
           "tech_stack_sections": "all",
           "architecture_depth": "overview"
       })
   ```

3. **Create Pydantic Schema**:
   ```python
   # api/schemas/user_schemas.py
   class DepthConfig(BaseModel):
       vision_chunking: Literal["none", "light", "moderate", "heavy"] = "moderate"
       memory_last_n_projects: Literal[1, 3, 5, 10] = 3
       git_commits: Literal[10, 25, 50, 100] = 25
       agent_template_detail: Literal["minimal", "standard", "full"] = "standard"
       tech_stack_sections: Literal["required", "all"] = "all"
       architecture_depth: Literal["overview", "detailed"] = "overview"

   class UpdateDepthConfigRequest(BaseModel):
       depth_config: DepthConfig
   ```

4. **Validation Logic**:
   - Validate depth parameter options per source (e.g., vision_chunking must be none/light/moderate/heavy)
   - Reject invalid combinations
   - Warn if estimated total exceeds token budget (via token calculator)

5. **API Endpoint**:
   - Endpoint: `PUT /api/users/me/context/depth`
   - Request body: `{"depth_config": {"vision_chunking": "heavy", ...}}`
   - Response: Updated depth config + token estimate + WebSocket event

6. **Token Calculator Service**:
   ```python
   # src/giljo_mcp/services/depth_token_estimator.py
   class DepthTokenEstimator:
       """Estimate token usage based on depth settings"""

       TOKEN_ESTIMATES = {
           "vision_chunking": {"none": 50000, "light": 10000, "moderate": 17500, "heavy": 30000},
           "memory_last_n_projects": {1: 500, 3: 1500, 5: 2500, 10: 5000},
           "git_commits": {10: 500, 25: 1250, 50: 2500, 100: 5000},
           "agent_template_detail": {"minimal": 400, "standard": 800, "full": 2400},
           "tech_stack_sections": {"required": 200, "all": 400},
           "architecture_depth": {"overview": 300, "detailed": 1500}
       }

       @staticmethod
       def estimate_total(depth_config: DepthConfig) -> int:
           """Calculate total estimated tokens"""
           total = 0
           total += DepthTokenEstimator.TOKEN_ESTIMATES["vision_chunking"][depth_config.vision_chunking]
           total += DepthTokenEstimator.TOKEN_ESTIMATES["memory_last_n_projects"][depth_config.memory_last_n_projects]
           total += DepthTokenEstimator.TOKEN_ESTIMATES["git_commits"][depth_config.git_commits]
           total += DepthTokenEstimator.TOKEN_ESTIMATES["agent_template_detail"][depth_config.agent_template_detail]
           total += DepthTokenEstimator.TOKEN_ESTIMATES["tech_stack_sections"][depth_config.tech_stack_sections]
           total += DepthTokenEstimator.TOKEN_ESTIMATES["architecture_depth"][depth_config.architecture_depth]
           return total
   ```

7. **WebSocket Metadata Emission**:
   - Event: `depth_config_updated`
   - Payload: `{user_id, timestamp, total_estimated_tokens, changes_applied: {...}}`

### Frontend Changes

1. **New Component**: `DepthConfiguration.vue`
   - Location: `frontend/src/components/settings/DepthConfiguration.vue`
   - Features:
     - Dropdown/slider for each depth setting
     - Real-time token estimates per source
     - Total estimated tokens display
     - Warning if total exceeds user's token budget
     - WebSocket listener for `depth_config_updated` events

2. **UI Design** (ASCII mockup in 0312):
   ```
   Depth Configuration

   Configure granularity for each context source
   Higher depth = more tokens, richer context

   Vision Documents
   Chunking: [None] [Light] [●Moderate] [Heavy]
   Est. tokens: ~17.5K (5 chunks × ~3.5K each)

   360 Memory (Project History)
   Last N projects: [1] [●3] [5] [10]
   Est. tokens: ~1.5K (3 projects × ~500 tokens summary)

   Git History
   Commits: [10] [●25] [50] [100]
   Est. tokens: ~1.25K (25 commits × ~50 tokens each)

   Agent Templates
   Detail: [Minimal] [●Standard] [Full]
   Est. tokens: ~800 (8 agents × ~100 tokens standard)

   Tech Stack
   Sections: [Required] [●All]
   Est. tokens: ~400 (all fields included)

   Architecture
   Depth: [●Overview] [Detailed]
   Est. tokens: ~300 (high-level summary)

   ────────────────────────────────────────────
   Total Estimated Tokens: ~21.75K
   Your Token Budget: 2000
   ⚠️ Warning: Estimated usage exceeds budget by 11x

   [Save Depth Configuration]
   ```

3. **Token Calculator (Frontend)**:
   ```typescript
   // frontend/src/services/depthTokenEstimator.ts
   export class DepthTokenEstimator {
       private static TOKEN_ESTIMATES = {
           // Same as backend estimates
       };

       static estimateTotal(depthConfig: DepthConfig): number {
           // Calculate real-time as user adjusts sliders
       }

       static estimateBySource(source: string, value: any): number {
           // Return estimate for individual source
       }
   }
   ```

4. **Integration with My Settings**:
   - Add "Context Configuration" section to My Settings
   - Tab 1: Priority Configuration (handover 0313)
   - Tab 2: Depth Configuration (this handover)

---

## Code Reuse from v1.0

**Reuse**:
- `UserService` structure for CRUD operations
- Frontend settings layout from `MySettings.vue`
- WebSocket emission pattern

**New**:
- `User.depth_config` JSONB column (database migration)
- `DepthTokenEstimator` service (Python + TypeScript)
- `DepthConfiguration.vue` component

---

## Testing Strategy

### Unit Tests (`tests/api/test_depth_controls.py`)

1. **Depth Validation**:
   - Test depth parameter options per source (valid values only)
   - Test rejection of invalid options (e.g., vision_chunking="invalid")
   - Test default depth settings for new users

2. **Token Calculator Accuracy**:
   - Test token estimates within ±10% margin
   - Test total calculation (sum of all sources)
   - Test edge cases (all "none"/"minimal" vs all "heavy"/"full")

3. **API Endpoint**:
   - Test successful depth update
   - Test validation errors (invalid depth values)
   - Test multi-tenant isolation
   - Test WebSocket metadata emission

### Frontend Tests (`tests/frontend/DepthConfiguration.spec.ts`)

1. **UI Rendering**:
   - Test all depth controls render correctly
   - Test real-time token estimates update on slider/dropdown change
   - Test warning displayed when exceeding token budget

2. **API Integration**:
   - Test save button calls API with updated depth config
   - Test WebSocket event updates UI without page reload
   - Test error handling (API failure)

**Coverage Target**: >80%

---

## Deliverables

1. Database migration script (add `depth_config` column)
2. API endpoint: `PUT /api/users/me/context/depth`
3. Frontend component: `DepthConfiguration.vue`
4. Token calculator service: `DepthTokenEstimator` (Python + TypeScript)
5. Tests: `test_depth_controls.py` (>80% coverage)
6. Updated documentation: My Settings → Context Configuration → Depth Tab

---

## Success Criteria

- [ ] `User.depth_config` JSONB column added to database
- [ ] Depth controls support per-source granularity (6 sources)
- [ ] Token calculator estimates usage within ±10% accuracy
- [ ] Frontend displays real-time token estimates
- [ ] Warning displayed if estimated usage exceeds token budget
- [ ] WebSocket metadata emitted on depth changes
- [ ] Tests pass with >80% coverage
- [ ] Default depth settings seeded for new users

---

## Dependencies

**Blocked by**:
- 0312 (v2.0 Design)
- 0313 (Priority System) - depth controls independent but UX better if priority system complete

**Blocks**: 0315 (MCP Thin Client) - MCP tools need depth config to determine HOW MUCH data to return

---

## Notes

**Database Migration Required**: Adding new `User.depth_config` JSONB column. Update `install.py` to run migration script.

**Token Calculator Accuracy**: Estimates are approximate (±10% margin). Actual token usage depends on data size (e.g., vision document length, 360 memory project count).

**Follow 013A Patterns**:
- Use `UserService` for CRUD operations
- Emit WebSocket events for real-time UI updates
- Multi-tenant isolation (filter by user_id/tenant_key)
- Production-grade code from start (no TODOs, no bandaids)
- Use `pathlib.Path()` for all file operations
