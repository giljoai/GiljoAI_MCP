/**
 * SEC-0001 Phase 2 — Frontend upload pre-check.
 *
 * Pure, dependency-free guard that mirrors the backend upload allowlist
 * (.txt / .md / .markdown, 5 MB cap). This is fail-fast UX only — the
 * backend (see `api/endpoints/vision_documents.py`, `api/endpoints/products/vision.py`,
 * and `src/giljo_mcp/security/upload_guard.py`) remains the authoritative
 * security boundary. Rejecting here avoids a pointless multipart POST for
 * files the server would refuse anyway.
 *
 * Keep `MAX_UPLOAD_BYTES` and `ALLOWED_UPLOAD_EXTENSIONS` in sync with
 * backend `UploadConfig` (`src/giljo_mcp/config_manager.py`) — if the
 * server cap changes, update this file AND the hint text in
 * `frontend/src/components/products/ProductForm.vue`.
 */

export const MAX_UPLOAD_BYTES = 5 * 1024 * 1024 // 5 MB
export const ALLOWED_UPLOAD_EXTENSIONS = ['.txt', '.md', '.markdown']

/**
 * Get the lowercased extension of a filename including the leading dot,
 * or an empty string if none is present.
 *
 * @param {string} filename
 * @returns {string}
 */
function getExtension(filename) {
  if (!filename || typeof filename !== 'string') return ''
  const dotIndex = filename.lastIndexOf('.')
  if (dotIndex === -1 || dotIndex === filename.length - 1) return ''
  return filename.slice(dotIndex).toLowerCase()
}

/**
 * Validate a single upload candidate against the SEC-0001 pre-check rules.
 * Returns an object mirroring the backend error contract so callers can
 * feed the result straight into `showToast` / `parseErrorResponse`-style
 * surfacing without extra mapping.
 *
 * @param {File | null | undefined} file
 * @returns {{ valid: boolean, errorCode: string | null, message: string | null }}
 */
export function validateUploadFile(file) {
  if (!file || typeof file.name !== 'string' || file.name.trim() === '') {
    return {
      valid: false,
      errorCode: 'UPLOAD_FILENAME_INVALID',
      message: 'Filename contains invalid characters or is empty.',
    }
  }

  const ext = getExtension(file.name)
  if (!ALLOWED_UPLOAD_EXTENSIONS.includes(ext)) {
    return {
      valid: false,
      errorCode: 'UPLOAD_TYPE_NOT_ALLOWED',
      message: 'Only .txt and .md files are accepted.',
    }
  }

  if (typeof file.size === 'number' && file.size > MAX_UPLOAD_BYTES) {
    return {
      valid: false,
      errorCode: 'UPLOAD_TOO_LARGE',
      message: 'File is too large. Maximum size is 5 MB.',
    }
  }

  return { valid: true, errorCode: null, message: null }
}

/**
 * Validate a batch of files (e.g. from a multi-select `<v-file-input>`).
 * Short-circuits on the first invalid file so the UI can surface a single
 * focused error instead of drowning the user in a wall of toasts.
 *
 * @param {File[] | null | undefined} files
 * @returns {{ valid: boolean, invalid: Array<{file: File, errorCode: string, message: string}> }}
 */
export function validateUploadFiles(files) {
  if (!files || files.length === 0) {
    return { valid: true, invalid: [] }
  }

  const invalid = []
  for (const file of files) {
    const result = validateUploadFile(file)
    if (!result.valid) {
      invalid.push({
        file,
        errorCode: result.errorCode,
        message: result.message,
      })
      // Fail fast — one toast per submit is clearer UX.
      break
    }
  }

  return { valid: invalid.length === 0, invalid }
}

export default {
  MAX_UPLOAD_BYTES,
  ALLOWED_UPLOAD_EXTENSIONS,
  validateUploadFile,
  validateUploadFiles,
}
