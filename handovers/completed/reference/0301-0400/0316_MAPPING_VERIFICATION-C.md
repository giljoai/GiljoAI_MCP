# 🗺️ Complete Mapping: GET Commands → Fields → Badges (As Proposed in 0316)

**Date**: 2025-11-18
**Purpose**: Verify field mappings for Context Field Alignment Refactor
**Status**: Awaiting User Confirmation

---

## 📊 Proposed Mapping Table (After 0316 Implementation)

| # | GET Command | Database Fields Accessed | Product/Project UI Tab | Context Configurator Badge | Status in 0316 |
|---|-------------|-------------------------|------------------------|---------------------------|----------------|
| **1** | `get_product_context` | `Product.name`<br>`Product.description`<br>`config_data.features.core` | **Basic Info** tab | **"Product Core"** | ✅ NEW TOOL<br>⚠️ Move Features field |
| **2** | `get_vision_document` | `VisionDocument.content`<br>`MCPContextIndex.content` | **Vision Documents** tab | **"Vision Documents"** | ✅ Already working |
| **3** | `get_tech_stack` | `config_data.tech_stack.languages`<br>`config_data.tech_stack.frontend`<br>`config_data.tech_stack.backend`<br>`config_data.tech_stack.database`<br>`config_data.tech_stack.infrastructure` | **Tech Stack** tab | **"Tech Stack"**<br>⚠️ MISSING BADGE | ✅ BUG FIX<br>❌ Badge not mentioned |
| **4** | `get_architecture` | `config_data.architecture.pattern`<br>`config_data.architecture.layers`<br>`config_data.architecture.notes`<br>`config_data.architecture.api_style` | **Architecture** tab | **"Architecture"**<br>⚠️ MISSING BADGE | ✅ BUG FIX<br>❌ Badge not mentioned |
| **5** | `get_testing` | `Product.quality_standards` (NEW FIELD)<br>`config_data.testing.strategy`<br>`config_data.testing.coverage_target`<br>`config_data.testing.frameworks` | **Testing** tab<br>(rename from "Features & Testing") | **"Testing"**<br>⚠️ NEW BADGE | ✅ NEW TOOL<br>✅ New field<br>✅ Tab rename |
| **6** | `get_project` | `Project.name`<br>`Project.description`<br>`Project.mission`<br>~~`Project.context_budget`~~ (deprecate) | **Project** window | **"Project Context"** | ✅ NEW TOOL<br>✅ Deprecate context_budget |
| **7** | `get_360_memory` | `Product.product_memory.sequential_history[]`<br>(ONLY project closeouts) | Not in UI<br>(internal memory) | **"360 Memory"** | ❌ NOT mentioned in 0316<br>✅ Mentioned in 0318 |
| **8** | `get_git_history` | `Product.product_memory.sequential_history[].git_commits[]`<br>(aggregated commits) | Not in UI<br>(GitHub integration in settings) | **"Git History"** | ❌ NOT mentioned in 0316<br>✅ Mentioned in 0318 |
| **9** | `get_agent_templates` | `AgentTemplate.name`<br>`AgentTemplate.role`<br>`AgentTemplate.description`<br>`AgentTemplate.meta_data` | Not in Product UI<br>(separate section) | **"Agent Templates"** | ✅ Already working |

---

## 🎨 Visual Flow Diagram (Post-0316)

### Product UI Tabs → Database → MCP Tools → Context Badges

```
Product UI Tabs              Database Fields                    MCP Tool              Context Badge
═══════════════              ═══════════════                    ════════              ═════════════

┌─────────────┐
│ Basic Info  │ ──┬──→ Product.name                    ┌─────────────────────┐   ┌──────────────┐
└─────────────┘   ├──→ Product.description         ──→ │ get_product_context │──→│ Product Core │
                  └──→ config_data.features.core       └─────────────────────┘   └──────────────┘
                         (MOVED from Features tab)

┌─────────────┐
│Vision Docs  │ ────→ VisionDocument.content        ──→ │ get_vision_document │──→│Vision Documents│
└─────────────┘                                         └─────────────────────┘   └────────────────┘

┌─────────────┐
│ Tech Stack  │ ──┬──→ config_data.tech_stack.languages  ┌──────────────┐   ┌────────────┐
└─────────────┘   ├──→ .frontend                     ──→ │get_tech_stack│──→│ Tech Stack │❌ MISSING
                  ├──→ .backend                          └──────────────┘   └────────────┘
                  ├──→ .database
                  └──→ .infrastructure

┌─────────────┐
│Architecture │ ──┬──→ config_data.architecture.pattern   ┌─────────────────┐   ┌──────────────┐
└─────────────┘   ├──→ .layers                       ──→ │get_architecture │──→│ Architecture │❌ MISSING
                  ├──→ .notes                            └─────────────────┘   └──────────────┘
                  └──→ .api_style

┌─────────────┐
│  Testing    │ ──┬──→ Product.quality_standards (NEW) ┌─────────────┐   ┌─────────┐
└─────────────┘   ├──→ config_data.testing.strategy ──→│ get_testing │──→│ Testing │✅ NEW
(renamed from     ├──→ .coverage_target                └─────────────┘   └─────────┘
Features&Testing) └──→ .frameworks
```

