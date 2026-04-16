#!/usr/bin/env python3
"""
Validate BSKG graph output against expected properties.

This script validates that alphaswarm build-kg produces correct
knowledge graphs with:
- Expected function nodes
- Required semantic operations
- Correct security properties
- Behavioral signatures

Usage:
    uv run python scripts/validate_graph.py --graph .vrs/graphs/project.toon
    uv run python scripts/validate_graph.py --graph .vrs/graphs/project.toon --expected expected/graph-checks.json
    uv run python scripts/validate_graph.py --help

Examples:
    # Basic validation (checks graph structure)
    uv run python scripts/validate_graph.py --graph .vrs/graphs/Vault.toon

    # Full validation against expected properties
    uv run python scripts/validate_graph.py \\
        --graph .vrs/graphs/Vault.toon \\
        --expected tests/fixtures/foundry-vault/expected/graph-checks.json

    # With output file
    uv run python scripts/validate_graph.py \\
        --graph .vrs/graphs/Vault.toon \\
        --expected expected/graph-checks.json \\
        --output validation-results.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional

# Add src to path for TOON parser
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from alphaswarm_sol.kg.toon import toon_loads
except ImportError:
    toon_loads = None


@dataclass
class ValidationResult:
    """Result of a single validation check."""
    passed: bool
    check_name: str
    check_type: str
    expected: Any
    actual: Any
    message: str


def load_graph(graph_path: Path) -> dict:
    """Load graph from TOON or JSON format.

    Args:
        graph_path: Path to graph file (.toon or .json)

    Returns:
        Parsed graph as dictionary

    Raises:
        ImportError: If TOON parser not available for .toon files
        ValueError: If file format not supported
    """
    content = graph_path.read_text()

    if graph_path.suffix == ".toon":
        if toon_loads is None:
            raise ImportError(
                "TOON parser not available. "
                "Ensure alphaswarm_sol is installed: uv pip install -e ."
            )
        return toon_loads(content)
    elif graph_path.suffix == ".json":
        return json.loads(content)
    else:
        raise ValueError(f"Unsupported graph format: {graph_path.suffix}")


def find_function(graph: dict, func_name: str) -> Optional[dict]:
    """Find a function node by name in the graph.

    Args:
        graph: Parsed graph dictionary
        func_name: Name of function to find

    Returns:
        Function node dictionary or None if not found
    """
    for node in graph.get("nodes", []):
        if node.get("type") == "function" and node.get("name") == func_name:
            return node
    return None


def get_all_operations(graph: dict) -> set[str]:
    """Get all semantic operations present in the graph.

    Args:
        graph: Parsed graph dictionary

    Returns:
        Set of operation names found
    """
    operations = set()

    for node in graph.get("nodes", []):
        # Check operations field
        if "operations" in node:
            ops = node["operations"]
            if isinstance(ops, list):
                operations.update(ops)
            elif isinstance(ops, str):
                operations.add(ops)

        # Check properties.operations
        props = node.get("properties", {})
        if "operations" in props:
            ops = props["operations"]
            if isinstance(ops, list):
                operations.update(ops)
            elif isinstance(ops, str):
                operations.add(ops)

    return operations


def validate_node_count_min(graph: dict, min_count: int) -> ValidationResult:
    """Check that graph has minimum number of nodes.

    Args:
        graph: Parsed graph dictionary
        min_count: Minimum expected node count

    Returns:
        ValidationResult with pass/fail status
    """
    nodes = graph.get("nodes", [])
    actual_count = len(nodes)
    passed = actual_count >= min_count

    return ValidationResult(
        passed=passed,
        check_name="node_count_min",
        check_type="structure",
        expected=min_count,
        actual=actual_count,
        message=f"Graph has {actual_count} nodes (minimum: {min_count})"
    )


def validate_operations(graph: dict, required_ops: list[str]) -> ValidationResult:
    """Check if graph contains required semantic operations.

    Args:
        graph: Parsed graph dictionary
        required_ops: List of required operation names

    Returns:
        ValidationResult with pass/fail status
    """
    found_ops = get_all_operations(graph)
    missing = set(required_ops) - found_ops

    if missing:
        return ValidationResult(
            passed=False,
            check_name="has_operations",
            check_type="operations",
            expected=required_ops,
            actual=list(found_ops),
            message=f"Missing operations: {sorted(missing)}",
        )

    return ValidationResult(
        passed=True,
        check_name="has_operations",
        check_type="operations",
        expected=required_ops,
        actual=list(found_ops),
        message="All required operations present",
    )


def validate_function_property(
    graph: dict,
    func_name: str,
    prop_name: str,
    expected_value: Any
) -> ValidationResult:
    """Validate a specific property of a function node.

    Args:
        graph: Parsed graph dictionary
        func_name: Name of function to check
        prop_name: Property name to validate
        expected_value: Expected property value

    Returns:
        ValidationResult with pass/fail status
    """
    func = find_function(graph, func_name)

    if func is None:
        return ValidationResult(
            passed=False,
            check_name=f"function:{func_name}.{prop_name}",
            check_type="function_property",
            expected=expected_value,
            actual=None,
            message=f"Function not found: {func_name}",
        )

    # Check both direct properties and nested properties
    actual_value = func.get(prop_name)
    if actual_value is None:
        actual_value = func.get("properties", {}).get(prop_name)

    passed = actual_value == expected_value

    return ValidationResult(
        passed=passed,
        check_name=f"function:{func_name}.{prop_name}",
        check_type="function_property",
        expected=expected_value,
        actual=actual_value,
        message="Property matches" if passed else f"Expected {expected_value}, got {actual_value}",
    )


def validate_behavioral_signature(
    graph: dict,
    func_name: str,
    expected_sig: str
) -> ValidationResult:
    """Validate behavioral signature of a function.

    Args:
        graph: Parsed graph dictionary
        func_name: Name of function to check
        expected_sig: Expected behavioral signature

    Returns:
        ValidationResult with pass/fail status
    """
    func = find_function(graph, func_name)

    if func is None:
        return ValidationResult(
            passed=False,
            check_name=f"behavioral_signature:{func_name}",
            check_type="behavioral_signature",
            expected=expected_sig,
            actual=None,
            message=f"Function not found: {func_name}",
        )

    # Check multiple possible locations for behavioral signature
    actual_sig = (
        func.get("behavioral_signature") or
        func.get("properties", {}).get("behavioral_signature") or
        func.get("signature")
    )

    passed = actual_sig == expected_sig

    return ValidationResult(
        passed=passed,
        check_name=f"behavioral_signature:{func_name}",
        check_type="behavioral_signature",
        expected=expected_sig,
        actual=actual_sig,
        message="Signature matches" if passed else f"Expected '{expected_sig}', got '{actual_sig}'",
    )


def validate_reentrancy_vulnerable(
    graph: dict,
    expected: list[str],
    not_expected: list[str]
) -> ValidationResult:
    """Check which functions are flagged as vulnerable to reentrancy.

    Args:
        graph: Parsed graph dictionary
        expected: Functions that SHOULD be flagged
        not_expected: Functions that should NOT be flagged

    Returns:
        ValidationResult with pass/fail status
    """
    vulnerable = []
    safe = []

    for node in graph.get("nodes", []):
        if node.get("type") != "function":
            continue

        name = node.get("name", "")

        # Check for reentrancy vulnerability indicators
        has_guard = (
            node.get("has_reentrancy_guard") or
            node.get("properties", {}).get("has_reentrancy_guard")
        )

        external_before_state = (
            node.get("external_calls_before_state_writes") or
            node.get("properties", {}).get("external_calls_before_state_writes")
        )

        # A function is vulnerable if it has external calls before state writes
        # and does NOT have a reentrancy guard
        if external_before_state and not has_guard:
            vulnerable.append(name)
        else:
            safe.append(name)

    # Check expected functions are vulnerable
    missing_vulnerable = set(expected) - set(vulnerable)

    # Check not-expected functions are safe
    false_positives = set(not_expected) & set(vulnerable)

    issues = []
    if missing_vulnerable:
        issues.append(f"Should be flagged but wasn't: {sorted(missing_vulnerable)}")
    if false_positives:
        issues.append(f"Should NOT be flagged but was: {sorted(false_positives)}")

    passed = not missing_vulnerable and not false_positives

    return ValidationResult(
        passed=passed,
        check_name="reentrancy_vulnerable_functions",
        check_type="vulnerability_detection",
        expected={"vulnerable": expected, "safe": not_expected},
        actual={"vulnerable": vulnerable, "safe": safe},
        message="Correct reentrancy detection" if passed else "; ".join(issues),
    )


def validate_access_control_missing(
    graph: dict,
    expected: list[str],
    not_expected: list[str]
) -> ValidationResult:
    """Check which functions are flagged for missing access control.

    Args:
        graph: Parsed graph dictionary
        expected: Functions that SHOULD be flagged (missing access control)
        not_expected: Functions that should NOT be flagged (have access control)

    Returns:
        ValidationResult with pass/fail status
    """
    missing_access = []
    has_access = []

    for node in graph.get("nodes", []):
        if node.get("type") != "function":
            continue

        name = node.get("name", "")

        # Check for access control
        has_gate = (
            node.get("has_access_gate") or
            node.get("properties", {}).get("has_access_gate")
        )

        # Check if function modifies sensitive state (owner, admin, etc.)
        modifies_owner = (
            node.get("modifies_owner") or
            node.get("properties", {}).get("modifies_owner")
        )

        operations = set(node.get("operations", []))
        if not operations:
            operations = set(node.get("properties", {}).get("operations", []))

        modifies_critical = "MODIFIES_OWNER" in operations or modifies_owner

        # Function missing access control if it modifies critical state
        # but doesn't have an access gate
        if modifies_critical and not has_gate:
            missing_access.append(name)
        elif modifies_critical and has_gate:
            has_access.append(name)

    # Check expected functions are missing access control
    missing_expected = set(expected) - set(missing_access)

    # Check not-expected functions have access control
    false_positives = set(not_expected) & set(missing_access)

    issues = []
    if missing_expected:
        issues.append(f"Should be flagged but wasn't: {sorted(missing_expected)}")
    if false_positives:
        issues.append(f"Should NOT be flagged but was: {sorted(false_positives)}")

    passed = not missing_expected and not false_positives

    return ValidationResult(
        passed=passed,
        check_name="access_control_missing",
        check_type="vulnerability_detection",
        expected={"missing": expected, "present": not_expected},
        actual={"missing": missing_access, "present": has_access},
        message="Correct access control detection" if passed else "; ".join(issues),
    )


def validate_required_nodes(graph: dict, required_nodes: dict) -> list[ValidationResult]:
    """Validate all required function nodes and their properties.

    Args:
        graph: Parsed graph dictionary
        required_nodes: Dict mapping function names to expected properties

    Returns:
        List of ValidationResults for each function/property
    """
    results = []

    for func_name, expected_props in required_nodes.items():
        func = find_function(graph, func_name)

        if func is None:
            results.append(ValidationResult(
                passed=False,
                check_name=f"function_exists:{func_name}",
                check_type="structure",
                expected=True,
                actual=False,
                message=f"Required function not found: {func_name}",
            ))
            continue

        results.append(ValidationResult(
            passed=True,
            check_name=f"function_exists:{func_name}",
            check_type="structure",
            expected=True,
            actual=True,
            message=f"Function found: {func_name}",
        ))

        # Validate each property
        for prop_name, expected_value in expected_props.items():
            # Skip operations and behavioral_signature - handled separately
            if prop_name in ("operations", "behavioral_signature"):
                continue

            results.append(
                validate_function_property(graph, func_name, prop_name, expected_value)
            )

        # Handle behavioral_signature if present
        if "behavioral_signature" in expected_props:
            results.append(
                validate_behavioral_signature(
                    graph, func_name, expected_props["behavioral_signature"]
                )
            )

    return results


def run_validation(graph: dict, expected: dict) -> list[ValidationResult]:
    """Run all validation rules against graph.

    Args:
        graph: Parsed graph dictionary
        expected: Expected checks configuration

    Returns:
        List of all ValidationResults
    """
    results = []

    # Validate required nodes if specified
    if "required_nodes" in expected:
        results.extend(validate_required_nodes(graph, expected["required_nodes"]))

    # Run validation rules
    for rule in expected.get("validation_rules", []):
        check_type = rule.get("check")

        if check_type == "node_count_min":
            results.append(validate_node_count_min(graph, rule["value"]))

        elif check_type == "has_operations":
            results.append(validate_operations(graph, rule["required"]))

        elif check_type == "function_properties":
            results.append(
                validate_function_property(
                    graph,
                    rule["function"],
                    rule["property"],
                    rule["expected"]
                )
            )

        elif check_type == "behavioral_signature":
            results.append(
                validate_behavioral_signature(
                    graph, rule["function"], rule["expected"]
                )
            )

        elif check_type == "reentrancy_vulnerable_functions":
            results.append(
                validate_reentrancy_vulnerable(
                    graph,
                    rule.get("expected", []),
                    rule.get("not_expected", [])
                )
            )

        elif check_type == "access_control_missing":
            results.append(
                validate_access_control_missing(
                    graph,
                    rule.get("expected", []),
                    rule.get("not_expected", [])
                )
            )

    return results


def basic_validation(graph: dict) -> list[ValidationResult]:
    """Perform basic graph structure validation.

    Args:
        graph: Parsed graph dictionary

    Returns:
        List of basic ValidationResults
    """
    results = []

    # Check graph has nodes
    nodes = graph.get("nodes", [])
    results.append(ValidationResult(
        passed=len(nodes) > 0,
        check_name="has_nodes",
        check_type="structure",
        expected="> 0",
        actual=len(nodes),
        message=f"Graph has {len(nodes)} nodes" if nodes else "Graph has no nodes",
    ))

    # Check for function nodes
    func_nodes = [n for n in nodes if n.get("type") == "function"]
    results.append(ValidationResult(
        passed=len(func_nodes) > 0,
        check_name="has_function_nodes",
        check_type="structure",
        expected="> 0",
        actual=len(func_nodes),
        message=f"Graph has {len(func_nodes)} function nodes",
    ))

    # Check for operations
    operations = get_all_operations(graph)
    results.append(ValidationResult(
        passed=len(operations) > 0,
        check_name="has_operations",
        check_type="operations",
        expected="> 0",
        actual=len(operations),
        message=f"Graph has {len(operations)} unique operations: {sorted(operations)}",
    ))

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Validate BSKG graph properties",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic validation (structure only)
    %(prog)s --graph .vrs/graphs/Vault.toon

    # Full validation against expected properties
    %(prog)s --graph .vrs/graphs/Vault.toon --expected expected/graph-checks.json

    # With output file
    %(prog)s --graph .vrs/graphs/Vault.toon --expected expected/graph-checks.json --output results.json
        """
    )
    parser.add_argument(
        "--graph",
        required=True,
        help="Path to graph file (.toon or .json)"
    )
    parser.add_argument(
        "--expected",
        help="Path to expected checks JSON (optional - performs basic validation if omitted)"
    )
    parser.add_argument(
        "--output",
        help="Output file for validation results (JSON)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output"
    )
    args = parser.parse_args()

    graph_path = Path(args.graph)

    # Validate graph file exists
    if not graph_path.exists():
        print(f"ERROR: Graph file not found: {graph_path}")
        sys.exit(1)

    # Load graph
    try:
        graph = load_graph(graph_path)
    except ImportError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in graph file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to load graph: {e}")
        sys.exit(1)

    # Run validation
    if args.expected:
        expected_path = Path(args.expected)

        if not expected_path.exists():
            print(f"WARNING: Expected checks file not found: {expected_path}")
            print("Performing basic graph structure validation only")
            results = basic_validation(graph)
        else:
            try:
                expected = json.loads(expected_path.read_text())
            except json.JSONDecodeError as e:
                print(f"ERROR: Invalid JSON in expected file: {e}")
                sys.exit(1)

            results = run_validation(graph, expected)
    else:
        # Basic validation only
        results = basic_validation(graph)

    # Output results
    all_passed = all(r.passed for r in results)
    passed_count = sum(1 for r in results if r.passed)
    failed_count = sum(1 for r in results if not r.passed)

    print("")
    print("=" * 60)
    print(" BSKG Graph Validation Results")
    print("=" * 60)
    print(f"Graph file: {graph_path}")
    if args.expected:
        print(f"Expected:   {args.expected}")
    print("-" * 60)

    for result in results:
        status = "[PASS]" if result.passed else "[FAIL]"
        print(f"  {status} {result.check_name}")
        if not result.passed or args.verbose:
            print(f"         {result.message}")
            if args.verbose:
                print(f"         Expected: {result.expected}")
                print(f"         Actual:   {result.actual}")

    print("-" * 60)
    print(f"Total: {passed_count}/{len(results)} passed, {failed_count} failed")
    print("=" * 60)

    # Write output file
    if args.output:
        output_data = {
            "passed": all_passed,
            "total_checks": len(results),
            "passed_checks": passed_count,
            "failed_checks": failed_count,
            "graph_file": str(graph_path),
            "expected_file": args.expected,
            "results": [asdict(r) for r in results],
        }
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(output_data, indent=2))
        print(f"\nResults written to: {args.output}")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
