"""
Cross-platform test runner with hang detection and diagnostic logging.

Works on both Windows and Linux. Runs pytest with per-test timeouts
and writes a structured log so you can identify exactly which test hung.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py tests/unit/        # Run specific directory
    python run_tests.py -k "test_auth"     # Filter by name
    python run_tests.py --timeout 60       # Override per-test timeout (seconds)
    python run_tests.py --no-cov           # Skip coverage (faster)
    python run_tests.py --suite-timeout 600  # Overall suite timeout (seconds)
"""

# ruff: noqa: T201 - print is intentional in this CLI runner

import argparse
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

TIMESTAMP = _now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = LOG_DIR / f"test_run_{TIMESTAMP}.log"
SUMMARY_FILE = LOG_DIR / f"test_run_{TIMESTAMP}_summary.log"

# Regex for pytest verbose result lines: "tests/path.py::Class::test PASSED [ 7%]"
_RESULT_RE = re.compile(
    r"^(tests/.+?::\S+)"  # node_id
    r"\s+"
    r"(PASSED|FAILED|ERROR|XFAIL|XPASS|SKIPPED)"  # status
    r"(?:\s+\[.*\])?"  # optional progress
    r"\s*$",
)
# Regex for pytest-timeout forced failures (shows up in FAILURES section)
_TIMEOUT_RE = re.compile(r"Timeout\s*>\s*[\d.]+s", re.IGNORECASE)


def parse_args():
    parser = argparse.ArgumentParser(description="Run test suite with hang detection")
    parser.add_argument("paths", nargs="*", default=[], help="Test paths/files to run")
    parser.add_argument("-k", "--filter", default="", help="pytest -k filter expression")
    parser.add_argument("-m", "--marker", default="", help="pytest -m marker expression")
    parser.add_argument("--timeout", type=int, default=30, help="Per-test timeout in seconds (default: 30)")
    parser.add_argument("--suite-timeout", type=int, default=0, help="Overall suite timeout in seconds (0=unlimited)")
    parser.add_argument("--no-cov", action="store_true", help="Disable coverage collection (faster)")
    parser.add_argument("--failfast", "-x", action="store_true", help="Stop on first failure")
    parser.add_argument("--last-failed", action="store_true", help="Re-run only last failed tests")
    parser.add_argument("-v", "--verbose", action="store_true", help="Extra verbose output")
    return parser.parse_args()


def build_pytest_cmd(args):
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-v",
        "--tb=short",
        f"--timeout={args.timeout}",
        "--timeout-method=thread",
        "-p",
        "no:faulthandler",
    ]

    if args.no_cov:
        cmd += ["--no-cov", "--override-ini=addopts="]
    else:
        cmd += [
            "--cov=giljo_mcp",
            "--cov-report=term-missing",
        ]

    if args.failfast:
        cmd.append("-x")

    if args.last_failed:
        cmd.append("--lf")

    if args.filter:
        cmd += ["-k", args.filter]

    if args.marker:
        cmd += ["-m", args.marker]

    if args.verbose:
        cmd.append("-vv")

    cmd.append("--ignore=tests/test_websocket_security.py")

    if args.paths:
        cmd += args.paths
    else:
        cmd.append("tests/")

    return cmd


