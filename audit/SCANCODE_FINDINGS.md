# ScanCode Source Scan Findings

**Audit phase:** 0860b (ScanCode Source Scanning)
**Date:** 2026-03-30
**ScanCode version:** 32.5.0 (SPDX License list v3.27)
**Branch:** `feature/0860-license-audit`

---

## 1. Scan Summary

| Scan | Files Scanned | Duration | Errors |
|------|--------------|----------|--------|
| Backend (`src/giljo_mcp/`, `api/`, `migrations/`, `install.py`) | 331 | 866.8s (~14 min) | 0 |
| Frontend — package manifests (`package.json`, `package-lock.json`) | 2 | 319.8s (~5 min) | 0 |
| Frontend — source files (`frontend/src/`) | 161 | 33.0s | 0 |
| **Total** | **494** | **~20 min** | **0** |

**Note:** The initial frontend scan with `--classify` filtered out all `.vue`/`.js` source files (ScanCode pre-scan ignore rules). A supplementary scan of `frontend/src/` was run without `--classify` and the results were merged into `scancode_frontend.json`.

**Missing scan targets:** `setup_gui.py` and `bootstrap.py` do not exist in the repository — omitted from the backend scan. This is a deviation from the handover spec but has no impact (files simply don't exist).

---

## 2. BLOCK — Both Editions (AGPL)

**None.**

Zero AGPL-licensed files or license headers detected in any scanned source file. This is consistent with the 0860a dependency scan which also found zero AGPL dependencies.

---

## 3. BLOCK — CE Only (GPL)

**None.**

Zero GPL-licensed files or license headers detected in any scanned source file. No GPL code is embedded in the project's own source files.

---

## 4. REVIEW Items

### 4a. High-Confidence Detections (score >= 80)

| # | File | License Detected | Score | Edition Impact | Assessment |
|---|------|-----------------|-------|---------------|------------|
| 1 | `frontend/package-lock.json` (line 3149) | MPL-2.0 OR Apache-2.0 | 100 | CE: SAFE, SaaS: SAFE | **dompurify@3.3.1** — dual-licensed. Project can elect Apache-2.0. No action needed. |
| 2 | `frontend/package.json` (line 6) | LicenseRef-scancode-unknown-license-reference | 100 | N/A | **giljo-mcp-frontend@1.0.0** — our own project declaring `"license": "SEE LICENSE IN LICENSE"`. Expected; not a third-party issue. |
| 3 | `frontend/package-lock.json` (line 10) | LicenseRef-scancode-unknown-license-reference | 100 | N/A | Same as above — lockfile mirrors the project's own license declaration. |

**Verdict:** All three REVIEW items are benign. No action required.

### 4b. Low-Confidence License Clues (for owner awareness)

These are "license clues" (not full detections) flagged by ScanCode. Per the handover's Rejection Authority rule, these are documented separately and do not affect the main findings.

| File | Clue Type | Score | Lines | Context |
|------|----------|-------|-------|---------|
| `api/endpoints/auth.py` | commercial-license | 100 | 734 | String literal: *"Multi-user deployments require a Commercial License."* — Our own licensing enforcement message. |
| `frontend/src/components/LicensingDialog.vue` | commercial-license | 100 | 6, 18, 21, 26 | Our licensing UI component discussing commercial license terms. |
| `frontend/src/components/navigation/AppBar.vue` | commercial-license | 100 | 138-139 | Navigation bar referencing licensing dialog. |
| `frontend/src/components/settings/tabs/NetworkSettingsTab.vue` | public-domain | 70 | 301 | Low-confidence clue; likely incidental text match. Below threshold. |

All clues are from our own code discussing GiljoAI's licensing model. No third-party license contamination.

---

## 5. GPL Dependency Register (SaaS TRACK)

**Empty.**

No GPL dependencies were detected in the source scan. The dependency-level GPL packages identified in 0860a (scancode-toolkit and scanoss themselves) are audit tools only, not shipped with either edition.

---

## 6. Dependency License Summary

The following license distribution was detected across all package manifests scanned by ScanCode in this phase. This covers npm packages declared in `package-lock.json`:

| License (SPDX) | Count | Status |
|----------------|-------|--------|
| MIT | 392 | SAFE |
| ISC | 32 | SAFE |
| Apache-2.0 | 27 | SAFE |
| BSD-2-Clause | 15 | SAFE |
| BSD-3-Clause | 9 | SAFE |
| BlueOak-1.0.0 | 3 | SAFE |
| MIT-0 | 2 | SAFE |
| CC0-1.0 | 2 | SAFE |
| CC-BY-4.0 | 1 | SAFE |
| MPL-2.0 (dual: OR Apache-2.0) | 1 | SAFE (elect Apache-2.0) |
| 0BSD | 1 | SAFE |

**Python source files:** Zero license headers detected in 331 backend files. All Python dependency licenses were catalogued in 0860a (`audit/DEPENDENCY_LICENSES.md`).

**Frontend source files:** Zero license headers detected in 161 `.vue`/`.js` files.

---

## 7. Copyright Anomalies

**None.**

Zero copyright statements were detected in any project source file (backend or frontend). This is expected — GiljoAI MCP source files do not carry per-file copyright headers. The project's copyright is established through the top-level LICENSE file.

No unexpected third-party copyright notices (e.g., "Copyright (c) FastAPI", "Copyright (c) Vue.js") were found embedded in project source code.

---

## Scan Artifacts

| File | Description |
|------|------------|
| `audit/scancode_backend.json` | Full backend scan results (331 files) |
| `audit/scancode_frontend.json` | Merged frontend scan results (2 manifest + 161 source files) |
| `audit/scancode_frontend_src.json` | Supplementary frontend source-only scan (kept for audit trail) |

---

## Conclusion

The ScanCode source scan found **zero license contamination** in the GiljoAI MCP codebase. No AGPL, GPL, LGPL, or any copyleft license headers are embedded in project source files. All npm dependency licenses detected in package manifests are permissive (MIT, ISC, Apache-2.0, BSD). The single MPL-2.0 detection (dompurify) is dual-licensed with Apache-2.0 and poses no risk.

**No blockers for CE launch from the ScanCode source scan perspective.**
