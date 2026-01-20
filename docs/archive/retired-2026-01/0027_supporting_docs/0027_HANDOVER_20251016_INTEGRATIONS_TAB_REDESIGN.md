# 0027_HANDOVER_20251016_INTEGRATIONS_TAB_REDESIGN.md

## Project Overview
**Handover ID**: 0027  
**Date Created**: 2025-10-16  
**Status**: ACTIVE  
**Priority**: MEDIUM  
**Type**: UI/UX Redesign - Integrations  

## Objective
Redesign the Admin Settings Integrations tab to focus on system-wide agent coding tools and native integrations, removing individual API configurations (moved to user profiles).

## Background Context
The current "API and Integrations" tab contains user-specific API configurations that should be moved to individual user profiles. Instead, this admin-level tab should showcase system-wide integration capabilities, particularly our agent coding tool ecosystem and native integrations.

## Scope of Work

### 1. Tab Renaming
- [ ] Change tab name from "API and Integrations" to "Integrations"
- [ ] Update navigation and routing if needed

### 2. Remove API Integration Components
- [ ] Remove all user-specific API key configurations
- [ ] Remove MCP tool setup (moved to user settings)
- [ ] Clean up related code and components

### 3. Agent Coding Tools Section
Create a comprehensive section explaining our agent coding tool integration:

#### 3.1 Claude Code CLI
- [ ] Add Claude logo/branding
- [ ] Explain Claude Code integration with MCP configuration
- [ ] Describe marketplace tools and sub-agents
- [ ] **Yellow alert box**: "FINISH THESE INSTRUCTIONS AFTER ALPHA TESTING AND AGENT CREATION IS DONE"
- [ ] Configuration instructions:
  - API key generation under user profile
  - Marketplace configuration option
  - Manual configuration option
- [ ] "How to Configure Claude" button → Modal with:
  - Marketplace configuration steps
  - Manual copy/paste method with `{your-api-key-here}` placeholder
  - Optional download instructions

#### 3.2 Codex CLI
- [ ] Add Codex branding/logo
- [ ] Explain sub-agent integration and workflow
- [ ] Configuration instructions (no marketplace - copy/paste only):
  - API key generation under user profile
  - Manual configuration steps
  - Download instructions option
- [ ] "How to Configure Codex" button → Modal with instructions

#### 3.3 Gemini CLI
- [ ] Add Gemini branding/logo
- [ ] "[COMING SOON]" badge/indicator
- [ ] Placeholder description for future integration

### 4. Native Integrations Section
- [ ] Section heading: "Native Integrations"
- [ ] **Serena Integration**:
  - Serena logo/branding
  - Small paragraph explaining Serena's role in the application
  - GitHub link for credit to owner
  - Note: "Each user enables Serena under User Settings → Integrations"
- [ ] "[More Coming Soon]" indicator

## Technical Requirements

### Files to Modify
- `frontend/src/views/SystemSettings.vue` - Integrations tab content
- Create new modal components for configuration instructions
- Add logo/branding assets for tools
- Update navigation labels

### Modal Components to Create
1. **ClaudeConfigModal.vue**:
   - Marketplace configuration instructions
   - Manual configuration with copy/paste
   - Download instructions option

2. **CodexConfigModal.vue**:
   - Manual configuration instructions
   - Download instructions option

### Asset Requirements
- Claude Code logo/icon
- Codex logo/icon
- Gemini logo/icon
- Serena logo/icon

### Content Structure
```
Integrations Tab
├── Agent Coding Tools
│   ├── Claude Code CLI
│   │   ├── Description & MCP integration
│   │   ├── Sub-agent explanation
│   │   ├── Yellow alert (alpha testing note)
│   │   └── Configuration button → Modal
│   ├── Codex CLI
│   │   ├── Description & sub-agent workflow
│   │   └── Configuration button → Modal
│   └── Gemini CLI [COMING SOON]
└── Native Integrations
    ├── Serena
    │   ├── Description
    │   ├── GitHub link & credit
    │   └── User settings note
    └── [More Coming Soon]
```

## Content Requirements

### Claude Code Description
- Explain MCP configuration usage
- Describe marketplace tools integration
- Sub-agent creation and management
- Alpha testing disclaimer

### Codex Description
- Sub-agent workflow explanation
- Integration capabilities
- Configuration requirements

### Serena Description
- Role in GiljoAI MCP Server
- Capabilities and features
- User-level configuration note

### Configuration Instructions
- Clear step-by-step guides
- API key placeholder format: `{your-api-key-here}`
- Both GUI and manual configuration options
- Downloadable instruction formats

## Design Requirements
- Professional, organized layout
- Clear section separation
- Prominent logos/branding for each tool
- Consistent button styling
- Modal dialogs for detailed instructions
- Responsive design for all screen sizes

## Acceptance Criteria
- [ ] Tab renamed to "Integrations"
- [ ] All API components removed
- [ ] Agent Coding Tools section complete with three tools
- [ ] Native Integrations section with Serena
- [ ] Configuration modals functional
- [ ] Professional appearance with proper branding
- [ ] Clear instructions for each integration
- [ ] Alpha testing disclaimer prominently displayed

## Implementation Notes
- Follow Vuetify design patterns
- Maintain consistency with existing admin interface
- Ensure modals are accessible and mobile-friendly
- Use appropriate icons and branding
- Consider loading states for future dynamic content

## Dependencies
- Logo/branding assets for each tool
- Understanding of marketplace vs manual configuration flows
- User profile API key generation workflow
- Serena GitHub repository information

---

**Next Steps**: Begin implementation by analyzing current integrations tab structure and removing API components, then build the new agent coding tools section.