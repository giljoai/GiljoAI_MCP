# Code Provenance & License Compliance Audit

**Project type:** Standalone audit (not a numbered handover)
**Target:** GiljoAI MCP Community Edition codebase
**Timing:** Must complete before CE public launch (April 5, 2026)
**Owner review required:** Patrik must personally review all flagged items before clearing the audit

---

## Why This Audit Exists

GiljoAI MCP CE is built primarily through AI coding agents (Claude Code, Codex CLI, Gemini CLI). AI-generated code carries two specific risks that this audit addresses:

1. **License contamination.** A dependency or transitive dependency may carry a copyleft license (GPL, LGPL, AGPL) that is incompatible with the GiljoAI Community License v1.1. The GiljoAI license is source-available and proprietary -- it is NOT open source. Copyleft code in the dependency tree could create obligations to release GiljoAI source under the copyleft license.

2. **Code snippet provenance.** AI models trained on open source may generate code that is substantially similar to existing copyleft-licensed source code. Even without a direct dependency, embedded code fragments from GPL/AGPL projects would create the same license conflict. This is the harder problem and the one most solo founders skip.

---

## Edition Context: CE vs SaaS

GiljoAI MCP ships as two editions from one codebase. The license compliance implications differ significantly between them because copyright law treats distribution and server-side execution differently.

### Community Edition (CE)

- Licensed under GiljoAI Community License v1.1 (source-available, proprietary)
- Source code is distributed to end users
- Users download, install, and run the software on their own machines
- **Distribution triggers copyleft obligations.** If CE includes or links against GPL-licensed code, the GPL requires that the entire combined work be released under the GPL. This directly conflicts with the GiljoAI Community License.

### SaaS Edition

- Private repository, never distributed
- Only GiljoAI LLC (Patrik) runs the software
- Users interact exclusively through a browser -- they never receive source code or binaries
- **No distribution means most copyleft licenses do not trigger.** GPL and LGPL obligations arise only upon distribution of the software. Running GPL-licensed code on your own server and letting users access it over HTTP is generally permissible under GPL/LGPL terms.
- **AGPL is the exception.** The GNU Affero General Public License (AGPL-3.0) was written specifically to address this scenario. Its Section 13 requires that if users interact with the software over a network, the complete corresponding source must be made available. AGPL dependencies are therefore BLOCK for both editions.

### Practical Consequence for This Audit

A finding of GPL-2.0 or GPL-3.0 in a dependency has different severity depending on edition:

- **CE:** BLOCK. Must remove or replace before distribution.
- **SaaS:** SAFE (with caveat). The dependency can remain, but document it. If the SaaS edition ever gets distributed (open-sourced, sold as installable software, or white-labeled), the GPL obligation would activate retroactively.

AGPL-3.0 is BLOCK for both editions, no exception.

This audit runs against the shared codebase. Findings are tagged by edition impact so the project owner can make informed decisions about what to fix now (CE launch) versus what to track for later (SaaS launch).

**Important:** This is the standard industry interpretation of copyleft license mechanics, not legal advice. Consult an attorney before relying on the SaaS/no-distribution reasoning for any specific dependency.

---

## Scope

### In scope

- All Python source under `src/giljo_mcp/`
- All API endpoints under `api/`
- All frontend source under `frontend/src/`
- All dependencies declared in `pyproject.toml` (both `dependencies` and `dev` optional-dependencies)
- All npm dependencies in `frontend/package.json` and `frontend/package-lock.json`
- Installer scripts (`install.py`, `setup_gui.py`, `bootstrap.py`)
- Migration files under `migrations/`

### Out of scope

- `tests/` directory (test code is not distributed)
- `node_modules/` and `.venv/` (transitive dependencies are covered by dependency license scanning)
- `docs/`, `handovers/`, `.md` files (documentation, not executable code)
- Pre-built frontend assets in `frontend/dist/` (these are built from in-scope source)

