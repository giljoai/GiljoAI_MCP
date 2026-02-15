# Handover 0283: Documentation Remediation - Monolithic Context

**Status**: 📋 READY FOR IMPLEMENTATION
**Priority**: 🔴 CRITICAL
**Parent**: Handover 0280 (Monolithic Context Architecture Roadmap)
**Prerequisite**: Handover 0281 (Backend) + 0282 (Testing) COMPLETE
**Created**: 2025-12-01
**Estimated Effort**: 4 days (12-16 hours)
**Team**: Documentation Manager Agent

---

## 🎯 Mission

Update ALL documentation to reflect monolithic context architecture:
1. **4 Critical Reference Docs** (user-specified) - 6 hours
2. **Core Documentation** (ORCHESTRATOR.md, CLAUDE.md) - 4 hours
3. **32 Completed Handovers** (batch deprecation notices) - 3 hours
4. **Code Comments** (5 files) - 2 hours

**Outcome**: Consistent documentation where no file references outdated modular fetch_* architecture.

---

## 📋 Documentation Update Checklist

### Phase 1: Critical Reference Docs (Days 1-2, 6 hours)

#### File 1: `F:\GiljoAI_MCP\handovers\Reference_docs\Dynamic_context.md`

**Effort**: 3 hours

**Changes Required**:

- [ ] **Task 1.1**: Add architecture change notice at top
  ```markdown
  ---
  **ARCHITECTURE CHANGE NOTICE** (Handover 0280 - December 2025)

  This document describes OLD v3.1 modular architecture where orchestrators called 9 separate fetch_* tools.

  **CURRENT ARCHITECTURE (v3.2+)**: Single `get_orchestrator_instructions()` returns complete context with user-configured priority framing and depth control.

  See: [Handover 0280](../0280_monolithic_context_architecture_roadmap.md) for current architecture.

  **This document remains for HISTORICAL REFERENCE ONLY.**
  ---
  ```

- [ ] **Task 1.2**: Rewrite "Context Sources" section (lines 92-131)
  **OLD TEXT** (references 9 fetch_* tools):
  ```
  Context sources include:
  1. Product Core (fetch_product_context)
  2. Vision Documents (fetch_vision_document)
  3. Tech Stack (fetch_tech_stack)
  ...
  ```

  **NEW TEXT** (monolithic approach):
  ```
  **v3.2+ Architecture**: All context delivered via single `get_orchestrator_instructions()` call.

  Context dimensions (9 total):
  1. Product Core (Priority 1 - CRITICAL by default)
  2. Vision Documents (Priority 2 - IMPORTANT, depth: none/light/moderate/heavy)
  3. Tech Stack (Priority 2 - IMPORTANT)
  4. Architecture (Priority 3 - REFERENCE)
  5. Testing Config (Priority 3 - REFERENCE)
  6. 360 Memory (Priority 2 - IMPORTANT, depth: 1/3/5/10 projects)
  7. Git History (Priority 4 - EXCLUDED by default, depth: 5/15/25 commits)
  8. Agent Templates (Priority 2 - IMPORTANT, depth: minimal/standard/full)
  9. Project Context (Priority 1 - CRITICAL)

  **User Control**: Via Context Priority Config in User Settings
  - Toggle: ON/OFF per dimension (0 bytes when OFF)
  - Priority: 1-4 (CRITICAL/IMPORTANT/REFERENCE/EXCLUDED)
  - Depth: Control token volume per dimension
  ```

- [ ] **Task 1.3**: Update staging prompt flow (lines 56-89)
  **Remove**: References to orchestrator calling individual tools during staging
  **Add**: Description of monolithic context delivery

- [ ] **Task 1.4**: Update edge cases section (lines 134-150)
  **Remove**: "Dynamic refresh" use case (NEVER HAPPENS)
  **Add**: User control edge cases (missing config, graceful degradation)

---

#### File 2: `F:\GiljoAI_MCP\handovers\Reference_docs\Mcp_tool_catalog.md`

**Effort**: 2 hours

**Changes Required**:

- [ ] **Task 2.1**: Add architecture change notice at top (same as File 1)

