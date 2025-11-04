/**
 * Natural language instruction generator for downloads
 * Provides AI-agent-friendly instructions for downloading and installing
 * GiljoAI MCP tools (slash commands and agent templates).
 *
 * Handover 0094: Token-Efficient Downloads
 */

/**
 * Generate natural language instructions for slash commands download
 * @param {string} downloadUrl - The download URL (from token-based endpoint)
 * @returns {string} AI-agent-friendly natural language instructions
 */
export function generateSlashCommandsInstructions(downloadUrl) {
  return `Download the slash commands from: ${downloadUrl}

Once downloaded:
1. Extract the ZIP file to your home directory
2. For Claude Code / Cursor / Windsurf:
   - Copy the .md files to ~/.claude/commands/
   - Copy install.sh or install.ps1 to run the installer
3. For macOS/Linux users, run: bash install.sh
4. For Windows users, run: powershell -ExecutionPolicy Bypass -File install.ps1
5. Restart your AI coding tool to load the new commands
6. Type "gil_" in your tool to see available GiljoAI slash commands`
}

/**
 * Generate natural language instructions for personal agents export
 * @param {string} downloadUrl - The download URL (from token-based endpoint)
 * @returns {string} AI-agent-friendly natural language instructions
 */
export function generatePersonalAgentsInstructions(downloadUrl) {
  return `Download personal agents from: ${downloadUrl}

Once downloaded, follow these steps:
1. Extract the ZIP file to find your agent templates
2. Install to global agents folder (available to all your projects):
   - macOS/Linux: Extract to ~/.claude/agents/
   - Windows: Extract to %USERPROFILE%\\.claude\\agents\\
3. Run the included install script if present:
   - macOS/Linux: bash install.sh
   - Windows: powershell -ExecutionPolicy Bypass -File install.ps1
4. Check the included instructions.md file for detailed setup steps
5. Restart your AI coding tool to load the agents
6. These agents will be available in all your projects`
}

/**
 * Generate natural language instructions for product agents export
 * @param {string} downloadUrl - The download URL (from token-based endpoint)
 * @returns {string} AI-agent-friendly natural language instructions
 */
export function generateProductAgentsInstructions(downloadUrl) {
  return `Download product agents from: ${downloadUrl}

Once downloaded, follow these steps:
1. Extract the ZIP file to find your agent templates
2. Install to project-specific agents folder:
   - macOS/Linux: Extract to .claude/agents/ in your project root
   - Windows: Extract to .\\.claude\\agents\\ in your project root
3. Run the included install script if present:
   - macOS/Linux: bash install.sh
   - Windows: powershell -ExecutionPolicy Bypass -File install.ps1
4. Check the included instructions.md file for detailed setup steps
5. Restart your AI coding tool
6. These agents will only be available in this project`
}

/**
 * Copy text to clipboard with fallback support
 * @param {string} text - Text to copy
 * @param {function} onSuccess - Callback on success
 * @param {function} onError - Callback on error
 */
export async function copyToClipboardSafe(text, onSuccess, onError) {
  try {
    // Try modern Clipboard API first
    if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
      try {
        await navigator.clipboard.writeText(text)
        onSuccess?.()
        return
      } catch (clipboardError) {
        console.warn('Clipboard API failed, trying fallback:', clipboardError)
      }
    }

    // Fallback method
    const fallbackCopy = () => {
      try {
        const textarea = document.createElement('textarea')
        textarea.value = text
        textarea.setAttribute('readonly', '')
        textarea.style.position = 'absolute'
        textarea.style.left = '-9999px'
        textarea.style.top = '0'
        document.body.appendChild(textarea)

        textarea.focus()
        textarea.select()

        // iOS compatibility
        if (navigator.userAgent.match(/ipad|iphone/i)) {
          const range = document.createRange()
          range.selectNodeContents(textarea)
          const selection = window.getSelection()
          selection.removeAllRanges()
          selection.addRange(range)
          textarea.setSelectionRange(0, text.length)
        }

        const success = document.execCommand('copy')
        document.body.removeChild(textarea)

        if (success) {
          onSuccess?.()
        } else {
          onError?.('Fallback copy failed')
        }
      } catch (err) {
        console.error('Fallback copy error:', err)
        onError?.(err.message)
      }
    }

    fallbackCopy()
  } catch (err) {
    console.error('Unexpected clipboard error:', err)
    onError?.(err.message)
  }
}

/**
 * Trigger browser download of blob
 * @param {Blob} blob - Blob to download
 * @param {string} filename - Filename for download
 */
export function downloadBlob(blob, filename) {
  try {
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.style.display = 'none'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Download error:', error)
    throw error
  }
}
