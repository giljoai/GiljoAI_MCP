# Handovers

This folder contains **agent-to-agent task handovers** for the GiljoAI MCP project.

## Purpose

Handovers enable seamless task delegation between development agents/sessions by providing:
- Complete context and background
- Detailed implementation plans
- Testing requirements
- Success criteria
- Rollback strategies

## Active Handovers

**Not Started:**
- [`0001_HANDOVER_20251012_REMOVE_DYNAMIC_IP_DETECTION.md`](0001_HANDOVER_20251012_REMOVE_DYNAMIC_IP_DETECTION.md) - Priority: High
- [`0002_HANDOVER_20251012_REMOVE_LOCALHOST_BYPASS_COMPLETE_V3_UNIFICATION.md`](0002_HANDOVER_20251012_REMOVE_LOCALHOST_BYPASS_COMPLETE_V3_UNIFICATION.md) - Priority: CRITICAL

**In Progress:**
- None

**Blocked:**
- None

## Quick Start

### For Agents Receiving a Handover

1. Read [`HANDOVER_INSTRUCTIONS.md`](HANDOVER_INSTRUCTIONS.md) completely
2. Check git status: `git status && git log --oneline -5`
3. Read the assigned handover document thoroughly
4. Review referenced documentation in `/docs/`
5. Use Serena MCP tools to explore codebase
6. Update handover with progress
7. When complete, archive to `/handovers/completed/` with `-C` suffix

### For Agents Creating a Handover

1. Follow the template in [`HANDOVER_INSTRUCTIONS.md`](HANDOVER_INSTRUCTIONS.md)
2. Determine next sequence number: `ls handovers/ | grep "^[0-9]" | sort -n | tail -1`
3. Use naming convention: `[SEQUENCE]_HANDOVER_YYYYMMDD_[TASK_NAME].md`
4. Include all 10 required sections (see instructions)
5. Commit handover: `git add handovers/ && git commit -m "docs: Create handover [SEQUENCE]"`

## Execution Order

Some handovers have dependencies. Check each handover's "Dependencies and Blockers" section.

**Current Recommendation:**
1. Execute **0002** (Localhost Bypass Removal) first
2. Then execute **0001** (Dynamic IP Detection)

**Reason:** 0002 establishes unified authentication as foundation, 0001 builds on that by auto-configuring CORS.

## Folder Structure

```
handovers/
├── README.md                          ← This file
├── HANDOVER_INSTRUCTIONS.md           ← Detailed protocol for agents
├── [SEQUENCE]_HANDOVER_YYYYMMDD_*.md  ← Active handover tasks
└── completed/
    ├── README.md                      ← Archive documentation
    └── [SEQUENCE]_*-C.md              ← Completed handovers
```

## Documentation

- **[HANDOVER_INSTRUCTIONS.md](HANDOVER_INSTRUCTIONS.md)** - Complete handover protocol
- **[completed/README.md](completed/README.md)** - Archive documentation
- **[/docs/README_FIRST.md](/docs/README_FIRST.md)** - Project navigation
- **[/CLAUDE.md](/CLAUDE.md)** - Development environment guidance

## Handover Lifecycle

```
Create → Not Started → In Progress → Completed → Archive with -C suffix
```

**Example Workflow:**
1. Agent creates: `0003_HANDOVER_20251013_NEW_FEATURE.md`
2. Status: "Not Started"
3. Implementation agent picks up, status: "In Progress"
4. All phases complete, tests pass, status: "Completed"
5. Archive: `mv handovers/0003_*.md handovers/completed/0003_*-C.md`
6. Commit: `git commit -m "docs: Archive completed handover 0003"`

## Support

Questions? Check:
- `/docs/README_FIRST.md` - Project overview
- `/CLAUDE.md` - Development environment
- Previous completed handovers in `/handovers/completed/` for examples

---

**Remember:** A good handover enables the next agent to succeed. Take the time to be thorough.
