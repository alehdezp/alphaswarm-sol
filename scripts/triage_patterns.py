#!/usr/bin/env python3
"""Pattern triage script: classify all patterns by property health.

Builds a real graph on tests/contracts/ReentrancyClassic.sol, extracts
all builder-emitted properties, then scans every pattern YAML to classify:

  WORKING  — All tier_a property conditions resolve
  PARTIAL  — Some resolve, some are orphans
  BROKEN   — ALL property conditions are orphans (none resolve)
  NO_MATCH — Pattern has no match block or no property conditions
"""
from __future__ import annotations

import sys
import yaml
from pathlib import Path
from collections import defaultdict

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

VULNDOCS = ROOT / "vulndocs"

# ---------------------------------------------------------------------------
# Get actual builder properties by building a real graph
# ---------------------------------------------------------------------------

from alphaswarm_sol.kg.builder.core import build_graph

contract = ROOT / "tests" / "contracts" / "ReentrancyClassic.sol"
print(f"Building graph on {contract.name}...")
graph = build_graph(contract)

fn_props: set[str] = set()
contract_props: set[str] = set()
for node in graph.nodes.values():
    if node.type.lower() == "function":
        fn_props.update(node.properties.keys())
    elif node.type.lower() == "contract":
        contract_props.update(node.properties.keys())

# Special resolution properties (resolved at match time, not emitted)
SPECIAL = {"label", "type", "id", "name"}
builder_props = fn_props | contract_props | SPECIAL

print(f"Builder emits {len(fn_props)} function properties, {len(contract_props)} contract properties")
print(f"Total resolvable properties: {len(builder_props)}")
print()

# ---------------------------------------------------------------------------
# Extract property conditions from match blocks
# ---------------------------------------------------------------------------

def extract_property_names(match_block: dict) -> list[str]:
    """Extract all property names from a match block."""
    props = []
    if not isinstance(match_block, dict):
        return props

    for section in ("all", "any", "none"):
        items = match_block.get(section, [])
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and "property" in item:
                    props.append(item["property"])

    # Tiered: tier_a
    for tier_key in ("tier_a",):
        tier = match_block.get(tier_key, {})
        if isinstance(tier, dict):
            for section in ("all", "any", "none"):
                items = tier.get(section, [])
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict) and "property" in item:
                            props.append(item["property"])

    return props

# ---------------------------------------------------------------------------
# Classify patterns
# ---------------------------------------------------------------------------

pattern_files = sorted(VULNDOCS.rglob("patterns/*.yaml"))
print(f"Found {len(pattern_files)} pattern files\n")

class PatternInfo:
    def __init__(self, path: Path, pattern_id: str, status: str,
                 all_props: list[str], orphan_props: list[str],
                 working_props: list[str], has_ops: bool, severity: str,
                 raw_data: dict):
        self.path = path
        self.pattern_id = pattern_id
        self.status = status
        self.all_props = all_props
        self.orphan_props = orphan_props
        self.working_props = working_props
        self.has_ops = has_ops
        self.severity = severity
        self.raw_data = raw_data

results: list[PatternInfo] = []

for pf in pattern_files:
    try:
        data = yaml.safe_load(pf.read_text())
    except Exception:
        continue
    if not isinstance(data, dict):
        continue

    pattern_id = data.get("id", pf.stem)
    severity = data.get("severity", "medium")
    match_block = data.get("match", {})

    if not isinstance(match_block, dict):
        results.append(PatternInfo(
            path=pf, pattern_id=pattern_id, status="NO_MATCH",
            all_props=[], orphan_props=[], working_props=[],
            has_ops=False, severity=severity, raw_data=data
        ))
        continue

    props = extract_property_names(match_block)

    # Check for operation conditions (they don't need property resolution)
    has_ops = False
    for section in ("all", "any", "none"):
        items = match_block.get(section, []) or []
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    if any(k in item for k in ("has_operation", "has_all_operations",
                                                 "has_any_operation", "sequence_order",
                                                 "signature_matches")):
                        has_ops = True
    # Also check tier_a
    tier_a = match_block.get("tier_a", {})
    if isinstance(tier_a, dict):
        for section in ("all", "any", "none"):
            items = tier_a.get(section, []) or []
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        if any(k in item for k in ("has_operation", "has_all_operations",
                                                     "has_any_operation", "sequence_order",
                                                     "signature_matches")):
                            has_ops = True

    if not props:
        # No property conditions at all (may have operation conditions)
        status = "NO_MATCH" if not has_ops else "WORKING"
        results.append(PatternInfo(
            path=pf, pattern_id=pattern_id, status=status,
            all_props=[], orphan_props=[], working_props=[],
            has_ops=has_ops, severity=severity, raw_data=data
        ))
        continue

    orphans = [p for p in props if p not in builder_props]
    working = [p for p in props if p in builder_props]

    if not orphans:
        status = "WORKING"
    elif not working:
        # ALL property conditions are orphans
        if has_ops:
            # Has operation conditions that work even if property conditions are broken
            status = "PARTIAL"
        else:
            status = "BROKEN"
    else:
        status = "PARTIAL"

    results.append(PatternInfo(
        path=pf, pattern_id=pattern_id, status=status,
        all_props=props, orphan_props=orphans, working_props=working,
        has_ops=has_ops, severity=severity, raw_data=data
    ))

