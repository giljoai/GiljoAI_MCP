#!/usr/bin/env python3
"""
Simple Refactoring Bot Example
Demonstrates orchestrating multiple agents to refactor legacy code
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# GiljoAI MCP imports
from giljo_mcp.database import DatabaseManager
from giljo_mcp.orchestrator import ProjectOrchestrator
from giljo_mcp.models import Project, Agent, Message
from giljo_mcp.template_manager import TemplateManager
from giljo_mcp.config_manager import get_config


class RefactoringBot:
    """Orchestrates code refactoring using multiple specialized agents"""

    def __init__(self, project_path: Path, tenant_key: str = "refactor-bot-demo"):
        """
        Initialize the refactoring bot

        Args:
            project_path: Path to the codebase to refactor
            tenant_key: Unique identifier for this refactoring session
        """
        self.project_path = project_path
        self.tenant_key = tenant_key
        self.config = Config()
        self.db = DatabaseManager(self.config.database_url)
        self.orchestrator = None
        self.project = None
        self.agents = {}

    async def setup(self):
        """Initialize database and orchestrator"""
        await self.db.initialize()

        # Create orchestrator
        self.orchestrator = ProjectOrchestrator(
            db=self.db,
            tenant_key=self.tenant_key
        )

        # Create project
        self.project = await self.orchestrator.create_project(
            name=f"Refactor {self.project_path.name}",
            mission=self._get_mission()
        )

        print(f"✅ Project created: {self.project.id}")

    def _get_mission(self) -> str:
        """Generate the refactoring mission"""
        return f"""
        Refactor the codebase at {self.project_path} to improve code quality.

        OBJECTIVES:
        1. Identify code quality issues and anti-patterns
        2. Apply consistent naming conventions
        3. Add missing docstrings and type hints
        4. Split complex functions into smaller ones
        5. Modernize code to use latest Python features

        CONSTRAINTS:
        - Maintain backward compatibility
        - All tests must pass after refactoring
        - Performance must not degrade
        - Follow PEP 8 style guidelines

        TARGET: {self.project_path}
        """

    async def spawn_agents(self):
        """Create specialized refactoring agents"""

        # Get template manager
        tm = TemplateManager(
            session=self.db.session,
            tenant_key=self.tenant_key,
            product_id=self.project.id
        )

        # Define agent configurations
        agent_configs = [
            {
                "name": "analyzer",
                "template": "code_analyzer",
                "mission": await tm.get_template(
                    name="analyzer",
                    augmentations="Focus on Python code quality metrics",
                    variables={"target_path": str(self.project_path)}
                )
            },
            {
                "name": "linter",
                "template": "style_checker",
                "mission": await tm.get_template(
                    name="linter",
                    augmentations="Use strict PEP 8 checking with Black and Ruff",
                    variables={"auto_fix": True}
                )
            },
            {
                "name": "refactor",
                "template": "code_transformer",
                "mission": await tm.get_template(
                    name="refactor",
                    augmentations="Apply safe transformations only",
                    variables={"preserve_api": True}
                )
            },
            {
                "name": "validator",
                "template": "test_runner",
                "mission": await tm.get_template(
                    name="validator",
                    augmentations="Run full test suite and performance benchmarks",
                    variables={"fail_fast": False}
                )
            }
        ]

        # Spawn agents
        for config in agent_configs:
            agent = await self.orchestrator.spawn_agent(
                name=config["name"],
                mission=config["mission"],
                project_id=self.project.id
            )
            self.agents[config["name"]] = agent
            print(f"🤖 Spawned {config['name']} agent")

    async def execute_workflow(self):
        """Execute the refactoring workflow"""

        print("\n🚀 Starting refactoring workflow...\n")

        # Phase 1: Analysis
        print("📊 Phase 1: Analyzing codebase...")
        await self._analyze_phase()

        # Phase 2: Linting
        print("🔍 Phase 2: Checking style violations...")
        await self._lint_phase()

        # Phase 3: Refactoring
        print("🔧 Phase 3: Applying refactoring transformations...")
        await self._refactor_phase()

        # Phase 4: Validation
        print("✓ Phase 4: Validating changes...")
        await self._validate_phase()

        # Phase 5: Report
        print("📋 Phase 5: Generating report...")
        await self._report_phase()

    async def _analyze_phase(self):
        """Run code analysis"""
        # Send task to analyzer
        await self.orchestrator.send_message(
            from_agent="orchestrator",
            to_agent="analyzer",
            content={
                "task": "analyze_codebase",
                "path": str(self.project_path),
                "metrics": ["complexity", "coverage", "duplication", "maintainability"]
            }
        )

        # Wait for analysis results
        results = await self._wait_for_response("analyzer", timeout=60)

        # Store analysis for other agents
        await self._broadcast_to_agents({
            "analysis_results": results,
            "issues_found": results.get("issues", []),
            "priority_files": results.get("priority_files", [])
        })

    async def _lint_phase(self):
        """Run style checking"""
        await self.orchestrator.send_message(
            from_agent="orchestrator",
            to_agent="linter",
            content={
                "task": "check_style",
                "auto_fix": True,
                "tools": ["black", "ruff", "mypy"]
            }
        )

        lint_results = await self._wait_for_response("linter", timeout=30)

        print(f"  - Style violations: {lint_results.get('violations', 0)}")
        print(f"  - Auto-fixed: {lint_results.get('fixed', 0)}")

    async def _refactor_phase(self):
        """Apply refactoring transformations"""
        # Get priority files from analysis
        analysis = await self._get_agent_context("analyzer")
        priority_files = analysis.get("priority_files", [])

        for file_path in priority_files:
            await self.orchestrator.send_message(
                from_agent="orchestrator",
                to_agent="refactor",
                content={
                    "task": "refactor_file",
                    "file": file_path,
                    "transformations": [
                        "split_complex_functions",
                        "add_type_hints",
                        "modernize_syntax",
                        "extract_constants"
                    ]
                }
            )

            result = await self._wait_for_response("refactor", timeout=20)
            print(f"  - Refactored: {file_path}")

    async def _validate_phase(self):
        """Validate all changes"""
        await self.orchestrator.send_message(
            from_agent="orchestrator",
            to_agent="validator",
            content={
                "task": "run_validation",
                "tests": ["unit", "integration", "performance"],
                "compare_baseline": True
            }
        )

        validation = await self._wait_for_response("validator", timeout=120)

        if validation.get("tests_passed"):
            print("  ✅ All tests passed!")
        else:
            print("  ⚠️ Some tests failed - review needed")

        return validation

    async def _report_phase(self):
        """Generate final report"""
        # Collect results from all agents
        results = {}
        for agent_name in self.agents:
            context = await self._get_agent_context(agent_name)
            results[agent_name] = context

        # Generate report
        report = self._generate_report(results)

        # Save report
        report_path = self.project_path / "refactoring_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n📄 Report saved to: {report_path}")

        # Print summary
        self._print_summary(report)

    def _generate_report(self, results: Dict) -> Dict:
        """Generate comprehensive refactoring report"""
        return {
            "project": str(self.project_path),
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "files_analyzed": len(results.get("analyzer", {}).get("files", [])),
                "issues_found": results.get("analyzer", {}).get("issues_count", 0),
                "violations_fixed": results.get("linter", {}).get("fixed", 0),
                "refactorings_applied": results.get("refactor", {}).get("count", 0),
                "tests_passed": results.get("validator", {}).get("tests_passed", False)
            },
            "metrics": {
                "before": results.get("analyzer", {}).get("metrics_before", {}),
                "after": results.get("validator", {}).get("metrics_after", {})
            },
            "details": results
        }

    def _print_summary(self, report: Dict):
        """Print readable summary"""
        print("\n" + "="*60)
        print("REFACTORING COMPLETE")
        print("="*60)

        summary = report["summary"]
        print(f"Files Analyzed:        {summary['files_analyzed']}")
        print(f"Issues Found:          {summary['issues_found']}")
        print(f"Violations Fixed:      {summary['violations_fixed']}")
        print(f"Refactorings Applied:  {summary['refactorings_applied']}")
        print(f"Tests Status:          {'✅ PASSED' if summary['tests_passed'] else '❌ FAILED'}")

        # Show metrics improvement
        metrics = report["metrics"]
        if metrics.get("before") and metrics.get("after"):
            print("\nMetrics Improvement:")
            for metric, before in metrics["before"].items():
                after = metrics["after"].get(metric, before)
                change = ((after - before) / before * 100) if before else 0
                symbol = "📈" if change > 0 else "📉" if change < 0 else "➖"
                print(f"  {metric}: {before:.2f} → {after:.2f} ({symbol} {abs(change):.1f}%)")

    async def _wait_for_response(self, agent: str, timeout: int = 30) -> Dict:
        """Wait for agent response with timeout"""
        start = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start < timeout:
            messages = await self.orchestrator.get_messages(agent)
            if messages:
                # Get latest message
                latest = messages[0]
                # Acknowledge receipt
                await self.orchestrator.acknowledge_message(latest.id, agent)
                return json.loads(latest.content) if isinstance(latest.content, str) else latest.content

            await asyncio.sleep(1)

        raise TimeoutError(f"No response from {agent} within {timeout}s")

    async def _broadcast_to_agents(self, content: Dict):
        """Send message to all agents"""
        for agent_name in self.agents:
            if agent_name != "orchestrator":
                await self.orchestrator.send_message(
                    from_agent="orchestrator",
                    to_agent=agent_name,
                    content=content
                )

    async def _get_agent_context(self, agent: str) -> Dict:
        """Get agent's current context"""
        # This would query the agent's state/results
        # For demo, returning mock data
        return {
            "agent": agent,
            "status": "completed",
            "results": {}
        }

    async def cleanup(self):
        """Clean up resources"""
        if self.orchestrator:
            await self.orchestrator.close_project(self.project.id)
        if self.db:
            await self.db.close()


