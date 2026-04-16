"""Phase 12: Cost Tracking for Micro-Agents.

This module provides comprehensive cost tracking for micro-agent
operations, enabling budget control and cost visibility.

Key features:
- Per-agent cost tracking
- Aggregate cost reporting
- Budget enforcement
- Cost estimation
- Historical cost data

Usage:
    from alphaswarm_sol.agents.cost import (
        CostTracker,
        CostReport,
        BudgetExceededError,
        estimate_cost,
    )

    tracker = CostTracker(budget_usd=10.00)
    tracker.record_usage(agent_type, tokens_in, tokens_out)

    if tracker.remaining_budget < 1.00:
        print("Budget running low!")

    report = tracker.get_report()
    print(f"Total cost: ${report.total_cost_usd:.2f}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import logging


logger = logging.getLogger(__name__)


class CostError(Exception):
    """Base exception for cost-related errors."""
    pass


class BudgetExceededError(CostError):
    """Raised when budget is exceeded."""
    def __init__(
        self,
        message: str,
        budget_usd: float,
        spent_usd: float,
        requested_usd: float,
    ):
        super().__init__(message)
        self.budget_usd = budget_usd
        self.spent_usd = spent_usd
        self.requested_usd = requested_usd


# Token pricing per model (USD per 1M tokens)
# These are approximate - actual pricing varies by provider
TOKEN_PRICING = {
    # Claude models
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},

    # GPT models
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "o1": {"input": 15.00, "output": 60.00},

    # Gemini models
    "gemini-1.5-pro": {"input": 3.50, "output": 10.50},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},

    # Default (conservative estimate)
    "default": {"input": 5.00, "output": 15.00},
}


@dataclass
class UsageRecord:
    """Record of a single usage event.

    Attributes:
        timestamp: When the usage occurred
        agent_type: Type of micro-agent
        model: Model used (if known)
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cost_usd: Calculated cost in USD
        bead_id: Associated bead ID (if any)
        duration_seconds: Execution duration
    """
    timestamp: datetime
    agent_type: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    bead_id: Optional[str] = None
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "agent_type": self.agent_type,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "bead_id": self.bead_id,
            "duration_seconds": self.duration_seconds,
        }


@dataclass
class CostReport:
    """Comprehensive cost report.

    Attributes:
        total_cost_usd: Total cost
        total_input_tokens: Total input tokens
        total_output_tokens: Total output tokens
        total_requests: Number of requests
        avg_cost_per_request: Average cost per request
        cost_by_agent: Cost breakdown by agent type
        cost_by_model: Cost breakdown by model
        budget_usd: Budget if set
        remaining_budget: Remaining budget
        usage_records: Individual usage records
    """
    total_cost_usd: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_requests: int = 0
    avg_cost_per_request: float = 0.0
    cost_by_agent: Dict[str, float] = field(default_factory=dict)
    cost_by_model: Dict[str, float] = field(default_factory=dict)
    budget_usd: Optional[float] = None
    remaining_budget: Optional[float] = None
    usage_records: List[UsageRecord] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_cost_usd": round(self.total_cost_usd, 4),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_requests": self.total_requests,
            "avg_cost_per_request": round(self.avg_cost_per_request, 4),
            "cost_by_agent": {k: round(v, 4) for k, v in self.cost_by_agent.items()},
            "cost_by_model": {k: round(v, 4) for k, v in self.cost_by_model.items()},
            "budget_usd": self.budget_usd,
            "remaining_budget": round(self.remaining_budget, 4) if self.remaining_budget else None,
            "budget_utilization_pct": (
                round(self.total_cost_usd / self.budget_usd * 100, 1)
                if self.budget_usd else None
            ),
        }

    def get_console_summary(self) -> str:
        """Get formatted summary for console display."""
        lines = [
            "╔══════════════════════════════════════════════╗",
            "║            MICRO-AGENT COST REPORT           ║",
            "╠══════════════════════════════════════════════╣",
            f"║  Total Cost:       ${self.total_cost_usd:>10.4f}            ║",
            f"║  Total Tokens:     {self.total_input_tokens + self.total_output_tokens:>10,}            ║",
            f"║  Total Requests:   {self.total_requests:>10}            ║",
        ]

        if self.budget_usd:
            utilization = self.total_cost_usd / self.budget_usd * 100
            lines.extend([
                "╠══════════════════════════════════════════════╣",
                f"║  Budget:           ${self.budget_usd:>10.2f}            ║",
                f"║  Remaining:        ${self.remaining_budget or 0:>10.2f}            ║",
                f"║  Utilization:      {utilization:>10.1f}%           ║",
            ])

        if self.cost_by_agent:
            lines.append("╠══════════════════════════════════════════════╣")
            lines.append("║  Cost by Agent Type:                         ║")
            for agent, cost in sorted(self.cost_by_agent.items()):
                lines.append(f"║    {agent:<18} ${cost:>8.4f}           ║")

        lines.append("╚══════════════════════════════════════════════╝")

        return "\n".join(lines)


class CostTracker:
    """Tracker for micro-agent costs.

    Tracks token usage and costs across all micro-agent operations,
    with optional budget enforcement.

    Example:
        tracker = CostTracker(budget_usd=10.00)

        # Record usage
        tracker.record_usage(
            agent_type="verifier",
            model="claude-3-5-sonnet",
            input_tokens=1000,
            output_tokens=500,
        )

        # Check budget
        if not tracker.can_afford(estimated_cost=0.50):
            print("Insufficient budget")

        # Get report
        report = tracker.get_report()
    """

    def __init__(
        self,
        budget_usd: Optional[float] = None,
        enforce_budget: bool = True,
    ):
        """Initialize cost tracker.

        Args:
            budget_usd: Optional budget limit in USD
            enforce_budget: Whether to raise error on budget exceeded
        """
        self.budget_usd = budget_usd
        self.enforce_budget = enforce_budget
        self._records: List[UsageRecord] = []

    @property
    def total_cost(self) -> float:
        """Total cost so far."""
        return sum(r.cost_usd for r in self._records)

    @property
    def remaining_budget(self) -> Optional[float]:
        """Remaining budget if set."""
        if self.budget_usd is None:
            return None
        return max(0.0, self.budget_usd - self.total_cost)

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return sum(r.input_tokens + r.output_tokens for r in self._records)

    def record_usage(
        self,
        agent_type: str,
        model: str = "default",
        input_tokens: int = 0,
        output_tokens: int = 0,
        bead_id: Optional[str] = None,
        duration_seconds: float = 0.0,
    ) -> UsageRecord:
        """Record a usage event.

        Args:
            agent_type: Type of micro-agent
            model: Model used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            bead_id: Associated bead ID
            duration_seconds: Execution duration

        Returns:
            The created UsageRecord

        Raises:
            BudgetExceededError: If budget exceeded and enforcement enabled
        """
        cost = calculate_cost(model, input_tokens, output_tokens)

        # Check budget before recording
        if self.budget_usd is not None:
            new_total = self.total_cost + cost
            if new_total > self.budget_usd:
                if self.enforce_budget:
                    raise BudgetExceededError(
                        f"Budget exceeded: ${new_total:.2f} > ${self.budget_usd:.2f}",
                        budget_usd=self.budget_usd,
                        spent_usd=self.total_cost,
                        requested_usd=cost,
                    )
                else:
                    logger.warning(
                        f"Budget exceeded: ${new_total:.2f} > ${self.budget_usd:.2f}"
                    )

        record = UsageRecord(
            timestamp=datetime.now(),
            agent_type=agent_type,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            bead_id=bead_id,
            duration_seconds=duration_seconds,
        )

        self._records.append(record)
        return record

    def can_afford(self, estimated_cost: float) -> bool:
        """Check if estimated cost is within budget.

        Args:
            estimated_cost: Estimated cost in USD

        Returns:
            True if within budget (or no budget set)
        """
        if self.budget_usd is None:
            return True
        return self.total_cost + estimated_cost <= self.budget_usd

    def get_report(self) -> CostReport:
        """Generate comprehensive cost report.

        Returns:
            CostReport with all statistics
        """
        if not self._records:
            return CostReport(
                budget_usd=self.budget_usd,
                remaining_budget=self.budget_usd,
            )

        total_input = sum(r.input_tokens for r in self._records)
        total_output = sum(r.output_tokens for r in self._records)
        total_cost = sum(r.cost_usd for r in self._records)

        # Cost by agent type
        cost_by_agent: Dict[str, float] = {}
        for r in self._records:
            cost_by_agent[r.agent_type] = cost_by_agent.get(r.agent_type, 0) + r.cost_usd

        # Cost by model
        cost_by_model: Dict[str, float] = {}
        for r in self._records:
            cost_by_model[r.model] = cost_by_model.get(r.model, 0) + r.cost_usd

        return CostReport(
            total_cost_usd=total_cost,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_requests=len(self._records),
            avg_cost_per_request=total_cost / len(self._records),
            cost_by_agent=cost_by_agent,
            cost_by_model=cost_by_model,
            budget_usd=self.budget_usd,
            remaining_budget=self.remaining_budget,
            usage_records=self._records,
        )

    def reset(self) -> None:
        """Reset all tracked usage."""
        self._records = []


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Calculate cost for token usage.

    Args:
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Cost in USD
    """
    # Get pricing for model
    pricing = TOKEN_PRICING.get(model, TOKEN_PRICING["default"])

    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]

    return input_cost + output_cost


