"""Test suite for oracle-l2-sequencer-grace-missing pattern.

Phase 7.2 Exemplar Test Pack - 50+ test cases for L2 sequencer grace period detection.

This test suite validates the pattern detection for:
- Missing grace period after sequencer uptime check
- Proper grace period enforcement (safe cases)
- Counterfactual variants (guard inversion, ordering)
- Helper-depth variations
- L1/L2 conditional branches

Usage:
    pytest vulndocs/oracle/sequencer-uptime/tests/test_oracle_sequencer_grace_missing.py -v
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
import yaml


# =============================================================================
# Test Case Data Models
# =============================================================================


@dataclass
class TestCaseProperties:
    """Properties extracted from test case for pattern matching."""

    has_sequencer_uptime_check: bool = False
    has_grace_period_check: bool = False
    reads_oracle_price: bool = False
    is_view: bool = False
    is_pure: bool = False
    is_l2_deployment: bool = True
    grace_period_seconds: Optional[int] = None
    helper_depth: int = 0
    has_staleness_check: bool = False
    has_fallback_oracle: bool = False
    uses_library: bool = False
    uses_inheritance: bool = False
    # Additional properties from test cases
    is_liquidation: bool = False
    is_lending: bool = False
    is_swap: bool = False
    is_internal: bool = False
    has_pause_mechanism: bool = False
    has_configurable_grace: bool = False
    has_chain_conditional: bool = False
    has_conditional_sequencer: bool = False
    is_l2_adapter: bool = False


@dataclass
class TestCase:
    """A single test case from cases.yaml."""

    id: str
    name: str
    code: str
    expected_match: bool
    properties: TestCaseProperties
    description: str = ""
    severity: str = "high"
    notes: str = ""
    category: str = "vulnerable"  # vulnerable, safe, counterfactual, helper_depth


@dataclass
class PatternMatchResult:
    """Result of pattern matching against a test case."""

    case_id: str
    matched: bool
    expected_match: bool
    passed: bool
    reason: str = ""


# =============================================================================
# Test Case Loader
# =============================================================================


def load_test_cases() -> List[TestCase]:
    """Load test cases from cases.yaml."""
    cases_path = Path(__file__).parent / "cases.yaml"

    with open(cases_path, "r") as f:
        data = yaml.safe_load(f)

    cases = []

    # Load vulnerable cases
    for case_data in data.get("vulnerable_cases", []):
        props = TestCaseProperties(**case_data.get("properties", {}))
        case = TestCase(
            id=case_data["id"],
            name=case_data["name"],
            code=case_data.get("code", ""),
            expected_match=case_data.get("expected_match", True),
            properties=props,
            description=case_data.get("description", ""),
            severity=case_data.get("severity", "high"),
            notes=case_data.get("notes", ""),
            category="vulnerable",
        )
        cases.append(case)

    # Load safe cases
    for case_data in data.get("safe_cases", []):
        props = TestCaseProperties(**case_data.get("properties", {}))
        case = TestCase(
            id=case_data["id"],
            name=case_data["name"],
            code=case_data.get("code", ""),
            expected_match=case_data.get("expected_match", False),
            properties=props,
            description=case_data.get("description", ""),
            notes=case_data.get("notes", ""),
            category="safe",
        )
        cases.append(case)

    # Load counterfactual cases
    for case_data in data.get("counterfactual_cases", []):
        props = TestCaseProperties(**case_data.get("properties", {}))
        case = TestCase(
            id=case_data["id"],
            name=case_data["name"],
            code=case_data.get("code", ""),
            expected_match=case_data.get("expected_match", True),
            properties=props,
            description=case_data.get("description", ""),
            notes=case_data.get("notes", ""),
            category="counterfactual",
        )
        cases.append(case)

    # Load helper depth cases
    for case_data in data.get("helper_depth_cases", []):
        props = TestCaseProperties(**case_data.get("properties", {}))
        case = TestCase(
            id=case_data["id"],
            name=case_data["name"],
            code=case_data.get("code", ""),
            expected_match=case_data.get("expected_match", True),
            properties=props,
            description=case_data.get("description", ""),
            notes=case_data.get("notes", ""),
            category="helper_depth",
        )
        cases.append(case)

    return cases


# =============================================================================
# Pattern Matcher (Simplified for property-based testing)
# =============================================================================


def match_pattern(case: TestCase) -> PatternMatchResult:
    """Match the oracle-l2-sequencer-grace-missing pattern against a test case.

    Pattern logic:
    - MUST have sequencer uptime check (has_sequencer_uptime_check = true)
    - MUST NOT have grace period check (has_grace_period_check = false)
    - MUST read oracle price (reads_oracle_price = true)
    - MUST NOT be view or pure function

    The pattern specifically targets: sequencer check EXISTS but grace period MISSING.
    """
    props = case.properties

    # Exclude view/pure functions
    if props.is_view or props.is_pure:
        return PatternMatchResult(
            case_id=case.id,
            matched=False,
            expected_match=case.expected_match,
            passed=not case.expected_match,  # Should not match
            reason="View/pure function excluded",
        )

    # Must read oracle
    if not props.reads_oracle_price:
        return PatternMatchResult(
            case_id=case.id,
            matched=False,
            expected_match=case.expected_match,
            passed=not case.expected_match,
            reason="No oracle read detected",
        )

    # Pattern requires sequencer check to exist (distinguishes from oracle-004)
    if not props.has_sequencer_uptime_check:
        return PatternMatchResult(
            case_id=case.id,
            matched=False,
            expected_match=case.expected_match,
            passed=not case.expected_match,
            reason="No sequencer uptime check (different pattern: oracle-004)",
        )

    # Vulnerable if sequencer check exists but grace period missing
    if props.has_grace_period_check:
        # Safe: has both sequencer check and grace period
        matched = False
        reason = "Has grace period check (safe)"
    else:
        # Vulnerable: has sequencer check but no grace period
        matched = True
        reason = "Missing grace period after sequencer check (vulnerable)"

    # Check if short grace period should still be flagged
    if props.has_grace_period_check and props.grace_period_seconds is not None:
        if props.grace_period_seconds < 1800:  # Less than 30 minutes
            # Still vulnerable if grace period is too short
            matched = True
            reason = f"Grace period too short ({props.grace_period_seconds}s < 1800s)"

    return PatternMatchResult(
        case_id=case.id,
        matched=matched,
        expected_match=case.expected_match,
        passed=(matched == case.expected_match),
        reason=reason,
    )


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def all_test_cases() -> List[TestCase]:
    """Load all test cases from cases.yaml."""
    return load_test_cases()


@pytest.fixture(scope="module")
def vulnerable_cases(all_test_cases: List[TestCase]) -> List[TestCase]:
    """Get vulnerable test cases."""
    return [c for c in all_test_cases if c.category == "vulnerable"]


@pytest.fixture(scope="module")
def safe_cases(all_test_cases: List[TestCase]) -> List[TestCase]:
    """Get safe test cases."""
    return [c for c in all_test_cases if c.category == "safe"]


@pytest.fixture(scope="module")
def counterfactual_cases(all_test_cases: List[TestCase]) -> List[TestCase]:
    """Get counterfactual test cases."""
    return [c for c in all_test_cases if c.category == "counterfactual"]


@pytest.fixture(scope="module")
def helper_depth_cases(all_test_cases: List[TestCase]) -> List[TestCase]:
    """Get helper depth test cases."""
    return [c for c in all_test_cases if c.category == "helper_depth"]


# =============================================================================
# Test Cases
# =============================================================================


class TestCasesLoaded:
    """Verify test cases are loaded correctly."""

    def test_cases_loaded(self, all_test_cases: List[TestCase]) -> None:
        """Verify test cases are loaded from YAML."""
        assert len(all_test_cases) >= 50, f"Expected 50+ cases, got {len(all_test_cases)}"

    def test_case_distribution(self, all_test_cases: List[TestCase]) -> None:
        """Verify case distribution across categories."""
        vulnerable = sum(1 for c in all_test_cases if c.category == "vulnerable")
        safe = sum(1 for c in all_test_cases if c.category == "safe")
        counterfactual = sum(1 for c in all_test_cases if c.category == "counterfactual")
        helper_depth = sum(1 for c in all_test_cases if c.category == "helper_depth")

        assert vulnerable >= 20, f"Expected 20+ vulnerable cases, got {vulnerable}"
        assert safe >= 10, f"Expected 10+ safe cases, got {safe}"
        assert counterfactual >= 5, f"Expected 5+ counterfactual cases, got {counterfactual}"
        assert helper_depth >= 3, f"Expected 3+ helper depth cases, got {helper_depth}"


class TestVulnerableCases:
    """Test vulnerable cases (should match pattern)."""

    @pytest.mark.parametrize(
        "case_id",
        [
            "vuln-001",
            "vuln-002",
            "vuln-003",
            "vuln-004",
            "vuln-005",
            "vuln-006",
            "vuln-007",
            "vuln-008",
            "vuln-009",
            "vuln-010",
            "vuln-011",
            "vuln-012",
            "vuln-013",
            "vuln-014",
            "vuln-015",
            "vuln-016",
            "vuln-017",
            "vuln-018",
            "vuln-019",
            "vuln-020",
            "vuln-021",
            "vuln-022",
            "vuln-023",
            "vuln-024",
            "vuln-025",
        ],
    )
    def test_vulnerable_case(
        self, case_id: str, vulnerable_cases: List[TestCase]
    ) -> None:
        """Test individual vulnerable case."""
        case = next((c for c in vulnerable_cases if c.id == case_id), None)
        if case is None:
            pytest.skip(f"Case {case_id} not found")

        result = match_pattern(case)
        assert result.passed, (
            f"Case {case_id} ({case.name}) failed: "
            f"expected_match={result.expected_match}, matched={result.matched}, "
            f"reason={result.reason}"
        )


class TestSafeCases:
    """Test safe cases (should NOT match pattern)."""

    @pytest.mark.parametrize(
        "case_id",
        [
            "safe-001",
            "safe-002",
            "safe-003",
            "safe-004",
            "safe-005",
            "safe-006",
            "safe-007",
            "safe-008",
            "safe-009",
            "safe-010",
            "safe-011",
            "safe-012",
            "safe-013",
            "safe-014",
            "safe-015",
        ],
    )
    def test_safe_case(self, case_id: str, safe_cases: List[TestCase]) -> None:
        """Test individual safe case."""
        case = next((c for c in safe_cases if c.id == case_id), None)
        if case is None:
            pytest.skip(f"Case {case_id} not found")

        result = match_pattern(case)
        assert result.passed, (
            f"Case {case_id} ({case.name}) failed: "
            f"expected_match={result.expected_match}, matched={result.matched}, "
            f"reason={result.reason}"
        )


class TestCounterfactualCases:
    """Test counterfactual cases (mutations of safe/vulnerable patterns)."""

    @pytest.mark.parametrize(
        "case_id",
        [
            "cf-001",
            "cf-002",
            "cf-003",
            "cf-004",
            "cf-005",
            "cf-006",
            "cf-007",
            "cf-008",
            "cf-009",
            "cf-010",
        ],
    )
    def test_counterfactual_case(
        self, case_id: str, counterfactual_cases: List[TestCase]
    ) -> None:
        """Test individual counterfactual case."""
        case = next((c for c in counterfactual_cases if c.id == case_id), None)
        if case is None:
            pytest.skip(f"Case {case_id} not found")

        result = match_pattern(case)
        assert result.passed, (
            f"Case {case_id} ({case.name}) failed: "
            f"expected_match={result.expected_match}, matched={result.matched}, "
            f"reason={result.reason}"
        )


class TestHelperDepthCases:
    """Test helper depth cases (delegation patterns)."""

    @pytest.mark.parametrize(
        "case_id",
        [
            "helper-001",
            "helper-002",
            "helper-003",
            "helper-004",
            "helper-005",
        ],
    )
    def test_helper_depth_case(
        self, case_id: str, helper_depth_cases: List[TestCase]
    ) -> None:
        """Test individual helper depth case."""
        case = next((c for c in helper_depth_cases if c.id == case_id), None)
        if case is None:
            pytest.skip(f"Case {case_id} not found")

        result = match_pattern(case)
        assert result.passed, (
            f"Case {case_id} ({case.name}) failed: "
            f"expected_match={result.expected_match}, matched={result.matched}, "
            f"reason={result.reason}"
        )


class TestPatternMetrics:
    """Test pattern detection metrics."""

    def test_precision_baseline(self, all_test_cases: List[TestCase]) -> None:
        """Verify precision meets baseline target (>=0.80)."""
        results = [match_pattern(c) for c in all_test_cases]

        # True positives: correctly identified vulnerable
        true_positives = sum(
            1 for r in results if r.matched and r.expected_match
        )
        # False positives: incorrectly flagged as vulnerable
        false_positives = sum(
            1 for r in results if r.matched and not r.expected_match
        )

        if true_positives + false_positives > 0:
            precision = true_positives / (true_positives + false_positives)
        else:
            precision = 0.0

        assert precision >= 0.80, f"Precision {precision:.2f} < 0.80 baseline"

    def test_recall_baseline(self, all_test_cases: List[TestCase]) -> None:
        """Verify recall meets baseline target (>=0.75)."""
        results = [match_pattern(c) for c in all_test_cases]

        # True positives: correctly identified vulnerable
        true_positives = sum(
            1 for r in results if r.matched and r.expected_match
        )
        # False negatives: missed vulnerabilities
        false_negatives = sum(
            1 for r in results if not r.matched and r.expected_match
        )

        if true_positives + false_negatives > 0:
            recall = true_positives / (true_positives + false_negatives)
        else:
            recall = 0.0

        assert recall >= 0.75, f"Recall {recall:.2f} < 0.75 baseline"

    def test_overall_accuracy(self, all_test_cases: List[TestCase]) -> None:
        """Verify overall accuracy (passed tests / total tests)."""
        results = [match_pattern(c) for c in all_test_cases]
        passed = sum(1 for r in results if r.passed)
        total = len(results)

        accuracy = passed / total if total > 0 else 0.0

        assert accuracy >= 0.85, f"Accuracy {accuracy:.2f} < 0.85 baseline"


class TestCriticalOperations:
    """Test critical operation cases specifically."""

    def test_liquidation_detected(self, vulnerable_cases: List[TestCase]) -> None:
        """Verify liquidation without grace period is detected."""
        case = next((c for c in vulnerable_cases if c.id == "vuln-016"), None)
        if case is None:
            pytest.skip("Case vuln-016 not found")

        result = match_pattern(case)
        assert result.matched, "Liquidation without grace period should be detected"

    def test_borrow_detected(self, vulnerable_cases: List[TestCase]) -> None:
        """Verify borrow without grace period is detected."""
        case = next((c for c in vulnerable_cases if c.id == "vuln-017"), None)
        if case is None:
            pytest.skip("Case vuln-017 not found")

        result = match_pattern(case)
        assert result.matched, "Borrow without grace period should be detected"


class TestL1L2Conditional:
    """Test L1/L2 conditional cases."""

    def test_l1_deployment_not_flagged(self, safe_cases: List[TestCase]) -> None:
        """Verify L1 deployment is not flagged."""
        case = next((c for c in safe_cases if c.id == "safe-009"), None)
        if case is None:
            pytest.skip("Case safe-009 not found")

        result = match_pattern(case)
        assert not result.matched, "L1 deployment should not be flagged"

    def test_conditional_l2_check_safe(self, safe_cases: List[TestCase]) -> None:
        """Verify conditional L2 check with grace is safe."""
        case = next((c for c in safe_cases if c.id == "safe-010"), None)
        if case is None:
            pytest.skip("Case safe-010 not found")

        result = match_pattern(case)
        assert not result.matched, "Conditional L2 check with grace should be safe"


class TestViewPureFunctions:
    """Test view/pure function exclusion."""

    def test_view_function_not_flagged(self, safe_cases: List[TestCase]) -> None:
        """Verify view functions are not flagged."""
        case = next((c for c in safe_cases if c.id == "safe-013"), None)
        if case is None:
            pytest.skip("Case safe-013 not found")

        result = match_pattern(case)
        assert not result.matched, "View function should not be flagged"

    def test_pure_function_not_flagged(self, safe_cases: List[TestCase]) -> None:
        """Verify pure functions are not flagged."""
        case = next((c for c in safe_cases if c.id == "safe-014"), None)
        if case is None:
            pytest.skip("Case safe-014 not found")

        result = match_pattern(case)
        assert not result.matched, "Pure function should not be flagged"


# =============================================================================
# Summary Report
# =============================================================================


def generate_summary_report(cases: List[TestCase]) -> Dict[str, Any]:
    """Generate a summary report of pattern matching results."""
    results = [match_pattern(c) for c in cases]

    # Calculate metrics
    true_positives = sum(1 for r in results if r.matched and r.expected_match)
    false_positives = sum(1 for r in results if r.matched and not r.expected_match)
    true_negatives = sum(1 for r in results if not r.matched and not r.expected_match)
    false_negatives = sum(1 for r in results if not r.matched and r.expected_match)

    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives) > 0
        else 0.0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives) > 0
        else 0.0
    )
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    # Categorize results
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed

    return {
        "total_cases": len(cases),
        "passed": passed,
        "failed": failed,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "true_negatives": true_negatives,
        "false_negatives": false_negatives,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "failed_cases": [
            {"id": r.case_id, "expected": r.expected_match, "matched": r.matched, "reason": r.reason}
            for r in results
            if not r.passed
        ],
    }


if __name__ == "__main__":
    # Run as script to generate summary report
    cases = load_test_cases()
    report = generate_summary_report(cases)

    print("=" * 60)
    print("oracle-l2-sequencer-grace-missing Pattern Test Report")
    print("=" * 60)
    print(f"Total Cases: {report['total_cases']}")
    print(f"Passed: {report['passed']}")
    print(f"Failed: {report['failed']}")
    print()
    print("Confusion Matrix:")
    print(f"  True Positives:  {report['true_positives']}")
    print(f"  False Positives: {report['false_positives']}")
    print(f"  True Negatives:  {report['true_negatives']}")
    print(f"  False Negatives: {report['false_negatives']}")
    print()
    print("Metrics:")
    print(f"  Precision: {report['precision']:.2%}")
    print(f"  Recall:    {report['recall']:.2%}")
    print(f"  F1 Score:  {report['f1_score']:.2%}")

    if report["failed_cases"]:
        print()
        print("Failed Cases:")
        for fc in report["failed_cases"]:
            print(f"  - {fc['id']}: expected={fc['expected']}, matched={fc['matched']}")
            print(f"    Reason: {fc['reason']}")
