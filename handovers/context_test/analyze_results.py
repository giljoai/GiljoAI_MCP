"""
Results Analysis Script for Context Configuration Tests.

Provides utilities to analyze test results and generate insights.

Usage:
    python analyze_results.py
"""

import json
from pathlib import Path
from typing import Any, Dict


class ResultsAnalyzer:
    """Analyzes context configuration test results."""

    def __init__(self, results_dir: Path):
        self.results_dir = results_dir
        self.summary_file = results_dir / "summary.json"
        self.summary: Dict[str, Any] = {}
        self.load_summary()

    def load_summary(self):
        """Load summary file."""
        if self.summary_file.exists():
            with open(self.summary_file, encoding="utf-8") as f:
                self.summary = json.load(f)
        else:
            raise FileNotFoundError(
                f"Summary file not found: {self.summary_file}\nPlease run run_context_tests.py first."
            )

    def print_overview(self):
        """Print test run overview."""
        print("\n" + "=" * 80)
        print("CONTEXT CONFIGURATION TEST RESULTS - OVERVIEW")
        print("=" * 80)

        print(f"\nTest Run: {self.summary['test_run_timestamp']}")
        print(f"Total Tests: {self.summary['total_tests']}")
        print(f"Successful: {self.summary['successful_tests']}")
        print(f"Failed: {self.summary['failed_tests']}")

        success_rate = self.summary["successful_tests"] / self.summary["total_tests"] * 100
        print(f"Success Rate: {success_rate:.1f}%")

    def print_token_statistics(self):
        """Print token usage statistics."""
        print("\n" + "=" * 80)
        print("TOKEN STATISTICS")
        print("=" * 80)

        results = self.summary["results"]
        successful_results = [r for r in results if r["success"]]

        if not successful_results:
            print("\nNo successful tests to analyze.")
            return

        tokens = [r["estimated_tokens"] for r in successful_results]

        print(f"\nMinimum Tokens: {min(tokens)}")
        print(f"Maximum Tokens: {max(tokens)}")
        print(f"Average Tokens: {sum(tokens) / len(tokens):.0f}")
        print(f"Median Tokens: {sorted(tokens)[len(tokens) // 2]}")

        # Find min/max configurations
        min_result = min(successful_results, key=lambda r: r["estimated_tokens"])
        max_result = max(successful_results, key=lambda r: r["estimated_tokens"])

        print("\nLowest Token Configuration:")
        print(f"  {min_result['test_name']}: {min_result['estimated_tokens']} tokens")

        print("\nHighest Token Configuration:")
        print(f"  {max_result['test_name']}: {max_result['estimated_tokens']} tokens")

    def print_priority_impact(self):
        """Analyze impact of priority settings on token count."""
        print("\n" + "=" * 80)
        print("PRIORITY IMPACT ANALYSIS")
        print("=" * 80)

        results = self.summary["results"]

        # Find priority sweep tests
        priority_tests = [r for r in results if r["test_name"].startswith("Priority Sweep")]

        if not priority_tests:
            print("\nNo priority sweep tests found.")
            return

        # Group by field
        fields = [
            "product_core",
            "vision_documents",
            "tech_stack",
            "architecture",
            "testing_config",
            "memory_360",
            "git_history",
            "agent_templates",
        ]

        print("\nToken count by field priority level:")
        print(f"\n{'Field':<20} {'OFF':<10} {'Critical':<10} {'Important':<10} {'Reference':<10}")
        print("-" * 60)

        for field in fields:
            field_tests = [r for r in priority_tests if field in r["test_name"].lower()]

            if not field_tests:
                continue

            # Extract token counts by priority level
            off = next(
                (r["estimated_tokens"] for r in field_tests if "OFF" in r["test_name"]),
                0,
            )
            critical = next(
                (r["estimated_tokens"] for r in field_tests if "Critical" in r["test_name"]),
                0,
            )
            important = next(
                (r["estimated_tokens"] for r in field_tests if "Important" in r["test_name"]),
                0,
            )
            reference = next(
                (r["estimated_tokens"] for r in field_tests if "Reference" in r["test_name"]),
                0,
            )

            print(f"{field:<20} {off:<10} {critical:<10} {important:<10} {reference:<10}")

    def print_depth_impact(self):
        """Analyze impact of depth settings on token count."""
        print("\n" + "=" * 80)
        print("DEPTH IMPACT ANALYSIS")
        print("=" * 80)

        results = self.summary["results"]

        # Find depth sweep tests
        depth_tests = [r for r in results if r["test_name"].startswith("Depth Sweep")]

        if not depth_tests:
            print("\nNo depth sweep tests found.")
            return

        # Group by field
        depth_fields = {
            "vision_documents": ["optional", "light", "medium", "full"],
            "memory_last_n_projects": ["1", "3", "5", "10"],
            "git_commits": ["5", "10", "25", "50", "100"],
            "agent_templates": ["type_only", "full"],
        }

        print("\nToken count by depth level:")

        for field, levels in depth_fields.items():
            field_tests = [r for r in depth_tests if field in r["test_name"].lower()]

            if not field_tests:
                continue

            print(f"\n{field}:")
            print(f"{'Level':<20} {'Tokens':<10}")
            print("-" * 30)

            for level in levels:
                test = next(
                    (r for r in field_tests if str(level) in r["test_name"]),
                    None,
                )
                if test:
                    print(f"{level:<20} {test['estimated_tokens']:<10}")

    def print_edge_case_analysis(self):
        """Analyze edge case test results."""
        print("\n" + "=" * 80)
        print("EDGE CASE ANALYSIS")
        print("=" * 80)

        results = self.summary["results"]

        # Find edge case tests
        edge_tests = [r for r in results if r["test_name"].startswith("Edge Case")]

        if not edge_tests:
            print("\nNo edge case tests found.")
            return

        print(f"\n{'Test Name':<45} {'Tokens':<10} {'Success':<10}")
        print("-" * 65)

        for test in edge_tests:
            success = "✓" if test["success"] else "✗"
            test_name = test["test_name"].replace("Edge Case - ", "")
            print(f"{test_name:<45} {test['estimated_tokens']:<10} {success:<10}")

    def print_failed_tests(self):
        """Print details of failed tests."""
        results = self.summary["results"]
        failed = [r for r in results if not r["success"]]

        if not failed:
            print("\n✓ All tests passed!")
            return

        print("\n" + "=" * 80)
        print("FAILED TESTS")
        print("=" * 80)

        for test in failed:
            print(f"\n✗ {test['test_name']}")

            # Load individual result file for error details
            result_file = self.results_dir / f"combo_{test['combo_id']:03d}.json"
            if result_file.exists():
                with open(result_file, encoding="utf-8") as f:
                    details = json.load(f)
                    print(f"  Error: {details.get('error', 'Unknown error')}")

    def export_csv(self, output_file: str = "results_export.csv"):
        """Export results to CSV for analysis in Excel/Google Sheets."""
        import csv

        results = self.summary["results"]

        output_path = self.results_dir / output_file
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "combo_id",
                    "test_name",
                    "success",
                    "estimated_tokens",
                    "validation_passed",
                ],
            )
            writer.writeheader()

            for r in results:
                writer.writerow(
                    {
                        "combo_id": r["combo_id"],
                        "test_name": r["test_name"],
                        "success": r["success"],
                        "estimated_tokens": r["estimated_tokens"],
                        "validation_passed": all(r["validation"].values()),
                    }
                )

        print(f"\n✓ Results exported to: {output_path}")

    def run_full_analysis(self):
        """Run complete analysis and print all reports."""
        self.print_overview()
        self.print_token_statistics()
        self.print_priority_impact()
        self.print_depth_impact()
        self.print_edge_case_analysis()
        self.print_failed_tests()

        print("\n" + "=" * 80)
        print("ANALYSIS COMPLETE")
        print("=" * 80)

        # Offer CSV export
        print("\nTo export results to CSV, run:")
        print("  analyzer.export_csv()")


def main():
    """Main entry point."""
    results_dir = Path(__file__).parent / "results"

    if not results_dir.exists():
        print(f"ERROR: Results directory not found: {results_dir}")
        print("Please run run_context_tests.py first.")
        return

    analyzer = ResultsAnalyzer(results_dir)
    analyzer.run_full_analysis()

    # Export CSV
    analyzer.export_csv()


if __name__ == "__main__":
    main()
