# 0875 — Project Detail Page Layout Redesign

**Edition Scope:** CE
**Branch:** feature/0873-style-centralization
**Priority:** High
**Estimated Sessions:** 1-2
**Reference Mockup:** `C:\Projects\GiljoAI_MCP\Untitled.png` (screenshot of desired layout)

---

## Goal

Restructure the project detail page (Staging + Implementation tabs) to follow the **Products page layout pattern** — same margins, card style, background treatment, and visual hierarchy. The project detail page is essentially the Products page skeleton with a tab layer on top.

## Reference Design: Products Page

The Products page (`/Products`) is the gold standard. Its structure:

```
┌──────────────────────────────────────────────────────────┐
│ Products                                     (title, h4) │
│ Manage your product configurations...     (subtitle, muted)│
│                                                          │
│ [Search...........] [Sort ▾] [+ New Product] [Deleted]   │
│                                                          │
│ ┌─ card ─┐  ┌─ card ─┐  ┌─ card ─┐  ┌─ card ─┐         │
│ │Product │  │Product │  │Product │  │Product │          │
│ │  A     │  │  B     │  │  C     │  │  D     │          │
│ └────────┘  └────────┘  └────────┘  └────────┘          │
└──────────────────────────────────────────────────────────┘
```

Key traits:
- `v-container` (standard Vuetify padding, not custom)
- Title + subtitle as plain elements (unnested, not in a card)
- Filter bar as a flex row directly below title
- Cards float on the page background (no wrapper card)
- Smooth-border on individual cards, `$elevation-raised` background

## Target Design: Project Detail Page

Apply the same pattern, adding a tab layer:

```
┌──────────────────────────────────────────────────────────────────────┐
│ Project: [0003] test                                    (title row) │
│ Project ID: 90bf70c1-...                              (subtitle ID) │
│                                                                      │
│ [🚀 Staging]  [{} Implementation]                     (tab pills)   │
│                                                                      │
│ Execution Mode: [Multi-Terminal] [Claude] [Codex] [Gemini] (?)       │
│                                                                      │
│ [Stage Project]  [Implement]                  [Git] [Serena] [Tool]  │
│                                                                      │
│ ┌─ Description ────────┐  ┌─ Mission ──────────────┐   Agents       │
│ │ PROJECT DESCRIPTION  │  │ MISSION           ↻    │                │
│ │ ✏ 💡                 │  │ ✨ Orchestrator Gen.   │   [ORC] Orch.  │
│ │                      │  │                        │   [ANA] Anal.  │
│ │ Refactor the settings│  │ Restructure into three │   [IMP] Impl.  │
│ │ integrations page... │  │ visual groups: a hero  │   [DOC] Docu.  │
│ │                      │  │ card for GiljoAI MCP,  │   [REV] Revi.  │
│ │                      │  │ a two-column grid...   │   [TST] Test.  │
│ │                      │  │                        │                │
│ └──────────────────────┘  └────────────────────────┘                │
└──────────────────────────────────────────────────────────────────────┘
```

## Files to Modify

### 1. ProjectTabs.vue (`frontend/src/components/projects/ProjectTabs.vue`)

**Current:** Custom `project-tabs-container` with `padding: 24px`, custom header classes, `bordered-tabs-content` wrapper (already removed smooth-border in prior commit).

**Change to:**
- Keep `project-tabs-container` but match `v-container` padding pattern
- Execution mode row: left-aligned, same margin as filter bars on other pages
- Action buttons row: same line as or just below execution mode, with integration icons right-aligned on same row
- Remove any remaining background/border from `bordered-tabs-content`
- The `bordered-tabs-content` becomes a bare flex container

**Layout for Staging tab:**
```
[Execution Mode: pills...]                    [Git] [Serena] [Tool]
[Stage Project] [Implement]

[Description card]  [Mission card]   [Agents bare list]
```

**Layout for Implementation tab:**
- Agent execution table as its own floating card
- Chat input bar as its own floating card below
- (Already done from prior work — verify it still looks correct)

### 2. LaunchTab.vue (`frontend/src/components/projects/LaunchTab.vue`)

**Current:** 3-column `content-grid` with Description card, Mission card, and Agents column. Already restructured — cards have smooth-border, agents are bare.

**Changes needed:**
- Description card: style like a Products page product card — same padding, border-radius, background, smooth-border pattern
- Mission card: same treatment, with "Orchestrator Generated" tinted tag inside
- Agents column: integration icons at top, then "Agents" label, then bare list — already done but verify spacing matches
- Move integration icons row to be RIGHT-ALIGNED on the same row as Stage/Implement buttons (currently below them, left-aligned in LaunchTab — should be in ProjectTabs at the button row level, right-aligned)

**Key structural change:** The integration icons currently live inside LaunchTab.vue. They should move up to ProjectTabs.vue so they sit on the same row as Stage Project / Implement, right-aligned. This means:
- LaunchTab emits integration status (gitEnabled, serenaEnabled, agenticTool) as props or the parent reads them
- ProjectTabs renders the icons on the action-buttons-row, right-aligned with `v-spacer` between buttons and icons
- LaunchTab's agents column no longer has the integrations-row

### 3. CSS Alignment

All margins, padding, and gaps should match the Products/Projects/Tasks pages:

| Element | Value | Token |
|---------|-------|-------|
| Container padding | 16px (Vuetify v-container default) | — |
| Title bottom margin | mb-4 (16px) | Vuetify class |
| Filter bar gap | 10px | scoped .filter-bar |
| Filter bar bottom margin | 20px | scoped .filter-bar |
| Card border-radius | 16px | $border-radius-rounded |
| Card background | #182739 | $elevation-raised |
| Card border | smooth-border (inset box-shadow) | .smooth-border class |
| Card padding | 20-24px | scoped |
| Grid gap | 20px | scoped .content-grid |

## Rules

- ZERO inline styles — all in scoped SCSS with design-tokens
- Use smooth-border class (never CSS border on rounded elements)
- Use $elevation-raised for card backgrounds
- Use design tokens for all spacing, colors, radii
- Keep all existing functionality: edit description, tips dialog, agent click handlers, modals, tooltips
- Run full Vitest suite — all tests must pass
- Commit when done

## Success Criteria

1. Project detail staging tab visually matches the Products page card layout
2. Description and Mission are product-card-style floating cards
3. Agents are a bare vertical list right-aligned (no card frame)
4. Integration icons sit right-aligned on the Stage/Implement button row
5. All margins/padding match Projects and Tasks pages
6. Implementation tab unaffected (already has floating cards)
7. Zero visual regressions on other pages
8. All 1916 Vitest tests pass
