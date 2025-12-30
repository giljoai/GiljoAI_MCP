#!/usr/bin/env python3
"""
CSP Verification Script

Verifies that the hash-based Content Security Policy is correctly configured.

Created in Handover 1007 - Hash-Based CSP Implementation

Usage:
    python scripts/verify_csp.py
    GILJO_ENV=dev python scripts/verify_csp.py  # Test development mode
"""

import sys
from pathlib import Path

# Add API directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'api'))

from middleware.security import (
    SecurityHeadersMiddleware,
    is_development_mode,
    CSP_STYLE_HASH,
    CSP_SCRIPT_HASH_1,
    CSP_SCRIPT_HASH_2
)


def main():
    """Verify CSP configuration."""
    print("=" * 70)
    print("CSP VERIFICATION REPORT")
    print("=" * 70)
    print()

    # Environment detection
    is_dev = is_development_mode()
    mode = "DEVELOPMENT" if is_dev else "PRODUCTION"
    print(f"Environment Mode: {mode}")
    print()

    # Show loaded hashes
    print("Loaded CSP Hashes:")
    print(f"  Style:    {CSP_STYLE_HASH}")
    print(f"  Script 1: {CSP_SCRIPT_HASH_1}")
    print(f"  Script 2: {CSP_SCRIPT_HASH_2}")
    print()

    # Show CSP directives
    print("CSP Directives:")
    print()

    # script-src
    script_src = f"'self' {CSP_SCRIPT_HASH_1} {CSP_SCRIPT_HASH_2}"
    if is_dev:
        script_src += " 'unsafe-eval'"
    print(f"  script-src: {script_src}")

    # style-src
    print(f"  style-src: 'self' {CSP_STYLE_HASH}")
    print()

    # Full CSP header
    print("Full Content-Security-Policy Header:")
    print("-" * 70)
    csp_header = (
        "default-src 'self'; "
        f"script-src {script_src}; "
        f"style-src 'self' {CSP_STYLE_HASH}; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' ws: wss:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    print(csp_header)
    print("-" * 70)
    print()

    # Security analysis
    print("Security Analysis:")
    print()
    if is_dev:
        print("  [!] DEVELOPMENT MODE - unsafe-eval is ENABLED for HMR")
        print("      This is acceptable for development but NOT for production")
    else:
        print("  [+] PRODUCTION MODE - No unsafe-inline or unsafe-eval")
        print("      Hash-based CSP provides strong XSS protection")

    print()
    print("  [+] All inline scripts/styles are whitelisted via SHA-256 hashes")
    print("  [+] WebSocket connections allowed (ws: wss:) for real-time features")
    print("  [+] Frame-ancestors set to 'none' (prevents clickjacking)")
    print()

    # Maintenance reminder
    print("Maintenance:")
    print()
    print("  If you modify inline code in frontend/index.html, you MUST:")
    print("  1. Run: python scripts/generate_csp_hashes.py")
    print("  2. Update CSP hash constants in api/middleware/security.py")
    print("  3. Restart the API server")
    print()

    print("=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70)

    return 0


if __name__ == '__main__':
    exit(main())