---

## Two-Layer Audit Strategy

### Layer 1: License & Dependency Compliance (ScanCode Toolkit)

**What it catches:** License text in source files, copyright statements, license declarations in package manifests, dependency license conflicts.

**What it does NOT catch:** Code that was copied/generated without license headers.

### Layer 2: Code Snippet Provenance (SCANOSS)

**What it catches:** Source code fragments that match known open source files, including partial matches, copy-pasted functions, and vendored code without attribution.

**What it does NOT catch:** Novel code that happens to solve a problem the same way as existing code (algorithmic similarity without textual similarity).

Both layers are required. Neither alone is sufficient.

---

## Layer 1: ScanCode Toolkit

### Installation

```bash
pip install scancode-toolkit --break-system-packages
```

Verify installation:

```bash
scancode --version
```

Expected: v32.4.x or later.

### Execution -- Python Backend

```bash
scancode \
  --license \
  --copyright \
  --package \
  --info \
  --classify \
  --json-pp /home/user/audit/scancode_backend.json \
  --processes 4 \
  --timeout 120 \
  src/giljo_mcp/ api/ migrations/ install.py setup_gui.py bootstrap.py
```

### Execution -- Frontend

```bash
scancode \
  --license \
  --copyright \
  --package \
  --info \
  --classify \
  --json-pp /home/user/audit/scancode_frontend.json \
  --processes 4 \
  --timeout 120 \
  frontend/src/ frontend/package.json frontend/package-lock.json
```

### Execution -- Dependency Licenses Only

This scans the installed dependency tree for license declarations:

```bash
# Python dependencies
pip install pip-licenses --break-system-packages
pip-licenses --format=json --output-file=/home/user/audit/python_dep_licenses.json --with-urls --with-description

# npm dependencies
cd frontend && npx license-checker --json --out /home/user/audit/npm_dep_licenses.json
```

### Interpreting Results

**The license policy for GiljoAI MCP (edition-aware):**

| License Category | CE Status | SaaS Status | Action |
|---|---|---|---|
| MIT, BSD-2-Clause, BSD-3-Clause, ISC | SAFE | SAFE | No action needed |
| Apache-2.0 | SAFE | SAFE | No action needed (note the patent clause) |
| PSF-2.0, Python-2.0 | SAFE | SAFE | Standard Python ecosystem license |
| MPL-2.0 | REVIEW | SAFE | File-level copyleft -- safe in CE if MPL files are unmodified, flag if modified |
| LGPL-2.1, LGPL-3.0 | REVIEW | SAFE | CE: safe for dynamic linking only, flag any LGPL source copied into codebase. SaaS: no distribution, no obligation |
| GPL-2.0, GPL-3.0 | BLOCK | SAFE* | CE: incompatible, must remove or replace. SaaS: no distribution triggers obligation, but document for future tracking |
| AGPL-3.0 | BLOCK | BLOCK | Incompatible with BOTH editions. Network use clause triggers on SaaS. Must remove or replace |
| SSPL, BSL (non-GiljoAI), CPAL | REVIEW | REVIEW | Evaluate on a case-by-case basis for both editions |
| Unknown / No license detected | REVIEW | REVIEW | Investigate the source. Unlicensed code is not automatically safe |

*GPL SAFE for SaaS assumes SaaS is never distributed. If SaaS source is ever shared, sold as installable software, or white-labeled, GPL obligations activate. Document all GPL dependencies even if SaaS-only.

### Agent Output Requirements

Produce a summary file at `/home/user/audit/SCANCODE_FINDINGS.md` containing:

