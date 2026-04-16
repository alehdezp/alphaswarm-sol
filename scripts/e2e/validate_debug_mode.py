#!/usr/bin/env python3
"""
Debug Mode Validator for AlphaSwarm E2E Testing

Validates that all required debug artifacts are present and valid
according to the debug_mode_matrix.yaml specification.

Exit codes:
- 0: All validations passed
- 1: Validation failed (missing/invalid debug artifacts)
- 2: Configuration error (missing matrix, bad paths)

Usage:
    python validate_debug_mode.py evidence/debug/
    python validate_debug_mode.py evidence/debug/ --matrix configs/debug_mode_matrix.yaml
    python validate_debug_mode.py evidence/debug/ --strict
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


# =============================================================================
# Error Codes (match DEBUG-MODE-ENFORCEMENT.md)
# =============================================================================
E012 = "E012"  # MISSING_DEBUG_RECORD
E013 = "E013"  # INCOMPLETE_DEBUG_RECORD
E014 = "E014"  # INVALID_DURATION
E015 = "E015"  # INVALID_TIMESTAMPS
E016 = "E016"  # UNKNOWN_SKILL_AGENT
E017 = "E017"  # EMPTY_REQUIRED_FIELD
E018 = "E018"  # DEBUG_MODE_DISABLED
E019 = "E019"  # DEBUG_DIR_NOT_WRITABLE
E020 = "E020"  # EMPTY_DEBUG_MATRIX


# =============================================================================
# Data Classes
# =============================================================================
@dataclass
class ValidationError:
    """Represents a single validation error."""

    code: str
    message: str
    skill_or_agent: str = ""
    record_path: str = ""
    field: str = ""

    def __str__(self) -> str:
        parts = [f"ERROR {self.code}:"]
        if self.skill_or_agent:
            parts.append(f"[{self.skill_or_agent}]")
        parts.append(self.message)
        if self.record_path:
            parts.append(f"\n  Record: {self.record_path}")
        if self.field:
            parts.append(f"\n  Field: {self.field}")
        return " ".join(parts)


@dataclass
class ValidationResult:
    """Result of validation run."""

    passed: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    def add_error(self, error: ValidationError) -> None:
        """Add an error and mark as failed."""
        self.errors.append(error)
        self.passed = False

    def add_warning(self, warning: str) -> None:
        """Add a warning (does not fail validation)."""
        self.warnings.append(warning)


@dataclass
class DebugRequirements:
    """Requirements for a skill or agent."""

    debug_required: bool
    inputs: list[str]
    tool_calls: str  # 'required' | 'optional'
    bskg_queries: str  # 'required' | 'optional'
    outputs: list[str]
    min_duration_ms: int


# =============================================================================
# Matrix Loader
# =============================================================================
def load_debug_matrix(matrix_path: Path) -> dict[str, dict[str, DebugRequirements]]:
    """Load and parse the debug mode matrix."""
    if not matrix_path.exists():
        raise FileNotFoundError(f"Debug matrix not found: {matrix_path}")

    with open(matrix_path) as f:
        raw = yaml.safe_load(f)

    if not raw:
        raise ValueError(f"{E020}: Empty debug matrix")

    result: dict[str, dict[str, DebugRequirements]] = {"skills": {}, "agents": {}}

    # Parse skills
    for skill_id, spec in raw.get("skills", {}).items():
        if spec is None:
            continue
        result["skills"][skill_id] = DebugRequirements(
            debug_required=spec.get("debug_required", True),
            inputs=spec.get("inputs", []),
            tool_calls=spec.get("tool_calls", "optional"),
            bskg_queries=spec.get("bskg_queries", "optional"),
            outputs=spec.get("outputs", []),
            min_duration_ms=spec.get("min_duration_ms", 1000),
        )

    # Parse agents
    for agent_id, spec in raw.get("agents", {}).items():
        if spec is None:
            continue
        result["agents"][agent_id] = DebugRequirements(
            debug_required=spec.get("debug_required", True),
            inputs=spec.get("inputs", []),
            tool_calls=spec.get("tool_calls", "optional"),
            bskg_queries=spec.get("bskg_queries", "optional"),
            outputs=spec.get("outputs", []),
            min_duration_ms=spec.get("min_duration_ms", 1000),
        )

    return result


# =============================================================================
# Record Validation
# =============================================================================
def validate_debug_record(
    record_path: Path,
    record: dict[str, Any],
    requirements: DebugRequirements,
) -> list[ValidationError]:
    """Validate a single debug record against requirements."""
    errors: list[ValidationError] = []
    skill_or_agent = record.get("skill_or_agent", "unknown")

    # Check record_id
    record_id = record.get("record_id", "")
    if not record_id or not isinstance(record_id, str) or record_id.strip() == "":
        errors.append(
            ValidationError(
                code=E017,
                message="record_id is missing or empty",
                skill_or_agent=skill_or_agent,
                record_path=str(record_path),
                field="record_id",
            )
        )

    # Check timestamps
    timestamp_start = record.get("timestamp_start", "")
    timestamp_end = record.get("timestamp_end", "")

    if not timestamp_start or not timestamp_end:
        errors.append(
            ValidationError(
                code=E015,
                message="timestamps missing",
                skill_or_agent=skill_or_agent,
                record_path=str(record_path),
                field="timestamp_start/timestamp_end",
            )
        )
    else:
        try:
            start_dt = datetime.fromisoformat(timestamp_start.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(timestamp_end.replace("Z", "+00:00"))

            # Check for epoch zero (fake timestamps)
            if start_dt.year < 2020:
                errors.append(
                    ValidationError(
                        code=E015,
                        message=f"timestamp_start appears fake: {timestamp_start}",
                        skill_or_agent=skill_or_agent,
                        record_path=str(record_path),
                        field="timestamp_start",
                    )
                )

            # Check for future timestamps
            now = datetime.now(start_dt.tzinfo) if start_dt.tzinfo else datetime.now()
            if start_dt > now:
                errors.append(
                    ValidationError(
                        code=E015,
                        message=f"timestamp_start is in the future: {timestamp_start}",
                        skill_or_agent=skill_or_agent,
                        record_path=str(record_path),
                        field="timestamp_start",
                    )
                )

            # Check start < end
            if start_dt >= end_dt:
                errors.append(
                    ValidationError(
                        code=E015,
                        message="timestamp_start >= timestamp_end",
                        skill_or_agent=skill_or_agent,
                        record_path=str(record_path),
                        field="timestamps",
                    )
                )
        except ValueError as e:
            errors.append(
                ValidationError(
                    code=E015,
                    message=f"invalid timestamp format: {e}",
                    skill_or_agent=skill_or_agent,
                    record_path=str(record_path),
                    field="timestamps",
                )
            )

    # Check duration
    duration_ms = record.get("duration_ms", 0)
    if not isinstance(duration_ms, int | float) or duration_ms <= 0:
        errors.append(
            ValidationError(
                code=E014,
                message=f"duration_ms is invalid: {duration_ms} (must be > 0)",
                skill_or_agent=skill_or_agent,
                record_path=str(record_path),
                field="duration_ms",
            )
        )
    elif duration_ms < requirements.min_duration_ms:
        errors.append(
            ValidationError(
                code=E014,
                message=(
                    f"duration_ms too low: {duration_ms} < {requirements.min_duration_ms} "
                    "(possible mock execution)"
                ),
                skill_or_agent=skill_or_agent,
                record_path=str(record_path),
                field="duration_ms",
            )
        )

    # Check inputs
    inputs = record.get("inputs", {})
    if not inputs or not isinstance(inputs, dict):
        errors.append(
            ValidationError(
                code=E013,
                message="inputs section missing or invalid",
                skill_or_agent=skill_or_agent,
                record_path=str(record_path),
                field="inputs",
            )
        )
    else:
        # Check required input fields
        for required_field in requirements.inputs:
            value = inputs.get(required_field)
            if value is None:
                errors.append(
                    ValidationError(
                        code=E013,
                        message=f"required input field missing: {required_field}",
                        skill_or_agent=skill_or_agent,
                        record_path=str(record_path),
                        field=f"inputs.{required_field}",
                    )
                )
            elif isinstance(value, str) and value.strip() == "":
                errors.append(
                    ValidationError(
                        code=E017,
                        message=f"required input field is empty: {required_field}",
                        skill_or_agent=skill_or_agent,
                        record_path=str(record_path),
                        field=f"inputs.{required_field}",
                    )
                )

    # Check tool_calls
    tool_calls = record.get("tool_calls")
    if tool_calls is None:
        errors.append(
            ValidationError(
                code=E013,
                message="tool_calls field missing",
                skill_or_agent=skill_or_agent,
                record_path=str(record_path),
                field="tool_calls",
            )
        )
    elif requirements.tool_calls == "required" and len(tool_calls) == 0:
        errors.append(
            ValidationError(
                code=E013,
                message="tool_calls is required but empty",
                skill_or_agent=skill_or_agent,
                record_path=str(record_path),
                field="tool_calls",
            )
        )

    # Check bskg_queries
    bskg_queries = record.get("bskg_queries")
    if bskg_queries is None:
        errors.append(
            ValidationError(
                code=E013,
                message="bskg_queries field missing",
                skill_or_agent=skill_or_agent,
                record_path=str(record_path),
                field="bskg_queries",
            )
        )
    elif requirements.bskg_queries == "required" and len(bskg_queries) == 0:
        errors.append(
            ValidationError(
                code=E013,
                message="bskg_queries is required but empty",
                skill_or_agent=skill_or_agent,
                record_path=str(record_path),
                field="bskg_queries",
            )
        )

    # Check outputs
    outputs = record.get("outputs", {})
    if not outputs or not isinstance(outputs, dict):
        errors.append(
            ValidationError(
                code=E013,
                message="outputs section missing or invalid",
                skill_or_agent=skill_or_agent,
                record_path=str(record_path),
                field="outputs",
            )
        )
    else:
        # Check final_response (always required)
        final_response = outputs.get("final_response", "")
        if not final_response or (
            isinstance(final_response, str) and final_response.strip() == ""
        ):
            errors.append(
                ValidationError(
                    code=E017,
                    message="outputs.final_response is empty",
                    skill_or_agent=skill_or_agent,
                    record_path=str(record_path),
                    field="outputs.final_response",
                )
            )

        # Check additional required output fields
        for required_field in requirements.outputs:
            if required_field == "final_response":
                continue  # Already checked above
            value = outputs.get(required_field)
            if value is None:
                errors.append(
                    ValidationError(
                        code=E013,
                        message=f"required output field missing: {required_field}",
                        skill_or_agent=skill_or_agent,
                        record_path=str(record_path),
                        field=f"outputs.{required_field}",
                    )
                )

    return errors


# =============================================================================
# Main Validation Logic
# =============================================================================
def validate_debug_directory(
    debug_dir: Path,
    matrix: dict[str, dict[str, DebugRequirements]],
    strict: bool = False,
) -> ValidationResult:
    """
    Validate all debug records in a directory against the matrix.

    Args:
        debug_dir: Path to evidence/debug/ directory
        matrix: Loaded debug requirements matrix
        strict: If True, fail on any unknown skill/agent

    Returns:
        ValidationResult with errors and stats
    """
    result = ValidationResult(passed=True)

    if not debug_dir.exists():
        result.add_error(
            ValidationError(
                code=E019,
                message=f"Debug directory does not exist: {debug_dir}",
            )
        )
        return result

    # Track what we've seen
    seen_skills: set[str] = set()
    seen_agents: set[str] = set()
    total_records = 0
    valid_records = 0

    # Check index file
    index_path = debug_dir / "index.json"
    if index_path.exists():
        with open(index_path) as f:
            index = json.load(f)
        result.stats["run_id"] = index.get("run_id", "unknown")
        result.stats["index_records"] = len(index.get("records", []))
    else:
        result.add_warning("No index.json found - checking all JSON files")

    # Scan skills directory
    skills_dir = debug_dir / "skills"
    if skills_dir.exists():
        for record_path in skills_dir.glob("*.json"):
            total_records += 1
            try:
                with open(record_path) as f:
                    record = json.load(f)

                skill_id = record.get("skill_or_agent", "").replace("/vrs-", "")
                if not skill_id:
                    # Try to extract from filename
                    skill_id = record_path.stem.split("-")[0]

                seen_skills.add(skill_id)

                # Get requirements
                if skill_id not in matrix["skills"]:
                    if strict:
                        result.add_error(
                            ValidationError(
                                code=E016,
                                message=f"Unknown skill not in matrix: {skill_id}",
                                skill_or_agent=skill_id,
                                record_path=str(record_path),
                            )
                        )
                    else:
                        result.add_warning(f"Unknown skill: {skill_id}")
                    continue

                requirements = matrix["skills"][skill_id]
                if not requirements.debug_required:
                    continue  # Skip dev-only skills

                errors = validate_debug_record(record_path, record, requirements)
                if errors:
                    for error in errors:
                        result.add_error(error)
                else:
                    valid_records += 1

            except json.JSONDecodeError as e:
                result.add_error(
                    ValidationError(
                        code=E013,
                        message=f"Invalid JSON: {e}",
                        record_path=str(record_path),
                    )
                )
            except Exception as e:
                result.add_error(
                    ValidationError(
                        code=E013,
                        message=f"Failed to read record: {e}",
                        record_path=str(record_path),
                    )
                )

    # Scan agents directory
    agents_dir = debug_dir / "agents"
    if agents_dir.exists():
        for record_path in agents_dir.glob("*.json"):
            total_records += 1
            try:
                with open(record_path) as f:
                    record = json.load(f)

                agent_id = record.get("skill_or_agent", "")
                if not agent_id:
                    # Try to extract from filename
                    parts = record_path.stem.split("-")
                    if len(parts) >= 2:
                        agent_id = f"{parts[0]}-{parts[1]}"

                seen_agents.add(agent_id)

                # Get requirements
                if agent_id not in matrix["agents"]:
                    if strict:
                        result.add_error(
                            ValidationError(
                                code=E016,
                                message=f"Unknown agent not in matrix: {agent_id}",
                                skill_or_agent=agent_id,
                                record_path=str(record_path),
                            )
                        )
                    else:
                        result.add_warning(f"Unknown agent: {agent_id}")
                    continue

                requirements = matrix["agents"][agent_id]
                if not requirements.debug_required:
                    continue

                errors = validate_debug_record(record_path, record, requirements)
                if errors:
                    for error in errors:
                        result.add_error(error)
                else:
                    valid_records += 1

            except json.JSONDecodeError as e:
                result.add_error(
                    ValidationError(
                        code=E013,
                        message=f"Invalid JSON: {e}",
                        record_path=str(record_path),
                    )
                )
            except Exception as e:
                result.add_error(
                    ValidationError(
                        code=E013,
                        message=f"Failed to read record: {e}",
                        record_path=str(record_path),
                    )
                )

    # Check for missing required skills/agents
    required_skills = {
        sid for sid, req in matrix["skills"].items() if req.debug_required
    }
    required_agents = {
        aid for aid, req in matrix["agents"].items() if req.debug_required
    }

    missing_skills = required_skills - seen_skills
    missing_agents = required_agents - seen_agents

    # Only report missing if we found ANY records (otherwise it's likely a wrong path)
    if total_records > 0 and strict:
        for skill_id in missing_skills:
            result.add_error(
                ValidationError(
                    code=E012,
                    message=f"No debug record found for required skill: {skill_id}",
                    skill_or_agent=skill_id,
                )
            )

        for agent_id in missing_agents:
            result.add_error(
                ValidationError(
                    code=E012,
                    message=f"No debug record found for required agent: {agent_id}",
                    skill_or_agent=agent_id,
                )
            )

    # Populate stats
    result.stats.update(
        {
            "total_records": total_records,
            "valid_records": valid_records,
            "error_count": len(result.errors),
            "skills_seen": len(seen_skills),
            "skills_required": len(required_skills),
            "skills_coverage": (
                len(seen_skills & required_skills) / len(required_skills) * 100
                if required_skills
                else 0
            ),
            "agents_seen": len(seen_agents),
            "agents_required": len(required_agents),
            "agents_coverage": (
                len(seen_agents & required_agents) / len(required_agents) * 100
                if required_agents
                else 0
            ),
        }
    )

    return result


# =============================================================================
# Report Generation
# =============================================================================
def print_report(result: ValidationResult) -> None:
    """Print validation report to stdout."""
    print("=" * 70)
    print("DEBUG MODE VALIDATION REPORT")
    print("=" * 70)
    print()

    # Summary
    status = "PASSED" if result.passed else "FAILED"
    print(f"Status: {status}")
    print(f"Total Records: {result.stats.get('total_records', 0)}")
    print(f"Valid Records: {result.stats.get('valid_records', 0)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Warnings: {len(result.warnings)}")
    print()

    # Coverage
    print("Coverage:")
    print(
        f"  Skills: {result.stats.get('skills_seen', 0)}/{result.stats.get('skills_required', 0)} "
        f"({result.stats.get('skills_coverage', 0):.1f}%)"
    )
    print(
        f"  Agents: {result.stats.get('agents_seen', 0)}/{result.stats.get('agents_required', 0)} "
        f"({result.stats.get('agents_coverage', 0):.1f}%)"
    )
    print()

    # Errors
    if result.errors:
        print("ERRORS:")
        print("-" * 70)
        for error in result.errors:
            print(str(error))
            print()

    # Warnings
    if result.warnings:
        print("WARNINGS:")
        print("-" * 70)
        for warning in result.warnings:
            print(f"  - {warning}")
        print()

    print("=" * 70)


# =============================================================================
# CLI Entry Point
# =============================================================================
def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate debug mode artifacts for AlphaSwarm E2E testing"
    )
    parser.add_argument(
        "debug_dir",
        type=Path,
        help="Path to evidence/debug/ directory",
    )
    parser.add_argument(
        "--matrix",
        type=Path,
        default=Path("configs/debug_mode_matrix.yaml"),
        help="Path to debug mode matrix YAML (default: configs/debug_mode_matrix.yaml)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on unknown skills/agents and missing coverage",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output errors (no summary)",
    )

    args = parser.parse_args()

    # Load matrix
    try:
        matrix = load_debug_matrix(args.matrix)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    # Run validation
    result = validate_debug_directory(args.debug_dir, matrix, strict=args.strict)

    # Output results
    if args.json:
        output = {
            "passed": result.passed,
            "errors": [
                {
                    "code": e.code,
                    "message": e.message,
                    "skill_or_agent": e.skill_or_agent,
                    "record_path": e.record_path,
                    "field": e.field,
                }
                for e in result.errors
            ],
            "warnings": result.warnings,
            "stats": result.stats,
        }
        print(json.dumps(output, indent=2))
    elif not args.quiet:
        print_report(result)
    else:
        # Quiet mode - only show errors
        for error in result.errors:
            print(str(error), file=sys.stderr)

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
