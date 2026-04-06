# GiljoAI MCP Branding Guide

**Version**: 4.0.0
**Last Updated**: 2026-03-24
**Purpose**: Naming conventions, terminology standards, and visual branding guidelines for GiljoAI MCP

---

## Product Naming

| Context | Use this | Example |
|---|---|---|
| Product name (all contexts) | **GiljoAI MCP** | "GiljoAI MCP gives your AI coding agents a shared memory." |
| Company/brand | **GiljoAI** | "© 2026 GiljoAI LLC" |
| Trademark | **GILJO™** | "GILJO™ is a trademark of GiljoAI LLC." |
| LICENSE file only | **GiljoAI MCP Coding Orchestrator** | Keep as-is — legal specificity required |
| Informal shorthand (after first mention) | **the MCP server** (lowercase) | "The MCP server runs on your machine." |

### Retired product name forms — do not use:

- ~~GiljoAI MCP Coding Orchestrator~~ (except LICENSE)
- ~~GiljoAI Orchestrator~~
- ~~Giljo MCP~~
- ~~MCP Orchestrator~~
- ~~GiljoAI MCP Server~~ (as a product name — "the MCP server" as shorthand is fine)

---

## Functional Descriptions

| Term | When to use |
|---|---|
| **context engineering platform** | Primary functional descriptor. Use in headlines, one-liners, README first paragraph, meta tags. |
| **passive orchestrator** | Technical clarification only. Use where the "no AI inference" distinction matters (architecture docs, BYOAI disclaimers). |

### Retired functional descriptions — do not use:

- ~~passive orchestration platform~~
- ~~persistent context layer~~

---

## Terminology Standards

When referring to Claude Code, Codex CLI, Gemini CLI, or similar tools, always use **"AI coding agents"** (plural) or **"AI coding agent"** (singular).

### Retired terminology — do not use:

- ~~CLI tool / CLI tools~~
- ~~coding tool / coding tools~~
- ~~AI tool / AI tools~~
- ~~CLI agent / CLI agents~~
- ~~agentic CLI tools~~
- ~~AI coding tool / AI coding tools~~

---

## Footer Standard

All pages must use this footer text:

> © 2026 GiljoAI LLC. GILJO™ is a trademark of GiljoAI LLC. Source-available under GiljoAI Community License.

---

## Agent Role Colors

All agent roles use **consistent color coding** across the application to ensure visual coherence and user recognition.

### Color Definitions

| Agent Role | Primary Color | RGB | Dark Variant | Light Variant | Usage |
|------------|---------------|-----|--------------|---------------|-------|
| **Orchestrator** | `#D4B08A` | rgb(212, 176, 138) | `#B8956E` | `#E5CDA7` | Tan/Beige - Project coordination |
| **Analyzer** | `#E07872` | rgb(224, 120, 114) | `#C45E58` | `#ECA09C` | Red - Analysis & research |
| **Implementer** | `#6DB3E4` | rgb(109, 179, 228) | `#5199CA` | `#93C9ED` | Blue - Code implementation |
| **Tester** | `#EDBA4A` | rgb(237, 186, 74) | `#D4A434` | `#F3CE78` | Yellow - Testing & QA |
| **Reviewer** | `#AC80CC` | rgb(172, 128, 204) | `#9366B2` | `#C4A0DD` | Purple - Code review |
| **Documenter** | `#5EC48E` | rgb(94, 196, 142) | `#48AC78` | `#80D4AA` | Green - Documentation |
| **Researcher** | `#5EC48E` | rgb(94, 196, 142) | `#48AC78` | `#80D4AA` | Green - Research (alias) |
| **Custom** | `#90A4AE` | rgb(144, 164, 174) | `#78909C` | `#B0BEC5` | Gray - Custom agents |

### Color Aliases

Some agent roles share colors:
- **Implementer** / **Implementor**: Both use `#6DB3E4` (Blue)
- **Documenter** / **Researcher**: Both use `#5EC48E` (Green)

---

## Status Badge Colors

Agent job status indicators use the following color scheme:

| Status | Color | RGB | Usage |
|--------|-------|-----|-------|
| **Waiting** | `#90A4AE` | rgb(144, 164, 174) | Gray - Job queued |
| **Working** | `#3498DB` | rgb(52, 152, 219) | Blue - Job in progress |
| **Complete** | `#FFC300` | rgb(255, 195, 0) | Yellow - Job finished successfully |
| **Failure** | `#C6298C` | rgb(198, 41, 140) | Pink/Magenta - Job failed |
| **Blocked** | `#E67E22` | rgb(230, 126, 34) | Orange - Job blocked/waiting |

---

## AI Coding Agent Colors

Colors for AI coding agent integrations:

| Tool | Color | RGB | Usage |
|------|-------|-----|-------|
| **Claude Code** | `#E67E22` | rgb(230, 126, 34) | Orange - Anthropic's Claude |
| **Codex CLI** | `#9B59B6` | rgb(155, 89, 182) | Purple - OpenAI Codex |
| **Gemini** | `#3498DB` | rgb(52, 152, 219) | Blue - Google Gemini |

