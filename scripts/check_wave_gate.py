#!/usr/bin/env python3
"""
check_wave_gate.py - Abort Detection for Existential Tests

IMP-J3: Abort Criteria for Existential Tests

This script:
1. Loads abort criteria from YAML specification
2. Checks if abort conditions are met based on test results
3. Returns appropriate halt/continue signals
4. Integrates with wave gate validation

Usage:
    python scripts/check_wave_gate.py --check-abort --validation IMP-G1
    python scripts/check_wave_gate.py --check-wave --wave 5
    python scripts/check_wave_gate.py --record-iteration --validation IMP-G1 --metrics-file results.yaml
    python scripts/check_wave_gate.py --status

Reference: .planning/testing/decision-trees/abort-criteria.yaml
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
ABORT_CRITERIA_PATH = (
    PROJECT_ROOT / ".planning/testing/decision-trees/abort-criteria.yaml"
)
ITERATIONS_PATH = PROJECT_ROOT / ".vrs/testing/existential/iterations.yaml"
DECISION_TREES_DIR = PROJECT_ROOT / ".planning/testing/decision-trees"


class Status(str, Enum):
    PASS = "PASS"
    ITERATE = "ITERATE"
    ABORT = "ABORT"
    PENDING = "PENDING"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    FATAL = "fatal"


@dataclass
class AbortCondition:
    """A single abort condition."""

    id: str
    condition: str
    check_expression: str
    action: str
    reason: str
    escalation: str | list[str]
    severity: Severity


@dataclass
class ValidationResult:
    """Result of checking a validation's abort status."""

    validation_id: str
    status: Status
    triggered_condition: AbortCondition | None = None
    iterations: int = 0
    max_iterations: int = 3
    recommendation: str = ""


@dataclass
class WaveGateResult:
    """Result of checking a wave gate."""

    wave: int
    can_pass: bool
    blocking_validations: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class IterationRecord:
    """Record of a single validation iteration."""

    iteration_id: str
    validation_id: str
    timestamp: str
    metrics: dict[str, Any]
    verdict: str
    status: Status
    notes: str = ""


def load_abort_criteria() -> dict[str, Any]:
    """Load the abort criteria YAML file."""
    if not ABORT_CRITERIA_PATH.exists():
        raise FileNotFoundError(f"Abort criteria not found: {ABORT_CRITERIA_PATH}")

    with open(ABORT_CRITERIA_PATH) as f:
        return yaml.safe_load(f)


def load_iterations() -> dict[str, list[dict[str, Any]]]:
    """Load the iterations tracking file."""
    if not ITERATIONS_PATH.exists():
        return {}

    with open(ITERATIONS_PATH) as f:
        data = yaml.safe_load(f)
        return data if data else {}


def save_iterations(iterations: dict[str, list[dict[str, Any]]]) -> None:
    """Save the iterations tracking file."""
    ITERATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ITERATIONS_PATH, "w") as f:
        yaml.dump(iterations, f, default_flow_style=False)


def flatten_run(run: dict[str, Any]) -> dict[str, Any]:
    """Flatten a run's metrics into top level for easier expression evaluation."""
    flattened = dict(run)
    if "metrics" in run:
        flattened.update(run["metrics"])
    return flattened


def get_last_n_runs(
    validation_id: str, n: int = 3
) -> list[dict[str, Any]]:
    """Get the last N runs for a validation, with flattened metrics."""
    iterations = load_iterations()
    runs = iterations.get(validation_id, [])
    result = runs[-n:] if len(runs) >= n else runs
    return [flatten_run(r) for r in result]


def get_all_runs(validation_id: str) -> list[dict[str, Any]]:
    """Get all runs for a validation, with flattened metrics."""
    iterations = load_iterations()
    runs = iterations.get(validation_id, [])
    return [flatten_run(r) for r in runs]


def evaluate_condition(
    check_expression: str, context: dict[str, Any]
) -> bool:
    """
    Evaluate an abort condition expression.

    This uses a safe evaluation with limited context.
    """
    # Build evaluation context with helper functions
    eval_context = {
        "last_n_runs": lambda n: get_last_n_runs(
            context.get("validation_id", ""), n
        ),
        "all_runs": get_all_runs(context.get("validation_id", "")),
        "latest_run": context.get("latest_run", {}),
        "all": all,
        "any": any,
        "sum": sum,
        "len": len,
        **context,
    }

    try:
        # Safe evaluation - only allow specific operations
        result = eval(check_expression, {"__builtins__": {}}, eval_context)
        return bool(result)
    except Exception as e:
        print(f"Warning: Could not evaluate condition '{check_expression}': {e}")
        return False


