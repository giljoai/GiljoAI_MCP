#!/usr/bin/env python3
"""
Script to fix MCPAgentJob usage in test files after import migration.

This script:
1. Replaces MCPAgentJob( instantiations with AgentExecution(
2. Maps old field names to new field names
3. Updates type hints
4. Fixes isinstance checks
5. Skips migration test files (0367*)
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

# Field mappings for AgentExecution model
FIELD_MAPPINGS = {
    # Direct mappings (field name changes)
    'job_id=': 'job_id=',  # Keep same (foreign key)
    'tenant_key=': 'tenant_key=',  # Keep same
    'agent_type=': 'agent_type=',  # Keep same on AgentExecution
    'agent_name=': 'agent_name=',  # Keep same
    'mission=': 'mission=',  # Keep same (though primarily on AgentJob)
    'status=': 'status=',  # Keep same
    'project_id=': 'project_id=',  # Keep same
    'spawned_by=': 'spawned_by=',  # Keep same
    'agent_id=': 'agent_id=',  # Keep same
}


def should_skip_file(file_path: Path) -> bool:
    """Check if file should be skipped (migration tests)."""
    return '0367' in file_path.name


def fix_instantiations(content: str) -> Tuple[str, int]:
    """Replace MCPAgentJob( with AgentExecution( and count changes."""
    count = 0

    # Replace MCPAgentJob( with AgentExecution(
    pattern = r'\bMCPAgentJob\('
    matches = re.findall(pattern, content)
    count += len(matches)
    content = re.sub(pattern, 'AgentExecution(', content)

    return content, count


def fix_type_hints(content: str) -> Tuple[str, int]:
    """Fix type hints from MCPAgentJob to AgentExecution."""
    count = 0

    # Pattern: -> MCPAgentJob or : MCPAgentJob or [MCPAgentJob] or Optional[MCPAgentJob]
    patterns = [
        (r':\s*MCPAgentJob\b', ': AgentExecution'),
        (r'->\s*MCPAgentJob\b', '-> AgentExecution'),
        (r'\[MCPAgentJob\]', '[AgentExecution]'),
        (r'List\[MCPAgentJob\]', 'List[AgentExecution]'),
        (r'Optional\[MCPAgentJob\]', 'Optional[AgentExecution]'),
    ]

    for pattern, replacement in patterns:
        matches = re.findall(pattern, content)
        count += len(matches)
        content = re.sub(pattern, replacement, content)

    return content, count


def fix_isinstance_checks(content: str) -> Tuple[str, int]:
    """Fix isinstance checks."""
    count = 0

    pattern = r'isinstance\([^,]+,\s*MCPAgentJob\)'
    matches = re.findall(pattern, content)
    count += len(matches)
    content = re.sub(r'isinstance\(([^,]+),\s*MCPAgentJob\)', r'isinstance(\1, AgentExecution)', content)

    return content, count


def fix_assert_type_checks(content: str) -> Tuple[str, int]:
    """Fix assert isinstance checks."""
    count = 0

    pattern = r'assert\s+isinstance\([^,]+,\s*MCPAgentJob\)'
    matches = re.findall(pattern, content)
    count += len(matches)
    content = re.sub(r'assert\s+isinstance\(([^,]+),\s*MCPAgentJob\)', r'assert isinstance(\1, AgentExecution)', content)

    return content, count


def fix_sqlalchemy_selects(content: str) -> Tuple[str, int]:
    """Fix SQLAlchemy select() statements."""
    count = 0

    # Pattern: select(MCPAgentJob)
    pattern = r'select\(MCPAgentJob\)'
    matches = re.findall(pattern, content)
    count += len(matches)
    content = re.sub(pattern, 'select(AgentExecution)', content)

    # Pattern: query(MCPAgentJob) - old SQLAlchemy 1.x syntax
    pattern = r'query\(MCPAgentJob\)'
    matches = re.findall(pattern, content)
    count += len(matches)
    content = re.sub(pattern, 'query(AgentExecution)', content)

    # Pattern: MCPAgentJob.field in where/filter clauses
    pattern = r'\bMCPAgentJob\.'
    matches = re.findall(pattern, content)
    count += len(matches)
    content = re.sub(r'\bMCPAgentJob\.', 'AgentExecution.', content)

    return content, count


def fix_other_references(content: str) -> Tuple[str, int]:
    """Fix other references like Mock spec, db_session.get, etc."""
    count = 0

    # Pattern: Mock(spec=MCPAgentJob)
    pattern = r'Mock\(spec=MCPAgentJob\)'
    matches = re.findall(pattern, content)
    count += len(matches)
    content = re.sub(pattern, 'Mock(spec=AgentExecution)', content)

    # Pattern: db_session.get(MCPAgentJob, ...)
    pattern = r'\.get\(MCPAgentJob,'
    matches = re.findall(pattern, content)
    count += len(matches)
    content = re.sub(r'\.get\(MCPAgentJob,', '.get(AgentExecution,', content)

    # Pattern: filter_by in chain after MCPAgentJob
    # This is already handled by query() fix above

    return content, count


def fix_inline_imports(content: str) -> Tuple[str, int]:
    """Fix inline imports in function bodies."""
    count = 0

    # Pattern: from giljo_mcp.models import ..., MCPAgentJob, ...
    # Handle various import patterns

    # Case 1: MCPAgentJob at end of import list
    pattern = r'(from giljo_mcp\.models(?:\.agents)? import [^,\n]+,\s*)MCPAgentJob'
    matches = re.findall(pattern, content)
    count += len(matches)
    content = re.sub(pattern, r'\1AgentExecution', content)

    # Case 2: MCPAgentJob in middle of import list
    pattern = r'MCPAgentJob,\s*([A-Z])'
    matches = re.findall(pattern, content)
    count += len(matches)
    content = re.sub(pattern, r'AgentExecution, \1', content)

    # Case 3: Standalone import
    pattern = r'from giljo_mcp\.models(?:\.agents)? import MCPAgentJob\b'
    matches = re.findall(pattern, content)
    count += len(matches)
    content = re.sub(
        r'from giljo_mcp\.models(?:\.agents)? import MCPAgentJob\b',
        'from giljo_mcp.models.agents import AgentExecution',
        content
    )

    return content, count


def fix_model_class_params(content: str) -> Tuple[str, int]:
    """Fix model class parameters (e.g., in test isolation calls)."""
    count = 0

    # Pattern: function(session, MCPAgentJob, ...)
    # Look for MCPAgentJob as a parameter (not string, not in comment)
    pattern = r'\(\s*session,\s*MCPAgentJob,'
    matches = re.findall(pattern, content)
    count += len(matches)
    content = re.sub(r'\(\s*session,\s*MCPAgentJob,', '(session, AgentExecution,', content)

    # Pattern: [MCPAgentJob, OtherModel] in lists
    pattern = r'\bMCPAgentJob,\s*[A-Z]\w+'
    # Only if not in a comment or string
    for line in content.split('\n'):
        if re.search(pattern, line) and not line.strip().startswith('#'):
            count += 1

    # Don't replace here - too risky, handled case-by-case above

    return content, count


def process_file(file_path: Path) -> Tuple[bool, int]:
    """Process a single file and return (changed, total_replacements)."""
    if should_skip_file(file_path):
        return False, 0

    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        total_changes = 0

        # Apply all fixes
        content, count = fix_instantiations(content)
        total_changes += count

        content, count = fix_type_hints(content)
        total_changes += count

        content, count = fix_isinstance_checks(content)
        total_changes += count

        content, count = fix_assert_type_checks(content)
        total_changes += count

        content, count = fix_sqlalchemy_selects(content)
        total_changes += count

        content, count = fix_other_references(content)
        total_changes += count

        content, count = fix_inline_imports(content)
        total_changes += count

        content, count = fix_model_class_params(content)
        total_changes += count

        # Only write if changed
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            return True, total_changes

        return False, 0

    except Exception as e:
        print(f"Error processing {file_path}: {e}", file=sys.stderr)
        return False, 0


def main():
    """Main entry point."""
    tests_dir = Path('tests')

    if not tests_dir.exists():
        print("Error: tests/ directory not found", file=sys.stderr)
        sys.exit(1)

    # Find all Python files
    py_files = list(tests_dir.rglob('*.py'))

    # Filter out __pycache__
    py_files = [f for f in py_files if '__pycache__' not in str(f)]

    print(f"Found {len(py_files)} Python files in tests/")

    files_changed = 0
    total_replacements = 0
    skipped_files = 0

    for file_path in py_files:
        if should_skip_file(file_path):
            skipped_files += 1
            continue

        changed, count = process_file(file_path)
        if changed:
            files_changed += 1
            total_replacements += count
            print(f"[OK] {file_path.relative_to(tests_dir)}: {count} changes")

    print(f"\nSummary:")
    print(f"  Files processed: {len(py_files) - skipped_files}")
    print(f"  Files skipped (0367*): {skipped_files}")
    print(f"  Files changed: {files_changed}")
    print(f"  Total replacements: {total_replacements}")


if __name__ == '__main__':
    main()
