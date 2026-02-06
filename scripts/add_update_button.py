#!/usr/bin/env python3
"""Add 'Update Graph' button to dependency graph HTML."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
HTML_FILE = PROJECT_ROOT / "docs" / "cleanup" / "dependency_graph.html"

UPDATE_BUTTON_HTML = """
<button id="update-graph" title="Regenerate dependency graph from current codebase">
  <span id="update-icon">🔄</span> Update Graph
</button>
"""

UPDATE_BUTTON_STYLE = """
#update-graph {
  width: 100%;
  padding: 8px;
  margin: 10px 0;
  background: #0f172a;
  border: 1px solid #334155;
  color: #60a5fa;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

#update-graph:hover {
  background: #334155;
  border-color: #60a5fa;
  color: #93c5fd;
}

#update-graph:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

#update-icon {
  display: inline-block;
  transition: transform 0.6s;
}

#update-graph.updating #update-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.update-status {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 5px;
  text-align: center;
}

.update-status.success {
  color: #22c55e;
}

.update-status.error {
  color: #ef4444;
}
"""

UPDATE_BUTTON_SCRIPT = """
async function updateGraph() {
  const btn = document.getElementById('update-graph');
  const statusDiv = document.getElementById('update-status');

  if (!statusDiv) {
    const div = document.createElement('div');
    div.id = 'update-status';
    div.className = 'update-status';
    btn.parentElement.appendChild(div);
  }

  try {
    btn.disabled = true;
    btn.classList.add('updating');
    document.getElementById('update-status').textContent = 'Scanning codebase...';
    document.getElementById('update-status').className = 'update-status';

    const response = await fetch('/api/admin/update-dependency-graph', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();

    document.getElementById('update-status').textContent = 'Graph updated! Reloading...';
    document.getElementById('update-status').className = 'update-status success';

    // Reload page after 1 second to show new data
    setTimeout(() => {
      window.location.reload();
    }, 1000);

  } catch (error) {
    document.getElementById('update-status').textContent = `Error: ${error.message}`;
    document.getElementById('update-status').className = 'update-status error';
    btn.disabled = false;
    btn.classList.remove('updating');
  }
}

document.getElementById('update-graph')?.addEventListener('click', updateGraph);
"""


def main():
    print(f"Reading HTML from {HTML_FILE}...")
    html_content = HTML_FILE.read_text(encoding='utf-8')

    # Check if button already exists
    if 'id="update-graph"' in html_content:
        print("Update button already exists. Skipping...")
        return 0

    # Add button after reset-view button
    reset_button = '<button id="reset-view">Reset View</button>'
    if reset_button not in html_content:
        print("ERROR: Could not find reset-view button")
        return 1

    html_content = html_content.replace(
        reset_button,
        reset_button + '\n' + UPDATE_BUTTON_HTML
    )

    # Add styles
    style_end = '</style>'
    style_insertion = html_content.rfind(style_end)
    if style_insertion == -1:
        print("ERROR: Could not find style section")
        return 1

    html_content = (
        html_content[:style_insertion] +
        UPDATE_BUTTON_STYLE +
        html_content[style_insertion:]
    )

    # Add script
    script_end = '</script>\n</body>'
    script_insertion = html_content.rfind(script_end)
    if script_insertion == -1:
        print("ERROR: Could not find script section")
        return 1

    html_content = (
        html_content[:script_insertion] +
        UPDATE_BUTTON_SCRIPT +
        html_content[script_insertion:]
    )

    # Write back
    print(f"Writing updated HTML to {HTML_FILE}...")
    HTML_FILE.write_text(html_content, encoding='utf-8')

    print("[SUCCESS] Added update button to dependency graph")
    print("\nFeatures:")
    print("  - Click 'Update Graph' to regenerate from current codebase")
    print("  - Shows progress spinner and status messages")
    print("  - Auto-reloads page after successful update")
    print("  - No LLM required - pure static analysis")

    return 0


if __name__ == "__main__":
    exit(main())
