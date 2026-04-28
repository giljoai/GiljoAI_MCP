/**
 * Pre-filled project templates surfaced on the Welcome screen step-4
 * branch (active product, zero projects). Clicking a template card calls
 * `projectStore.createProject({ name, description })` with the payload
 * defined here — there is no new entity type, no DB schema change, and
 * no backend coupling. This file is the single source of truth for the
 * starter-template payloads.
 */

export const PROJECT_TEMPLATES = Object.freeze([
  Object.freeze({
    id: 'new_product_bootstrap',
    cardTitle: 'Bootstrap a new product',
    cardSubtitle:
      'Scaffold folders, requirements.txt, README, and propose your first 4 dev projects.',
    icon: 'mdi-rocket-launch-outline',
    projectName: 'Initiate new product (GiljoAI proposed starter)',
    projectDescription: [
      'Scaffold the project skeleton for a brand-new product: backend folder, frontend folder, shared requirements.txt (or package.json depending on stack), and a starter README.md. Use sensible defaults for the stack the user has indicated, or ask if unclear.',
      '',
      'When the scaffold is in place, propose four follow-up projects via /gil_add (Claude Code, Gemini CLI) or $gil-add (Codex CLI) covering:',
      '1. Backend bootstrap — framework choice, app entry, health endpoint, env handling',
      '2. Frontend bootstrap — framework choice, root layout, theme, basic routing',
      '3. Auth + data layer — chosen auth strategy, ORM/DB connection, first migration',
      '4. Deployment + CI — build script, container or platform target, CI workflow',
      '',
      'Keep each proposal small enough to ship in one focused session. Do NOT begin coding the four follow-ups in this project — just stage them via the gil_add skill and let the user activate them in order from the dashboard.',
    ].join('\n'),
  }),
  Object.freeze({
    id: 'existing_product_bootstrap',
    cardTitle: 'Import an existing product',
    cardSubtitle:
      'Analyze code, docs, and git history to seed 360-memory before new work.',
    icon: 'mdi-database-import-outline',
    projectName: 'Import existing product (GiljoAI 360-memory bootstrap)',
    projectDescription: [
      'Bootstrap the 360-memory for an existing codebase. Propose four read-only audit projects via /gil_add (Claude Code, Gemini CLI) or $gil-add (Codex CLI):',
      '1. Frontend audit — components, routes, state management, design system, build setup',
      '2. Backend audit — services, endpoints, data model, auth flow, integration points',
      '3. Documentation audit — README, handovers, ADRs, inline docstrings, gaps',
      '4. Git history audit — last 90 days of commits, contributors, hotspots, recent churn',
      '',
      'Each follow-up project, once activated, writes its findings to 360-memory so the orchestrator has a complete picture before any feature work begins.',
      '',
      'Hard rule: do NOT modify source code during the audits. Read-only inspection plus 360-memory writes only. The user will request feature work in separate projects after the bootstrap is complete.',
    ].join('\n'),
  }),
])
