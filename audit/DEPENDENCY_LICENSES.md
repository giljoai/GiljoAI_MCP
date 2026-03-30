# Dependency License Audit Report

**Date:** 2026-03-30
**Tools:** pip-licenses 5.5.5, license-checker 25.0.1
**Branch:** feature/0860-license-audit

---

## Summary Counts

| Metric | Python | npm |
|---|---|---|
| Total packages | 268 | 383 (incl. own project) |
| Permissive (MIT/BSD/Apache/ISC/PSF/etc.) | 248 | 381 |
| Copyleft or mixed | 19 | 1 |
| Unknown | 1 | 0 |

**AGPL dependencies found: ZERO** — no AGPL blockers for either edition.

---

## Flagged Dependencies

### BLOCK (Both Editions) — AGPL

**None found.**

### BLOCK (CE Only) — GPL

| Package | Version | License | Required By | CE Impact | SaaS Impact |
|---|---|---|---|---|---|
| gemfileparser2 | 0.9.4 | GPL-3.0-or-later OR MIT | scancode-toolkit (audit tool only) | N/A (not shipped) | N/A |
| text-unidecode | 1.3 | Artistic License; GPL; GPLv2+ | scancode-toolkit (audit tool only) | N/A (not shipped) | N/A |
| docutils | 0.22.2 | BSD; GPL; Public Domain | rich-rst (dev tooling) | N/A (not shipped) | N/A |
| typecode-libmagic | 5.39.210531 | apache-2.0 AND ... (bsd-new OR gpl-1.0-plus) ... | scancode-toolkit (audit tool only) | N/A (not shipped) | N/A |

**Assessment:** All GPL-flagged packages are dependencies of the audit tools (scancode-toolkit) or dev tooling — they are NOT shipped with CE or SaaS. These are **non-issues** for both editions but documented for completeness.

### REVIEW — LGPL

| Package | Version | License | Required By | CE Impact | SaaS Impact |
|---|---|---|---|---|---|
| psycopg2-binary | 2.9.10 | LGPL with exceptions | **Direct project dep** | REVIEW | SAFE |
| chardet | 5.2.0 | LGPLv2+ | scancode-toolkit (audit tool only) | N/A (not shipped) | N/A |
| intbitset | 4.1.0 | LGPLv3+ | scancode-toolkit (audit tool only) | N/A (not shipped) | N/A |
| crc32c | 2.8 | LGPLv2+ | scanoss (audit tool only) | N/A (not shipped) | N/A |
| pycountry | 26.2.16 | LGPL-2.1-only | sumy -> **Direct project dep** | REVIEW | SAFE |
| PyGithub | 2.8.1 | LGPL | **Dev/integration tool** | REVIEW | SAFE |
| extractcode-7z | 16.5.210531 | apache-2.0 AND lgpl-2.1 AND unrar | scancode-toolkit (audit tool only) | N/A (not shipped) | N/A |

**Key findings for CE:**

1. **psycopg2-binary (LGPL with exceptions):** This is a direct project dependency. The "exceptions" clause in psycopg2's LGPL license specifically permits linking without copyleft obligations. The psycopg2 project explicitly states this. **CE: SAFE** (LGPL exception applies). No action needed.

2. **pycountry (LGPL-2.1-only):** Transitive dep via sumy (direct project dep). Used as a dynamically linked Python package, not copied into codebase. Under LGPL terms, dynamic linking is permitted. **CE: REVIEW** — verify no pycountry source is vendored.

3. **PyGithub (LGPL):** Not listed in pyproject.toml direct deps. Likely installed separately for GitHub integration scripting. If not shipped with CE, this is a non-issue. **CE: REVIEW** — verify not shipped.

### REVIEW — MPL-2.0