- [ ] **Task 2.2**: Delete 9 fetch_* tool entries from catalog
  **DELETE SECTIONS**:
  - `### fetch_product_context`
  - `### fetch_vision_document`
  - `### fetch_tech_stack`
  - `### fetch_architecture`
  - `### fetch_testing_config`
  - `### fetch_360_memory`
  - `### fetch_git_history`
  - `### fetch_agent_templates`
  - `### fetch_project_context`

- [ ] **Task 2.3**: Update `get_orchestrator_instructions` entry
  **EXPAND SECTION** with:
  - New signature: `get_orchestrator_instructions(orchestrator_id, tenant_key, user_id=None)`
  - Response structure (mission, field_priorities_applied, depth_config_applied, warnings)
  - Priority framing examples (CRITICAL/IMPORTANT/REFERENCE)
  - Depth config behavior
  - Usage examples

- [ ] **Task 2.4**: Add "Context Management" section
  **NEW SECTION**:
  ```markdown
  ## Context Management (v3.2+)

  **Single Tool, Complete Context**: `get_orchestrator_instructions()` replaces all individual fetch_* tools.

  **User Configuration**:
  - Field Priorities: Set via My Settings → Context → Field Priority Configuration
  - Depth Config: Set via My Settings → Context → Depth Configuration

  **Priority Framing**:
  - Priority 1: **CRITICAL** - "REQUIRED FOR ALL OPERATIONS"
  - Priority 2: **IMPORTANT** - "High priority context"
  - Priority 3: **REFERENCE** - "Supplemental information"
  - Priority 4: **EXCLUDED** - 0 bytes included

  **Depth Control**:
  - Vision Documents: none (0) / light (2 chunks) / moderate (4) / heavy (6)
  - 360 Memory: 1 / 3 / 5 / 10 projects
  - Git History: 5 / 15 / 25 commits
  - Agent Templates: minimal / standard / full

  **Token Savings**: ~5,400 tokens per orchestrator (vs old 9-tool system)
  ```

---

#### File 3: `F:\GiljoAI_MCP\handovers\Reference_docs\start_to_finish_agent_FLOW.md`

**Effort**: 1 hour

**Changes Required**:

- [ ] **Task 3.1**: Add architecture change notice at top (same format)

- [ ] **Task 3.2**: Update "Orchestrator Staging Phase" section
  **OLD**: Orchestrator calls 9 fetch_* tools sequentially
  **NEW**: Orchestrator calls `get_orchestrator_instructions()` once

- [ ] **Task 3.3**: Update workflow diagram
  **OLD**:
  ```
  Orchestrator → fetch_product_context()
              → fetch_vision_document()
              → fetch_tech_stack()
              ... (9 calls)
              → Analyze context → Create mission
  ```

  **NEW**:
  ```
  Orchestrator → get_orchestrator_instructions(orchestrator_id, tenant_key)
              → Receive complete mission with priority framing
              → Create agent assignments
  ```

---

#### File 4: `F:\GiljoAI_MCP\CLAUDE.md`

**Effort**: 1 hour

**Changes Required**:

- [ ] **Task 4.1**: Update "Context Management (v2.0)" section
  **Find**: Lines 63-98 (Context Management section)
  **Update**: Remove references to 9 MCP context tools
  **Add**: Monolithic context description

  **NEW TEXT**:
  ```markdown
  ## Context Management (v2.0 - Monolithic Architecture)

  GiljoAI uses a 2-dimensional context management model:

  **Priority Dimension** (WHAT to fetch):
  - Priority 1 (CRITICAL) - Always included, emphasized in prompt
  - Priority 2 (IMPORTANT) - High priority, standard emphasis
  - Priority 3 (NICE_TO_HAVE) - Medium priority, subdued emphasis
  - Priority 4 (EXCLUDED) - Never included (0 bytes)

  **Depth Dimension** (HOW MUCH detail):
  - Vision Documents: none/light/moderate/heavy (0-25K tokens)
  - 360 Memory: 1/3/5/10 projects (500-5K tokens)
  - Git History: 5/15/25 commits (500-2.5K tokens)
  - Agent Templates: minimal/standard/full (400-2.4K tokens)

  **Single MCP Context Tool**:
  - `get_orchestrator_instructions(orchestrator_id, tenant_key, user_id)` - Returns complete context with priority framing and depth control

  **Configuration**:
  - Priority: My Settings → Context → Field Priority Configuration
  - Depth: My Settings → Context → Depth Configuration

  **Token Efficiency**: ~5,400 tokens saved per orchestrator (vs old 9-tool system)
  ```

