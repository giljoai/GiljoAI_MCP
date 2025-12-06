import { ESLint } from 'eslint'
import fs from 'fs'

const eslint = new ESLint({
  overrideConfigFile: './.eslintrc.json',
})

const results = await eslint.lintFiles(['src/**/*.{vue,js,jsx,ts,tsx}'])
fs.writeFileSync('../temp/eslint_results.json', JSON.stringify(results, null, 2))

let totalErrors = 0
let totalWarnings = 0
for (const result of results) {
  totalErrors += result.errorCount
  totalWarnings += result.warningCount
}

console.log(`ESLint scan complete: ${results.length} files, ${totalErrors} errors, ${totalWarnings} warnings`)
