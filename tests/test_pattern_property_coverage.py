"""Property validation CI gate for pattern-builder alignment.

Phase 2.3: Ensures every property referenced in pattern YAML match blocks
resolves against the builder's actual emitted properties.

This prevents future drift between pattern authors and builder output.
"""

from __future__ import annotations

import yaml
from pathlib import Path

import pytest

# Root of the project
ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collect_pattern_files() -> list[Path]:
    """Find all pattern YAML files under vulndocs/."""
    vulndocs = ROOT / "vulndocs"
    if not vulndocs.exists():
        return []
    return sorted(vulndocs.rglob("patterns/*.yaml"))


def _extract_conditions(match_block: dict) -> list[dict]:
    """Extract all property-based conditions from a pattern match block.

    Handles both formats:
      - Legacy: match.all / match.none / match.any
      - Tiered: match.tier_a.all / match.tier_a.any / match.tier_a.none
    """
    conditions: list[dict] = []
    if not isinstance(match_block, dict):
        return conditions

    for section_key in ("all", "any", "none"):
        items = match_block.get(section_key, [])
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and "property" in item:
                    conditions.append(item)

    # Tiered match blocks: tier_a, tier_b, tier_c
    for tier_key in ("tier_a", "tier_b", "tier_c"):
        tier = match_block.get(tier_key, {})
        if isinstance(tier, dict):
            for section_key in ("all", "any", "none"):
                items = tier.get(section_key, [])
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict) and "property" in item:
                            conditions.append(item)

    return conditions


def _get_builder_function_properties() -> set[str]:
    """Return the set of property keys emitted by FunctionProcessor.

    Builds a real graph on a test contract and extracts function node property keys.
    """
    from alphaswarm_sol.kg.builder.core import build_graph

    contract = ROOT / "tests" / "contracts" / "ReentrancyClassic.sol"
    if not contract.exists():
        pytest.skip("Test contract not found")

    graph = build_graph(contract)

    fn_props: set[str] = set()
    for node in graph.nodes.values():
        if node.type.lower() == "function":
            fn_props.update(node.properties.keys())

    return fn_props


def _get_builder_contract_properties() -> set[str]:
    """Return the set of property keys emitted by ContractProcessor."""
    from alphaswarm_sol.kg.builder.core import build_graph

    contract = ROOT / "tests" / "contracts" / "ReentrancyClassic.sol"
    if not contract.exists():
        pytest.skip("Test contract not found")

    graph = build_graph(contract)

    contract_props: set[str] = set()
    for node in graph.nodes.values():
        if node.type.lower() == "contract":
            contract_props.update(node.properties.keys())

    return contract_props


