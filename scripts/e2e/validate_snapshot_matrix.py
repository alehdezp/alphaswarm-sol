#!/usr/bin/env python3
"""
Validate snapshot matrix completeness for E2E testing.

This validator reads the worktree_snapshot_policy.yaml and verifies that
all required snapshots exist for each scenario in an evidence pack.

Usage:
    python validate_snapshot_matrix.py <evidence_pack_path>
    python validate_snapshot_matrix.py <evidence_pack_path> --scenario S01,S02
    python validate_snapshot_matrix.py <evidence_pack_path> --strict
    python validate_snapshot_matrix.py <evidence_pack_path> --json

Exit codes:
    0 - All required snapshots present
    1 - Missing required snapshots
    2 - Invalid arguments or configuration
    3 - Evidence pack not found

Author: AlphaSwarm.sol Team
Version: 1.0.0
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class SnapshotStage:
    """Represents a snapshot stage."""

    id: str
    description: str
    artifacts: list[str]
    order: int


@dataclass
class CategoryPolicy:
    """Represents a category's snapshot policy."""

    name: str
    description: str
    scenario_range: tuple[str, str]
    required_stages: list[str]
    optional_stages: list[str] = field(default_factory=list)
    conditional_stages: list[str] = field(default_factory=list)
    rationale: str = ""


