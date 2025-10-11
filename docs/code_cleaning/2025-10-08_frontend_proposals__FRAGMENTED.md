# Frontend Code Cleanliness Audit – 2025-10-08

## Scope & Method
- Reviewed `frontend/src` (Vue 3 + Vite) for files outside the main bundle path that look like backups, alternates, or unused utilities.
- Used `find`/`rg` to trace component and composable imports; flagged artifacts with zero references in the live app.
- Cross-checked wizard flow (`SetupWizard.vue`) and services to confirm which assets actually drive production UI.

## High-Risk Zombies & Dead Ends
- `frontend/src/services/setupService.js.bak:1` – Full duplicate of the wizard service left as a `.bak`. No imports reference it (`rg "setupService.js.bak"` returns nothing). Risk: future edits may diverge from the canonical service or confuse contributors.
  - **Next checks**: Delete or archive outside src; rerun wizard smoke tests (`npm run test:run -- SetupWizard`) to ensure the live service still covers needed endpoints.
- `frontend/src/components/setup/DatabaseStep_NEW.vue:1` & `frontend/src/components/setup/DatabaseStep.vue.old:1` – Legacy and alternate database-step components stranded alongside the real flow (`SetupWizard` now mounts `DatabaseCheckStep`). `rg "DatabaseStep_NEW"` returns no runtime references.
  - **Next checks**: Confirm wizard navigation works with only `DatabaseCheckStep`; remove stale files after validating `npm run test:run -- SetupWizard`. Update docs if screenshots mention the old step order.
- `frontend/src/composables/useFocusTrap.js:1` – Utility composable exported but never consumed (`rg --glob "*.vue" "useFocusTrap" frontend/src` yields nothing). Indicates abandoned accessibility work.
  - **Next checks**: Decide whether to implement focus trapping (e.g., for modals) or drop the composable; if kept, add unit coverage via Vitest + jsdom.

## Serena Feature Inconsistency
- Several views (`frontend/src/views/SettingsView.vue:307`, `frontend/src/components/setup/SerenaAttachStep.vue:3`) gate UI around Serena MCP enablement, yet backend hooks remain placeholders (see backend report on `SerenaHooks`). UX currently promises functionality that cannot execute.
  - **Next checks**: Align with backend decision—either hide Serena toggles until the service is real or add feature-flag plumbing guarded by actual availability checks.

## Recommended Follow-Up Tests
1. `npm run test:run -- SetupWizard` to ensure wizard still passes component tests after pruning backups.
2. `npm run build` to catch any missing imports if unused files are removed.
3. If focus-trap logic is reclaimed, add targeted Vitest suites (`npm run test -- useFocusTrap.spec.ts`) to validate keyboard trapping before shipping.
