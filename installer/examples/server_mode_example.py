#!/usr/bin/env python3
"""
GiljoAI MCP Server Mode Installation Example
Demonstrates Phase 2 network engineering features
"""

import sys
from pathlib import Path

# Add installer to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from installer.core import (
    ServerInstaller,
    NetworkManager,
    FirewallManager,
    SecurityManager,
    detect_network_conflicts
)


def example_server_installation():
    """Complete server mode installation example"""

    print("=" * 70)
    print("  GiljoAI MCP Server Mode Installation Example")
    print("=" * 70)
    print()

    # Configuration settings
    settings = {
        'mode': 'server',
        'bind': '0.0.0.0',  # Network exposure
        'api_port': 8000,
        'ws_port': 8001,
        'dashboard_port': 3000,
        'pg_host': 'localhost',
        'pg_port': 5432,

        # SSL Configuration
        'features': {
            'ssl': True,
            'api_keys': True,
            'multi_user': False
        },
        'ssl': {
            'type': 'self-signed',  # or 'existing'
            # For existing certs:
            # 'cert_path': '/path/to/cert.crt',
            # 'key_path': '/path/to/key.key'
        },

        # Admin User
        'server': {
            'admin_user': 'admin',
            'admin_password': 'ChangeThisPassword123!',
            'admin_email': 'admin@example.com'
        },

        # Database credentials (from Phase 1)
        'owner_password': 'secure_owner_password',
        'user_password': 'secure_user_password',

        # Optional
        'hostname': 'giljo-mcp.local',
        'batch': False  # Interactive mode
    }

    # Create installer
    installer = ServerInstaller(settings)

    # Run installation
    print("\nStarting server mode installation...")
    result = installer.install()

    # Display results
    print("\n" + "=" * 70)
    if result['success']:
        print("  ✅ INSTALLATION SUCCESSFUL")
        print("=" * 70)
        print()
        print("Installation Details:")
        print(f"  Mode: {result['mode']}")
        print(f"  Log file: {result['log_file']}")

        if 'admin_user' in result:
            print(f"  Admin user: {result['admin_user']}")

        if 'api_key' in result:
            print(f"  API Key: {result['api_key']}")
            print("  ⚠️  SAVE THIS KEY - IT WILL NOT BE SHOWN AGAIN!")

        if 'firewall_files' in result:
            print("\n  Firewall Scripts Generated:")
            for file in result['firewall_files']:
                print(f"    - {file}")

        if 'warnings' in result and result['warnings']:
            print("\n  ⚠️  Warnings:")
            for warning in result['warnings']:
                print(f"    - {warning}")

        print("\n  Next Steps:")
        print("  1. Apply firewall rules (see firewall_rules.txt)")
        print("  2. Review security settings in config.yaml")
        print("  3. Save API key in secure location")
        print("  4. Run: python launchers/start_giljo.py")

    else:
        print("  ❌ INSTALLATION FAILED")
        print("=" * 70)
        print(f"\n  Error: {result.get('error', 'Unknown error')}")
        if 'details' in result:
            print("\n  Details:")
            for detail in result['details']:
                print(f"    - {detail}")

    print()


def example_network_check():
    """Network configuration and conflict detection example"""

    print("\n" + "=" * 70)
    print("  Network Configuration Check")
    print("=" * 70)
    print()

    # Check for port conflicts
    print("Checking for port conflicts...")
    conflicts = detect_network_conflicts()

    if conflicts['has_conflicts']:
        print("\n⚠️  Port Conflicts Detected:")
        for issue in conflicts['issues']:
            print(f"  - {issue}")

        print("\n💡 Recommendations:")
        for rec in conflicts['recommendations']:
            print(f"  - {rec}")
    else:
        print("✅ No port conflicts detected")

    # Network configuration
    settings = {
        'mode': 'server',
        'bind': '0.0.0.0',
        'api_port': 8000,
        'ws_port': 8001,
        'dashboard_port': 3000,
        'features': {'ssl': True},
        'ssl': {'type': 'self-signed'}
    }

    network_mgr = NetworkManager(settings)

    # Get network info
    print("\n" + "-" * 70)
    print("Network Configuration:")
    info = network_mgr.get_network_info()
    print(f"  Hostname: {info['hostname']}")
    print(f"  Platform: {info['platform']}")
    print(f"  Bind Address: {info['bind_address']}")
    print(f"  SSL Enabled: {info['ssl_enabled']}")
    print(f"  Network Exposed: {info['network_exposed']}")

    if info['local_ips']:
        print(f"  Local IPs: {', '.join(info['local_ips'])}")

    # Display security warning
    warning = network_mgr.print_network_warning()
    if warning:
        print(warning)


