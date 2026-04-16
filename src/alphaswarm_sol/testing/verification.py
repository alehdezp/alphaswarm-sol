"""
Test Summary and Verification Loop (Tasks 4.10-4.11)

Provides verification workflow for closing the loop on findings:
1. Generate test scaffolds
2. Track compilation/execution
3. Update finding verdicts
4. Produce summary reports

Philosophy:
- Close the verification loop from finding -> test -> verdict
- Track metrics to validate tier success rates
- Provide actionable summaries
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import json

from alphaswarm_sol.enterprise.reports import Finding, Verdict, TestResult
from alphaswarm_sol.testing.generator import TestScaffold, generate_tier1_scaffold, generate_tier2_scaffold
from alphaswarm_sol.testing.detection import ProjectConfig
from alphaswarm_sol.testing.tiers import TestTier, TIER_DEFINITIONS
from alphaswarm_sol.testing.quality import (
    QualityTracker,
    QualityMetrics,
    CompilationStatus,
    ExecutionStatus,
    generate_with_fallback,
)


@dataclass
class VerificationSummary:
    """
    Summary of verification workflow for a set of findings.

    Provides overview of scaffolds generated, tests run, and verdicts reached.
    """
    total_findings: int = 0
    scaffolds_generated: int = 0
    scaffolds_compiled: int = 0
    tests_executed: int = 0

    # Verdict counts
    verdicts_confirmed: int = 0
    verdicts_false_positive: int = 0
    verdicts_inconclusive: int = 0
    verdicts_pending: int = 0

    # Quality metrics
    compile_rate: float = 0.0
    execution_rate: float = 0.0

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def verification_rate(self) -> float:
        """Percentage of findings that have been verified."""
        if self.total_findings == 0:
            return 0.0
        verified = self.verdicts_confirmed + self.verdicts_false_positive + self.verdicts_inconclusive
        return verified / self.total_findings

    @property
    def duration_seconds(self) -> Optional[float]:
        """Duration of verification in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_findings": self.total_findings,
            "scaffolds_generated": self.scaffolds_generated,
            "scaffolds_compiled": self.scaffolds_compiled,
            "tests_executed": self.tests_executed,
            "verdicts": {
                "confirmed": self.verdicts_confirmed,
                "false_positive": self.verdicts_false_positive,
                "inconclusive": self.verdicts_inconclusive,
                "pending": self.verdicts_pending,
            },
            "rates": {
                "compile_rate": f"{self.compile_rate:.1%}",
                "execution_rate": f"{self.execution_rate:.1%}",
                "verification_rate": f"{self.verification_rate:.1%}",
            },
            "timing": {
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "completed_at": self.completed_at.isoformat() if self.completed_at else None,
                "duration_seconds": self.duration_seconds,
            },
        }


@dataclass
class VerificationResult:
    """
    Result of verifying a single finding.

    Links finding -> scaffold -> test result -> verdict.
    """
    finding: Finding
    scaffold: Optional[TestScaffold] = None
    compiled: bool = False
    compilation_error: Optional[str] = None
    executed: bool = False
    execution_error: Optional[str] = None
    verdict: Verdict = Verdict.PENDING
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "finding_id": self.finding.id,
            "finding_title": self.finding.title,
            "finding_severity": self.finding.severity.value,
            "scaffold_filename": self.scaffold.filename if self.scaffold else None,
            "scaffold_tier": self.scaffold.tier if self.scaffold else None,
            "compiled": self.compiled,
            "compilation_error": self.compilation_error,
            "executed": self.executed,
            "execution_error": self.execution_error,
            "verdict": self.verdict.value,
            "notes": self.notes,
        }


