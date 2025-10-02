"""
Security module for server mode
Handles API key generation, admin user creation, and authentication setup
"""

import os
import secrets
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class SecurityManager:
    """Manage security configuration for server mode"""

    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self.mode = settings.get('mode', 'localhost')
        self.logger = logging.getLogger(self.__class__.__name__)

    def configure(self) -> Dict[str, Any]:
        """Main security configuration workflow"""
        result = {'success': False, 'errors': []}

        try:
            # Server mode requires additional security
            if self.mode == 'server':
                # Generate admin user credentials if not provided
                if self.settings.get('admin_username'):
                    admin_result = self.create_admin_user()
                    if not admin_result['success']:
                        result['errors'].extend(admin_result.get('errors', []))
                        return result

                    result['admin_user'] = admin_result.get('username')

                # Generate API keys if enabled
                if self.settings.get('generate_api_key', False):
                    api_result = self.generate_api_key()
                    if not api_result['success']:
                        result['errors'].extend(api_result.get('errors', []))
                        return result

                    result['api_key'] = api_result.get('key')
                    result['api_key_file'] = api_result.get('key_file')

            result['success'] = True
            self.logger.info("Security configuration completed successfully")
            return result

        except Exception as e:
            result['errors'].append(str(e))
            self.logger.error(f"Security configuration failed: {e}")
            return result

    def create_admin_user(self) -> Dict[str, Any]:
        """Create admin user with hashed password"""
        result = {'success': False, 'errors': []}

        try:
            username = self.settings.get('admin_username', 'admin')
            password = self.settings.get('admin_password')

            if not password:
                result['errors'].append("Admin password is required for server mode")
                return result

            # Hash password
            password_hash = self.hash_password(password)

            # Store admin credentials
            admin_data = {
                'username': username,
                'password_hash': password_hash,
                'created_at': datetime.now().isoformat(),
                'role': 'admin'
            }

            # Save to credentials file
            creds_file = Path('.admin_credentials')
            import json
            with open(creds_file, 'w') as f:
                json.dump(admin_data, f, indent=2)

            # Secure file permissions
            if os.name != 'nt':  # Unix-like systems
                os.chmod(creds_file, 0o600)

            result['success'] = True
            result['username'] = username
            result['credentials_file'] = str(creds_file.absolute())

            self.logger.info(f"Admin user created: {username}")
            return result

        except Exception as e:
            result['errors'].append(str(e))
            self.logger.error(f"Admin user creation failed: {e}")
            return result

    def generate_api_key(self) -> Dict[str, Any]:
        """Generate secure API key for programmatic access"""
        result = {'success': False, 'errors': []}

        try:
            # Generate secure random API key
            key = f"gai_{secrets.token_urlsafe(32)}"

            # Create API keys file
            keys_file = Path('api_keys.json')
            import json

            # Load existing keys if file exists
            if keys_file.exists():
                with open(keys_file, 'r') as f:
                    keys_data = json.load(f)
            else:
                keys_data = {'keys': []}

            # Add new key
            key_entry = {
                'key': key,
                'name': self.settings.get('api_key_name', 'default'),
                'created_at': datetime.now().isoformat(),
                'created_by': self.settings.get('admin_username', 'admin'),
                'permissions': ['read', 'write'],
                'active': True
            }

            keys_data['keys'].append(key_entry)

            # Save keys file
            with open(keys_file, 'w') as f:
                json.dump(keys_data, f, indent=2)

            # Secure file permissions
            if os.name != 'nt':
                os.chmod(keys_file, 0o600)

            result['success'] = True
            result['key'] = key
            result['key_file'] = str(keys_file.absolute())

            self.logger.info("API key generated successfully")
            return result

        except Exception as e:
            result['errors'].append(str(e))
            self.logger.error(f"API key generation failed: {e}")
            return result

    def hash_password(self, password: str) -> str:
        """Hash password using PBKDF2-SHA256"""
        # Generate salt
        salt = secrets.token_bytes(32)

        # Hash password with salt using PBKDF2
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000  # iterations
        )

        # Combine salt and key
        import base64
        hash_str = base64.b64encode(salt + key).decode('utf-8')

        return hash_str

    def verify_password(self, password: str, hash_str: str) -> bool:
        """Verify password against hash"""
        try:
            import base64
            # Decode hash
            hash_bytes = base64.b64decode(hash_str.encode('utf-8'))

            # Extract salt and key
            salt = hash_bytes[:32]
            stored_key = hash_bytes[32:]

            # Hash provided password with stored salt
            key = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt,
                100000
            )

            # Compare
            return key == stored_key

        except Exception:
            return False

    def generate_session_secret(self) -> str:
        """Generate secure session secret"""
        return secrets.token_urlsafe(64)

    def generate_jwt_secret(self) -> str:
        """Generate JWT signing secret"""
        return secrets.token_urlsafe(64)

    def setup_authentication(self) -> Dict[str, Any]:
        """Configure authentication settings"""
        result = {'success': False, 'errors': []}

        try:
            auth_config = {
                'session_secret': self.generate_session_secret(),
                'jwt_secret': self.generate_jwt_secret(),
                'token_expiry_hours': 24,
                'refresh_token_expiry_days': 30,
                'password_min_length': 8,
                'require_api_key': self.settings.get('features', {}).get('api_keys', False),
                'multi_user_enabled': self.settings.get('features', {}).get('multi_user', False)
            }

            # Save auth configuration
            import json
            auth_file = Path('.auth_config.json')
            with open(auth_file, 'w') as f:
                json.dump(auth_config, f, indent=2)

            # Secure file permissions
            if os.name != 'nt':
                os.chmod(auth_file, 0o600)

            result['success'] = True
            result['auth_config'] = auth_config
            result['auth_file'] = str(auth_file.absolute())

            self.logger.info("Authentication configuration completed")
            return result

        except Exception as e:
            result['errors'].append(str(e))
            self.logger.error(f"Authentication setup failed: {e}")
            return result

    def generate_firewall_rules(self) -> Dict[str, Any]:
        """Generate firewall configuration helper scripts"""
        result = {'success': False, 'errors': []}

        try:
            from .firewall import FirewallHelper

            firewall = FirewallHelper(self.settings)
            firewall_result = firewall.generate_rules()

            if not firewall_result['success']:
                result['errors'].extend(firewall_result.get('errors', []))
                return result

            result['success'] = True
            result['firewall_scripts'] = firewall_result.get('scripts', [])

            return result

        except ImportError:
            # Firewall helper not available, generate inline
            result['success'] = True
            result['firewall_scripts'] = []
            self.logger.warning("Firewall helper not available")
            return result
        except Exception as e:
            result['errors'].append(str(e))
            self.logger.error(f"Firewall rule generation failed: {e}")
            return result


