#!/usr/bin/env python3
"""Migrate evaluation contracts to hardened schema (Plan 06).

Three operations:
(a) insert_with_category_default() — hooks and evaluation_config
(b) migrate_deprecated() — metadata.evaluation_depth → evaluation_config.depth
(c) set_if_absent() — status: active, coverage_axes: []

Idempotent: safe to run multiple times. Does NOT set reasoning_dimensions.

Usage:
    python scripts/migrate_contracts.py [--dry-run]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

CONTRACTS_DIR = Path("src/alphaswarm_sol/testing/evaluation/contracts")
TEMPLATES_DIR = CONTRACTS_DIR / "templates"

# Category → default hooks (from CONTEXT.md P13-IMP-10/CSC-01)
CATEGORY_HOOKS: dict[str, list[str]] = {
    "agent": ["SessionStart", "Stop", "PreCompact", "TeammateIdle", "TaskCompleted", "SessionEnd"],
    "skill": ["Stop", "SessionEnd"],
    "orchestrator": ["TeammateIdle", "TaskCompleted", "PreCompact", "SessionEnd"],
}

# Category → default evaluation_config
CATEGORY_EVAL_CONFIG: dict[str, dict] = {
    "agent": {"run_gvs": True, "run_reasoning": True, "debrief": True, "depth": "deep"},
    "skill": {"run_gvs": False, "run_reasoning": True, "debrief": False, "depth": "standard"},
    "orchestrator": {"run_gvs": True, "run_reasoning": True, "debrief": True, "depth": "deep"},
}


def insert_with_category_default(contract: dict) -> bool:
    """Insert hooks and evaluation_config using category defaults."""
    changed = False
    cat = contract.get("category", "skill")

    if "hooks" not in contract:
        contract["hooks"] = CATEGORY_HOOKS.get(cat, ["Stop", "SessionEnd"])
        changed = True

    if "evaluation_config" not in contract:
        contract["evaluation_config"] = dict(CATEGORY_EVAL_CONFIG.get(cat, CATEGORY_EVAL_CONFIG["skill"]))
        changed = True
    else:
        ec = contract["evaluation_config"]
        defaults = CATEGORY_EVAL_CONFIG.get(cat, CATEGORY_EVAL_CONFIG["skill"])
        for key in ("run_gvs", "run_reasoning", "debrief", "depth"):
            if key not in ec:
                ec[key] = defaults[key]
                changed = True

    return changed


def migrate_deprecated(contract: dict) -> bool:
    """Move metadata.evaluation_depth → evaluation_config.depth."""
    meta = contract.get("metadata", {})
    if not meta or "evaluation_depth" not in meta:
        return False

    ec = contract.setdefault("evaluation_config", {})
    if "depth" not in ec:
        ec["depth"] = meta.pop("evaluation_depth")
    else:
        meta.pop("evaluation_depth")
    if not meta:
        contract.pop("metadata", None)
    return True


def set_if_absent(contract: dict) -> bool:
    """Set status: active and coverage_axes: [] if missing."""
    changed = False
    if "status" not in contract:
        contract["status"] = "active"
        changed = True
    if "coverage_axes" not in contract:
        contract["coverage_axes"] = []
        changed = True
    return changed


def migrate_file(path: Path, dry_run: bool = False) -> bool:
    """Migrate a single contract file. Returns True if changed."""
    with open(path) as f:
        contract = yaml.safe_load(f)
    if not isinstance(contract, dict):
        return False

    c1 = migrate_deprecated(contract)
    c2 = insert_with_category_default(contract)
    c3 = set_if_absent(contract)
    changed = c1 or c2 or c3

    if changed and not dry_run:
        with open(path, "w") as f:
            yaml.dump(contract, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate evaluation contracts to hardened schema")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing")
    args = parser.parse_args()

    targets = list(CONTRACTS_DIR.glob("*.yaml")) + list(TEMPLATES_DIR.glob("*.yaml"))
    targets = [t for t in targets if t.name != "dimension_registry.yaml"]

    changed_count = 0
    for path in sorted(targets):
        changed = migrate_file(path, dry_run=args.dry_run)
        label = "[CHANGED]" if changed else "[OK]"
        print(f"  {label} {path.relative_to(CONTRACTS_DIR.parent.parent.parent.parent)}")
        if changed:
            changed_count += 1

    action = "would change" if args.dry_run else "changed"
    print(f"\n{changed_count}/{len(targets)} files {action}")
    if args.dry_run and changed_count > 0:
        print("Run without --dry-run to apply changes.")


if __name__ == "__main__":
    main()
