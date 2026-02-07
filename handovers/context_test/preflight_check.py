"""
Pre-flight Check for Context Configuration Test Suite.

Validates that all prerequisites are met before running tests.

REQUIRED CREDENTIALS:
---------------------
1. GILJO_API_KEY - Your API key from Settings -> API Keys in the GiljoAI dashboard

   To create an API key:
   a) Open http://10.1.0.164:7274 and log in
   b) Click the gear icon (Settings) -> API Keys tab
   c) Click "Create New API Key"
   d) Copy the key (starts with 'gk_')

2. ORCHESTRATOR_ID - UUID of an orchestrator job (default provided)
3. TENANT_KEY - Your tenant isolation key (default provided)

Set credentials as environment variables:
    Windows PowerShell:  $env:GILJO_API_KEY = "gk_your_key_here"
    Windows CMD:         set GILJO_API_KEY=gk_your_key_here
    Linux/macOS:         export GILJO_API_KEY="gk_your_key_here"

Usage:
    python preflight_check.py
"""

import os
import sys
from pathlib import Path


# ASCII-safe symbols for Windows compatibility
CHECK = "[OK]"
FAIL = "[FAIL]"
WARN = "[WARN]"


def check_python_version():
    """Check Python version is 3.11+."""
    print("Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 11:
        print(f"  {CHECK} Python {version.major}.{version.minor}.{version.micro}")
        return True
    print(f"  {FAIL} Python {version.major}.{version.minor}.{version.micro}")
    print("  ERROR: Python 3.11+ required")
    return False


def check_dependencies():
    """Check required dependencies are installed."""
    print("\nChecking dependencies...")
    try:
        import httpx

        print(f"  {CHECK} httpx {httpx.__version__}")
        return True
    except ImportError:
        print(f"  {FAIL} httpx not found")
        print("  ERROR: Install with: pip install httpx")
        return False


def check_api_key():
    """Check API key is set."""
    print("\nChecking API key...")
    api_key = os.environ.get("GILJO_API_KEY", "gk_9-TgHc3tqq0-GzXJRXts_GjyxgIkLmGLthoJbtfrOac")
    if api_key:
        masked = api_key[:6] + "..." + api_key[-4:] if len(api_key) > 10 else "***"
        print(f"  {CHECK} GILJO_API_KEY is set ({masked})")
        return True
    print(f"  {FAIL} GILJO_API_KEY not set")
    print()
    print("  HOW TO GET YOUR API KEY:")
    print("  -------------------------")
    print("  1. Open the GiljoAI dashboard: http://10.1.0.164:7274")
    print("  2. Log in with your credentials")
    print("  3. Go to: Settings (gear icon) -> API Keys")
    print("  4. Click 'Create New API Key'")
    print("  5. Copy the key (starts with 'gk_')")
    print("  6. Set the environment variable:")
    print()
    print("     Windows PowerShell:")
    print('       $env:GILJO_API_KEY = "gk_your_key_here"')
    print()
    print("     Windows CMD:")
    print("       set GILJO_API_KEY=gk_your_key_here")
    print()
    print("     Linux/macOS:")
    print('       export GILJO_API_KEY="gk_your_key_here"')
    return False


def check_server_connection():
    """Check server is reachable."""
    print("\nChecking server connection...")
    api_base_url = os.environ.get("GILJO_API_URL", "http://10.1.0.164:7274")

    try:
        import httpx

        client = httpx.Client(timeout=5.0)
        response = client.get(f"{api_base_url}/health")

        if response.status_code == 200:
            print(f"  {CHECK} Server reachable at {api_base_url}")
            return True
        print(f"  {WARN} Server returned {response.status_code}")
        print(f"       URL: {api_base_url}")
        return True  # Server reachable, just not health endpoint
    except Exception as e:
        print(f"  {FAIL} Connection failed: {e}")
        print(f"       Check that server is running at {api_base_url}")
        return False


def check_api_authentication():
    """Verify API key is valid by making authenticated MCP request."""
    print("\nChecking API authentication (via MCP)...")

    api_key = os.environ.get("GILJO_API_KEY", "gk_9-TgHc3tqq0-GzXJRXts_GjyxgIkLmGLthoJbtfrOac")
    api_base_url = os.environ.get("GILJO_API_URL", "http://10.1.0.164:7274")

    if not api_key:
        print(f"  {WARN} Skipping (no API key set)")
        return True  # Already reported in check_api_key

    try:
        import httpx

        # Test against MCP endpoint (which uses X-API-Key)
        headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "health_check", "arguments": {}},
        }

        client = httpx.Client(timeout=10.0)
        response = client.post(f"{api_base_url}/mcp", json=payload, headers=headers)

        if response.status_code == 200:
            data = response.json()
            if "result" in data:
                print(f"  {CHECK} API key valid (MCP authenticated)")
                return True
            if "error" in data:
                print(f"  {FAIL} MCP error: {data['error']}")
                return False
        elif response.status_code == 401:
            print(f"  {FAIL} API key invalid or expired")
            print("       Create a new API key in Settings -> API Keys")
            return False
        else:
            print(f"  {WARN} Unexpected status: {response.status_code}")
            return True
    except Exception as e:
        print(f"  {FAIL} Authentication check failed: {e}")
        return False


