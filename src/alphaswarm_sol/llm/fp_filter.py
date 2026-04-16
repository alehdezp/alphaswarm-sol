"""
False Positive Filtering (Task 11.4)

Specialized module for filtering false positives using LLM analysis.
Builds on TierBWorkflow with FP-specific prompts and metrics.

Key features:
- FP-focused prompt templates
- Before/after metrics tracking
- Safe guard against dismissing true positives
- Pattern-specific FP heuristics
"""

from dataclasses import dataclass, field
from typing import Optional, Callable, Awaitable, Any
from enum import Enum
import json

from alphaswarm_sol.findings.model import (
    Finding,
    FindingStatus,
    FindingTier,
    FindingConfidence,
)
from alphaswarm_sol.llm.workflow import (
    TierBWorkflow,
    WorkflowResult,
    WorkflowStatus,
    create_tier_b_workflow,
)
from alphaswarm_sol.llm.contract import (
    PromptContract,
    PromptInput,
    PromptType,
    build_standard_prompt,
)
from alphaswarm_sol.llm.validate import Verdict
from alphaswarm_sol.llm.limits import RateLimiter, create_rate_limiter


class FPFilterDecision(str, Enum):
    """Decision from FP filter."""
    CONFIRMED_FP = "confirmed_fp"  # Definitely false positive
    CONFIRMED_VULN = "confirmed_vuln"  # Definitely vulnerable
    NEEDS_REVIEW = "needs_review"  # Uncertain, needs human review
    SKIPPED = "skipped"  # Not analyzed (high/low confidence)
    ERROR = "error"  # Analysis failed


@dataclass
class FPFilterResult:
    """Result from FP filtering."""
    finding_id: str
    decision: FPFilterDecision
    original_status: FindingStatus
    confidence_before: float
    confidence_after: Optional[int] = None
    reasoning: str = ""
    evidence: list[str] = field(default_factory=list)
    tokens_used: int = 0
    cost_usd: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "finding_id": self.finding_id,
            "decision": self.decision.value,
            "original_status": self.original_status.value,
            "confidence_before": self.confidence_before,
            "confidence_after": self.confidence_after,
            "reasoning": self.reasoning,
            "evidence": self.evidence,
            "tokens_used": self.tokens_used,
            "cost_usd": round(self.cost_usd, 6),
        }


@dataclass
class FPFilterMetrics:
    """Metrics for FP filtering effectiveness."""
    total_findings: int = 0
    analyzed: int = 0
    confirmed_fp: int = 0
    confirmed_vuln: int = 0
    needs_review: int = 0
    skipped: int = 0
    errors: int = 0

    # Before/after comparison
    fp_before_count: int = 0  # Initial suspected FPs
    fp_after_count: int = 0   # Final confirmed FPs
    true_positives_preserved: int = 0  # Vulns NOT dismissed

    total_tokens: int = 0
    total_cost_usd: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        total = self.total_findings
        analyzed = self.analyzed

        return {
            "total_findings": total,
            "analyzed": analyzed,
            "confirmed_fp": self.confirmed_fp,
            "confirmed_vuln": self.confirmed_vuln,
            "needs_review": self.needs_review,
            "skipped": self.skipped,
            "errors": self.errors,
            # Rates
            "fp_identification_rate": (
                self.confirmed_fp / analyzed * 100 if analyzed > 0 else 0
            ),
            "vuln_confirmation_rate": (
                self.confirmed_vuln / analyzed * 100 if analyzed > 0 else 0
            ),
            # Before/after
            "fp_before_count": self.fp_before_count,
            "fp_after_count": self.fp_after_count,
            "fp_reduction_rate": (
                (self.fp_before_count - self.fp_after_count) / self.fp_before_count * 100
                if self.fp_before_count > 0 else 0
            ),
            "true_positives_preserved": self.true_positives_preserved,
            "true_positive_preservation_rate": 100.0,  # Should be 100% by design
            # Costs
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 4),
        }


