"""
Populate config_data for existing products from CLAUDE.md and project detection.

This script:
1. Reads CLAUDE.md to extract architecture, tech stack, test commands
2. Detects frontend/backend frameworks from package files
3. Checks Serena MCP availability
4. Populates Product.config_data JSONB field

Usage:
    python scripts/populate_config_data.py [--product-id PRODUCT_ID] [--dry-run]
"""

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.database import get_db_manager
from src.giljo_mcp.models import Product
from src.giljo_mcp.context_manager import validate_config_data


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def extract_architecture_from_claude_md(claude_md_path: Path) -> Optional[str]:
    """Extract architecture description from CLAUDE.md"""
    if not claude_md_path.exists():
        logger.warning(f"CLAUDE.md not found at {claude_md_path}")
        return None

    content = claude_md_path.read_text(encoding='utf-8')

    # Look for architecture section
    arch_patterns = [
        r'##\s*Architecture\s*(?:Overview)?\s*\n+([^\n#]+)',  # ## Architecture Overview\n<text> (not another header)
        r'###\s*Architecture\s*(?:Overview)?\s*\n+([^\n#]+)',  # ### Architecture Overview\n<text> (not another header)
        r'Architecture:\s*(.+?)(?=\n|$)',  # Architecture: <text>
        r'System:\s*(.+?)(?=\n|$)'  # System: <text>
    ]

    for pattern in arch_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            arch = match.group(1).strip()
            # Skip if it's just whitespace or looks like a header
            if arch and not arch.startswith('#'):
                return arch

    # Fallback: try to infer from content
    if 'FastAPI' in content and 'PostgreSQL' in content:
        if 'Vue' in content:
            return "FastAPI + PostgreSQL + Vue.js"
        elif 'React' in content:
            return "FastAPI + PostgreSQL + React"
        else:
            return "FastAPI + PostgreSQL"

    return None


def extract_tech_stack_from_claude_md(claude_md_path: Path) -> List[str]:
    """Extract technology stack from CLAUDE.md"""
    if not claude_md_path.exists():
        return []

    content = claude_md_path.read_text(encoding='utf-8')
    tech_stack = []

    # Common patterns
    python_match = re.search(r'Python\s+([\d\.]+)', content, re.IGNORECASE)
    if python_match:
        tech_stack.append(f"Python {python_match.group(1)}")

    postgres_match = re.search(r'PostgreSQL\s+([\d]+)', content, re.IGNORECASE)
    if postgres_match:
        tech_stack.append(f"PostgreSQL {postgres_match.group(1)}")

    # Frontend frameworks
    for framework in ['Vue 3', 'Vue.js', 'React', 'Angular', 'Svelte']:
        if framework in content:
            tech_stack.append(framework)
            break

    # Backend frameworks
    for framework in ['FastAPI', 'Django', 'Flask', 'Express.js']:
        if framework in content:
            tech_stack.append(framework)
            break

    # Tools
    if 'Docker' in content:
        tech_stack.append('Docker')
    if 'Alembic' in content:
        tech_stack.append('Alembic')
    if 'SQLAlchemy' in content:
        tech_stack.append('SQLAlchemy')

    return tech_stack


def extract_test_commands_from_claude_md(claude_md_path: Path) -> List[str]:
    """Extract test commands from CLAUDE.md"""
    if not claude_md_path.exists():
        return []

    content = claude_md_path.read_text(encoding='utf-8')
    test_commands = []

    # Look for test command patterns - must be in command context (after : or on new line or after $)
    # Match patterns like "pytest tests/" or "Run: pytest" but not "use pytest for"
    pytest_patterns = [
        r'(?:^|\n|:|\$)\s*pytest\s+\S+[^\n]*',  # After newline, colon, or $
        r'```[^\n]*\n\s*pytest\s+\S+[^\n]*',  # In code block
    ]

    for pattern in pytest_patterns:
        pytest_match = re.search(pattern, content)
        if pytest_match:
            cmd = pytest_match.group(0).strip()
            # Clean up prefixes
            cmd = re.sub(r'^[$:]\s*', '', cmd)
            if cmd.startswith('pytest'):
                test_commands.append(cmd)
                break

    npm_test_match = re.search(r'npm\s+run\s+test[^\n]*', content)
    if npm_test_match:
        test_commands.append(npm_test_match.group(0).strip())

    # Fallback defaults (only if commands are mentioned but no specific command found)
    if not test_commands:
        # Only add fallback if the word "pytest" appears and testing is mentioned
        if re.search(r'\bpytest\b', content, re.IGNORECASE) and 'test' in content.lower():
            test_commands.append('pytest tests/')
        # Only add npm test if npm is mentioned with test context
        if re.search(r'\bnpm\b', content, re.IGNORECASE) and 'test' in content.lower():
            test_commands.append('npm run test')

    return test_commands


