"""
TDD validation tests for Handover 0367d: MCPAgentJob Cleanup Verification

These tests validate that:
1. Zero MCPAgentJob references exist in production code
2. All production code uses AgentJob + AgentExecution exclusively

RED → GREEN → REFACTOR
- All tests should PASS (MCPAgentJob completely removed)

Test Organization:
- TestMCPAgentJobRemovalValidation: Verify no imports in production code
- TestProductionCodeReferenceCount: Verify zero code references
- TestTableReferenceValidation: Verify no mcp_agent_jobs table queries
"""
import ast
import os
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestMCPAgentJobRemovalValidation:
    """Verify MCPAgentJob is removed from production code"""

    def test_no_mcpagentjob_imports_in_services(self):
        """Services should not import MCPAgentJob"""
        services_dir = PROJECT_ROOT / "src" / "giljo_mcp" / "services"
        violations = []

        for py_file in services_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            if "MCPAgentJob" in content:
                # Check if it's an actual import, not just a comment
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.Import, ast.ImportFrom)):
                            import_str = ast.unparse(node)
                            if "MCPAgentJob" in import_str:
                                violations.append(f"{py_file.relative_to(PROJECT_ROOT)}")
                except SyntaxError:
                    # Skip files with syntax errors
                    pass

        assert not violations, f"MCPAgentJob imports found in services: {violations}"

    def test_no_mcpagentjob_imports_in_api(self):
        """API endpoints should not import MCPAgentJob"""
        api_dir = PROJECT_ROOT / "api" / "endpoints"
        violations = []

        for py_file in api_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            if "MCPAgentJob" in content:
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.Import, ast.ImportFrom)):
                            import_str = ast.unparse(node)
                            if "MCPAgentJob" in import_str:
                                violations.append(f"{py_file.relative_to(PROJECT_ROOT)}")
                except SyntaxError:
                    pass

        assert not violations, f"MCPAgentJob imports found in API: {violations}"

    def test_no_mcpagentjob_imports_in_tools(self):
        """Tools should not import MCPAgentJob"""
        tools_dir = PROJECT_ROOT / "src" / "giljo_mcp" / "tools"
        violations = []

        for py_file in tools_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            if "MCPAgentJob" in content:
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.Import, ast.ImportFrom)):
                            import_str = ast.unparse(node)
                            if "MCPAgentJob" in import_str:
                                violations.append(f"{py_file.relative_to(PROJECT_ROOT)}")
                except SyntaxError:
                    pass

        assert not violations, f"MCPAgentJob imports found in tools: {violations}"

    def test_no_mcpagentjob_imports_in_monitoring(self):
        """Monitoring should not import MCPAgentJob"""
        monitoring_dir = PROJECT_ROOT / "src" / "giljo_mcp" / "monitoring"
        violations = []

        for py_file in monitoring_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            if "MCPAgentJob" in content:
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.Import, ast.ImportFrom)):
                            import_str = ast.unparse(node)
                            if "MCPAgentJob" in import_str:
                                violations.append(f"{py_file.relative_to(PROJECT_ROOT)}")
                except SyntaxError:
                    pass

        assert not violations, f"MCPAgentJob imports found in monitoring: {violations}"

    def test_no_mcpagentjob_imports_in_orchestrator(self):
        """Orchestrator files should not import MCPAgentJob"""
        src_dir = PROJECT_ROOT / "src" / "giljo_mcp"
        orchestrator_files = [
            src_dir / "orchestrator.py",
            src_dir / "orchestrator_succession.py",
            src_dir / "staging_rollback.py",
            src_dir / "thin_prompt_generator.py",
        ]
        violations = []

        for py_file in orchestrator_files:
            if py_file.exists():
                content = py_file.read_text(encoding="utf-8")
                if "MCPAgentJob" in content:
                    try:
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if isinstance(node, (ast.Import, ast.ImportFrom)):
                                import_str = ast.unparse(node)
                                if "MCPAgentJob" in import_str:
                                    violations.append(f"{py_file.relative_to(PROJECT_ROOT)}")
                    except SyntaxError:
                        pass

        assert not violations, f"MCPAgentJob imports found in orchestrator: {violations}"