class APIKeyManager:
    """Manage API keys for programmatic access"""

    def __init__(self, keys_file: Path = Path('api_keys.json')):
        self.keys_file = keys_file
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate_key(self, name: str = 'default', permissions: list = None) -> str:
        """Generate a new API key"""
        if permissions is None:
            permissions = ['read', 'write']

        key = f"gai_{secrets.token_urlsafe(32)}"

        # Load existing keys
        import json
        if self.keys_file.exists():
            with open(self.keys_file, 'r') as f:
                data = json.load(f)
        else:
            data = {'keys': []}

        # Add new key
        data['keys'].append({
            'key': key,
            'name': name,
            'created_at': datetime.now().isoformat(),
            'permissions': permissions,
            'active': True
        })

        # Save
        with open(self.keys_file, 'w') as f:
            json.dump(data, f, indent=2)

        # Secure permissions
        if os.name != 'nt':
            os.chmod(self.keys_file, 0o600)

        return key

    def validate_key(self, key: str) -> bool:
        """Validate an API key"""
        import json
        if not self.keys_file.exists():
            return False

        with open(self.keys_file, 'r') as f:
            data = json.load(f)

        for key_entry in data.get('keys', []):
            if key_entry['key'] == key and key_entry.get('active', True):
                return True

        return False

    def revoke_key(self, key: str) -> bool:
        """Revoke an API key"""
        import json
        if not self.keys_file.exists():
            return False

        with open(self.keys_file, 'r') as f:
            data = json.load(f)

        for key_entry in data.get('keys', []):
            if key_entry['key'] == key:
                key_entry['active'] = False
                key_entry['revoked_at'] = datetime.now().isoformat()

                with open(self.keys_file, 'w') as f:
                    json.dump(data, f, indent=2)

                return True

        return False

    def list_keys(self) -> list:
        """List all API keys"""
        import json
        if not self.keys_file.exists():
            return []

        with open(self.keys_file, 'r') as f:
            data = json.load(f)

        return data.get('keys', [])


def generate_secure_token(length: int = 32) -> str:
    """Generate a secure random token"""
    return secrets.token_urlsafe(length)


def generate_api_key_prefix(prefix: str = "gai") -> str:
    """Generate API key with custom prefix"""
    return f"{prefix}_{secrets.token_urlsafe(32)}"