- [ ] **Task 4.2**: Update "Orchestrator Workflow" section
  **Find**: Lines 120-145
  **Update**: Remove references to multiple tool calls
  **Add**: Single tool call example

---

### Phase 2: Core Documentation (Day 3, 4 hours)

#### File 5: `F:\GiljoAI_MCP\docs\ORCHESTRATOR.md`

**Effort**: 2 hours

**Changes Required**:

- [ ] **Task 5.1**: Add "Monolithic Context Architecture (v3.2+)" section
  **Location**: After "Context Management" section
  **Content**: Complete description of new architecture

- [ ] **Task 5.2**: Update "Context Fetching" section
  **Remove**: References to 9 individual tools
  **Add**: Single tool description with examples

- [ ] **Task 5.3**: Add "Migration from v3.1" section
  **Content**: Guide for updating old orchestrators

#### File 6: `F:\GiljoAI_MCP\docs\components\CONTEXT_CONFIGURATOR.md`

**Effort**: 1 hour

**Changes Required**:

- [ ] **Task 6.1**: Update component description
  **Clarify**: 9 context dimensions → 1 MCP tool (not 9 tools)

- [ ] **Task 6.2**: Update "Badge System" section
  **Explain**: Badges represent context dimensions, not individual MCP tools

#### File 7: `F:\GiljoAI_MCP\docs\README_FIRST.md`

**Effort**: 30 minutes

**Changes Required**:

- [ ] **Task 7.1**: Update navigation links
  **Add**: Link to Handover 0280 (Monolithic Context Architecture)
  **Update**: Context Management description

---

### Phase 3: Batch Deprecation Notices (Day 3, 3 hours)

**Target**: 32 completed handovers mentioning fetch_* or modular context

**Batch Operation**:

- [ ] **Task 8.1**: Create script to prepend deprecation notice
  **File**: `handovers/scripts/add_deprecation_notices.sh`
  ```bash
  #!/bin/bash
  # Prepend deprecation notice to handover files

  NOTICE="---
  **ARCHITECTURE CHANGE NOTICE** (Handover 0280 - December 2025)

  This handover references OLD v3.1 modular architecture (9 fetch_* tools).

  **CURRENT ARCHITECTURE (v3.2+)**: Single \`get_orchestrator_instructions()\` returns complete context.

  See: [Handover 0280](./0280_monolithic_context_architecture_roadmap.md)

  **HISTORICAL REFERENCE ONLY.**
  ---

  "

  while IFS= read -r file; do
      echo "Updating: $file"
      # Create temp file with notice + original content
      echo "$NOTICE" | cat - "$file" > temp && mv temp "$file"
  done < "$1"
  ```

- [ ] **Task 8.2**: Create file list
  **File**: `handovers/scripts/files_to_update.txt`
  ```
  handovers/completed/0246a_orchestrator_staging_workflow.md
  handovers/completed/0246b_generic_agent_template.md
  handovers/completed/0246c_dynamic_agent_discovery.md
  handovers/completed/0279_context_priority_integration_fix.md
  ... (32 files total)
  ```

- [ ] **Task 8.3**: Run batch update
  ```bash
  cd F:\GiljoAI_MCP
  chmod +x handovers/scripts/add_deprecation_notices.sh
  ./handovers/scripts/add_deprecation_notices.sh handovers/scripts/files_to_update.txt
  ```

- [ ] **Task 8.4**: Verify 32 files updated
  ```bash
  # Check that all files have deprecation notice
  grep -l "ARCHITECTURE CHANGE NOTICE" handovers/completed/*.md | wc -l
  # Should output: 32
  ```

**Special Case - Handover 0279**:

- [ ] **Task 8.5**: Mark Handover 0279 as SUPERSEDED
  **File**: `handovers/0279_context_priority_integration_fix.md`
  **Add at top**:
  ```markdown
  ---
  **STATUS: SUPERSEDED BY HANDOVER 0280**

  This handover fixed missing user_id in fetch_* tool templates.

  **As of v3.2+**: The 9 fetch_* tools have been DELETED. User control is now implemented directly in `get_orchestrator_instructions()`.

  See: [Handover 0280](./0280_monolithic_context_architecture_roadmap.md)

  **THIS HANDOVER IS OBSOLETE.**
  ---
  ```