# ---------------------------------------------------------------------------
# Print results
# ---------------------------------------------------------------------------

working = [r for r in results if r.status == "WORKING"]
partial = [r for r in results if r.status == "PARTIAL"]
broken = [r for r in results if r.status == "BROKEN"]
no_match = [r for r in results if r.status == "NO_MATCH"]

print("=" * 80)
print(f"PATTERN TRIAGE RESULTS")
print("=" * 80)
print(f"  WORKING:  {len(working):>4}  (all property conditions resolve)")
print(f"  PARTIAL:  {len(partial):>4}  (some orphan properties)")
print(f"  BROKEN:   {len(broken):>4}  (ALL property conditions are orphans)")
print(f"  NO_MATCH: {len(no_match):>4}  (no match block or no property conditions)")
print(f"  TOTAL:    {len(results):>4}")
print()

# Show all BROKEN patterns
print("=" * 80)
print("BROKEN PATTERNS (ALL conditions reference non-existent properties)")
print("=" * 80)
for r in sorted(broken, key=lambda x: x.pattern_id):
    rel = r.path.relative_to(VULNDOCS)
    print(f"\n  {r.pattern_id}  [{r.severity}]")
    print(f"    File: {rel}")
    print(f"    Orphan properties: {', '.join(r.orphan_props)}")

# Show PARTIAL patterns
print()
print("=" * 80)
print("PARTIAL PATTERNS (some orphan properties)")
print("=" * 80)
for r in sorted(partial, key=lambda x: x.pattern_id):
    rel = r.path.relative_to(VULNDOCS)
    print(f"\n  {r.pattern_id}  [{r.severity}]")
    print(f"    File: {rel}")
    print(f"    Working: {', '.join(r.working_props)}")
    print(f"    Orphan:  {', '.join(r.orphan_props)}")

# Show NO_MATCH patterns
print()
print("=" * 80)
print("NO_MATCH PATTERNS (no match block or no property conditions)")
print("=" * 80)
for r in sorted(no_match, key=lambda x: x.pattern_id):
    rel = r.path.relative_to(VULNDOCS)
    ops_note = " [has operation conditions]" if r.has_ops else ""
    print(f"  {r.pattern_id}  [{r.severity}]{ops_note}  ({rel})")

# ---------------------------------------------------------------------------
# Unique orphan properties across all patterns
# ---------------------------------------------------------------------------
print()
print("=" * 80)
print("UNIQUE ORPHAN PROPERTIES (referenced but not emitted)")
print("=" * 80)

orphan_index: dict[str, list[str]] = defaultdict(list)
for r in results:
    for p in r.orphan_props:
        orphan_index[p].append(r.pattern_id)

for prop, pids in sorted(orphan_index.items(), key=lambda x: -len(x[1])):
    status_marks = []
    for pid in pids:
        for r in results:
            if r.pattern_id == pid:
                status_marks.append(f"{pid}[{r.status}]")
                break
    print(f"  {prop} ({len(pids)} patterns): {', '.join(status_marks[:8])}")

# ---------------------------------------------------------------------------
# Dump machine-readable list of broken pattern IDs + paths
# ---------------------------------------------------------------------------
print()
print("=" * 80)
print("BROKEN PATTERN PATHS (for git mv)")
print("=" * 80)
for r in sorted(broken, key=lambda x: x.pattern_id):
    rel = r.path.relative_to(ROOT)
    print(f"  {rel}")
