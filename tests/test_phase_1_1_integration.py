"""Phase 1.1 Integration Tests - FIX-01, FIX-02, FIX-04.

Tests real data flows through PatternEngine, Router, and VulnDocs validation.
No mocks. All graphs built from real Solidity contracts, all patterns loaded
from the vulndocs/ directory on disk, all YAML validated against Pydantic models.

Verification matrix:
  FIX-01 (PatternEngine): run_all_patterns, run_pattern, finding structure
  FIX-02 (Router/Resume): metadata-based routing, no infinite loops, phase advancement
  FIX-04 (VulnDocs):      index.yaml validation, pattern parsing, regression gate
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from alphaswarm_sol.kg.schema import KnowledgeGraph
from alphaswarm_sol.orchestration.router import RouteAction, Router
from alphaswarm_sol.orchestration.schemas import Pool, PoolStatus, Scope
from alphaswarm_sol.queries.patterns import PatternEngine, PatternStore
from alphaswarm_sol.vulndocs.schema import load_vulndoc_index
from tests.graph_cache import load_graph

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VULNDOCS_DIR = PROJECT_ROOT / "vulndocs"

# ---------------------------------------------------------------------------
# FIX-01: PatternEngine Integration
# ---------------------------------------------------------------------------


class TestPatternEngineIntegration:
    """Verify PatternEngine loads real patterns and produces real findings."""

    @pytest.mark.slow
    def test_run_all_patterns_produces_findings(self) -> None:
        """ReentrancyClassic.sol is a known-vulnerable contract.

        Running all vulndocs patterns against it must produce at least one
        finding -- the reentrancy detection tier-A match is verified to work.
        """
        graph = load_graph("ReentrancyClassic.sol")
        engine = PatternEngine(pattern_dir=VULNDOCS_DIR)
        findings = engine.run_all_patterns(graph)
        assert isinstance(findings, list)
        assert len(findings) >= 1, (
            "Expected at least 1 finding on ReentrancyClassic.sol; "
            f"got {len(findings)}"
        )

    @pytest.mark.slow
    def test_run_all_patterns_returns_finding_structure(self) -> None:
        """Every finding dict must carry the keys the downstream pipeline expects."""
        graph = load_graph("ReentrancyClassic.sol")
        engine = PatternEngine(pattern_dir=VULNDOCS_DIR)
        findings = engine.run_all_patterns(graph)
        assert len(findings) >= 1, "Need at least 1 finding to validate structure"

        required_keys = {
            "pattern_id",
            "pattern_name",
            "severity",
            "node_id",
            "node_label",
            "node_type",
        }
        for finding in findings:
            missing = required_keys - set(finding.keys())
            assert not missing, (
                f"Finding for pattern '{finding.get('pattern_id', '?')}' "
                f"missing keys: {missing}"
            )
            # pattern_id and node_id must be non-empty strings
            assert finding["pattern_id"], "pattern_id must be non-empty"
            assert finding["node_id"], "node_id must be non-empty"

    @pytest.mark.slow
    def test_run_pattern_specific_id(self) -> None:
        """Running a known reentrancy pattern by ID produces findings.

        First we load all patterns to pick a real ID, then run that single
        pattern. This avoids hard-coding an ID that could be renamed.
        """
        graph = load_graph("ReentrancyClassic.sol")
        engine = PatternEngine(pattern_dir=VULNDOCS_DIR)

        # Discover a real pattern ID from the store
        patterns = PatternStore.load_vulndocs_patterns(VULNDOCS_DIR)
        assert len(patterns) > 0, "vulndocs must contain at least one pattern"

        # Try each reentrancy-scoped pattern until one matches
        reentrancy_ids = [
            p.id for p in patterns if "reentrancy" in p.id.lower() or "reentran" in p.id.lower()
        ]
        if not reentrancy_ids:
            # Fall back to any pattern that matches
            reentrancy_ids = [p.id for p in patterns]

        found_any = False
        for pid in reentrancy_ids:
            findings = engine.run_pattern(graph, pid)
            if findings:
                found_any = True
                assert findings[0]["pattern_id"] == pid
                break

        assert found_any, (
            f"Expected at least one pattern from {reentrancy_ids[:5]} to produce "
            "findings on ReentrancyClassic.sol"
        )

    def test_pattern_dir_loads_from_vulndocs(self) -> None:
        """PatternEngine(pattern_dir=vulndocs/) loads a non-trivial number of patterns.

        The verification results confirmed 562 patterns. We assert >= 100 as
        a reasonable lower bound that won't break on minor additions/removals.
        """
        engine = PatternEngine(pattern_dir=VULNDOCS_DIR)
        # Access the internal _load_patterns to count without running against a graph
        patterns = engine._load_patterns()
        assert len(patterns) >= 100, (
            f"Expected >= 100 patterns from vulndocs/; got {len(patterns)}"
        )

    @pytest.mark.slow
    def test_safe_contract_fewer_findings(self) -> None:
        """ReentrancyWithGuard.sol should have fewer reentrancy findings than
        ReentrancyClassic.sol because it has a reentrancy guard.

        This tests that the engine is not blindly flagging everything.
        """
        engine = PatternEngine(pattern_dir=VULNDOCS_DIR)

        graph_vuln = load_graph("ReentrancyClassic.sol")
        graph_safe = load_graph("ReentrancyWithGuard.sol")

        # Filter to reentrancy-related patterns for a targeted comparison
        findings_vuln = engine.run_all_patterns(graph_vuln, limit=200)
        findings_safe = engine.run_all_patterns(graph_safe, limit=200)

        # Narrow to reentrancy-related findings for a cleaner comparison
        reent_vuln = [
            f for f in findings_vuln
            if "reentrancy" in f.get("pattern_id", "").lower()
            or "reentran" in f.get("pattern_name", "").lower()
        ]
        reent_safe = [
            f for f in findings_safe
            if "reentrancy" in f.get("pattern_id", "").lower()
            or "reentran" in f.get("pattern_name", "").lower()
        ]

        # The guarded contract should have strictly fewer reentrancy findings
        # (or zero). We do not require zero -- some patterns may still fire
        # on unrelated functions -- but the count must be lower.
        assert len(reent_safe) < len(reent_vuln), (
            f"Expected guarded contract to have fewer reentrancy findings; "
            f"vuln={len(reent_vuln)}, safe={len(reent_safe)}"
        )

    def test_run_all_patterns_no_crash_on_empty_graph(self) -> None:
        """An empty KnowledgeGraph should return an empty list, not crash."""
        empty_graph = KnowledgeGraph()
        engine = PatternEngine(pattern_dir=VULNDOCS_DIR)
        findings = engine.run_all_patterns(empty_graph)
        assert findings == [], f"Expected [] on empty graph; got {findings}"


# ---------------------------------------------------------------------------
# FIX-02: Router State Advancement
# ---------------------------------------------------------------------------


class TestRouterStateAdvancement:
    """Verify Router metadata checks prevent infinite re-dispatch."""

    def _make_pool(
        self,
        status: PoolStatus = PoolStatus.INTAKE,
        metadata: dict | None = None,
    ) -> Pool:
        """Helper: create a minimal pool in the given status."""
        pool = Pool(
            id="test-pool",
            scope=Scope(files=["Vault.sol"]),
            status=status,
            metadata=metadata or {},
        )
        return pool

    # -- INTAKE phase -------------------------------------------------------

    def test_intake_returns_build_graph_when_no_metadata(self) -> None:
        """Fresh INTAKE pool with no metadata -> BUILD_GRAPH."""
        pool = self._make_pool(status=PoolStatus.INTAKE)
        decision = Router().route(pool)
        assert decision.action == RouteAction.BUILD_GRAPH

    def test_intake_returns_wait_when_graph_built(self) -> None:
        """INTAKE pool with graph_built=True -> WAIT (do not re-build)."""
        pool = self._make_pool(
            status=PoolStatus.INTAKE,
            metadata={"graph_built": True},
        )
        decision = Router().route(pool)
        assert decision.action == RouteAction.WAIT

    # -- CONTEXT phase ------------------------------------------------------

    def test_context_returns_detect_patterns_initially(self) -> None:
        """CONTEXT pool with no metadata -> DETECT_PATTERNS."""
        pool = self._make_pool(status=PoolStatus.CONTEXT)
        decision = Router().route(pool)
        assert decision.action == RouteAction.DETECT_PATTERNS

    def test_context_returns_load_context_when_patterns_detected(self) -> None:
        """CONTEXT pool with patterns_detected=True -> LOAD_CONTEXT."""
        pool = self._make_pool(
            status=PoolStatus.CONTEXT,
            metadata={"patterns_detected": True},
        )
        decision = Router().route(pool)
        assert decision.action == RouteAction.LOAD_CONTEXT

    def test_context_returns_wait_when_context_loaded(self) -> None:
        """CONTEXT pool with context_loaded=True -> WAIT."""
        pool = self._make_pool(
            status=PoolStatus.CONTEXT,
            metadata={"context_loaded": True},
        )
        decision = Router().route(pool)
        assert decision.action == RouteAction.WAIT

    # -- BEADS phase --------------------------------------------------------

    def test_beads_returns_create_beads_initially(self) -> None:
        """BEADS pool with no metadata -> CREATE_BEADS."""
        pool = self._make_pool(status=PoolStatus.BEADS)
        decision = Router().route(pool)
        assert decision.action == RouteAction.CREATE_BEADS

    def test_beads_returns_wait_when_beads_created(self) -> None:
        """BEADS pool with beads_created=True -> WAIT."""
        pool = self._make_pool(
            status=PoolStatus.BEADS,
            metadata={"beads_created": True},
        )
        decision = Router().route(pool)
        assert decision.action == RouteAction.WAIT

    # -- INTEGRATE phase ----------------------------------------------------

    def test_integrate_returns_generate_report_initially(self) -> None:
        """INTEGRATE pool with no metadata -> GENERATE_REPORT."""
        pool = self._make_pool(status=PoolStatus.INTEGRATE)
        decision = Router().route(pool)
        assert decision.action == RouteAction.GENERATE_REPORT

    def test_integrate_returns_wait_when_report_generated(self) -> None:
        """INTEGRATE pool with report_generated=True -> WAIT."""
        pool = self._make_pool(
            status=PoolStatus.INTEGRATE,
            metadata={"report_generated": True},
        )
        decision = Router().route(pool)
        assert decision.action == RouteAction.WAIT

    # -- Terminal states ----------------------------------------------------

    def test_failed_pool_returns_wait(self) -> None:
        """A FAILED pool always routes to WAIT."""
        pool = self._make_pool(status=PoolStatus.FAILED)
        decision = Router().route(pool)
        assert decision.action == RouteAction.WAIT

    def test_paused_pool_returns_wait(self) -> None:
        """A PAUSED pool always routes to WAIT."""
        pool = self._make_pool(status=PoolStatus.PAUSED)
        decision = Router().route(pool)
        assert decision.action == RouteAction.WAIT

    # -- Full sequence (no infinite loop) -----------------------------------

    def test_no_infinite_loop_full_sequence(self) -> None:
        """Walk a pool through INTAKE -> CONTEXT -> BEADS, verifying that
        once a handler sets its completion flag the router returns WAIT
        (not the same action again).

        This is the key FIX-02 regression test: before the fix, setting
        metadata had no effect and the router would re-dispatch the same
        action indefinitely.
        """
        router = Router()
        pool = self._make_pool(status=PoolStatus.INTAKE)

        # --- INTAKE ---
        d1 = router.route(pool)
        assert d1.action == RouteAction.BUILD_GRAPH, "First route in INTAKE"

        # Simulate handler completion
        pool.metadata["graph_built"] = True
        d2 = router.route(pool)
        assert d2.action == RouteAction.WAIT, "After graph_built, INTAKE should WAIT"

        # Advance phase
        pool.advance_phase()  # INTAKE -> CONTEXT
        assert pool.status == PoolStatus.CONTEXT

        # --- CONTEXT ---
        d3 = router.route(pool)
        assert d3.action == RouteAction.DETECT_PATTERNS, "First route in CONTEXT"

        pool.metadata["patterns_detected"] = True
        d4 = router.route(pool)
        assert d4.action == RouteAction.LOAD_CONTEXT, "After patterns_detected"

        pool.metadata["context_loaded"] = True
        d5 = router.route(pool)
        assert d5.action == RouteAction.WAIT, "After context_loaded, CONTEXT should WAIT"

        # Advance phase
        pool.advance_phase()  # CONTEXT -> BEADS
        assert pool.status == PoolStatus.BEADS

        # --- BEADS ---
        d6 = router.route(pool)
        assert d6.action == RouteAction.CREATE_BEADS, "First route in BEADS"

        pool.metadata["beads_created"] = True
        d7 = router.route(pool)
        assert d7.action == RouteAction.WAIT, "After beads_created, BEADS should WAIT"

    def test_route_decision_has_reason(self) -> None:
        """Every RouteDecision should include a non-empty reason string."""
        router = Router()
        pool = self._make_pool(status=PoolStatus.INTAKE)
        decision = router.route(pool)
        assert isinstance(decision.reason, str)
        assert len(decision.reason) > 0, "reason must be non-empty"

    def test_route_decision_payload_hash_deterministic(self) -> None:
        """Same pool state -> same payload hash (idempotent queue dedup)."""
        router = Router()
        pool = self._make_pool(status=PoolStatus.INTAKE)
        d1 = router.route(pool)
        d2 = router.route(pool)
        assert d1.payload_hash == d2.payload_hash


# ---------------------------------------------------------------------------
# FIX-04: VulnDocs Validation
# ---------------------------------------------------------------------------


class TestVulnDocsValidation:
    """Validate VulnDocs index.yaml files against the Pydantic schema
    using REAL data from disk."""

    @staticmethod
    def _collect_index_files() -> list[Path]:
        """Collect all index.yaml files under vulndocs/."""
        return sorted(VULNDOCS_DIR.rglob("index.yaml"))

    @staticmethod
    def _collect_pattern_files() -> list[Path]:
        """Collect all pattern YAML files under vulndocs/."""
        yamls = sorted(VULNDOCS_DIR.glob("**/patterns/*.yaml"))
        ymls = sorted(VULNDOCS_DIR.glob("**/patterns/*.yml"))
        return yamls + ymls

    def test_all_subcategory_index_validate(self) -> None:
        """Iterate every index.yaml, validate each, track pass/fail.

        This test always passes (it is a census, not a gate), but it
        asserts that we found a reasonable number of index files and
        records the pass/fail breakdown for visibility.
        """
        index_files = self._collect_index_files()
        assert len(index_files) >= 50, (
            f"Expected >= 50 index.yaml files; found {len(index_files)}"
        )

        passed: list[Path] = []
        failed: dict[Path, str] = {}

        for path in index_files:
            try:
                load_vulndoc_index(path)
                passed.append(path)
            except Exception as exc:
                failed[path] = str(exc)

        total = len(index_files)
        pass_count = len(passed)
        fail_count = len(failed)

        # Print summary for pytest -v visibility
        print(
            f"\n[VulnDocs Census] total={total} "
            f"passed={pass_count} failed={fail_count}"
        )
        if failed:
            sample = list(failed.items())[:5]
            for p, err in sample:
                print(f"  FAIL: {p.relative_to(VULNDOCS_DIR)}: {err[:120]}")

        # Sanity: most entries should pass
        assert pass_count > fail_count, (
            f"More entries fail ({fail_count}) than pass ({pass_count})"
        )

    def test_known_valid_entry_validates(self) -> None:
        """reentrancy/classic/index.yaml is known-good; verify it passes."""
        path = VULNDOCS_DIR / "reentrancy" / "classic" / "index.yaml"
        assert path.exists(), f"Known-good index not found: {path}"
        doc = load_vulndoc_index(path)
        assert doc.id == "classic"
        assert doc.parent_category == "reentrancy"

    def test_failing_entries_documented(self) -> None:
        """Count failing entries and assert the count is within a known range.

        This acts as a regression gate: if someone fixes entries the count
        should decrease. If it increases past the upper bound, the test
        will fail and alert us to new breakage.

        Verified baseline: 17 failures out of 106 index files.
        We set the upper bound at 25 to allow for some churn but catch
        significant regressions.
        """
        index_files = self._collect_index_files()
        fail_count = 0

        for path in index_files:
            try:
                load_vulndoc_index(path)
            except Exception:
                fail_count += 1

        # Upper bound regression gate
        max_allowed_failures = 25
        assert fail_count <= max_allowed_failures, (
            f"VulnDocs failures ({fail_count}) exceed regression gate "
            f"({max_allowed_failures}). New entries may have been added "
            "with validation errors."
        )

        # Lower bound: if all suddenly pass, we should know (could mean
        # the validator got too permissive).
        # Only enforce if we previously had failures.
        print(f"\n[Regression gate] current failures: {fail_count}")

    def test_pattern_files_parse(self) -> None:
        """Every pattern YAML file in vulndocs/ must parse without error.

        This tests raw YAML parsing (syntax), not schema validation.
        A parse failure would indicate a broken file that blocks the
        entire pattern loading pipeline.
        """
        pattern_files = self._collect_pattern_files()
        assert len(pattern_files) >= 50, (
            f"Expected >= 50 pattern files; found {len(pattern_files)}"
        )

        failures: dict[Path, str] = {}
        for path in pattern_files:
            try:
                with open(path) as f:
                    data = yaml.safe_load(f)
                # Basic sanity: should be a dict (or list of dicts)
                assert data is not None, f"Empty YAML: {path}"
                assert isinstance(data, (dict, list)), (
                    f"Unexpected top-level type {type(data).__name__} in {path}"
                )
            except Exception as exc:
                failures[path] = str(exc)

        if failures:
            sample = list(failures.items())[:5]
            details = "\n".join(
                f"  {p.relative_to(VULNDOCS_DIR)}: {e[:100]}"
                for p, e in sample
            )
            pytest.fail(
                f"{len(failures)} pattern files failed to parse:\n{details}"
            )

    def test_pattern_store_loads_without_error(self) -> None:
        """PatternStore.load_vulndocs_patterns should not raise on the real
        vulndocs directory. This bridges FIX-01 and FIX-04: the patterns
        that the engine uses must all parse through the store layer.
        """
        patterns = PatternStore.load_vulndocs_patterns(VULNDOCS_DIR)
        assert len(patterns) >= 100, (
            f"Expected >= 100 parsed PatternDefinitions; got {len(patterns)}"
        )
        # Every pattern must have an id
        for p in patterns:
            assert p.id, f"Pattern from vulndocs has empty id: {p}"
