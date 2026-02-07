"""
Temporary script to create organization tables.
Handover 0424a - Organization Database Schema
"""

import sys
from pathlib import Path

import yaml


# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.giljo_mcp.database import DatabaseManager


# Load config from config.yaml
config_path = Path(__file__).parent / "config.yaml"
if not config_path.exists():
    print("ERROR: config.yaml not found")
    sys.exit(1)

config = yaml.safe_load(config_path.read_text())
db_config = config.get("database", {})

# Build database URL
# Use postgres superuser with password 4010
database_url = f"postgresql://postgres:***@{db_config['host']}:{db_config['port']}/{db_config['name']}"

# Create database manager
db_manager = DatabaseManager(database_url=database_url, is_async=False)

# Create tables
print("Creating organization tables...")
db_manager.create_tables()
print("Organization tables created successfully!")
