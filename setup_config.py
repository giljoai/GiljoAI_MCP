#!/usr/bin/env python3
"""
Configuration Management for GiljoAI MCP Setup
Handles import/export of configurations, profiles, and backup/restore
"""

import json
import yaml
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import shutil
import hashlib
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class ConfigurationManager:
    """Manages configuration import/export with encryption support"""
    
    def __init__(self, root_path: Optional[Path] = None):
        self.root_path = root_path or Path.cwd()
        self.config_dir = self.root_path / '.giljo-config'
        self.profiles_dir = self.config_dir / 'profiles'
        self.backups_dir = self.config_dir / 'backups'
        self.current_profile = None
        self.encryption_key = None
        
        # Create directories
        self.config_dir.mkdir(exist_ok=True)
        self.profiles_dir.mkdir(exist_ok=True)
        self.backups_dir.mkdir(exist_ok=True)
    
    def load_env_config(self, env_path: Optional[Path] = None) -> Dict[str, str]:
        """Load configuration from .env file"""
        if not env_path:
            env_path = self.root_path / '.env'
        
        config = {}
        
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        # Remove quotes
                        value = value.strip().strip('"\'')
                        config[key.strip()] = value
        
        return config
    
    def load_yaml_config(self, yaml_path: Optional[Path] = None) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not yaml_path:
            yaml_path = self.root_path / 'config.yaml'
        
        if yaml_path.exists():
            with open(yaml_path, 'r') as f:
                return yaml.safe_load(f) or {}
        
        return {}
    
    def export_config(self, 
                     output_path: Optional[Path] = None,
                     format: str = 'json',
                     include_secrets: bool = False,
                     encrypt: bool = False,
                     password: Optional[str] = None) -> Path:
        """Export current configuration"""
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"giljo_config_{timestamp}.{format}"
            output_path = self.config_dir / filename
        
        # Gather all configuration
        config = {
            'metadata': {
                'exported_at': datetime.now().isoformat(),
                'version': '1.0.0',
                'encrypted': encrypt,
                'format': format
            },
            'environment': self.load_env_config(),
            'yaml_config': self.load_yaml_config()
        }
        
        # Remove secrets if requested
        if not include_secrets:
            config['environment'] = self._sanitize_secrets(config['environment'])
        
        # Encrypt if requested
        if encrypt:
            if not password:
                password = self._prompt_password("Enter encryption password: ")
            config = self._encrypt_config(config, password)
        
        # Export based on format
        if format == 'json':
            with open(output_path, 'w') as f:
                json.dump(config, f, indent=2, default=str)
        elif format == 'yaml':
            with open(output_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        print(f"Configuration exported to: {output_path}")
        return output_path
    
    def import_config(self,
                     import_path: Path,
                     merge: bool = False,
                     password: Optional[str] = None) -> bool:
        """Import configuration from file"""
        if not import_path.exists():
            print(f"Error: Configuration file not found: {import_path}")
            return False
        
        try:
            # Detect format
            if import_path.suffix == '.json':
                with open(import_path, 'r') as f:
                    config = json.load(f)
            elif import_path.suffix in ['.yaml', '.yml']:
                with open(import_path, 'r') as f:
                    config = yaml.safe_load(f)
            else:
                print(f"Error: Unsupported file format: {import_path.suffix}")
                return False
            
            # Decrypt if needed
            if config.get('metadata', {}).get('encrypted'):
                if not password:
                    password = self._prompt_password("Enter decryption password: ")
                config = self._decrypt_config(config, password)
            
            # Backup current config
            self.backup_config()
            
            # Apply configuration
            if merge:
                self._merge_config(config)
            else:
                self._apply_config(config)
            
            print(f"Configuration imported from: {import_path}")
            return True
            
        except Exception as e:
            print(f"Error importing configuration: {e}")
            return False
    
    def create_profile(self, 
                      name: str,
                      description: Optional[str] = None) -> bool:
        """Create a new configuration profile"""
        profile_dir = self.profiles_dir / name
        
        if profile_dir.exists():
            print(f"Profile '{name}' already exists")
            return False
        
        profile_dir.mkdir()
        
        # Copy current configuration
        current_env = self.root_path / '.env'
        current_yaml = self.root_path / 'config.yaml'
        
        if current_env.exists():
            shutil.copy2(current_env, profile_dir / '.env')
        
        if current_yaml.exists():
            shutil.copy2(current_yaml, profile_dir / 'config.yaml')
        
        # Create profile metadata
        metadata = {
            'name': name,
            'description': description or f"Profile created at {datetime.now().isoformat()}",
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        with open(profile_dir / 'profile.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Profile '{name}' created")
        return True
    
    def list_profiles(self) -> List[Dict]:
        """List all available profiles"""
        profiles = []
        
        for profile_dir in self.profiles_dir.iterdir():
            if profile_dir.is_dir():
                metadata_file = profile_dir / 'profile.json'
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                        profiles.append(metadata)
                else:
                    profiles.append({
                        'name': profile_dir.name,
                        'description': 'No metadata'
                    })
        
        return profiles
    
    def switch_profile(self, name: str) -> bool:
        """Switch to a different configuration profile"""
        profile_dir = self.profiles_dir / name
        
        if not profile_dir.exists():
            print(f"Profile '{name}' not found")
            return False
        
        # Backup current configuration
        self.backup_config()
        
        # Apply profile configuration
        profile_env = profile_dir / '.env'
        profile_yaml = profile_dir / 'config.yaml'
        
        if profile_env.exists():
            shutil.copy2(profile_env, self.root_path / '.env')
        
        if profile_yaml.exists():
            shutil.copy2(profile_yaml, self.root_path / 'config.yaml')
        
        self.current_profile = name
        print(f"Switched to profile: {name}")
        return True
    
    def delete_profile(self, name: str) -> bool:
        """Delete a configuration profile"""
        profile_dir = self.profiles_dir / name
        
        if not profile_dir.exists():
            print(f"Profile '{name}' not found")
            return False
        
        if self.current_profile == name:
            print(f"Cannot delete active profile '{name}'")
            return False
        
        shutil.rmtree(profile_dir)
        print(f"Profile '{name}' deleted")
        return True
    
    def backup_config(self, name: Optional[str] = None) -> Path:
        """Create a backup of current configuration"""
        if not name:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            name = f"backup_{timestamp}"
        
        backup_dir = self.backups_dir / name
        backup_dir.mkdir()
        
        # Copy configuration files
        files_to_backup = [
            '.env',
            'config.yaml',
            'requirements.txt',
            'docker-compose.yml',
            'Dockerfile'
        ]
        
        for file in files_to_backup:
            source = self.root_path / file
            if source.exists():
                shutil.copy2(source, backup_dir / file)
        
        # Create backup metadata
        metadata = {
            'name': name,
            'created_at': datetime.now().isoformat(),
            'profile': self.current_profile,
            'files': [f for f in files_to_backup if (self.root_path / f).exists()]
        }
        
        with open(backup_dir / 'backup.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Backup created: {backup_dir}")
        return backup_dir
    
    def list_backups(self) -> List[Dict]:
        """List all available backups"""
        backups = []
        
        for backup_dir in self.backups_dir.iterdir():
            if backup_dir.is_dir():
                metadata_file = backup_dir / 'backup.json'
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                        backups.append(metadata)
        
        # Sort by creation date
        backups.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return backups
    
    def restore_backup(self, name: str) -> bool:
        """Restore configuration from backup"""
        backup_dir = self.backups_dir / name
        
        if not backup_dir.exists():
            print(f"Backup '{name}' not found")
            return False
        
        # Create current backup first
        self.backup_config(f"before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        # Restore files
        metadata_file = backup_dir / 'backup.json'
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                files = metadata.get('files', [])
        else:
            files = [f.name for f in backup_dir.iterdir() if f.is_file() and f.name != 'backup.json']
        
        for file in files:
            source = backup_dir / file
            if source.exists():
                shutil.copy2(source, self.root_path / file)
                print(f"  Restored: {file}")
        
        print(f"Configuration restored from backup: {name}")
        return True
    
    def validate_config(self, config: Dict) -> Tuple[bool, List[str]]:
        """Validate configuration values"""
        issues = []
        
        env_config = config.get('environment', {})
        
        # Check required keys
        required_keys = [
            'DATABASE_URL',
            'GILJO_MCP_MODE'
        ]
        
        for key in required_keys:
            if key not in env_config:
                issues.append(f"Missing required key: {key}")
        
        # Validate database URL
        db_url = env_config.get('DATABASE_URL', '')
        if db_url:
            if not (db_url.startswith('sqlite://') or 
                   db_url.startswith('postgresql://')):
                issues.append("Invalid DATABASE_URL format")
        
        # Validate ports
        port_keys = [
            'GILJO_MCP_DASHBOARD_PORT',
            'GILJO_MCP_SERVER_PORT',
            'GILJO_MCP_API_PORT',
            'GILJO_MCP_WEBSOCKET_PORT'
        ]
        
        for key in port_keys:
            if key in env_config:
                try:
                    port = int(env_config[key])
                    if port < 1024 or port > 65535:
                        issues.append(f"{key}: Port must be between 1024 and 65535")
                except ValueError:
                    issues.append(f"{key}: Invalid port number")
        
        # Validate mode
        mode = env_config.get('GILJO_MCP_MODE', '')
        valid_modes = ['local', 'development', 'production', 'lan', 'wan']
        if mode and mode not in valid_modes:
            issues.append(f"Invalid mode: {mode}. Must be one of {valid_modes}")
        
        valid = len(issues) == 0
        return valid, issues
    
    def _sanitize_secrets(self, config: Dict) -> Dict:
        """Remove or mask sensitive values"""
        sanitized = config.copy()
        
        secret_keys = [
            'PASSWORD', 'SECRET', 'KEY', 'TOKEN', 'API_KEY',
            'JWT', 'CREDENTIAL', 'AUTH'
        ]
        
        for key in list(sanitized.keys()):
            # Check if key contains secret keywords
            if any(secret in key.upper() for secret in secret_keys):
                value = sanitized[key]
                if value and len(value) > 4:
                    # Mask all but first 2 and last 2 characters
                    sanitized[key] = value[:2] + '*' * (len(value) - 4) + value[-2:]
                else:
                    sanitized[key] = '***'
        
        return sanitized
    
    def _encrypt_config(self, config: Dict, password: str) -> Dict:
        """Encrypt configuration data"""
        # Generate key from password
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        # Encrypt data
        fernet = Fernet(key)
        data = json.dumps(config).encode()
        encrypted = fernet.encrypt(data)
        
        return {
            'encrypted': True,
            'salt': base64.b64encode(salt).decode(),
            'data': base64.b64encode(encrypted).decode()
        }
    
    def _decrypt_config(self, encrypted_config: Dict, password: str) -> Dict:
        """Decrypt configuration data"""
        salt = base64.b64decode(encrypted_config['salt'])
        
        # Regenerate key from password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        # Decrypt data
        fernet = Fernet(key)
        encrypted = base64.b64decode(encrypted_config['data'])
        decrypted = fernet.decrypt(encrypted)
        
        return json.loads(decrypted.decode())
    
    def _apply_config(self, config: Dict):
        """Apply imported configuration"""
        # Write environment variables
        env_config = config.get('environment', {})
        if env_config:
            env_path = self.root_path / '.env'
            with open(env_path, 'w') as f:
                for key, value in env_config.items():
                    f.write(f"{key}={value}\n")
        
        # Write YAML config
        yaml_config = config.get('yaml_config', {})
        if yaml_config:
            yaml_path = self.root_path / 'config.yaml'
            with open(yaml_path, 'w') as f:
                yaml.dump(yaml_config, f, default_flow_style=False)
    
    def _merge_config(self, config: Dict):
        """Merge imported configuration with existing"""
        # Load current config
        current_env = self.load_env_config()
        current_yaml = self.load_yaml_config()
        
        # Merge environment
        new_env = config.get('environment', {})
        current_env.update(new_env)
        
        # Merge YAML (deep merge would be better)
        new_yaml = config.get('yaml_config', {})
        current_yaml.update(new_yaml)
        
        # Apply merged config
        self._apply_config({
            'environment': current_env,
            'yaml_config': current_yaml
        })
    
    def _prompt_password(self, prompt: str) -> str:
        """Prompt for password securely"""
        import getpass
        return getpass.getpass(prompt)
    
    def generate_config_template(self, 
                                output_path: Optional[Path] = None,
                                environment: str = 'development') -> Path:
        """Generate a configuration template"""
        if not output_path:
            output_path = self.config_dir / f"template_{environment}.yaml"
        
        template = {
            'metadata': {
                'environment': environment,
                'generated_at': datetime.now().isoformat(),
                'description': f'Configuration template for {environment} environment'
            },
            'database': {
                'type': 'sqlite' if environment == 'development' else 'postgresql',
                'sqlite': {
                    'path': 'data/giljo_mcp.db'
                },
                'postgresql': {
                    'host': 'localhost',
                    'port': 5432,
                    'database': 'giljo_mcp',
                    'user': 'postgres',
                    'password': ''
                }
            },
            'server': {
                'mode': environment,
                'ports': {
                    'dashboard': 6000,
                    'server': 6001,
                    'api': 6002,
                    'websocket': 6003
                },
                'host': '0.0.0.0' if environment == 'production' else '127.0.0.1'
            },
            'security': {
                'api_key_enabled': environment == 'production',
                'api_key': '',
                'jwt_secret': '',
                'cors_enabled': True,
                'cors_origins': ['http://localhost:*']
            },
            'logging': {
                'level': 'DEBUG' if environment == 'development' else 'INFO',
                'file': 'logs/giljo_mcp.log',
                'max_size': '100MB',
                'backup_count': 5
            },
            'features': {
                'hot_reload': environment == 'development',
                'debug': environment == 'development',
                'telemetry': False
            }
        }
        
        with open(output_path, 'w') as f:
            yaml.dump(template, f, default_flow_style=False, sort_keys=False)
        
        print(f"Configuration template generated: {output_path}")
        return output_path


def main():
    """CLI interface for configuration management"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GiljoAI MCP Configuration Manager')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export configuration')
    export_parser.add_argument('--output', type=Path, help='Output file path')
    export_parser.add_argument('--format', choices=['json', 'yaml'], default='json')
    export_parser.add_argument('--include-secrets', action='store_true')
    export_parser.add_argument('--encrypt', action='store_true')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import configuration')
    import_parser.add_argument('file', type=Path, help='Configuration file to import')
    import_parser.add_argument('--merge', action='store_true', help='Merge with existing')
    
    # Profile commands
    profile_parser = subparsers.add_parser('profile', help='Manage profiles')
    profile_sub = profile_parser.add_subparsers(dest='profile_cmd')
    
    profile_sub.add_parser('list', help='List profiles')
    
    create_profile = profile_sub.add_parser('create', help='Create profile')
    create_profile.add_argument('name', help='Profile name')
    create_profile.add_argument('--description', help='Profile description')
    
    switch_profile = profile_sub.add_parser('switch', help='Switch profile')
    switch_profile.add_argument('name', help='Profile name')
    
    delete_profile = profile_sub.add_parser('delete', help='Delete profile')
    delete_profile.add_argument('name', help='Profile name')
    
    # Backup commands
    backup_parser = subparsers.add_parser('backup', help='Manage backups')
    backup_sub = backup_parser.add_subparsers(dest='backup_cmd')
    
    backup_sub.add_parser('create', help='Create backup')
    backup_sub.add_parser('list', help='List backups')
    
    restore_backup = backup_sub.add_parser('restore', help='Restore backup')
    restore_backup.add_argument('name', help='Backup name')
    
    # Template command
    template_parser = subparsers.add_parser('template', help='Generate config template')
    template_parser.add_argument('--env', choices=['development', 'production', 'test'],
                                default='development')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate configuration')
    validate_parser.add_argument('file', type=Path, nargs='?', help='Config file to validate')
    
    args = parser.parse_args()
    
    manager = ConfigurationManager()
    
    if args.command == 'export':
        manager.export_config(
            output_path=args.output,
            format=args.format,
            include_secrets=args.include_secrets,
            encrypt=args.encrypt
        )
    
    elif args.command == 'import':
        manager.import_config(args.file, merge=args.merge)
    
    elif args.command == 'profile':
        if args.profile_cmd == 'list':
            profiles = manager.list_profiles()
            for p in profiles:
                print(f"- {p['name']}: {p.get('description', 'No description')}")
        elif args.profile_cmd == 'create':
            manager.create_profile(args.name, args.description)
        elif args.profile_cmd == 'switch':
            manager.switch_profile(args.name)
        elif args.profile_cmd == 'delete':
            manager.delete_profile(args.name)
    
    elif args.command == 'backup':
        if args.backup_cmd == 'create':
            manager.backup_config()
        elif args.backup_cmd == 'list':
            backups = manager.list_backups()
            for b in backups:
                print(f"- {b['name']}: {b['created_at']}")
        elif args.backup_cmd == 'restore':
            manager.restore_backup(args.name)
    
    elif args.command == 'template':
        manager.generate_config_template(environment=args.env)
    
    elif args.command == 'validate':
        if args.file:
            # Validate specific file
            if args.file.suffix == '.json':
                with open(args.file, 'r') as f:
                    config = json.load(f)
            else:
                with open(args.file, 'r') as f:
                    config = yaml.safe_load(f)
        else:
            # Validate current config
            config = {
                'environment': manager.load_env_config(),
                'yaml_config': manager.load_yaml_config()
            }
        
        valid, issues = manager.validate_config(config)
        if valid:
            print("✓ Configuration is valid")
        else:
            print("✗ Configuration has issues:")
            for issue in issues:
                print(f"  - {issue}")


if __name__ == "__main__":
    # Check for required dependencies
    try:
        import yaml
    except ImportError:
        print("Error: pyyaml not installed. Run: pip install pyyaml")
        sys.exit(1)
    
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        print("Note: cryptography not installed. Encryption features disabled.")
        print("To enable: pip install cryptography")
    
    main()