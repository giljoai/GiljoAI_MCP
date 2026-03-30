# GiljoAI MCP — Code Provenance & License Audit Summary

**Date:** 2026-03-30
**ScanCode version:** 32.5.0 (SPDX License list v3.27)
**SCANOSS version:** 1.51.0 (OSSKB server 5.4.22, KB daily 26.03.21)
**Branch:** `feature/0860-license-audit`

---

## Verdict

### CE Edition: PASS WITH REVIEW ITEMS
### SaaS Edition: PASS

---

## Critical Findings — BLOCK (both editions)

**None.**

Zero AGPL-licensed dependencies, source files, or code snippet matches were found across all three scanning layers. Two SCANOSS matches referenced AGPL-licensed components (settings.py at 14%, DonutChart.vue at 4%) but both were assessed as false positives — standard SQLAlchemy and Vue boilerplate patterns, not actual AGPL code provenance.

## Critical Findings — BLOCK (CE only)

**None.**

No GPL-licensed code is embedded in project source files. All GPL-flagged Python packages (gemfileparser2, text-unidecode, docutils, typecode-libmagic) are dependencies of the audit tools (scancode-toolkit) and are NOT shipped with CE or SaaS.

## GPL Dependency Register (SaaS TRACK items)

**None.**

No GPL dependencies ship with either edition. No SCANOSS snippet or file matches against GPL-licensed source exceeded actionable thresholds. The register is empty.

> Note: This register must be re-evaluated if the SaaS edition is ever distributed (white-labeled, sold as installable software, or open-sourced).

## Items Requiring Owner Review (REVIEW)

### 1. `frontend/src/composables/useToast.js` — SCANOSS 79% snippet match

| Field | Value |
|---|---|
| Source | SCANOSS snippet scan (0860c) |
| Match % | 79% (8 of 48 lines matched, lines 8-43) |
| Matched component | FreshTab (vamosdalian/FreshTab v1.0.3) |
| Matched license | **None listed** (no license file in matched component) |
| Affected editions | CE: REVIEW, SaaS: REVIEW |

**Assessment:** Standard Vue 3 composable managing toast notifications via a reactive ref array. The pattern (push/splice/findIndex on notification objects) is documented in numerous Vue tutorials. The high match percentage is driven by the small file size (48 lines). The matched component has no license declared, so there is no license conflict — but the absence of a license also means no explicit permission grant from the matched project.

**Recommendation:** Owner should visually compare the two files. If confirmed as independently authored boilerplate, no action needed. If there is any concern, the composable is trivially rewritable (48 lines of simple state management).

### 2. `psycopg2-binary` (LGPL with exceptions) — Dependency scan

| Field | Value |
|---|---|
| Source | pip-licenses dependency scan (0860a) |
| Package | psycopg2-binary 2.9.10 |
| License | LGPL with exceptions |
| Affected editions | CE: REVIEW (assessed safe), SaaS: SAFE |

**Assessment:** The psycopg2 LGPL license includes an explicit exception clause permitting linking without copyleft obligations. The psycopg2 project documentation confirms this. Standard dynamic linking usage — no psycopg2 source is vendored into the codebase (confirmed by ScanCode: zero LGPL headers in project source).

**Recommendation:** No action required. The LGPL exception clause covers CE distribution.

### 3. `pycountry` (LGPL-2.1-only) — Dependency scan

| Field | Value |
|---|---|
| Source | pip-licenses dependency scan (0860a) |
| Package | pycountry 26.2.16 |
| License | LGPL-2.1-only |
| Required by | sumy (direct project dependency) |
| Affected editions | CE: REVIEW (assessed safe), SaaS: SAFE |

**Assessment:** Transitive dependency via sumy. Used as a standard dynamically linked Python package — no pycountry source is vendored into the codebase (confirmed by ScanCode: zero LGPL headers in project source). Under LGPL-2.1 terms, dynamic linking does not trigger copyleft obligations for the larger work.

**Recommendation:** No action required for standard usage. If pycountry source is ever vendored or modified, re-evaluate.

### 4. `PyGithub` (LGPL) — Dependency scan

| Field | Value |
|---|---|
| Source | pip-licenses dependency scan (0860a) |
| Package | PyGithub 2.8.1 |
| License | LGPL |
| Affected editions | CE: REVIEW, SaaS: SAFE |