def check_abort_conditions(
    validation_id: str, context: dict[str, Any] | None = None
) -> ValidationResult:
    """
    Check if any abort condition is met for a validation.

    Args:
        validation_id: The validation ID (e.g., "IMP-G1_graph_ablation")
        context: Optional context dict with metrics and state

    Returns:
        ValidationResult with status and any triggered condition
    """
    criteria = load_abort_criteria()
    abort_criteria = criteria.get("abort_criteria", {})

    if validation_id not in abort_criteria:
        return ValidationResult(
            validation_id=validation_id,
            status=Status.PENDING,
            recommendation=f"Unknown validation: {validation_id}",
        )

    validation_spec = abort_criteria[validation_id]
    max_iterations = validation_spec.get("max_iterations", 3)

    # Get runs for this validation
    all_runs = get_all_runs(validation_id)
    iterations = len(all_runs)
    latest_run = all_runs[-1] if all_runs else {}

    # If no iterations yet, return PENDING (can't evaluate conditions)
    if iterations == 0:
        return ValidationResult(
            validation_id=validation_id,
            status=Status.PENDING,
            iterations=iterations,
            max_iterations=max_iterations,
            recommendation="No iterations recorded yet. Run validation first.",
        )

    # Flatten metrics from latest_run for easier expression evaluation
    flattened_latest = dict(latest_run)
    if "metrics" in latest_run:
        flattened_latest.update(latest_run["metrics"])

    # Build context for condition evaluation
    eval_context = {
        "validation_id": validation_id,
        "latest_run": flattened_latest,
        "iterations": iterations,
        **(context or {}),
    }

    # Check abort conditions
    for abort_cond in validation_spec.get("abort_conditions", []):
        condition = AbortCondition(
            id=abort_cond["id"],
            condition=abort_cond["condition"],
            check_expression=abort_cond["check_expression"],
            action=abort_cond["action"],
            reason=abort_cond["reason"],
            escalation=abort_cond["escalation"],
            severity=Severity(abort_cond.get("severity", "high")),
        )

        if evaluate_condition(condition.check_expression, eval_context):
            return ValidationResult(
                validation_id=validation_id,
                status=Status.ABORT,
                triggered_condition=condition,
                iterations=iterations,
                max_iterations=max_iterations,
                recommendation=f"ABORT: {condition.reason}. Escalation: {condition.escalation}",
            )

    # Check success conditions
    for success_cond in validation_spec.get("success_conditions", []):
        if evaluate_condition(success_cond["check_expression"], eval_context):
            return ValidationResult(
                validation_id=validation_id,
                status=Status.PASS,
                iterations=iterations,
                max_iterations=max_iterations,
                recommendation="Success condition met",
            )

    # Check continue conditions
    for continue_cond in validation_spec.get("continue_conditions", []):
        max_attempts = continue_cond.get("max_attempts", 2)
        if evaluate_condition(continue_cond["check_expression"], eval_context):
            if iterations < max_iterations:
                return ValidationResult(
                    validation_id=validation_id,
                    status=Status.ITERATE,
                    iterations=iterations,
                    max_iterations=max_iterations,
                    recommendation=f"ITERATE: {continue_cond['instruction']} (attempt {iterations}/{max_attempts})",
                )

    # If max iterations reached without success, check if we should abort
    if iterations >= max_iterations:
        return ValidationResult(
            validation_id=validation_id,
            status=Status.ABORT,
            iterations=iterations,
            max_iterations=max_iterations,
            recommendation=f"Max iterations ({max_iterations}) reached without success",
        )

    # No conditions triggered - pending
    return ValidationResult(
        validation_id=validation_id,
        status=Status.PENDING,
        iterations=iterations,
        max_iterations=max_iterations,
        recommendation="No abort conditions triggered. Continue validation.",
    )


def check_global_abort() -> tuple[bool, str | None]:
    """
    Check if global abort condition is met.

    Returns:
        (should_abort, reason)
    """
    criteria = load_abort_criteria()
    global_abort = criteria.get("global_abort", {})

    # Get status of all existential validations
    existential_validations = {
        "IMP-G1_graph_ablation": check_abort_conditions("IMP-G1_graph_ablation"),
        "IMP-H1_multi_agent": check_abort_conditions("IMP-H1_multi_agent"),
        "IMP-I1_behavioral_detection": check_abort_conditions(
            "IMP-I1_behavioral_detection"
        ),
    }

    # Count aborts
    abort_count = sum(
        1 for v in existential_validations.values() if v.status == Status.ABORT
    )

    # Check GLOBAL-ABORT-01: Any two fail
    if abort_count >= 2:
        aborted = [k for k, v in existential_validations.items() if v.status == Status.ABORT]
        return True, f"Two or more existential validations failed: {', '.join(aborted)}"

    # Check GLOBAL-ABORT-02: All three fail
    if abort_count == 3:
        return True, "All three existential validations failed - PROJECT ARCHITECTURE INVALID"

    return False, None


