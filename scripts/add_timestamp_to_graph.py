#!/usr/bin/env python3
"""Add timestamp display and update button handler to dependency graph HTML."""

from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).parent.parent
HTML_FILE = PROJECT_ROOT / "docs" / "cleanup" / "dependency_graph.html"


def add_timestamp_display():
    """Add timestamp display and event handler to HTML."""
    print(f"Reading {HTML_FILE}...")
    content = HTML_FILE.read_text(encoding="utf-8")

    # 1. Add timestamp display div after the update button
    button_pattern = r'(<button id="update-graph"[^>]*>.*?</button>)'

    if not re.search(button_pattern, content, re.DOTALL):
        print("ERROR: Could not find update-graph button")
        return False

    # Check if timestamp div already exists
    if 'id="last-updated"' in content:
        print("Timestamp display already exists, updating...")
    else:
        # Add timestamp display after button
        timestamp_html = '\n<div id="last-updated" style="font-size:11px;color:#94a3b8;margin-top:5px;font-style:italic;">Loading...</div>\n'
        content = re.sub(
            button_pattern,
            r'\1' + timestamp_html,
            content,
            flags=re.DOTALL
        )
        print("Added timestamp display div")

    # 2. Add JavaScript to display timestamp and handle button click
    # Find the last </script> tag
    last_script_pos = content.rfind('</script>')

    if last_script_pos == -1:
        print("ERROR: Could not find </script> tag")
        return False

    # Check if our script already exists
    if 'function updateTimestamp()' in content:
        print("Timestamp script already exists, skipping...")
    else:
        # Add our script before the last </script>
        timestamp_script = '''
// Display last updated timestamp
function updateTimestamp() {
  const timestampEl = document.getElementById('last-updated');
  if (graphData && graphData.metadata && graphData.metadata.generated_at) {
    const timestamp = new Date(graphData.metadata.generated_at);
    const formatted = timestamp.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
    timestampEl.textContent = `Last updated: ${formatted}`;
  } else {
    timestampEl.textContent = 'Last updated: Unknown';
  }
}

// Handle update button click
document.getElementById('update-graph').addEventListener('click', function() {
  alert(
    'To update the dependency graph, run this command in your terminal:\\n\\n' +
    'python scripts/update_dependency_graph_full.py\\n\\n' +
    'This will regenerate the graph from the current codebase and refresh this page automatically.'
  );
});

// Initialize timestamp on load
updateTimestamp();
'''
        content = content[:last_script_pos] + timestamp_script + content[last_script_pos:]
        print("Added timestamp and button event handler JavaScript")

    # Write back
    print(f"Writing updated HTML to {HTML_FILE}...")
    HTML_FILE.write_text(content, encoding="utf-8")
    print("[OK] Successfully updated HTML file")
    return True


if __name__ == "__main__":
    success = add_timestamp_display()
    exit(0 if success else 1)