def detect_frontend_framework(root_path: Path) -> Optional[str]:
    """Detect frontend framework from package.json"""
    package_json = root_path / "package.json"

    if not package_json.exists():
        # Check in frontend subdirectory
        package_json = root_path / "frontend" / "package.json"

    if not package_json.exists():
        return None

    try:
        with open(package_json, encoding='utf-8') as f:
            data = json.load(f)

        dependencies = {**data.get('dependencies', {}), **data.get('devDependencies', {})}

        if 'vue' in dependencies:
            version = dependencies['vue']
            if version.startswith('^3') or version.startswith('3.'):
                return "Vue 3"
            return "Vue.js"
        elif 'react' in dependencies:
            return "React"
        elif '@angular/core' in dependencies:
            return "Angular"
        elif 'svelte' in dependencies:
            return "Svelte"

    except Exception as e:
        logger.warning(f"Failed to parse package.json: {e}")

    return None


def detect_backend_framework(root_path: Path) -> Optional[str]:
    """Detect backend framework from requirements.txt or pyproject.toml"""
    requirements_txt = root_path / "requirements.txt"

    if requirements_txt.exists():
        content = requirements_txt.read_text(encoding='utf-8').lower()

        if 'fastapi' in content:
            return "FastAPI"
        elif 'django' in content:
            return "Django"
        elif 'flask' in content:
            return "Flask"

    # Check pyproject.toml
    pyproject_toml = root_path / "pyproject.toml"
    if pyproject_toml.exists():
        content = pyproject_toml.read_text(encoding='utf-8').lower()

        if 'fastapi' in content:
            return "FastAPI"
        elif 'django' in content:
            return "Django"
        elif 'flask' in content:
            return "Flask"

    return None


def detect_codebase_structure(root_path: Path) -> Dict[str, str]:
    """Detect codebase directory structure"""
    structure = {}

    # Common directories to check
    dirs_to_check = {
        'api': 'REST API endpoints',
        'frontend': 'Frontend application',
        'src': 'Core application code',
        'tests': 'Test suites',
        'docs': 'Documentation',
        'installer': 'Installation scripts',
        'scripts': 'Utility scripts',
        'migrations': 'Database migrations',
        'static': 'Static assets',
        'templates': 'Templates'
    }

    for dir_name, description in dirs_to_check.items():
        dir_path = root_path / dir_name
        if dir_path.exists() and dir_path.is_dir():
            structure[dir_name] = description

    # Check for nested src structure
    src_path = root_path / "src"
    if src_path.exists():
        # Find main package
        for item in src_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                structure[f"src/{item.name}"] = f"{item.name.replace('_', ' ').title()} package"
                break

    return structure


def check_serena_mcp_available() -> bool:
    """Check if Serena MCP is available"""
    try:
        # Check if serena-mcp package is importable
        import importlib.util
        spec = importlib.util.find_spec("serena_mcp")
        return spec is not None
    except Exception:
        return False


