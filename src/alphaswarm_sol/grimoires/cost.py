"""Cost Tracking for Grimoire Execution.

Task 13.8: Track and report costs for grimoire execution.

Cost tracking provides:
- Token usage tracking (input/output)
- Cost estimation based on model pricing
- Budget enforcement
- Cost breakdown by step
- Aggregate cost reporting
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CostCategory(Enum):
    """Categories of costs in grimoire execution."""

    LLM_TOKENS = "llm_tokens"  # Token costs for LLM calls
    COMPUTE = "compute"  # Compute/execution costs
    API_CALLS = "api_calls"  # External API calls
    STORAGE = "storage"  # Storage operations
    NETWORK = "network"  # Network/RPC costs


@dataclass
class TokenUsage:
    """Token usage for an LLM operation."""

    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0  # Prompt cache hits

    @property
    def total_tokens(self) -> int:
        """Get total tokens used."""
        return self.input_tokens + self.output_tokens

    @property
    def effective_input_tokens(self) -> int:
        """Get effective input tokens (accounting for cache)."""
        return max(0, self.input_tokens - self.cached_tokens)

    def add(self, other: "TokenUsage") -> "TokenUsage":
        """Add another token usage to this one."""
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cached_tokens=self.cached_tokens + other.cached_tokens,
        )

    def to_dict(self) -> Dict[str, int]:
        """Serialize to dictionary."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_tokens": self.cached_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class ModelPricing:
    """Pricing information for a model.

    Prices are in USD per 1M tokens.
    """

    model_name: str
    input_price_per_million: float  # USD per 1M input tokens
    output_price_per_million: float  # USD per 1M output tokens
    cached_input_price_per_million: float = 0.0  # USD per 1M cached tokens

    def calculate_cost(self, usage: TokenUsage) -> float:
        """Calculate cost for given token usage.

        Args:
            usage: Token usage

        Returns:
            Cost in USD
        """
        effective_input = usage.effective_input_tokens
        cached = usage.cached_tokens

        input_cost = (effective_input / 1_000_000) * self.input_price_per_million
        cached_cost = (cached / 1_000_000) * self.cached_input_price_per_million
        output_cost = (usage.output_tokens / 1_000_000) * self.output_price_per_million

        return input_cost + cached_cost + output_cost


# Default pricing for common models (as of 2026-01)
DEFAULT_PRICING = {
    "claude-3-opus": ModelPricing(
        model_name="claude-3-opus",
        input_price_per_million=15.0,
        output_price_per_million=75.0,
        cached_input_price_per_million=1.5,
    ),
    "claude-3-sonnet": ModelPricing(
        model_name="claude-3-sonnet",
        input_price_per_million=3.0,
        output_price_per_million=15.0,
        cached_input_price_per_million=0.3,
    ),
    "claude-3-haiku": ModelPricing(
        model_name="claude-3-haiku",
        input_price_per_million=0.25,
        output_price_per_million=1.25,
        cached_input_price_per_million=0.03,
    ),
    "gpt-4-turbo": ModelPricing(
        model_name="gpt-4-turbo",
        input_price_per_million=10.0,
        output_price_per_million=30.0,
    ),
    "gpt-4o": ModelPricing(
        model_name="gpt-4o",
        input_price_per_million=5.0,
        output_price_per_million=15.0,
    ),
    "gpt-4o-mini": ModelPricing(
        model_name="gpt-4o-mini",
        input_price_per_million=0.15,
        output_price_per_million=0.60,
    ),
    # Default fallback
    "default": ModelPricing(
        model_name="default",
        input_price_per_million=1.0,
        output_price_per_million=3.0,
    ),
}


@dataclass
class StepCost:
    """Cost breakdown for a single step."""

    step_number: int
    step_name: str
    category: CostCategory
    tokens: TokenUsage = field(default_factory=TokenUsage)
    cost_usd: float = 0.0
    duration_ms: int = 0
    model: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "step_number": self.step_number,
            "step_name": self.step_name,
            "category": self.category.value,
            "tokens": self.tokens.to_dict(),
            "cost_usd": round(self.cost_usd, 6),
            "duration_ms": self.duration_ms,
            "model": self.model,
        }


