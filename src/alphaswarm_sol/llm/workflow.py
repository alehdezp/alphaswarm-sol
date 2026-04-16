"""
Tier B Analysis Workflow (Task 11.3)

End-to-end orchestration of Tier B LLM analysis:
1. Evaluate confidence to determine routing
2. Slice context for relevant findings
3. Build and execute prompt with contract enforcement
4. Parse and validate LLM response
5. Update finding with verdict

Philosophy: Tier B enhances Tier A, never replaces it.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, Awaitable, Any
from datetime import datetime, timezone
import json

from alphaswarm_sol.findings.model import (
    Finding,
    FindingStatus,
    FindingTier,
    FindingConfidence,
)
from alphaswarm_sol.llm.confidence import (
    ConfidenceEvaluator,
    ConfidenceResult,
    ConfidenceAction,
    ConfidenceThresholds,
)
from alphaswarm_sol.llm.slicer import ContextSlicer, ContextSlice
from alphaswarm_sol.llm.triage import TriageClassifier, TriageLevel, TriageResult
from alphaswarm_sol.llm.contract import (
    PromptContract,
    PromptInput,
    PromptType,
    build_standard_prompt,
)
from alphaswarm_sol.llm.validate import Verdict, LLMVerdict
from alphaswarm_sol.llm.limits import RateLimiter, create_rate_limiter


class WorkflowStatus(str, Enum):
    """Status of a workflow execution."""
    SUCCESS = "success"
    SKIPPED_HIGH_CONFIDENCE = "skipped_high_confidence"
    SKIPPED_LOW_CONFIDENCE = "skipped_low_confidence"
    LLM_ERROR = "llm_error"
    VALIDATION_ERROR = "validation_error"
    RATE_LIMITED = "rate_limited"


@dataclass
class WorkflowResult:
    """Result of Tier B workflow execution."""
    finding_id: str
    status: WorkflowStatus
    original_confidence: float
    tier_b_verdict: Optional[Verdict] = None
    tier_b_confidence: Optional[int] = None
    tier_b_reasoning: Optional[str] = None
    tier_b_evidence: list[str] = field(default_factory=list)
    context_tokens: int = 0
    response_tokens: int = 0
    cost_usd: float = 0.0
    processing_time_ms: int = 0
    error_message: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "finding_id": self.finding_id,
            "status": self.status.value,
            "original_confidence": self.original_confidence,
            "tier_b_verdict": self.tier_b_verdict.value if self.tier_b_verdict else None,
            "tier_b_confidence": self.tier_b_confidence,
            "tier_b_reasoning": self.tier_b_reasoning,
            "tier_b_evidence": self.tier_b_evidence,
            "context_tokens": self.context_tokens,
            "response_tokens": self.response_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "processing_time_ms": self.processing_time_ms,
            "error_message": self.error_message,
        }


@dataclass
class WorkflowStats:
    """Statistics for a batch workflow run."""
    total_findings: int = 0
    tier_b_analyzed: int = 0
    skipped_high_confidence: int = 0
    skipped_low_confidence: int = 0
    confirmed_vulnerable: int = 0
    confirmed_safe: int = 0
    uncertain: int = 0
    errors: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_time_ms: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total_findings": self.total_findings,
            "tier_b_analyzed": self.tier_b_analyzed,
            "skipped_high_confidence": self.skipped_high_confidence,
            "skipped_low_confidence": self.skipped_low_confidence,
            "confirmed_vulnerable": self.confirmed_vulnerable,
            "confirmed_safe": self.confirmed_safe,
            "uncertain": self.uncertain,
            "errors": self.errors,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 4),
            "total_time_ms": self.total_time_ms,
            "analysis_rate": (
                self.tier_b_analyzed / self.total_findings * 100
                if self.total_findings > 0 else 0
            ),
        }


# Type alias for LLM call function
LLMCallFn = Callable[[str], Awaitable[str]]


class TierBWorkflow:
    """
    End-to-end Tier B analysis workflow.

    Workflow:
    1. Evaluate confidence to determine if Tier B needed
    2. For middle-confidence findings:
       a. Slice context based on triage level
       b. Build prompt using contract
       c. Call LLM
       d. Validate and parse response
       e. Update finding with verdict
    3. Track costs and token usage

    Example:
        >>> workflow = TierBWorkflow()
        >>> result = await workflow.analyze_finding(finding, llm_call_fn)
        >>> if result.tier_b_verdict == Verdict.SAFE:
        ...     finding.update_status(FindingStatus.FALSE_POSITIVE)
    """

    def __init__(
        self,
        confidence_thresholds: Optional[ConfidenceThresholds] = None,
        rate_limiter: Optional[RateLimiter] = None,
        contract: Optional[PromptContract] = None,
        strict_mode: bool = True,
    ):
        """
        Initialize Tier B workflow.

        Args:
            confidence_thresholds: Thresholds for auto-confirm/dismiss
            rate_limiter: Rate limiter for cost control
            contract: Prompt contract for validation
            strict_mode: If True, raise on validation errors
        """
        self.confidence_evaluator = ConfidenceEvaluator(confidence_thresholds)
        self.context_slicer = ContextSlicer()
        self.triage_classifier = TriageClassifier()
        self.rate_limiter = rate_limiter or create_rate_limiter()
        self.contract = contract or PromptContract(
            max_retries=3,
            strict_mode=strict_mode,
        )
        self.strict_mode = strict_mode

    async def analyze_finding(
        self,
        finding: Finding,
        llm_call: LLMCallFn,
        kg: Optional[Any] = None,
        code_context: Optional[str] = None,
    ) -> WorkflowResult:
        """
        Run Tier B analysis on a finding.

        Args:
            finding: The Tier A finding to analyze
            llm_call: Async function that calls LLM and returns response
            kg: Optional knowledge graph for context slicing
            code_context: Optional code context (overrides slicing)

        Returns:
            WorkflowResult with verdict and metadata
        """
        import time
        start_time = time.time()

        # Step 1: Evaluate confidence
        confidence_result = self.confidence_evaluator.evaluate(finding)

        # Step 2: Check if we should skip Tier B
        if confidence_result.skip_tier_b:
            return self._create_skipped_result(finding, confidence_result)

        # Step 3: Check rate limits
        allowed, message = self.rate_limiter.check_limits(500)  # Estimate 500 tokens
        if not allowed:
            return WorkflowResult(
                finding_id=finding.id,
                status=WorkflowStatus.RATE_LIMITED,
                original_confidence=confidence_result.numeric_confidence,
                error_message=message,
            )

        # Step 4: Get context
        context = code_context or self._get_context(finding, kg)

        # Step 5: Build prompt input
        prompt_input = PromptInput(
            prompt_type=PromptType.VULNERABILITY_ANALYSIS,
            code_context=context,
            finding_id=finding.id,
            pattern_id=finding.pattern,
            evidence=finding.evidence.properties_matched,
            task_description=finding.description,
        )

        # Step 6: Execute with contract
        try:
            verdict_result = await self.contract.execute_with_contract(
                prompt_input,
                llm_call,
                build_standard_prompt,
            )
        except Exception as e:
            return WorkflowResult(
                finding_id=finding.id,
                status=WorkflowStatus.LLM_ERROR,
                original_confidence=confidence_result.numeric_confidence,
                error_message=str(e),
            )

        # Step 7: Record usage
        # Estimate tokens based on context length
        context_tokens = len(context.split()) * 2  # Rough estimate
        response_tokens = 200  # Typical response size
        cost = (context_tokens * 0.00001) + (response_tokens * 0.00003)  # Rough pricing

        self.rate_limiter.record_usage(
            input_tokens=context_tokens,
            output_tokens=response_tokens,
            cost_usd=cost,
            findings=1,
        )

        # Step 8: Create result
        end_time = time.time()
        processing_time_ms = int((end_time - start_time) * 1000)

        if verdict_result.verdict == Verdict.ERROR:
            return WorkflowResult(
                finding_id=finding.id,
                status=WorkflowStatus.VALIDATION_ERROR,
                original_confidence=confidence_result.numeric_confidence,
                error_message="Failed to get valid LLM response",
                processing_time_ms=processing_time_ms,
            )

        return WorkflowResult(
            finding_id=finding.id,
            status=WorkflowStatus.SUCCESS,
            original_confidence=confidence_result.numeric_confidence,
            tier_b_verdict=verdict_result.verdict,
            tier_b_confidence=verdict_result.confidence,
            tier_b_reasoning=verdict_result.reasoning,
            tier_b_evidence=verdict_result.evidence,
            context_tokens=context_tokens,
            response_tokens=response_tokens,
            cost_usd=cost,
            processing_time_ms=processing_time_ms,
        )

    def _create_skipped_result(
        self,
        finding: Finding,
        confidence_result: ConfidenceResult,
    ) -> WorkflowResult:
        """Create result for skipped findings."""
        if confidence_result.action == ConfidenceAction.AUTO_CONFIRM:
            return WorkflowResult(
                finding_id=finding.id,
                status=WorkflowStatus.SKIPPED_HIGH_CONFIDENCE,
                original_confidence=confidence_result.numeric_confidence,
            )
        else:
            return WorkflowResult(
                finding_id=finding.id,
                status=WorkflowStatus.SKIPPED_LOW_CONFIDENCE,
                original_confidence=confidence_result.numeric_confidence,
            )

    def _get_context(self, finding: Finding, kg: Optional[Any]) -> str:
        """Get context for finding."""
        # First, try to get context from finding evidence
        if finding.evidence.code_snippet:
            return finding.evidence.code_snippet

        # Build context from function node if we have KG
        if kg and finding.location.function:
            # Get triage level for context depth
            fn_node = self._find_function_node(kg, finding)
            if fn_node:
                triage = self.triage_classifier.classify(fn_node)
                slice_result = self.context_slicer.slice(
                    kg,
                    finding.location.function,
                    triage.level,
                )
                return self._format_context(slice_result, finding)

        # Fallback to minimal context
        return self._build_minimal_context(finding)

    def _find_function_node(self, kg: Any, finding: Finding) -> Optional[dict]:
        """Find function node in KG."""
        if isinstance(kg, dict):
            nodes = kg.get("nodes", [])
            for node in nodes:
                if isinstance(node, dict):
                    if node.get("name") == finding.location.function:
                        return node
        return None

    def _format_context(self, slice_result: ContextSlice, finding: Finding) -> str:
        """Format context slice for LLM."""
        lines = [
            f"// File: {finding.location.file}",
            f"// Function: {finding.location.function}",
            f"// Line: {finding.location.line}",
            "",
        ]

        if finding.evidence.code_snippet:
            lines.append(finding.evidence.code_snippet)
        else:
            lines.append(f"// Context includes {len(slice_result.included_nodes)} nodes")

        return "\n".join(lines)

    def _build_minimal_context(self, finding: Finding) -> str:
        """Build minimal context from finding."""
        lines = [
            f"// Finding: {finding.pattern}",
            f"// Location: {finding.location}",
            f"// Description: {finding.description}",
        ]

        if finding.evidence.behavioral_signature:
            lines.append(f"// Signature: {finding.evidence.behavioral_signature}")

        if finding.evidence.properties_matched:
            lines.append(f"// Properties: {', '.join(finding.evidence.properties_matched)}")

        return "\n".join(lines)

    async def analyze_batch(
        self,
        findings: list[Finding],
        llm_call: LLMCallFn,
        kg: Optional[Any] = None,
    ) -> tuple[list[WorkflowResult], WorkflowStats]:
        """
        Run Tier B analysis on a batch of findings.

        Args:
            findings: List of findings to analyze
            llm_call: Async function that calls LLM
            kg: Optional knowledge graph

        Returns:
            Tuple of (results list, aggregate stats)
        """
        results = []
        stats = WorkflowStats(total_findings=len(findings))

        for finding in findings:
            result = await self.analyze_finding(finding, llm_call, kg)
            results.append(result)

            # Update stats
            if result.status == WorkflowStatus.SKIPPED_HIGH_CONFIDENCE:
                stats.skipped_high_confidence += 1
            elif result.status == WorkflowStatus.SKIPPED_LOW_CONFIDENCE:
                stats.skipped_low_confidence += 1
            elif result.status == WorkflowStatus.SUCCESS:
                stats.tier_b_analyzed += 1
                if result.tier_b_verdict == Verdict.VULNERABLE:
                    stats.confirmed_vulnerable += 1
                elif result.tier_b_verdict == Verdict.SAFE:
                    stats.confirmed_safe += 1
                else:
                    stats.uncertain += 1
            else:
                stats.errors += 1

            stats.total_tokens += result.context_tokens + result.response_tokens
            stats.total_cost_usd += result.cost_usd
            stats.total_time_ms += result.processing_time_ms

        return results, stats

    def update_finding_from_result(
        self,
        finding: Finding,
        result: WorkflowResult,
    ) -> None:
        """
        Update finding based on Tier B result.

        Args:
            finding: The finding to update
            result: The workflow result
        """
        if result.status == WorkflowStatus.SKIPPED_HIGH_CONFIDENCE:
            # High confidence - auto-confirm
            finding.tier = FindingTier.TIER_A  # Stays Tier A
            finding.status = FindingStatus.PENDING  # Still needs human review
            finding.investigator_notes = f"Auto-confirmed (confidence: {result.original_confidence:.2f})"

        elif result.status == WorkflowStatus.SKIPPED_LOW_CONFIDENCE:
            # Low confidence - auto-dismiss
            finding.tier = FindingTier.TIER_A
            finding.status = FindingStatus.FALSE_POSITIVE
            finding.status_reason = f"Auto-dismissed (confidence: {result.original_confidence:.2f})"

        elif result.status == WorkflowStatus.SUCCESS:
            # Tier B analysis complete
            finding.tier = FindingTier.TIER_B

            if result.tier_b_verdict == Verdict.VULNERABLE:
                finding.status = FindingStatus.CONFIRMED
                finding.confidence = FindingConfidence.HIGH
            elif result.tier_b_verdict == Verdict.SAFE:
                finding.status = FindingStatus.FALSE_POSITIVE
                finding.status_reason = result.tier_b_reasoning or "LLM determined false positive"
            else:  # UNCERTAIN
                finding.status = FindingStatus.ESCALATED
                finding.status_reason = "Needs human review"

            finding.investigator_notes = (
                f"Tier B verdict: {result.tier_b_verdict.value}\n"
                f"Confidence: {result.tier_b_confidence}%\n"
                f"Reasoning: {result.tier_b_reasoning}"
            )

    def get_usage_report(self) -> dict:
        """Get usage report from rate limiter."""
        return self.rate_limiter.get_usage_report().to_dict()


def create_tier_b_workflow(
    auto_confirm_threshold: float = 0.9,
    auto_dismiss_threshold: float = 0.3,
    max_tokens: int = 100_000,
    max_cost: float = 5.00,
    strict_mode: bool = True,
) -> TierBWorkflow:
    """
    Factory function to create a Tier B workflow.

    Args:
        auto_confirm_threshold: Confidence >= this skips Tier B (auto-confirm)
        auto_dismiss_threshold: Confidence <= this skips Tier B (auto-dismiss)
        max_tokens: Maximum tokens per run
        max_cost: Maximum cost per run in USD
        strict_mode: If True, raise on validation errors

    Returns:
        Configured TierBWorkflow
    """
    thresholds = ConfidenceThresholds(
        auto_confirm_threshold=auto_confirm_threshold,
        auto_dismiss_threshold=auto_dismiss_threshold,
    )
    rate_limiter = create_rate_limiter(
        max_tokens=max_tokens,
        max_cost=max_cost,
    )
    return TierBWorkflow(
        confidence_thresholds=thresholds,
        rate_limiter=rate_limiter,
        strict_mode=strict_mode,
    )
