/**
 * Script to generate a subset of @mdi/js icons based on actual usage in the codebase.
 * Run with: node scripts/generate-icons.js
 */

import { execSync } from 'child_process'
import { writeFileSync } from 'fs'
import * as mdiIcons from '@mdi/js'

// Find all mdi-* icon usages in the codebase
const grepResult = execSync('grep -roh "mdi-[a-zA-Z0-9-]*" src/ | sort -u', {
  encoding: 'utf-8',
  cwd: process.cwd(),
})

const usedIcons = [
  ...new Set(
    grepResult
      .split('\n')
      .filter((line) => line && line !== 'mdi-')
      .map((iconName) => {
        // Convert mdi-account-circle to mdiAccountCircle
        const parts = iconName.split('-')
        return (
          parts[0] +
          parts
            .slice(1)
            .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
            .join('')
        )
      })
      .filter((iconName) => iconName in mdiIcons)
  ),
]

console.log(`Found ${usedIcons.length} unique icons in use`)

// Generate the icons subset file
const iconExports = usedIcons
  .map((iconName) => `  '${iconName}': mdi.${iconName},`)
  .join('\n')

const fileContent = `/**
 * Auto-generated icon subset based on actual usage in the codebase.
 * This file only includes icons that are actually used, reducing bundle size.
 *
 * Regenerate with: node scripts/generate-icons.js
 * Total icons: ${usedIcons.length} (vs 7000+ in full @mdi/js)
 */

import * as mdi from '@mdi/js'

export const iconPaths: Record<string, string> = {
${iconExports}
}

// Re-export for direct imports if needed
${usedIcons.map((name) => `export const ${name} = mdi.${name}`).join('\n')}
`

writeFileSync('src/plugins/icon-paths.ts', fileContent)
console.log('Generated src/plugins/icon-paths.ts')
