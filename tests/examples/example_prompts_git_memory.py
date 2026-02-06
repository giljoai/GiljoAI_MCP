"""
Generate example prompts showing Git + 360 Memory injection.

Handover: Git Integration + 360 Memory Prompt Injection
Author: Backend Integration Tester Agent
Date: 2025-11-16

PURPOSE: Demonstrate prompt injection behavior with real examples.
"""

from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator
from src.giljo_mcp.models.products import Product


def create_example_product_git_enabled():
    """Create example product with git integration enabled."""
    return Product(
        id="prod-example-git",
        tenant_key="demo-tenant",
        name="GiljoAI MCP Server",
        description="Multi-agent orchestration system",
        product_memory={
            "git_integration": {
                "enabled": True,
                "commit_limit": 20,
                "default_branch": "main"
            },
            "learnings": [
                {
                    "sequence": 1,
                    "summary": "Initial backend setup completed with FastAPI + PostgreSQL",
                    "key_outcomes": ["Database migrations working", "Auth system functional"],
                    "timestamp": "2025-11-01T10:00:00Z"
                },
                {
                    "sequence": 2,
                    "summary": "Frontend dashboard integrated with WebSocket real-time updates",
                    "key_outcomes": ["Agent status live updates", "Project grid responsive"],
                    "timestamp": "2025-11-05T14:30:00Z"
                },
                {
                    "sequence": 3,
                    "summary": "Orchestrator succession implemented with manual handover",
                    "key_outcomes": ["Context handover working", "Lineage tracking complete"],
                    "timestamp": "2025-11-10T09:15:00Z"
                }
            ],
            "context": {
                "objectives": [
                    "Maintain >80% test coverage across services",
                    "Ensure multi-tenant data isolation",
                    "Keep thin client prompts under 200 tokens"
                ],
                "decisions": [
                    "Use PostgreSQL exclusively (no SQLite support)",
                    "Always enable authentication (no default credentials)",
                    "JSONB columns for flexible config and memory storage"
                ]
            }
        }
    )


def create_example_product_git_disabled():
    """Create example product without git integration."""
    return Product(
        id="prod-example-nogit",
        tenant_key="demo-tenant",
        name="Prototype App",
        description="Quick prototyping without version control",
        product_memory={
            "git_integration": {
                "enabled": False
            },
            "learnings": [
                {
                    "sequence": 1,
                    "summary": "Initial prototype built with manual tracking",
                    "key_outcomes": ["Core features working"],
                    "timestamp": "2025-11-15T12:00:00Z"
                }
            ],
            "context": {
                "objectives": ["Rapid prototyping", "Minimal overhead"]
            }
        }
    )


def main():
    """Generate and display example prompts."""

    print("=" * 80)
    print("EXAMPLE PROMPTS: Git + 360 Memory Injection")
    print("=" * 80)
    print()

    # Initialize generator (no actual DB needed for examples)
    generator = ThinClientPromptGenerator(db=None, tenant_key="demo-tenant")

    # Example 1: Git ENABLED
    print("EXAMPLE 1: Git Integration ENABLED")
    print("-" * 80)
    product_git = create_example_product_git_enabled()

    prompt_git = generator._build_thin_prompt_with_memory(
        orchestrator_id="orch-example-123",
        project_id="proj-example-456",
        project_name="GiljoAI MCP Server",        tool="universal",
        product=product_git
    )

    print(prompt_git)
    print()
    print(f"Token Estimate: {len(prompt_git) // 4} tokens")
    print(f"Character Count: {len(prompt_git)} chars")
    print()

    # Example 2: Git DISABLED
    print("=" * 80)
    print("EXAMPLE 2: Git Integration DISABLED")
    print("-" * 80)
    product_nogit = create_example_product_git_disabled()

    prompt_nogit = generator._build_thin_prompt_with_memory(
        orchestrator_id="orch-example-789",
        project_id="proj-example-012",
        project_name="Prototype App",        tool="universal",
        product=product_nogit
    )

    print(prompt_nogit)
    print()
    print(f"Token Estimate: {len(prompt_nogit) // 4} tokens")
    print(f"Character Count: {len(prompt_nogit)} chars")
    print()

    # Comparison
    print("=" * 80)
    print("COMPARISON")
    print("-" * 80)
    print(f"With Git:    {len(prompt_git)} chars (~{len(prompt_git) // 4} tokens)")
    print(f"Without Git: {len(prompt_nogit)} chars (~{len(prompt_nogit) // 4} tokens)")
    print(f"Difference:  {len(prompt_git) - len(prompt_nogit)} chars (~{(len(prompt_git) - len(prompt_nogit)) // 4} tokens)")
    print()

    # Verify both have 360 memory
    assert "360 Memory" in prompt_git or "memory" in prompt_git.lower()
    assert "360 Memory" in prompt_nogit or "memory" in prompt_nogit.lower()
    print("[OK] Both prompts include 360 Memory section")

    # Verify only git-enabled has git instructions
    assert "git log" in prompt_git
    assert "git log" not in prompt_nogit
    print("[OK] Only git-enabled prompt includes git instructions")

    # Verify existing structure preserved
    assert "IDENTITY" in prompt_git and "IDENTITY" in prompt_nogit
    assert "MCP CONNECTION" in prompt_git and "MCP CONNECTION" in prompt_nogit
    print("[OK] Existing prompt structure preserved in both")

    print()
    print("=" * 80)
    print("SUCCESS: All examples generated and validated!")
    print("=" * 80)

    # Save to file for review
    with open("F:/GiljoAI_MCP/tests/examples/example_prompts_output.txt", "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("EXAMPLE PROMPTS: Git + 360 Memory Injection\n")
        f.write("=" * 80 + "\n\n")

        f.write("EXAMPLE 1: Git Integration ENABLED\n")
        f.write("-" * 80 + "\n")
        f.write(prompt_git)
        f.write(f"\n\nToken Estimate: {len(prompt_git) // 4} tokens\n")
        f.write(f"Character Count: {len(prompt_git)} chars\n\n")

        f.write("=" * 80 + "\n")
        f.write("EXAMPLE 2: Git Integration DISABLED\n")
        f.write("-" * 80 + "\n")
        f.write(prompt_nogit)
        f.write(f"\n\nToken Estimate: {len(prompt_nogit) // 4} tokens\n")
        f.write(f"Character Count: {len(prompt_nogit)} chars\n\n")

    print("\nPrompts saved to: tests/examples/example_prompts_output.txt")


if __name__ == "__main__":
    main()