**Assessment:** Not listed in pyproject.toml direct dependencies. Likely installed separately for GitHub integration scripting. If not included in CE distribution (not in pyproject.toml dependencies), this is a non-issue.

**Recommendation:** Verify PyGithub is not shipped with CE. If it is only a dev/integration tool, no action needed. If it is a runtime dependency, apply same LGPL dynamic-linking analysis as pycountry.

---

## Cross-Reference Analysis

All three scanning layers were compared for contradictions:

| Check | Result |
|---|---|
| Dependency flagged in 0860a also detected in 0860b source scan? | No. Zero copyleft license headers in source files. |
| SCANOSS match in 0860c corresponds to license detection in 0860b? | No. SCANOSS matches are snippet-level code similarity, not license headers. ScanCode found no license headers in any matched file. |
| pip-licenses says MIT but ScanCode detects GPL in same package? | No contradictions. All license detections are consistent across layers. |
| dompurify appears in both 0860a and 0860b | Consistent: both report MPL-2.0 OR Apache-2.0 dual license. Single finding — elect Apache-2.0, no action needed. |

**No contradictions found across any scanning layer.**

---

## Statistics

| Metric | Count |
|---|---|
| Python files scanned (ScanCode) | 331 |
| Frontend files scanned (ScanCode) | 163 (2 manifests + 161 source) |
| Total files scanned (ScanCode) | 494 |
| Total files scanned (SCANOSS) | 384 |
| Python dependencies | 268 (all permissive in shipped deps: yes) |
| npm dependencies | 383 (all permissive: yes) |
| SCANOSS snippet matches flagged | 12 (1 REVIEW, 7 false positive, 4 below threshold) |
| SCANOSS file matches flagged | 0 |
| GPL dependencies in SaaS TRACK register | 0 |
| AGPL findings (all layers combined) | 0 |
| Contradictions across layers | 0 |

---

## What This Audit Does NOT Cover

- **Algorithmic similarity:** Code that solves problems the same way as GPL code structurally but not textually will not be caught by SCANOSS.
- **Training data provenance:** We cannot verify what code the AI models were trained on. This audit catches output similarity, not training input.
- **Transitive dependency depth:** Dynamically loaded or optional sub-dependencies may not appear in the dependency scan.
- **Binary artifacts:** This audit scans source code only.
- **Legal interpretation:** Whether a specific match constitutes infringement is a legal question. This audit identifies potential issues for legal review.
- **SaaS distribution assumption:** SaaS verdicts assume the edition is never distributed. If the business model changes, the GPL Dependency Register (currently empty) must be re-evaluated.

---

## Audit Trail

| Phase | Document | Scope |
|---|---|---|
| 0860a | `audit/DEPENDENCY_LICENSES.md` | pip-licenses (268 Python) + license-checker (383 npm) |
| 0860b | `audit/SCANCODE_FINDINGS.md` | ScanCode license + copyright scan of 494 source files |
| 0860c | `audit/SCANOSS_FINDINGS.md` | SCANOSS snippet provenance scan of 384 source files |
| 0860d | `audit/AUDIT_SUMMARY.md` | This document — consolidated findings and verdicts |

Raw scan data (JSON) is in the `audit/` directory but excluded from git commits per audit protocol.

---

## Owner Review Resolution (2026-03-30)

All 4 REVIEW items assessed by project owner (Patrik Pettersson). Resolution:

| # | Item | Resolution | Rationale |
|---|------|-----------|-----------|
| 1 | useToast.js (79% SCANOSS match) | **CLEARED** | Common Vue notification pattern used by thousands of projects. Matched component has no license — no conflict exists. Independently authored boilerplate. |
| 2 | psycopg2-binary (LGPL w/ exception) | **CLEARED** | LGPL exception clause explicitly permits linking without copyleft obligation. Industry-standard PostgreSQL driver used by virtually every Python+PostgreSQL application. |
| 3 | pycountry (LGPL-2.1) | **CLEARED** | Transitive dependency via sumy. Standard dynamic linking — LGPL-2.1 does not trigger copyleft for the larger work under dynamic linking. |
| 4 | PyGithub (LGPL) | **CLEARED** | Not in pyproject.toml. Not a shipped dependency. Present only as a transitive install from audit tooling (scancode-toolkit). Does not ship with CE or SaaS. |

**Updated Verdicts:**

### CE Edition: PASS
### SaaS Edition: PASS

No remaining REVIEW or BLOCK items. Audit gate cleared for CE public launch April 5, 2026.