---

### Phase 4: Code Comments Cleanup (Day 4, 2 hours)

**Target**: 5 files with outdated comments

#### File 8: `src/giljo_mcp/tools/orchestration.py`

- [ ] **Task 9.1**: Update function docstrings
  **Function**: `get_orchestrator_instructions()`
  **Update docstring**: Add v3.2+ architecture description, priority framing, depth config

- [ ] **Task 9.2**: Remove TODO comments referencing fetch_* tools
  **Search**: `# TODO.*fetch_`
  **Action**: Delete (tasks completed in Handover 0281)

#### File 9: `src/giljo_mcp/thin_prompt_generator.py`

- [ ] **Task 9.3**: Update class docstring
  **Class**: `ThinClientPromptGenerator`
  **Update**: Remove references to tool template generation

- [ ] **Task 9.4**: Remove fetch_* tool template generation comments
  **Search**: `# Generate fetch_.*tool template`
  **Action**: Delete (code deleted in Handover 0281)

#### File 10: `frontend/src/components/settings/ContextPriorityConfig.vue`

- [ ] **Task 9.5**: Update component docstring
  **Add comment**:
  ```javascript
  /**
   * Context Priority Configuration Component (v3.2+)
   *
   * Allows users to configure context priorities and depth for orchestrator.
   * Settings control SINGLE get_orchestrator_instructions() MCP tool.
   *
   * Architecture: Monolithic context (not 9 separate fetch_* tools).
   * See: Handover 0280 for architecture details.
   */
  ```

#### File 11: `tests/integration/test_orchestrator_priority_filtering.py`

- [ ] **Task 9.6**: Update file docstring
  **Update**: Clarify that tests verify monolithic tool, not individual fetch_* tools

#### File 12: `src/giljo_mcp/__init__.py`

- [ ] **Task 9.7**: Remove fetch_* tool imports (if any remain)
  **Search**: `from.*fetch_`
  **Action**: Delete (tools deleted in Handover 0281)

---

## 📊 Verification Checklist

### Post-Update Verification

- [ ] **Verify 1**: No references to "fetch_product_context" (except in deprecation notices)
  ```bash
  grep -r "fetch_product_context" --include="*.md" --exclude-dir=handovers/scripts
  # Should only return files with deprecation notices
  ```

- [ ] **Verify 2**: No references to "fetch_vision_document" (except in deprecation notices)
  ```bash
  grep -r "fetch_vision_document" --include="*.md" --exclude-dir=handovers/scripts
  ```

- [ ] **Verify 3**: All 4 critical reference docs have architecture change notices
  ```bash
  head -n 15 handovers/Reference_docs/Dynamic_context.md | grep "ARCHITECTURE CHANGE"
  head -n 15 handovers/Reference_docs/Mcp_tool_catalog.md | grep "ARCHITECTURE CHANGE"
  head -n 15 handovers/Reference_docs/start_to_finish_agent_FLOW.md | grep "ARCHITECTURE CHANGE"
  head -n 15 CLAUDE.md | grep "v2.0 - Monolithic"
  ```

- [ ] **Verify 4**: 32 completed handovers have deprecation notices
  ```bash
  grep -l "ARCHITECTURE CHANGE NOTICE" handovers/completed/*.md | wc -l
  # Should output: 32
  ```

- [ ] **Verify 5**: Handover 0279 marked as SUPERSEDED
  ```bash
  head -n 5 handovers/0279_context_priority_integration_fix.md | grep "SUPERSEDED"
  ```

- [ ] **Verify 6**: Code comments updated (no fetch_* references)
  ```bash
  grep -r "fetch_" --include="*.py" src/giljo_mcp/
  # Should return 0 results (all deleted/updated)
  ```

- [ ] **Verify 7**: Cross-references valid (all links work)
  ```bash
  # Manually check that [Handover 0280] links work in updated docs
  ```

---

## 📝 Documentation Quality Standards

### Consistency Checklist

- [ ] All architecture change notices use same format
- [ ] All dates use YYYY-MM-DD format
- [ ] All handover references use [Handover XXXX] format
- [ ] All v3.2+ references are consistent
- [ ] All priority framing terms consistent (CRITICAL/IMPORTANT/REFERENCE/EXCLUDED)
- [ ] All depth config options consistent (none/light/moderate/heavy, 1/3/5/10, etc.)