@dataclass
class ValidationResult:
    """Result of validating a single scenario."""

    scenario_id: str
    category: str
    required_stages: list[str]
    present_stages: list[str]
    missing_stages: list[str]
    optional_missing: list[str]
    is_complete: bool
    manifest_found: bool
    errors: list[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    """Overall validation report."""

    evidence_pack_path: str
    scenarios_validated: int
    scenarios_complete: int
    scenarios_incomplete: int
    total_missing_stages: int
    results: list[ValidationResult]
    policy_version: str
    is_valid: bool


class SnapshotPolicyLoader:
    """Loads and parses the worktree snapshot policy."""

    def __init__(self, policy_path: Path | None = None):
        if policy_path is None:
            # Default to configs/worktree_snapshot_policy.yaml
            self.policy_path = Path(__file__).parent.parent.parent / "configs" / "worktree_snapshot_policy.yaml"
        else:
            self.policy_path = Path(policy_path)

        self.policy: dict[str, Any] = {}
        self.stages: dict[str, SnapshotStage] = {}
        self.categories: dict[str, CategoryPolicy] = {}

    def load(self) -> bool:
        """Load the policy file."""
        if not self.policy_path.exists():
            print(f"Error: Policy file not found: {self.policy_path}", file=sys.stderr)
            return False

        with open(self.policy_path) as f:
            self.policy = yaml.safe_load(f)

        self._parse_stages()
        self._parse_categories()
        return True

    def _parse_stages(self) -> None:
        """Parse stage definitions."""
        for stage_def in self.policy.get("stages", []):
            stage = SnapshotStage(
                id=stage_def["id"],
                description=stage_def.get("description", ""),
                artifacts=stage_def.get("artifacts", []),
                order=stage_def.get("order", 0),
            )
            self.stages[stage.id] = stage

    def _parse_categories(self) -> None:
        """Parse category definitions."""
        for name, cat_def in self.policy.get("categories", {}).items():
            scenario_range = cat_def.get("scenario_range", ["S00", "S00"])
            category = CategoryPolicy(
                name=name,
                description=cat_def.get("description", ""),
                scenario_range=(scenario_range[0], scenario_range[1]),
                required_stages=cat_def.get("required_stages", []),
                optional_stages=cat_def.get("optional_stages", []),
                conditional_stages=cat_def.get("conditional_stages", []),
                rationale=cat_def.get("rationale", ""),
            )
            self.categories[name] = category

    def get_version(self) -> str:
        """Get policy version."""
        return self.policy.get("version", "unknown")

    def get_category_for_scenario(self, scenario_id: str) -> CategoryPolicy | None:
        """Find the category for a given scenario ID."""
        # Extract numeric part from scenario ID (e.g., S01 -> 1)
        try:
            num = int(scenario_id[1:])
        except (ValueError, IndexError):
            return None

        for category in self.categories.values():
            start_num = int(category.scenario_range[0][1:])
            end_num = int(category.scenario_range[1][1:])
            if start_num <= num <= end_num:
                return category

        return None

    def get_required_stages(self, scenario_id: str) -> list[str]:
        """Get required stages for a scenario."""
        category = self.get_category_for_scenario(scenario_id)
        if category:
            return category.required_stages
        # Default to minimum stages
        return self.policy.get("validation", {}).get("minimum_stages", ["pre-graph", "post-report"])


class SnapshotValidator:
    """Validates snapshot completeness for evidence packs."""

    def __init__(self, policy: SnapshotPolicyLoader, strict: bool = False):
        self.policy = policy
        self.strict = strict

    def validate_snapshots(
        self,
        evidence_pack_path: Path,
        scenarios: list[str] | None = None,
    ) -> ValidationReport:
        """Validate all snapshots in an evidence pack."""
        results: list[ValidationResult] = []
        snapshots_dir = evidence_pack_path / "snapshots"

        if not snapshots_dir.exists():
            # Check for alternate structure
            snapshots_dir = evidence_pack_path

        # Discover scenarios to validate
        if scenarios:
            scenario_ids = scenarios
        else:
            scenario_ids = self._discover_scenarios(snapshots_dir)

        for scenario_id in scenario_ids:
            result = self._validate_scenario(snapshots_dir, scenario_id)
            results.append(result)

        # Calculate summary
        complete = sum(1 for r in results if r.is_complete)
        incomplete = len(results) - complete
        total_missing = sum(len(r.missing_stages) for r in results)

        is_valid = incomplete == 0 if self.strict else total_missing == 0

        return ValidationReport(
            evidence_pack_path=str(evidence_pack_path),
            scenarios_validated=len(results),
            scenarios_complete=complete,
            scenarios_incomplete=incomplete,
            total_missing_stages=total_missing,
            results=results,
            policy_version=self.policy.get_version(),
            is_valid=is_valid,
        )

    def _discover_scenarios(self, snapshots_dir: Path) -> list[str]:
        """Discover scenario IDs from the snapshots directory."""
        scenarios: list[str] = []

        if not snapshots_dir.exists():
            return scenarios

        for item in snapshots_dir.iterdir():
            if item.is_dir() and item.name.startswith("S"):
                scenarios.append(item.name)

        return sorted(scenarios, key=lambda s: int(s[1:]) if s[1:].isdigit() else 0)

    def _validate_scenario(self, snapshots_dir: Path, scenario_id: str) -> ValidationResult:
        """Validate a single scenario's snapshots."""
        category = self.policy.get_category_for_scenario(scenario_id)
        category_name = category.name if category else "unknown"
        required_stages = self.policy.get_required_stages(scenario_id)
        optional_stages = category.optional_stages if category else []

        scenario_dir = snapshots_dir / scenario_id
        present_stages: list[str] = []
        missing_stages: list[str] = []
        optional_missing: list[str] = []
        errors: list[str] = []
        manifest_found = False

        # Check for manifest
        manifest_path = scenario_dir / "manifest.yaml"
        if manifest_path.exists():
            manifest_found = True
            # Validate manifest against actual files
            try:
                with open(manifest_path) as f:
                    manifest = yaml.safe_load(f)
                stages_in_manifest = [s.get("stage") for s in manifest.get("stages_captured", [])]
                present_stages = stages_in_manifest
            except yaml.YAMLError as e:
                errors.append(f"Invalid manifest YAML: {e}")
        else:
            # Discover stages from files
            if scenario_dir.exists():
                for stage_id in self.policy.stages:
                    stage_file = scenario_dir / f"{stage_id}.tar.gz"
                    if stage_file.exists():
                        present_stages.append(stage_id)

        # Check required stages
        for stage in required_stages:
            if stage not in present_stages:
                missing_stages.append(stage)

        # Check optional stages
        for stage in optional_stages:
            if stage not in present_stages:
                optional_missing.append(stage)

        is_complete = len(missing_stages) == 0

        return ValidationResult(
            scenario_id=scenario_id,
            category=category_name,
            required_stages=required_stages,
            present_stages=present_stages,
            missing_stages=missing_stages,
            optional_missing=optional_missing,
            is_complete=is_complete,
            manifest_found=manifest_found,
            errors=errors,
        )


def format_report_text(report: ValidationReport) -> str:
    """Format the validation report as text."""
    lines = [
        "=" * 70,
        " Snapshot Matrix Validation Report",
        "=" * 70,
        "",
        f"Evidence Pack:      {report.evidence_pack_path}",
        f"Policy Version:     {report.policy_version}",
        f"Scenarios Checked:  {report.scenarios_validated}",
        f"Complete:           {report.scenarios_complete}",
        f"Incomplete:         {report.scenarios_incomplete}",
        f"Total Missing:      {report.total_missing_stages}",
        f"Status:             {'PASS' if report.is_valid else 'FAIL'}",
        "",
    ]

    if report.total_missing_stages > 0:
        lines.append("-" * 70)
        lines.append(" Missing Snapshots by Scenario")
        lines.append("-" * 70)
        lines.append("")

        for result in report.results:
            if result.missing_stages:
                lines.append(f"  {result.scenario_id} ({result.category}):")
                lines.append(f"    Required: {', '.join(result.required_stages)}")
                lines.append(f"    Present:  {', '.join(result.present_stages) or '(none)'}")
                lines.append(f"    Missing:  {', '.join(result.missing_stages)}")
                if result.errors:
                    lines.append(f"    Errors:   {'; '.join(result.errors)}")
                lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)


