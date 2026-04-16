#!/usr/bin/env python3
"""
Analyze detection by vulnerability subtype.

This script analyzes how well AlphaSwarm detects different subtypes of
vulnerabilities within a category (e.g., different access control subtypes).

Usage:
    uv run python scripts/analyze_by_subtype.py --worktree /path/to/worktree
    uv run python scripts/analyze_by_subtype.py --worktree /path/to/worktree --output analysis.json
    uv run python scripts/analyze_by_subtype.py --worktree /path/to/worktree --verbose

Output:
    JSON with per-subtype metrics and overall summary.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


def load_yaml(path: Path) -> dict:
    """Load YAML file, handling optional PyYAML dependency."""
    try:
        import yaml
        return yaml.safe_load(path.read_text())
    except ImportError:
        # Fallback: simple YAML parsing for our specific format
        return _simple_yaml_parse(path.read_text())


def _simple_yaml_parse(content: str) -> dict:
    """Simple YAML parser for ground-truth.yaml format."""
    result: dict = {
        "contracts": [],
        "safe_contracts": [],
        "subtype_summary": {},
        "thresholds": {},
    }
    current_contract: dict = {}
    current_vuln: dict = {}
    current_section = None
    in_vulnerabilities = False
    in_pattern_expected = False
    indent_level = 0

    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())

        # Top-level keys
        if indent == 0 and stripped.endswith(":"):
            key = stripped[:-1]
            if key == "contracts":
                current_section = "contracts"
            elif key == "safe_contracts":
                current_section = "safe_contracts"
            elif key == "subtype_summary":
                current_section = "subtype_summary"
            elif key == "thresholds":
                current_section = "thresholds"
            continue

        if indent == 0 and ":" in stripped:
            key, val = stripped.split(":", 1)
            key = key.strip()
            val = val.strip()
            if val:
                result[key] = val
            continue

        # Contracts section
        if current_section == "contracts":
            if stripped.startswith("- file:"):
                if current_contract:
                    if current_vuln:
                        current_contract.setdefault("vulnerabilities", []).append(current_vuln)
                        current_vuln = {}
                    result["contracts"].append(current_contract)
                current_contract = {"file": stripped.split(":", 1)[1].strip()}
                in_vulnerabilities = False
            elif stripped == "vulnerabilities:":
                in_vulnerabilities = True
            elif stripped.startswith("- id:") and in_vulnerabilities:
                if current_vuln:
                    current_contract.setdefault("vulnerabilities", []).append(current_vuln)
                current_vuln = {"id": stripped.split(":", 1)[1].strip()}
                in_pattern_expected = False
            elif current_vuln and in_vulnerabilities:
                if stripped == "pattern_expected:":
                    in_pattern_expected = True
                    current_vuln["pattern_expected"] = []
                elif in_pattern_expected and stripped.startswith("- "):
                    current_vuln["pattern_expected"].append(stripped[2:].strip())
                elif ":" in stripped and not stripped.startswith("-"):
                    key, val = stripped.split(":", 1)
                    key = key.strip()
                    val = val.strip()
                    if val:
                        current_vuln[key] = val
                    in_pattern_expected = False

        # Thresholds section
        elif current_section == "thresholds":
            if ":" in stripped:
                key, val = stripped.split(":", 1)
                key = key.strip()
                val = val.strip()
                try:
                    result["thresholds"][key] = float(val)
                except ValueError:
                    result["thresholds"][key] = val

    # Don't forget last items
    if current_vuln:
        current_contract.setdefault("vulnerabilities", []).append(current_vuln)
    if current_contract:
        result["contracts"].append(current_contract)

    return result


@dataclass
class VulnerabilityInfo:
    """Ground truth vulnerability information."""
    id: str
    vuln_type: str
    subtype: str
    function: str
    line: Optional[int]
    severity: str
    contract_file: str
    description: Optional[str] = None


@dataclass
class FindingInfo:
    """Audit finding information."""
    id: str
    vuln_type: str
    function: str
    severity: str = "unknown"
    line: Optional[int] = None
    confidence: float = 0.0
    file: str = ""


@dataclass
class SubtypeMetrics:
    """Metrics for a single vulnerability subtype."""
    subtype: str
    total: int
    detected: int
    missed: int
    detection_rate: float
    detected_ids: list[str] = field(default_factory=list)
    missed_ids: list[str] = field(default_factory=list)


@dataclass
class AnalysisResults:
    """Complete analysis results."""
    by_subtype: dict[str, SubtypeMetrics]
    total_vulnerabilities: int
    total_detected: int
    overall_recall: float
    subtypes_with_perfect_detection: int
    subtypes_with_zero_detection: int


def load_ground_truth(worktree: Path) -> list[VulnerabilityInfo]:
    """Load ground truth from YAML file, extracting subtype info."""
    gt_file = worktree / "ground-truth.yaml"
    if not gt_file.exists():
        raise FileNotFoundError(f"Ground truth file not found: {gt_file}")

    data = load_yaml(gt_file)
    vulns: list[VulnerabilityInfo] = []

    for contract in data.get("contracts", []):
        contract_file = contract.get("file", "")
        for v in contract.get("vulnerabilities", []):
            line_val = v.get("line")
            line = int(line_val) if line_val else None

            vulns.append(VulnerabilityInfo(
                id=v.get("id", ""),
                vuln_type=v.get("type", "unknown"),
                subtype=v.get("subtype", v.get("type", "unknown")),
                function=v.get("function", ""),
                line=line,
                severity=v.get("severity", "unknown"),
                contract_file=contract_file,
                description=v.get("description"),
            ))

    return vulns


def load_findings(worktree: Path) -> list[FindingInfo]:
    """Load findings from audit output files."""
    findings: list[FindingInfo] = []
    vrs_dir = worktree / ".vrs"

    # Try verdicts first (most complete, from debate stage)
    verdicts_file = vrs_dir / "findings" / "verdicts.json"
    if verdicts_file.exists():
        try:
            data = json.loads(verdicts_file.read_text())
            verdict_list = data if isinstance(data, list) else data.get("verdicts", [])
            for i, v in enumerate(verdict_list):
                findings.append(FindingInfo(
                    id=v.get("id", f"verdict-{i}"),
                    vuln_type=v.get("type", v.get("vulnerability_type", "unknown")),
                    function=v.get("function", v.get("location", {}).get("function", "")),
                    severity=v.get("severity", "unknown"),
                    line=v.get("line", v.get("location", {}).get("line")),
                    confidence=v.get("confidence", 0.0),
                    file=v.get("file", v.get("location", {}).get("file", "")),
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
                findings.append(FindingInfo(
                    id=inv.get("id", f"agent-{i}"),
                    vuln_type=inv.get("type", inv.get("vulnerability_type", "unknown")),
                    function=inv.get("function", inv.get("target_function", "")),
                    severity=inv.get("severity", "unknown"),
                    line=inv.get("line"),
                    confidence=inv.get("confidence", 0.0),
                    file=inv.get("file", ""),
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
                findings.append(FindingInfo(
                    id=m.get("pattern_id", f"pattern-{i}"),
                    vuln_type=m.get("type", m.get("category", "unknown")),
                    function=m.get("function", m.get("function_name", "")),
                    severity=m.get("severity", "unknown"),
                    line=m.get("line"),
                    confidence=m.get("confidence", m.get("score", 0.0)),
                    file=m.get("file", ""),
                ))
        except (json.JSONDecodeError, KeyError):
            pass

    return findings


def normalize_type(t: str) -> str:
    """Normalize vulnerability type for matching."""
    t = t.lower().strip().replace("_", "-").replace(" ", "-")

    # Common normalizations
    type_map = {
        "reentrancy": "reentrancy",
        "reentrant": "reentrancy",
        "access-control": "access-control",
        "access-control-missing": "access-control",
        "missing-access-control": "access-control",
        "tx-origin": "tx-origin",
        "tx-origin-auth": "tx-origin",
        "tx-origin-authentication": "tx-origin",
        "suicide": "suicide",
        "selfdestruct": "suicide",
        "suicide-access-control": "suicide",
        "unprotected-selfdestruct": "suicide",
        "ownership": "ownership",
        "ownership-manipulation": "ownership",
        "unauthorized-transfer": "unauthorized-transfer",
        "arbitrary-send": "unauthorized-transfer",
    }

    for key, norm in type_map.items():
        if key in t:
            return norm

    return t


def match_finding_to_vuln(finding: FindingInfo, vuln: VulnerabilityInfo) -> bool:
    """Determine if a finding matches a ground truth vulnerability."""
    finding_func = finding.function.lower().strip()
    vuln_func = vuln.function.lower().strip()

    # Exact function match
    if finding_func and vuln_func and finding_func == vuln_func:
        return True

    # Partial function match with type check
    if finding_func and vuln_func:
        if finding_func in vuln_func or vuln_func in finding_func:
            if normalize_type(finding.vuln_type) == normalize_type(vuln.vuln_type):
                return True

    # Match by file + line number (with tolerance)
    if vuln.line and finding.line:
        # Check if file matches (if file info available)
        file_match = True
        if finding.file and vuln.contract_file:
            finding_file = finding.file.lower()
            vuln_file = vuln.contract_file.lower()
            file_match = vuln_file in finding_file or finding_file in vuln_file

        if file_match and abs(finding.line - vuln.line) <= 5:
            return True

    # Match by type + partial function
    if normalize_type(finding.vuln_type) == normalize_type(vuln.vuln_type):
        if finding_func and vuln_func:
            # Check for common words
            finding_words = set(finding_func.replace("_", " ").replace("-", " ").split())
            vuln_words = set(vuln_func.replace("_", " ").replace("-", " ").split())
            if finding_words & vuln_words:
                return True

    return False


def organize_by_subtype(vulns: list[VulnerabilityInfo]) -> dict[str, list[VulnerabilityInfo]]:
    """Organize vulnerabilities by subtype."""
    by_subtype: dict[str, list[VulnerabilityInfo]] = defaultdict(list)
    for vuln in vulns:
        by_subtype[vuln.subtype].append(vuln)
    return dict(by_subtype)


def analyze_by_subtype(
    ground_truth: list[VulnerabilityInfo],
    findings: list[FindingInfo],
    verbose: bool = False,
) -> AnalysisResults:
    """Analyze detection by vulnerability subtype."""
    by_subtype = organize_by_subtype(ground_truth)
    results: dict[str, SubtypeMetrics] = {}

    total_gt = 0
    total_detected = 0

    for subtype, vulns in sorted(by_subtype.items()):
        detected_ids: list[str] = []
        missed_ids: list[str] = []

        for vuln in vulns:
            # Check if any finding matches this vulnerability
            found = any(match_finding_to_vuln(f, vuln) for f in findings)
            if found:
                detected_ids.append(vuln.id)
                if verbose:
                    print(f"  [DETECTED] {vuln.id}: {vuln.function} ({subtype})", file=sys.stderr)
            else:
                missed_ids.append(vuln.id)
                if verbose:
                    print(f"  [MISSED] {vuln.id}: {vuln.function} ({subtype})", file=sys.stderr)

        detection_rate = len(detected_ids) / len(vulns) if vulns else 0.0

        results[subtype] = SubtypeMetrics(
            subtype=subtype,
            total=len(vulns),
            detected=len(detected_ids),
            missed=len(missed_ids),
            detection_rate=detection_rate,
            detected_ids=detected_ids,
            missed_ids=missed_ids,
        )

        total_gt += len(vulns)
        total_detected += len(detected_ids)

    subtypes_with_perfect = sum(1 for m in results.values() if m.detection_rate == 1.0)
    subtypes_with_zero = sum(1 for m in results.values() if m.detection_rate == 0.0)

    return AnalysisResults(
        by_subtype=results,
        total_vulnerabilities=total_gt,
        total_detected=total_detected,
        overall_recall=total_detected / total_gt if total_gt > 0 else 0.0,
        subtypes_with_perfect_detection=subtypes_with_perfect,
        subtypes_with_zero_detection=subtypes_with_zero,
    )


def results_to_dict(results: AnalysisResults) -> dict[str, Any]:
    """Convert results to JSON-serializable dict."""
    return {
        "by_subtype": {
            subtype: {
                "subtype": m.subtype,
                "total": m.total,
                "detected": m.detected,
                "missed": m.missed,
                "detection_rate": round(m.detection_rate, 4),
                "detected_ids": m.detected_ids,
                "missed_ids": m.missed_ids,
            }
            for subtype, m in results.by_subtype.items()
        },
        "summary": {
            "total_vulnerabilities": results.total_vulnerabilities,
            "total_detected": results.total_detected,
            "overall_recall": round(results.overall_recall, 4),
            "subtypes_with_perfect_detection": results.subtypes_with_perfect_detection,
            "subtypes_with_zero_detection": results.subtypes_with_zero_detection,
            "subtypes_count": len(results.by_subtype),
        },
    }


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze detection by vulnerability subtype",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s --worktree /tmp/vrs-worktrees/smartbugs-access-control
    %(prog)s --worktree /tmp/vrs-worktrees/test --output subtype-analysis.json
    %(prog)s --worktree /tmp/vrs-worktrees/test --verbose
        """,
    )
    parser.add_argument(
        "--worktree",
        required=True,
        help="Path to worktree containing ground-truth.yaml and .vrs/ outputs",
    )
    parser.add_argument(
        "--output",
        help="Output file for analysis JSON (also prints to stdout)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed matching information",
    )
    args = parser.parse_args()

    worktree = Path(args.worktree)

    try:
        ground_truth = load_ground_truth(worktree)
        if args.verbose:
            print(f"Loaded {len(ground_truth)} ground truth vulnerabilities:", file=sys.stderr)
            for v in ground_truth:
                print(f"  - {v.id}: {v.subtype} in {v.function} ({v.contract_file})", file=sys.stderr)
            print(file=sys.stderr)

        findings = load_findings(worktree)
        if args.verbose:
            print(f"Loaded {len(findings)} findings:", file=sys.stderr)
            for f in findings:
                print(f"  - {f.id}: {f.vuln_type} in {f.function}", file=sys.stderr)
            print(file=sys.stderr)

        if not findings:
            print("WARNING: No findings loaded from audit output", file=sys.stderr)

        results = analyze_by_subtype(ground_truth, findings, verbose=args.verbose)
        output = results_to_dict(results)

        if args.output:
            Path(args.output).write_text(json.dumps(output, indent=2))

        print(json.dumps(output, indent=2))
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
