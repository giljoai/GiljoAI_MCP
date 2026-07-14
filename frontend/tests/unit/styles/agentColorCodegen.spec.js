/**
 * Test: agent-color codegen freshness (FE-9129)
 *
 * Renders the generator's managed regions in memory and asserts they
 * string-equal what's currently committed between the markers. Fails any
 * PR where agentColors.js changed without re-running `npm run
 * codegen:colors`, or where a generated region was hand-edited.
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'fs'
import { resolve } from 'path'
import { renderAgentColorsScssRegion, renderDesignTokensScssRegion } from '../../../scripts/generate-agent-colors.mjs'

const agentColorsScssPath = resolve(__dirname, '../../../src/styles/agent-colors.scss')
const designTokensScssPath = resolve(__dirname, '../../../src/styles/design-tokens.scss')

const BEGIN_MARKER = '// giljo:agent-colors:generated:begin'
const END_MARKER = '// giljo:agent-colors:generated:end'

function extractRegion(source) {
  const beginIdx = source.indexOf(BEGIN_MARKER)
  const endIdx = source.indexOf(END_MARKER)
  if (beginIdx === -1 || endIdx === -1) {
    throw new Error(`markers not found: ${BEGIN_MARKER} / ${END_MARKER}`)
  }
  const beginLineEnd = source.indexOf('\n', beginIdx) + 1
  const endLineStart = source.lastIndexOf('\n', endIdx) + 1
  // Normalize CRLF -> LF: this repo's .gitattributes leaves *.scss on the
  // generic `text=auto` rule, so a Windows checkout with core.autocrlf=true
  // may have CRLF on disk. The render functions are EOL-agnostic (LF);
  // byte-for-byte EOL matching is proven separately by the compiled-CSS
  // comparison, which parses either.
  return source.slice(beginLineEnd, endLineStart - 1).replace(/\r/g, '')
}

describe('agentColorCodegen', () => {
  it('agent-colors.scss managed region matches the rendered output of agentColors.js', () => {
    const current = extractRegion(readFileSync(agentColorsScssPath, 'utf-8'))
    expect(current).toBe(renderAgentColorsScssRegion())
  })

  it('design-tokens.scss managed region matches the rendered output of agentColors.js', () => {
    const current = extractRegion(readFileSync(designTokensScssPath, 'utf-8'))
    expect(current).toBe(renderDesignTokensScssRegion())
  })
})
