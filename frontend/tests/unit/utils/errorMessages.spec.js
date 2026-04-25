/**
 * SEC-0001 — parseErrorResponse + ERROR_MESSAGES upload additions.
 *
 * Focused spec covering the two frontend changes in errorMessages.js:
 *   1. Four new UPLOAD_* keys so `getErrorMessage()` returns friendly copy
 *      when the backend response omits `message`.
 *   2. Defensive unwrap of `error.response.data.detail.error_code` (the
 *      shape FastAPI produces when the backend raises `HTTPException`
 *      with a dict `detail` — see api/exception_handlers.py:58).
 */
import { describe, it, expect } from 'vitest'
import errorMessagesModule, {
  getErrorMessage,
  parseErrorResponse,
} from '@/utils/errorMessages'

const { ERROR_MESSAGES } = errorMessagesModule

describe('ERROR_MESSAGES — SEC-0001 upload keys', () => {
  it.each([
    ['UPLOAD_TOO_LARGE', /5\s?MB/],
    ['UPLOAD_TYPE_NOT_ALLOWED', /\.txt.*\.md/i],
    ['UPLOAD_CONTENT_NOT_TEXT', /plain text/i],
    ['UPLOAD_FILENAME_INVALID', /filename/i],
  ])('maps %s to user-friendly copy', (code, pattern) => {
    expect(ERROR_MESSAGES[code]).toMatch(pattern)
    expect(getErrorMessage(code)).toMatch(pattern)
  })
})

describe('parseErrorResponse — structured body passthrough', () => {
  it('surfaces backend detail verbatim when error_code is top-level', () => {
    const error = {
      response: {
        status: 415,
        data: {
          error_code: 'UPLOAD_TYPE_NOT_ALLOWED',
          message: 'Only .txt, .md, and .markdown files are accepted.',
          context: { filename: 'evil.pdf' },
        },
      },
    }
    const parsed = parseErrorResponse(error)
    expect(parsed.isStructured).toBe(true)
    expect(parsed.errorCode).toBe('UPLOAD_TYPE_NOT_ALLOWED')
    expect(parsed.message).toBe('Only .txt, .md, and .markdown files are accepted.')
    expect(parsed.status).toBe(415)
    expect(parsed.context).toEqual({ filename: 'evil.pdf' })
  })

  it('falls back to ERROR_MESSAGES copy when backend omits message', () => {
    const error = {
      response: {
        status: 413,
        data: { error_code: 'UPLOAD_TOO_LARGE' },
      },
    }
    const parsed = parseErrorResponse(error)
    expect(parsed.errorCode).toBe('UPLOAD_TOO_LARGE')
    expect(parsed.message).toMatch(/5\s?MB/)
  })
})

describe('parseErrorResponse — FastAPI HTTPException dict-detail unwrap', () => {
  it('unwraps response.data.detail.error_code when body is nested', () => {
    const error = {
      response: {
        status: 413,
        data: {
          detail: {
            error_code: 'UPLOAD_TOO_LARGE',
            message: 'File is too large. Maximum size is 5 MB.',
            context: { max_bytes: 5242880 },
          },
        },
      },
    }
    const parsed = parseErrorResponse(error)
    expect(parsed.isStructured).toBe(true)
    expect(parsed.errorCode).toBe('UPLOAD_TOO_LARGE')
    expect(parsed.message).toBe('File is too large. Maximum size is 5 MB.')
    expect(parsed.status).toBe(413)
    expect(parsed.context).toEqual({ max_bytes: 5242880 })
  })

  it('prefers top-level error_code over nested detail when both are present', () => {
    const error = {
      response: {
        status: 400,
        data: {
          error_code: 'UPLOAD_FILENAME_INVALID',
          message: 'top-level wins',
          detail: { error_code: 'UPLOAD_TYPE_NOT_ALLOWED', message: 'nested loses' },
        },
      },
    }
    const parsed = parseErrorResponse(error)
    expect(parsed.errorCode).toBe('UPLOAD_FILENAME_INVALID')
    expect(parsed.message).toBe('top-level wins')
  })
})
