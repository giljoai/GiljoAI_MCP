#!/usr/bin/env python3
"""Add sortable hub files table to dependency graph HTML."""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
JSON_FILE = PROJECT_ROOT / "docs" / "cleanup" / "dependency_graph.json"
HTML_FILE = PROJECT_ROOT / "docs" / "cleanup" / "dependency_graph.html"

def build_hub_table_html(hub_files):
    """Build HTML for the hub files table."""

    # Build table rows
    rows = []
    for f in hub_files:
        prod = f.get('production_dependents', 0)
        test = f.get('test_dependents', 0)
        total = f['dependents']
        prod_pct = (prod / total * 100) if total > 0 else 0

        # Visual ratio bar
        ratio_bar = f'<div class="ratio-bar"><div class="ratio-prod" style="width:{prod_pct}%"></div></div>'

        rows.append(f"""
    <tr data-prod="{prod}" data-test="{test}" data-total="{total}">
      <td>{f['path']}</td>
      <td><span class="layer-badge" style="background:{get_layer_color(f['layer'])}">{f['layer']}</span></td>
      <td class="number dep-total">{total}</td>
      <td class="number dep-prod">{prod}</td>
      <td class="number dep-test">{test}</td>
      <td class="ratio-cell">{ratio_bar}<span class="ratio-text">{prod_pct:.0f}% prod</span></td>
      <td class="number">{f['dependencies']}</td>
      <td><span class="risk-badge risk-{f['risk']}">{f['risk']}</span></td>
      <td class="number">{f['todos']}</td>
      <td class="number">{f['deprecations']}</td>
    </tr>""")

    rows_html = "".join(rows)

    return f"""
<!-- Hub Files Analysis Table -->
<div id="hub-files-section">
  <div id="hub-header" onclick="toggleHubTable()">
    <h2>Critical Hub Files (50+ Dependents) <span id="hub-toggle">▼</span></h2>
    <p class="subtitle">Files with high dependency counts that may need refactoring to reduce coupling</p>
  </div>

  <div id="hub-content">
    <table id="hub-table">
    <thead>
      <tr>
        <th onclick="sortTable(0)">File Path ▼</th>
        <th onclick="sortTable(1)">Layer ▼</th>
        <th onclick="sortTable(2)">Total Deps ▼</th>
        <th onclick="sortTable(3)">Production ▼</th>
        <th onclick="sortTable(4)">Test/Other ▼</th>
        <th onclick="sortTable(5)">Ratio ▼</th>
        <th onclick="sortTable(6)">Dependencies ▼</th>
        <th onclick="sortTable(7)">Risk ▼</th>
        <th onclick="sortTable(8)">TODOs ▼</th>
        <th onclick="sortTable(9)">Deprecations ▼</th>
      </tr>
    </thead>
    <tbody>
{rows_html}
    </tbody>
  </table>
  </div>
</div>

<style>
#hub-files-section {{
  position: absolute;
  bottom: 20px;
  left: 340px;
  right: 20px;
  background: #1e293b;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #334155;
  max-height: 450px;
  overflow: visible;
}}

#hub-header {{
  cursor: pointer;
  user-select: none;
  margin-bottom: 10px;
}}

#hub-header:hover {{
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
  margin: -5px -10px 5px -10px;
  padding: 5px 10px;
}}

#hub-files-section h2 {{
  color: #60a5fa;
  margin: 0 0 5px 0;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}}

#hub-toggle {{
  font-size: 14px;
  transition: transform 0.2s;
}}

#hub-files-section.collapsed #hub-toggle {{
  transform: rotate(-90deg);
}}

#hub-files-section .subtitle {{
  color: #94a3b8;
  font-size: 12px;
  margin: 0;
}}

#hub-content {{
  max-height: 350px;
  overflow-y: auto;
  transition: max-height 0.3s ease-out, opacity 0.3s ease-out;
}}

#hub-files-section.collapsed #hub-content {{
  max-height: 0;
  opacity: 0;
  overflow: hidden;
}}

#hub-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}}

#hub-table th {{
  background: #0f172a;
  color: #60a5fa;
  padding: 8px;
  text-align: left;
  cursor: pointer;
  position: sticky;
  top: 0;
  border-bottom: 2px solid #334155;
  user-select: none;
}}

#hub-table th:hover {{
  background: #1e293b;
  color: #93c5fd;
}}

#hub-table td {{
  padding: 6px 8px;
  border-bottom: 1px solid #334155;
  color: #e2e8f0;
}}

#hub-table tbody tr:hover {{
  background: #334155;
}}

#hub-table .number {{
  text-align: right;
  font-family: monospace;
}}

.layer-badge {{
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: #fff;
}}

.risk-badge {{
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}}

.risk-low {{ background: #22c55e; color: #fff; }}
.risk-medium {{ background: #eab308; color: #000; }}
.risk-high {{ background: #f97316; color: #fff; }}
.risk-critical {{ background: #dc2626; color: #fff; }}

.ratio-cell {{
  min-width: 120px;
}}

.ratio-bar {{
  width: 60px;
  height: 12px;
  background: #0f172a;
  border-radius: 3px;
  overflow: hidden;
  display: inline-block;
  margin-right: 8px;
  vertical-align: middle;
  border: 1px solid #334155;
}}

.ratio-prod {{
  height: 100%;
  background: linear-gradient(90deg, #22c55e, #16a34a);
  transition: width 0.3s;
}}

.ratio-text {{
  font-size: 11px;
  color: #94a3b8;
  vertical-align: middle;
}}

#hub-table tr[data-prod="0"] .dep-prod {{
  color: #ef4444;
  font-weight: 600;
}}

#hub-table tr[data-test] {{
  opacity: 1;
  transition: opacity 0.2s;
}}

#hub-table.hide-tests tr[data-test] .dep-total {{
  opacity: 0.5;
}}

#hub-table.hide-tests tr[data-test] .dep-total::after {{
  content: ' → ';
  opacity: 0.5;
}}
</style>

<script>
let sortDirection = {{}};
let testFilterEnabled = true;

function toggleHubTable() {{
  const section = document.getElementById('hub-files-section');
  section.classList.toggle('collapsed');
}}

// Listen for test filter changes
function setupFilterListener() {{
  const testCheckbox = document.querySelector('#risk-filters input[data-risk="test"]');
  if (!testCheckbox) {{
    // Try layer filters
    const layerCheckbox = document.querySelector('#layer-filters input[data-layer="test"]');
    if (layerCheckbox) {{
      layerCheckbox.addEventListener('change', function() {{
        updateHubTableForTestFilter(this.checked);
      }});
    }}
  }}
}}

function updateHubTableForTestFilter(includeTests) {{
  testFilterEnabled = includeTests;
  const table = document.getElementById('hub-table');
  const rows = table.querySelectorAll('tbody tr');

  rows.forEach(row => {{
    const prod = parseInt(row.dataset.prod);
    const test = parseInt(row.dataset.test);
    const total = parseInt(row.dataset.total);

    if (includeTests) {{
      // Show total counts
      row.querySelector('.dep-total').textContent = total;
    }} else {{
      // Show only production counts
      row.querySelector('.dep-total').textContent = prod;
    }}
  }});

  // Toggle visual indicator
  if (includeTests) {{
    table.classList.remove('hide-tests');
  }} else {{
    table.classList.add('hide-tests');
  }}
}}

// Initialize on load
setTimeout(setupFilterListener, 500);

function sortTable(columnIndex) {{
  const table = document.getElementById('hub-table');
  const tbody = table.querySelector('tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));

  // Toggle sort direction
  if (sortDirection[columnIndex] === undefined) {{
    sortDirection[columnIndex] = 1; // ascending
  }} else {{
    sortDirection[columnIndex] *= -1;
  }}

  const direction = sortDirection[columnIndex];

  rows.sort((a, b) => {{
    let aValue = a.cells[columnIndex].textContent.trim();
    let bValue = b.cells[columnIndex].textContent.trim();

    // Special handling for ratio column (index 5)
    if (columnIndex === 5) {{
      aValue = parseFloat(aValue.replace('% prod', '')) || 0;
      bValue = parseFloat(bValue.replace('% prod', '')) || 0;
      return direction * (aValue - bValue);
    }}

    // Convert to numbers if it's a number column (Total, Prod, Test, Dependencies, TODOs, Deprecations)
    if ([2, 3, 4, 6, 8, 9].includes(columnIndex)) {{
      aValue = parseInt(aValue) || 0;
      bValue = parseInt(bValue) || 0;
      return direction * (aValue - bValue);
    }}

    // String comparison (Path, Layer, Risk)
    return direction * aValue.localeCompare(bValue);
  }});

  // Re-append sorted rows
  rows.forEach(row => tbody.appendChild(row));

  // Update header indicators
  const headers = table.querySelectorAll('th');
  headers.forEach((th, idx) => {{
    const text = th.textContent.replace(' ▼', '').replace(' ▲', '');
    if (idx === columnIndex) {{
      th.textContent = text + (direction === 1 ? ' ▲' : ' ▼');
    }} else {{
      th.textContent = text + ' ▼';
    }}
  }});
}}
</script>
"""