def format_report_json(report: ValidationReport) -> str:
    """Format the validation report as JSON."""
    data = {
        "evidence_pack_path": report.evidence_pack_path,
        "policy_version": report.policy_version,
        "summary": {
            "scenarios_validated": report.scenarios_validated,
            "scenarios_complete": report.scenarios_complete,
            "scenarios_incomplete": report.scenarios_incomplete,
            "total_missing_stages": report.total_missing_stages,
            "is_valid": report.is_valid,
        },
        "results": [
            {
                "scenario_id": r.scenario_id,
                "category": r.category,
                "required_stages": r.required_stages,
                "present_stages": r.present_stages,
                "missing_stages": r.missing_stages,
                "optional_missing": r.optional_missing,
                "is_complete": r.is_complete,
                "manifest_found": r.manifest_found,
                "errors": r.errors,
            }
            for r in report.results
        ],
    }
    return json.dumps(data, indent=2)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate snapshot matrix completeness for E2E testing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s /path/to/evidence-pack
    %(prog)s /path/to/evidence-pack --scenario S01,S02,S03
    %(prog)s /path/to/evidence-pack --strict --json
        """,
    )
    parser.add_argument(
        "evidence_pack",
        type=str,
        help="Path to the evidence pack directory",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        help="Comma-separated scenario IDs to validate (e.g., S01,S02)",
    )
    parser.add_argument(
        "--policy",
        type=str,
        help="Path to custom policy file (default: configs/worktree_snapshot_policy.yaml)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if any scenario is incomplete",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output report as JSON",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output on failure",
    )

    args = parser.parse_args()

    # Check evidence pack exists
    evidence_path = Path(args.evidence_pack)
    if not evidence_path.exists():
        print(f"Error: Evidence pack not found: {evidence_path}", file=sys.stderr)
        return 3

    # Load policy
    policy_path = Path(args.policy) if args.policy else None
    policy = SnapshotPolicyLoader(policy_path)
    if not policy.load():
        return 2

    # Parse scenarios
    scenarios = None
    if args.scenario:
        scenarios = [s.strip() for s in args.scenario.split(",")]

    # Validate
    validator = SnapshotValidator(policy, strict=args.strict)
    report = validator.validate_snapshots(evidence_path, scenarios)

    # Output
    if not args.quiet or not report.is_valid:
        if args.json:
            print(format_report_json(report))
        else:
            print(format_report_text(report))

    return 0 if report.is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