1. **Total files scanned** and scan duration
2. **BLOCK (both editions)** -- any AGPL-licensed files or dependencies. List file path, detected license, and the dependency that introduced it
3. **BLOCK (CE only)** -- any GPL-licensed files or dependencies. List file path, detected license, and the dependency that introduced it. Note: these are SAFE for SaaS under no-distribution assumption
4. **REVIEW items** -- any MPL/LGPL/unknown license detections. List file path, detected license, and which edition(s) are affected
5. **GPL Dependency Register** -- a dedicated list of all GPL (non-AGPL) dependencies for the SaaS TRACK register, even if they also appear in the BLOCK (CE only) section
6. **Dependency license summary** -- a table of all Python and npm dependencies with their licenses, sorted by license type
7. **Copyright anomalies** -- any files with copyright statements that are NOT "GiljoAI LLC" or expected upstream authors

Do NOT attempt to resolve BLOCK or REVIEW findings. Document them and stop. Resolution decisions belong to the project owner.

---

## Layer 2: SCANOSS Snippet Scanning

### Installation

```bash
pip install scanoss --break-system-packages
```

Verify installation:

```bash
scanoss-py --version
```

### Execution -- Python Backend

```bash
scanoss-py scan \
  --output /home/user/audit/scanoss_backend.json \
  src/giljo_mcp/ api/
```

### Execution -- Frontend

```bash
scanoss-py scan \
  --output /home/user/audit/scanoss_frontend.json \
  frontend/src/
```

Note: SCANOSS uses their free public API by default. This fingerprints source files locally and sends only the fingerprints (not your source code) to the OSSKB knowledge base for matching. For a codebase of this size (~200 endpoints, ~90 Vue components), the free tier should be sufficient for a one-time audit.

### Interpreting Results

SCANOSS returns match results per file. Each match includes:

- **id:** "file", "snippet", or "none"
- **matched:** percentage of the file that matches a known open source file
- **licenses:** license(s) associated with the matched source
- **component:** the open source project the match was found in

**Triage rules (edition-aware):**

| Match Type | Match % | License | CE Action | SaaS Action |
|---|---|---|---|---|
| snippet | < 30% | MIT/BSD/Apache | IGNORE | IGNORE |
| snippet | < 30% | GPL | REVIEW | TRACK* |
| snippet | < 30% | AGPL | REVIEW | REVIEW |
| snippet | >= 30% | Any permissive | REVIEW | REVIEW |
| snippet | >= 30% | GPL | BLOCK | TRACK* |
| snippet | >= 30% | AGPL | BLOCK | BLOCK |
| file | >= 70% | Any permissive | BLOCK | REVIEW |
| file | >= 70% | GPL | BLOCK | TRACK* |
| file | >= 70% | AGPL | BLOCK (critical) | BLOCK (critical) |
| none | n/a | n/a | SAFE | SAFE |

*TRACK means: not a blocker for SaaS launch, but document in a GPL dependency register. If the SaaS edition is ever distributed, these become BLOCK items. The agent should include TRACK items in the findings report as a separate category.

**Expected false positives (do not flag these):**

- FastAPI route handler boilerplate (decorators, request/response patterns)
- SQLAlchemy model definitions (standard ORM column declarations)
- Vue 3 component scaffolding (setup script, template/script/style structure)
- Pydantic model definitions
- Standard Python patterns (dataclasses, context managers, async patterns)
- Alembic migration boilerplate

### Agent Output Requirements

Produce a summary file at `/home/user/audit/SCANOSS_FINDINGS.md` containing:

1. **Total files scanned** and total files with matches
2. **BLOCK items** -- any file-level matches >= 70% against permissive/AGPL source, OR any snippet match >= 30% against AGPL source. Include: file path, matched component, match percentage, matched license, affected edition(s)
3. **TRACK items (SaaS GPL register)** -- any GPL (non-AGPL) matches that are BLOCK for CE but SAFE for SaaS. Include: file path, matched component, match percentage. These must be documented even though they do not block SaaS launch
4. **REVIEW items** -- any snippet matches >= 30% against permissive licenses. Include: file path, matched component, match percentage, matched license
5. **Statistics** -- count of files by match type (none, snippet, file) and breakdown by license category of matches

