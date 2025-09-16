#!/usr/bin/env python3
"""
Template initialization script for GiljoAI MCP.

Loads default agent templates into the database.
"""

import sys
import os
from pathlib import Path
import argparse
import re
from typing import Dict, List, Optional
import json
from datetime import datetime
from uuid import uuid4

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy.orm import Session
from giljo_mcp.database import DatabaseManager, get_db_manager
from giljo_mcp.models import AgentTemplate


def extract_variables(template_content: str) -> List[str]:
    """Extract variable names from template content."""
    # Find all {variable_name} patterns
    pattern = r'\{(\w+)\}'
    matches = re.findall(pattern, template_content)
    # Return unique variables
    return list(set(matches))


def get_default_templates() -> Dict[str, Dict]:
    """Get the default template definitions."""
    templates = {
        "orchestrator": {
            "content": """You are the Project Orchestrator for: {project_name}

PROJECT GOAL: {project_mission}
PRODUCT: {product_name}

YOUR DISCOVERY APPROACH (Dynamic Context Loading):
1. Read the vision document using get_vision()
2. Review product settings with get_product_settings()
3. Use Serena MCP to explore the codebase
4. Only load what's relevant to this specific project

YOUR RESPONSIBILITIES:
- Create any agents with ANY job types you deem necessary
- Define precise missions for each agent based on discoveries
- Choose optimal implementation approach
- Design the agent pipeline that best achieves the goal""",
            "role": "orchestrator",
            "description": "Main orchestrator agent that manages project workflow and spawns other agents",
            "is_default": True
        },
        "analyzer": {
            "content": """You are the Analyzer Agent for: {project_name}

PROJECT GOAL: {project_mission}

YOUR MISSION:
Perform deep analysis of the system to understand requirements, identify patterns,
and design optimal solutions that align with project goals.

YOUR APPROACH:
1. Analyze existing code structure and patterns
2. Identify integration points and dependencies
3. Design solutions that follow established patterns
4. Document findings and recommendations""",
            "role": "analyzer",
            "description": "Analyzes requirements and designs solutions",
            "is_default": False
        },
        "implementer": {
            "content": """You are the Implementation Agent for: {project_name}

PROJECT GOAL: {project_mission}

YOUR MISSION:
Implement the required functionality following design specifications and project standards.

YOUR APPROACH:
1. Follow design specifications exactly
2. Write clean, maintainable code
3. Add appropriate error handling
4. Test your implementation
5. Document complex logic""",
            "role": "implementer",
            "description": "Implements functionality according to specifications",
            "is_default": False
        },
        "tester": {
            "content": """You are the Testing Agent for: {project_name}

PROJECT GOAL: {project_mission}

YOUR MISSION:
Ensure quality through comprehensive testing of all functionality.

YOUR APPROACH:
1. Write comprehensive test cases
2. Test all functionality thoroughly
3. Verify edge cases
4. Document test results
5. Report any issues found""",
            "role": "tester",
            "description": "Tests functionality and ensures quality",
            "is_default": False
        },
        "reviewer": {
            "content": """You are the Review Agent for: {project_name}

PROJECT GOAL: {project_mission}

YOUR MISSION:
Review code and documentation to ensure quality, standards compliance, and completeness.

YOUR APPROACH:
1. Review code for quality and standards
2. Verify requirements are met
3. Check for security issues
4. Ensure documentation is complete
5. Provide constructive feedback""",
            "role": "reviewer",
            "description": "Reviews code and documentation for quality",
            "is_default": False
        },
        "documenter": {
            "content": """You are the Documentation Agent for: {project_name}

PROJECT GOAL: {project_mission}

YOUR MISSION:
Create comprehensive documentation for all project deliverables.

YOUR APPROACH:
1. Document all implemented features
2. Create usage examples and tutorials
3. Write API documentation
4. Update README and setup guides
5. Document architectural decisions""",
            "role": "documenter", 
            "description": "Creates comprehensive documentation",
            "is_default": False
        }
    }
    return templates


