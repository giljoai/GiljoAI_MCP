# Handover 0321: Settings Componentization & Integration Registry

## Problem Statement

The `UserSettings.vue` and `SystemSettings.vue` views have grown to 1400+ lines each, making them difficult to maintain, test, and extend. Additionally, integrations are hardcoded in templates rather than driven by a centralized registry, which creates inconsistency as new integrations are added.

## Current State

- **UserSettings.vue**: 1405 lines (7 tabs, 2 sub-tabs for Context)
- **SystemSettings.vue**: 1421 lines (5 tabs, 3 configuration modals)
- **Integration registry**: Not implemented (each integration card is manually placed in templates)

### Existing Component Extractions

Some components have already been extracted:
- `TemplateManager.vue` (Agents tab)
- `ApiKeyManager.vue` (API Keys tab)
- `DepthConfiguration.vue` (Context → Depth sub-tab)
- `AiToolConfigWizard.vue` (Integrations)
- `ClaudeCodeExport.vue` (Integrations)
- `SlashCommandSetup.vue` (Integrations)
- `SerenaAdvancedSettingsDialog.vue` (Integrations)
- `DatabaseConnection.vue` (SystemSettings)

## Scope

### In Scope

1. Implement integration registry pattern as specified in handover 013A (Section 2.8)
2. Extract remaining UserSettings tab content into dedicated components
3. Extract remaining SystemSettings tab content into dedicated components
4. Reduce both view files to orchestration/routing code only (<800 lines each)
5. Ensure all extracted components maintain existing functionality and test coverage

### Out of Scope

- New integration features (just reorganizing existing code)
- Backend changes (frontend-only refactor)
- Redesigning the settings UI/UX
- Changes to existing component APIs (TemplateManager, ApiKeyManager, etc.)

## Success Criteria

1. **Integration registry** created at `frontend/src/integrations/registry.ts`
2. **UserSettings.vue** reduced to <800 lines
3. **SystemSettings.vue** reduced to <800 lines
4. All tabs render components via dynamic imports or the registry
5. Existing tests pass without modification
6. No visual or functional changes to the UI

## Technical Approach

### Phase 1: Integration Registry (Priority 1)

Create a centralized integration registry that both UserSettings and SystemSettings can consume:

```typescript
// frontend/src/integrations/registry.ts
export interface Integration {
  id: string
  name: string
  kind: 'tooling' | 'export' | 'ai_tool' | 'scm' | 'native'
  description: string
  icon?: string
  userConfigComponent?: string    // Component for UserSettings
  adminInfoComponent?: string     // Component for SystemSettings (read-only info)
}

export const INTEGRATIONS: Integration[] = [
  {
    id: 'mcp',
    name: 'GiljoAI MCP Integration',
    kind: 'tooling',
    description: 'Connect your AI coding tool to GiljoAI orchestration',
    userConfigComponent: 'McpIntegrationCard',
  },
  {
    id: 'slash_commands',
    name: 'Slash Commands',
    kind: 'tooling',
    description: 'Setup slash commands for AI coding tools',
    userConfigComponent: 'SlashCommandSetup',
  },
  {
    id: 'claude_code',
    name: 'Claude Code Export',
    kind: 'export',
    description: 'Export agent templates to Claude Code',
    userConfigComponent: 'ClaudeCodeExport',
  },
  {
    id: 'serena',
    name: 'Serena MCP',
    kind: 'ai_tool',
    description: 'Intelligent codebase understanding and navigation',
    userConfigComponent: 'SerenaIntegrationCard',
    adminInfoComponent: 'SerenaAdminInfo',
  },
  {
    id: 'github',
    name: 'Git + 360 Memory',
    kind: 'scm',
    description: 'Track git commits in 360 Memory for orchestrator context',
    userConfigComponent: 'GitIntegrationCard',
  },
]
```

### Phase 2: UserSettings Extraction (Priority 2)

Extract the following inline content into dedicated components:

| Tab | Current State | New Component | Est. Lines |
|-----|---------------|---------------|------------|
| Setup | Inline placeholder | `SetupTab.vue` | ~50 |
| Appearance | Inline (~100 lines) | `AppearanceTab.vue` | ~120 |
| Notifications | Inline (~100 lines) | `NotificationsTab.vue` | ~120 |
| Agents | Already extracted | `TemplateManager.vue` | - |
| Context → Priority | Inline (~200 lines) | `PriorityConfiguration.vue` | ~250 |
| Context → Depth | Already extracted | `DepthConfiguration.vue` | - |
| API Keys | Already extracted | `ApiKeyManager.vue` | - |
| Integrations → MCP | Inline (~50 lines) | `McpIntegrationCard.vue` | ~80 |
| Integrations → Serena | Inline (~100 lines) | `SerenaIntegrationCard.vue` | ~130 |
| Integrations → GitHub | Inline (~150 lines) | `GitIntegrationCard.vue` | ~180 |

