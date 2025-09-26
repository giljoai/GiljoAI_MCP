#!/usr/bin/env python3
"""
AKE-MCP Migration Tool for GiljoAI MCP
Handles migration of projects, agents, messages, and tasks from AKE-MCP to GiljoAI MCP
"""

import json
import os
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


# Database imports
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor

    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

try:
    import sqlalchemy
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False


class AKEMCPMigrator:
    """Migrates data from AKE-MCP to GiljoAI MCP with multi-tenant support"""

    def __init__(self):
        self.ake_path = None
        self.ake_config = None
        self.giljo_config = None
        self.migration_log = []
        self.id_mapping = {"projects": {}, "agents": {}, "messages": {}, "tasks": {}}
        self.tenant_key = None

    def detect_ake_mcp(self) -> Optional[Path]:
        """Detect AKE-MCP installation"""
        # Check common locations
        possible_paths = [
            Path.home() / "ake-mcp",
            Path.home() / ".ake-mcp",
            Path("/opt/ake-mcp"),
            Path("/usr/local/ake-mcp"),
            Path.cwd().parent / "ake-mcp",
            Path.cwd().parent / "AKE-MCP",
            Path("F:/AKE-MCP"),  # Specific to your system
            Path("C:/AKE-MCP"),
        ]

        # Check environment variable
        env_path = os.environ.get("AKE_MCP_PATH")
        if env_path:
            possible_paths.insert(0, Path(env_path))

        for path in possible_paths:
            if path.exists() and (path / ".env").exists():
                self.log(f"Found AKE-MCP installation at: {path}")
                return path

        return None

    def load_ake_config(self, ake_path: Path) -> bool:
        """Load AKE-MCP configuration"""
        self.ake_path = ake_path
        config = {}

        # Load .env file
        env_file = ake_path / ".env"
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        config[key.strip()] = value.strip().strip("\"'")

        # Load config.json if exists
        config_json = ake_path / "config.json"
        if config_json.exists():
            with open(config_json) as f:
                json_config = json.load(f)
                config.update(json_config)

        self.ake_config = config
        self.log(f"Loaded AKE-MCP configuration with {len(config)} settings")
        return bool(config)

    def connect_ake_database(self) -> Optional[Any]:
        """Connect to AKE-MCP PostgreSQL database"""
        if not PSYCOPG2_AVAILABLE:
            self.log("ERROR: psycopg2 not installed. Run: pip install psycopg2")
            return None

        # Get database config from AKE-MCP
        db_config = {
            "host": self.ake_config.get("DB_HOST", "localhost"),
            "port": self.ake_config.get("DB_PORT", "5432"),
            "database": self.ake_config.get("DB_NAME", "ake_mcp"),
            "user": self.ake_config.get("DB_USER", "postgres"),
            "password": self.ake_config.get("DB_PASSWORD", ""),
        }

        try:
            conn = psycopg2.connect(**db_config)
            self.log(f"Connected to AKE-MCP database: {db_config['database']}")
            return conn
        except Exception as e:
            self.log(f"ERROR: Failed to connect to AKE-MCP database: {e}")
            return None

    def export_ake_data(self, conn) -> dict:
        """Export all data from AKE-MCP database"""
        data = {
            "metadata": {
                "source": "AKE-MCP",
                "export_date": datetime.now().isoformat(),
                "version": self.ake_config.get("VERSION", "1.0.0"),
            },
            "projects": [],
            "agents": [],
            "messages": [],
            "tasks": [],
            "sessions": [],
            "vision": [],
            "configurations": [],
        }

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Export projects
            try:
                cur.execute("SELECT * FROM projects ORDER BY created_at")
                data["projects"] = [dict(row) for row in cur.fetchall()]
                self.log(f"Exported {len(data['projects'])} projects")
            except Exception as e:
                self.log(f"Warning: Could not export projects: {e}")

            # Export agents
            try:
                cur.execute("SELECT * FROM agents ORDER BY created_at")
                data["agents"] = [dict(row) for row in cur.fetchall()]
                self.log(f"Exported {len(data['agents'])} agents")
            except Exception as e:
                self.log(f"Warning: Could not export agents: {e}")

            # Export messages
            try:
                cur.execute("SELECT * FROM messages ORDER BY created_at")
                data["messages"] = [dict(row) for row in cur.fetchall()]
                self.log(f"Exported {len(data['messages'])} messages")
            except Exception as e:
                self.log(f"Warning: Could not export messages: {e}")

            # Export tasks
            try:
                cur.execute("SELECT * FROM tasks ORDER BY created_at")
                data["tasks"] = [dict(row) for row in cur.fetchall()]
                self.log(f"Exported {len(data['tasks'])} tasks")
            except Exception as e:
                self.log(f"Warning: Could not export tasks: {e}")

            # Export sessions
            try:
                cur.execute("SELECT * FROM sessions ORDER BY created_at")
                data["sessions"] = [dict(row) for row in cur.fetchall()]
                self.log(f"Exported {len(data['sessions'])} sessions")
            except Exception as e:
                self.log(f"Warning: Could not export sessions: {e}")

            # Export vision documents
            try:
                cur.execute("SELECT * FROM vision ORDER BY created_at")
                data["vision"] = [dict(row) for row in cur.fetchall()]
                self.log(f"Exported {len(data['vision'])} vision documents")
            except Exception as e:
                self.log(f"Warning: Could not export vision: {e}")

            # Export configurations
            try:
                cur.execute("SELECT * FROM configurations")
                data["configurations"] = [dict(row) for row in cur.fetchall()]
                self.log(f"Exported {len(data['configurations'])} configurations")
            except Exception as e:
                self.log(f"Warning: Could not export configurations: {e}")

        return data

    def transform_for_multitenant(self, data: dict) -> dict:
        """Transform AKE-MCP data for multi-tenant GiljoAI MCP"""
        # Generate tenant key for this migration
        self.tenant_key = f"migrated-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        transformed = {
            "metadata": data["metadata"],
            "tenant_key": self.tenant_key,
            "projects": [],
            "agents": [],
            "messages": [],
            "tasks": [],
            "sessions": [],
            "vision": [],
            "configurations": [],
        }

        # Transform projects
        for project in data["projects"]:
            old_id = project.get("id")
            new_id = str(uuid.uuid4())
            self.id_mapping["projects"][old_id] = new_id

            transformed_project = {
                "id": new_id,
                "tenant_key": self.tenant_key,
                "name": project.get("name"),
                "mission": project.get("mission"),
                "status": project.get("status", "migrated"),
                "context_budget": project.get("context_budget", 150000),
                "context_used": project.get("context_used", 0),
                "metadata": {
                    "original_id": old_id,
                    "migrated_from": "AKE-MCP",
                    "migration_date": datetime.now().isoformat(),
                },
                "created_at": project.get("created_at"),
                "updated_at": datetime.now().isoformat(),
            }
            transformed["projects"].append(transformed_project)

        # Transform agents
        for agent in data["agents"]:
            old_id = agent.get("id")
            new_id = str(uuid.uuid4())
            self.id_mapping["agents"][old_id] = new_id

            # Map project ID
            old_project_id = agent.get("project_id")
            new_project_id = self.id_mapping["projects"].get(old_project_id)

            transformed_agent = {
                "id": new_id,
                "tenant_key": self.tenant_key,
                "project_id": new_project_id,
                "name": agent.get("name"),
                "role": agent.get("role", "worker"),
                "mission": agent.get("mission"),
                "status": agent.get("status", "migrated"),
                "context_used": agent.get("context_used", 0),
                "metadata": {"original_id": old_id, "migrated_from": "AKE-MCP"},
                "created_at": agent.get("created_at"),
                "updated_at": datetime.now().isoformat(),
            }
            transformed["agents"].append(transformed_agent)

        # Transform messages
        for message in data["messages"]:
            old_id = message.get("id")
            new_id = str(uuid.uuid4())
            self.id_mapping["messages"][old_id] = new_id

            # Map agent IDs
            from_agent_old = message.get("from_agent")
            to_agent_old = message.get("to_agent")
            from_agent_new = self.id_mapping["agents"].get(from_agent_old)
            to_agent_new = self.id_mapping["agents"].get(to_agent_old)

            # Map project ID
            old_project_id = message.get("project_id")
            new_project_id = self.id_mapping["projects"].get(old_project_id)

            transformed_message = {
                "id": new_id,
                "tenant_key": self.tenant_key,
                "project_id": new_project_id,
                "from_agent": from_agent_new or from_agent_old,
                "to_agent": to_agent_new or to_agent_old,
                "message_type": message.get("message_type", "migrated"),
                "content": message.get("content"),
                "priority": message.get("priority", "normal"),
                "status": message.get("status", "delivered"),
                "metadata": {"original_id": old_id, "migrated_from": "AKE-MCP"},
                "created_at": message.get("created_at"),
                "acknowledged_at": message.get("acknowledged_at"),
                "completed_at": message.get("completed_at"),
            }
            transformed["messages"].append(transformed_message)

        # Transform tasks
        for task in data["tasks"]:
            old_id = task.get("id")
            new_id = str(uuid.uuid4())
            self.id_mapping["tasks"][old_id] = new_id

            # Map agent ID
            old_agent_id = task.get("agent_id")
            new_agent_id = self.id_mapping["agents"].get(old_agent_id)

            # Map project ID
            old_project_id = task.get("project_id")
            new_project_id = self.id_mapping["projects"].get(old_project_id)

            transformed_task = {
                "id": new_id,
                "tenant_key": self.tenant_key,
                "project_id": new_project_id,
                "agent_id": new_agent_id,
                "title": task.get("title"),
                "description": task.get("description"),
                "status": task.get("status", "migrated"),
                "priority": task.get("priority", "medium"),
                "metadata": {"original_id": old_id, "migrated_from": "AKE-MCP"},
                "created_at": task.get("created_at"),
                "completed_at": task.get("completed_at"),
            }
            transformed["tasks"].append(transformed_task)

        # Transform other entities similarly...
        transformed["sessions"] = data["sessions"]
        transformed["vision"] = data["vision"]
        transformed["configurations"] = data["configurations"]

        self.log(f"Transformed data for multi-tenant with key: {self.tenant_key}")
        return transformed

    def validate_migration(self, original: dict, transformed: dict) -> tuple[bool, list[str]]:
        """Validate the migration data"""
        issues = []

        # Check counts
        if len(transformed["projects"]) != len(original["projects"]):
            issues.append(f"Project count mismatch: {len(original['projects'])} -> {len(transformed['projects'])}")

        if len(transformed["agents"]) != len(original["agents"]):
            issues.append(f"Agent count mismatch: {len(original['agents'])} -> {len(transformed['agents'])}")

        if len(transformed["messages"]) != len(original["messages"]):
            issues.append(f"Message count mismatch: {len(original['messages'])} -> {len(transformed['messages'])}")

        # Check ID mappings
        for project in transformed["projects"]:
            if not project.get("id"):
                issues.append(f"Project missing ID: {project.get('name')}")
            if project.get("tenant_key") != self.tenant_key:
                issues.append(f"Project tenant key mismatch: {project.get('name')}")

        # Check relationships
        for agent in transformed["agents"]:
            project_id = agent.get("project_id")
            if project_id and project_id not in [p["id"] for p in transformed["projects"]]:
                issues.append(f"Agent {agent.get('name')} references non-existent project")

        for message in transformed["messages"]:
            from_agent = message.get("from_agent")
            to_agent = message.get("to_agent")

            if (
                from_agent
                and from_agent not in [a["id"] for a in transformed["agents"]]
                and from_agent != "orchestrator"
            ):
                issues.append(f"Message references non-existent from_agent: {from_agent}")

            if to_agent and to_agent not in [a["id"] for a in transformed["agents"]] and to_agent != "orchestrator":
                issues.append(f"Message references non-existent to_agent: {to_agent}")

        valid = len(issues) == 0
        return valid, issues

    def save_migration_data(self, data: dict, output_path: Path):
        """Save migration data to file"""
        output_file = output_path / f"ake_migration_{self.tenant_key}.json"

        with open(output_file, "w") as f:
            json.dump(data, f, indent=2, default=str)

        self.log(f"Saved migration data to: {output_file}")
        return output_file

    def import_to_giljo(self, data: dict, giljo_db_url: str) -> bool:
        """Import transformed data into GiljoAI MCP database"""
        if not SQLALCHEMY_AVAILABLE:
            self.log("ERROR: SQLAlchemy not installed. Run: pip install sqlalchemy")
            return False

        try:
            engine = create_engine(giljo_db_url)

            with engine.begin() as conn:
                # Import projects
                for project in data["projects"]:
                    conn.execute(
                        text(
                            """
                        INSERT INTO projects (id, tenant_key, name, mission, status,
                                            context_budget, context_used, metadata,
                                            created_at, updated_at)
                        VALUES (:id, :tenant_key, :name, :mission, :status,
                               :context_budget, :context_used, :metadata,
                               :created_at, :updated_at)
                    """
                        ),
                        project,
                    )

                self.log(f"Imported {len(data['projects'])} projects")

                # Import agents
                for agent in data["agents"]:
                    conn.execute(
                        text(
                            """
                        INSERT INTO agents (id, tenant_key, project_id, name, role,
                                          mission, status, context_used, metadata,
                                          created_at, updated_at)
                        VALUES (:id, :tenant_key, :project_id, :name, :role,
                               :mission, :status, :context_used, :metadata,
                               :created_at, :updated_at)
                    """
                        ),
                        agent,
                    )

                self.log(f"Imported {len(data['agents'])} agents")

                # Import messages
                for message in data["messages"]:
                    conn.execute(
                        text(
                            """
                        INSERT INTO messages (id, tenant_key, project_id, from_agent,
                                            to_agent, message_type, content, priority,
                                            status, metadata, created_at,
                                            acknowledged_at, completed_at)
                        VALUES (:id, :tenant_key, :project_id, :from_agent,
                               :to_agent, :message_type, :content, :priority,
                               :status, :metadata, :created_at,
                               :acknowledged_at, :completed_at)
                    """
                        ),
                        message,
                    )

                self.log(f"Imported {len(data['messages'])} messages")

                # Import tasks
                for task in data["tasks"]:
                    conn.execute(
                        text(
                            """
                        INSERT INTO tasks (id, tenant_key, project_id, agent_id,
                                         title, description, status, priority,
                                         metadata, created_at, completed_at)
                        VALUES (:id, :tenant_key, :project_id, :agent_id,
                               :title, :description, :status, :priority,
                               :metadata, :created_at, :completed_at)
                    """
                        ),
                        task,
                    )

                self.log(f"Imported {len(data['tasks'])} tasks")

            self.log("Migration completed successfully!")
            return True

        except Exception as e:
            self.log(f"ERROR: Failed to import data: {e}")
            return False

    def copy_vision_documents(self):
        """Copy vision documents from AKE-MCP to GiljoAI MCP"""
        if not self.ake_path:
            return

        ake_vision = self.ake_path / "vision"
        giljo_vision = Path.cwd() / "docs" / "Vision" / "migrated"

        if ake_vision.exists():
            giljo_vision.mkdir(parents=True, exist_ok=True)

            for file in ake_vision.glob("*.md"):
                dest = giljo_vision / file.name
                shutil.copy2(file, dest)
                self.log(f"Copied vision document: {file.name}")

    def log(self, message: str):
        """Log migration activity"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.migration_log.append(log_entry)
        print(log_entry)

    def save_log(self, output_path: Path):
        """Save migration log"""
        log_file = output_path / f"migration_log_{self.tenant_key}.txt"

        with open(log_file, "w") as f:
            f.write("\n".join(self.migration_log))

        print(f"Migration log saved to: {log_file}")

    def run_migration(
        self, ake_path: Optional[Path] = None, giljo_db_url: Optional[str] = None, output_path: Optional[Path] = None
    ) -> bool:
        """Run the complete migration process"""
        # Set defaults
        if not output_path:
            output_path = Path.cwd() / "migrations"
        output_path.mkdir(exist_ok=True)

        # Step 1: Detect AKE-MCP
        if not ake_path:
            ake_path = self.detect_ake_mcp()

        if not ake_path:
            self.log("ERROR: Could not find AKE-MCP installation")
            return False

        # Step 2: Load configuration
        if not self.load_ake_config(ake_path):
            self.log("ERROR: Could not load AKE-MCP configuration")
            return False

        # Step 3: Connect to AKE database
        conn = self.connect_ake_database()
        if not conn:
            return False

        try:
            # Step 4: Export data
            self.log("Starting data export...")
            original_data = self.export_ake_data(conn)

            # Step 5: Transform for multi-tenant
            self.log("Transforming data for multi-tenant architecture...")
            transformed_data = self.transform_for_multitenant(original_data)

            # Step 6: Validate
            self.log("Validating migration...")
            valid, issues = self.validate_migration(original_data, transformed_data)

            if not valid:
                self.log("ERROR: Validation failed:")
                for issue in issues:
                    self.log(f"  - {issue}")
                return False

            self.log("Validation passed!")

            # Step 7: Save migration data
            migration_file = self.save_migration_data(transformed_data, output_path)

            # Step 8: Import to GiljoAI if URL provided
            if giljo_db_url:
                self.log("Importing data to GiljoAI MCP...")
                if not self.import_to_giljo(transformed_data, giljo_db_url):
                    self.log("ERROR: Import failed")
                    return False

            # Step 9: Copy vision documents
            self.copy_vision_documents()

            # Step 10: Save log
            self.save_log(output_path)

            self.log("\n✓ Migration completed successfully!")
            self.log(f"  Tenant Key: {self.tenant_key}")
            self.log(f"  Migration File: {migration_file}")
            self.log(f"  Projects: {len(transformed_data['projects'])}")
            self.log(f"  Agents: {len(transformed_data['agents'])}")
            self.log(f"  Messages: {len(transformed_data['messages'])}")
            self.log(f"  Tasks: {len(transformed_data['tasks'])}")

            return True

        finally:
            conn.close()


def main():
    """CLI interface for migration tool"""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate from AKE-MCP to GiljoAI MCP")
    parser.add_argument("--ake-path", type=Path, help="Path to AKE-MCP installation")
    parser.add_argument("--giljo-db", help="GiljoAI database URL (e.g., postgresql://...)")
    parser.add_argument("--output", type=Path, help="Output directory for migration files")
    parser.add_argument("--dry-run", action="store_true", help="Export only, no import")

    args = parser.parse_args()

    migrator = AKEMCPMigrator()

    # Handle dry run
    giljo_db = None if args.dry_run else args.giljo_db

    success = migrator.run_migration(ake_path=args.ake_path, giljo_db_url=giljo_db, output_path=args.output)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
