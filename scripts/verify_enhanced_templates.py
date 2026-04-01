"""
Verification script for Phase 7: Enhanced Agent Templates

This script verifies that all agent templates have been properly enhanced
with MCP coordination instructions.

Usage:
    python scripts/verify_enhanced_templates.py [tenant_key]

If tenant_key is not provided, uses "default" tenant.
"""

import asyncio
import sys
from pathlib import Path


# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select

from src.giljo_mcp.database import get_db_manager
from src.giljo_mcp.models import AgentTemplate


async def verify_templates(tenant_key: str = "default"):
    """
    Verify that all templates have MCP enhancements.

    Args:
        tenant_key: Tenant key to verify templates for

    Returns:
        dict: Verification results
    """
    print(f"\n{'=' * 80}")
    print(f"ENHANCED TEMPLATE VERIFICATION - Tenant: {tenant_key}")
    print(f"{'=' * 80}\n")

    db_manager = get_db_manager()
    async with db_manager.get_session_async() as session:
        # Get all templates for tenant
        result = await session.execute(
            select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key).order_by(AgentTemplate.role)
        )
        templates = result.scalars().all()

        if not templates:
            print(f"❌ ERROR: No templates found for tenant '{tenant_key}'")
            print("\nTo seed templates, run:")
            print(
                f"  python -c \"from src.giljo_mcp.template_seeder import seed_tenant_templates; import asyncio; from src.giljo_mcp.database import get_db_manager; asyncio.run(get_db_manager().run_async(lambda s: seed_tenant_templates(s, '{tenant_key}')))\"\n"
            )
            return {"status": "error", "message": "No templates found"}

        print(f"Found {len(templates)} templates\n")

        # Verification checks
        mcp_checks = {
            "behavioral_rules": [
                "MCP tools",
                "report progress",
                "set_agent_status",
            ],
            "success_criteria": [
                "MCP checkpoint",
                "progress",
            ],
            "template_content": [
                "MCP COMMUNICATION PROTOCOL",
                "Phase 1: Job Acknowledgment",
                "Phase 2: Incremental Progress",
                "Phase 3: Completion",
                "Error Handling",
                "get_pending_jobs",
                "report_progress",
                "complete_job",
                "set_agent_status",
            ],
        }

        results = {}
        all_passed = True

        for template in templates:
            print(f"\n{'─' * 80}")
            print(f"TEMPLATE: {template.role.upper()}")
            print(f"{'─' * 80}")

            template_passed = True
            checks_passed = 0
            total_checks = 0

            # Check behavioral rules
            print(f"\n  Behavioral Rules ({len(template.behavioral_rules)} total):")
            for keyword in mcp_checks["behavioral_rules"]:
                total_checks += 1
                rules_text = " ".join(template.behavioral_rules).lower()
                found = keyword.lower() in rules_text
                checks_passed += 1 if found else 0
                status = "✓" if found else "✗"
                print(f"    {status} Contains '{keyword}': {found}")
                if not found:
                    template_passed = False

            # Check success criteria
            print(f"\n  Success Criteria ({len(template.success_criteria)} total):")
            for keyword in mcp_checks["success_criteria"]:
                total_checks += 1
                criteria_text = " ".join(template.success_criteria).lower()
                found = keyword.lower() in criteria_text
                checks_passed += 1 if found else 0
                status = "✓" if found else "✗"
                print(f"    {status} Contains '{keyword}': {found}")
                if not found:
                    template_passed = False

            # Check template content
            print(f"\n  Template Content ({len(template.template_content)} chars):")
            for keyword in mcp_checks["template_content"]:
                total_checks += 1
                found = keyword in template.template_content
                checks_passed += 1 if found else 0
                status = "✓" if found else "✗"
                print(f"    {status} Contains '{keyword}': {found}")
                if not found:
                    template_passed = False

            # Metadata checks
            print("\n  Metadata:")
            total_checks += 3
            tool_ok = template.tool in ["claude", "codex", "gemini", "auto"]
            version_ok = template.version == "3.0.0"
            active_ok = template.is_active is True
            checks_passed += sum([tool_ok, version_ok, active_ok])

            print(f"    {'✓' if tool_ok else '✗'} Tool: {template.tool}")
            print(f"    {'✓' if version_ok else '✗'} Version: {template.version}")
            print(f"    {'✓' if active_ok else '✗'} Active: {template.is_active}")

            if not all([tool_ok, version_ok, active_ok]):
                template_passed = False

            # Overall status
            print(f"\n  Overall: {checks_passed}/{total_checks} checks passed")
            if template_passed:
                print("  Status: ✅ PASSED")
            else:
                print("  Status: ❌ FAILED")
                all_passed = False

            results[template.role] = {
                "passed": template_passed,
                "checks_passed": checks_passed,
                "total_checks": total_checks,
            }

        # Summary
        print(f"\n{'=' * 80}")
        print("SUMMARY")
        print(f"{'=' * 80}\n")

        passed_count = sum(1 for r in results.values() if r["passed"])
        total_count = len(results)

        print(f"Templates Verified: {total_count}")
        print(f"  ✅ Passed: {passed_count}")
        print(f"  ❌ Failed: {total_count - passed_count}")

        if all_passed:
            print("\n🎉 ALL TEMPLATES ENHANCED SUCCESSFULLY!")
        else:
            print("\n⚠️  SOME TEMPLATES NEED ATTENTION")
            print("\nFailed templates:")
            for role, result in results.items():
                if not result["passed"]:
                    print(f"  - {role}: {result['checks_passed']}/{result['total_checks']} checks passed")

        print(f"\n{'=' * 80}\n")

        return {
            "status": "success" if all_passed else "failed",
            "templates": results,
            "passed_count": passed_count,
            "total_count": total_count,
        }


def print_sample_content(tenant_key: str = "default", role: str = "orchestrator"):
    """Print sample template content for visual verification"""
    import asyncio

    async def get_sample():
        db_manager = get_db_manager()
        async with db_manager.get_session_async() as session:
            result = await session.execute(
                select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key, AgentTemplate.role == role)
            )
            template = result.scalar_one_or_none()

            if not template:
                print(f"❌ Template '{role}' not found for tenant '{tenant_key}'")
                return

            print(f"\n{'=' * 80}")
            print(f"SAMPLE TEMPLATE CONTENT: {role}")
            print(f"{'=' * 80}\n")

            # Print last 1500 chars (MCP section)
            content = template.template_content
            mcp_section_start = content.find("## MCP COMMUNICATION PROTOCOL")

            if mcp_section_start >= 0:
                mcp_section = content[mcp_section_start:]
                print(mcp_section)
            else:
                print("❌ MCP section not found in template!")
                print(f"\nLast 500 chars:\n{content[-500:]}")

            print(f"\n{'=' * 80}")

    asyncio.run(get_sample())


if __name__ == "__main__":
    tenant_key = sys.argv[1] if len(sys.argv) > 1 else "default"

    # Run verification
    results = asyncio.run(verify_templates(tenant_key))

    # Print sample content
    if results.get("status") == "success":
        print("\nSample MCP Coordination Section:")
        print_sample_content(tenant_key, "implementer")

    # Exit with appropriate code
    sys.exit(0 if results.get("status") == "success" else 1)