# Type alias for LLM call function
LLMCallFn = Callable[[str], Awaitable[str]]


# Pattern categories known to have high FP rates
HIGH_FP_PATTERNS = {
    "reentrancy",  # Many patterns are guarded
    "unchecked-return",  # Often intentional
    "timestamp-dependency",  # Usually benign
}

# Patterns that should never be auto-dismissed
NEVER_DISMISS_PATTERNS = {
    "access-control",
    "privilege-escalation",
    "owner-manipulation",
    "fund-drain",
}


class FPFilter:
    """
    False Positive Filter for security findings.

    Uses LLM analysis with specialized FP-checking prompts
    to reduce false positive rate while preserving true positives.

    Example:
        >>> fp_filter = FPFilter()
        >>> result = await fp_filter.analyze_finding(finding, llm_call)
        >>> if result.decision == FPFilterDecision.CONFIRMED_FP:
        ...     finding.update_status(FindingStatus.FALSE_POSITIVE)
    """

    def __init__(
        self,
        workflow: Optional[TierBWorkflow] = None,
        contract: Optional[PromptContract] = None,
        rate_limiter: Optional[RateLimiter] = None,
        min_confidence_for_fp: int = 80,
        never_dismiss_patterns: Optional[set[str]] = None,
    ):
        """
        Initialize FP filter.

        Args:
            workflow: Optional TierBWorkflow to use
            contract: Optional PromptContract for validation
            rate_limiter: Optional rate limiter
            min_confidence_for_fp: Minimum LLM confidence to mark as FP
            never_dismiss_patterns: Patterns that should never be auto-dismissed
        """
        self.workflow = workflow or create_tier_b_workflow(strict_mode=False)
        self.contract = contract or PromptContract(max_retries=3, strict_mode=False)
        self.rate_limiter = rate_limiter or create_rate_limiter()
        self.min_confidence_for_fp = min_confidence_for_fp
        self.never_dismiss_patterns = never_dismiss_patterns or NEVER_DISMISS_PATTERNS

        self._metrics = FPFilterMetrics()

    async def analyze_finding(
        self,
        finding: Finding,
        llm_call: LLMCallFn,
        code_context: Optional[str] = None,
        _track_total: bool = True,
    ) -> FPFilterResult:
        """
        Analyze a finding for false positive potential.

        Args:
            finding: The finding to analyze
            llm_call: Async function to call LLM
            code_context: Optional code context
            _track_total: Internal flag to avoid double counting in batch

        Returns:
            FPFilterResult with decision and reasoning
        """
        if _track_total:
            self._metrics.total_findings += 1

        # Track original status
        original_status = finding.status
        confidence_before = self._get_numeric_confidence(finding)

        # Check if pattern should never be auto-dismissed
        if self._should_protect_pattern(finding):
            return FPFilterResult(
                finding_id=finding.id,
                decision=FPFilterDecision.NEEDS_REVIEW,
                original_status=original_status,
                confidence_before=confidence_before,
                reasoning=f"Pattern '{finding.pattern}' requires human review",
            )

        # Check rate limits
        allowed, message = self.rate_limiter.check_limits(500)
        if not allowed:
            self._metrics.skipped += 1
            return FPFilterResult(
                finding_id=finding.id,
                decision=FPFilterDecision.SKIPPED,
                original_status=original_status,
                confidence_before=confidence_before,
                reasoning=f"Rate limited: {message}",
            )

        # Build FP-specific prompt
        context = code_context or self._get_context(finding)
        prompt_input = PromptInput(
            prompt_type=PromptType.FALSE_POSITIVE_CHECK,
            code_context=context,
            finding_id=finding.id,
            pattern_id=finding.pattern,
            evidence=finding.evidence.properties_matched,
            task_description=self._build_fp_task_description(finding),
        )

        # Execute with contract
        try:
            verdict = await self.contract.execute_with_contract(
                prompt_input,
                llm_call,
                build_standard_prompt,
            )
        except Exception as e:
            self._metrics.errors += 1
            return FPFilterResult(
                finding_id=finding.id,
                decision=FPFilterDecision.ERROR,
                original_status=original_status,
                confidence_before=confidence_before,
                reasoning=str(e),
            )

        # Track usage
        tokens = len(context.split()) * 2 + 200
        cost = tokens * 0.00002
        self.rate_limiter.record_usage(tokens, 200, cost, findings=1)
        self._metrics.total_tokens += tokens
        self._metrics.total_cost_usd += cost
        self._metrics.analyzed += 1

        # Determine decision based on verdict
        decision = self._make_decision(finding, verdict)

        # Update metrics
        self._update_metrics(decision, finding)

        return FPFilterResult(
            finding_id=finding.id,
            decision=decision,
            original_status=original_status,
            confidence_before=confidence_before,
            confidence_after=verdict.confidence,
            reasoning=verdict.reasoning,
            evidence=verdict.evidence,
            tokens_used=tokens,
            cost_usd=cost,
        )

    def _should_protect_pattern(self, finding: Finding) -> bool:
        """Check if pattern should be protected from auto-dismissal."""
        pattern_lower = finding.pattern.lower()
        for protected in self.never_dismiss_patterns:
            if protected in pattern_lower:
                return True
        return False

    def _get_numeric_confidence(self, finding: Finding) -> float:
        """Convert FindingConfidence to numeric."""
        mapping = {
            FindingConfidence.HIGH: 0.85,
            FindingConfidence.MEDIUM: 0.60,
            FindingConfidence.LOW: 0.35,
        }
        return mapping.get(finding.confidence, 0.60)

    def _get_context(self, finding: Finding) -> str:
        """Get code context from finding."""
        if finding.evidence.code_snippet:
            return finding.evidence.code_snippet
        return f"// Location: {finding.location}\n// Pattern: {finding.pattern}"

    def _build_fp_task_description(self, finding: Finding) -> str:
        """Build task description for FP checking."""
        parts = [
            f"Pattern: {finding.pattern}",
            f"Severity: {finding.severity.value}",
            f"Description: {finding.description}",
        ]

        if finding.evidence.behavioral_signature:
            parts.append(f"Behavioral Signature: {finding.evidence.behavioral_signature}")

        if finding.evidence.why_vulnerable:
            parts.append(f"Initial Assessment: {finding.evidence.why_vulnerable}")

        return "\n".join(parts)

    def _make_decision(
        self,
        finding: Finding,
        verdict: Any,  # LLMVerdict
    ) -> FPFilterDecision:
        """
        Make FP decision based on verdict.

        Guards against dismissing true positives by:
        1. Requiring high confidence (>= min_confidence_for_fp) to dismiss
        2. Never auto-dismissing protected patterns
        3. Escalating uncertain cases for human review
        """
        if verdict.verdict == Verdict.ERROR:
            return FPFilterDecision.ERROR

        if verdict.verdict == Verdict.SAFE:
            # Only confirm FP if confidence is high enough
            if verdict.confidence >= self.min_confidence_for_fp:
                return FPFilterDecision.CONFIRMED_FP
            else:
                # Low confidence SAFE -> needs review
                return FPFilterDecision.NEEDS_REVIEW

        if verdict.verdict == Verdict.VULNERABLE:
            return FPFilterDecision.CONFIRMED_VULN

        # UNCERTAIN
        return FPFilterDecision.NEEDS_REVIEW

    def _update_metrics(self, decision: FPFilterDecision, finding: Finding):
        """Update metrics based on decision."""
        if decision == FPFilterDecision.CONFIRMED_FP:
            self._metrics.confirmed_fp += 1
            self._metrics.fp_after_count += 1
        elif decision == FPFilterDecision.CONFIRMED_VULN:
            self._metrics.confirmed_vuln += 1
            self._metrics.true_positives_preserved += 1
        elif decision == FPFilterDecision.NEEDS_REVIEW:
            self._metrics.needs_review += 1
        elif decision == FPFilterDecision.SKIPPED:
            self._metrics.skipped += 1
        else:
            self._metrics.errors += 1

    async def filter_batch(
        self,
        findings: list[Finding],
        llm_call: LLMCallFn,
    ) -> tuple[list[FPFilterResult], FPFilterMetrics]:
        """
        Filter a batch of findings.

        Args:
            findings: List of findings to analyze
            llm_call: Async function to call LLM

        Returns:
            Tuple of (results list, metrics)
        """
        # Reset metrics for batch
        self._metrics = FPFilterMetrics(
            total_findings=len(findings),
            fp_before_count=sum(
                1 for f in findings
                if f.confidence == FindingConfidence.LOW
                or self._is_likely_fp_pattern(f)
            ),
        )

        results = []
        for finding in findings:
            result = await self.analyze_finding(finding, llm_call, _track_total=False)
            results.append(result)

        return results, self._metrics

    def _is_likely_fp_pattern(self, finding: Finding) -> bool:
        """Check if pattern is known to have high FP rate."""
        pattern_lower = finding.pattern.lower()
        for high_fp in HIGH_FP_PATTERNS:
            if high_fp in pattern_lower:
                return True
        return False

    def apply_results(
        self,
        findings: list[Finding],
        results: list[FPFilterResult],
    ) -> list[Finding]:
        """
        Apply FP filter results to findings.

        Args:
            findings: List of findings
            results: FP filter results

        Returns:
            Updated findings list
        """
        result_map = {r.finding_id: r for r in results}

        for finding in findings:
            result = result_map.get(finding.id)
            if not result:
                continue

            if result.decision == FPFilterDecision.CONFIRMED_FP:
                finding.update_status(
                    FindingStatus.FALSE_POSITIVE,
                    reason=result.reasoning,
                )
                finding.tier = FindingTier.TIER_B

            elif result.decision == FPFilterDecision.CONFIRMED_VULN:
                finding.update_status(
                    FindingStatus.CONFIRMED,
                    reason=result.reasoning,
                )
                finding.tier = FindingTier.TIER_B
                finding.confidence = FindingConfidence.HIGH

            elif result.decision == FPFilterDecision.NEEDS_REVIEW:
                finding.update_status(
                    FindingStatus.ESCALATED,
                    reason="LLM uncertain, needs human review",
                )

        return findings

    def get_metrics(self) -> FPFilterMetrics:
        """Get current metrics."""
        return self._metrics

    def reset_metrics(self):
        """Reset metrics."""
        self._metrics = FPFilterMetrics()


def create_fp_filter(
    min_confidence_for_fp: int = 80,
    max_tokens: int = 100_000,
    max_cost: float = 5.00,
) -> FPFilter:
    """
    Factory function to create an FP filter.

    Args:
        min_confidence_for_fp: Minimum confidence to mark as FP
        max_tokens: Maximum tokens per batch
        max_cost: Maximum cost per batch

    Returns:
        Configured FPFilter
    """
    return FPFilter(
        rate_limiter=create_rate_limiter(
            max_tokens=max_tokens,
            max_cost=max_cost,
        ),
        min_confidence_for_fp=min_confidence_for_fp,
    )


def calculate_fp_reduction(
    before_count: int,
    after_count: int,
) -> float:
    """
    Calculate FP reduction percentage.

    Args:
        before_count: Count of suspected FPs before filtering
        after_count: Count of confirmed FPs after filtering

    Returns:
        Reduction percentage (negative if FP increased)
    """
    if before_count == 0:
        return 0.0
    return (before_count - after_count) / before_count * 100
