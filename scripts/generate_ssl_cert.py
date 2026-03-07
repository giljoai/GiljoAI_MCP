"""
SSL Certificate Generation Script for GiljoAI MCP

Generates self-signed SSL certificates for development and testing.
For production, use Let's Encrypt (see docs/security/HTTPS_SETUP.md).
"""
import argparse
import subprocess
from pathlib import Path


def generate_self_signed_cert(output_dir: Path, domain: str = "localhost", days: int = 365):
    """Generate self-signed SSL certificate using OpenSSL."""
    output_dir.mkdir(parents=True, exist_ok=True)

    key_path = output_dir / "ssl_key.pem"
    cert_path = output_dir / "ssl_cert.pem"

    cmd = [
        "openssl", "req", "-x509", "-newkey", "rsa:4096",
        "-keyout", str(key_path),
        "-out", str(cert_path),
        "-days", str(days),
        "-nodes",
        "-subj", f"/CN={domain}/O=GiljoAI MCP/C=US"
    ]

    print(f"Generating self-signed SSL certificate for '{domain}'...")
    print(f"   Valid for: {days} days")

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Certificate generated successfully!")
        print(f"   Key:  {key_path}")
        print(f"   Cert: {cert_path}")
        print()
        print("NOTE: Self-signed certificates will show browser warnings.")
        print("   For production, use Let's Encrypt (see docs/security/HTTPS_SETUP.md)")
        return key_path, cert_path
    except subprocess.CalledProcessError as e:
        print(f"Failed to generate certificate: {e.stderr}")
        return None, None
    except FileNotFoundError:
        print("OpenSSL not found. Please install OpenSSL:")
        print("   Windows: https://slproweb.com/products/Win32OpenSSL.html")
        print("   Linux:   sudo apt-get install openssl")
        print("   macOS:   brew install openssl")
        return None, None


def update_config_yaml(cert_path: Path, key_path: Path):
    """Update config.yaml with SSL paths and enable SSL."""
    import yaml

    config_path = Path.cwd() / "config.yaml"

    if not config_path.exists():
        print(f"config.yaml not found at {config_path}")
        return False

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f) or {}

    if 'features' not in config:
        config['features'] = {}
    config['features']['ssl_enabled'] = True

    if 'paths' not in config:
        config['paths'] = {}
    config['paths']['ssl_cert'] = str(cert_path.absolute())
    config['paths']['ssl_key'] = str(key_path.absolute())

    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print("Updated config.yaml:")
    print("   features.ssl_enabled: true")
    print(f"   paths.ssl_cert: {cert_path}")
    print(f"   paths.ssl_key: {key_path}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Generate SSL certificates for GiljoAI MCP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/generate_ssl_cert.py
  python scripts/generate_ssl_cert.py --domain my-server.local
  python scripts/generate_ssl_cert.py --days 730
  python scripts/generate_ssl_cert.py --output ./my-certs
  python scripts/generate_ssl_cert.py --no-update-config
        """
    )

    parser.add_argument(
        "--domain",
        default="localhost",
        help="Domain name for certificate (default: localhost)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Certificate validity in days (default: 365)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path.cwd() / "certs",
        help="Output directory for certificates (default: ./certs)"
    )
    parser.add_argument(
        "--no-update-config",
        action="store_true",
        help="Don't update config.yaml with certificate paths"
    )

    args = parser.parse_args()

    key_path, cert_path = generate_self_signed_cert(args.output, args.domain, args.days)

    if key_path and cert_path:
        if not args.no_update_config:
            update_config_yaml(cert_path, key_path)

        print()
        print("Next Steps:")
        print("   1. Restart the server: python startup.py")
        print("   2. Access via HTTPS: https://localhost:7272")
        print("   3. Accept browser security warning (self-signed cert)")
        print()
        print("Production Setup:")
        print("   See docs/security/HTTPS_SETUP.md for Let's Encrypt configuration")


if __name__ == "__main__":
    main()