def check_wave_gate(wave: int) -> WaveGateResult:
    """
    Check if a wave gate can be passed.

    Args:
        wave: The wave number to check

    Returns:
        WaveGateResult with pass/fail and recommendations
    """
    criteria = load_abort_criteria()
    wave_gate = criteria.get("wave_gate", {})

    if wave == 5:
        # Wave 5 is existential validations
        validations_required = wave_gate.get("wave_5_gate", {}).get(
            "validations_required", []
        )

        blocking = []
        recommendations = []

        for validation_id in validations_required:
            result = check_abort_conditions(validation_id)

            if result.status == Status.ABORT:
                blocking.append(validation_id)
                recommendations.append(
                    f"{validation_id}: {result.recommendation}"
                )
            elif result.status == Status.ITERATE:
                recommendations.append(
                    f"{validation_id}: {result.recommendation}"
                )
            elif result.status == Status.PENDING:
                blocking.append(validation_id)
                recommendations.append(f"{validation_id}: Not yet executed")

        can_pass = len(blocking) == 0

        # Check global abort
        global_abort, global_reason = check_global_abort()
        if global_abort:
            can_pass = False
            recommendations.insert(0, f"GLOBAL ABORT: {global_reason}")

        return WaveGateResult(
            wave=wave,
            can_pass=can_pass,
            blocking_validations=blocking,
            recommendations=recommendations,
        )

    # For other waves, just return pending
    return WaveGateResult(
        wave=wave,
        can_pass=True,
        blocking_validations=[],
        recommendations=[f"Wave {wave} gate check not implemented"],
    )


def record_iteration(
    validation_id: str,
    metrics: dict[str, Any],
    verdict: str,
    status: Status,
    notes: str = "",
) -> IterationRecord:
    """
    Record a validation iteration result.

    Args:
        validation_id: The validation ID
        metrics: Metrics from the run
        verdict: The verdict (L1/L2/L3/L4)
        status: The status (PASS/ITERATE/ABORT)
        notes: Optional notes

    Returns:
        The recorded iteration
    """
    iterations = load_iterations()

    if validation_id not in iterations:
        iterations[validation_id] = []

    # Generate iteration ID
    iteration_num = len(iterations[validation_id]) + 1
    iteration_id = f"{validation_id}-iter-{iteration_num:03d}"

    record = IterationRecord(
        iteration_id=iteration_id,
        validation_id=validation_id,
        timestamp=datetime.now().isoformat(),
        metrics=metrics,
        verdict=verdict,
        status=status,
        notes=notes,
    )

    iterations[validation_id].append({
        "iteration_id": record.iteration_id,
        "validation_id": record.validation_id,
        "timestamp": record.timestamp,
        "metrics": record.metrics,
        "verdict": record.verdict,
        "status": record.status.value,
        "notes": record.notes,
    })

    save_iterations(iterations)
    return record


