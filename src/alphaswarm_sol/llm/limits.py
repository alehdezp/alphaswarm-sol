"""
LLM Rate Limiting and Cost Caps (Task 11.11)

Prevents runaway costs and API abuse:
1. Token limits per run
2. Cost caps per run
3. Requests per minute rate limiting
4. Clear error messages when limits exceeded
"""

import time
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict, Any
from enum import Enum


class LimitType(Enum):
    """Types of limits that can be exceeded."""
    TOKENS = "tokens"
    COST = "cost"
    RATE = "rate"
    FINDINGS = "findings"


class LimitExceededError(Exception):
    """Raised when a usage limit is exceeded."""
    def __init__(self, limit_type: LimitType, message: str, current: float, maximum: float):
        self.limit_type = limit_type
        self.current = current
        self.maximum = maximum
        super().__init__(message)


@dataclass
class LLMLimits:
    """LLM usage limits and caps."""
    # Token limits
    max_tokens_per_run: int = 100_000
    max_input_tokens_per_request: int = 50_000
    max_output_tokens_per_request: int = 4_096

    # Cost limits
    max_cost_per_run_usd: float = 5.00
    warn_cost_threshold_usd: float = 1.00

    # Rate limits
    max_requests_per_minute: int = 60
    max_findings_per_run: int = 200

    # Enforcement behavior
    hard_limit: bool = True  # If True, stop; if False, warn and continue

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "max_tokens_per_run": self.max_tokens_per_run,
            "max_input_tokens_per_request": self.max_input_tokens_per_request,
            "max_output_tokens_per_request": self.max_output_tokens_per_request,
            "max_cost_per_run_usd": self.max_cost_per_run_usd,
            "warn_cost_threshold_usd": self.warn_cost_threshold_usd,
            "max_requests_per_minute": self.max_requests_per_minute,
            "max_findings_per_run": self.max_findings_per_run,
            "hard_limit": self.hard_limit,
        }