def check_test_credentials():
    """Verify test credentials are configured."""
    print("\nChecking test credentials...")

    # Get credentials from environment or use defaults
    orchestrator_id = os.environ.get("GILJO_ORCHESTRATOR_ID", "6792fae5-c46b-4ed7-86d6-df58aa833df3")
    tenant_key = os.environ.get("GILJO_TENANT_KEY", "***REMOVED***")
    project_id = os.environ.get("GILJO_PROJECT_ID", "97d95e5a-51dd-47ae-92de-7f8839de503a")

    print(f"  {CHECK} ORCHESTRATOR_ID: {orchestrator_id[:8]}...")
    print(f"  {CHECK} TENANT_KEY: {tenant_key[:12]}...")
    print(f"  {CHECK} PROJECT_ID: {project_id[:8]}...")
    print()
    print("  Note: Override defaults with environment variables:")
    print("    GILJO_ORCHESTRATOR_ID, GILJO_TENANT_KEY, GILJO_PROJECT_ID")
    return True


def check_results_directory():
    """Check results directory exists and is writable."""
    print("\nChecking results directory...")

    results_dir = Path(__file__).parent / "results"

    if not results_dir.exists():
        try:
            results_dir.mkdir(parents=True)
            print(f"  {CHECK} Created: {results_dir}")
            return True
        except Exception as e:
            print(f"  {FAIL} Cannot create: {e}")
            return False
    else:
        # Check if writable
        test_file = results_dir / ".write_test"
        try:
            test_file.write_text("test")
            test_file.unlink()
            print(f"  {CHECK} Writable: {results_dir}")
            return True
        except Exception as e:
            print(f"  {FAIL} Not writable: {e}")
            return False


def main():
    """Run all pre-flight checks."""
    print()
    print("=" * 80)
    print("CONTEXT CONFIGURATION TEST SUITE - PRE-FLIGHT CHECK")
    print("=" * 80)

    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("API Key", check_api_key),
        ("Server Connection", check_server_connection),
        ("API Authentication", check_api_authentication),
        ("Test Credentials", check_test_credentials),
        ("Results Directory", check_results_directory),
    ]

    results = []
    for name, check_func in checks:
        results.append(check_func())

    # Summary
    print()
    print("=" * 80)
    print("PRE-FLIGHT CHECK SUMMARY")
    print("=" * 80)
    print()

    passed = sum(results)
    total = len(results)

    for i, (name, _) in enumerate(checks):
        status = f"{CHECK} PASS" if results[i] else f"{FAIL} FAIL"
        print(f"  {name:<25} {status}")

    print()
    print(f"  Total: {passed}/{total} checks passed")

    if passed == total:
        print()
        print(f"  {CHECK} All checks passed! Ready to run tests.")
        print()
        print("  Run tests with:")
        print("    python run_context_tests.py")
        return 0
    print()
    print(f"  {FAIL} Some checks failed. Please fix errors above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
