#!/usr/bin/env python3
"""
Detailed per-contract analysis for SmartBugs reentrancy suite.

This script provides granular analysis of audit results against the SmartBugs
curated dataset, including:
- Per-contract detection status
- Vulnerability-level matching
- Safe contract false positive tracking
- Variant-specific analysis

Usage:
    uv run python scripts/analyze_smartbugs_results.py --worktree /path/to/worktree
    uv run python scripts/analyze_smartbugs_results.py --worktree /path/to/worktree --output analysis.json
    uv run python scripts/analyze_smartbugs_results.py --worktree /path/to/worktree --verbose

Output:
    JSON with per-contract analysis, summary statistics, and variant breakdown.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


def load_yaml(path: Path) -> dict:
    """Load YAML file, handling optional PyYAML dependency."""
    try:
        import yaml
        return yaml.safe_load(path.read_text())
    except ImportError:
        # Fallback: simple YAML parsing
        content = path.read_text()
        return _simple_yaml_parse(content)


def _simple_yaml_parse(content: str) -> dict:
    """Simple YAML parser for ground-truth.yaml format."""
    result: dict = {
        "contracts": [],
        "safe_contracts": [],
        "thresholds": {},
    }

    current_contract: Optional[dict] = None
    current_vuln: Optional[dict] = None
    current_section: Optional[str] = None
    in_vulnerabilities = False

    lines = content.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        indent = len(line) - len(line.lstrip())

        # Top-level sections
        if indent == 0:
            if stripped.startswith("contracts:"):
                current_section = "contracts"
            elif stripped.startswith("safe_contracts:"):
                current_section = "safe_contracts"
            elif stripped.startswith("thresholds:"):
                current_section = "thresholds"
            elif ":" in stripped:
                key, val = stripped.split(":", 1)
                result[key.strip()] = val.strip()
            i += 1
            continue

        # Contracts section
        if current_section == "contracts":
            if stripped.startswith("- file:"):
                # Save previous contract
                if current_contract:
                    result["contracts"].append(current_contract)
                current_contract = {
                    "file": stripped.split(":", 1)[1].strip(),
                    "vulnerabilities": [],
                }
                in_vulnerabilities = False
                current_vuln = None
            elif current_contract and stripped.startswith("vulnerabilities:"):
                in_vulnerabilities = True
            elif current_contract and in_vulnerabilities and stripped.startswith("- id:"):
                # Save previous vulnerability
                if current_vuln:
                    current_contract["vulnerabilities"].append(current_vuln)
                current_vuln = {"id": stripped.split(":", 1)[1].strip()}
            elif current_vuln and ":" in stripped and not stripped.startswith("-"):
                key, val = stripped.split(":", 1)
                key = key.strip()
                val = val.strip()
                if val and val not in ("", "|", ">"):
                    current_vuln[key] = val

        # Safe contracts section
        elif current_section == "safe_contracts":
            if stripped.startswith("- file:"):
                safe = {"file": stripped.split(":", 1)[1].strip()}
                result["safe_contracts"].append(safe)
            elif result["safe_contracts"] and ":" in stripped and not stripped.startswith("-"):
                key, val = stripped.split(":", 1)
                key = key.strip()
                val = val.strip()
                if val:
                    result["safe_contracts"][-1][key] = val

        # Thresholds section
        elif current_section == "thresholds":
            if ":" in stripped:
                key, val = stripped.split(":", 1)
                try:
                    result["thresholds"][key.strip()] = float(val.strip())
                except ValueError:
                    result["thresholds"][key.strip()] = val.strip()

        i += 1

    # Don't forget last items
    if current_vuln and current_contract:
        current_contract["vulnerabilities"].append(current_vuln)
    if current_contract:
        result["contracts"].append(current_contract)

    return result


@dataclass
class GroundTruthVuln:
    """A single ground truth vulnerability."""
    id: str
    type: str
    function: str
    line: int
    severity: str
    description: str = ""
    pattern: str = ""


@dataclass
class GroundTruthContract:
    """A contract with its known vulnerabilities."""
    file: str
    vulnerabilities: list[GroundTruthVuln]


@dataclass
class SafeContract:
    """A contract known to be safe (no vulnerabilities)."""
    file: str
    reason: str


@dataclass
class Finding:
    """A finding from the audit output."""
    id: str
    type: str
    function: str
    file: str = ""
    line: Optional[int] = None
    severity: str = "unknown"
    confidence: float = 0.0
    raw: dict = field(default_factory=dict)


@dataclass
class ContractAnalysis:
    """Analysis result for a single contract."""
    file: str
    ground_truth_count: int
    detected: list[str]  # List of vuln IDs detected
    missed: list[str]    # List of vuln IDs missed
    findings_count: int
    detection_rate: float
    is_complete: bool  # All vulns detected


@dataclass
class SafeContractAnalysis:
    """Analysis result for a safe contract."""
    file: str
    is_safe: bool = True
    false_positives: int = 0
    reason: str = ""
    findings: list[str] = field(default_factory=list)


def load_ground_truth(worktree: Path) -> tuple[list[GroundTruthContract], list[SafeContract]]:
    """Load ground truth from YAML file."""
    gt_file = worktree / "ground-truth.yaml"
    if not gt_file.exists():
        raise FileNotFoundError(f"Ground truth file not found: {gt_file}")

    data = load_yaml(gt_file)

    contracts = []
    for c in data.get("contracts", []):
        vulns = []
        for v in c.get("vulnerabilities", []):
            vulns.append(GroundTruthVuln(
                id=v.get("id", ""),
                type=v.get("type", "unknown"),
                function=v.get("function", ""),
                line=int(v.get("line", 0)),
                severity=v.get("severity", "unknown"),
                description=v.get("description", ""),
                pattern=v.get("pattern", ""),
            ))
        contracts.append(GroundTruthContract(
            file=c.get("file", ""),
            vulnerabilities=vulns,
        ))

    safe_contracts = []
    for s in data.get("safe_contracts", []):
        safe_contracts.append(SafeContract(
            file=s.get("file", ""),
            reason=s.get("reason", ""),
        ))

    return contracts, safe_contracts


def load_findings(worktree: Path) -> list[Finding]:
    """Load findings from audit output files."""
    findings = []
    vrs_dir = worktree / ".vrs"

    # Try verdicts first (most complete, from debate stage)
    verdicts_file = vrs_dir / "findings" / "verdicts.json"
    if verdicts_file.exists():
        try:
            data = json.loads(verdicts_file.read_text())
            items = data if isinstance(data, list) else data.get("verdicts", [])
            for i, v in enumerate(items):
                file_path = v.get("file", v.get("location", {}).get("file", ""))
                findings.append(Finding(
                    id=v.get("id", f"verdict-{i}"),
                    type=v.get("type", v.get("vulnerability_type", "unknown")),
                    function=v.get("function", v.get("location", {}).get("function", "")),
                    file=file_path,
                    line=v.get("line", v.get("location", {}).get("line")),
                    severity=v.get("severity", "unknown"),
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
            items = data if isinstance(data, list) else data.get("investigations", [])
            for i, inv in enumerate(items):
                file_path = inv.get("file", inv.get("location", {}).get("file", ""))
                findings.append(Finding(
                    id=inv.get("id", f"agent-{i}"),
                    type=inv.get("type", inv.get("vulnerability_type", "unknown")),
                    function=inv.get("function", inv.get("target_function", "")),
                    file=file_path,
                    line=inv.get("line"),
                    severity=inv.get("severity", "unknown"),
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
            items = data if isinstance(data, list) else data.get("matches", [])
            for i, m in enumerate(items):
                file_path = m.get("file", m.get("location", {}).get("file", ""))
                findings.append(Finding(
                    id=m.get("pattern_id", f"pattern-{i}"),
                    type=m.get("type", m.get("category", "unknown")),
                    function=m.get("function", m.get("function_name", "")),
                    file=file_path,
                    line=m.get("line"),
                    severity=m.get("severity", "unknown"),
                    confidence=m.get("confidence", m.get("score", 0.0)),
                    raw=m,
                ))
        except (json.JSONDecodeError, KeyError):
            pass

    return findings


def normalize_filename(filename: str) -> str:
    """Normalize filename for matching."""
    # Remove path prefixes and normalize
    return Path(filename).name.lower()


def get_findings_for_contract(findings: list[Finding], contract_file: str) -> list[Finding]:
    """Get all findings that match a contract file."""
    normalized = normalize_filename(contract_file)
    result = []

    for f in findings:
        # Check if finding file matches
        finding_file = normalize_filename(f.file) if f.file else ""
        if finding_file and normalized in finding_file or finding_file in normalized:
            result.append(f)
            continue

        # Also check raw data for file references
        raw_file = f.raw.get("file", "")
        if raw_file:
            if normalized in normalize_filename(raw_file):
                result.append(f)
                continue

        # Check location in raw
        location = f.raw.get("location", {})
        if isinstance(location, dict):
            loc_file = location.get("file", "")
            if loc_file and normalized in normalize_filename(loc_file):
                result.append(f)

    return result


def match_finding_to_vuln(finding: Finding, vuln: GroundTruthVuln) -> bool:
    """Determine if a finding matches a ground truth vulnerability."""
    # Match by function name
    finding_func = finding.function.lower().strip()
    vuln_func = vuln.function.lower().strip()

    if finding_func and vuln_func:
        # Exact match
        if finding_func == vuln_func:
            return True
        # Partial match with same type
        if (finding_func in vuln_func or vuln_func in finding_func):
            return True

    # Match by line number (with tolerance)
    if vuln.line and finding.line:
        if abs(finding.line - vuln.line) <= 5:
            return True

    # Match by type (if function names overlap at all)
    finding_type = finding.type.lower()
    vuln_type = vuln.type.lower()

    if "reentr" in finding_type and "reentr" in vuln_type:
        # For reentrancy, check function name overlap
        if finding_func and vuln_func:
            finding_words = set(finding_func.replace("_", " ").split())
            vuln_words = set(vuln_func.replace("_", " ").split())
            if finding_words & vuln_words:
                return True

    return False


def analyze_contract(
    contract: GroundTruthContract,
    findings: list[Finding],
) -> ContractAnalysis:
    """Analyze detection results for a single contract."""
    contract_findings = get_findings_for_contract(findings, contract.file)

    detected = []
    missed = []

    for vuln in contract.vulnerabilities:
        found = any(match_finding_to_vuln(f, vuln) for f in contract_findings)
        if found:
            detected.append(vuln.id)
        else:
            missed.append(vuln.id)

    gt_count = len(contract.vulnerabilities)
    detection_rate = len(detected) / gt_count if gt_count > 0 else 0.0

    return ContractAnalysis(
        file=contract.file,
        ground_truth_count=gt_count,
        detected=detected,
        missed=missed,
        findings_count=len(contract_findings),
        detection_rate=detection_rate,
        is_complete=len(missed) == 0 and gt_count > 0,
    )


def analyze_safe_contract(
    safe: SafeContract,
    findings: list[Finding],
) -> SafeContractAnalysis:
    """Analyze false positive rate for a safe contract."""
    contract_findings = get_findings_for_contract(findings, safe.file)

    finding_ids = [f.id for f in contract_findings]

    return SafeContractAnalysis(
        file=safe.file,
        is_safe=True,
        false_positives=len(contract_findings),
        reason=safe.reason,
        findings=finding_ids,
    )


def analyze_by_variant(
    contracts: list[GroundTruthContract],
    analyses: dict[str, ContractAnalysis],
) -> dict[str, dict[str, Any]]:
    """Analyze detection rates by reentrancy variant."""
    variants: dict[str, dict[str, Any]] = {}

    for contract in contracts:
        for vuln in contract.vulnerabilities:
            # Determine variant from type or pattern
            variant = vuln.type
            if "cross" in variant.lower():
                variant = "cross-function"
            elif "modifier" in vuln.description.lower():
                variant = "modifier-bypass"
            else:
                variant = "classic"

            if variant not in variants:
                variants[variant] = {
                    "total": 0,
                    "detected": 0,
                    "vulnerabilities": [],
                }

            variants[variant]["total"] += 1
            variants[variant]["vulnerabilities"].append(vuln.id)

            # Check if detected
            analysis = analyses.get(contract.file)
            if analysis and vuln.id in analysis.detected:
                variants[variant]["detected"] += 1

    # Calculate rates
    for variant in variants:
        total = variants[variant]["total"]
        detected = variants[variant]["detected"]
        variants[variant]["detection_rate"] = detected / total if total > 0 else 0.0

    return variants


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Detailed per-contract analysis for SmartBugs suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s --worktree /tmp/vrs-worktrees/smartbugs-reentrancy
    %(prog)s --worktree /tmp/vrs-worktrees/smartbugs-reentrancy --output analysis.json
    %(prog)s --worktree /tmp/vrs-worktrees/smartbugs-reentrancy --verbose
        """,
    )
    parser.add_argument(
        "--worktree",
        required=True,
        help="Path to worktree containing ground-truth.yaml and .vrs/ outputs"
    )
    parser.add_argument(
        "--output",
        help="Output file for analysis JSON"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed analysis information"
    )
    args = parser.parse_args()

    worktree = Path(args.worktree)

    try:
        # Load data
        contracts, safe_contracts = load_ground_truth(worktree)
        if args.verbose:
            print(f"Loaded {len(contracts)} vulnerable contracts", file=sys.stderr)
            print(f"Loaded {len(safe_contracts)} safe contracts", file=sys.stderr)

        findings = load_findings(worktree)
        if args.verbose:
            print(f"Loaded {len(findings)} findings", file=sys.stderr)

        # Analyze each contract
        per_contract: dict[str, dict[str, Any]] = {}

        for contract in contracts:
            analysis = analyze_contract(contract, findings)
            per_contract[contract.file] = {
                "ground_truth_count": analysis.ground_truth_count,
                "detected": analysis.detected,
                "missed": analysis.missed,
                "findings_count": analysis.findings_count,
                "detection_rate": round(analysis.detection_rate, 4),
                "is_complete": analysis.is_complete,
            }

        # Analyze safe contracts
        for safe in safe_contracts:
            analysis = analyze_safe_contract(safe, findings)
            per_contract[safe.file] = {
                "is_safe": True,
                "false_positives": analysis.false_positives,
                "reason": analysis.reason,
                "findings": analysis.findings,
            }

        # Build summary
        total_contracts = len(contracts)
        detected_contracts = sum(
            1 for c in contracts
            if per_contract.get(c.file, {}).get("detection_rate", 0) > 0
        )
        missed_contracts = sum(
            1 for c in contracts
            if per_contract.get(c.file, {}).get("detection_rate", 0) == 0
        )
        complete_contracts = sum(
            1 for c in contracts
            if per_contract.get(c.file, {}).get("is_complete", False)
        )
        safe_flagged = sum(
            1 for s in safe_contracts
            if per_contract.get(s.file, {}).get("false_positives", 0) > 0
        )

        # Variant analysis
        variant_analysis = analyze_by_variant(
            contracts,
            {c.file: analyze_contract(c, findings) for c in contracts}
        )

        # Build result
        result = {
            "per_contract": per_contract,
            "summary": {
                "total_contracts": total_contracts,
                "detected_contracts": detected_contracts,
                "missed_contracts": missed_contracts,
                "complete_contracts": complete_contracts,
                "safe_contracts": len(safe_contracts),
                "safe_flagged": safe_flagged,
            },
            "by_variant": {
                name: {
                    "total": v["total"],
                    "detected": v["detected"],
                    "detection_rate": round(v["detection_rate"], 4),
                }
                for name, v in variant_analysis.items()
            },
            "findings_summary": {
                "total_findings": len(findings),
                "unique_functions": len(set(f.function for f in findings if f.function)),
            },
        }

        # Output
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