def estimate_cost(
    model: str = "default",
    prompt_length: int = 0,
    expected_response_length: int = 0,
    chars_per_token: float = 4.0,
) -> float:
    """Estimate cost based on text length.

    Args:
        model: Model to estimate for
        prompt_length: Length of prompt in characters
        expected_response_length: Expected response length in characters
        chars_per_token: Characters per token (default 4)

    Returns:
        Estimated cost in USD
    """
    input_tokens = int(prompt_length / chars_per_token)
    output_tokens = int(expected_response_length / chars_per_token)

    return calculate_cost(model, input_tokens, output_tokens)


def get_cost_summary(records: List[UsageRecord]) -> Dict[str, Any]:
    """Get summary statistics from usage records.

    Args:
        records: List of usage records

    Returns:
        Summary dictionary
    """
    if not records:
        return {
            "total_cost_usd": 0.0,
            "total_tokens": 0,
            "request_count": 0,
        }

    return {
        "total_cost_usd": sum(r.cost_usd for r in records),
        "total_tokens": sum(r.input_tokens + r.output_tokens for r in records),
        "total_input_tokens": sum(r.input_tokens for r in records),
        "total_output_tokens": sum(r.output_tokens for r in records),
        "request_count": len(records),
        "avg_cost_per_request": sum(r.cost_usd for r in records) / len(records),
        "models_used": list(set(r.model for r in records)),
        "agent_types_used": list(set(r.agent_type for r in records)),
    }


