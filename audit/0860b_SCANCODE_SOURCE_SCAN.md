# 0860b: ScanCode Source Scanning

**Series:** 0860 (Code Provenance & License Compliance Audit)
**Phase:** 2 of 4
**Branch:** `feature/0860-license-audit`
**Priority:** CRITICAL — license header and copyright detection
**Estimated Time:** 2-3 hours (CPU-intensive scans)

### Reference Documents (READ FIRST)
- **Audit spec:** `handovers/CODE_PROVENANCE_LICENSE_AUDIT.md` — read Layer 1 section completely
- **Project rules:** `CLAUDE.md`

### Tracking Files
- **Chain log:** `prompts/0860_chain/chain_log.json`

---

## Context

ScanCode Toolkit scans source files for embedded license text, copyright statements, license declarations in package manifests, and license conflicts. It catches licenses declared in file headers, NOTICE files, and package metadata. It does NOT catch code copied without license headers — that's Layer 2 (SCANOSS, phase 0860c).

This phase is CPU-intensive. Each scan may take 30-60 minutes depending on codebase size and machine speed.

---

## Pre-Work

1. Read `handovers/CODE_PROVENANCE_LICENSE_AUDIT.md` — especially the ScanCode section and the license policy table
2. Read 0860a's `notes_for_next` in the chain log for tool versions and any early warnings
3. Verify ScanCode is installed: `scancode --version`

---

## Scope

### Task 1: ScanCode Backend Scan

```bash
scancode --license --copyright --package --info --classify --json-pp audit/scancode_backend.json --processes 4 --timeout 120 src/giljo_mcp/ api/ migrations/ install.py setup_gui.py bootstrap.py
```

**Expected runtime:** 30-60 minutes. The `--processes 4` flag parallelizes.

If the scan takes too long or times out on specific files, note the files in deviations and continue with available results.

### Task 2: ScanCode Frontend Scan

```bash
scancode --license --copyright --package --info --classify --json-pp audit/scancode_frontend.json --processes 4 --timeout 120 frontend/src/ frontend/package.json frontend/package-lock.json
```

**Note:** Do NOT scan `frontend/node_modules/` — transitive dependency licenses were already captured by license-checker in 0860a.

### Task 3: Parse and Triage Results

For each scan result JSON, extract files where `license_detections` is non-empty. Triage each using the license policy table from the spec:

| License | CE Status | SaaS Status |
|---------|-----------|-------------|
| MIT, BSD, ISC, Apache-2.0, PSF-2.0 | SAFE | SAFE |
| MPL-2.0 | REVIEW | SAFE |
| LGPL-2.1, LGPL-3.0 | REVIEW | SAFE |
| GPL-2.0, GPL-3.0 | BLOCK | SAFE* (TRACK) |
| AGPL-3.0 | BLOCK | BLOCK |
| Unknown / No license | REVIEW | REVIEW |

### Task 4: Produce SCANCODE_FINDINGS.md

Create `audit/SCANCODE_FINDINGS.md` per the spec's Agent Output Requirements:

1. **Total files scanned** and scan duration
2. **BLOCK (both editions)** — AGPL findings
3. **BLOCK (CE only)** — GPL findings (note: SAFE for SaaS)
4. **REVIEW items** — MPL, LGPL, unknown
5. **GPL Dependency Register** — all GPL (non-AGPL) items for SaaS TRACK
6. **Dependency license summary** — table sorted by license
7. **Copyright anomalies** — any copyright NOT "GiljoAI LLC" or expected upstream (e.g., "Copyright (c) FastAPI", "Copyright (c) Vue.js")

**Expected findings to NOT flag:**
- Standard Python stdlib license headers
- Third-party package license files that got included in the scan path
- MIT/BSD headers in vendored utilities (SAFE, just note them)

---

## Agent Protocols (MANDATORY)

### Rejection Authority
ScanCode may detect "license clues" with low confidence scores. Only flag detections with `score >= 80`. Lower-confidence matches should be noted in a separate "low confidence" section for owner review, not in the main findings.

### Flow Investigation
For any BLOCK finding, verify the file is actually in the shipping codebase (not a test file, not a doc, not a generated artifact). Check if the license detection is on OUR code or on a third-party file that shouldn't be in the scan path. Context matters — a GPL header in a file we wrote is very different from a GPL header in a vendored dependency's LICENSE file.

If you discover a BLOCK finding that could be a false positive (e.g., ScanCode detecting GPL text in a comment that discusses GPL compatibility), note it as "REVIEW — possible false positive" rather than BLOCK.

---

## What NOT To Do

- Do NOT remove or modify any license headers
- Do NOT modify any source code
- Do NOT attempt to resolve findings
- Do NOT run SCANOSS — that's phase 0860c
- Do NOT scan node_modules, .venv, or test directories

---

## Acceptance Criteria

- [ ] `audit/scancode_backend.json` produced (backend scan complete)
- [ ] `audit/scancode_frontend.json` produced (frontend scan complete)
- [ ] `audit/SCANCODE_FINDINGS.md` produced with all 7 required sections
- [ ] All BLOCK findings clearly documented with file path, license, and edition impact
- [ ] Copyright anomalies documented
- [ ] Any AGPL findings noted in chain log as CRITICAL

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0860_chain/chain_log.json`
- Check `orchestrator_directives`
- Review 0860a's `notes_for_next` for tool versions and early warnings

### Step 2: Mark Session Started
Update your session: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Tasks 1-4

### Step 4: Update Chain Log
In `notes_for_next`, include:
- Total files scanned (backend + frontend)
- Count of BLOCK/REVIEW/SAFE findings
- Any AGPL findings (CRITICAL)
- Any false positive patterns to help 0860d consolidation
- Scan duration

### Step 5: STOP
Do NOT spawn the next terminal. Commit chain log update and exit.