@dataclass
class CostReport:
    """Complete cost report for a grimoire execution."""

    grimoire_id: str
    finding_id: str = ""
    started_at: str = ""
    completed_at: str = ""

    # Aggregated costs
    total_cost_usd: float = 0.0
    total_tokens: TokenUsage = field(default_factory=TokenUsage)

    # Per-step costs
    step_costs: List[StepCost] = field(default_factory=list)

    # Budget tracking
    budget_usd: Optional[float] = None
    budget_exceeded: bool = False
    budget_remaining: float = 0.0

    # Cost by category
    cost_by_category: Dict[str, float] = field(default_factory=dict)

    def add_step_cost(self, cost: StepCost) -> None:
        """Add a step cost to the report.

        Args:
            cost: Step cost to add
        """
        self.step_costs.append(cost)
        self.total_cost_usd += cost.cost_usd
        self.total_tokens = self.total_tokens.add(cost.tokens)

        # Update category breakdown
        category = cost.category.value
        if category not in self.cost_by_category:
            self.cost_by_category[category] = 0.0
        self.cost_by_category[category] += cost.cost_usd

        # Check budget
        if self.budget_usd is not None:
            self.budget_remaining = self.budget_usd - self.total_cost_usd
            self.budget_exceeded = self.total_cost_usd > self.budget_usd

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "grimoire_id": self.grimoire_id,
            "finding_id": self.finding_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "total_tokens": self.total_tokens.to_dict(),
            "step_costs": [s.to_dict() for s in self.step_costs],
            "budget_usd": self.budget_usd,
            "budget_exceeded": self.budget_exceeded,
            "budget_remaining": round(self.budget_remaining, 6) if self.budget_usd else None,
            "cost_by_category": {k: round(v, 6) for k, v in self.cost_by_category.items()},
        }

    def to_summary(self) -> str:
        """Generate human-readable cost summary."""
        lines = [
            f"Cost Report: {self.grimoire_id}",
            f"Finding: {self.finding_id}" if self.finding_id else "",
            "",
            f"Total Cost: ${self.total_cost_usd:.4f}",
            f"Total Tokens: {self.total_tokens.total_tokens:,}",
            f"  Input: {self.total_tokens.input_tokens:,}",
            f"  Output: {self.total_tokens.output_tokens:,}",
            f"  Cached: {self.total_tokens.cached_tokens:,}",
            "",
        ]

        if self.budget_usd is not None:
            status = "EXCEEDED" if self.budget_exceeded else "OK"
            lines.extend([
                f"Budget: ${self.budget_usd:.4f} ({status})",
                f"Remaining: ${self.budget_remaining:.4f}",
                "",
            ])

        if self.cost_by_category:
            lines.append("Cost by Category:")
            for category, cost in sorted(self.cost_by_category.items()):
                lines.append(f"  {category}: ${cost:.4f}")
            lines.append("")

        if self.step_costs:
            lines.append("Step Costs:")
            for step in self.step_costs:
                lines.append(
                    f"  {step.step_number}. {step.step_name}: "
                    f"${step.cost_usd:.4f} ({step.tokens.total_tokens:,} tokens)"
                )

        return "\n".join(line for line in lines if line is not None)