# Global tracker instance
_global_tracker: Optional[CostTracker] = None


def get_global_tracker() -> CostTracker:
    """Get or create global cost tracker.

    Returns:
        Global CostTracker instance
    """
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = CostTracker()
    return _global_tracker


def set_global_budget(budget_usd: float) -> None:
    """Set budget on global tracker.

    Args:
        budget_usd: Budget in USD
    """
    global _global_tracker
    _global_tracker = CostTracker(budget_usd=budget_usd)


def reset_global_tracker() -> None:
    """Reset global cost tracker."""
    global _global_tracker
    if _global_tracker:
        _global_tracker.reset()


def record_pool_usage(
    pool_id: str,
    agent_type: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    bead_id: Optional[str] = None,
    operation: Optional[str] = None,
) -> None:
    """Record usage and sync to pool cost ledger.

    This is a convenience function that records usage both to the
    global tracker and to the pool-specific cost ledger (if available).

    Args:
        pool_id: Pool identifier for cost attribution
        agent_type: Type of agent
        model: Model used
        input_tokens: Input tokens consumed
        output_tokens: Output tokens generated
        bead_id: Optional bead ID for attribution
        operation: Optional operation description

    Raises:
        PoolBudgetExceededError: If pool budget exceeded (hard limit mode)
    """
    from ..metrics.cost_ledger import get_pool_ledger

    # Record to global tracker
    global_tracker = get_global_tracker()
    global_tracker.record_usage(
        agent_type=agent_type,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        bead_id=bead_id,
    )

    # Record to pool ledger (may raise PoolBudgetExceededError)
    ledger = get_pool_ledger(pool_id)
    ledger.record(
        agent_type=agent_type,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        bead_id=bead_id,
        operation=operation,
    )