| Package | Version | License | Required By | CE Impact | SaaS Impact |
|---|---|---|---|---|---|
| certifi | 2025.8.3 | MPL-2.0 | httpx, requests (direct deps) | REVIEW | SAFE |
| fqdn | 1.5.1 | MPL-2.0 | scancode-toolkit (audit tool only) | N/A | N/A |
| pathspec | 0.12.1 | MPL-2.0 | black (dev dep only) | N/A | N/A |
| publicsuffix2 | 2.20191221 | MIT; MPL-2.0 | scancode-toolkit (audit tool only) | N/A | N/A |
| tqdm | 4.67.1 | MIT; MPL-2.0 | Various | REVIEW | SAFE |

**Key findings for CE:**

1. **certifi (MPL-2.0):** Transitive dep of httpx/requests (direct project deps). MPL-2.0 is file-level copyleft — safe as long as certifi files are unmodified (they always are, it's a CA bundle). **CE: SAFE** in practice.

2. **tqdm (MIT; MPL-2.0):** Dual-licensed MIT/MPL-2.0. Can be used under MIT terms. **CE: SAFE.**

### REVIEW — Unknown License

| Package | Version | License | Required By | CE Impact | SaaS Impact |
|---|---|---|---|---|---|
| multiregex | 2.0.3 | UNKNOWN (actually MIT per PyPI) | scancode-toolkit (audit tool only) | N/A | N/A |

### REVIEW — Other Copyleft Flags

| Package | Version | License | Required By | CE Impact | SaaS Impact |
|---|---|---|---|---|---|
| scancode-toolkit | 32.5.0 | Apache-2.0 AND CC-BY-4.0 AND other-permissive AND other-copyleft | Audit tool only | N/A | N/A |
| extractcode-libarchive | 3.5.1.210531 | apache-2.0 AND bsd AND other-copyleft | scancode-toolkit (audit tool only) | N/A | N/A |

### npm Flagged Items

| Package | Version | License | CE Impact | SaaS Impact |
|---|---|---|---|---|
| dompurify | 3.3.1 | (MPL-2.0 OR Apache-2.0) | SAFE | SAFE |
| giljo-mcp-frontend | 1.0.0 | UNLICENSED | N/A (own project) | N/A |

**dompurify** is dual-licensed MPL-2.0 OR Apache-2.0. Using it under Apache-2.0 terms. **SAFE for both editions.**

**giljo-mcp-frontend** is our own project package. UNLICENSED is expected — it's under GiljoAI Community License.

---

## Python Dependency Table (by license)

Full data in `audit/python_dep_licenses.json` (268 packages).

**License distribution:**
- MIT / MIT License: 103
- Apache Software License / Apache-2.0: 62
- BSD / BSD License / BSD-2-Clause / BSD-3-Clause: 55
- ISC: 4
- PSF / Python-2.0: 5
- Unlicense: 2
- MPL-2.0 (including dual): 5
- LGPL (various): 7
- GPL (various, all audit tools): 4
- Other/Mixed permissive: 20
- Unknown: 1

## npm Dependency Table (by license)

Full data in `audit/npm_dep_licenses.json` (383 packages).

**License distribution:**
- MIT: 297
- ISC: 27
- Apache-2.0: 23
- BSD-2-Clause: 14
- BSD-3-Clause: 8
- BlueOak-1.0.0: 3
- MIT-0: 2
- Other permissive: 7
- MPL-2.0 (dual with Apache): 1
- UNLICENSED (own project): 1

---

## Verdict for 0860a (Dependency-Only Scan)

### AGPL: CLEAR — Zero AGPL dependencies in either ecosystem.

### CE Edition Dependencies:
- **No GPL dependencies ship with CE** (all GPL packages are audit-tool-only)
- **Two LGPL dependencies to verify:** psycopg2-binary (has LGPL exception — safe), pycountry (dynamic linking — safe in standard usage)
- **MPL deps (certifi, tqdm):** Safe — unmodified files / dual-licensed

### SaaS Edition Dependencies:
- **All clear.** LGPL/GPL/MPL are SAFE for SaaS under no-distribution assumption.

### Recommendation:
No blockers found. Proceed with source-level scanning (0860b, 0860c) to verify no copyleft code is embedded in project source files.
