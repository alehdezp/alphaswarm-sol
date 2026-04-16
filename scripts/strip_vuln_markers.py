#!/usr/bin/env python3
"""Strip VULNERABILITY markers from corpus contracts, preserving ground truth.

Prestep P3 for Phase 3.1c: markers like `// VULNERABILITY: ...` and
`* VULNERABILITY: ...` give agents the answers, invalidating evaluation.

This script:
1. Extracts markers to corpus/ground_truth_markers.yaml
2. Strips markers from .sol files (replaces with plain comments)
3. Is idempotent — safe to re-run

Usage:
    python scripts/strip_vuln_markers.py [--dry-run] [--contracts-dir DIR]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import yaml

DEFAULT_DIR = Path("tests/contracts")
GROUND_TRUTH_PATH = Path("corpus/ground_truth_markers.yaml")

# Matches lines containing VULNERABILITY: or CRITICAL VULNERABILITY: or THE VULNERABILITY:
MARKER_RE = re.compile(
    r"(//\s*(?:CRITICAL\s+)?(?:THE\s+)?VULNERABILITY:\s*)(.*)",
    re.IGNORECASE,
)
NATSPEC_MARKER_RE = re.compile(
    r"(\*\s*(?:CRITICAL\s+)?(?:THE\s+)?VULNERABILITY:\s*)(.*)",
    re.IGNORECASE,
)


def check_git_clean() -> None:
    """Fail fast if working tree has staged changes in contracts dir."""
    result = subprocess.run(
        ["git", "status", "--porcelain", str(DEFAULT_DIR)],
        capture_output=True,
        text=True,
    )
    staged = [l for l in result.stdout.strip().splitlines() if l and l[0] != "?"]
    if staged:
        print("ERROR: Dirty working tree in contracts dir. Commit or stash first.", file=sys.stderr)
        print("\n".join(staged), file=sys.stderr)
        sys.exit(1)


def extract_and_strip(contracts_dir: Path, dry_run: bool = False) -> dict:
    """Extract markers and strip them. Returns ground truth dict."""
    ground_truth: dict[str, list[dict]] = {}
    files_changed = 0

    for sol_file in sorted(contracts_dir.rglob("*.sol")):
        lines = sol_file.read_text().splitlines(keepends=True)
        markers: list[dict] = []
        new_lines: list[str] = []
        changed = False

        for i, line in enumerate(lines, 1):
            # Check single-line comment markers
            m = MARKER_RE.search(line)
            if m:
                markers.append({"line": i, "text": m.group(0).strip()})
                # Replace with generic comment
                stripped = MARKER_RE.sub(r"// \2", line)
                new_lines.append(stripped)
                changed = True
                continue

            # Check NatSpec/block comment markers
            m = NATSPEC_MARKER_RE.search(line)
            if m:
                markers.append({"line": i, "text": m.group(0).strip()})
                stripped = NATSPEC_MARKER_RE.sub(r"* \2", line)
                new_lines.append(stripped)
                changed = True
                continue

            new_lines.append(line)

        if markers:
            rel_path = str(sol_file.relative_to(contracts_dir.parent.parent))
            ground_truth[rel_path] = markers

            if changed and not dry_run:
                sol_file.write_text("".join(new_lines))
                files_changed += 1

    return {"files_changed": files_changed, "ground_truth": ground_truth}


def save_ground_truth(ground_truth: dict, output_path: Path, dry_run: bool) -> None:
    """Save extracted markers to YAML."""
    doc = {
        "version": "1.0.0",
        "description": "Vulnerability markers extracted from corpus contracts by strip_vuln_markers.py",
        "note": "These markers were removed to prevent agents from trivially finding vulnerabilities during evaluation.",
        "markers": ground_truth,
    }
    if dry_run:
        print(f"Would write ground truth to {output_path}")
        print(yaml.dump(doc, default_flow_style=False, sort_keys=False)[:500])
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(yaml.dump(doc, default_flow_style=False, sort_keys=False))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without modifying files")
    parser.add_argument("--contracts-dir", type=Path, default=DEFAULT_DIR, help="Contracts directory")
    parser.add_argument("--skip-git-check", action="store_true", help="Skip dirty working tree check")
    args = parser.parse_args()

    if not args.skip_git_check and not args.dry_run:
        check_git_clean()

    result = extract_and_strip(args.contracts_dir, dry_run=args.dry_run)
    ground_truth = result["ground_truth"]

    if not ground_truth:
        print("No VULNERABILITY markers found. Already stripped or none present.")
        return

    total_markers = sum(len(v) for v in ground_truth.values())
    print(f"Found {total_markers} markers across {len(ground_truth)} files")

    save_ground_truth(ground_truth, GROUND_TRUTH_PATH, dry_run=args.dry_run)

    if args.dry_run:
        print(f"\n[DRY RUN] Would strip {total_markers} markers from {len(ground_truth)} files")
        for f, markers in ground_truth.items():
            print(f"  {f}: {len(markers)} markers")
    else:
        print(f"\nStripped {total_markers} markers from {result['files_changed']} files")
        print(f"Ground truth saved to {GROUND_TRUTH_PATH}")


if __name__ == "__main__":
    main()
