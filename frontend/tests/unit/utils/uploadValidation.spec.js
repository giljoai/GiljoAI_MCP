/**
 * SEC-0001 Phase 2 — Upload pre-check validator.
 *
 * TDD: these tests are written BEFORE the implementation. They pin the
 * client-side UX guard that mirrors the backend upload allowlist
 * (TXT / MD / markdown, 5 MB cap). The frontend is a fail-fast UX layer
 * — the backend remains the authoritative security boundary.
 */
import { describe, it, expect } from 'vitest'
import {
  MAX_UPLOAD_BYTES,
  ALLOWED_UPLOAD_EXTENSIONS,
  validateUploadFile,
  validateUploadFiles,
} from '@/utils/uploadValidation'

function makeFile(name, sizeBytes) {
  // jsdom File supports size via Blob content length. A single repeat is
  // enough for jsdom to report the correct .size without allocating GB.
  const blob = new Blob([new Uint8Array(sizeBytes)], { type: 'text/plain' })
  return new File([blob], name, { type: 'text/plain' })
}

describe('uploadValidation — SEC-0001 constants', () => {
  it('exposes the 5 MB cap shared with backend UploadConfig.max_upload_bytes', () => {
    expect(MAX_UPLOAD_BYTES).toBe(5 * 1024 * 1024)
  })

  it('allows .txt, .md, and .markdown (matches backend TEXT_EXTENSIONS)', () => {
    expect(ALLOWED_UPLOAD_EXTENSIONS).toEqual(['.txt', '.md', '.markdown'])
  })
})

describe('validateUploadFile — single file pre-check', () => {
  it('accepts a plain .txt file under the cap', () => {
    const result = validateUploadFile(makeFile('vision.txt', 1024))
    expect(result.valid).toBe(true)
    expect(result.errorCode).toBeNull()
  })

  it('accepts a .md file', () => {
    const result = validateUploadFile(makeFile('roadmap.md', 2048))
    expect(result.valid).toBe(true)
  })

  it('accepts a .markdown file', () => {
    const result = validateUploadFile(makeFile('spec.markdown', 100))
    expect(result.valid).toBe(true)
  })

  it('is case-insensitive on extensions (.TXT, .MD, .Markdown)', () => {
    expect(validateUploadFile(makeFile('UPPER.TXT', 100)).valid).toBe(true)
    expect(validateUploadFile(makeFile('MixedCase.Md', 100)).valid).toBe(true)
    expect(validateUploadFile(makeFile('Odd.Markdown', 100)).valid).toBe(true)
  })

  it('rejects a .pdf file with UPLOAD_TYPE_NOT_ALLOWED', () => {
    const result = validateUploadFile(makeFile('doc.pdf', 100))
    expect(result.valid).toBe(false)
    expect(result.errorCode).toBe('UPLOAD_TYPE_NOT_ALLOWED')
    expect(result.message).toMatch(/\.txt.*\.md/i)
  })

  it('rejects a .docx file with UPLOAD_TYPE_NOT_ALLOWED', () => {
    const result = validateUploadFile(makeFile('doc.docx', 100))
    expect(result.valid).toBe(false)
    expect(result.errorCode).toBe('UPLOAD_TYPE_NOT_ALLOWED')
  })

  it('rejects a file with no extension', () => {
    const result = validateUploadFile(makeFile('README', 100))
    expect(result.valid).toBe(false)
    expect(result.errorCode).toBe('UPLOAD_TYPE_NOT_ALLOWED')
  })

  it('rejects a 6 MB file with UPLOAD_TOO_LARGE', () => {
    const result = validateUploadFile(makeFile('big.txt', 6 * 1024 * 1024))
    expect(result.valid).toBe(false)
    expect(result.errorCode).toBe('UPLOAD_TOO_LARGE')
    expect(result.message).toMatch(/5\s?MB/i)
  })

  it('accepts a 4.9 MB file (just under the cap)', () => {
    const size = Math.floor(4.9 * 1024 * 1024)
    const result = validateUploadFile(makeFile('edge.txt', size))
    expect(result.valid).toBe(true)
  })

  it('accepts a file exactly equal to the cap (5 MB)', () => {
    const result = validateUploadFile(makeFile('exact.txt', MAX_UPLOAD_BYTES))
    expect(result.valid).toBe(true)
  })

  it('rejects a file one byte over the cap', () => {
    const result = validateUploadFile(makeFile('over.txt', MAX_UPLOAD_BYTES + 1))
    expect(result.valid).toBe(false)
    expect(result.errorCode).toBe('UPLOAD_TOO_LARGE')
  })

  it('accepts an empty 0-byte file (backend is source of truth for empty-file policy)', () => {
    const result = validateUploadFile(makeFile('empty.txt', 0))
    expect(result.valid).toBe(true)
  })

  it('rejects a null / undefined file with UPLOAD_FILENAME_INVALID', () => {
    expect(validateUploadFile(null).errorCode).toBe('UPLOAD_FILENAME_INVALID')
    expect(validateUploadFile(undefined).errorCode).toBe('UPLOAD_FILENAME_INVALID')
  })

  it('rejects a file with empty name', () => {
    const result = validateUploadFile(makeFile('', 100))
    expect(result.valid).toBe(false)
    expect(result.errorCode).toBe('UPLOAD_FILENAME_INVALID')
  })
})

describe('validateUploadFiles — batch pre-check', () => {
  it('returns { valid: true } when every file passes', () => {
    const files = [makeFile('a.txt', 100), makeFile('b.md', 200)]
    const result = validateUploadFiles(files)
    expect(result.valid).toBe(true)
    expect(result.invalid).toEqual([])
  })

  it('returns the first failing file so caller can surface a focused error', () => {
    const files = [
      makeFile('ok.txt', 100),
      makeFile('bad.pdf', 100),
      makeFile('huge.md', 10 * 1024 * 1024),
    ]
    const result = validateUploadFiles(files)
    expect(result.valid).toBe(false)
    expect(result.invalid.length).toBeGreaterThanOrEqual(1)
    expect(result.invalid[0].file.name).toBe('bad.pdf')
    expect(result.invalid[0].errorCode).toBe('UPLOAD_TYPE_NOT_ALLOWED')
  })

  it('returns valid when the list is empty', () => {
    expect(validateUploadFiles([]).valid).toBe(true)
    expect(validateUploadFiles(null).valid).toBe(true)
    expect(validateUploadFiles(undefined).valid).toBe(true)
  })
})