def extract_project_config_data(root_path: Path) -> Dict[str, Any]:
    """
    Extract rich context from project files.

    Args:
        root_path: Root path of the project

    Returns:
        config_data dictionary
    """
    config_data = {}

    # Read CLAUDE.md for architecture
    claude_md = root_path / "CLAUDE.md"

    architecture = extract_architecture_from_claude_md(claude_md)
    if architecture:
        config_data["architecture"] = architecture

    tech_stack = extract_tech_stack_from_claude_md(claude_md)
    if tech_stack:
        config_data["tech_stack"] = tech_stack

    test_commands = extract_test_commands_from_claude_md(claude_md)
    if test_commands:
        config_data["test_commands"] = test_commands

    # Detect frameworks
    frontend = detect_frontend_framework(root_path)
    if frontend:
        config_data["frontend_framework"] = frontend

    backend = detect_backend_framework(root_path)
    if backend:
        config_data["backend_framework"] = backend

    # Detect codebase structure
    structure = detect_codebase_structure(root_path)
    if structure:
        config_data["codebase_structure"] = structure

    # Check Serena MCP
    config_data["serena_mcp_enabled"] = check_serena_mcp_available()

    # Add defaults if not found
    if "architecture" not in config_data:
        config_data["architecture"] = "Unknown (populate manually)"

    # Documentation defaults
    if (root_path / "docs").exists():
        config_data["api_docs"] = "/docs/api_reference.md"
        config_data["documentation_style"] = "Markdown with mermaid diagrams"

    # Database type (check for PostgreSQL indicators)
    if (root_path / "alembic").exists() or "PostgreSQL" in str(tech_stack):
        config_data["database_type"] = "postgresql"

    return config_data


def populate_product_config_data(
    product_id: Optional[str] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Populate config_data for products.

    Args:
        product_id: Optional specific product ID (if None, process all)
        dry_run: If True, don't write to database

    Returns:
        Summary of operation
    """
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")

    db = get_db_manager(database_url=database_url)

    # Use current directory as project root
    root_path = Path.cwd()

    results = {
        "processed": 0,
        "updated": 0,
        "errors": 0,
        "skipped": 0
    }

    with db.get_session() as session:
        # Get products to process
        if product_id:
            products = session.query(Product).filter(Product.id == product_id).all()
        else:
            products = session.query(Product).all()

        for product in products:
            results["processed"] += 1

            try:
                # Check if already has config_data
                if product.config_data and len(product.config_data) > 0:
                    logger.info(f"Product {product.name} already has config_data, skipping")
                    results["skipped"] += 1
                    continue

                # Extract config_data
                logger.info(f"Extracting config_data for product: {product.name}")
                config_data = extract_project_config_data(root_path)

                # Validate
                is_valid, errors = validate_config_data(config_data)
                if not is_valid:
                    logger.error(f"Validation failed for {product.name}: {errors}")
                    results["errors"] += 1
                    continue

                logger.info(f"Extracted config_data:\n{json.dumps(config_data, indent=2)}")

                if not dry_run:
                    # Update product
                    product.config_data = config_data
                    session.commit()
                    logger.info(f"Updated config_data for product: {product.name}")
                    results["updated"] += 1
                else:
                    logger.info(f"[DRY RUN] Would update product: {product.name}")
                    results["updated"] += 1

            except Exception as e:
                logger.error(f"Failed to process product {product.name}: {e}")
                results["errors"] += 1

    return results


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Populate config_data for products")
    parser.add_argument(
        "--product-id",
        help="Specific product ID to process (if not provided, process all)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without writing to database"
    )

    args = parser.parse_args()

    logger.info("Starting config_data population")

    if args.dry_run:
        logger.info("DRY RUN MODE - No database changes will be made")

    results = populate_product_config_data(
        product_id=args.product_id,
        dry_run=args.dry_run
    )

    logger.info("\n" + "="*60)
    logger.info("POPULATION SUMMARY")
    logger.info("="*60)
    logger.info(f"Products processed: {results['processed']}")
    logger.info(f"Products updated: {results['updated']}")
    logger.info(f"Products skipped (already have config_data): {results['skipped']}")
    logger.info(f"Errors: {results['errors']}")
    logger.info("="*60)

    if results['errors'] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