def get_layer_color(layer):
    """Get color for layer badge."""
    colors = {
        'model': '#3b82f6',
        'service': '#22c55e',
        'api': '#eab308',
        'frontend': '#a855f7',
        'test': '#6b7280',
        'config': '#f97316',
        'docs': '#06b6d4'
    }
    return colors.get(layer, '#6b7280')

def main():
    # Read JSON data
    print(f"Reading JSON from {JSON_FILE}...")
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        graph_data = json.load(f)

    # Find hub files (50+ dependents)
    hub_files = []
    for node in graph_data['nodes']:
        dependent_count = len(node['dependents'])
        if dependent_count >= 50:
            hub_files.append({
                'path': node['path'],
                'name': node['name'],
                'layer': node['layer'],
                'dependents': dependent_count,
                'dependencies': len(node['dependencies']),
                'risk': node['risk'],
                'todos': node.get('todos', 0),
                'deprecations': node.get('deprecations', 0),
                'production_dependents': node.get('production_dependents', 0),
                'test_dependents': node.get('test_dependents', 0)
            })

    # Sort by dependents descending
    hub_files.sort(key=lambda x: x['dependents'], reverse=True)

    print(f"Found {len(hub_files)} hub files with 50+ dependents")

    if not hub_files:
        print("No hub files found. Nothing to add.")
        return 0

    # Read HTML file
    print(f"Reading HTML from {HTML_FILE}...")
    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Check if table already exists
    if 'id="hub-files-section"' in html_content:
        print("Hub files table already exists. Removing old version...")
        # Remove old table section
        start_marker = '<!-- Hub Files Analysis Table -->'
        end_marker = '</script>\n</body>'

        start_idx = html_content.find(start_marker)
        end_idx = html_content.find(end_marker, start_idx)

        if start_idx != -1 and end_idx != -1:
            html_content = html_content[:start_idx] + html_content[end_idx:]

    # Build table HTML
    table_html = build_hub_table_html(hub_files)

    # Insert before closing </body> tag
    insertion_point = html_content.rfind('</body>')
    if insertion_point == -1:
        print("ERROR: Could not find </body> tag")
        return 1

    new_html = (
        html_content[:insertion_point] +
        table_html +
        html_content[insertion_point:]
    )

    # Write back
    print(f"Writing updated HTML to {HTML_FILE}...")
    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(new_html)

    print(f"[SUCCESS] Added hub files table with {len(hub_files)} entries")
    for i, f in enumerate(hub_files[:5], 1):
        print(f"  {i}. {f['path']} - {f['dependents']} dependents")

    return 0

if __name__ == "__main__":
    exit(main())