class TestProductionCodeReferenceCount:
    """Verify MCPAgentJob reference counts in production code"""

    def test_zero_mcpagentjob_code_references_in_services(self):
        """Count MCPAgentJob code references in services (should be 0)"""
        services_dir = PROJECT_ROOT / "src" / "giljo_mcp" / "services"
        code_refs = 0
        violations = []

        for py_file in services_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            try:
                tree = ast.parse(content)
                file_refs = 0
                for node in ast.walk(tree):
                    # Check for MCPAgentJob as a name reference (not in comments)
                    if isinstance(node, ast.Name) and node.id == "MCPAgentJob":
                        code_refs += 1
                        file_refs += 1
                    # Check for attribute access like models.MCPAgentJob
                    if isinstance(node, ast.Attribute) and node.attr == "MCPAgentJob":
                        code_refs += 1
                        file_refs += 1
                if file_refs > 0:
                    violations.append(f"{py_file.relative_to(PROJECT_ROOT)} ({file_refs} refs)")
            except SyntaxError:
                pass

        assert code_refs == 0, f"Found {code_refs} MCPAgentJob code references in services: {violations}"

    def test_zero_mcpagentjob_code_references_in_api(self):
        """Count MCPAgentJob code references in API (should be 0)"""
        api_dir = PROJECT_ROOT / "api" / "endpoints"
        code_refs = 0
        violations = []

        for py_file in api_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            try:
                tree = ast.parse(content)
                file_refs = 0
                for node in ast.walk(tree):
                    if isinstance(node, ast.Name) and node.id == "MCPAgentJob":
                        code_refs += 1
                        file_refs += 1
                    if isinstance(node, ast.Attribute) and node.attr == "MCPAgentJob":
                        code_refs += 1
                        file_refs += 1
                if file_refs > 0:
                    violations.append(f"{py_file.relative_to(PROJECT_ROOT)} ({file_refs} refs)")
            except SyntaxError:
                pass

        assert code_refs == 0, f"Found {code_refs} MCPAgentJob code references in API: {violations}"

    def test_zero_mcpagentjob_code_references_in_tools(self):
        """Count MCPAgentJob code references in tools (should be 0)"""
        tools_dir = PROJECT_ROOT / "src" / "giljo_mcp" / "tools"
        code_refs = 0
        violations = []

        for py_file in tools_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            try:
                tree = ast.parse(content)
                file_refs = 0
                for node in ast.walk(tree):
                    if isinstance(node, ast.Name) and node.id == "MCPAgentJob":
                        code_refs += 1
                        file_refs += 1
                    if isinstance(node, ast.Attribute) and node.attr == "MCPAgentJob":
                        code_refs += 1
                        file_refs += 1
                if file_refs > 0:
                    violations.append(f"{py_file.relative_to(PROJECT_ROOT)} ({file_refs} refs)")
            except SyntaxError:
                pass

        assert code_refs == 0, f"Found {code_refs} MCPAgentJob code references in tools: {violations}"

    def test_zero_mcpagentjob_code_references_in_monitoring(self):
        """Count MCPAgentJob code references in monitoring (should be 0)"""
        monitoring_dir = PROJECT_ROOT / "src" / "giljo_mcp" / "monitoring"
        code_refs = 0
        violations = []

        for py_file in monitoring_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            try:
                tree = ast.parse(content)
                file_refs = 0
                for node in ast.walk(tree):
                    if isinstance(node, ast.Name) and node.id == "MCPAgentJob":
                        code_refs += 1
                        file_refs += 1
                    if isinstance(node, ast.Attribute) and node.attr == "MCPAgentJob":
                        code_refs += 1
                        file_refs += 1
                if file_refs > 0:
                    violations.append(f"{py_file.relative_to(PROJECT_ROOT)} ({file_refs} refs)")
            except SyntaxError:
                pass

        assert code_refs == 0, f"Found {code_refs} MCPAgentJob code references in monitoring: {violations}"

    def test_zero_mcpagentjob_code_references_in_orchestrator(self):
        """Count MCPAgentJob code references in orchestrator files (should be 0)"""
        src_dir = PROJECT_ROOT / "src" / "giljo_mcp"
        orchestrator_files = [
            src_dir / "orchestrator.py",
            src_dir / "orchestrator_succession.py",
            src_dir / "staging_rollback.py",
            src_dir / "thin_prompt_generator.py",
        ]
        code_refs = 0
        violations = []

        for py_file in orchestrator_files:
            if py_file.exists():
                content = py_file.read_text(encoding="utf-8")
                try:
                    tree = ast.parse(content)
                    file_refs = 0
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Name) and node.id == "MCPAgentJob":
                            code_refs += 1
                            file_refs += 1
                        if isinstance(node, ast.Attribute) and node.attr == "MCPAgentJob":
                            code_refs += 1
                            file_refs += 1
                    if file_refs > 0:
                        violations.append(f"{py_file.relative_to(PROJECT_ROOT)} ({file_refs} refs)")
                except SyntaxError:
                    pass

        assert code_refs == 0, f"Found {code_refs} MCPAgentJob code references in orchestrator: {violations}"


class TestTableReferenceValidation:
    """Verify no mcp_agent_jobs table queries in production code"""

    def test_no_mcp_agent_jobs_table_queries_in_services(self):
        """Services should not query mcp_agent_jobs table"""
        services_dir = PROJECT_ROOT / "src" / "giljo_mcp" / "services"
        violations = []

        for py_file in services_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            # Check for table name references
            if "mcp_agent_jobs" in content:
                # Verify it's not in a comment
                lines = content.split("\n")
                for line_num, line in enumerate(lines, 1):
                    if "mcp_agent_jobs" in line and not line.strip().startswith("#"):
                        violations.append(f"{py_file.relative_to(PROJECT_ROOT)}:{line_num}")

        assert not violations, f"mcp_agent_jobs table references found in services: {violations}"

    def test_no_mcp_agent_jobs_table_queries_in_api(self):
        """API endpoints should not query mcp_agent_jobs table"""
        api_dir = PROJECT_ROOT / "api" / "endpoints"
        violations = []

        for py_file in api_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            if "mcp_agent_jobs" in content:
                lines = content.split("\n")
                for line_num, line in enumerate(lines, 1):
                    if "mcp_agent_jobs" in line and not line.strip().startswith("#"):
                        violations.append(f"{py_file.relative_to(PROJECT_ROOT)}:{line_num}")

        assert not violations, f"mcp_agent_jobs table references found in API: {violations}"

    def test_no_mcp_agent_jobs_table_queries_in_tools(self):
        """Tools should not query mcp_agent_jobs table"""
        tools_dir = PROJECT_ROOT / "src" / "giljo_mcp" / "tools"
        violations = []

        for py_file in tools_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            if "mcp_agent_jobs" in content:
                lines = content.split("\n")
                for line_num, line in enumerate(lines, 1):
                    if "mcp_agent_jobs" in line and not line.strip().startswith("#"):
                        violations.append(f"{py_file.relative_to(PROJECT_ROOT)}:{line_num}")

        assert not violations, f"mcp_agent_jobs table references found in tools: {violations}"
