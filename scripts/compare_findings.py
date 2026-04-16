#!/usr/bin/env python3
"""
Compare audit findings to external ground truth.

This script loads findings from an audit run and compares them to the
ground truth vulnerabilities defined in ground-truth.yaml. It supports:

1. Loading findings from multiple output formats (verdicts, investigations, pattern-matches)
2. Matching findings to ground truth vulnerabilities
3. Checking for false positives on safe functions
4. Calculating precision, recall, and F1 score

Usage:
    uv run python scripts/compare_findings.py --worktree /path/to/worktree
    uv run python scripts/compare_findings.py --worktree /path/to/worktree --output metrics.json
    uv run python scripts/compare_findings.py --worktree /path/to/worktree --verbose

Output:
    JSON with precision, recall, F1 score, and lists of TP/FP/FN findings.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


def load_yaml(path: Path) -> dict:
    """Load YAML file, handling optional PyYAML dependency."""
    try:
        import yaml
        return yaml.safe_load(path.read_text())
    except ImportError:
        # Fallback: simple YAML parsing for our specific format
        content = path.read_text()
        return _simple_yaml_parse(content)


def _simple_yaml_parse(content: str) -> dict:
    """Simple YAML parser for ground-truth.yaml format."""
    result: dict = {"vulnerabilities": [], "safe_functions": [], "thresholds": {}}
    current_vuln: dict = {}
    current_section = None
    indent_stack: list[tuple[int, str, dict]] = []

    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())

        # Top-level keys
        if indent == 0 and ":" in stripped:
            key = stripped.split(":")[0].strip()
            if key == "vulnerabilities":
                current_section = "vulnerabilities"
            elif key == "safe_functions":
                current_section = "safe_functions"
            elif key == "thresholds":
                current_section = "thresholds"
            elif key in ("contract", "file"):
                val = stripped.split(":", 1)[1].strip()
                result[key] = val

        # List items in vulnerabilities
        elif current_section == "vulnerabilities" and stripped.startswith("- id:"):
            if current_vuln:
                result["vulnerabilities"].append(current_vuln)
            current_vuln = {"id": stripped.split(":", 1)[1].strip()}

        elif current_section == "vulnerabilities" and current_vuln:
            if ":" in stripped and not stripped.startswith("-"):
                key, val = stripped.split(":", 1)
                key = key.strip()
                val = val.strip()
                if val:
                    # Handle line ranges
                    if val.startswith("[") and val.endswith("]"):
                        val = [int(x.strip()) for x in val[1:-1].split(",")]
                    current_vuln[key] = val

        # Thresholds
        elif current_section == "thresholds" and ":" in stripped:
            key, val = stripped.split(":", 1)
            key = key.strip()
            val = val.strip()
            try:
                result["thresholds"][key] = float(val)
            except ValueError:
                result["thresholds"][key] = val

    # Don't forget last vulnerability
    if current_vuln:
        result["vulnerabilities"].append(current_vuln)

    return result


@dataclass
class Vulnerability:
    """Ground truth vulnerability."""
    id: str
    type: str
    severity: str
    function: str
    line: Optional[int] = None
    line_range: Optional[tuple[int, int]] = None
    description: Optional[str] = None


@dataclass
class Finding:
    """Audit finding from VRS output."""
    id: str
    type: str
    function: str
    severity: str = "unknown"
    line: Optional[int] = None
    confidence: float = 0.0
    raw: dict = field(default_factory=dict)


@dataclass
class Metrics:
    """Comparison metrics."""
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    tp_list: list[str]
    fp_list: list[str]
    fn_list: list[str]


@dataclass
class SafeFunction:
    """Function that should NOT be flagged as vulnerable."""
    function: str
    reason: str
    expected_properties: dict = field(default_factory=dict)


def load_ground_truth(worktree: Path) -> list[Vulnerability]:
    """Load ground truth from YAML file."""
    gt_file = worktree / "ground-truth.yaml"
    if not gt_file.exists():
        raise FileNotFoundError(f"Ground truth file not found: {gt_file}")

    data = load_yaml(gt_file)
    vulns = []

    for v in data.get("vulnerabilities", []):
        line_range = v.get("line_range")
        if line_range and isinstance(line_range, list) and len(line_range) >= 2:
            line_range = (line_range[0], line_range[1])
        else:
            line_range = None

        vulns.append(Vulnerability(
            id=v["id"],
            type=v.get("type", "unknown"),
            severity=v.get("severity", "unknown"),
            function=v.get("function", ""),
            line=v.get("line"),
            line_range=line_range,
            description=v.get("description"),
        ))

    return vulns


def load_safe_functions(worktree: Path) -> list[SafeFunction]:
    """Load safe functions that should NOT be flagged."""
    gt_file = worktree / "ground-truth.yaml"
    if not gt_file.exists():
        return []

    data = load_yaml(gt_file)
    safe_funcs = []

    for sf in data.get("safe_functions", []):
        safe_funcs.append(SafeFunction(
            function=sf.get("function", ""),
            reason=sf.get("reason", ""),
            expected_properties=sf.get("expected_properties", {}),
        ))

    return safe_funcs


def load_findings(worktree: Path) -> list[Finding]:
    """Load findings from audit output files."""
    findings = []
    vrs_dir = worktree / ".vrs"

    # Try verdicts first (most complete, from debate stage)
    verdicts_file = vrs_dir / "findings" / "verdicts.json"
    if verdicts_file.exists():
        try:
            data = json.loads(verdicts_file.read_text())
            for i, v in enumerate(data if isinstance(data, list) else data.get("verdicts", [])):
                findings.append(Finding(
                    id=v.get("id", f"verdict-{i}"),
                    type=v.get("type", v.get("vulnerability_type", "unknown")),
                    function=v.get("function", v.get("location", {}).get("function", "")),
                    severity=v.get("severity", "unknown"),
                    line=v.get("line", v.get("location", {}).get("line")),
                    confidence=v.get("confidence", 0.0),
                    raw=v,
                ))
            if findings:
                return findings
        except (json.JSONDecodeError, KeyError):
            pass

    # Fall back to agent investigations
    agent_file = vrs_dir / "findings" / "agent-investigations.json"
    if agent_file.exists():
        try:
            data = json.loads(agent_file.read_text())
            investigations = data if isinstance(data, list) else data.get("investigations", [])
            for i, inv in enumerate(investigations):
                findings.append(Finding(
                    id=inv.get("id", f"agent-{i}"),
                    type=inv.get("type", inv.get("vulnerability_type", "unknown")),
                    function=inv.get("function", inv.get("target_function", "")),
                    severity=inv.get("severity", "unknown"),
                    line=inv.get("line"),
                    confidence=inv.get("confidence", 0.0),
                    raw=inv,
                ))
            if findings:
                return findings
        except (json.JSONDecodeError, KeyError):
            pass

    # Fall back to pattern matches
    pattern_file = vrs_dir / "findings" / "pattern-matches.json"
    if pattern_file.exists():
        try:
            data = json.loads(pattern_file.read_text())
            matches = data if isinstance(data, list) else data.get("matches", [])
            for i, m in enumerate(matches):
                findings.append(Finding(
                    id=m.get("pattern_id", f"pattern-{i}"),
                    type=m.get("type", m.get("category", "unknown")),
                    function=m.get("function", m.get("function_name", "")),
                    severity=m.get("severity", "unknown"),
                    line=m.get("line"),
                    confidence=m.get("confidence", m.get("score", 0.0)),
                    raw=m,
                ))
        except (json.JSONDecodeError, KeyError):
            pass

    return findings


def normalize_type(t: str) -> str:
    """Normalize vulnerability type for matching."""
    t = t.lower().strip()
    # Common normalizations
    if "reentr" in t:
        return "reentrancy"
    if "access" in t or "auth" in t or "permission" in t:
        return "access-control"
    if "oracle" in t or "price" in t:
        return "oracle"
    if "overflow" in t or "underflow" in t:
        return "arithmetic"
    return t


def match_finding_to_vuln(finding: Finding, vuln: Vulnerability) -> bool:
    """Determine if a finding matches a ground truth vulnerability."""
    # Match by function name (most reliable)
    finding_func = finding.function.lower().strip()
    vuln_func = vuln.function.lower().strip()

    # Exact function match
    if finding_func and vuln_func and finding_func == vuln_func:
        return True

    # Partial function match (finding function contains vuln function or vice versa)
    if finding_func and vuln_func:
        if finding_func in vuln_func or vuln_func in finding_func:
            # Also check type similarity
            if normalize_type(finding.type) == normalize_type(vuln.type):
                return True

    # Match by line number (with tolerance)
    if vuln.line and finding.line:
        if abs(finding.line - vuln.line) <= 5:
            return True

    # Match by line range
    if vuln.line_range and finding.line:
        if vuln.line_range[0] <= finding.line <= vuln.line_range[1]:
            return True

    # Match by type + partial function
    finding_type = normalize_type(finding.type)
    vuln_type = normalize_type(vuln.type)

    if finding_type == vuln_type:
        # Check if functions are related
        if finding_func and vuln_func:
            # One contains the other
            if finding_func in vuln_func or vuln_func in finding_func:
                return True
            # Common words
            finding_words = set(finding_func.replace("_", " ").split())
            vuln_words = set(vuln_func.replace("_", " ").split())
            if finding_words & vuln_words:  # Common words
                return True

    return False


def check_false_positive_on_safe(finding: Finding, safe_functions: list[SafeFunction]) -> Optional[SafeFunction]:
    """Check if a finding incorrectly flags a safe function."""
    finding_func = finding.function.lower().strip()
    for sf in safe_functions:
        safe_func = sf.function.lower().strip()
        if finding_func == safe_func or safe_func in finding_func or finding_func in safe_func:
            return sf
    return None


def calculate_metrics(
    ground_truth: list[Vulnerability],
    findings: list[Finding],
    safe_functions: Optional[list[SafeFunction]] = None,
) -> Metrics:
    """Calculate precision, recall, and F1 score.

    Args:
        ground_truth: Known vulnerabilities
        findings: Detected findings from audit
        safe_functions: Functions that should NOT be flagged (extra FP if flagged)
    """
    if safe_functions is None:
        safe_functions = []

    matched_vulns: set[str] = set()
    matched_findings: set[int] = set()

    # Find true positives by matching findings to vulnerabilities
    for i, finding in enumerate(findings):
        for vuln in ground_truth:
            if vuln.id not in matched_vulns and match_finding_to_vuln(finding, vuln):
                matched_vulns.add(vuln.id)
                matched_findings.add(i)
                break

    # Count false positives from flagging safe functions
    safe_fp_count = 0
    safe_fp_list: list[str] = []
    for i, finding in enumerate(findings):
        if i not in matched_findings:  # Only check unmatched findings
            sf = check_false_positive_on_safe(finding, safe_functions)
            if sf:
                safe_fp_count += 1
                safe_fp_list.append(f"{finding.id} (flagged safe function: {sf.function})")

    tp = len(matched_vulns)
    fn = len(ground_truth) - tp
    # FP = findings not matched to any vuln (including those hitting safe functions)
    fp = len(findings) - len(matched_findings)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    # Build FP list including safe function violations
    fp_list = []
    for i in range(len(findings)):
        if i not in matched_findings:
            sf = check_false_positive_on_safe(findings[i], safe_functions)
            if sf:
                fp_list.append(f"{findings[i].id} (safe: {sf.function})")
            else:
                fp_list.append(findings[i].id)

    return Metrics(
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        precision=precision,
        recall=recall,
        f1_score=f1,
        tp_list=[v.id for v in ground_truth if v.id in matched_vulns],
        fp_list=fp_list,
        fn_list=[v.id for v in ground_truth if v.id not in matched_vulns],
    )


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Compare audit findings to ground truth",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s --worktree /tmp/vrs-worktrees/test
    %(prog)s --worktree /tmp/vrs-worktrees/test --output metrics.json
    %(prog)s --worktree /tmp/vrs-worktrees/test --verbose
        """,
    )
    parser.add_argument(
        "--worktree",
        required=True,
        help="Path to worktree containing ground-truth.yaml and .vrs/ outputs"
    )
    parser.add_argument(
        "--output",
        help="Output file for metrics JSON (also prints to stdout)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed matching information"
    )
    args = parser.parse_args()

    worktree = Path(args.worktree)

    try:
        ground_truth = load_ground_truth(worktree)
        if args.verbose:
            print(f"Loaded {len(ground_truth)} ground truth vulnerabilities:", file=sys.stderr)
            for v in ground_truth:
                print(f"  - {v.id}: {v.type} in {v.function}", file=sys.stderr)
            print(file=sys.stderr)

        safe_functions = load_safe_functions(worktree)
        if args.verbose and safe_functions:
            print(f"Loaded {len(safe_functions)} safe functions:", file=sys.stderr)
            for sf in safe_functions:
                print(f"  - {sf.function}: {sf.reason}", file=sys.stderr)
            print(file=sys.stderr)

        findings = load_findings(worktree)
        if args.verbose:
            print(f"Loaded {len(findings)} findings:", file=sys.stderr)
            for f in findings:
                print(f"  - {f.id}: {f.type} in {f.function}", file=sys.stderr)
            print(file=sys.stderr)

        if not findings:
            print("WARNING: No findings loaded from audit output", file=sys.stderr)

        metrics = calculate_metrics(ground_truth, findings, safe_functions)

        result = {
            "ground_truth_count": len(ground_truth),
            "findings_count": len(findings),
            "safe_functions_count": len(safe_functions),
            "true_positives": metrics.true_positives,
            "false_positives": metrics.false_positives,
            "false_negatives": metrics.false_negatives,
            "precision": round(metrics.precision, 4),
            "recall": round(metrics.recall, 4),
            "f1_score": round(metrics.f1_score, 4),
            "tp_list": metrics.tp_list,
            "fp_list": metrics.fp_list,
            "fn_list": metrics.fn_list,
        }

        if args.output:
            Path(args.output).write_text(json.dumps(result, indent=2))

        print(json.dumps(result, indent=2))
        return 0

    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
