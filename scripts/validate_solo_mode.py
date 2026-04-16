#!/usr/bin/env python3
"""
Validate solo mode output.

Solo mode should:
- Complete Stages 1-5, 7
- Skip Stage 6 (debate) - verdicts.json should NOT exist

Usage:
    python scripts/validate_solo_mode.py /path/to/worktree
"""

from __future__ import annotations

import sys
from pathlib import Path


def validate_solo_mode(worktree: Path) -> bool:
    """Validate solo mode output.

    Returns:
        True if validation passes, False otherwise.
    """
    vrs_dir = worktree / ".vrs"
    all_passed = True
    checks = []

    # Stage 2: Graph exists
    graph_exists = (
        list((vrs_dir / "graphs").glob("*.toon")) or
        list((vrs_dir / "graphs").glob("*.json"))
    ) if (vrs_dir / "graphs").exists() else []

    if graph_exists:
        checks.append(("Stage 2: Graph exists", "PASS", str(graph_exists[0].name)))
    else:
        checks.append(("Stage 2: Graph exists", "FAIL", "No graph file found"))
        all_passed = False

    # Stage 4: Pattern matches exist
    pattern_file = vrs_dir / "findings" / "pattern-matches.json"
    if pattern_file.exists():
        checks.append(("Stage 4: Pattern matches", "PASS", str(pattern_file)))
    else:
        checks.append(("Stage 4: Pattern matches", "FAIL", "No pattern matches file"))
        all_passed = False

    # Stage 5: Agent investigations exist
    agent_file = vrs_dir / "findings" / "agent-investigations.json"
    if agent_file.exists():
        checks.append(("Stage 5: Agent investigations", "PASS", str(agent_file)))
    else:
        checks.append(("Stage 5: Agent investigations", "FAIL", "No agent investigations"))
        all_passed = False

    # Stage 6: MUST NOT EXIST (solo mode skips debate)
    verdicts_file = vrs_dir / "findings" / "verdicts.json"
    if not verdicts_file.exists():
        checks.append(("Stage 6: Verdicts ABSENT", "PASS", "Correctly skipped (no verdicts.json)"))
    else:
        checks.append(("Stage 6: Verdicts ABSENT", "FAIL", "verdicts.json should NOT exist in solo mode"))
        all_passed = False

    # Stage 7: Report exists
    report_file = vrs_dir / "reports" / "audit-report.md"
    if report_file.exists():
        checks.append(("Stage 7: Report exists", "PASS", str(report_file)))
    else:
        checks.append(("Stage 7: Report exists", "FAIL", "No audit report"))
        all_passed = False

    # Print results
    print("Solo Mode Validation Results:")
    print("-" * 60)
    for check_name, status, detail in checks:
        status_symbol = "[PASS]" if status == "PASS" else "[FAIL]"
        print(f"  {status_symbol} {check_name}")
        print(f"         {detail}")
    print("-" * 60)

    if all_passed:
        print("Solo mode validation: PASSED")
        print("  - Stages 1-5, 7: Completed")
        print("  - Stage 6: Correctly skipped")
    else:
        print("Solo mode validation: FAILED")

    return all_passed


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python validate_solo_mode.py <worktree-path>", file=sys.stderr)
        return 1

    worktree = Path(sys.argv[1])
    if not worktree.exists():
        print(f"ERROR: Worktree does not exist: {worktree}", file=sys.stderr)
        return 1

    return 0 if validate_solo_mode(worktree) else 1


if __name__ == "__main__":
    sys.exit(main())
