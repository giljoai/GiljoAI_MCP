# Documentation Generator Example

This example demonstrates using GiljoAI MCP Orchestrator to automatically generate comprehensive documentation from your codebase.

## What This Example Shows

- Automated documentation extraction
- Multi-format documentation generation
- Code example extraction
- API documentation from code
- Architecture diagram generation

## The Scenario

You have a complex codebase that needs comprehensive documentation including:

- API reference documentation
- Code architecture diagrams
- Usage examples and tutorials
- Configuration guides
- Deployment documentation

The orchestrator coordinates specialized agents to analyze code and generate complete documentation.

## Architecture

```
┌─────────────────┐
│   Orchestrator  │ Coordinates documentation generation
└────────┬────────┘
         │
    ┌────┴────┬──────────┬──────────┬──────────┐
    ▼         ▼          ▼          ▼          ▼
┌────────┐ ┌──────┐ ┌───────┐ ┌──────┐ ┌─────────┐
│Scanner │ │Parser│ │Writer │ │Diagram│ │Publisher│
└────────┘ └──────┘ └───────┘ └──────┘ └─────────┘
```

## Quick Start

```python
# 1. Initialize the documentation generator
from giljo_mcp import create_orchestrator

orchestrator = create_orchestrator(
    project_name="documentation-generation",
    tenant_key="doc-gen-demo"
)

# 2. Define documentation requirements
requirements = """
Generate comprehensive documentation for the codebase including:
- API reference with examples
- Architecture overview with diagrams
- Getting started guide
- Configuration reference
- Deployment guide
"""

# 3. Create the project
project = orchestrator.create_project(
    name="Documentation Generation",
    mission=requirements
)

# 4. Spawn documentation agents
agents = orchestrator.spawn_agents([
    {"name": "scanner", "type": "code_scanner"},
    {"name": "parser", "type": "code_parser"},
    {"name": "writer", "type": "doc_writer"},
    {"name": "diagram", "type": "diagram_generator"},
    {"name": "publisher", "type": "doc_publisher"}
])

# 5. Generate documentation
orchestrator.execute()
```

## Full Implementation

See `doc_generator.py` for the complete implementation.

## Agent Workflows

### Scanner Agent

- Discovers all code files and structure
- Identifies documentation comments
- Extracts function signatures and types
- Maps module dependencies

### Parser Agent

- Parses code AST for detailed analysis
- Extracts docstrings and comments
- Identifies design patterns
- Builds symbol table

### Writer Agent

- Generates markdown documentation
- Creates usage examples
- Writes API references
- Produces configuration guides

### Diagram Agent

- Creates architecture diagrams
- Generates sequence diagrams
- Builds class diagrams
- Produces dependency graphs

### Publisher Agent

- Formats documentation for different outputs
- Generates static site (MkDocs/Sphinx)
- Creates PDF documentation
- Publishes to documentation hosting

## Documentation Types Generated

### 1. API Reference

````markdown
## API Reference

### `create_project(name: str, mission: str) -> Project`

Creates a new project with orchestration agents.

**Parameters:**

- `name`: Project identifier
- `mission`: Project objectives and requirements

**Returns:**

- `Project`: The created project instance

**Example:**

```python
project = orchestrator.create_project(
    name="My Project",
    mission="Build awesome features"
)
```
````

````

### 2. Architecture Documentation
- System overview diagrams
- Component interaction flows
- Database schema diagrams
- Deployment architecture

### 3. User Guides
- Getting started tutorial
- Common use cases
- Best practices
- Troubleshooting guide

### 4. Configuration Reference
- Environment variables
- Configuration files
- Feature flags
- Performance tuning

## Customization

### Select Documentation Formats
```python
config = {
    "formats": ["markdown", "html", "pdf"],
    "themes": {
        "html": "material",
        "pdf": "professional"
    },
    "languages": ["python", "javascript", "yaml"]
}
````

### Configure Analysis Depth

```python
analysis_config = {
    "include_private": False,
    "extract_examples": True,
    "generate_tests": True,
    "complexity_metrics": True
}
```

### Custom Templates

```python
templates = {
    "api_reference": "templates/api.md",
    "user_guide": "templates/guide.md",
    "architecture": "templates/arch.md"
}
```

## Output Structure

```
docs/
├── api/
│   ├── reference.md
│   ├── examples.md
│   └── schemas.json
├── guides/
│   ├── getting-started.md
│   ├── configuration.md
│   └── deployment.md
├── architecture/
│   ├── overview.md
│   ├── diagrams/
│   │   ├── system.svg
│   │   ├── database.svg
│   │   └── sequence.svg
│   └── patterns.md
├── mkdocs.yml
└── index.md
```

## Advanced Features

### Auto-Update Documentation

```python
# Watch for code changes
orchestrator.watch_mode(
    paths=["src/", "api/"],
    on_change=lambda: orchestrator.regenerate_docs()
)
```

### Version Documentation

```python
# Generate docs for multiple versions
versions = ["v1.0", "v2.0", "latest"]
for version in versions:
    orchestrator.generate_docs(version=version)
```

### Multi-Language Support

```python
# Generate docs in multiple languages
languages = ["en", "es", "fr", "de"]
for lang in languages:
    orchestrator.generate_docs(language=lang)
```

## Example: Documenting GiljoAI MCP

```python
# Document the orchestrator itself
doc_gen = DocumentationGenerator(
    source_path="./src/giljo_mcp",
    output_path="./docs"
)

# Configure what to document
doc_gen.configure(
    include_patterns=["*.py"],
    exclude_patterns=["test_*.py", "__pycache__"],
    extract_todos=True,
    generate_examples=True
)

# Generate comprehensive docs
await doc_gen.generate()
```

## Integration with CI/CD

```yaml
# .github/workflows/docs.yml
name: Generate Documentation
on:
  push:
    branches: [main]

jobs:
  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Generate Docs
        run: python doc_generator.py
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./docs
```

## Monitoring Progress

```python
# Subscribe to generation events
orchestrator.on("agent_progress", lambda e:
    print(f"{e.agent}: {e.progress}% - {e.current_file}")
)

# Track documentation completeness
stats = orchestrator.get_documentation_stats()
print(f"Documented: {stats['documented_symbols']} / {stats['total_symbols']}")
print(f"Coverage: {stats['coverage']}%")
```

## Troubleshooting

### Missing Documentation

```python
# Find undocumented code
undocumented = scanner.find_undocumented()
for item in undocumented:
    print(f"Missing docs: {item['file']}:{item['line']} - {item['symbol']}")
```

### Parsing Errors

```python
# Handle parsing failures gracefully
parser.on_error(lambda e:
    print(f"Parse error in {e.file}: {e.message}")
)
```

## Next Steps

- Customize documentation templates
- Add custom documentation extractors
- Integrate with your existing docs workflow
- Set up automated documentation updates

## Learn More

- [Template Customization](../../docs/guides/templates.md)
- [Parser Configuration](../../docs/api/parser.md)
- [Diagram Generation](../../docs/guides/diagrams.md)