Do NOT attempt to resolve findings. Do NOT rewrite matched code. Document and stop.

---

## Execution Sequence

Run in this order:

1. Create audit output directory: `mkdir -p /home/user/audit`
2. Run ScanCode on backend sources
3. Run ScanCode on frontend sources
4. Run pip-licenses for Python dependency tree
5. Run license-checker for npm dependency tree
6. Produce `SCANCODE_FINDINGS.md`
7. Run SCANOSS on backend sources
8. Run SCANOSS on frontend sources
9. Produce `SCANOSS_FINDINGS.md`
10. Produce final `AUDIT_SUMMARY.md` (see below)

### Final Summary

Produce `/home/user/audit/AUDIT_SUMMARY.md` combining both layers:

```
# GiljoAI MCP -- Code Provenance & License Audit Summary
Date: [scan date]
ScanCode version: [version]
SCANOSS version: [version]

## Verdict

### CE Edition: [PASS / PASS WITH REVIEW ITEMS / FAIL]
### SaaS Edition: [PASS / PASS WITH REVIEW ITEMS / FAIL]

## Critical Findings -- BLOCK (both editions)
[AGPL findings or "None"]

## Critical Findings -- BLOCK (CE only)
[GPL findings that are safe for SaaS or "None"]

## GPL Dependency Register (SaaS TRACK items)
[GPL dependencies safe for SaaS under no-distribution assumption, or "None"]
Note: These become BLOCK if SaaS is ever distributed.

## Items Requiring Owner Review (REVIEW)
[list or "None"]

## Statistics
- Python files scanned: [n]
- Frontend files scanned: [n]
- Python dependencies: [n] (all permissive: yes/no)
- npm dependencies: [n] (all permissive: yes/no)
- SCANOSS snippet matches flagged: [n]
- SCANOSS file matches flagged: [n]
- GPL dependencies in SaaS TRACK register: [n]
```

Verdict logic (per edition):
- **PASS:** Zero BLOCK items AND zero REVIEW items for that edition
- **PASS WITH REVIEW ITEMS:** Zero BLOCK items, one or more REVIEW items for that edition
- **FAIL:** One or more BLOCK items for that edition

Note: A finding can be FAIL for CE and PASS for SaaS simultaneously (GPL without AGPL). The CE verdict gates the April 5 launch. The SaaS verdict is informational until SaaS launch.

---

## What This Audit Does NOT Cover

Be explicit about limitations. This audit is a good-faith compliance check, not a legal opinion.

- **Algorithmic similarity.** If an AI agent writes a sorting function that happens to match a GPL implementation structurally but not textually, SCANOSS will not catch it. No affordable tool catches this reliably.
- **Training data provenance.** We cannot verify what specific code the AI models were trained on. This audit catches the output, not the training input.
- **Transitive dependency depth.** pip-licenses and license-checker cover direct and resolved transitive dependencies. Dynamically loaded or optional sub-dependencies may not appear.
- **Binary artifacts.** This audit scans source code only. If any pre-compiled binaries ship with CE, they would need separate analysis.
- **Legal interpretation.** Whether a specific match constitutes infringement is a legal question. This audit identifies potential issues for legal review, it does not render legal conclusions.
- **SaaS distribution assumption.** The SaaS triage rules assume the SaaS edition is never distributed -- users only access it over a network. If the business model changes (white-labeling, on-premise enterprise installs, open-sourcing), the GPL TRACK register must be re-evaluated as potential BLOCK items. This assumption should be reviewed at each SaaS milestone.

---

## Re-running This Audit

This audit should be repeated:
- Before each major CE release
- After adding any new dependency
- After any large AI-agent-generated code sprint (500+ lines in a single session)
- Before SaaS launch (broader exposure increases risk)

Consider adding ScanCode and/or SCANOSS to the pre-commit hook chain or CI pipeline once a GitHub Actions workflow is established.