def init_templates(
    database_url: Optional[str] = None,
    tenant_key: Optional[str] = None,
    product_id: Optional[str] = None,
    force_reload: bool = False
):
    """
    Initialize the database with default templates.
    
    Args:
        database_url: Database URL. If None, uses default SQLite.
        tenant_key: Tenant key for multi-tenant isolation.
        product_id: Product ID for template association.
        force_reload: Whether to reload templates even if they exist.
    """
    print(f"Initializing templates...")
    
    # Create database manager
    db_manager = get_db_manager(database_url)
    
    if database_url:
        print(f"Using database: {database_url}")
    else:
        print(f"Using default SQLite database: {db_manager.database_url}")
    
    # Use defaults if not provided
    if not tenant_key:
        tenant_key = "default"
        print(f"Using default tenant key: {tenant_key}")
    
    if not product_id:
        product_id = str(uuid4())
        print(f"Generated product ID: {product_id}")
    
    try:
        # Get database session
        with db_manager.get_session() as session:
            # Get default templates
            templates = get_default_templates()
            
            created_count = 0
            skipped_count = 0
            updated_count = 0
            
            for name, template_def in templates.items():
                # Check if template already exists
                existing = session.query(AgentTemplate).filter(
                    AgentTemplate.tenant_key == tenant_key,
                    AgentTemplate.product_id == product_id,
                    AgentTemplate.name == name
                ).first()
                
                if existing and not force_reload:
                    print(f"  Template '{name}' already exists, skipping...")
                    skipped_count += 1
                    continue
                elif existing and force_reload:
                    # Update existing template
                    print(f"  Updating template '{name}'...")
                    existing.template_content = template_def["content"]
                    existing.role = template_def["role"]
                    existing.description = template_def["description"]
                    existing.is_default = template_def["is_default"]
                    existing.variables = json.dumps(extract_variables(template_def["content"]))
                    existing.version = "1.0.0"
                    existing.updated_at = datetime.utcnow()
                    updated_count += 1
                else:
                    # Create new template
                    print(f"  Creating template '{name}'...")
                    
                    template = AgentTemplate(
                        id=str(uuid4()),
                        tenant_key=tenant_key,
                        product_id=product_id,
                        name=name,
                        category="role",  # All templates are role-based
                        role=template_def["role"],
                        template_content=template_def["content"],
                        variables=json.dumps(extract_variables(template_def["content"])),
                        description=template_def["description"],
                        version="1.0.0",
                        is_active=True,
                        is_default=template_def["is_default"],
                        tags=json.dumps([template_def["role"], "default"]),
                        meta_data=json.dumps({
                            "source": "init_templates",
                            "created_by": "system"
                        }),
                        usage_count=0,
                        avg_generation_ms=0.0,
                        created_by="system"
                    )
                    
                    session.add(template)
                    created_count += 1
            
            # Commit all changes
            session.commit()
            
            print(f"\nTemplate initialization complete!")
            print(f"  Created: {created_count} templates")
            print(f"  Updated: {updated_count} templates")
            print(f"  Skipped: {skipped_count} templates")
            
            # Verify templates were created
            total_templates = session.query(AgentTemplate).filter(
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.product_id == product_id
            ).count()
            
            print(f"\nTotal templates in database: {total_templates}")
            
            # List all templates
            print("\nAvailable templates:")
            for template in session.query(AgentTemplate).filter(
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.product_id == product_id
            ).all():
                default_marker = " (DEFAULT)" if template.is_default else ""
                print(f"  - {template.name} ({template.role}){default_marker}")
            
            return True
        
    except Exception as e:
        print(f"Error initializing templates: {e}", file=sys.stderr)
        return False
    finally:
        db_manager.close()


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Initialize GiljoAI MCP templates")
    
    parser.add_argument(
        "--database-url",
        help="Database URL (e.g., sqlite:///path/to/db.db or postgresql://user:pass@host/db)",
        default=None
    )
    
    parser.add_argument(
        "--tenant-key",
        help="Tenant key for multi-tenant isolation",
        default="default"
    )
    
    parser.add_argument(
        "--product-id",
        help="Product ID for template association",
        default=None
    )
    
    parser.add_argument(
        "--force-reload",
        action="store_true",
        help="Force reload templates even if they already exist"
    )
    
    parser.add_argument(
        "--postgresql",
        action="store_true",
        help="Use PostgreSQL with default local settings"
    )
    
    args = parser.parse_args()
    
    # Build database URL if PostgreSQL flag is set
    database_url = args.database_url
    if args.postgresql and not database_url:
        database_url = DatabaseManager.build_postgresql_url(
            host="localhost",
            port=5432,
            database="giljo_mcp",
            username="postgres",
            password=os.getenv("DB_PASSWORD", "")
        )
    
    # Initialize templates
    success = init_templates(
        database_url=database_url,
        tenant_key=args.tenant_key,
        product_id=args.product_id,
        force_reload=args.force_reload
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()