### Clarity Checklist

- [ ] No ambiguous references to "old" or "new" (use v3.1 vs v3.2+)
- [ ] No dangling references (all links valid)
- [ ] No contradictions between documents
- [ ] Clear distinction: Historical reference vs Current architecture

---

## 🚀 Deployment Plan

### Pre-Deployment

- [ ] All 12 files updated
- [ ] All 32 batch deprecation notices added
- [ ] All verification checks pass
- [ ] Git commit prepared with descriptive message

### Git Commit Strategy

**Single Commit** (recommended):
```bash
git add handovers/ docs/ src/ frontend/ CLAUDE.md
git commit -m "docs(handover-0283): Migrate documentation to monolithic context architecture (v3.2+)

**Architecture Change**: Replaced 9 fetch_* tools with single get_orchestrator_instructions()

**Changes**:
- Updated 4 critical reference docs with architecture change notices
- Updated core docs (ORCHESTRATOR.md, CLAUDE.md)
- Added deprecation notices to 32 completed handovers
- Marked Handover 0279 as SUPERSEDED
- Cleaned up code comments (5 files)

**Impact**:
- All documentation reflects v3.2+ monolithic architecture
- Historical references clearly marked
- No dangling references to deleted fetch_* tools

See: Handover 0280 (Master Roadmap), 0281 (Backend), 0282 (Testing), 0283 (Documentation)

🤖 Generated with Claude Code
```

### Post-Deployment

- [ ] Verify documentation accessible (no broken links)
- [ ] Team notification sent (architecture change communication)
- [ ] Update tracking in Handover 0280 (mark 0283 COMPLETE)

---

## 📚 Reference Documents

### Generated by Research Agents

**Agent 3 - Documentation Audit**:
- Location: Output embedded in Handover 0280 Section 6.3
- Contains: Complete file-by-file analysis, change instructions, deprecation template

**Master Roadmap**:
- File: `handovers/0280_monolithic_context_architecture_roadmap.md`
- Section: "User-Specified Files to Update" (4 critical files listed)

### Standard Templates

**Architecture Change Notice** (for active docs):
```markdown
---
**ARCHITECTURE CHANGE NOTICE** (Handover 0280 - December 2025)

This document describes OLD v3.1 modular architecture.

**CURRENT (v3.2+)**: Single `get_orchestrator_instructions()` returns complete context.

See: [Handover 0280](./0280_monolithic_context_architecture_roadmap.md)

**HISTORICAL REFERENCE ONLY.**
---
```

**Deprecation Notice** (for completed handovers):
```markdown
---
**ARCHITECTURE CHANGE NOTICE** (Handover 0280 - December 2025)

This handover references OLD v3.1 modular architecture (9 fetch_* tools).

**CURRENT (v3.2+)**: Single `get_orchestrator_instructions()` returns complete context.

See: [Handover 0280](./0280_monolithic_context_architecture_roadmap.md)

**HISTORICAL REFERENCE ONLY.**
---
```

**Superseded Notice** (for Handover 0279):
```markdown
---
**STATUS: SUPERSEDED BY HANDOVER 0280**

This handover fixed missing user_id in fetch_* tool templates.

**As of v3.2+**: The 9 fetch_* tools have been DELETED.

See: [Handover 0280](./0280_monolithic_context_architecture_roadmap.md)

**THIS HANDOVER IS OBSOLETE.**
---
```

---

## ✅ Definition of Done

**This handover is COMPLETE when**:
1. ✅ All 4 critical reference docs updated with architecture change notices
2. ✅ Core docs (ORCHESTRATOR.md, CLAUDE.md) reflect v3.2+ architecture
3. ✅ 32 completed handovers have deprecation notices
4. ✅ Handover 0279 marked as SUPERSEDED
5. ✅ Code comments cleaned up (5 files)
6. ✅ All verification checks pass (7 checks)
7. ✅ Git commit created with descriptive message
8. ✅ No dangling references to deleted fetch_* tools

**Deliverable**: Consistent documentation where ALL files reflect monolithic context architecture (v3.2+) or are clearly marked as historical reference.

---

**END OF HANDOVER 0283**

**Handover Series Complete**: 0280 (Roadmap) → 0281 (Backend) → 0282 (Testing) → 0283 (Documentation) ✅