def get_status_report() -> dict[str, Any]:
    """Get a status report of all existential validations."""
    validations = [
        "IMP-G1_graph_ablation",
        "IMP-H1_multi_agent",
        "IMP-I1_behavioral_detection",
    ]

    report = {
        "timestamp": datetime.now().isoformat(),
        "validations": {},
        "global_status": "OK",
        "wave_5_gate": "UNKNOWN",
    }

    for validation_id in validations:
        result = check_abort_conditions(validation_id)
        report["validations"][validation_id] = {
            "status": result.status.value,
            "iterations": result.iterations,
            "max_iterations": result.max_iterations,
            "recommendation": result.recommendation,
        }

    # Check global abort
    global_abort, global_reason = check_global_abort()
    if global_abort:
        report["global_status"] = f"ABORT: {global_reason}"

    # Check wave 5 gate
    wave_result = check_wave_gate(5)
    report["wave_5_gate"] = "PASS" if wave_result.can_pass else "BLOCKED"
    report["wave_5_blockers"] = wave_result.blocking_validations
    report["wave_5_recommendations"] = wave_result.recommendations

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Check wave gates and abort conditions for existential tests"
    )

    parser.add_argument(
        "--check-abort",
        action="store_true",
        help="Check if any abort condition is met",
    )
    parser.add_argument(
        "--check-wave",
        action="store_true",
        help="Check if wave gate can be passed",
    )
    parser.add_argument(
        "--record-iteration",
        action="store_true",
        help="Record a validation iteration result",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Get status report of all validations",
    )
    parser.add_argument(
        "--validation",
        type=str,
        help="Validation ID (e.g., IMP-G1_graph_ablation)",
    )
    parser.add_argument(
        "--wave",
        type=int,
        help="Wave number to check",
    )
    parser.add_argument(
        "--metrics-file",
        type=str,
        help="Path to metrics YAML file for recording iteration",
    )
    parser.add_argument(
        "--verdict",
        type=str,
        choices=["L1", "L2", "L3", "L4"],
        help="Verdict for recording iteration",
    )
    parser.add_argument(
        "--notes",
        type=str,
        default="",
        help="Optional notes for recording iteration",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    args = parser.parse_args()

    if args.check_abort:
        if not args.validation:
            parser.error("--check-abort requires --validation")

        result = check_abort_conditions(args.validation)

        if args.json:
            output = {
                "validation_id": result.validation_id,
                "status": result.status.value,
                "iterations": result.iterations,
                "max_iterations": result.max_iterations,
                "abort": result.status == Status.ABORT,
                "recommendation": result.recommendation,
            }
            if result.triggered_condition:
                output["triggered_condition"] = {
                    "id": result.triggered_condition.id,
                    "reason": result.triggered_condition.reason,
                    "escalation": result.triggered_condition.escalation,
                    "severity": result.triggered_condition.severity.value,
                }
            print(json.dumps(output, indent=2))
        else:
            print(f"Validation: {result.validation_id}")
            print(f"Status: {result.status.value}")
            print(f"Iterations: {result.iterations}/{result.max_iterations}")
            print(f"Recommendation: {result.recommendation}")
            if result.triggered_condition:
                print(f"\nTriggered Condition:")
                print(f"  ID: {result.triggered_condition.id}")
                print(f"  Reason: {result.triggered_condition.reason}")
                print(f"  Escalation: {result.triggered_condition.escalation}")
                print(f"  Severity: {result.triggered_condition.severity.value}")

        sys.exit(1 if result.status == Status.ABORT else 0)

    elif args.check_wave:
        if not args.wave:
            parser.error("--check-wave requires --wave")

        result = check_wave_gate(args.wave)

        if args.json:
            output = {
                "wave": result.wave,
                "can_pass": result.can_pass,
                "blocking_validations": result.blocking_validations,
                "recommendations": result.recommendations,
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"Wave {result.wave} Gate Check")
            print(f"Can Pass: {'YES' if result.can_pass else 'NO'}")
            if result.blocking_validations:
                print(f"Blocking: {', '.join(result.blocking_validations)}")
            if result.recommendations:
                print("Recommendations:")
                for rec in result.recommendations:
                    print(f"  - {rec}")

        sys.exit(0 if result.can_pass else 1)

    elif args.record_iteration:
        if not args.validation:
            parser.error("--record-iteration requires --validation")
        if not args.metrics_file:
            parser.error("--record-iteration requires --metrics-file")
        if not args.verdict:
            parser.error("--record-iteration requires --verdict")

        # Load metrics
        metrics_path = Path(args.metrics_file)
        if not metrics_path.exists():
            parser.error(f"Metrics file not found: {args.metrics_file}")

        with open(metrics_path) as f:
            metrics = yaml.safe_load(f)

        # Determine status from verdict
        verdict_status = {
            "L1": Status.PASS,
            "L2": Status.PASS,
            "L3": Status.ITERATE,
            "L4": Status.ABORT,
        }
        status = verdict_status.get(args.verdict, Status.PENDING)

        record = record_iteration(
            validation_id=args.validation,
            metrics=metrics,
            verdict=args.verdict,
            status=status,
            notes=args.notes,
        )

        if args.json:
            output = {
                "iteration_id": record.iteration_id,
                "validation_id": record.validation_id,
                "timestamp": record.timestamp,
                "verdict": record.verdict,
                "status": record.status.value,
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"Recorded iteration: {record.iteration_id}")
            print(f"Validation: {record.validation_id}")
            print(f"Verdict: {record.verdict}")
            print(f"Status: {record.status.value}")

    elif args.status:
        report = get_status_report()

        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print("=" * 60)
            print("Existential Validation Status Report")
            print("=" * 60)
            print(f"Timestamp: {report['timestamp']}")
            print(f"Global Status: {report['global_status']}")
            print(f"Wave 5 Gate: {report['wave_5_gate']}")
            print()
            print("Validations:")
            for val_id, val_status in report["validations"].items():
                print(f"\n  {val_id}:")
                print(f"    Status: {val_status['status']}")
                print(f"    Iterations: {val_status['iterations']}/{val_status['max_iterations']}")
                print(f"    Recommendation: {val_status['recommendation']}")
            print()
            if report.get("wave_5_blockers"):
                print("Wave 5 Blockers:")
                for blocker in report["wave_5_blockers"]:
                    print(f"  - {blocker}")
            if report.get("wave_5_recommendations"):
                print("Wave 5 Recommendations:")
                for rec in report["wave_5_recommendations"]:
                    print(f"  - {rec}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
