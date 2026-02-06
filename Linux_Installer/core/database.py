"""
PostgreSQL 18 database installer with fallback script generation
Handles database creation, role setup, and migrations

This module provides comprehensive PostgreSQL setup capabilities:
- PostgreSQL version detection and validation (14-18)
- Direct database creation with admin credentials
- Fallback script generation for elevated privileges
- Alembic migration support
- Secure password generation
- Optimized for Linux environments
"""

import logging
import os
import platform
import secrets
import socket
import string
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


try:
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    psycopg2 = None
    sql = None
    ISOLATION_LEVEL_AUTOCOMMIT = None


class DatabaseInstaller:
    """Handle PostgreSQL setup with elevation fallback"""

    # Supported PostgreSQL versions
    MIN_PG_VERSION = 14
    MAX_PG_VERSION = 18
    RECOMMENDED_VERSION = 18

    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self.host = settings.get("host", "localhost")
        self.port = settings.get("port", 5432)
        self.password = settings.get("password")
        self.username = settings.get("username", "postgres")
        self.db_name = "giljo_mcp"
        self.logger = logging.getLogger(self.__class__.__name__)

        # Generated credentials
        self.owner_password = None
        self.user_password = None
        self.credentials_file = None

        # PostgreSQL version info
        self.pg_version = None
        self.pg_version_string = None

    def setup(self) -> Dict[str, Any]:
        """Main database setup workflow"""
        result = {"success": False, "errors": [], "warnings": []}

        try:
            # Check PostgreSQL availability
            self.logger.info("Checking PostgreSQL connection...")
            if not check_postgresql_connection(self.host, self.port):
                result["errors"].append("Cannot connect to PostgreSQL")
                result["postgresql_guide"] = self.get_postgresql_install_guide()
                return result

            # Check psycopg2 availability
            if not psycopg2:
                self.logger.warning("psycopg2 not installed, using fallback approach")
                return self.fallback_setup()

            # Detect and validate PostgreSQL version
            self.logger.info("Detecting PostgreSQL version...")
            version_result = self.detect_postgresql_version()
            if not version_result["success"]:
                result["warnings"].append(
                    f"Could not detect PostgreSQL version: {version_result.get('error', 'Unknown')}"
                )
            else:
                self.pg_version = version_result["version"]
                self.pg_version_string = version_result["version_string"]
                self.logger.info(f"Detected PostgreSQL {self.pg_version_string}")

                # Validate version compatibility
                if self.pg_version < self.MIN_PG_VERSION:
                    result["errors"].append(
                        f"PostgreSQL {self.pg_version} is not supported. "
                        f"Minimum version: {self.MIN_PG_VERSION}. "
                        f"Please upgrade to PostgreSQL {self.RECOMMENDED_VERSION}."
                    )
                    return result
                if self.pg_version > self.MAX_PG_VERSION:
                    result["warnings"].append(
                        f"PostgreSQL {self.pg_version} is newer than tested version {self.MAX_PG_VERSION}. "
                        "Installation will proceed but compatibility is not guaranteed."
                    )
                elif self.pg_version < self.RECOMMENDED_VERSION:
                    result["warnings"].append(
                        f"PostgreSQL {self.pg_version} is supported but version {self.RECOMMENDED_VERSION} "
                        "is recommended for best compatibility."
                    )

            # Try direct database creation
            self.logger.info("Attempting direct database creation...")
            direct_result = self.create_database_direct()

            if direct_result["success"]:
                self.logger.info("Database created successfully via direct connection")
                result = direct_result
                result["warnings"] = result.get("warnings", [])
            else:
                # Need elevation - generate fallback scripts
                self.logger.info("Direct creation failed, generating fallback scripts...")
                result = self.fallback_setup()

            return result

        except Exception as e:
            result["errors"].append(str(e))
            self.logger.error(f"Database setup failed: {e}", exc_info=True)
            return result

    def detect_postgresql_version(self) -> Dict[str, Any]:
        """Detect PostgreSQL version via connection"""
        result = {"success": False}

        try:
            # Try to connect and get version
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database="postgres",
                user=self.username,
                password=self.password,
                connect_timeout=5,
            )

            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                version_string = cur.fetchone()[0]

                # Also get numeric version
                cur.execute("SHOW server_version_num;")
                version_num = int(cur.fetchone()[0])

                # Extract major version (first two digits)
                major_version = version_num // 10000

            conn.close()

            result["success"] = True
            result["version"] = major_version
            result["version_string"] = version_string
            result["version_num"] = version_num

            return result

        except psycopg2.OperationalError as e:
            result["error"] = f"Connection failed: {e!s}"
            return result
        except Exception as e:
            result["error"] = str(e)
            return result

    def create_database_direct(self) -> Dict[str, Any]:
        """Attempt to create database with provided credentials"""
        result = {"success": False, "errors": [], "warnings": []}

        try:
            # Generate secure passwords
            self.owner_password = self.generate_password()
            self.user_password = self.generate_password()

            # Connect to PostgreSQL as admin
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database="postgres",
                user=self.username,
                password=self.password,
                connect_timeout=10,
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

            with conn.cursor() as cur:
                # Check if database exists
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (self.db_name,))
                db_exists = cur.fetchone() is not None

                # Check if roles exist
                cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", ("giljo_owner",))
                owner_exists = cur.fetchone() is not None

                cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", ("giljo_user",))
                user_exists = cur.fetchone() is not None

                # Create or update roles
                self.logger.info("Setting up database roles...")

                if owner_exists:
                    # Update password for existing owner role
                    self.logger.info("Updating password for existing giljo_owner role")
                    cur.execute(
                        sql.SQL("ALTER ROLE {} WITH PASSWORD %s").format(sql.Identifier("giljo_owner")),
                        [self.owner_password],
                    )
                else:
                    # Create owner role
                    self.logger.info("Creating giljo_owner role")
                    cur.execute(
                        sql.SQL("CREATE ROLE {} LOGIN PASSWORD %s").format(sql.Identifier("giljo_owner")),
                        [self.owner_password],
                    )

                if user_exists:
                    # Update password for existing user role
                    self.logger.info("Updating password for existing giljo_user role")
                    cur.execute(
                        sql.SQL("ALTER ROLE {} WITH PASSWORD %s").format(sql.Identifier("giljo_user")),
                        [self.user_password],
                    )
                else:
                    # Create application user role
                    self.logger.info("Creating giljo_user role")
                    cur.execute(
                        sql.SQL("CREATE ROLE {} LOGIN PASSWORD %s").format(sql.Identifier("giljo_user")),
                        [self.user_password],
                    )

                # Create database if needed
                if not db_exists:
                    self.logger.info(f"Creating database {self.db_name}...")
                    cur.execute(
                        sql.SQL("CREATE DATABASE {} OWNER {}").format(
                            sql.Identifier(self.db_name), sql.Identifier("giljo_owner")
                        )
                    )
                    self.logger.info("Database created successfully")
                else:
                    self.logger.info(f"Database {self.db_name} already exists")
                    result["warnings"].append(f"Database {self.db_name} already exists, using existing database")

            conn.close()

            # Connect to the database and setup permissions
            self.logger.info("Setting up database permissions...")
            conn_db = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.db_name,
                user=self.username,
                password=self.password,
            )
            conn_db.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

            with conn_db.cursor() as cur:
                # Grant database-level permissions
                cur.execute(
                    sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                        sql.Identifier(self.db_name), sql.Identifier("giljo_user")
                    )
                )

                # Grant schema permissions
                cur.execute("""
                    GRANT USAGE, CREATE ON SCHEMA public TO giljo_owner;
                    GRANT ALL ON SCHEMA public TO giljo_user;
                """)

                # Grant privileges on existing tables and sequences
                cur.execute("""
                    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO giljo_user;
                    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO giljo_user;
                """)
                # Grant default privileges for tables
                cur.execute("""
                    ALTER DEFAULT PRIVILEGES FOR ROLE giljo_owner IN SCHEMA public
                    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO giljo_user;
                """)

                # Grant default privileges for sequences
                cur.execute("""
                    ALTER DEFAULT PRIVILEGES FOR ROLE giljo_owner IN SCHEMA public
                    GRANT USAGE, SELECT ON SEQUENCES TO giljo_user;
                """)

            conn_db.close()

            # Save credentials
            self.save_credentials()

            result["success"] = True
            result["credentials"] = {"owner_password": self.owner_password, "user_password": self.user_password}
            result["credentials_file"] = str(self.credentials_file)
            result["database_existed"] = db_exists

            return result

        except psycopg2.OperationalError as e:
            error_msg = str(e).lower()
            if "password authentication failed" in error_msg:
                result["errors"].append("Invalid PostgreSQL admin password")
            elif "could not connect" in error_msg or "connection refused" in error_msg:
                result["errors"].append("Cannot connect to PostgreSQL server")
            elif "permission denied" in error_msg:
                result["errors"].append("Insufficient privileges - try fallback script")
            else:
                result["errors"].append(f"Database operation failed: {e}")
            return result

        except psycopg2.Error as e:
            result["errors"].append(f"PostgreSQL error: {e}")
            self.logger.error(f"PostgreSQL error during database creation: {e}")
            return result

        except Exception as e:
            result["errors"].append(str(e))
            self.logger.error(f"Direct database creation failed: {e}", exc_info=True)
            return result

    def fallback_setup(self) -> Dict[str, Any]:
        """Generate fallback scripts for manual execution"""
        result = {"success": False, "errors": []}

        try:
            # Generate secure passwords
            self.owner_password = self.generate_password()
            self.user_password = self.generate_password()

            # Create scripts directory for Linux scripts (absolute path)
            base_dir = Path(__file__).resolve().parent.parent
            scripts_dir = base_dir / "scripts"
            scripts_dir.mkdir(parents=True, exist_ok=True)

            # Generate Linux script for elevated execution
            script_path = self.generate_linux_script(scripts_dir)

            # Save credentials for later use
            self.save_credentials()

            # Guide user through elevation
            self.display_elevation_guide(script_path)

            # Wait for user confirmation
            if not self.settings.get("batch"):
                input("\nPress Enter after running the script...")

                # Verify database was created
                if self.verify_database_exists():
                    result["success"] = True
                    result["credentials"] = {"owner_password": self.owner_password, "user_password": self.user_password}
                    result["credentials_file"] = str(self.credentials_file)
                    self.logger.info("Database verified after fallback script execution")
                else:
                    result["errors"].append("Database not found after script execution")
            else:
                # In batch mode, assume success but note manual step required
                result["success"] = True
                result["manual_step_required"] = True
                result["script_path"] = str(script_path)
                result["credentials_file"] = str(self.credentials_file)

            return result

        except Exception as e:
            result["errors"].append(str(e))
            self.logger.error(f"Fallback setup failed: {e}")
            return result

    def generate_linux_script(self, scripts_dir: Path) -> Path:
        """Generate Linux elevation script"""
        script_path = scripts_dir / "create_db.sh"

        script_content = f"""#!/bin/bash
# GiljoAI MCP Database Creation Script for Linux
# Generated: {datetime.now().isoformat()}
#
# INSTRUCTIONS:
# 1. Make sure you have the PostgreSQL admin password
# 2. Run this script with: bash create_db.sh
#    (On Linux, you may need: sudo bash create_db.sh)
#
# This script will:
# - Create PostgreSQL roles (giljo_owner, giljo_user)
# - Create the giljo_mcp database
# - Set up all required permissions
# - Save credentials for the installer

set -euo pipefail

echo ""
echo "====================================================================="
echo "   GiljoAI MCP - PostgreSQL Database Creation Script"
echo "====================================================================="
echo ""

# Configuration (pre-filled by installer)
PG_HOST="{self.host}"
PG_PORT={self.port}
PG_USER="{self.username}"
DB_NAME="{self.db_name}"
OWNER_ROLE="giljo_owner"
USER_ROLE="giljo_user"
OWNER_PASSWORD="{self.owner_password}"
USER_PASSWORD="{self.user_password}"

echo "Configuration:"
echo "  PostgreSQL Host: $PG_HOST"
echo "  PostgreSQL Port: $PG_PORT"
echo "  Database Name:   $DB_NAME"
echo ""

# Function to run psql command
run_psql() {{
    local database="${{1:-postgres}}"
    local command="$2"
    local ignore_error="${{3:-false}}"

    if [ "$ignore_error" = "true" ]; then
        PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$database" -c "$command" 2>/dev/null || true
    else
        PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$database" -c "$command"
    fi
}}

# Prompt for PostgreSQL admin password
echo "PostgreSQL Administration"
read -sp "Enter password for PostgreSQL user '$PG_USER': " POSTGRES_PASSWORD
echo ""
echo ""

echo "Testing PostgreSQL connection..."

if ! run_psql "postgres" "SELECT version();" "true" > /dev/null 2>&1; then
    echo "  ERROR: Cannot connect to PostgreSQL"
    echo ""
    echo "Please verify:"
    echo "  1. PostgreSQL is installed and running"
    echo "  2. The password is correct"
    echo "  3. PostgreSQL is accepting connections on port $PG_PORT"
    echo ""
    exit 1
fi

echo "  Connected successfully!"
echo ""

echo "Creating database roles..."

# Check if owner role exists
if run_psql "postgres" "SELECT 1 FROM pg_roles WHERE rolname='$OWNER_ROLE';" "true" | grep -q "1"; then
    echo "  Role '$OWNER_ROLE' exists, updating password..."
    run_psql "postgres" "ALTER ROLE $OWNER_ROLE WITH PASSWORD '$OWNER_PASSWORD';"
else
    echo "  Creating role '$OWNER_ROLE'..."
    run_psql "postgres" "CREATE ROLE $OWNER_ROLE LOGIN PASSWORD '$OWNER_PASSWORD';"
fi

# Check if user role exists
if run_psql "postgres" "SELECT 1 FROM pg_roles WHERE rolname='$USER_ROLE';" "true" | grep -q "1"; then
    echo "  Role '$USER_ROLE' exists, updating password..."
    run_psql "postgres" "ALTER ROLE $USER_ROLE WITH PASSWORD '$USER_PASSWORD';"
else
    echo "  Creating role '$USER_ROLE'..."
    run_psql "postgres" "CREATE ROLE $USER_ROLE LOGIN PASSWORD '$USER_PASSWORD';"
fi

echo "  Roles created successfully!"
echo ""

echo "Creating database..."

# Check if database exists
if run_psql "postgres" "SELECT 1 FROM pg_database WHERE datname='$DB_NAME';" "true" | grep -q "1"; then
    echo "  Database '$DB_NAME' already exists"
else
    echo "  Creating database '$DB_NAME'..."
    run_psql "postgres" "CREATE DATABASE $DB_NAME OWNER $OWNER_ROLE;"
    echo "  Database created successfully!"
fi

echo ""
echo "Setting up permissions..."

# Grant permissions (ignore errors if already granted)
run_psql "$DB_NAME" "GRANT CONNECT ON DATABASE $DB_NAME TO $USER_ROLE;" "true"
run_psql "$DB_NAME" "GRANT USAGE, CREATE ON SCHEMA public TO $OWNER_ROLE;" "true"
run_psql "$DB_NAME" "GRANT USAGE ON SCHEMA public TO $USER_ROLE;" "true"

# Grant default privileges
run_psql "$DB_NAME" "ALTER DEFAULT PRIVILEGES FOR ROLE $OWNER_ROLE IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO $USER_ROLE;" "true"
run_psql "$DB_NAME" "ALTER DEFAULT PRIVILEGES FOR ROLE $OWNER_ROLE IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO $USER_ROLE;" "true"

echo "  Permissions configured successfully!"
echo ""

# Clear password from environment
unset POSTGRES_PASSWORD

# Create verification flag for installer
echo "Creating verification flag..."
timestamp=$(date '+%Y-%m-%d %H:%M:%S')
echo "DATABASE_CREATED=$timestamp" > ../../database_created.flag

echo ""
echo "====================================================================="
echo "   Database Setup Complete!"
echo "====================================================================="
echo ""
echo "Database Details:"
echo "  Database: $DB_NAME"
echo "  Owner Role: $OWNER_ROLE"
echo "  User Role: $USER_ROLE"
echo ""
echo "Credentials have been saved to:"
echo "  Linux_Installer/credentials/db_credentials_*.txt"
echo ""
echo "You can now return to the installer and press Enter to continue."
echo ""
"""

        script_path.write_text(script_content, encoding="utf-8")
        script_path.chmod(0o755)
        self.logger.info(f"Generated Linux script: {script_path}")
        return script_path

    def display_elevation_guide(self, script_path: Path):
        """Display clear instructions for running elevation script"""
        print("\n" + "=" * 60)
        print("Database Setup Required")
        print("=" * 60)
        print()
        print("Administrative privileges are needed to create the database.")
        print("A script has been generated with all necessary commands.")
        print()

        print("Please run the following command:")
        print()
        resolved_path = script_path.resolve()
        try:
            display_path = resolved_path.relative_to(Path.cwd())
        except ValueError:
            display_path = resolved_path
        print(f"  sudo bash {display_path}")
        print()

        print()
        print("The script will:")
        print("  - Create the giljo_mcp database")
        print("  - Set up required roles and permissions")
        print("  - Save credentials securely")
        print()

    def verify_database_exists(self) -> bool:
        """Check if database was created successfully"""
        # First check for flag file
        flag_file = Path("database_created.flag")
        if flag_file.exists():
            self.logger.info("Database creation flag found")
            flag_file.unlink()  # Remove flag
            return True

        # Try to connect if psycopg2 available
        if psycopg2:
            try:
                conn = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    database=self.db_name,
                    user="giljo_user",
                    password=self.user_password,
                )
                conn.close()
                return True
            except:
                pass

        return False

    def create_default_admin_account(self) -> Dict[str, Any]:
        """
        Create default admin account on fresh install.

        Credentials:
        - Username: admin
        - Password: admin (bcrypt hashed)

        Sets default_password_active: true in setup state

        Returns:
            Dict with success status and admin user info
        """
        result = {"success": False, "errors": []}

        try:
            # Import bcrypt
            try:
                import bcrypt
            except ImportError:
                result["errors"].append("bcrypt not installed - cannot hash password")
                return result

            # Connect to giljo_mcp database
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.db_name,
                user="giljo_owner",
                password=self.owner_password,
                connect_timeout=10,
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

            with conn.cursor() as cur:
                # Check if admin user already exists (idempotent)
                cur.execute("SELECT 1 FROM users WHERE username = %s", ("admin",))
                if cur.fetchone():
                    self.logger.info("Admin user already exists, skipping creation")
                    result["success"] = True
                    result["already_exists"] = True
                    return result

                # Hash the default password 'admin'
                password_hash = bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode("utf-8")

                # Generate UUID for admin user
                import uuid

                admin_id = str(uuid.uuid4())

                # Create admin user
                cur.execute(
                    """
                    INSERT INTO users (
                        id, tenant_key, username, password_hash,
                        email, role, is_active, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, NOW()
                    )
                """,
                    (admin_id, "default", "admin", password_hash, "admin@localhost", "admin", True),
                )

                # Update setup state to mark default password as active
                cur.execute("""
                    UPDATE setup_state
                    SET default_password_active = true
                    WHERE tenant_key = 'default'
                """)

                # If no setup_state exists, create one
                if cur.rowcount == 0:
                    setup_id = str(uuid.uuid4())
                    cur.execute(
                        """
                        INSERT INTO setup_state (
                            id, tenant_key, completed, default_password_active,
                            setup_version, created_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, NOW()
                        )
                    """,
                        (setup_id, "default", False, True, "3.0.0"),
                    )

            conn.close()

            # Display credentials in terminal
            print("\n" + "=" * 60)
            print("Default Admin Credentials:")
            print("  Username: admin")
            print("  Password: admin")
            print("\n  IMPORTANT: Change this password on first login!")
            print("=" * 60 + "\n")

            self.logger.info("Default admin account created successfully")
            result["success"] = True
            result["username"] = "admin"
            return result

        except Exception as e:
            result["errors"].append(f"Failed to create admin account: {e!s}")
            self.logger.error(f"Admin account creation failed: {e}", exc_info=True)
            return result

    def save_credentials(self):
        """Save database credentials securely"""
        base_dir = Path(__file__).resolve().parent.parent
        credentials_dir = base_dir / "credentials"
        credentials_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.credentials_file = credentials_dir / f"db_credentials_{timestamp}.txt"

        content = f"""# GiljoAI MCP Database Credentials
# Generated: {datetime.now().isoformat()}
# KEEP THIS FILE SECURE!

DATABASE_NAME={self.db_name}
DATABASE_HOST={self.host}
DATABASE_PORT={self.port}

OWNER_ROLE=giljo_owner
OWNER_PASSWORD={self.owner_password}

USER_ROLE=giljo_user
USER_PASSWORD={self.user_password}

# Connection strings:
OWNER_URL=postgresql://giljo_owner:{self.owner_password}@{self.host}:{self.port}/{self.db_name}
USER_URL=postgresql://giljo_user:{self.user_password}@{self.host}:{self.port}/{self.db_name}
"""

        self.credentials_file.write_text(content)

        # Set restrictive permissions for Linux environments
        os.chmod(self.credentials_file, 0o600)

        self.logger.info(f"Credentials saved to: {self.credentials_file}")

    def generate_password(self, length: int = 20) -> str:
        """Generate a secure random password"""
        alphabet = string.ascii_letters + string.digits
        # Avoid special characters that might cause issues in connection strings
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        return password

    def get_postgresql_install_guide(self) -> str:
        """Return Ubuntu-optimized PostgreSQL installation guide"""

        # Detect Ubuntu for specific instructions
        ubuntu_specific = ""
        try:
            dist_info = platform.freedesktop_os_release()
            if dist_info.get("ID") == "ubuntu":
                ubuntu_version = dist_info.get("VERSION_ID", "")
                ubuntu_specific = f"""
Ubuntu {ubuntu_version} Specific Instructions:

Method 1 - Official PostgreSQL Repository (Recommended):
  # Add PostgreSQL official APT repository
  wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
  echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" | sudo tee /etc/apt/sources.list.d/pgdg.list
  sudo apt update
  sudo apt install postgresql-18 postgresql-client-18 postgresql-contrib-18
  sudo systemctl enable --now postgresql
  # Set password for postgres user
  sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'your_password';"

Method 2 - Ubuntu Default Repository:
  sudo apt update
  sudo apt install postgresql postgresql-contrib
  sudo systemctl enable --now postgresql
  # Set password for postgres user
  sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'your_password';"

Ubuntu Tips:
  • Check status: sudo systemctl status postgresql
  • View logs: sudo journalctl -u postgresql
  • Default data directory: /var/lib/postgresql/
  • Configuration files: /etc/postgresql/*/main/
"""
        except:
            pass

        return f"""
PostgreSQL Installation Guide for Linux:
{ubuntu_specific}
General Linux Instructions:

Ubuntu/Debian:
  sudo apt update
  sudo apt install postgresql-18 postgresql-client-18
  sudo systemctl enable --now postgresql

RHEL/CentOS/Fedora:
  sudo dnf install postgresql18-server postgresql18
  sudo /usr/pgsql-18/bin/postgresql-18-setup initdb
  sudo systemctl enable --now postgresql-18

Arch:
  sudo pacman -S postgresql
  sudo -u postgres initdb -D /var/lib/postgres/data
  sudo systemctl enable --now postgresql

Docker Alternative (Development Only):
  # Install Docker
  sudo apt update && sudo apt install docker.io
  sudo systemctl enable --now docker
  # Run PostgreSQL 18
  sudo docker run --name giljo-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:18

Post-Installation (All Distributions):
  • Set postgres user password (REQUIRED)
  • Verify service is running: sudo systemctl status postgresql
  • Test connection: psql -h localhost -U postgres -d postgres
"""

    def run_migrations(self, alembic_ini_path: Optional[Path] = None) -> Dict[str, Any]:
        """Run Alembic migrations to initialize/update database schema"""
        result = {"success": False, "errors": [], "warnings": []}

        try:
            # Try to import alembic
            try:
                from alembic import command
                from alembic.config import Config
            except ImportError:
                result["errors"].append("Alembic not installed - cannot run migrations")
                self.logger.warning("Alembic not available for migrations")
                return result

            # Find alembic.ini
            if alembic_ini_path is None:
                # Look for alembic.ini in current directory or parent directories
                search_paths = [
                    Path.cwd() / "alembic.ini",
                    Path.cwd().parent / "alembic.ini",
                    Path.cwd().parent.parent / "alembic.ini",
                ]
                for path in search_paths:
                    if path.exists():
                        alembic_ini_path = path
                        break

            if alembic_ini_path is None or not alembic_ini_path.exists():
                result["warnings"].append("alembic.ini not found - skipping migrations")
                self.logger.warning("No alembic.ini found, skipping migrations")
                result["success"] = True  # Not an error, just skip
                return result

            self.logger.info(f"Running migrations using {alembic_ini_path}")

            # Configure Alembic
            alembic_cfg = Config(str(alembic_ini_path))

            # Set the database URL (use owner credentials for migrations)
            db_url = f"postgresql://{self.settings.get('pg_user', 'giljo_owner')}:{self.owner_password}@{self.host}:{self.port}/{self.db_name}"
            alembic_cfg.set_main_option("sqlalchemy.url", db_url)

            # Run migrations to head
            self.logger.info("Upgrading database schema to latest version...")
            command.upgrade(alembic_cfg, "head")

            self.logger.info("Migrations completed successfully")
            result["success"] = True
            return result

        except Exception as e:
            result["errors"].append(f"Migration failed: {e!s}")
            self.logger.error(f"Failed to run migrations: {e}", exc_info=True)
            return result


def check_postgresql_connection(host: str, port: int, timeout: int = 5) -> bool:
    """Check if PostgreSQL is accessible on given host:port"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def detect_postgresql_cli() -> Optional[str]:
    """Detect if psql is available in PATH"""
    try:
        result = subprocess.run(["psql", "--version"], check=False, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return None
