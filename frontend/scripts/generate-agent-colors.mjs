/**
 * Generates the agent-color managed regions in agent-colors.scss and
 * design-tokens.scss from agentColors.js — the single source of truth.
 *
 * Run via: npm run codegen:colors
 *
 * No shebang line: this module is also imported by
 * tests/unit/styles/agentColorCodegen.spec.js, and Vite's hashbang-strip
 * regex (/^#!.*\n/) misses a CRLF-terminated shebang on Windows checkouts,
 * so import-analysis injects hoisted code BEFORE the shebang and the parse
 * fails (RolldownError). Invoke with `node scripts/generate-agent-colors.mjs`.
 *
 * Rewrites ONLY the text strictly between the `giljo:agent-colors:generated`
 * marker comments (sass-stripped `//` comments — zero bytes in compiled
 * CSS). Idempotent: re-running with unchanged source data produces zero
 * diff. Everything outside the markers is hand-written and untouched.
 */
import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { dirname, resolve } from 'node:path'
import { AGENT_COLORS, AGENT_COLOR_SHADES, AGENT_COLOR_META } from '../src/config/agentColors.js'

const __dirname = dirname(fileURLToPath(import.meta.url))

const AGENT_COLORS_SCSS_PATH = resolve(__dirname, '../src/styles/agent-colors.scss')
const DESIGN_TOKENS_SCSS_PATH = resolve(__dirname, '../src/styles/design-tokens.scss')

const BEGIN_MARKER = '// giljo:agent-colors:generated:begin'
const END_MARKER = '// giljo:agent-colors:generated:end'

// SCSS-side legacy name that holds the REAL value for each canonical role.
// implementer/documenter are aliases pointing at implementor/researcher —
// preserve this asymmetry exactly, do not "fix" it.
const SCSS_REAL_NAME = {
  orchestrator: 'orchestrator',
  analyzer: 'analyzer',
  implementer: 'implementor',
  documenter: 'researcher',
  reviewer: 'reviewer',
  tester: 'tester',
}

// Heading display name per role, as it appears in agent-colors.scss's
// `/* <heading> - <swatch> — Luminous Pastels */` comments. Two roles show
// both the canonical and legacy name; the rest show a single name.
const SCSS_HEADING_NAME = {
  orchestrator: 'Orchestrator',
  analyzer: 'Analyzer',
  implementer: 'Implementer/Implementor',
  documenter: 'Documenter/Researcher',
  reviewer: 'Reviewer',
  tester: 'Tester',
}

// Region A role order (agent-colors.scss). Data, not derivable — matches
// the file's existing layout exactly.
const REGION_A_ORDER = ['orchestrator', 'analyzer', 'implementer', 'documenter', 'reviewer', 'tester']

// Region B role order (design-tokens.scss). Deliberately NOT the same order
// as Region A — matches the file's existing layout exactly.
const REGION_B_ORDER = ['orchestrator', 'analyzer', 'implementer', 'tester', 'documenter', 'reviewer']

// Roles whose canonical name differs from their SCSS real-value name and
// therefore need alias vars emitted after the real-value block.
const ALIASED_ROLES = new Set(['implementer', 'documenter'])

function hexToRgbaTinted(hex) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r}, ${g}, ${b}, 0.15)`
}

export function renderAgentColorsScssRegion() {
  const blocks = REGION_A_ORDER.map((role) => {
    const scssName = SCSS_REAL_NAME[role]
    const hex = AGENT_COLORS[role].hex.toLowerCase()
    const shades = AGENT_COLOR_SHADES[role]
    const heading = `  /* ${SCSS_HEADING_NAME[role]} - ${AGENT_COLOR_META[role].swatch} — Luminous Pastels */`
    const lines = [
      heading,
      `  --agent-${scssName}-primary: ${hex};`,
      `  --agent-${scssName}-dark: ${shades.dark};`,
      `  --agent-${scssName}-light: ${shades.light};`,
      `  --agent-${scssName}-tinted: ${hexToRgbaTinted(hex)};`,
    ]
    if (ALIASED_ROLES.has(role)) {
      lines.push(
        '  /* Alias variables for canonical naming */',
        `  --agent-${role}-primary: var(--agent-${scssName}-primary);`,
        `  --agent-${role}-dark: var(--agent-${scssName}-dark);`,
        `  --agent-${role}-light: var(--agent-${scssName}-light);`,
        `  --agent-${role}-tinted: var(--agent-${scssName}-tinted);`,
      )
    }
    return lines.join('\n')
  })
  return blocks.join('\n\n')
}

export function renderDesignTokensScssRegion() {
  return REGION_B_ORDER.map((role) => {
    const scssName = SCSS_REAL_NAME[role]
    const hex = AGENT_COLORS[role].hex.toLowerCase()
    const meta = AGENT_COLOR_META[role]
    return `$color-agent-${scssName}: ${hex}; // ${meta.swatch} — Luminous Pastels (WCAG ${meta.wcagRatio})`
  }).join('\n')
}

function replaceRegion(source, renderedBody, filePath) {
  const beginIdx = source.indexOf(BEGIN_MARKER)
  const endIdx = source.indexOf(END_MARKER)
  if (beginIdx === -1 || endIdx === -1) {
    throw new Error(
      `generate-agent-colors.mjs: markers not found in ${filePath}. ` +
        `Expected "${BEGIN_MARKER}" and "${END_MARKER}".`,
    )
  }
  const beginLineEnd = source.indexOf('\n', beginIdx) + 1
  const endLineStart = source.lastIndexOf('\n', endIdx) + 1
  return source.slice(0, beginLineEnd) + renderedBody + '\n' + source.slice(endLineStart)
}

function detectEol(content) {
  return content.includes('\r\n') ? '\r\n' : '\n'
}

function applyEol(content, eol) {
  return eol === '\r\n' ? content.replace(/\n/g, '\r\n') : content
}

export function regenerate() {
  const agentColorsScss = readFileSync(AGENT_COLORS_SCSS_PATH, 'utf-8')
  const agentColorsEol = detectEol(agentColorsScss)
  const nextAgentColorsScss = replaceRegion(
    agentColorsScss,
    applyEol(renderAgentColorsScssRegion(), agentColorsEol),
    AGENT_COLORS_SCSS_PATH,
  )
  writeFileSync(AGENT_COLORS_SCSS_PATH, nextAgentColorsScss)

  const designTokensScss = readFileSync(DESIGN_TOKENS_SCSS_PATH, 'utf-8')
  const designTokensEol = detectEol(designTokensScss)
  const nextDesignTokensScss = replaceRegion(
    designTokensScss,
    applyEol(renderDesignTokensScssRegion(), designTokensEol),
    DESIGN_TOKENS_SCSS_PATH,
  )
  writeFileSync(DESIGN_TOKENS_SCSS_PATH, nextDesignTokensScss)
}

const isMain = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href
if (isMain) {
  regenerate()
  console.log('generate-agent-colors: regenerated agent-colors.scss and design-tokens.scss managed regions.')
}