class TestWatcher:
    """Watches pytest output to track which test is currently running."""

    def __init__(self, log_path: Path, summary_path: Path):
        self.log_path = log_path
        self.summary_path = summary_path
        self.current_test = None
        self.current_test_start = None
        self.test_times: dict[str, float] = {}
        self.passed = 0
        self.failed = 0
        self.errors = 0
        self.timeouts = 0
        self.timed_out_tests: list[str] = []
        self.failed_tests: list[str] = []
        self.skipped = 0
        self.total_start = time.monotonic()
        self._log_path = log_path
        self._log_handle = log_path.open("w", encoding="utf-8")
        self._in_failures_section = False

    def _log(self, line: str):
        ts = _now().strftime("%H:%M:%S.%f")[:-3]
        self._log_handle.write(f"[{ts}] {line}\n")
        self._log_handle.flush()

    def _finish_current_test(self):
        """Record elapsed time for the test that just finished."""
        if self.current_test and self.current_test_start:
            elapsed = time.monotonic() - self.current_test_start
            self.test_times[self.current_test] = elapsed

    def process_line(self, line: str):
        """Parse a pytest output line and track state."""
        stripped = line.strip()

        # Track FAILURES section for timeout detection
        if stripped.startswith(("= FAILURES =", "=== FAILURES ===")):
            self._in_failures_section = True
        elif self._in_failures_section and stripped.startswith("=") and "FAILURES" not in stripped:
            self._in_failures_section = False

        # Detect pytest-timeout messages in failure blocks
        if self._in_failures_section and _TIMEOUT_RE.search(stripped):
            self.timeouts += 1
            if self.current_test:
                self.timed_out_tests.append(self.current_test)
            self._log(f"TIMEOUT DETECTED: {stripped}")

        # Match pytest verbose result lines
        m = _RESULT_RE.match(stripped)
        if m:
            node_id = m.group(1)
            status = m.group(2)

            self._finish_current_test()
            self.current_test = node_id
            self.current_test_start = time.monotonic()

            if status == "PASSED":
                self.passed += 1
                self._log(f"PASS  {node_id}")
            elif status == "FAILED":
                self.failed += 1
                self.failed_tests.append(node_id)
                self._log(f"FAIL  {node_id}")
            elif status == "ERROR":
                self.errors += 1
                self.failed_tests.append(node_id)
                self._log(f"ERROR {node_id}")
            elif status in ("SKIPPED", "XFAIL", "XPASS"):
                self.skipped += 1
            return

        # Detect test node lines without status (test is running NOW)
        if "::" in stripped and stripped.startswith("tests/"):
            parts = stripped.split()
            candidate = parts[0]
            if "::" in candidate and not any(s in candidate for s in ["PASSED", "FAILED", "ERROR", "SKIPPED"]):
                self._finish_current_test()
                self.current_test = candidate
                self.current_test_start = time.monotonic()
                self._log(f"START {candidate}")

        # Detect _ FAILURES _ header lines with test names
        if stripped.startswith("_") and stripped.endswith("_") and "::" in stripped:
            test_name = stripped.strip("_ ")
            if test_name:
                self.current_test = test_name
                self._log(f"FAILURE BLOCK: {test_name}")

    def write_summary(self, return_code: int) -> str:
        self._finish_current_test()
        elapsed = time.monotonic() - self.total_start

        slowest = sorted(self.test_times.items(), key=lambda x: x[1], reverse=True)[:20]

        lines = [
            "=" * 70,
            f"TEST RUN SUMMARY - {_now().strftime('%Y-%m-%d %H:%M:%S')} UTC",
            "=" * 70,
            f"Total time:  {elapsed:.1f}s",
            f"Exit code:   {return_code}",
            f"Passed:      {self.passed}",
            f"Failed:      {self.failed}",
            f"Errors:      {self.errors}",
            f"Timeouts:    {self.timeouts}",
            f"Skipped:     {self.skipped}",
            "",
        ]

        if self.timed_out_tests:
            lines.append("TIMED-OUT TESTS (these are your hang culprits):")
            lines.extend(f"  {t}" for t in self.timed_out_tests)
            lines.append("")

        if self.failed_tests:
            lines.append("FAILED TESTS:")
            lines.extend(f"  {t}" for t in self.failed_tests)
            lines.append("")

        if slowest:
            lines.append("TOP 20 SLOWEST TESTS:")
            for node_id, t in slowest:
                marker = " <<< SLOW" if t > 10 else ""
                lines.append(f"  {t:6.1f}s  {node_id}{marker}")
            lines.append("")

        if self.current_test and return_code not in (0, None):
            lines += [
                "LAST TEST SEEN WHEN SUITE ENDED:",
                f"  {self.current_test}",
                "  (If the suite was killed, this test likely caused the hang)",
                "",
            ]

        lines += [
            f"Full log: {self.log_path}",
            "=" * 70,
        ]

        summary_text = "\n".join(lines)
        with self.summary_path.open("w", encoding="utf-8") as f:
            f.write(summary_text)

        return summary_text

    def close(self):
        self._log_handle.close()


def run_with_suite_timeout(cmd, suite_timeout, watcher):
    """Run subprocess with optional overall suite timeout."""
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        bufsize=1,
    )

    timed_out = False

    def kill_on_timeout():
        nonlocal timed_out
        timed_out = True
        msg = (
            f"\n{'=' * 70}\n"
            f"SUITE TIMEOUT ({suite_timeout}s) REACHED\n"
            f"Last test running: {watcher.current_test or 'unknown'}\n"
            f"{'=' * 70}\n"
        )
        print(msg)
        watcher._log(f"SUITE TIMEOUT after {suite_timeout}s - killing process")
        watcher._log(f"Last test: {watcher.current_test}")
        proc.terminate()
        time.sleep(3)
        if proc.poll() is None:
            proc.kill()

    timer = None
    if suite_timeout > 0:
        timer = threading.Timer(suite_timeout, kill_on_timeout)
        timer.daemon = True
        timer.start()

    try:
        for raw_line in proc.stdout:
            output = raw_line.rstrip("\n\r")
            print(output, flush=True)
            watcher.process_line(output)
            watcher._log(output)
    except KeyboardInterrupt:
        print("\nInterrupted by user - terminating...")
        watcher._log("INTERRUPTED by user (Ctrl+C)")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    finally:
        if timer:
            timer.cancel()

    proc.wait()
    return proc.returncode if not timed_out else 99


def main():
    args = parse_args()

    print(f"Test runner starting at {_now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"Per-test timeout: {args.timeout}s")
    if args.suite_timeout:
        print(f"Suite timeout: {args.suite_timeout}s")
    print(f"Log file: {LOG_FILE}")
    print(f"Summary: {SUMMARY_FILE}")
    print()

    cmd = build_pytest_cmd(args)
    print(f"Command: {' '.join(cmd)}\n")

    watcher = TestWatcher(LOG_FILE, SUMMARY_FILE)

    try:
        return_code = run_with_suite_timeout(cmd, args.suite_timeout, watcher)
    except KeyboardInterrupt:
        watcher._log("RUNNER INTERRUPTED")
        return_code = 130
    except OSError as e:
        watcher._log(f"RUNNER ERROR: {e}")
        return_code = 1
    finally:
        summary = watcher.write_summary(return_code)
        watcher.close()

    print()
    print(summary)

    return return_code


if __name__ == "__main__":
    sys.exit(main())