**Result**: UserSettings.vue becomes a ~300-400 line shell that:
- Manages tab state
- Imports and registers components
- Renders components via `<component :is="...">` for integrations

### Phase 3: SystemSettings Extraction (Priority 3)

Extract the following inline content into dedicated components:

| Tab | Current State | New Component | Est. Lines |
|-----|---------------|---------------|------------|
| Network | Inline (~140 lines) | `NetworkSettingsTab.vue` | ~160 |
| Database | Already extracted | `DatabaseConnection.vue` | - |
| Integrations | Inline (~150 lines) | `AdminIntegrationsTab.vue` | ~180 |
| Security | Inline (~100 lines) | `SecuritySettingsTab.vue` | ~120 |
| System | Inline (~90 lines) | `SystemPromptTab.vue` | ~110 |

Additionally, extract the three configuration modals:
- `ClaudeConfigModal.vue` (~100 lines)
- `CodexConfigModal.vue` (~100 lines)
- `GeminiConfigModal.vue` (~90 lines)

**Result**: SystemSettings.vue becomes a ~400-500 line shell

### Component Location

New components will be placed in:
```
frontend/src/components/settings/
├── tabs/
│   ├── SetupTab.vue
│   ├── AppearanceTab.vue
│   ├── NotificationsTab.vue
│   ├── PriorityConfiguration.vue
│   ├── NetworkSettingsTab.vue
│   ├── SecuritySettingsTab.vue
│   ├── SystemPromptTab.vue
│   └── AdminIntegrationsTab.vue
├── integrations/
│   ├── McpIntegrationCard.vue
│   ├── SerenaIntegrationCard.vue
│   ├── GitIntegrationCard.vue
│   └── SerenaAdminInfo.vue
└── modals/
    ├── ClaudeConfigModal.vue
    ├── CodexConfigModal.vue
    └── GeminiConfigModal.vue
```

### State Management Strategy

Each extracted component will:
1. Receive required props from parent (settings object, loading states)
2. Emit events for mutations (save, reset, update)
3. Parent view coordinates state and API calls

Alternative: Components can use `useSettingsStore` directly for simpler prop drilling.

## File Changes Summary

### New Files (16 total)

- `frontend/src/integrations/registry.ts`
- 7 tab components in `frontend/src/components/settings/tabs/`
- 4 integration card components in `frontend/src/components/settings/integrations/`
- 3 modal components in `frontend/src/components/settings/modals/`
- 1 index file: `frontend/src/components/settings/index.ts`

### Modified Files (2)

- `frontend/src/views/UserSettings.vue` (major reduction)
- `frontend/src/views/SystemSettings.vue` (major reduction)

## Estimated Effort

| Phase | Task | Estimated Time |
|-------|------|----------------|
| 1 | Integration Registry | 2-3 hours |
| 2 | UserSettings Extraction | 4-6 hours |
| 3 | SystemSettings Extraction | 4-6 hours |
| - | Testing & Verification | 2-3 hours |
| **Total** | | **12-18 hours** |

This can be done incrementally over 2-3 sessions. Each phase is independently valuable.

## Testing Strategy

1. **No new tests required initially** - existing tests should continue to pass
2. **Component tests can be added later** for extracted components
3. **Manual verification checklist**:
   - [ ] All 7 UserSettings tabs render correctly
   - [ ] All 5 SystemSettings tabs render correctly
   - [ ] Serena toggle and advanced dialog work
   - [ ] Git integration toggle and save work
   - [ ] Priority drag-and-drop works
   - [ ] All modals open/close correctly
   - [ ] Theme switching works
   - [ ] Settings save/reset/reload work

## Dependencies

None - this is an internal frontend refactoring.

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing functionality | Medium | High | Extract exact code, test thoroughly |
| State management complexity | Low | Medium | Start with prop drilling, refactor to stores if needed |
| Inconsistent styling | Low | Low | Keep all styles with their components |

## Future Considerations

1. **Lazy loading**: Tab components could be lazy-loaded for performance
2. **Integration plugins**: Registry could support runtime registration for third-party integrations
3. **Component library**: Extracted components could be reused in other views
4. **Storybook**: Individual components are easier to document in a component library

## References

- `handovers/013A_code_review_architecture_status.md` (Section 2.8 - Integration Registry recommendation)
- `frontend/src/views/UserSettings.vue` (current implementation)
- `frontend/src/views/SystemSettings.vue` (current implementation)
- `frontend/src/components/settings/DepthConfiguration.vue` (example of existing extraction)
