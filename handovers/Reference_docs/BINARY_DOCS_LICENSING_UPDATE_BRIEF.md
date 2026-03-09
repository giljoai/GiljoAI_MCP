# Binary Document Licensing Update Brief

**Date:** 2026-03-07
**Context:** GiljoAI MCP project adopted the GiljoAI Community License v1.0 (replacing MIT) on 2026-03-07. This brief provides instructions for an external agent to update binary files (PDFs/PowerPoints) that cannot be edited programmatically in the codebase.

---

## What Changed

The GiljoAI MCP project previously used the MIT License. As of 2026-03-07, it now uses the **GiljoAI Community License v1.0**:

- **Single-user use**: Free, no restrictions
- **Multi-user / commercial use**: Requires a separate commercial license from GiljoAI
- **This is NOT an open-source (OSI-approved) license** -- do not use terms like "MIT", "open source", or "open core"

The correct terminology is:
- **Product name**: GiljoAI MCP Coding Orchestrator
- **Edition**: Community Edition
- **License**: GiljoAI Community License v1.0
- **Strategy**: Community Edition (free, single-user) now. SaaS Edition (multi-user, subscription) later.

---

## Architectural North Star: Community vs SaaS Edition Split

The product is being developed in a single repository with two long-lived branches: `main` (Community Edition, public) and `saas` (SaaS Edition, private). Merge direction is one-way: `main → saas`. When CE goes public, `main` pushes to a public GitHub remote; `saas` pushes only to a private remote. SaaS-only code is physically isolated in `saas/` directories. See `docs/EDITION_ISOLATION_GUIDE.md` for the full specification.

**Any architecture diagrams in these files should reflect this two-edition model if they show system boundaries, deployment, or feature scope.**

### What stays in Community Edition (public repo)
| Component | Description |
|-----------|-------------|
| Core orchestration engine | Mission planning, agent coordination, context management |
| Agent management | Templates, spawning, communication, job lifecycle |
| Single-user auth | Login/password, JWT, single admin user |
| Tenant isolation | Infrastructure kept but hidden in single-user mode |
| WebSocket & MCP protocol | Real-time communication, MCP tool integration |
| Frontend dashboard | Full UI for projects, agents, messages, settings |
| CE branding + licensing check | Edition badge, 30-day licensing reminder |

### What goes to SaaS Edition (private repo)
| Component | Description |
|-----------|-------------|
| OAuth / MFA / SSO | Enterprise auth providers, multi-factor |
| Billing & subscription | Stripe integration, plan enforcement, usage tracking |
| Organization & team management | Multi-org, roles, team structure |
| Multi-user admin tools | User management, org-level settings |
| Usage analytics & metering | API call tracking, agent hours, storage |
| SaaS onboarding flows | Trial/freemium, org setup wizard |
| SaaS deployment configs | Docker/K8s, horizontal scaling, Redis state |

### What this means for the architecture diagrams
- If a diagram shows the full system, it should be labeled as "Community Edition" scope
- If a diagram shows features like billing, OAuth, or multi-org, add a note: "SaaS Edition only (not in Community)"
- If a diagram shows deployment, note: "Community Edition: single-user local install. SaaS Edition: Docker/K8s multi-tenant deployment."

---

## Files to Review and Update

### File 1: `handovers/Reference_docs/giljoai workflow.pptx`
- **Type**: PowerPoint presentation
- **Content**: Architecture and workflow diagrams for the GiljoAI MCP system
- **What to check**: Any slides referencing "MIT", "open source", "open core", or licensing. Also check footer/header text on slides.
- **What to change**: Replace any MIT/open-source references with "GiljoAI Community License v1.0" or "Community Edition". If there is a footer or title slide with license info, update it.
- **If no licensing references exist**: Add a small footer or note on the title slide: "GiljoAI MCP Community Edition -- GiljoAI Community License v1.0"

### File 2: `handovers/Reference_docs/giljoai workflow.pdf`
- **Type**: PDF (likely an export of the PowerPoint above)
- **What to do**: If File 1 (the .pptx) is updated, re-export this PDF from the updated PowerPoint. If this PDF is a standalone document (not an export of the .pptx), apply the same review and changes as File 1.

### File 3: `handovers/Reference_docs/Workflow architecture.pdf`
- **Type**: PDF -- architecture documentation
- **What to check**: Same as above -- any references to "MIT", "open source", "open core", or licensing terms.
- **What to change**: Same replacement rules as File 1.
- **If no licensing references exist**: Add a small footer or watermark: "GiljoAI MCP Community Edition"

---

## Do NOT Change

- **Diagrams, flowcharts, or technical content** -- only licensing/branding text
- **Color scheme or layout** -- keep existing design
- **Any file outside the 3 listed above** -- scope is limited to these files only

## Branding Reference

If you need the correct branding:
- **Product**: GiljoAI MCP Coding Orchestrator
- **Tagline**: "Break through AI context limits. Orchestrate teams of specialized AI agents."
- **Edition label**: "Community Edition"
- **License text** (short form): "GiljoAI Community License v1.0 -- Free for single-user use"
- **Website**: giljoai.com

---

## Delivery

After updating, provide:
1. Updated `.pptx` file (if PowerPoint was changed)
2. Updated `.pdf` exports of any changed files
3. A brief summary of what was changed in each file (or confirmation that no licensing references were found)