async def main():
    """Run the refactoring bot example"""

    # Target directory (use current dir for demo)
    target = Path("./sample_code")

    # Create sample code if doesn't exist
    if not target.exists():
        print("Creating sample code directory...")
        target.mkdir()

        # Create sample Python file with issues
        sample_file = target / "legacy_code.py"
        sample_file.write_text('''
# Legacy code with various issues

def calculate_total(items):
    """Missing type hints and uses old string formatting"""
    total = 0
    for i in range(len(items)):  # Should use enumerate
        total = total + items[i]['price'] * items[i]['quantity']

    # Old style formatting
    message = "Total: %s" % total
    print message  # Python 2 style print

    return total

class order_processor:  # Should be CamelCase
    def __init__(self):
        self.orders = []

    def process_order_with_validation_and_notification_and_logging(self, order):
        # Function too complex, should be split
        # Validate
        if not order:
            return False
        if not order.get('items'):
            return False
        if not order.get('customer'):
            return False

        # Calculate
        total = 0
        for item in order['items']:
            total += item['price'] * item['quantity']

        # Apply discount
        if total > 100:
            total = total * 0.9
        elif total > 50:
            total = total * 0.95

        # Process payment
        payment_result = self.charge_card(order['customer'], total)

        # Send notification
        if payment_result:
            self.send_email(order['customer'], "Order confirmed")
            self.send_sms(order['customer'], "Order confirmed")

        # Log
        print "Order processed"

        return payment_result
''')

    # Run refactoring bot
    bot = RefactoringBot(target)

    try:
        await bot.setup()
        await bot.spawn_agents()
        await bot.execute_workflow()
    finally:
        await bot.cleanup()


if __name__ == "__main__":
    asyncio.run(main())