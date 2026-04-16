"""
Noninteractive Batch Processing (Task 11.9)

Enables LLM analysis in CI/batch environments without human input.

Key features:
- Batch analysis of multiple findings
- Retry logic with backoff
- Progress tracking
- Graceful error handling
- CI-friendly output modes
"""

from dataclasses import dataclass, field
from typing import Optional, Callable, Awaitable, Any
from enum import Enum
import asyncio
import json
import logging
import time

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
from alphaswarm_sol.llm.fp_filter import (
    FPFilter,
    FPFilterResult,
    FPFilterDecision,
    create_fp_filter,
)
from alphaswarm_sol.llm.limits import (
    RateLimiter,
    LLMLimits,
    create_rate_limiter,
)
from alphaswarm_sol.llm.contract import (
    PromptContract,
    build_standard_prompt,
)


logger = logging.getLogger(__name__)


class OutputMode(str, Enum):
    """Output mode for batch results."""
    JSON = "json"
    SARIF = "sarif"
    COMPACT = "compact"
    SUMMARY = "summary"


class BatchStatus(str, Enum):
    """Status of batch processing."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchProgress:
    """Progress tracking for batch processing."""
    total: int = 0
    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0

    tokens_used: int = 0
    cost_usd: float = 0.0

    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None

    @property
    def percent_complete(self) -> float:
        """Calculate completion percentage."""
        return (self.processed / self.total * 100) if self.total > 0 else 0

    @property
    def elapsed_seconds(self) -> float:
        """Calculate elapsed time."""
        end = self.end_time or time.time()
        return end - self.start_time

    @property
    def findings_per_second(self) -> float:
        """Calculate processing rate."""
        elapsed = self.elapsed_seconds
        return self.processed / elapsed if elapsed > 0 else 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total": self.total,
            "processed": self.processed,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "skipped": self.skipped,
            "percent_complete": round(self.percent_complete, 1),
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "findings_per_second": round(self.findings_per_second, 2),
            "tokens_used": self.tokens_used,
            "cost_usd": round(self.cost_usd, 4),
        }

    def progress_line(self) -> str:
        """Generate progress line for display."""
        return (
            f"[{self.processed}/{self.total}] "
            f"Tokens: {self.tokens_used:,} | "
            f"Cost: ${self.cost_usd:.2f} | "
            f"Rate: {self.findings_per_second:.1f}/sec"
        )


@dataclass
class BatchResult:
    """Result of batch processing."""
    status: BatchStatus
    progress: BatchProgress
    results: list[WorkflowResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "progress": self.progress.to_dict(),
            "results": [r.to_dict() for r in self.results],
            "errors": self.errors,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def to_summary(self) -> str:
        """Generate summary text."""
        lines = [
            "=" * 60,
            "BATCH ANALYSIS COMPLETE",
            "=" * 60,
            "",
            f"Status: {self.status.value.upper()}",
            f"Total Findings: {self.progress.total}",
            f"Processed: {self.progress.processed}",
            f"  - Succeeded: {self.progress.succeeded}",
            f"  - Failed: {self.progress.failed}",
            f"  - Skipped: {self.progress.skipped}",
            "",
            f"Tokens Used: {self.progress.tokens_used:,}",
            f"Cost: ${self.progress.cost_usd:.4f}",
            f"Time: {self.progress.elapsed_seconds:.2f}s",
            f"Rate: {self.progress.findings_per_second:.2f} findings/sec",
            "",
        ]

        # Result breakdown
        confirmed = sum(1 for r in self.results if r.status == WorkflowStatus.CONFIRMED)
        dismissed = sum(1 for r in self.results if r.status == WorkflowStatus.DISMISSED)
        uncertain = sum(1 for r in self.results if r.status == WorkflowStatus.UNCERTAIN)

        lines.extend([
            "Results:",
            f"  - Confirmed Vulnerabilities: {confirmed}",
            f"  - Dismissed (FP): {dismissed}",
            f"  - Uncertain (Need Review): {uncertain}",
            "",
        ])

        if self.errors:
            lines.extend([
                "Errors:",
                *[f"  - {e}" for e in self.errors[:5]],
            ])
            if len(self.errors) > 5:
                lines.append(f"  ... and {len(self.errors) - 5} more errors")

        lines.append("=" * 60)
        return "\n".join(lines)


# Type aliases
LLMCallFn = Callable[[str], Awaitable[str]]
ProgressCallback = Callable[[BatchProgress], None]


@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0
    max_concurrent: int = 5
    fail_fast: bool = False
    show_progress: bool = True
    output_mode: OutputMode = OutputMode.SUMMARY

    # Cost limits
    max_tokens: int = 100_000
    max_cost_usd: float = 5.00

    # Workflow settings
    auto_confirm_threshold: float = 0.9
    auto_dismiss_threshold: float = 0.3


class NoninteractiveBatchRunner:
    """
    Noninteractive batch runner for LLM analysis.

    Designed for CI/batch environments where human input is not possible.
    Provides retry logic, progress tracking, and graceful error handling.

    Example:
        >>> runner = NoninteractiveBatchRunner()
        >>> result = await runner.run(findings, llm_call)
        >>> print(result.to_summary())
    """

    def __init__(
        self,
        config: Optional[BatchConfig] = None,
        workflow: Optional[TierBWorkflow] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        """
        Initialize batch runner.

        Args:
            config: Batch configuration
            workflow: Optional TierBWorkflow to use
            rate_limiter: Optional rate limiter
        """
        self.config = config or BatchConfig()
        self.workflow = workflow or create_tier_b_workflow(
            auto_confirm_threshold=self.config.auto_confirm_threshold,
            auto_dismiss_threshold=self.config.auto_dismiss_threshold,
        )
        self.rate_limiter = rate_limiter or create_rate_limiter(
            max_tokens=self.config.max_tokens,
            max_cost=self.config.max_cost_usd,
        )

        self._progress = BatchProgress()
        self._cancelled = False

    async def run(
        self,
        findings: list[Finding],
        llm_call: LLMCallFn,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> BatchResult:
        """
        Run batch analysis on findings.

        Args:
            findings: List of findings to analyze
            llm_call: Async function to call LLM
            progress_callback: Optional callback for progress updates

        Returns:
            BatchResult with all results
        """
        self._progress = BatchProgress(total=len(findings))
        self._cancelled = False

        results: list[WorkflowResult] = []
        errors: list[str] = []

        try:
            if self.config.max_concurrent > 1:
                # Concurrent processing
                results, errors = await self._run_concurrent(
                    findings, llm_call, progress_callback
                )
            else:
                # Sequential processing
                results, errors = await self._run_sequential(
                    findings, llm_call, progress_callback
                )

            self._progress.end_time = time.time()

            status = BatchStatus.COMPLETED
            if errors and self.config.fail_fast:
                status = BatchStatus.FAILED
            elif self._cancelled:
                status = BatchStatus.CANCELLED

            return BatchResult(
                status=status,
                progress=self._progress,
                results=results,
                errors=errors,
            )

        except Exception as e:
            self._progress.end_time = time.time()
            return BatchResult(
                status=BatchStatus.FAILED,
                progress=self._progress,
                results=results,
                errors=[str(e)] + errors,
            )

    async def _run_sequential(
        self,
        findings: list[Finding],
        llm_call: LLMCallFn,
        progress_callback: Optional[ProgressCallback],
    ) -> tuple[list[WorkflowResult], list[str]]:
        """Run analysis sequentially."""
        results = []
        errors = []

        for finding in findings:
            if self._cancelled:
                break

            result, error = await self._analyze_with_retry(finding, llm_call)

            if result:
                results.append(result)
                self._progress.succeeded += 1
            elif error:
                errors.append(error)
                self._progress.failed += 1
                if self.config.fail_fast:
                    break
            else:
                self._progress.skipped += 1

            self._progress.processed += 1

            if progress_callback:
                progress_callback(self._progress)

        return results, errors

    async def _run_concurrent(
        self,
        findings: list[Finding],
        llm_call: LLMCallFn,
        progress_callback: Optional[ProgressCallback],
    ) -> tuple[list[WorkflowResult], list[str]]:
        """Run analysis concurrently with semaphore."""
        semaphore = asyncio.Semaphore(self.config.max_concurrent)
        results: list[WorkflowResult] = []
        errors: list[str] = []
        results_lock = asyncio.Lock()

        async def process_finding(finding: Finding):
            if self._cancelled:
                return

            async with semaphore:
                result, error = await self._analyze_with_retry(finding, llm_call)

                async with results_lock:
                    if result:
                        results.append(result)
                        self._progress.succeeded += 1
                    elif error:
                        errors.append(error)
                        self._progress.failed += 1
                    else:
                        self._progress.skipped += 1

                    self._progress.processed += 1

                    if progress_callback:
                        progress_callback(self._progress)

        tasks = [process_finding(f) for f in findings]
        await asyncio.gather(*tasks)

        return results, errors

    async def _analyze_with_retry(
        self,
        finding: Finding,
        llm_call: LLMCallFn,
    ) -> tuple[Optional[WorkflowResult], Optional[str]]:
        """
        Analyze a finding with retry logic.

        Returns:
            Tuple of (result, error) - one will be None
        """
        # Check rate limits
        allowed, message = self.rate_limiter.check_limits(500)
        if not allowed:
            return None, f"Rate limited: {message}"

        delay = self.config.retry_delay

        for attempt in range(self.config.max_retries):
            try:
                result = await self.workflow.analyze_finding(finding, llm_call)

                # Record usage
                tokens = result.context_tokens + result.response_tokens
                cost = result.cost_usd
                self.rate_limiter.record_usage(tokens, result.response_tokens, cost, findings=1)
                self._progress.tokens_used += tokens
                self._progress.cost_usd += cost

                # Check if result is successful (not an error status)
                error_statuses = [
                    WorkflowStatus.LLM_ERROR,
                    WorkflowStatus.VALIDATION_ERROR,
                    WorkflowStatus.RATE_LIMITED,
                ]
                if result.status not in error_statuses:
                    return result, None

                # Error status - retry
                logger.warning(f"Attempt {attempt + 1} returned error status {result.status.value}: {result.error_message}")

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")

            # Wait before retry with backoff
            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(delay)
                delay *= self.config.retry_backoff

        return None, f"Max retries ({self.config.max_retries}) exceeded for finding {finding.id}"

    def cancel(self):
        """Cancel the batch processing."""
        self._cancelled = True

    @property
    def progress(self) -> BatchProgress:
        """Get current progress."""
        return self._progress


class CIRunner:
    """
    CI-specific runner that fails on any error.

    Example:
        >>> runner = CIRunner()
        >>> try:
        ...     result = await runner.run(findings, llm_call)
        ...     sys.exit(0 if result.progress.failed == 0 else 1)
        ... except CIError as e:
        ...     print(e)
        ...     sys.exit(1)
    """

    def __init__(
        self,
        max_findings: int = 100,
        max_cost_usd: float = 2.00,
    ):
        """
        Initialize CI runner.

        Args:
            max_findings: Maximum findings to process
            max_cost_usd: Maximum cost limit
        """
        self.config = BatchConfig(
            fail_fast=True,
            max_concurrent=3,
            max_cost_usd=max_cost_usd,
            show_progress=False,
            output_mode=OutputMode.JSON,
        )
        self.max_findings = max_findings

    async def run(
        self,
        findings: list[Finding],
        llm_call: LLMCallFn,
    ) -> BatchResult:
        """
        Run CI analysis.

        Args:
            findings: Findings to analyze (will be limited)
            llm_call: LLM call function

        Returns:
            BatchResult

        Raises:
            CIError: On configuration or limit errors
        """
        # Limit findings
        if len(findings) > self.max_findings:
            findings = findings[:self.max_findings]
            logger.warning(f"Limited to {self.max_findings} findings for CI")

        runner = NoninteractiveBatchRunner(config=self.config)
        return await runner.run(findings, llm_call)


class CIError(Exception):
    """Error during CI execution."""
    pass


def create_batch_runner(
    max_concurrent: int = 5,
    max_retries: int = 3,
    max_tokens: int = 100_000,
    max_cost_usd: float = 5.00,
    fail_fast: bool = False,
) -> NoninteractiveBatchRunner:
    """
    Factory function to create a batch runner.

    Args:
        max_concurrent: Maximum concurrent analyses
        max_retries: Maximum retries per finding
        max_tokens: Maximum tokens for batch
        max_cost_usd: Maximum cost for batch
        fail_fast: Whether to fail on first error

    Returns:
        Configured NoninteractiveBatchRunner
    """
    config = BatchConfig(
        max_concurrent=max_concurrent,
        max_retries=max_retries,
        max_tokens=max_tokens,
        max_cost_usd=max_cost_usd,
        fail_fast=fail_fast,
    )
    return NoninteractiveBatchRunner(config=config)


def create_ci_runner(
    max_findings: int = 100,
    max_cost_usd: float = 2.00,
) -> CIRunner:
    """
    Factory function to create a CI runner.

    Args:
        max_findings: Maximum findings to process
        max_cost_usd: Maximum cost limit

    Returns:
        Configured CIRunner
    """
    return CIRunner(
        max_findings=max_findings,
        max_cost_usd=max_cost_usd,
    )