### Project Window → Database → MCP Tools → Context Badges

```
Project Window       Project Database                   MCP Tool              Context Badge
══════════════       ═══════════════                    ════════              ═════════════

┌─────────────┐
│   Project   │ ──┬──→ Project.name                   ┌─────────────┐   ┌────────────────┐
└─────────────┘   ├──→ Project.description        ──→ │ get_project │──→│Project Context │✅ NEW
                  ├──→ Project.mission                 └─────────────┘   └────────────────┘
                  └──X Project.context_budget (DEPRECATE)
```

### Internal Memory → Database → MCP Tools → Context Badges

```
Internal Memory      Product Memory                     MCP Tool              Context Badge
═══════════════      ══════════════                     ════════              ═════════════

                  ┌──→ product_memory.sequential_history[]  ┌────────────────┐   ┌────────────┐
                  │    (project closeouts ONLY)         ──→ │get_360_memory  │──→│360 Memory  │✅ EXISTS
                  │                                         └────────────────┘   └────────────┘
                  │
                  └──→ .sequential_history[].git_commits[]  ┌────────────────┐   ┌────────────┐
                       (aggregated commits)             ──→ │get_git_history │──→│Git History │✅ EXISTS
                                                            └────────────────┘   └────────────┘
```

### Agent Templates → Database → MCP Tools → Context Badges

```
Agent Templates      AgentTemplate Table                MCP Tool              Context Badge
═══════════════      ═══════════════                    ════════              ═════════════

                  ┌──→ AgentTemplate.name              ┌───────────────────────┐   ┌────────────────┐
                  ├──→ .role                       ──→ │get_agent_templates    │──→│Agent Templates │✅ EXISTS
                  ├──→ .description                    └───────────────────────┘   └────────────────┘
                  └──→ .meta_data
```

---

## ❓ Questions for User Confirmation/Clarification

### **Question 1: Tech Stack & Architecture Badges**

In 0316, the tools `get_tech_stack` and `get_architecture` are **fixed**, but the **badges are NOT mentioned**.

**Should I update 0316 to explicitly add:**
- **a)** "Tech Stack" badge for `get_tech_stack`
- **b)** "Architecture" badge for `get_architecture`
- **c)** Leave it as-is (implementer will infer)

**Your Answer**: **a) and b) - YES, add both badges** ✅ (User said: "Yes add those badges (odd we used to have them)")

---

### **Question 2: Features Field Location**

You said move "Features" from "Features & Testing" tab → "Basic Info" tab.

**After the move:**
- **"Basic Info" tab** will have: Name, Description, **Features** ✅
- **"Testing" tab** (renamed) will have: Quality Standards, Testing Strategy, Coverage, Frameworks ✅

**Is this correct?**
- **a)** Yes, correct
- **b)** No, needs changes (explain):

**Your Answer**: **a) Yes, correct** ✅

---

### **Question 3: Quality Standards Field**

0316 proposes adding `Product.quality_standards` as a **new database column** (not JSONB).

**Should it be:**
- **a)** New column: `Product.quality_standards` (TEXT) ← 0316 proposes this
- **b)** JSONB path: `config_data.testing.quality_standards`
- **c)** Something else (explain):

**Your Answer**: **a) New column** ✅ (User said: "Quality standards is now a new field both in ui but also in database we add the model/field in DB AND merge eloquently into existing migration instructions")

---

### **Question 4: Architecture Fields**

In your original request, you listed architecture fields as:
- Primary architecture plan
- Design patterns and principles
- API style and communications
- Architecture notes

**Research found these JSONB fields exist:**
- `config_data.architecture.pattern`
- `config_data.architecture.layers`
- `config_data.architecture.notes`