class VerificationLoop:
    """
    Manages the verification workflow for findings.

    Coordinates scaffold generation, quality tracking, and verdict assignment.
    """

    def __init__(
        self,
        project_config: Optional[ProjectConfig] = None,
        storage_dir: Optional[Path] = None,
    ):
        """
        Initialize verification loop.

        Args:
            project_config: Project configuration for scaffold generation
            storage_dir: Directory for storing scaffolds and tracking data
        """
        self.project_config = project_config
        self.storage_dir = storage_dir

        # Initialize quality tracker
        tracker_path = storage_dir / "quality.json" if storage_dir else None
        self.tracker = QualityTracker(storage_path=tracker_path)

        # Track results
        self.results: Dict[str, VerificationResult] = {}
        self.summary = VerificationSummary()

    def add_finding(self, finding: Finding) -> VerificationResult:
        """
        Add a finding to the verification loop.

        Generates a scaffold for the finding and tracks it.

        Args:
            finding: The finding to verify

        Returns:
            VerificationResult for the finding
        """
        # Start timing on first finding
        if self.summary.started_at is None:
            self.summary.started_at = datetime.now()

        self.summary.total_findings += 1

        # Generate scaffold with fallback
        scaffold = generate_with_fallback(
            finding,
            target_tier=TestTier.TIER_2_SMART,
            project_config=self.project_config,
            tracker=self.tracker,
        )

        self.summary.scaffolds_generated += 1

        # Link scaffold to finding
        finding.link_test(scaffold.filename)

        # Create result
        result = VerificationResult(
            finding=finding,
            scaffold=scaffold,
        )

        self.results[finding.id] = result

        # Write scaffold to file if storage dir provided
        if self.storage_dir:
            self._write_scaffold(scaffold)

        return result

    def add_findings(self, findings: List[Finding]) -> List[VerificationResult]:
        """
        Add multiple findings to the verification loop.

        Args:
            findings: List of findings

        Returns:
            List of VerificationResults
        """
        return [self.add_finding(f) for f in findings]

    def record_compilation(
        self,
        finding_id: str,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """
        Record compilation result for a finding's scaffold.

        Args:
            finding_id: ID of the finding
            success: Whether compilation succeeded
            error: Error message if failed
        """
        result = self.results.get(finding_id)
        if not result or not result.scaffold:
            return

        result.compiled = success
        result.compilation_error = error

        # Update tracker
        self.tracker.record_compilation(result.scaffold.filename, success, error)

        # Update summary
        if success:
            self.summary.scaffolds_compiled += 1

        # Update compile rate
        metrics = self.tracker.get_metrics()
        self.summary.compile_rate = metrics.compile_rate

        # Update finding
        if success:
            result.finding.record_test_result(TestResult.NOT_RUN)
        else:
            result.finding.record_test_result(TestResult.ERROR)

    def record_execution(
        self,
        finding_id: str,
        passed: bool,
        error: Optional[str] = None,
    ) -> None:
        """
        Record test execution result for a finding's scaffold.

        Args:
            finding_id: ID of the finding
            passed: Whether test passed (vulnerability confirmed)
            error: Error message if execution failed
        """
        result = self.results.get(finding_id)
        if not result or not result.scaffold:
            return

        result.executed = True
        result.execution_error = error

        # Determine status
        if error:
            status = ExecutionStatus.ERROR
        elif passed:
            status = ExecutionStatus.PASSED
        else:
            status = ExecutionStatus.FAILED

        # Update tracker
        self.tracker.record_execution(result.scaffold.filename, status, error)

        # Update summary
        if status in (ExecutionStatus.PASSED, ExecutionStatus.FAILED):
            self.summary.tests_executed += 1

        # Update execution rate
        metrics = self.tracker.get_metrics()
        self.summary.execution_rate = metrics.execution_rate

        # Update finding test result
        if passed:
            result.finding.record_test_result(TestResult.PASSED)
        elif error:
            result.finding.record_test_result(TestResult.ERROR)
        else:
            result.finding.record_test_result(TestResult.FAILED)

    def set_verdict(
        self,
        finding_id: str,
        verdict: Verdict,
        evidence: Optional[List[str]] = None,
        notes: str = "",
    ) -> None:
        """
        Set the verdict for a finding.

        Args:
            finding_id: ID of the finding
            verdict: The verdict
            evidence: Supporting evidence
            notes: Auditor notes
        """
        result = self.results.get(finding_id)
        if not result:
            return

        result.verdict = verdict
        result.notes = notes

        # Update finding
        result.finding.set_verdict(verdict, evidence, notes)

        # Update summary counts
        self._update_verdict_counts()

    def _update_verdict_counts(self) -> None:
        """Update summary verdict counts."""
        self.summary.verdicts_confirmed = 0
        self.summary.verdicts_false_positive = 0
        self.summary.verdicts_inconclusive = 0
        self.summary.verdicts_pending = 0

        for result in self.results.values():
            if result.verdict == Verdict.CONFIRMED:
                self.summary.verdicts_confirmed += 1
            elif result.verdict == Verdict.FALSE_POSITIVE:
                self.summary.verdicts_false_positive += 1
            elif result.verdict == Verdict.INCONCLUSIVE:
                self.summary.verdicts_inconclusive += 1
            else:
                self.summary.verdicts_pending += 1

    def complete(self) -> VerificationSummary:
        """
        Mark verification loop as complete.

        Returns:
            Final summary
        """
        self.summary.completed_at = datetime.now()
        return self.summary

    def get_result(self, finding_id: str) -> Optional[VerificationResult]:
        """Get verification result for a finding."""
        return self.results.get(finding_id)

    def get_summary(self) -> VerificationSummary:
        """Get current verification summary."""
        return self.summary

    def get_pending_findings(self) -> List[VerificationResult]:
        """Get findings with pending verdicts."""
        return [r for r in self.results.values() if r.verdict == Verdict.PENDING]

    def get_confirmed_findings(self) -> List[VerificationResult]:
        """Get findings confirmed as true positives."""
        return [r for r in self.results.values() if r.verdict == Verdict.CONFIRMED]

    def _write_scaffold(self, scaffold: TestScaffold) -> Path:
        """Write scaffold to file."""
        if not self.storage_dir:
            raise ValueError("No storage directory configured")

        scaffold_dir = self.storage_dir / "scaffolds"
        scaffold_dir.mkdir(parents=True, exist_ok=True)

        output_path = scaffold_dir / scaffold.filename
        output_path.write_text(scaffold.content)
        return output_path

    def export_results(self, output_path: Path) -> None:
        """
        Export verification results to JSON file.

        Args:
            output_path: Path to output file
        """
        data = {
            "summary": self.summary.to_dict(),
            "results": [r.to_dict() for r in self.results.values()],
            "quality_metrics": self.tracker.get_summary(),
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(data, indent=2))


def format_verification_summary(summary: VerificationSummary) -> str:
    """
    Format verification summary as human-readable text.

    Args:
        summary: The summary to format

    Returns:
        Multi-line string summary
    """
    lines = [
        "=" * 60,
        "VERIFICATION SUMMARY",
        "=" * 60,
        "",
        f"Total Findings:      {summary.total_findings}",
        f"Scaffolds Generated: {summary.scaffolds_generated}",
        f"Scaffolds Compiled:  {summary.scaffolds_compiled} ({summary.compile_rate:.1%})",
        f"Tests Executed:      {summary.tests_executed} ({summary.execution_rate:.1%})",
        "",
        "VERDICTS:",
        f"  Confirmed:         {summary.verdicts_confirmed}",
        f"  False Positive:    {summary.verdicts_false_positive}",
        f"  Inconclusive:      {summary.verdicts_inconclusive}",
        f"  Pending:           {summary.verdicts_pending}",
        "",
        f"Verification Rate:   {summary.verification_rate:.1%}",
    ]

    if summary.duration_seconds is not None:
        lines.append(f"Duration:            {summary.duration_seconds:.1f}s")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


def format_finding_result(result: VerificationResult) -> str:
    """
    Format a single finding's verification result.

    Args:
        result: The verification result

    Returns:
        Formatted string
    """
    lines = [
        f"Finding: {result.finding.id} - {result.finding.title}",
        f"  Severity: {result.finding.severity.value}",
    ]

    if result.scaffold:
        lines.append(f"  Scaffold: {result.scaffold.filename} (Tier {result.scaffold.tier})")
        lines.append(f"  Compiled: {'Yes' if result.compiled else 'No'}")
        if result.compilation_error:
            lines.append(f"    Error: {result.compilation_error[:50]}...")
        lines.append(f"  Executed: {'Yes' if result.executed else 'No'}")

    lines.append(f"  Verdict: {result.verdict.value}")
    if result.notes:
        lines.append(f"  Notes: {result.notes}")

    return "\n".join(lines)
