"""
Configuration management for GiljoAI MCP.

Handles environment variables, config files, and database settings.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field
import yaml


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    
    Environment variables override config file values.
    """
    
    # Application
    app_name: str = Field(default="GiljoAI MCP Coding Orchestrator")
    app_version: str = Field(default="0.1.0")
    debug: bool = Field(default=False)
    
    # Database
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    database_type: str = Field(default="sqlite", env="DB_TYPE")  # sqlite or postgresql
    
    # PostgreSQL specific (used if database_type == "postgresql")
    db_host: str = Field(default="localhost", env="DB_HOST")
    db_port: int = Field(default=5432, env="DB_PORT")
    db_name: str = Field(default="giljo_mcp", env="DB_NAME")
    db_user: str = Field(default="postgres", env="DB_USER")
    db_password: str = Field(default="", env="DB_PASSWORD")
    
    # Paths (OS-neutral using pathlib)
    data_dir: Path = Field(default_factory=lambda: Path.home() / ".giljo-mcp" / "data")
    config_dir: Path = Field(default_factory=lambda: Path.home() / ".giljo-mcp" / "config")
    log_dir: Path = Field(default_factory=lambda: Path.home() / ".giljo-mcp" / "logs")
    
    # API Settings
    api_host: str = Field(default="127.0.0.1", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_key: Optional[str] = Field(default=None, env="API_KEY")
    
    # MCP Settings
    mcp_server_name: str = Field(default="giljo-mcp")
    mcp_max_context: int = Field(default=150000)
    
    # Multi-tenant Settings
    enable_multi_tenant: bool = Field(default=True)
    default_tenant_key: Optional[str] = Field(default=None)
    
    # Vision Document Settings
    vision_chunk_size: int = Field(default=50000)  # tokens
    vision_overlap: int = Field(default=500)  # token overlap between chunks
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def get_database_url(self) -> str:
        """
        Get the database URL, building it from components if needed.
        
        Returns:
            Database connection URL
        """
        if self.database_url:
            return self.database_url
        
        if self.database_type == "postgresql":
            from giljo_mcp.database import DatabaseManager
            return DatabaseManager.build_postgresql_url(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                username=self.db_user,
                password=self.db_password
            )
        else:
            # Default to SQLite
            db_path = self.data_dir / "giljo_mcp.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{db_path}"
    
    def ensure_directories(self):
        """Create required directories if they don't exist."""
        for dir_path in [self.data_dir, self.config_dir, self.log_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def load_config_file(self, config_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to config file. If None, uses default.
            
        Returns:
            Configuration dictionary
        """
        if config_path is None:
            config_path = self.config_dir / "config.yaml"
        
        if not config_path.exists():
            return {}
        
        with open(config_path, "r") as f:
            return yaml.safe_load(f) or {}
    
    def save_config_file(self, config: Dict[str, Any], config_path: Optional[Path] = None):
        """
        Save configuration to YAML file.
        
        Args:
            config: Configuration dictionary to save
            config_path: Path to config file. If None, uses default.
        """
        if config_path is None:
            config_path = self.config_dir / "config.yaml"
        
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=True)


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the global settings instance.
    
    Returns:
        Settings instance
    """
    global _settings
    
    if _settings is None:
        _settings = Settings()
        _settings.ensure_directories()
    
    return _settings


def set_settings(settings: Settings):
    """Set the global settings instance."""
    global _settings
    _settings = settings