@dataclass
class UsageReport:
    """Current usage statistics."""
    tokens_used: int = 0
    cost_usd: float = 0.0
    requests_made: int = 0
    findings_analyzed: int = 0
    warnings: List[str] = field(default_factory=list)
    limit_exceeded: bool = False
    exceeded_type: Optional[LimitType] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for display."""
        return {
            "tokens_used": self.tokens_used,
            "cost_usd": round(self.cost_usd, 4),
            "requests_made": self.requests_made,
            "findings_analyzed": self.findings_analyzed,
            "warnings": self.warnings,
            "limit_exceeded": self.limit_exceeded,
            "exceeded_type": self.exceeded_type.value if self.exceeded_type else None,
        }


class RateLimiter:
    """
    Rate limiting for LLM API calls.

    Tracks usage and enforces limits on:
    - Tokens per run
    - Cost per run
    - Requests per minute
    - Findings per run
    """

    def __init__(self, limits: Optional[LLMLimits] = None):
        """
        Initialize rate limiter.

        Args:
            limits: LLM limits configuration (uses defaults if None)
        """
        self.limits = limits or LLMLimits()
        self._tokens_used = 0
        self._cost_usd = 0.0
        self._requests: List[float] = []  # Timestamps of requests
        self._findings_analyzed = 0
        self._warnings: List[str] = []

    def check_limits(self, estimated_tokens: int = 0) -> Tuple[bool, str]:
        """
        Check if request is within limits.

        Args:
            estimated_tokens: Estimated tokens for the request

        Returns:
            Tuple of (allowed, message)
        """
        # Check token limit
        if self._tokens_used + estimated_tokens > self.limits.max_tokens_per_run:
            return False, (
                f"Token limit exceeded: {self._tokens_used:,} + {estimated_tokens:,} "
                f"> {self.limits.max_tokens_per_run:,}"
            )

        # Check cost limit
        if self._cost_usd > self.limits.max_cost_per_run_usd:
            return False, (
                f"Cost limit exceeded: ${self._cost_usd:.2f} "
                f"> ${self.limits.max_cost_per_run_usd:.2f}"
            )

        # Check rate limit (requests per minute)
        now = time.time()
        self._requests = [t for t in self._requests if now - t < 60]
        if len(self._requests) >= self.limits.max_requests_per_minute:
            return False, (
                f"Rate limit: {len(self._requests)} requests in last minute "
                f"(max: {self.limits.max_requests_per_minute})"
            )

        # Check findings limit
        if self._findings_analyzed >= self.limits.max_findings_per_run:
            return False, (
                f"Findings limit exceeded: {self._findings_analyzed} "
                f">= {self.limits.max_findings_per_run}"
            )

        return True, ""

    def check_and_raise(self, estimated_tokens: int = 0):
        """
        Check limits and raise if exceeded (in hard limit mode).

        Args:
            estimated_tokens: Estimated tokens for the request

        Raises:
            LimitExceededError: If limits exceeded in hard mode
        """
        allowed, message = self.check_limits(estimated_tokens)
        if not allowed and self.limits.hard_limit:
            # Determine which limit was exceeded
            if "Token limit" in message:
                limit_type = LimitType.TOKENS
                current = self._tokens_used + estimated_tokens
                maximum = self.limits.max_tokens_per_run
            elif "Cost limit" in message:
                limit_type = LimitType.COST
                current = self._cost_usd
                maximum = self.limits.max_cost_per_run_usd
            elif "Rate limit" in message:
                limit_type = LimitType.RATE
                current = len(self._requests)
                maximum = self.limits.max_requests_per_minute
            else:
                limit_type = LimitType.FINDINGS
                current = self._findings_analyzed
                maximum = self.limits.max_findings_per_run

            raise LimitExceededError(limit_type, message, current, maximum)
        elif not allowed:
            self._warnings.append(message)

    def record_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        findings: int = 1
    ):
        """
        Record usage after successful request.

        Args:
            input_tokens: Input tokens used
            output_tokens: Output tokens used
            cost_usd: Cost in USD
            findings: Number of findings analyzed
        """
        self._tokens_used += input_tokens + output_tokens
        self._cost_usd += cost_usd
        self._requests.append(time.time())
        self._findings_analyzed += findings

        # Check for cost warning threshold
        if (
            self._cost_usd >= self.limits.warn_cost_threshold_usd
            and self._cost_usd - cost_usd < self.limits.warn_cost_threshold_usd
        ):
            self._warnings.append(
                f"Cost warning: Passed ${self.limits.warn_cost_threshold_usd:.2f} threshold "
                f"(current: ${self._cost_usd:.2f})"
            )

    def get_usage_report(self) -> UsageReport:
        """Get current usage report."""
        allowed, message = self.check_limits()
        return UsageReport(
            tokens_used=self._tokens_used,
            cost_usd=self._cost_usd,
            requests_made=len(self._requests),
            findings_analyzed=self._findings_analyzed,
            warnings=self._warnings.copy(),
            limit_exceeded=not allowed,
            exceeded_type=self._get_exceeded_type() if not allowed else None,
        )

    def _get_exceeded_type(self) -> Optional[LimitType]:
        """Determine which limit type was exceeded."""
        if self._tokens_used >= self.limits.max_tokens_per_run:
            return LimitType.TOKENS
        if self._cost_usd >= self.limits.max_cost_per_run_usd:
            return LimitType.COST
        now = time.time()
        recent_requests = [t for t in self._requests if now - t < 60]
        if len(recent_requests) >= self.limits.max_requests_per_minute:
            return LimitType.RATE
        if self._findings_analyzed >= self.limits.max_findings_per_run:
            return LimitType.FINDINGS
        return None

    def get_remaining(self) -> Dict[str, Any]:
        """Get remaining budget/capacity."""
        now = time.time()
        recent_requests = len([t for t in self._requests if now - t < 60])

        return {
            "tokens_remaining": max(0, self.limits.max_tokens_per_run - self._tokens_used),
            "cost_remaining_usd": max(0, self.limits.max_cost_per_run_usd - self._cost_usd),
            "requests_remaining_per_minute": max(
                0, self.limits.max_requests_per_minute - recent_requests
            ),
            "findings_remaining": max(
                0, self.limits.max_findings_per_run - self._findings_analyzed
            ),
        }

    def reset(self):
        """Reset all counters."""
        self._tokens_used = 0
        self._cost_usd = 0.0
        self._requests = []
        self._findings_analyzed = 0
        self._warnings = []

    def format_status(self) -> str:
        """Format current status as a string for display."""
        remaining = self.get_remaining()
        return (
            f"Tokens: {self._tokens_used:,}/{self.limits.max_tokens_per_run:,} | "
            f"Cost: ${self._cost_usd:.2f}/${self.limits.max_cost_per_run_usd:.2f} | "
            f"Rate: {len([t for t in self._requests if time.time() - t < 60])}"
            f"/{self.limits.max_requests_per_minute}/min | "
            f"Findings: {self._findings_analyzed}/{self.limits.max_findings_per_run}"
        )


def create_rate_limiter(
    max_tokens: int = 100_000,
    max_cost: float = 5.00,
    max_rate: int = 60,
    hard_limit: bool = True,
) -> RateLimiter:
    """
    Factory function to create a rate limiter.

    Args:
        max_tokens: Maximum tokens per run
        max_cost: Maximum cost per run in USD
        max_rate: Maximum requests per minute
        hard_limit: Whether to enforce hard limits

    Returns:
        Configured RateLimiter
    """
    limits = LLMLimits(
        max_tokens_per_run=max_tokens,
        max_cost_per_run_usd=max_cost,
        max_requests_per_minute=max_rate,
        hard_limit=hard_limit,
    )
    return RateLimiter(limits)


def check_budget(
    rate_limiter: RateLimiter,
    estimated_tokens: int = 0,
) -> Tuple[bool, str]:
    """
    Convenience function to check if operation is within budget.

    Args:
        rate_limiter: The rate limiter to check
        estimated_tokens: Estimated tokens for the operation

    Returns:
        Tuple of (allowed, message)
    """
    return rate_limiter.check_limits(estimated_tokens)


def get_usage_summary(rate_limiter: RateLimiter) -> str:
    """
    Get a formatted usage summary.

    Args:
        rate_limiter: The rate limiter

    Returns:
        Formatted summary string
    """
    return rate_limiter.format_status()