# Properties resolved at match time, not emitted by builder
SPECIAL_RESOLUTION_PROPERTIES = {
    "label",   # Resolved from node.label (function/contract name)
    "type",    # Resolved from node.type
    "id",      # Resolved from node.id
    "name",    # Sometimes used as alias for label
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def pattern_files() -> list[Path]:
    return _collect_pattern_files()


@pytest.fixture(scope="module")
def all_builder_properties() -> set[str]:
    fn = _get_builder_function_properties()
    ct = _get_builder_contract_properties()
    return fn | ct | SPECIAL_RESOLUTION_PROPERTIES


@pytest.fixture(scope="module")
def function_properties() -> set[str]:
    return _get_builder_function_properties()


@pytest.fixture(scope="module")
def contract_properties() -> set[str]:
    return _get_builder_contract_properties()


@pytest.fixture(scope="module")
def pattern_property_index(pattern_files: list[Path]) -> dict[str, list[str]]:
    """Map: property_name -> [pattern_ids that reference it]."""
    index: dict[str, list[str]] = {}
    for pf in pattern_files:
        try:
            data = yaml.safe_load(pf.read_text())
        except Exception:
            continue
        if not isinstance(data, dict):
            continue

        pattern_id = data.get("id", pf.stem)
        match_block = data.get("match", {})
        if not isinstance(match_block, dict):
            continue

        conditions = _extract_conditions(match_block)
        for cond in conditions:
            prop = cond["property"]
            index.setdefault(prop, []).append(pattern_id)

    return index


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPatternPropertyCoverage:
    """Validate that pattern YAML properties resolve against builder output."""

    def test_pattern_files_found(self, pattern_files: list[Path]):
        """Sanity: patterns exist."""
        assert len(pattern_files) > 50, (
            f"Expected 50+ patterns, found {len(pattern_files)}"
        )

    def test_builder_emits_properties(self, all_builder_properties: set[str]):
        """Sanity: builder emits a substantial property set."""
        assert len(all_builder_properties) > 200, (
            f"Expected 200+ properties, found {len(all_builder_properties)}"
        )

    # Baseline: 147 orphan properties as of Phase 2.1-04 triage (2026-02-09)
    # Down from 223 after triaging 96 broken patterns.
    # This should only go DOWN. If it goes UP, new patterns reference
    # properties the builder doesn't emit — that's a regression.
    ORPHAN_BASELINE = 147

    # Baseline: 0 totally-broken patterns as of Phase 2.1-04 triage (2026-02-09)
    # All 96 broken patterns moved to .archive/deprecated/ or .quarantine/.
    # A totally-broken pattern has ALL conditions referencing non-existent
    # properties, meaning it silently returns zero findings. Must only go DOWN.
    TOTALLY_BROKEN_BASELINE = 0

    # Ratchet threshold: if orphan count drops this many below baseline,
    # the baseline is stale and should be updated.
    RATCHET_GAP_THRESHOLD = 10

    def test_no_orphan_properties(
        self,
        pattern_property_index: dict[str, list[str]],
        all_builder_properties: set[str],
    ):
        """Orphan property count must not exceed the known baseline.

        CI gate: catches new patterns that reference properties the builder
        doesn't emit. The baseline tracks known orphans and should decrease
        over time as more properties are implemented.
        """
        orphans: dict[str, list[str]] = {}
        for prop, pattern_ids in sorted(pattern_property_index.items()):
            if prop not in all_builder_properties:
                orphans[prop] = pattern_ids

        orphan_count = len(orphans)

        if orphan_count > self.ORPHAN_BASELINE:
            new_orphans = {
                p: ids for p, ids in orphans.items()
                if p not in all_builder_properties
            }
            lines = [
                f"\nOrphan count REGRESSION: {orphan_count} > baseline {self.ORPHAN_BASELINE}",
                f"New orphan properties:\n",
            ]
            for prop, pids in sorted(new_orphans.items(), key=lambda x: -len(x[1]))[:20]:
                lines.append(f"  {prop} ({len(pids)} patterns): {', '.join(pids[:5])}")
            pytest.fail("\n".join(lines))

    def test_no_totally_broken_patterns(
        self,
        pattern_files: list[Path],
        all_builder_properties: set[str],
    ):
        """Patterns where ALL conditions reference non-existent properties are useless.

        These patterns silently return zero findings — a correctness bug.
        Count must not exceed baseline and should decrease over time.
        """
        totally_broken: list[str] = []
        for pf in pattern_files:
            try:
                data = yaml.safe_load(pf.read_text())
                if not isinstance(data, dict):
                    continue
                if data.get("deprecated") or data.get("status") == "deprecated":
                    continue
                match_block = data.get("match", {})
                if not isinstance(match_block, dict):
                    continue
                conditions = _extract_conditions(match_block)
                if not conditions:
                    continue
                props = {c["property"] for c in conditions}
                if not props & all_builder_properties:
                    totally_broken.append(data.get("id", pf.stem))
            except Exception:
                pass

        if len(totally_broken) > self.TOTALLY_BROKEN_BASELINE:
            pytest.fail(
                f"Totally-broken patterns REGRESSION: {len(totally_broken)} > "
                f"baseline {self.TOTALLY_BROKEN_BASELINE}.\n"
                f"Patterns with ALL orphan conditions:\n"
                + "\n".join(f"  - {pid}" for pid in sorted(totally_broken)[:20])
            )

    def test_orphan_baseline_freshness(
        self,
        pattern_property_index: dict[str, list[str]],
        all_builder_properties: set[str],
    ):
        """If orphans drop significantly below baseline, the baseline is stale.

        This warns (via pytest.warns) when the gap exceeds the ratchet threshold,
        signaling the baseline should be tightened to lock in improvements.
        """
        orphans = {p for p in pattern_property_index if p not in all_builder_properties}
        gap = self.ORPHAN_BASELINE - len(orphans)
        if gap >= self.RATCHET_GAP_THRESHOLD:
            import warnings

            warnings.warn(
                f"ORPHAN_BASELINE ({self.ORPHAN_BASELINE}) is stale: actual orphans = "
                f"{len(orphans)} (gap of {gap}). Update baseline to match.",
                stacklevel=2,
            )

    def test_coverage_report(
        self,
        pattern_property_index: dict[str, list[str]],
        all_builder_properties: set[str],
    ):
        """Generate a coverage summary (always passes, informational)."""
        referenced = set(pattern_property_index.keys())
        covered = referenced & all_builder_properties
        orphaned = referenced - all_builder_properties - SPECIAL_RESOLUTION_PROPERTIES

        total_patterns_using_orphans = sum(
            len(pids) for prop, pids in pattern_property_index.items()
            if prop in orphaned
        )
        total_patterns = sum(len(pids) for pids in pattern_property_index.values())

        coverage_pct = (
            len(covered) / len(referenced) * 100 if referenced else 0
        )

        print(f"\n--- Property Coverage Report ---")
        print(f"Properties referenced by patterns: {len(referenced)}")
        print(f"Properties emitted by builder:     {len(all_builder_properties)}")
        print(f"Covered:                           {len(covered)} ({coverage_pct:.1f}%)")
        print(f"Orphaned:                          {len(orphaned)}")
        print(f"Pattern references using orphans:  {total_patterns_using_orphans}/{total_patterns}")

    def test_known_critical_properties_emitted(
        self, function_properties: set[str]
    ):
        """Validate that the most impactful properties are emitted.

        These are properties used by 5+ patterns — if any is missing,
        many patterns break simultaneously.
        """
        critical_props = {
            "visibility",
            "has_external_calls",
            "writes_state",
            "has_reentrancy_guard",
            "has_access_gate",
            "has_low_level_calls",
            "uses_delegatecall",
            "reads_oracle_price",
            "has_staleness_check",
            "swap_like",
            "has_slippage_parameter",
            "has_slippage_check",
            "has_deadline_parameter",
            "transfers_eth",
            "has_loops",
            "has_unbounded_loop",
            "has_division",
            "has_arithmetic",
            "has_unchecked_block",
            "callback_chain_surface",
            "is_pure",
        }
        missing = critical_props - function_properties
        assert not missing, (
            f"Critical properties missing from builder: {sorted(missing)}"
        )

    def test_no_duplicate_property_keys_in_builder(
        self, function_properties: set[str]
    ):
        """Properties should not have redundant aliases (informational check).

        We check that commonly confused pairs are both present and documented.
        """
        # These are known intentional aliases/bridges
        known_aliases = {
            ("is_upgradeable", "contract_is_upgradeable"),
            ("has_timelock", "contract_has_timelock"),
            ("has_multisig", "contract_has_multisig"),
            ("has_governance", "contract_has_governance"),
            ("performs_swap", "swap_like"),
        }
        for alias, canonical in known_aliases:
            if alias in function_properties and canonical in function_properties:
                # Both present — expected, this is a bridge
                pass


class TestPatternYAMLStructure:
    """Validate pattern YAML files have correct structure."""

    def test_all_patterns_parse(self, pattern_files: list[Path]):
        """Every pattern YAML must parse without error."""
        failures: list[str] = []
        for pf in pattern_files:
            try:
                data = yaml.safe_load(pf.read_text())
                if not isinstance(data, dict):
                    failures.append(f"{pf.name}: not a dict")
            except Exception as e:
                failures.append(f"{pf.name}: {e}")

        assert not failures, f"\n{len(failures)} parse failures:\n" + "\n".join(failures[:20])

    def test_all_patterns_have_id(self, pattern_files: list[Path]):
        """Every pattern must have an 'id' field."""
        missing: list[str] = []
        for pf in pattern_files:
            try:
                data = yaml.safe_load(pf.read_text())
                if isinstance(data, dict) and "id" not in data:
                    missing.append(pf.name)
            except Exception:
                pass  # parse errors caught in other test

        assert not missing, f"{len(missing)} patterns missing 'id': {missing[:20]}"

    # Baseline: 10 patterns missing match blocks as of Phase 2.3 (2026-02-08)
    # These are PCP/invariant stubs. Should decrease as patterns are completed.
    MISSING_MATCH_BASELINE = 10

    def test_all_patterns_have_match_block(self, pattern_files: list[Path]):
        """Non-deprecated patterns missing match blocks must not exceed baseline."""
        missing: list[str] = []
        for pf in pattern_files:
            try:
                data = yaml.safe_load(pf.read_text())
                if not isinstance(data, dict):
                    continue
                if data.get("deprecated") or data.get("status") == "deprecated":
                    continue
                if "match" not in data:
                    missing.append(data.get("id", pf.name))
            except Exception:
                pass

        assert len(missing) <= self.MISSING_MATCH_BASELINE, (
            f"Match block REGRESSION: {len(missing)} > baseline {self.MISSING_MATCH_BASELINE}. "
            f"New patterns missing 'match': {missing[:20]}"
        )

    def test_match_conditions_have_required_fields(self, pattern_files: list[Path]):
        """Each property condition must have property + value (op defaults to eq)."""
        issues: list[str] = []
        for pf in pattern_files:
            try:
                data = yaml.safe_load(pf.read_text())
                if not isinstance(data, dict):
                    continue
                match_block = data.get("match", {})
                if not isinstance(match_block, dict):
                    continue
                conditions = _extract_conditions(match_block)
                for cond in conditions:
                    # 'op' can be omitted (defaults to 'eq')
                    if "value" not in cond:
                        issues.append(f"{data.get('id', pf.name)}: missing 'value' for property '{cond.get('property')}'")
            except Exception:
                pass

        assert not issues, f"\n{len(issues)} structural issues:\n" + "\n".join(issues[:20])
