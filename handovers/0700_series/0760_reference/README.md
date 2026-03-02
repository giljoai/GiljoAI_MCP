# 0760 Perfect Score Reference Files

**Purpose:** Reference collection for the 0760 research agent tasked with validating the 10/10 code quality proposal.

**Start here:** Read `../0760_PERFECT_SCORE_PROPOSAL.md` first — it defines the task, all 4 tiers, and research agent instructions.

---

## File Index

### Primary Documents
| File | Purpose |
|------|---------|
| `../0760_PERFECT_SCORE_PROPOSAL.md` | The proposal to validate — 4 tiers, 26 items, estimated 20-30 agent hours |
| `0750_FINAL_AUDIT_REPORT.md` | Complete findings from the 0750 sprint final audit (score: 7.8/10) |
| `0750_final_audit.json` | Machine-readable audit data — findings, test suite stats, resolved/remaining |

### Audit History
| File | Purpose |
|------|---------|
| `0750_midpoint_audit.json` | Midpoint audit (score: 7.1) — shows trajectory |
| `0750_chain_log.json` | Full 0750 sprint execution log — all 7 phases with commits |
| `CODE_QUALITY_AUDIT_REPORT_2026_02_28.md` | Pre-sprint baseline audit (score: 6.6) |

### Architecture Reference
| File | Purpose |
|------|---------|
| `dependency_graph.json` | Current dependency graph — 833 nodes, 1574 edges, 193 orphans. Use to validate zero-reference claims (items 1C-1E, 2D). Flag orphans that should be deleted. |
| `CLEANUP_STRATEGY.md` | Original cleanup strategy document |
| `CLEANUP_ROADMAP_2026_02_28.md` | Cleanup roadmap that preceded the 0750 sprint |

### Methodology
| File | Purpose |
|------|---------|
| `Code_quality_prompt.md` | The audit prompt template — use this methodology when validating findings |

---

## Key Facts for the Research Agent

- **Current score:** 7.8/10 (baseline was 6.6)
- **Branch:** Create `0760-perfect-score` from `0750-cleanup-sprint`
- **Test suite:** 1334 passed, 340 skipped, 10 failed, 68 errors (pytest-asyncio compat)
- **Dict returns:** Services layer clean (0), tools layer has 37 remaining
- **Dead code:** ~1,460 lines removed in 0750, more identified in proposal
- **Dependency graph:** 193 orphan nodes — some are cleanup candidates
- **Product decisions needed:** Default tenant key, CSRF enablement, unhandled emits (planned vs dead)

## What to Write

Write your research report to: `../0760_RESEARCH_REPORT.md`