**Should `get_architecture` return:**
- **a)** `pattern`, `layers`, `notes`, `api_style` (what 0316 proposes)
- **b)** Different fields to match your list exactly
- **c)** It's fine as proposed

**Your Answer**: **b) Different fields - Use `design_patterns` instead of `layers`** ✅
**Corrected fields**: `pattern`, `design_patterns`, `api_style`, `notes`
(User said: "I am confused to this answer because I literally have those fields in the vue during product setup" - Research found the 4 Vue fields map to design_patterns, NOT layers)

---

### **Question 5: 360 Memory & Git History in 0316**

These tools already exist and work correctly, but you wanted clarification:
- `get_360_memory` = ONLY project closeout summaries
- `get_git_history` = aggregated commits from all projects

**Should I:**
- **a)** Add these clarifications to 0316 (coding handover)
- **b)** Leave them in 0318 only (documentation handover)
- **c)** Add to both handovers

**Your Answer**: **a) Add to 0316** ✅ (User said: "question 5 yes you have it right" - referring to adding clarifications to 0316)

---

### **Question 6: Context Budget Deprecation**

0316 says deprecate `Project.context_budget` field.

**Should the implementer:**
- **a)** Remove it entirely from database (migration drops column)
- **b)** Keep column but hide from UI (soft deprecation)
- **c)** Add `deprecated=True` flag but keep data

**Your Answer**: **b) Soft deprecation** ✅ (Keep column in database, hide from UI, show deprecation warning)

---

## 🎯 Summary of Issues in Current 0316 Mapping

| Issue | Current State | Needs Clarification? |
|-------|---------------|---------------------|
| "Tech Stack" badge | ❌ Not mentioned in 0316 | ✅ YES (Q1) |
| "Architecture" badge | ❌ Not mentioned in 0316 | ✅ YES (Q1) |
| Features field move | ✅ Specified in 0316 | ❌ Clear (Q2 confirms) |
| Quality Standards location | ✅ New column (not JSONB) | ⚠️ Confirm (Q3) |
| Architecture field names | ⚠️ Slight mismatch | ⚠️ Confirm (Q4) |
| 360 Memory clarification | ❌ Not in 0316 | ✅ YES (Q5) |
| Git History clarification | ❌ Not in 0316 | ✅ YES (Q5) |
| Context Budget deprecation | ✅ Mentioned but method unclear | ⚠️ Confirm (Q6) |

---

## 📋 Research Findings Summary

### **Current Desynchronization Issues:**

**2 Critical Bugs** (Tools accessing non-existent fields):
1. `get_tech_stack` - Accesses `product.programming_languages` (doesn't exist) instead of `config_data.tech_stack.languages`
2. `get_architecture` - Accesses `product.architecture_notes` (doesn't exist) instead of `config_data.architecture.notes`

**3 Missing Tools** (Badges with no backing):
1. "Product Core" badge → No `get_product_context` tool
2. "Project Context" badge → No `get_project` tool
3. "Testing" badge → No `get_testing` tool

**2 Orphan Tools** (Tools with no badges):
1. `get_tech_stack` → No "Tech Stack" badge in UI
2. `get_architecture` → No "Architecture" badge in UI

---

## ✅ Updates Completed (2025-11-18)

All 6 questions have been answered and both handovers have been updated:

**Handover 0316 Updates**:
- ✅ Added "Tech Stack" and "Architecture" badge documentation
- ✅ Fixed architecture field mapping (replaced `layers` with `design_patterns`)
- ✅ Added depth configuration section (Product Core toggle, Testing dropdown)
- ✅ Added 360 Memory and Git History clarifications
- ✅ Updated migration strategy (merge quality_standards, no rogue migrations)
- ✅ Clarified context_budget soft deprecation

**Handover 0318 Updates**:
- ✅ Updated badge mapping to include all 9 tools
- ✅ Updated depth controls list (8 total depth controls)
- ✅ Added badge names for each MCP tool

**Additional Research Findings**:
- ✅ Depth controls for Tech Stack and Architecture ALREADY EXIST (no new controls needed)
- ✅ Only 2 new depth controls needed (Product Core, Testing)
- ✅ Architecture Vue UI has 4 fields that match `design_patterns`, not `layers`

**Next Steps**:
1. Commit updated handovers to git
2. Ready for fresh agent execution following TDD principles
3. Estimated completion: 3-5 days (0316), 1-2 days (0318)
