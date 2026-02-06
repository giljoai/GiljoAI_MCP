#!/usr/bin/env python3
"""Analyze test linking before and after import resolution improvements."""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
JSON_FILE = PROJECT_ROOT / "docs" / "cleanup" / "dependency_graph.json"

with open(JSON_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Analyze test nodes
test_nodes = [n for n in data['nodes'] if n['layer'] == 'test']
total_tests = len(test_nodes)

# Count orphaned tests (zero dependencies = not importing anything)
orphaned_tests = [n for n in test_nodes if len(n['dependencies']) == 0]
linked_tests = [n for n in test_nodes if len(n['dependencies']) > 0]

print("=" * 70)
print("TEST LINKING ANALYSIS (After Import Resolution Enhancement)")
print("=" * 70)
print(f"\nTotal Test Files: {total_tests}")
print(f"Linked Tests: {len(linked_tests)} ({len(linked_tests)/total_tests*100:.1f}%)")
print(f"Orphaned Tests: {len(orphaned_tests)} ({len(orphaned_tests)/total_tests*100:.1f}%)")

# Show improvement
print(f"\n{'BEFORE (Summary):':<25} 332 orphaned (39.1%)")
print(f"{'AFTER (Current):':<25} {len(orphaned_tests)} orphaned ({len(orphaned_tests)/total_tests*100:.1f}%)")
print(f"{'IMPROVEMENT:':<25} {332 - len(orphaned_tests)} tests now linked!")

# Breakdown by file type
js_tests = [n for n in test_nodes if n['path'].endswith(('.spec.js', '.spec.ts'))]
py_tests = [n for n in test_nodes if n['path'].endswith('.py')]

js_linked = [n for n in js_tests if len(n['dependencies']) > 0]
py_linked = [n for n in py_tests if len(n['dependencies']) > 0]

print("\n" + "=" * 70)
print("BREAKDOWN BY FILE TYPE")
print("=" * 70)
print(f"\nJavaScript/TypeScript Tests (.spec.js/.spec.ts):")
print(f"  Total: {len(js_tests)}")
print(f"  Linked: {len(js_linked)} ({len(js_linked)/len(js_tests)*100:.1f}%)")
print(f"  Orphaned: {len(js_tests) - len(js_linked)}")

print(f"\nPython Tests (.py):")
print(f"  Total: {len(py_tests)}")
print(f"  Linked: {len(py_linked)} ({len(py_linked)/len(py_tests)*100:.1f}%)")
print(f"  Orphaned: {len(py_tests) - len(py_linked)}")

# Sample linked tests
print("\n" + "=" * 70)
print("SAMPLE SUCCESSFULLY LINKED TESTS")
print("=" * 70)

# Show some Vue tests that are now linked
vue_tests_linked = [n for n in js_tests if len(n['dependencies']) > 0][:5]
print("\nVue/JS Tests (now properly linked via @/ alias):")
for test in vue_tests_linked:
    deps = [data['nodes'][dep_id]['path'] for dep_id in test['dependencies'][:3]]
    print(f"  {test['path']}")
    print(f"    imports: {', '.join(deps[:2])}")

# Show example: UserSettings.spec.js
user_settings_test = next((n for n in test_nodes if 'UserSettings.spec.js' in n['path']), None)
if user_settings_test and len(user_settings_test['dependencies']) > 0:
    print(f"\n[SUCCESS] UserSettings.spec.js (user's example):")
    print(f"   Status: NOW LINKED!")
    deps = [data['nodes'][dep_id]['path'] for dep_id in user_settings_test['dependencies']]
    print(f"   Imports: {deps[0] if deps else 'none'}")

# Remaining orphaned tests
print("\n" + "=" * 70)
print("REMAINING ORPHANED TESTS (Likely Legitimate)")
print("=" * 70)
print("\nThese are likely:")
print("- Utility/fixture files with no imports (expected)")
print("- Integration tests with dynamic imports")
print("- Config files for test runners")

orphaned_sample = orphaned_tests[:10]
print(f"\nSample of {len(orphaned_sample)} remaining orphaned tests:")
for test in orphaned_sample:
    print(f"  {test['path']}")

print("\n" + "=" * 70)
print(f"CONCLUSION: Import resolution fix linked {332 - len(orphaned_tests)} additional tests!")
print("=" * 70)
