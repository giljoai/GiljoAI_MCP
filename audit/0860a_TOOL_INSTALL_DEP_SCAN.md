# 0860a: Tool Installation + Dependency License Scan

**Series:** 0860 (Code Provenance & License Compliance Audit)
**Phase:** 1 of 4
**Branch:** `feature/0860-license-audit`
**Priority:** CRITICAL — first phase, unblocks everything
**Estimated Time:** 30 minutes

### Reference Documents (READ FIRST)
- **Audit spec:** `handovers/CODE_PROVENANCE_LICENSE_AUDIT.md` — read the ENTIRE document
- **Project rules:** `CLAUDE.md`

### Tracking Files
- **Chain log:** `prompts/0860_chain/chain_log.json`

---

## Context

This is the first phase of a two-layer license audit gating the CE public launch (April 5, 2026). This phase installs the scanning tools and runs fast dependency-only license scans. The goal is to get immediate visibility into the dependency license landscape — if there's an AGPL transitive dep hiding in the tree, we need to know now, not after hours of source scanning.

---

## Pre-Work

1. Read `handovers/CODE_PROVENANCE_LICENSE_AUDIT.md` completely — especially the license policy table and edition-aware triage rules
2. Verify `audit/` directory exists (should have been created by orchestrator)

---

## Scope

### Task 1: Verify/Create Output Directory

```bash
mkdir -p audit
```

Verify `audit/` is in `.gitignore`. If not, add it (the large JSON scan results should not be committed).

### Task 2: Install Scanning Tools

```bash
# ScanCode Toolkit (Layer 1 — license/copyright scanning)
pip install scancode-toolkit

# SCANOSS (Layer 2 — code snippet provenance)
pip install scanoss

# Dependency license reporters
pip install pip-licenses
```

Verify each installation:
```bash
scancode --version
scanoss-py --version
pip-licenses --version
```

Record versions in chain log.

### Task 3: Python Dependency License Scan

```bash
pip-licenses --format=json --output-file=audit/python_dep_licenses.json --with-urls --with-description
```

### Task 4: npm Dependency License Scan

```bash
cd frontend && npx license-checker --json --out ../audit/npm_dep_licenses.json
```

### Task 5: Produce Dependency License Report

Parse both JSON files and produce `audit/DEPENDENCY_LICENSES.md` containing:

1. **Python dependency table** — columns: Package, Version, License, URL. Sorted by license type.
2. **npm dependency table** — same format.
3. **Flagged dependencies** — any dep with GPL, AGPL, LGPL, MPL, SSPL, BSL, CPAL, or unknown/missing license. For each flagged dep:
   - Package name and version
   - Detected license
   - CE impact (BLOCK/REVIEW/SAFE)
   - SaaS impact (BLOCK/REVIEW/SAFE/TRACK)
   - Which package depends on it (if transitive)
4. **Summary counts** — total deps, permissive count, copyleft count, unknown count

### Task 6: Early Warning Check

**CRITICAL:** If ANY dependency has an AGPL-3.0 license:
- Note it immediately in chain log `blockers_encountered`
- This is a BLOCK for BOTH editions
- The orchestrator needs to know before launching source scans

---

## Agent Protocols (MANDATORY)

### Rejection Authority
If a tool fails to install, try alternative installation methods (conda, pipx, etc.) before reporting as blocked. If pip-licenses or license-checker report "unknown" for a well-known package, check the package's PyPI/npm page manually — the tool may have missed the license metadata.

### Flow Investigation
For any flagged dependency, check if it's a direct or transitive dependency. Run `pip show <package>` to see what requires it. For npm, check `npm ls <package>`. Understanding the dependency chain is essential for remediation planning.

If you find a GPL transitive dependency, trace it to the direct dependency that pulls it in — the remediation may be replacing the direct dep, not the transitive one.

---

## What NOT To Do

- Do NOT uninstall or replace any dependencies — document only
- Do NOT modify any source code
- Do NOT run the source-level scans (ScanCode/SCANOSS on source files) — that's phases 0860b and 0860c
- Do NOT attempt to resolve any findings

---

## Acceptance Criteria

- [ ] ScanCode, SCANOSS, pip-licenses all installed and version-verified
- [ ] `audit/python_dep_licenses.json` produced
- [ ] `audit/npm_dep_licenses.json` produced
- [ ] `audit/DEPENDENCY_LICENSES.md` produced with complete tables and flagged items
- [ ] Any AGPL findings noted in chain log as CRITICAL
- [ ] Tool versions recorded in chain log

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0860_chain/chain_log.json`
- Check `orchestrator_directives` — if STOP, halt immediately
- This is the first session — no previous session to review

### Step 2: Mark Session Started
Update your session: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Tasks 1-6

### Step 4: Update Chain Log
In `notes_for_next`, include:
- Tool versions installed
- Total Python deps and npm deps counted
- Any AGPL/GPL/LGPL findings (critical for 0860b/c triage)
- Any tool installation issues

### Step 5: STOP
Do NOT spawn the next terminal. Commit chain log update and exit.
