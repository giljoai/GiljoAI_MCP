# Handovers

Agent-to-agent task handovers for the GiljoAI MCP project.

## Quick Start

1. **Find a handover:** Check [HANDOVER_CATALOGUE.md](./HANDOVER_CATALOGUE.md)
2. **Read instructions:** See [HANDOVER_INSTRUCTIONS.md](./HANDOVER_INSTRUCTIONS.md)
3. **Check git status:** `git status && git log --oneline -5`
4. **Execute the handover**
5. **Update catalogue** when complete

## Current Priority Handovers

| ID | Title | Priority | Est. Effort |
|----|-------|----------|-------------|
| **0325** | Tenant Isolation Surgical Fix | HIGH | 8-10 hours |
| 0298 | Legacy Messaging Queue Cleanup | Medium | 4-6 hours |
| 0284 | Address get_available_agents | Medium | 2-3 hours |

> See [HANDOVER_CATALOGUE.md](./HANDOVER_CATALOGUE.md) for complete list.

## Folder Structure

```
handovers/
├── README.md                    # This file
├── HANDOVER_CATALOGUE.md        # Central registry (check here first!)
├── HANDOVER_INSTRUCTIONS.md     # How to write/execute handovers
├── HANDOVER_QUICK_REFERENCE.md  # Quick checklist
├── [NNNN]_*.md                  # Active handovers
└── completed/
    ├── [NNNN]_*-C.md            # Recently completed
    └── reference/               # Archived by range
        ├── 0001-0100/
        ├── 0101-0200/
        ├── 0201-0300/
        ├── 0301-0400/
        ├── 0501-0600/
        └── 0601-0700/
```

## Handover Lifecycle

```
Create → Active → In Progress → Complete → Archive (-C suffix) → Reference
```

## Key Documentation

| Document | Purpose |
|----------|---------|
| [HANDOVER_CATALOGUE.md](./HANDOVER_CATALOGUE.md) | Find handovers, check numbering |
| [HANDOVER_INSTRUCTIONS.md](./HANDOVER_INSTRUCTIONS.md) | Writing & execution protocol |
| [/docs/README_FIRST.md](/docs/README_FIRST.md) | Project navigation |
| [/CLAUDE.md](/CLAUDE.md) | Development guidance |

## Recent Completions

- **0299** - Unified UI Messaging Endpoint (Dec 2025)
- **0323** - Context Management Simplification (Nov 2025)
- **0243 Series** - GUI Redesign / Nicepage Conversion (Nov 2025)
- **0246 Series** - Orchestrator Workflow & Token Optimization (Nov 2025)

---

**Remember:** A good handover enables the next agent to succeed. Be thorough.
