#!/usr/bin/env python3
"""
Documentation Generator Example
Orchestrates multiple agents to generate comprehensive documentation
"""

import asyncio
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from giljo_mcp.database import DatabaseManager
from giljo_mcp.orchestrator import ProjectOrchestrator
from giljo_mcp.template_manager import TemplateManager
from src.giljo_mcp.config_manager import Config


@dataclass
class CodeSymbol:
    """Represents a code symbol found during scanning"""

    name: str
    type: str  # function, class, method, variable
    file: str
    line: int
    docstring: Optional[str] = None
    signature: Optional[str] = None
    parent: Optional[str] = None
    children: list[str] = field(default_factory=list)


@dataclass
class DocumentationSection:
    """Represents a section of documentation"""

    title: str
    content: str
    format: str = "markdown"
    order: int = 0
    subsections: list["DocumentationSection"] = field(default_factory=list)


@dataclass
class DiagramSpec:
    """Specification for a diagram"""

    type: str  # architecture, sequence, class, dependency
    title: str
    elements: list[dict[str, Any]]
    relationships: list[dict[str, Any]]
    format: str = "mermaid"


class DocumentationOrchestrator:
    """Orchestrates documentation generation across multiple agents"""

    def __init__(self, source_path: Path, output_path: Path, tenant_key: str = "doc-gen-demo"):
        """
        Initialize the documentation orchestrator

        Args:
            source_path: Path to source code to document
            output_path: Path for generated documentation
            tenant_key: Unique identifier for this session
        """
        self.source_path = Path(source_path)
        self.output_path = Path(output_path)
        self.tenant_key = tenant_key
        self.config = Config()
        self.db = DatabaseManager(self.config.database_url)
        self.orchestrator = None
        self.project = None
        self.agents = {}

        # Documentation state
        self.symbols: list[CodeSymbol] = []
        self.sections: list[DocumentationSection] = []
        self.diagrams: list[DiagramSpec] = []

    async def setup(self):
        """Initialize database and orchestrator"""
        await self.db.initialize()

        self.orchestrator = ProjectOrchestrator(db=self.db, tenant_key=self.tenant_key)

        # Create project
        self.project = await self.orchestrator.create_project(
            name=f"Document {self.source_path.name}", mission=self._create_mission()
        )

        print(f"✅ Documentation project created: {self.project.id}")
        print(f"📁 Source: {self.source_path}")
        print(f"📄 Output: {self.output_path}")

    def _create_mission(self) -> str:
        """Create the documentation mission"""
        return f"""
        Generate comprehensive documentation for {self.source_path}.

        OBJECTIVES:
        1. Scan and analyze all source code
        2. Extract API documentation with examples
        3. Create architecture diagrams
        4. Generate user guides and tutorials
        5. Produce configuration reference

        OUTPUT FORMATS:
        - Markdown for all text documentation
        - Mermaid for diagrams
        - JSON for API schemas
        - HTML static site via MkDocs

        QUALITY STANDARDS:
        - Document all public APIs
        - Include usage examples for each function
        - Generate diagrams for complex flows
        - Maintain consistent formatting
        - Cross-reference related sections
        """

    async def spawn_agents(self):
        """Create specialized documentation agents"""
        tm = TemplateManager(session=self.db.session, tenant_key=self.tenant_key, product_id=self.project.id)

        agent_configs = [
            {
                "name": "scanner",
                "role": "Code scanner and indexer",
                "template": await tm.get_template(
                    name="scanner",
                    augmentations="Focus on Python, JavaScript, and YAML files",
                    variables={"source": str(self.source_path)},
                ),
            },
            {
                "name": "parser",
                "role": "Code parser and analyzer",
                "template": await tm.get_template(
                    name="parser",
                    augmentations="Extract complete AST, docstrings, and type hints",
                    variables={"extract_examples": True},
                ),
            },
            {
                "name": "writer",
                "role": "Documentation writer",
                "template": await tm.get_template(
                    name="writer",
                    augmentations="Clear, concise technical writing with examples",
                    variables={"style_guide": "Google Developer Documentation"},
                ),
            },
            {
                "name": "diagram",
                "role": "Diagram generator",
                "template": await tm.get_template(
                    name="diagram",
                    augmentations="Create Mermaid diagrams for architecture and flows",
                    variables={"formats": ["mermaid", "svg"]},
                ),
            },
            {
                "name": "publisher",
                "role": "Documentation publisher",
                "template": await tm.get_template(
                    name="publisher",
                    augmentations="Generate MkDocs site with Material theme",
                    variables={"deploy_target": "github-pages"},
                ),
            },
        ]

        for config in agent_configs:
            agent = await self.orchestrator.spawn_agent(
                name=config["name"], mission=config["template"], project_id=self.project.id
            )
            self.agents[config["name"]] = agent
            print(f"🤖 Spawned {config['name']}: {config['role']}")

    async def generate_documentation(self):
        """Execute the documentation generation workflow"""
        print("\n📚 Starting documentation generation...\n")

        # Phase 1: Scan codebase
        print("🔍 Phase 1: Scanning codebase...")
        await self._scan_phase()

        # Phase 2: Parse and analyze
        print("\n🔬 Phase 2: Parsing and analyzing code...")
        await self._parse_phase()

        # Phase 3: Generate documentation
        print("\n✍️ Phase 3: Writing documentation...")
        await self._write_phase()

        # Phase 4: Create diagrams
        print("\n📊 Phase 4: Generating diagrams...")
        await self._diagram_phase()

        # Phase 5: Publish documentation
        print("\n🚀 Phase 5: Publishing documentation...")
        await self._publish_phase()

        # Generate summary
        await self._generate_summary()

    async def _scan_phase(self):
        """Scan codebase for documentation targets"""
        # Request scan from scanner agent
        await self.orchestrator.send_message(
            from_agent="orchestrator",
            to_agent="scanner",
            content={
                "task": "scan_codebase",
                "path": str(self.source_path),
                "patterns": ["*.py", "*.js", "*.ts", "*.yaml", "*.json"],
                "exclude": ["__pycache__", "node_modules", ".git"],
            },
        )

        # Simulate receiving scan results
        scan_results = await self._wait_for_response("scanner", timeout=30)

        # Process scan results
        files_found = scan_results.get("files", [])
        print(f"  ✅ Found {len(files_found)} files to document")

        # Create symbol index
        await self.orchestrator.send_message(
            from_agent="orchestrator", to_agent="scanner", content={"task": "create_symbol_index", "files": files_found}
        )

        symbol_index = await self._wait_for_response("scanner", timeout=45)
        self.symbols = self._parse_symbols(symbol_index)

        print(f"  ✅ Indexed {len(self.symbols)} symbols")
        print(f"     - Classes: {len([s for s in self.symbols if s.type == 'class'])}")
        print(f"     - Functions: {len([s for s in self.symbols if s.type == 'function'])}")
        print(f"     - Methods: {len([s for s in self.symbols if s.type == 'method'])}")

    async def _parse_phase(self):
        """Parse code for detailed analysis"""
        # Group symbols by file for batch processing
        files_to_parse = {}
        for symbol in self.symbols:
            if symbol.file not in files_to_parse:
                files_to_parse[symbol.file] = []
            files_to_parse[symbol.file].append(symbol)

        parsed_data = []
        for file_path, symbols in files_to_parse.items():
            await self.orchestrator.send_message(
                from_agent="orchestrator",
                to_agent="parser",
                content={
                    "task": "parse_file",
                    "file": file_path,
                    "symbols": [asdict(s) for s in symbols],
                    "extract": ["docstrings", "types", "examples", "dependencies"],
                },
            )

            result = await self._wait_for_response("parser", timeout=20)
            parsed_data.append(result)

        print(f"  ✅ Parsed {len(parsed_data)} files")

        # Update symbols with parsed information
        for data in parsed_data:
            self._update_symbols_with_parsed_data(data)

    async def _write_phase(self):
        """Generate documentation content"""
        sections = []

        # API Reference
        await self.orchestrator.send_message(
            from_agent="orchestrator",
            to_agent="writer",
            content={
                "task": "generate_api_reference",
                "symbols": [asdict(s) for s in self.symbols],
                "format": "markdown",
                "include_examples": True,
            },
        )

        api_ref = await self._wait_for_response("writer", timeout=60)
        sections.append(DocumentationSection(title="API Reference", content=api_ref.get("content", ""), order=1))

        # User Guide
        await self.orchestrator.send_message(
            from_agent="orchestrator",
            to_agent="writer",
            content={
                "task": "generate_user_guide",
                "source_path": str(self.source_path),
                "key_features": self._identify_key_features(),
            },
        )

        user_guide = await self._wait_for_response("writer", timeout=45)
        sections.append(DocumentationSection(title="User Guide", content=user_guide.get("content", ""), order=2))

        # Configuration Guide
        await self.orchestrator.send_message(
            from_agent="orchestrator",
            to_agent="writer",
            content={"task": "generate_config_guide", "config_files": self._find_config_files()},
        )

        config_guide = await self._wait_for_response("writer", timeout=30)
        sections.append(DocumentationSection(title="Configuration", content=config_guide.get("content", ""), order=3))

        self.sections = sections
        print(f"  ✅ Generated {len(sections)} documentation sections")

    async def _diagram_phase(self):
        """Generate architecture and flow diagrams"""
        diagrams = []

        # Architecture diagram
        await self.orchestrator.send_message(
            from_agent="orchestrator",
            to_agent="diagram",
            content={
                "task": "generate_architecture_diagram",
                "components": self._identify_components(),
                "format": "mermaid",
            },
        )

        arch_diagram = await self._wait_for_response("diagram", timeout=30)
        diagrams.append(
            DiagramSpec(
                type="architecture",
                title="System Architecture",
                elements=arch_diagram.get("elements", []),
                relationships=arch_diagram.get("relationships", []),
            )
        )

        # Class diagram for main classes
        main_classes = [s for s in self.symbols if s.type == "class"][:10]
        if main_classes:
            await self.orchestrator.send_message(
                from_agent="orchestrator",
                to_agent="diagram",
                content={"task": "generate_class_diagram", "classes": [asdict(c) for c in main_classes]},
            )

            class_diagram = await self._wait_for_response("diagram", timeout=30)
            diagrams.append(
                DiagramSpec(
                    type="class",
                    title="Class Diagram",
                    elements=class_diagram.get("elements", []),
                    relationships=class_diagram.get("relationships", []),
                )
            )

        self.diagrams = diagrams
        print(f"  ✅ Generated {len(diagrams)} diagrams")

    async def _publish_phase(self):
        """Publish documentation in various formats"""
        # Prepare all content
        all_content = {
            "sections": [asdict(s) for s in self.sections],
            "diagrams": [asdict(d) for d in self.diagrams],
            "metadata": {"project": self.source_path.name, "generated": datetime.now().isoformat(), "version": "1.0.0"},
        }

        # Generate MkDocs site
        await self.orchestrator.send_message(
            from_agent="orchestrator",
            to_agent="publisher",
            content={
                "task": "generate_mkdocs",
                "content": all_content,
                "output_path": str(self.output_path),
                "theme": "material",
                "features": ["search", "navigation.tabs", "content.code.copy"],
            },
        )

        mkdocs_result = await self._wait_for_response("publisher", timeout=60)

        # Write documentation files
        self._write_documentation_files()

        print(f"  ✅ Documentation published to {self.output_path}")
        print("     - Format: MkDocs with Material theme")
        print(f"     - Files generated: {mkdocs_result.get('files_count', 0)}")

    def _write_documentation_files(self):
        """Write documentation files to disk"""
        # Create output directory
        self.output_path.mkdir(parents=True, exist_ok=True)

        # Write main index
        index_content = self._generate_index()
        (self.output_path / "index.md").write_text(index_content)

        # Write API reference
        api_dir = self.output_path / "api"
        api_dir.mkdir(exist_ok=True)

        for symbol in self.symbols:
            if symbol.type in ["class", "function"]:
                file_path = api_dir / f"{symbol.name.lower()}.md"
                content = self._generate_symbol_doc(symbol)
                file_path.write_text(content)

        # Write sections
        for section in self.sections:
            file_name = section.title.lower().replace(" ", "-") + ".md"
            (self.output_path / file_name).write_text(section.content)

        # Write diagrams
        diagrams_dir = self.output_path / "diagrams"
        diagrams_dir.mkdir(exist_ok=True)

        for diagram in self.diagrams:
            file_path = diagrams_dir / f"{diagram.type}.md"
            content = self._generate_diagram_content(diagram)
            file_path.write_text(content)

        # Generate MkDocs configuration
        mkdocs_config = self._generate_mkdocs_config()
        (self.output_path / "mkdocs.yml").write_text(mkdocs_config)

    def _generate_index(self) -> str:
        """Generate main index page"""
        return f"""# {self.source_path.name} Documentation

Welcome to the comprehensive documentation for {self.source_path.name}.

## Quick Start

Get started with {self.source_path.name} in minutes:

1. [Installation](user-guide.md#installation)
2. [Basic Usage](user-guide.md#basic-usage)
3. [API Reference](api-reference.md)

## Documentation Sections

- **[User Guide](user-guide.md)** - Complete guide for users
- **[API Reference](api-reference.md)** - Detailed API documentation
- **[Configuration](configuration.md)** - Configuration options
- **[Architecture](diagrams/architecture.md)** - System architecture

## Key Features

{self._format_key_features()}

## Getting Help

- [GitHub Issues](https://github.com/example/repo/issues)
- [Community Forum](https://forum.example.com)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/example)

---

*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    def _generate_symbol_doc(self, symbol: CodeSymbol) -> str:
        """Generate documentation for a symbol"""
        doc = f"# {symbol.name}\n\n"

        if symbol.signature:
            doc += f"```python\n{symbol.signature}\n```\n\n"

        if symbol.docstring:
            doc += f"{symbol.docstring}\n\n"

        if symbol.children:
            doc += "## Methods\n\n"
            for child in symbol.children:
                doc += f"- [{child}](#{child.lower()})\n"

        return doc

    def _generate_diagram_content(self, diagram: DiagramSpec) -> str:
        """Generate diagram content in Mermaid format"""
        content = f"# {diagram.title}\n\n"
        content += "```mermaid\n"

        if diagram.type == "architecture":
            content += "graph TB\n"
            for elem in diagram.elements:
                content += f"    {elem['id']}[{elem['label']}]\n"
            for rel in diagram.relationships:
                content += f"    {rel['from']} --> {rel['to']}\n"

        elif diagram.type == "class":
            content += "classDiagram\n"
            for elem in diagram.elements:
                content += f"    class {elem['name']} {{\n"
                for method in elem.get("methods", []):
                    content += f"        +{method}\n"
                content += "    }\n"

        content += "```\n"
        return content

    def _generate_mkdocs_config(self) -> str:
        """Generate MkDocs configuration"""
        config = {
            "site_name": f"{self.source_path.name} Documentation",
            "theme": {
                "name": "material",
                "features": [
                    "navigation.tabs",
                    "navigation.sections",
                    "toc.integrate",
                    "search.suggest",
                    "search.highlight",
                    "content.code.copy",
                ],
                "palette": {"scheme": "default", "primary": "indigo", "accent": "indigo"},
            },
            "nav": [
                {"Home": "index.md"},
                {"User Guide": "user-guide.md"},
                {
                    "API Reference": [{"Overview": "api-reference.md"}]
                    + [{s.name: f"api/{s.name.lower()}.md"} for s in self.symbols if s.type == "class"]
                },
                {"Configuration": "configuration.md"},
                {"Architecture": [{"Overview": "diagrams/architecture.md"}, {"Class Diagram": "diagrams/class.md"}]},
            ],
            "plugins": ["search", "mermaid2"],
            "markdown_extensions": [
                "pymdownx.highlight",
                "pymdownx.superfences",
                "pymdownx.inlinehilite",
                "pymdownx.snippets",
            ],
        }

        import yaml

        return yaml.dump(config, default_flow_style=False)

    def _parse_symbols(self, symbol_index: dict) -> list[CodeSymbol]:
        """Parse symbol index into CodeSymbol objects"""
        symbols = []
        for file_path, file_symbols in symbol_index.get("symbols", {}).items():
            for sym in file_symbols:
                symbol = CodeSymbol(
                    name=sym["name"],
                    type=sym["type"],
                    file=file_path,
                    line=sym.get("line", 0),
                    docstring=sym.get("docstring"),
                    signature=sym.get("signature"),
                    parent=sym.get("parent"),
                    children=sym.get("children", []),
                )
                symbols.append(symbol)
        return symbols

    def _update_symbols_with_parsed_data(self, data: dict):
        """Update symbols with parsed information"""
        for update in data.get("symbols", []):
            for symbol in self.symbols:
                if symbol.name == update["name"] and symbol.file == update["file"]:
                    symbol.docstring = update.get("docstring", symbol.docstring)
                    symbol.signature = update.get("signature", symbol.signature)

    def _identify_key_features(self) -> list[str]:
        """Identify key features from codebase"""
        # Simplified - would analyze code structure
        return [
            "Async/await support",
            "Type hints throughout",
            "Comprehensive error handling",
            "Modular architecture",
            "Extensive test coverage",
        ]

    def _format_key_features(self) -> str:
        """Format key features for display"""
        features = self._identify_key_features()
        return "\n".join(f"- ✨ {feature}" for feature in features)

    def _find_config_files(self) -> list[str]:
        """Find configuration files in the project"""
        config_patterns = ["*.yaml", "*.yml", "*.json", "*.toml", "*.ini"]
        config_files = []
        for pattern in config_patterns:
            config_files.extend(self.source_path.glob(pattern))
        return [str(f) for f in config_files]

    def _identify_components(self) -> list[dict]:
        """Identify system components for architecture diagram"""
        # Simplified - would analyze imports and structure
        return [
            {"id": "api", "label": "API Layer", "type": "service"},
            {"id": "core", "label": "Core Logic", "type": "library"},
            {"id": "db", "label": "Database", "type": "storage"},
            {"id": "cache", "label": "Cache", "type": "storage"},
            {"id": "queue", "label": "Message Queue", "type": "service"},
        ]

    async def _generate_summary(self):
        """Generate documentation summary"""
        print("\n" + "=" * 60)
        print("DOCUMENTATION GENERATION COMPLETE")
        print("=" * 60)
        print(f"📁 Source: {self.source_path}")
        print(f"📄 Output: {self.output_path}")
        print("\n📊 Statistics:")
        print(f"   - Symbols documented: {len(self.symbols)}")
        print(f"   - Sections generated: {len(self.sections)}")
        print(f"   - Diagrams created: {len(self.diagrams)}")
        print("\n✅ Next steps:")
        print(f"   1. cd {self.output_path}")
        print("   2. mkdocs serve")
        print("   3. Open http://localhost:7272")

    async def _wait_for_response(self, agent: str, timeout: int = 30) -> dict:
        """Wait for agent response (mock implementation)"""
        await asyncio.sleep(1)
        # Return mock data
        return {"status": "completed", "content": "", "files_count": 10}

    async def cleanup(self):
        """Clean up resources"""
        if self.orchestrator:
            await self.orchestrator.close_project(self.project.id)
        if self.db:
            await self.db.close()


async def main():
    """Run the documentation generator example"""

    # Define paths
    source_path = Path("./src")  # Source code to document
    output_path = Path("./docs")  # Output directory

    # Create orchestrator
    doc_gen = DocumentationOrchestrator(source_path, output_path)

    try:
        # Setup
        await doc_gen.setup()

        # Spawn agents
        await doc_gen.spawn_agents()

        # Generate documentation
        await doc_gen.generate_documentation()

    finally:
        await doc_gen.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
