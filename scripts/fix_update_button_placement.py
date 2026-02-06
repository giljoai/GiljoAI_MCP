#!/usr/bin/env python3
"""Fix update button placement - insert inside controls div."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
HTML_FILE = PROJECT_ROOT / "docs" / "cleanup" / "dependency_graph.html"

def main():
    print(f"Reading HTML from {HTML_FILE}...")
    html = HTML_FILE.read_text(encoding='utf-8')

    # Remove existing misplaced button if present
    if 'id="update-graph"' in html:
        print("Removing misplaced update button...")
        # Remove button HTML
        start_marker = '<button id="update-graph"'
        end_marker = '</button>'

        start_idx = html.find(start_marker)
        if start_idx != -1:
            end_idx = html.find(end_marker, start_idx) + len(end_marker)
            html = html[:start_idx] + html[end_idx:]

        # Remove button styles (we'll re-add them properly)
        style_start = html.find('#update-graph')
        if style_start != -1:
            # Find the start of this rule
            brace_start = html.rfind('{', 0, style_start)
            # Find closing of the animation
            anim_end = html.find('}', html.find('@keyframes spin'))
            if brace_start != -1 and anim_end != -1:
                # Remove from #update-graph to end of keyframes
                html = html[:style_start] + html[anim_end + 1:]

        # Remove button script
        script_start = html.find('async function updateGraph')
        if script_start != -1:
            script_end = html.find("document.getElementById('update-graph')", script_start)
            script_end = html.find(';', script_end) + 1
            if script_end > script_start:
                html = html[:script_start] + html[script_end:]

    # Find the correct insertion point - inside controls div, after reset-view
    # Pattern: <button id="reset-view">Reset View</button> followed by more content
    reset_button_end = html.find('</button>', html.find('id="reset-view"'))
    if reset_button_end == -1:
        print("ERROR: Could not find reset-view button")
        return 1

    insert_point = reset_button_end + len('</button>')

    # Build button HTML (no emoji to avoid encoding issues)
    button_html = '\n<button id="update-graph" title="Regenerate dependency graph from current codebase">\n  <span id="update-icon">[UPDATE]</span> Update Graph\n</button>\n'

    # Insert button
    html = html[:insert_point] + button_html + html[insert_point:]

    # Add styles before closing style tag
    style_end_idx = html.find('</style>')
    if style_end_idx == -1:
        print("ERROR: Could not find closing style tag")
        return 1

    button_styles = """
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
  margin-right: 6px;
}

#update-graph.updating #update-icon::after {
  content: '...';
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

    html = html[:style_end_idx] + button_styles + html[style_end_idx:]

    # Add script before closing script tag
    last_script_close = html.rfind('</script>')
    if last_script_close == -1:
        print("ERROR: Could not find closing script tag")
        return 1

    button_script = """
async function updateGraph() {
  const btn = document.getElementById('update-graph');
  let statusDiv = document.getElementById('update-status');

  if (!statusDiv) {
    statusDiv = document.createElement('div');
    statusDiv.id = 'update-status';
    statusDiv.className = 'update-status';
    btn.parentElement.appendChild(statusDiv);
  }

  try {
    btn.disabled = true;
    btn.classList.add('updating');
    statusDiv.textContent = 'Scanning codebase...';
    statusDiv.className = 'update-status';

    const response = await fetch('/api/admin/update-dependency-graph', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();

    statusDiv.textContent = 'Graph updated! Reloading...';
    statusDiv.className = 'update-status success';

    setTimeout(() => {
      window.location.reload();
    }, 1000);

  } catch (error) {
    statusDiv.textContent = `Error: ${error.message}. Try running: python scripts/update_dependency_graph_full.py`;
    statusDiv.className = 'update-status error';
    btn.disabled = false;
    btn.classList.remove('updating');
  }
}

const updateBtn = document.getElementById('update-graph');
if (updateBtn) {
  updateBtn.addEventListener('click', updateGraph);
}
"""

    html = html[:last_script_close] + button_script + html[last_script_close:]

    # Write back
    print(f"Writing fixed HTML to {HTML_FILE}...")
    HTML_FILE.write_text(html, encoding='utf-8')

    print("[SUCCESS] Update button fixed and properly placed")
    print("\nButton is now inside the controls div (left sidebar)")
    print("Refresh your browser to see it!")

    return 0

if __name__ == "__main__":
    exit(main())