---

## Base Theme Colors

### Dark Theme (Default)

```scss
--color-bg-primary: #0e1c2d;      // Primary background
--color-bg-secondary: #182739;    // Secondary background
--color-bg-elevated: #1e3147;     // Elevated surfaces
--color-border: #315074;          // Border color
--color-text-primary: #e1e1e1;    // Primary text
--color-text-secondary: #8f97b7;  // Secondary text
```

### Light Theme

```scss
--color-bg-primary: #ffffff;      // Primary background
--color-bg-secondary: #f5f5f5;    // Secondary background
--color-bg-elevated: #ffffff;     // Elevated surfaces
--color-border: #e0e0e0;          // Border color
--color-text-primary: #363636;    // Primary text
--color-text-secondary: #606060;  // Secondary text
```

### Accent Colors

```scss
--color-accent-primary: #ffc300;   // Yellow (brand primary)
--color-accent-success: #67bd6d;   // Green (success)
--color-accent-danger: #c6298c;    // Pink (danger/error)
--color-accent-special: #8b5cf6;   // Purple (special)
```

---

## Implementation Files

### Frontend

**Color Definitions**:
- `frontend/src/styles/agent-colors.scss` - SCSS variables and mixins
- `frontend/src/config/agentColors.js` - JavaScript color configuration

**Component Usage**:
- `frontend/src/components/TemplateManager.vue` - Template role chips
- `frontend/src/components/projects/AgentCardEnhanced.vue` - Agent job cards
- `frontend/src/components/projects/ChatHeadBadge.vue` - Agent chat badges
- `frontend/src/components/projects/LaunchPromptIcons.vue` - Tool icons

### Backend

**Template Seeding**:
- `src/giljo_mcp/template_seeder.py` - Seeds 6 default agent templates
- All templates seeded with `is_active=True` by default

---

## Usage Guidelines

### Agent Cards

```vue
<span
  :style="{
    backgroundColor: 'rgba(212, 176, 138, 0.15)',  // Orchestrator tinted
    color: '#D4B08A',
    borderRadius: '8px',
    padding: '2px 10px',
    fontSize: '0.8125rem',
    fontWeight: 500
  }"
>
  Orchestrator
</span>
```

### Status Badges

```vue
<v-chip
  size="small"
  :style="{
    backgroundColor: 'rgba(255, 195, 0, 0.2)',  // Yellow with opacity
    color: '#FFC300',
    border: '1px solid #FFC300'
  }"
>
  Complete
</v-chip>
```

### Agent Badges (Tinted Style)

```scss
.agent-badge--orchestrator {
  width: 32px;
  height: 32px;
  border-radius: 8px;  // Square, not round
  background-color: rgba(212, 176, 138, 0.15);  // Tinted at 15% opacity
  color: #D4B08A;  // Full brightness agent color
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  // No border — tinted background provides contrast
}
```

---

## Visual Consistency Rules

1. **Agent roles MUST use the Luminous Pastels hex colors** — no custom colors, no hardcoded values; use `getAgentColor()` or CSS `var(--agent-*-primary)`
2. **Agent badges MUST use tinted style** — `rgba(agent_color, 0.15)` background + full-brightness agent color text, `border-radius: 8px` (square geometry)
3. **Status badges MUST use semi-transparent backgrounds** (20% opacity) with solid border
4. **Tool icons MUST use solid backgrounds** with white text
5. **All color implementations MUST sync** across frontend/backend
6. **Never use Vuetify `text-medium-emphasis`** — use scoped CSS class with `color: #8895a8` for muted text

---

## Color Accessibility

All color combinations meet **WCAG 2.1 AA standards** for contrast:

- **Agent colors on `#182739` background**: ✅ All pass 4.5:1 minimum (Luminous Pastels palette)
- **`--text-muted` (`#8895a8`)**: ✅ 4.98:1 on `#182739` (was `#5a6a80` at 2.74:1 — critical fix)
- **`--text-secondary` (`#a3aac4`)**: ✅ 6.56:1 on `#182739`
- **Status badge combinations**: ✅ 3:1 minimum contrast ratio (large text)
- **Dark theme text**: ✅ 7:1 contrast ratio

---

## References

- **Handover 0077**: Launch/Jobs Dual‑Tab Interface (retired; colors referenced historically; superseded by 0073 grid)
- **Handover 0041**: Agent Template Management System
- **Frontend Styles**: `frontend/src/styles/agent-colors.scss`
- **Color Config**: `frontend/src/config/agentColors.js`

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 4.0.0 | 2026-03-24 | Added product naming, terminology standards, footer standard, retired forms |
| 3.1.0 | 2025-01-02 | Initial branding guide with standardized agent colors |

---

**For questions or updates**: Consult `frontend/src/styles/agent-colors.scss` as the source of truth.
