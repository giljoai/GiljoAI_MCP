# Upload Guardrails — Vision Documents (SEC-0001, 2026-Q2)

*Last updated: 2026-04-24*

This document is the security-posture reference for file uploads on the two
vision-document endpoints. It describes what the server accepts, what it
rejects, and the mechanism that enforces the rules. For the broader server
trust model, see [`docs/SECURITY_POSTURE.md`](../SECURITY_POSTURE.md) and
[`docs/ARCHITECTURE.md#trust-model-pitch`](../ARCHITECTURE.md#trust-model-pitch).

## Policy

- **Accepted:** `.txt`, `.md`, `.markdown` only. Content must be valid UTF-8
  text.
- **Rejected:** every other file type and any payload that is not strict UTF-8
  text (including files with a spoofed `.txt` extension whose bytes are PDF,
  PNG, ZIP, JPEG, ELF, GZIP, JPEG-XL, or UTF-16).
- **Size cap:** 5 MiB, enforced twice (once from `Content-Length` before the
  body is read, once with a streaming byte counter during read). Default is
  `5 * 1024 * 1024` bytes; overridable via `GILJO_MAX_UPLOAD_BYTES` or the
  YAML key `upload.max_bytes`.
- **Filename handling:** the original filename is preserved in the database
  record. The on-disk filename is a sanitized form; uploads whose filename
  cannot be sanitized are rejected at the boundary.

## Enforcement points

- **Helper module:** `src/giljo_mcp/security/upload_guard.py` (227 LOC,
  commit `b11714aa`). Pure functions — no I/O, no framework dependencies.
  Typed exceptions (`UploadFilenameError`, `UploadContentError`,
  `UploadSizeError`) subclass `ValueError` so endpoints can convert them to
  structured 4xx responses.
- **Config:** `UploadConfig` dataclass in `src/giljo_mcp/config_manager.py`
  (commit `6f8c4921`) — `max_upload_bytes=5 MiB`, `allowed_extensions=(.txt,
  .md, .markdown)`, `sniff_bytes=8192`.
- **Endpoint A:** `POST /api/vision-documents/` at
  `api/endpoints/vision_documents.py` — writes the sanitized file to
  `./products/{id}/vision/` and persists the original filename in the DB
  record.
- **Endpoint B:** `POST /api/v1/products/{product_id}/vision` at
  `api/endpoints/products/vision.py` — inline-only (no disk write) but
  publicly routable; hardened with the same chain because of exposure even
  though the UI does not currently use it.
- **Exception shape:** `api/exception_handlers.py` lifts the structured
  `{error_code, message, context, timestamp}` dict from
  `HTTPException.detail` to the response top level so the frontend's
  `parseErrorResponse` picks it up unmodified.
- **Wiring commit:** `1d6c4f9d`.

## Guard chain (order per endpoint)

1. `Content-Length` header pre-check — reject over-cap before reading the
   body (413).
2. Sanitize filename — reject path separators, absolute paths, NUL, C0
   control chars, Unicode bidi/RTL overrides, leading dots, Windows reserved
   device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`), and
   anything over 255 UTF-8 bytes after NFC normalization (400).
3. Extension allowlist — only `.txt`, `.md`, `.markdown` (415).
4. Streaming read with running byte counter — reject over-cap mid-stream
   (413). FastAPI `UploadFile` does not cap size on its own.
5. Byte-sniff of the first 8 KiB — reject if it contains binary C0 bytes
   (tolerating `\t`, `\n`, `\r` only) or matches known binary magic bytes
   (415).
6. Strict UTF-8 decode of the whole payload — the previous latin-1 fallback
   at `vision_documents.py:279` is gone; invalid UTF-8 now returns 415
   instead of silently decoding arbitrary bytes into the DB as "text".

## Error contract

| Code | HTTP | User message |
|---|---|---|
| `UPLOAD_FILENAME_INVALID` | 400 | Filename contains disallowed characters. |
| `UPLOAD_TYPE_NOT_ALLOWED` | 415 | Only TXT or MD files are accepted. |
| `UPLOAD_CONTENT_NOT_TEXT` | 415 | File is not valid UTF-8 text content. |
| `UPLOAD_TOO_LARGE` | 413 | File too large (max 5 MB). |

Response shape is top-level `{error_code, message, context, timestamp}`. The
frontend surfaces the server `message` verbatim via `parseErrorResponse`
(`frontend/src/utils/errorMessages.js`).

## What this prevents

- **Spoofed binary uploads.** A file named `malware.txt` whose bytes are a
  PDF, PNG, ZIP, JPEG, ELF, GZIP, or JPEG-XL is rejected with 415. The byte
  sniff does not trust the extension or the client-supplied `Content-Type`.
- **Memory-exhaustion DoS via large uploads.** The `Content-Length`
  pre-check rejects over-cap requests before the body is consumed, so an
  attacker cannot force the server to buffer a 2 GB body just to have it
  rejected afterwards. The streaming byte counter is a second layer in case
  the header is absent or lying.
- **Path-traversal via filename.** `../../etc/passwd`, `C:\Windows\...`,
  filenames containing NUL or control characters, and Unicode bidi override
  tricks (e.g., `file‮.txt` rendering as `file.txt` while being
  something else) are all rejected before any disk I/O runs. Endpoint A
  keeps its existing `resolve()` + `is_relative_to()` check as belt-and-
  braces, even though the sanitizer rejects separators earlier.
- **Permissive decoding of binary content.** The removed latin-1 fallback
  previously allowed arbitrary bytes to land in the DB as "text". Strict
  UTF-8 plus byte-sniff closes that path.

## What this does NOT cover

- **Virus / malware scanning.** Not applicable — we reject binary content
  outright, so there is no non-text payload to scan. If accepted file types
  expand beyond text in the future, this doc must be revisited.
- **Parser sandboxing.** Not applicable — plain UTF-8 text has no parser
  that could be exploited. If accepted file types grow to include
  structured formats (PDF, DOCX, HTML), a parser sandbox becomes
  in-scope.
- **Rate limiting of upload requests.** Covered by the global per-IP rate
  limiter described in the Trust Model; see
  [`docs/ARCHITECTURE.md#trust-model-pitch`](../ARCHITECTURE.md#trust-model-pitch)
  and `api/middleware/rate_limiter.py`.

## Test coverage

- **Backend unit:** `tests/security/test_upload_guard.py` — 73 parametrized
  cases covering every sanitizer rule plus PDF / PNG / ZIP / JPEG / ELF /
  GZIP / JPEG-XL / UTF-16 spoof detection and legitimate text/markdown
  regression.
- **Backend integration:** `tests/api/test_sec_0001_upload_endpoints.py` —
  16 cases exercising both endpoints for each of the four error codes, the
  legitimate `.txt` / `.md` / `.markdown` success paths, the inline-content
  branch of Endpoint A, and a cross-tenant regression on Endpoint B.
- **Frontend:** `frontend/tests/unit/utils/uploadValidation.spec.js` (19),
  `frontend/tests/unit/utils/errorMessages.spec.js` (8), and
  `frontend/tests/unit/views/ProductsView.upload-error-surface.spec.js` (4)
  — cover the client pre-check plus the backend-error-surface pipeline.
- **Total:** 89 backend + 31 frontend = 120 SEC-0001 tests.

## Commits

- `b11714aa` — `feat(SEC-0001): add upload_guard helper module (filename
  sanitizer + text sniff)`.
- `6f8c4921` — `feat(SEC-0001): add UploadConfig dataclass to ConfigManager`.
- `1d6c4f9d` — `feat(SEC-0001): wire upload guardrails into both
  vision-document endpoints`.
- `2ff89224` — `feat(SEC-0001): frontend upload pre-check + structured error
  surfacing`.
- `d552be33` — `docs(SEC-0001): upload surface analysis + edit plan`
  (analysis artifact, private handover).

## See also

- [`docs/SECURITY_POSTURE.md`](../SECURITY_POSTURE.md) — plain-English
  summary of the overall server trust model.
- [`docs/ARCHITECTURE.md#trust-model-pitch`](../ARCHITECTURE.md#trust-model-pitch)
  — engineering-depth Trust Model section with the Server DOES / DOES NOT
  lists.
- [`docs/security/SEC-0002_passive_server_audit.md`](SEC-0002_passive_server_audit.md)
  — the grep-evidence audit establishing the passive-server property this
  guardrail plugs into.
