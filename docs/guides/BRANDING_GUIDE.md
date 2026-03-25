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
| **Orchestrator** | `#D4A574` | rgb(212, 165, 116) | `#B8905E` | `#E5C9A3` | Tan/Beige - Project coordination |
| **Analyzer** | `#E74C3C` | rgb(231, 76, 60) | `#C0392B` | `#F1948A` | Red - Analysis & research |
| **Implementer** | `#3498DB` | rgb(52, 152, 219) | `#2980B9` | `#85C1E9` | Blue - Code implementation |
| **Tester** | `#FFC300` | rgb(255, 195, 0) | `#E6B000` | `#FFD633` | Yellow - Testing & QA |
| **Reviewer** | `#9B59B6` | rgb(155, 89, 182) | `#8E44AD` | `#C39BD3` | Purple - Code review |
| **Documenter** | `#27AE60` | rgb(39, 174, 96) | `#229954` | `#7DCEA0` | Green - Documentation |
| **Researcher** | `#27AE60` | rgb(39, 174, 96) | `#229954` | `#7DCEA0` | Green - Research (alias) |
| **Custom** | `#90A4AE` | rgb(144, 164, 174) | `#78909C` | `#B0BEC5` | Gray - Custom agents |

### Color Aliases

Some agent roles share colors:
- **Implementer** / **Implementor**: Both use `#3498DB` (Blue)
- **Documenter** / **Researcher**: Both use `#27AE60` (Green)

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
<v-chip
  size="small"
  :style="{
    backgroundColor: '#D4A574',  // Orchestrator tan
    color: 'white'
  }"
>
  Orchestrator
</v-chip>
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

### Chat Head Badges

```scss
.chat-head--orchestrator {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: #D4A574;  // Orchestrator tan
  color: white;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid white;
}
```

---

## Visual Consistency Rules

1. **Agent roles MUST use the defined hex colors** - no custom colors
2. **Status badges MUST use semi-transparent backgrounds** (20% opacity) with solid border
3. **Tool icons MUST use solid backgrounds** with white text
4. **Chat head badges MUST be circular** with 2px white border
5. **All color implementations MUST sync** across frontend/backend

---

## Color Accessibility

All color combinations meet **WCAG 2.1 AA standards** for contrast:

- **White text on agent colors**: ✅ 4.5:1 minimum contrast ratio
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