def example_ssl_generation():
    """SSL certificate generation example"""

    print("\n" + "=" * 70)
    print("  SSL Certificate Generation")
    print("=" * 70)
    print()

    settings = {
        'mode': 'server',
        'features': {'ssl': True},
        'ssl': {'type': 'self-signed'},
        'hostname': 'giljo-mcp.example.com'
    }

    network_mgr = NetworkManager(settings)

    print("Generating self-signed SSL certificate...")
    result = network_mgr.generate_self_signed_cert()

    if result['success']:
        print("\n✅ SSL Certificate Generated Successfully")
        print(f"  Certificate: {result['cert_path']}")
        print(f"  Private Key: {result['key_path']}")
        print(f"  Hostname: {result['hostname']}")
        print(f"  Valid for: {result['valid_days']} days")
        print("\n⚠️  Self-signed certificates will trigger browser warnings")
        print("   For production, use CA-signed certificates")
    else:
        print("\n❌ Certificate Generation Failed")
        for error in result.get('errors', []):
            print(f"  Error: {error}")


def example_api_key_management():
    """API key generation and management example"""

    print("\n" + "=" * 70)
    print("  API Key Management")
    print("=" * 70)
    print()

    from installer.core import APIKeyManager

    api_mgr = APIKeyManager()

    # Generate API key
    print("Generating API key...")
    api_key = api_mgr.generate_key(
        name='production',
        permissions=['read', 'write', 'admin']
    )

    print(f"\n✅ API Key Generated: {api_key}")
    print("⚠️  Save this key securely - it will not be shown again!")

    # Validate key
    print("\nValidating API key...")
    is_valid = api_mgr.validate_key(api_key)
    print(f"  Validation result: {'✅ Valid' if is_valid else '❌ Invalid'}")

    # List all keys
    print("\nAll API Keys:")
    keys = api_mgr.list_keys()
    for key in keys:
        status = '✅ Active' if key.get('active') else '❌ Revoked'
        print(f"  - {key['name']}: {status} (created: {key['created_at']})")
        print(f"    Permissions: {', '.join(key['permissions'])}")


def example_firewall_generation():
    """Firewall rule generation example"""

    print("\n" + "=" * 70)
    print("  Firewall Rule Generation")
    print("=" * 70)
    print()

    settings = {
        'mode': 'server',
        'bind': '0.0.0.0',
        'api_port': 8000,
        'ws_port': 8001,
        'dashboard_port': 3000,
        'pg_port': 5432
    }

    firewall_mgr = FirewallManager(settings)

    print("Generating firewall rules...")
    result = firewall_mgr.generate_firewall_rules()

    if result['success']:
        print(f"\n✅ Firewall Rules Generated ({result['platform']})")
        print("\nGenerated Scripts:")
        for file in result['files']:
            print(f"  - {file}")

        print("\n⚠️  Important: Firewall rules must be applied manually")
        print("   See firewall_rules.txt for quick reference")

        # Display instructions
        instructions = firewall_mgr.print_firewall_instructions()
        print(instructions)
    else:
        print("\n❌ Firewall Generation Failed")
        for error in result.get('errors', []):
            print(f"  Error: {error}")


def example_security_setup():
    """Security configuration example"""

    print("\n" + "=" * 70)
    print("  Security Configuration")
    print("=" * 70)
    print()

    settings = {
        'mode': 'server',
        'admin_username': 'admin',
        'admin_password': 'SecurePassword123!',
        'generate_api_key': True,
        'features': {
            'api_keys': True,
            'multi_user': False
        }
    }

    security_mgr = SecurityManager(settings)

    print("Configuring security...")
    result = security_mgr.configure()

    if result['success']:
        print("\n✅ Security Configuration Complete")

        if 'admin_user' in result:
            print(f"  Admin User: {result['admin_user']}")

        if 'api_key' in result:
            print(f"  API Key: {result['api_key']}")
            print(f"  Key File: {result.get('api_key_file')}")

        print("\n🔒 Security Features:")
        print("  - Password hashing: PBKDF2-SHA256 (100k iterations)")
        print("  - API key hashing: SHA-256")
        print("  - Secure random generation: secrets module")
        print("  - File permissions: Restricted (Unix)")
    else:
        print("\n❌ Security Configuration Failed")
        for error in result.get('errors', []):
            print(f"  Error: {error}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='GiljoAI MCP Server Mode Examples')
    parser.add_argument('--example', choices=[
        'install',
        'network',
        'ssl',
        'api-key',
        'firewall',
        'security',
        'all'
    ], default='all', help='Example to run')

    args = parser.parse_args()

    examples = {
        'install': example_server_installation,
        'network': example_network_check,
        'ssl': example_ssl_generation,
        'api-key': example_api_key_management,
        'firewall': example_firewall_generation,
        'security': example_security_setup
    }

    if args.example == 'all':
        for name, func in examples.items():
            func()
            print("\n" + "=" * 70 + "\n")
    else:
        examples[args.example]()

    print("\n✅ Example execution complete\n")
