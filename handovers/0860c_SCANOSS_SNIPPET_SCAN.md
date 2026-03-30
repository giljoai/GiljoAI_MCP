# 0860c: SCANOSS Snippet Scanning

**Series:** 0860 (Code Provenance & License Compliance Audit)
**Phase:** 3 of 4
**Branch:** `feature/0860-license-audit`
**Priority:** CRITICAL — code provenance detection
**Estimated Time:** 1-2 hours (network-dependent)

### Reference Documents (READ FIRST)
- **Audit spec:** `handovers/CODE_PROVENANCE_LICENSE_AUDIT.md` — read Layer 2 section completely
- **Project rules:** `CLAUDE.md`

### Tracking Files
- **Chain log:** `prompts/0860_chain/chain_log.json`

---

## Context

SCANOSS scans source files for code fragments that match known open source projects in the OSSKB knowledge base. Unlike ScanCode (which looks for license text), SCANOSS catches code that was copied or AI-generated without license headers. This is the harder problem — AI models trained on open source may generate code substantially similar to GPL/AGPL source.

SCANOSS fingerprints files locally and sends only fingerprints (not source code) to the OSSKB API. The free tier should be sufficient for this codebase size.

**This phase can run in parallel with 0860b** — SCANOSS is network-bound while ScanCode is CPU-bound.

---

## Pre-Work

1. Read `handovers/CODE_PROVENANCE_LICENSE_AUDIT.md` — especially the SCANOSS section, triage rules, and expected false positives
2. Read 0860a's `notes_for_next` for tool versions
3. Verify SCANOSS is installed: `scanoss-py --version`

---

## Scope

### Task 1: SCANOSS Backend Scan

```bash
scanoss-py scan --output audit/scanoss_backend.json src/giljo_mcp/ api/
```

**Note:** Do NOT scan `migrations/`, `install.py`, `setup_gui.py`, `bootstrap.py` — these are boilerplate-heavy and will generate noise. ScanCode (0860b) already covers their license headers.

### Task 2: SCANOSS Frontend Scan

```bash
scanoss-py scan --output audit/scanoss_frontend.json frontend/src/
```

**Note:** Do NOT scan `node_modules/` or `frontend/dist/`.

### Task 3: Parse and Triage Results

For each file in the scan results, check the match type and apply the edition-aware triage rules:

| Match Type | Match % | License | CE Action | SaaS Action |
|------------|---------|---------|-----------|-------------|
| snippet | < 30% | MIT/BSD/Apache | IGNORE | IGNORE |
| snippet | < 30% | GPL | REVIEW | TRACK |
| snippet | < 30% | AGPL | REVIEW | REVIEW |
| snippet | >= 30% | Permissive | REVIEW | REVIEW |
| snippet | >= 30% | GPL | BLOCK | TRACK |
| snippet | >= 30% | AGPL | BLOCK | BLOCK |
| file | >= 70% | Permissive | BLOCK | REVIEW |
| file | >= 70% | GPL | BLOCK | TRACK |
| file | >= 70% | AGPL | BLOCK (critical) | BLOCK (critical) |
| none | n/a | n/a | SAFE | SAFE |

### Task 4: Filter False Positives

The spec lists expected false positives that should NOT be flagged:
- FastAPI route handler boilerplate (decorators, request/response patterns)
- SQLAlchemy model definitions (standard ORM column declarations)
- Vue 3 component scaffolding (setup script, template/script/style structure)
- Pydantic model definitions
- Standard Python patterns (dataclasses, context managers, async patterns)
- Alembic migration boilerplate

For any match that looks like standard framework boilerplate, check the matched component in SCANOSS results. If the match is against the framework's own source (e.g., FastAPI matching FastAPI), it's a false positive — our code is using the framework as intended.

### Task 5: Produce SCANOSS_FINDINGS.md

Create `audit/SCANOSS_FINDINGS.md` per the spec's Agent Output Requirements:

1. **Total files scanned** and total files with matches
2. **BLOCK items** — file matches >= 70% against any license, OR snippet >= 30% against AGPL. Include: file path, matched component, match %, license, affected edition(s)
3. **TRACK items (SaaS GPL register)** — GPL matches that are BLOCK for CE but SAFE for SaaS. Include: file path, matched component, match %
4. **REVIEW items** — snippet matches >= 30% against permissive licenses. Include: file path, matched component, match %, license
5. **Statistics** — count by match type (none/snippet/file) and by license category

---

## Agent Protocols (MANDATORY)

### Rejection Authority
SCANOSS may return matches against extremely common patterns (e.g., a 3-line try/except block matching 50 different projects). Use judgment — if the same snippet matches 10+ unrelated projects, it's a common pattern, not a provenance concern. Document as "common pattern — no action" rather than flagging as REVIEW.

### Flow Investigation
For any BLOCK or high-percentage match, open the matched file in our codebase and compare it to the matched component listed in SCANOSS results. Is it genuinely similar code, or is SCANOSS matching on boilerplate? If you can't determine this from the match metadata alone, note it as "REVIEW — manual comparison needed" for the project owner.

If SCANOSS API rate-limits or fails, note it in `blockers_encountered`. The free tier has limits — if we hit them, we may need to split the scan into smaller batches or wait.

---

## What NOT To Do

- Do NOT rewrite any matched code — document only
- Do NOT modify any source files
- Do NOT attempt to resolve findings
- Do NOT scan node_modules, .venv, tests, or docs directories
- Do NOT send actual source code to any external service (SCANOSS only sends fingerprints by default — verify this)

---

## Acceptance Criteria

- [ ] `audit/scanoss_backend.json` produced
- [ ] `audit/scanoss_frontend.json` produced
- [ ] `audit/SCANOSS_FINDINGS.md` produced with all 5 required sections
- [ ] False positives filtered per expected patterns
- [ ] Any BLOCK findings clearly documented with file path, component, match %, license
- [ ] TRACK register for GPL (non-AGPL) items
- [ ] Any AGPL matches noted in chain log as CRITICAL

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0860_chain/chain_log.json`
- Check `orchestrator_directives`
- Review 0860a's `notes_for_next`
- If 0860b is complete, review its findings for context

### Step 2: Mark Session Started
Update your session: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Tasks 1-5

### Step 4: Update Chain Log
In `notes_for_next`, include:
- Total files scanned
- Count of matches by type (none/snippet/file)
- Count of BLOCK/TRACK/REVIEW findings
- Any AGPL findings (CRITICAL)
- API rate limit issues if any
- False positive patterns encountered

### Step 5: STOP
Do NOT spawn the next terminal. Commit chain log update and exit.