class CostTracker:
    """Tracks costs during grimoire execution.

    Example:
        tracker = CostTracker(
            grimoire_id="grimoire-reentrancy",
            budget_usd=2.0,
        )

        # Track LLM costs
        tracker.track_llm_cost(
            step_number=1,
            step_name="Analyze",
            tokens=TokenUsage(input_tokens=1000, output_tokens=500),
            model="claude-3-haiku",
        )

        # Get report
        report = tracker.get_report()
        print(report.to_summary())
    """

    def __init__(
        self,
        grimoire_id: str,
        finding_id: str = "",
        budget_usd: Optional[float] = None,
        pricing: Optional[Dict[str, ModelPricing]] = None,
    ) -> None:
        """Initialize cost tracker.

        Args:
            grimoire_id: ID of grimoire being executed
            finding_id: Optional finding ID
            budget_usd: Optional budget limit in USD
            pricing: Optional custom pricing (uses DEFAULT_PRICING if not provided)
        """
        self.grimoire_id = grimoire_id
        self.finding_id = finding_id
        self.budget_usd = budget_usd
        self.pricing = pricing or DEFAULT_PRICING
        self.started_at = datetime.utcnow().isoformat()

        self._report = CostReport(
            grimoire_id=grimoire_id,
            finding_id=finding_id,
            started_at=self.started_at,
            budget_usd=budget_usd,
            budget_remaining=budget_usd or 0.0,
        )

    def get_pricing(self, model: str) -> ModelPricing:
        """Get pricing for a model.

        Args:
            model: Model name

        Returns:
            ModelPricing for the model
        """
        # Try exact match
        if model in self.pricing:
            return self.pricing[model]

        # Try partial match (e.g., "claude-3-haiku-20241022" -> "claude-3-haiku")
        for key, pricing in self.pricing.items():
            if key in model or model in key:
                return pricing

        # Fall back to default
        return self.pricing.get("default", DEFAULT_PRICING["default"])

    def track_llm_cost(
        self,
        step_number: int,
        step_name: str,
        tokens: TokenUsage,
        model: str = "default",
        duration_ms: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StepCost:
        """Track cost for an LLM operation.

        Args:
            step_number: Step number
            step_name: Step name
            tokens: Token usage
            model: Model name for pricing
            duration_ms: Duration in milliseconds
            metadata: Optional metadata

        Returns:
            StepCost that was recorded
        """
        pricing = self.get_pricing(model)
        cost_usd = pricing.calculate_cost(tokens)

        step_cost = StepCost(
            step_number=step_number,
            step_name=step_name,
            category=CostCategory.LLM_TOKENS,
            tokens=tokens,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
            model=model,
            metadata=metadata or {},
        )

        self._report.add_step_cost(step_cost)

        if self._report.budget_exceeded:
            logger.warning(
                f"Budget exceeded for {self.grimoire_id}: "
                f"${self._report.total_cost_usd:.4f} > ${self.budget_usd:.4f}"
            )

        return step_cost

    def track_compute_cost(
        self,
        step_number: int,
        step_name: str,
        cost_usd: float,
        duration_ms: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StepCost:
        """Track cost for a compute operation.

        Args:
            step_number: Step number
            step_name: Step name
            cost_usd: Cost in USD
            duration_ms: Duration in milliseconds
            metadata: Optional metadata

        Returns:
            StepCost that was recorded
        """
        step_cost = StepCost(
            step_number=step_number,
            step_name=step_name,
            category=CostCategory.COMPUTE,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )

        self._report.add_step_cost(step_cost)
        return step_cost

    def track_api_cost(
        self,
        step_number: int,
        step_name: str,
        cost_usd: float,
        api_name: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StepCost:
        """Track cost for an external API call.

        Args:
            step_number: Step number
            step_name: Step name
            cost_usd: Cost in USD
            api_name: Name of API called
            metadata: Optional metadata

        Returns:
            StepCost that was recorded
        """
        step_cost = StepCost(
            step_number=step_number,
            step_name=step_name,
            category=CostCategory.API_CALLS,
            cost_usd=cost_usd,
            metadata={"api_name": api_name, **(metadata or {})},
        )

        self._report.add_step_cost(step_cost)
        return step_cost

    def is_budget_exceeded(self) -> bool:
        """Check if budget has been exceeded.

        Returns:
            True if budget is set and exceeded
        """
        return self._report.budget_exceeded

    def get_remaining_budget(self) -> Optional[float]:
        """Get remaining budget.

        Returns:
            Remaining budget in USD, or None if no budget set
        """
        if self.budget_usd is None:
            return None
        return self._report.budget_remaining

    def get_total_cost(self) -> float:
        """Get total cost so far.

        Returns:
            Total cost in USD
        """
        return self._report.total_cost_usd

    def get_report(self) -> CostReport:
        """Get the complete cost report.

        Returns:
            CostReport with all tracked costs
        """
        self._report.completed_at = datetime.utcnow().isoformat()
        return self._report


class BudgetExceededError(Exception):
    """Raised when grimoire execution exceeds budget."""

    def __init__(self, budget: float, spent: float, grimoire_id: str):
        self.budget = budget
        self.spent = spent
        self.grimoire_id = grimoire_id
        super().__init__(
            f"Budget exceeded for {grimoire_id}: "
            f"${spent:.4f} > ${budget:.4f}"
        )


def create_cost_tracker(
    grimoire_id: str,
    finding_id: str = "",
    budget_usd: Optional[float] = None,
) -> CostTracker:
    """Create a new cost tracker.

    Convenience function for creating trackers.

    Args:
        grimoire_id: Grimoire ID
        finding_id: Optional finding ID
        budget_usd: Optional budget limit

    Returns:
        New CostTracker instance
    """
    return CostTracker(
        grimoire_id=grimoire_id,
        finding_id=finding_id,
        budget_usd=budget_usd,
    )
