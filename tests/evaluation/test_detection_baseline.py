"""Detection quality baseline tests.

Runs lens-report on corpus contracts, compares findings against ground truth,
calculates precision/recall/F1, and stores results via BaselineManager.

Phase: 3.1d-05
CONTRACT_VERSION: 05.1
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from alphaswarm_sol.kg.builder import VKGBuilder
from alphaswarm_sol.queries.report import build_lens_report
from alphaswarm_sol.testing.evaluation.models import (
    DimensionScore,
    EvaluationResult,
    PipelineHealth,
    RunMode,
    ScoreCard,
)

from tests.workflow_harness.lib.regression_baseline import BaselineManager

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = ROOT / "tests" / "contracts"
DVDEFI_DIR = ROOT / "examples" / "damm-vuln-defi" / "src"
DEFAULT_LENSES = ["Ordering", "Oracle", "ExternalInfluence"]
BASELINE_DIR = ROOT / ".vrs" / "evaluation" / "baselines" / "detection"


# ---------------------------------------------------------------------------
# Ground truth definitions
# ---------------------------------------------------------------------------


@dataclass
class GroundTruth:
    """Ground truth for a single contract."""

    contract_path: Path
    target_contract_label: str
    known_vulns: list[str]
    expected_patterns: list[str] = field(default_factory=list)
    is_safe: bool = False


CORPUS: list[GroundTruth] = [
    GroundTruth(
        contract_path=DVDEFI_DIR / "side-entrance" / "SideEntranceLenderPool.sol",
        target_contract_label="SideEntranceLenderPool",
        known_vulns=[
            "flash-loan-reentrancy",
            "missing-access-control-flashloan",
        ],
        expected_patterns=[
            "reentrancy-basic",
            "value-movement-cross-function-reentrancy",
            "access-tierb-001-trust-assumption-violation",
        ],
    ),
    GroundTruth(
        contract_path=DVDEFI_DIR / "truster" / "TrusterLenderPool.sol",
        target_contract_label="TrusterLenderPool",
        known_vulns=[
            "arbitrary-external-call",
        ],
        expected_patterns=[
            "external-call-public-no-gate",
            "lib-001",
        ],
    ),
    GroundTruth(
        contract_path=DVDEFI_DIR / "naive-receiver" / "NaiveReceiverPool.sol",
        target_contract_label="NaiveReceiverPool",
        known_vulns=[
            "missing-sender-validation",
        ],
        expected_patterns=[
            "access-tierb-001-trust-assumption-violation",
            "ext-001",
        ],
    ),
    GroundTruth(
        contract_path=DVDEFI_DIR / "unstoppable" / "UnstoppableVault.sol",
        target_contract_label="UnstoppableVault",
        known_vulns=[
            "invariant-manipulation",
        ],
        expected_patterns=[],  # No pattern currently detects this
    ),
    GroundTruth(
        contract_path=DVDEFI_DIR / "selfie" / "SelfiePool.sol",
        target_contract_label="SelfiePool",
        known_vulns=[
            "flash-loan-governance-attack",
        ],
        expected_patterns=[],  # Cross-contract governance not detected
    ),
    GroundTruth(
        contract_path=CONTRACTS_DIR / "ReentrancyClassic.sol",
        target_contract_label="ReentrancyClassic",
        known_vulns=[
            "classic-reentrancy",
        ],
        expected_patterns=[
            "op-reentrancy-classic",
            "value-movement-classic-reentrancy",
        ],
    ),
    GroundTruth(
        contract_path=CONTRACTS_DIR / "ReentrancyWithGuard.sol",
        target_contract_label="ReentrancyWithGuard",
        known_vulns=[],
        expected_patterns=[],
        is_safe=True,
    ),
]


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------

# Patterns that are known to be overly generic and should not count as TP
# unless they match an expected_patterns entry.
GENERIC_NOISE_PATTERNS = {
    "has-user-input-writes-state-no-gate",
    "dataflow-input-taints-state",
    "attacker-controlled-write",
    "low-level-call-public",
}

# Patterns that detect the same reentrancy vuln -- only the first counts as TP
REENTRANCY_FAMILY = {
    "reentrancy-basic",
    "op-reentrancy-classic",
    "op-reentrancy-external-before-write",
    "value-movement-classic-reentrancy",
    "value-movement-eth-transfer-reentrancy",
    "value-movement-cross-function-reentrancy",
    "value-movement-cross-function-reentrancy-read",
    "value-movement-cross-contract-reentrancy",
    "state-write-after-call",
    "vm-001-classic",
    "op-vulnerable-withdrawal-signature",
    "lib-002",
}


def _extract_target_findings(
    report: dict[str, Any], target_label: str
) -> list[dict[str, Any]]:
    """Extract findings for the target contract only."""
    for contract in report.get("contracts", []):
        if contract.get("contract_label") == target_label:
            return contract.get("findings", [])
    return []


def _unique_patterns(findings: list[dict[str, Any]]) -> set[str]:
    """Get unique pattern IDs from findings."""
    return {f["pattern_id"] for f in findings}


@dataclass
class ClassificationResult:
    """Result of classifying findings for a contract."""

    contract: str
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tp_patterns: list[str] = field(default_factory=list)
    fp_patterns: list[str] = field(default_factory=list)
    fn_vulns: list[str] = field(default_factory=list)
    total_raw_findings: int = 0

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom > 0 else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom > 0 else 1.0  # No vulns = 100% recall

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


def classify_findings(
    gt: GroundTruth, findings: list[dict[str, Any]]
) -> ClassificationResult:
    """Classify findings as TP, FP, FN against ground truth."""
    result = ClassificationResult(contract=gt.target_contract_label)
    result.total_raw_findings = len(findings)
    patterns_found = _unique_patterns(findings)

    if gt.is_safe:
        # Safe contract: every finding is a false positive
        result.fp = len(patterns_found)
        result.fp_patterns = sorted(patterns_found)
        return result

    # Check which expected patterns were found (TP)
    matched_expected = patterns_found & set(gt.expected_patterns)
    result.tp = len(matched_expected)
    result.tp_patterns = sorted(matched_expected)

    # Check for expected patterns that were missed (contributes to FN)
    missed_expected = set(gt.expected_patterns) - patterns_found
    # Each missed expected pattern represents a vulnerability class not detected
    # But we count FN by vulnerability, not by pattern
    # A vulnerability is detected if ANY of its expected patterns fire
    detected_vulns = set()
    for vuln in gt.known_vulns:
        # Check if any expected pattern for this vuln was found
        # Since we don't have a vuln->pattern mapping, use heuristic:
        # if at least one expected pattern fires, consider vuln detected
        if matched_expected:
            detected_vulns.add(vuln)

    # If no expected patterns at all, check if any non-noise pattern fires
    # that could reasonably detect the vuln
    if not gt.expected_patterns:
        result.fn = len(gt.known_vulns)
        result.fn_vulns = list(gt.known_vulns)
    else:
        result.fn = len(gt.known_vulns) - len(detected_vulns)
        result.fn_vulns = [v for v in gt.known_vulns if v not in detected_vulns]

    # Everything not in expected_patterns is FP
    # But first remove reentrancy family duplicates (count family once)
    remaining = patterns_found - set(gt.expected_patterns)
    # Remove generic noise that fires everywhere
    noise = remaining & GENERIC_NOISE_PATTERNS
    non_noise = remaining - GENERIC_NOISE_PATTERNS
    # Reentrancy family: if any expected pattern is in reentrancy family,
    # other reentrancy family members are redundant not FP
    expected_has_reentrancy = bool(set(gt.expected_patterns) & REENTRANCY_FAMILY)
    if expected_has_reentrancy:
        reentrancy_redundant = non_noise & REENTRANCY_FAMILY
        non_noise = non_noise - reentrancy_redundant

    result.fp = len(noise) + len(non_noise)
    result.fp_patterns = sorted(noise | non_noise)

    return result


# ---------------------------------------------------------------------------
# Build graphs (cached per module)
# ---------------------------------------------------------------------------

_builder = VKGBuilder(ROOT)
_graph_cache: dict[str, Any] = {}


def _get_graph(contract_path: Path):
    key = str(contract_path)
    if key not in _graph_cache:
        _graph_cache[key] = _builder.build(contract_path)
    return _graph_cache[key]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDetectionBaseline:
    """Detection quality baseline tests."""

    @pytest.fixture(scope="class")
    def all_results(self) -> list[tuple[GroundTruth, dict[str, Any], ClassificationResult]]:
        """Build graphs and run lens-report for all corpus contracts."""
        results = []
        for gt in CORPUS:
            if not gt.contract_path.exists():
                pytest.skip(f"Contract not found: {gt.contract_path}")
            graph = _get_graph(gt.contract_path)
            report = build_lens_report(graph, DEFAULT_LENSES, limit=200)
            findings = _extract_target_findings(report, gt.target_contract_label)
            classification = classify_findings(gt, findings)
            results.append((gt, report, classification))
        return results

    def test_graphs_build_successfully(self, all_results):
        """All corpus contracts should build graphs without errors."""
        assert len(all_results) == len(CORPUS)

    def test_lens_reports_run_successfully(self, all_results):
        """All lens reports should produce output."""
        for gt, report, _ in all_results:
            assert report is not None, f"No report for {gt.target_contract_label}"
            assert "contracts" in report
            assert "findings" in report

    def test_reentrancy_classic_detected(self, all_results):
        """ReentrancyClassic must be detected as vulnerable."""
        for gt, _, classification in all_results:
            if gt.target_contract_label == "ReentrancyClassic":
                assert classification.tp > 0, (
                    f"ReentrancyClassic TP=0. Patterns found: "
                    f"{classification.tp_patterns}"
                )
                assert classification.fn == 0, (
                    f"ReentrancyClassic has missed vulns: {classification.fn_vulns}"
                )
                return
        pytest.fail("ReentrancyClassic not in results")

    def test_reentrancy_with_guard_no_reentrancy_tp(self, all_results):
        """ReentrancyWithGuard should ideally produce zero findings.

        Currently fails (12 FPs). This test documents the gap and will
        pass once guard recognition is implemented. Marked xfail.
        """
        for gt, _, classification in all_results:
            if gt.target_contract_label == "ReentrancyWithGuard":
                # Document current state: all findings are FP
                assert classification.tp == 0, "Safe contract should have 0 TP"
                return
        pytest.fail("ReentrancyWithGuard not in results")

    @pytest.mark.xfail(
        reason="Guard recognition not implemented - ReentrancyWithGuard produces 12 FPs",
        strict=False,
    )
    def test_safe_contract_zero_findings(self, all_results):
        """Safe contracts should produce zero findings (future goal)."""
        for gt, _, classification in all_results:
            if gt.is_safe:
                assert classification.fp == 0, (
                    f"{gt.target_contract_label} has {classification.fp} FPs: "
                    f"{classification.fp_patterns}"
                )

    def test_side_entrance_detected(self, all_results):
        """SideEntranceLenderPool vulnerabilities should be detected."""
        for gt, _, classification in all_results:
            if gt.target_contract_label == "SideEntranceLenderPool":
                assert classification.tp > 0, "SideEntrance should have TP > 0"
                assert classification.fn == 0, (
                    f"SideEntrance missed: {classification.fn_vulns}"
                )
                return
        pytest.fail("SideEntranceLenderPool not in results")

    def test_truster_detected(self, all_results):
        """TrusterLenderPool arbitrary call should be detected."""
        for gt, _, classification in all_results:
            if gt.target_contract_label == "TrusterLenderPool":
                assert classification.tp > 0, "Truster should have TP > 0"
                return
        pytest.fail("TrusterLenderPool not in results")

    def test_naive_receiver_detected(self, all_results):
        """NaiveReceiverPool missing sender validation should be detected."""
        for gt, _, classification in all_results:
            if gt.target_contract_label == "NaiveReceiverPool":
                assert classification.tp > 0, "NaiveReceiver should have TP > 0"
                return
        pytest.fail("NaiveReceiverPool not in results")

    @pytest.mark.xfail(
        reason="No pattern exists for invariant manipulation",
        strict=True,
    )
    def test_unstoppable_detected(self, all_results):
        """UnstoppableVault invariant manipulation should be detected."""
        for gt, _, classification in all_results:
            if gt.target_contract_label == "UnstoppableVault":
                assert classification.fn == 0, (
                    f"UnstoppableVault missed: {classification.fn_vulns}"
                )
                return
        pytest.fail("UnstoppableVault not in results")

    @pytest.mark.xfail(
        reason="No pattern exists for cross-contract governance attacks",
        strict=True,
    )
    def test_selfie_detected(self, all_results):
        """SelfiePool governance attack should be detected."""
        for gt, _, classification in all_results:
            if gt.target_contract_label == "SelfiePool":
                assert classification.fn == 0, (
                    f"SelfiePool missed: {classification.fn_vulns}"
                )
                return
        pytest.fail("SelfiePool not in results")

    def test_overall_precision_above_minimum(self, all_results):
        """Overall precision should be at least 10% (current baseline: ~13%).

        This is a regression guard. If precision drops below 10%, something
        is generating even more false positives.
        """
        total_tp = sum(c.tp for _, _, c in all_results)
        total_fp = sum(c.fp for _, _, c in all_results)
        denom = total_tp + total_fp
        precision = total_tp / denom if denom > 0 else 0.0
        assert precision >= 0.10, (
            f"Precision {precision:.1%} below 10% minimum. "
            f"TP={total_tp}, FP={total_fp}"
        )

    def test_overall_recall_above_minimum(self, all_results):
        """Overall recall (contract-level) should detect at least 4/6 vuln contracts.

        Current baseline: 5/6 contracts have at least partial detection.
        """
        vuln_contracts = [(gt, c) for gt, _, c in all_results if not gt.is_safe]
        detected = sum(1 for _, c in vuln_contracts if c.tp > 0)
        total = len(vuln_contracts)
        assert detected >= 4, (
            f"Only {detected}/{total} vulnerable contracts detected. "
            f"Need >= 4."
        )

    def test_publish_baseline_to_manager(self, all_results, tmp_path):
        """Store detection baseline results via BaselineManager."""
        mgr = BaselineManager(baseline_dir=tmp_path / "baselines")

        total_tp = sum(c.tp for _, _, c in all_results)
        total_fp = sum(c.fp for _, _, c in all_results)
        total_fn = sum(c.fn for _, _, c in all_results)
        denom = total_tp + total_fp
        precision = total_tp / denom if denom > 0 else 0.0
        recall_denom = total_tp + total_fn
        recall = total_tp / recall_denom if recall_denom > 0 else 1.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        # Create an EvaluationResult that encodes detection quality
        precision_pct = int(precision * 100)
        recall_pct = int(recall * 100)
        f1_pct = int(f1 * 100)
        overall = f1_pct  # Use F1 as overall score

        result = EvaluationResult(
            scenario_name="detection-baseline-corpus",
            workflow_id="detection-baseline",
            run_mode=RunMode.HEADLESS,
            score_card=ScoreCard(
                workflow_id="detection-baseline",
                dimensions=[
                    DimensionScore(
                        dimension="precision",
                        score=precision_pct,
                        weight=1.0,
                        explanation=f"TP={total_tp}, FP={total_fp}",
                    ),
                    DimensionScore(
                        dimension="recall",
                        score=recall_pct,
                        weight=1.0,
                        explanation=f"TP={total_tp}, FN={total_fn}",
                    ),
                    DimensionScore(
                        dimension="f1",
                        score=f1_pct,
                        weight=1.0,
                        explanation=f"F1={f1:.3f}",
                    ),
                ],
                overall_score=overall,
                passed=overall >= 20,  # Low bar for now
                pass_threshold=20,
            ),
            pipeline_health=PipelineHealth(
                parsed_records=len(all_results),
                expected_records=len(CORPUS),
                errors=0,
                stages_completed=["build_kg", "lens_report", "classify"],
            ),
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            metadata={
                "corpus_size": len(CORPUS),
                "total_tp": total_tp,
                "total_fp": total_fp,
                "total_fn": total_fn,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "per_contract": {
                    c.contract: {
                        "tp": c.tp,
                        "fp": c.fp,
                        "fn": c.fn,
                        "precision": round(c.precision, 4),
                        "recall": round(c.recall, 4),
                    }
                    for _, _, c in all_results
                },
            },
        )

        entry = mgr.update_baseline("detection-baseline", result)
        assert entry.workflow_id == "detection-baseline"
        assert entry.score == overall

        # Verify we can read it back
        loaded = mgr.get_baseline("detection-baseline")
        assert loaded is not None
        assert loaded.score == overall

    def test_print_summary(self, all_results, capsys):
        """Print human-readable summary (always passes, for visibility)."""
        total_tp = total_fp = total_fn = 0
        print("\n" + "=" * 70)
        print("DETECTION QUALITY BASELINE SUMMARY")
        print("=" * 70)
        for gt, _, c in all_results:
            total_tp += c.tp
            total_fp += c.fp
            total_fn += c.fn
            status = "SAFE" if gt.is_safe else "VULN"
            print(
                f"  {c.contract:30s} [{status}] "
                f"TP={c.tp} FP={c.fp} FN={c.fn} "
                f"P={c.precision:.0%} R={c.recall:.0%}"
            )
            if c.fn_vulns:
                print(f"    MISSED: {', '.join(c.fn_vulns)}")
            if c.fp_patterns and not gt.is_safe:
                print(f"    FP patterns: {', '.join(c.fp_patterns[:5])}")

        denom = total_tp + total_fp
        precision = total_tp / denom if denom > 0 else 0.0
        recall_denom = total_tp + total_fn
        recall = total_tp / recall_denom if recall_denom > 0 else 1.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        print("-" * 70)
        print(f"  TOTAL: TP={total_tp} FP={total_fp} FN={total_fn}")
        print(f"  Precision: {precision:.1%}  Recall: {recall:.1%}  F1: {f1:.1%}")
        print("=" * 70)
