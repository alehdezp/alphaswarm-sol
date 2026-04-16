"""Pool-scoped cost ledger for tracking per-pool spend and token usage.

This module provides cost tracking scoped to pools and beads, enabling:
- Per-pool spend tracking with budget enforcement
- Per-bead cost attribution
- Agent-level cost breakdown
- Dashboard-ready aggregation helpers

Integrates with:
- alphaswarm_sol.agents.cost: Low-level cost calculation
- alphaswarm_sol.llm.limits: LLMLimits hard/soft enforcement behavior
- alphaswarm_sol.orchestration.pool: Pool lifecycle management

Usage:
    from alphaswarm_sol.metrics.cost_ledger import CostLedger, PoolBudget

    # Create ledger with pool budget
    ledger = CostLedger(
        pool_id="pool-abc123",
        budget=PoolBudget(max_cost_usd=10.0, hard_limit=True)
    )

    # Record usage
    ledger.record(
        agent_type="vrs-attacker",
        model="claude-3-5-sonnet",
        input_tokens=1000,
        output_tokens=500,
        bead_id="VKG-042"
    )

    # Get summary
    summary = ledger.summary()
    print(f"Total spend: ${summary.total_cost_usd:.2f}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost for token usage.

    This is a local implementation to avoid circular imports with agents.cost.
    Uses the same pricing structure.

    Args:
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Cost in USD
    """
    # Token pricing per model (USD per 1M tokens) - matches agents/cost.py
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

    pricing = TOKEN_PRICING.get(model, TOKEN_PRICING["default"])
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost


class PoolBudgetExceededError(Exception):
    """Raised when a pool exceeds its budget (hard limit mode)."""

    def __init__(
        self,
        message: str,
        pool_id: str,
        budget_usd: float,
        spent_usd: float,
        requested_usd: float,
    ):
        super().__init__(message)
        self.pool_id = pool_id
        self.budget_usd = budget_usd
        self.spent_usd = spent_usd
        self.requested_usd = requested_usd


@dataclass
class PoolBudget:
    """Budget configuration for a pool.

    Attributes:
        max_cost_usd: Maximum cost allowed for the pool
        warn_threshold_pct: Percentage at which to issue warnings (0-100)
        hard_limit: If True, raises error on budget exceeded; if False, warns only
    """

    max_cost_usd: float = 5.00
    warn_threshold_pct: float = 80.0
    hard_limit: bool = True

    @property
    def warn_cost_usd(self) -> float:
        """Cost threshold for warnings."""
        return self.max_cost_usd * (self.warn_threshold_pct / 100.0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "max_cost_usd": self.max_cost_usd,
            "warn_threshold_pct": self.warn_threshold_pct,
            "hard_limit": self.hard_limit,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PoolBudget":
        """Create from dictionary."""
        return cls(
            max_cost_usd=float(data.get("max_cost_usd", 5.00)),
            warn_threshold_pct=float(data.get("warn_threshold_pct", 80.0)),
            hard_limit=bool(data.get("hard_limit", True)),
        )


@dataclass
class CostEntry:
    """Single cost entry in the ledger.

    Attributes:
        timestamp: When the cost was incurred
        agent_type: Type of agent (e.g., "vrs-attacker", "vrs-defender")
        model: Model used
        input_tokens: Input tokens consumed
        output_tokens: Output tokens generated
        cost_usd: Calculated cost in USD
        pool_id: Pool this entry belongs to
        bead_id: Optional bead ID for attribution
        operation: Optional operation description
    """

    timestamp: datetime
    agent_type: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    pool_id: str
    bead_id: Optional[str] = None
    operation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "agent_type": self.agent_type,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "pool_id": self.pool_id,
            "bead_id": self.bead_id,
            "operation": self.operation,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CostEntry":
        """Create from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        else:
            timestamp = datetime.now()

        return cls(
            timestamp=timestamp,
            agent_type=str(data.get("agent_type", "")),
            model=str(data.get("model", "default")),
            input_tokens=int(data.get("input_tokens", 0)),
            output_tokens=int(data.get("output_tokens", 0)),
            cost_usd=float(data.get("cost_usd", 0.0)),
            pool_id=str(data.get("pool_id", "")),
            bead_id=data.get("bead_id"),
            operation=data.get("operation"),
        )


@dataclass
class PoolCostSummary:
    """Aggregated cost summary for a pool.

    Attributes:
        pool_id: Pool identifier
        total_cost_usd: Total cost incurred
        total_input_tokens: Total input tokens
        total_output_tokens: Total output tokens
        total_requests: Number of LLM requests
        cost_by_agent: Cost breakdown by agent type
        cost_by_bead: Cost breakdown by bead ID
        cost_by_model: Cost breakdown by model
        budget_max_usd: Budget limit (if set)
        budget_remaining_usd: Remaining budget (if set)
        budget_utilization_pct: Budget utilization percentage
        warnings: Any budget warnings issued
    """

    pool_id: str
    total_cost_usd: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_requests: int = 0
    cost_by_agent: Dict[str, float] = field(default_factory=dict)
    cost_by_bead: Dict[str, float] = field(default_factory=dict)
    cost_by_model: Dict[str, float] = field(default_factory=dict)
    budget_max_usd: Optional[float] = None
    budget_remaining_usd: Optional[float] = None
    budget_utilization_pct: Optional[float] = None
    warnings: List[str] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        """Total tokens (input + output)."""
        return self.total_input_tokens + self.total_output_tokens

    @property
    def avg_cost_per_request(self) -> float:
        """Average cost per request."""
        if self.total_requests == 0:
            return 0.0
        return self.total_cost_usd / self.total_requests

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pool_id": self.pool_id,
            "total_cost_usd": round(self.total_cost_usd, 4),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "total_requests": self.total_requests,
            "avg_cost_per_request": round(self.avg_cost_per_request, 4),
            "cost_by_agent": {k: round(v, 4) for k, v in self.cost_by_agent.items()},
            "cost_by_bead": {k: round(v, 4) for k, v in self.cost_by_bead.items()},
            "cost_by_model": {k: round(v, 4) for k, v in self.cost_by_model.items()},
            "budget_max_usd": self.budget_max_usd,
            "budget_remaining_usd": (
                round(self.budget_remaining_usd, 4)
                if self.budget_remaining_usd is not None
                else None
            ),
            "budget_utilization_pct": (
                round(self.budget_utilization_pct, 1)
                if self.budget_utilization_pct is not None
                else None
            ),
            "warnings": self.warnings,
        }


class CostLedger:
    """Pool-scoped cost ledger for tracking spend and enforcing budgets.

    Tracks all cost entries for a pool with optional budget enforcement.
    Provides aggregation helpers for dashboard rendering.

    Example:
        ledger = CostLedger(
            pool_id="pool-abc123",
            budget=PoolBudget(max_cost_usd=10.0)
        )

        # Record usage
        ledger.record(
            agent_type="vrs-attacker",
            model="claude-3-5-sonnet",
            input_tokens=1000,
            output_tokens=500,
            bead_id="VKG-042"
        )

        # Check budget
        if not ledger.can_afford(estimated_cost=0.50):
            print("Insufficient budget")

        # Get summary for dashboard
        summary = ledger.summary()
    """

    def __init__(
        self,
        pool_id: str,
        budget: Optional[PoolBudget] = None,
    ):
        """Initialize cost ledger.

        Args:
            pool_id: Pool identifier for this ledger
            budget: Optional budget configuration
        """
        self.pool_id = pool_id
        self.budget = budget
        self._entries: List[CostEntry] = []
        self._warnings: List[str] = []
        self._warn_threshold_crossed = False

    @property
    def total_cost(self) -> float:
        """Total cost so far."""
        return sum(e.cost_usd for e in self._entries)

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return sum(e.input_tokens + e.output_tokens for e in self._entries)

    @property
    def remaining_budget(self) -> Optional[float]:
        """Remaining budget if set."""
        if self.budget is None:
            return None
        return max(0.0, self.budget.max_cost_usd - self.total_cost)

    @property
    def budget_utilization_pct(self) -> Optional[float]:
        """Budget utilization percentage."""
        if self.budget is None or self.budget.max_cost_usd == 0:
            return None
        return (self.total_cost / self.budget.max_cost_usd) * 100.0

    def record(
        self,
        agent_type: str,
        model: str = "default",
        input_tokens: int = 0,
        output_tokens: int = 0,
        bead_id: Optional[str] = None,
        operation: Optional[str] = None,
    ) -> CostEntry:
        """Record a cost entry.

        Args:
            agent_type: Type of agent
            model: Model used
            input_tokens: Input tokens consumed
            output_tokens: Output tokens generated
            bead_id: Optional bead ID for attribution
            operation: Optional operation description

        Returns:
            The created CostEntry

        Raises:
            PoolBudgetExceededError: If budget exceeded in hard limit mode
        """
        cost = _calculate_cost(model, input_tokens, output_tokens)

        # Check budget before recording
        if self.budget is not None:
            new_total = self.total_cost + cost

            # Check for budget exceeded
            if new_total > self.budget.max_cost_usd:
                if self.budget.hard_limit:
                    raise PoolBudgetExceededError(
                        f"Pool {self.pool_id} budget exceeded: "
                        f"${new_total:.2f} > ${self.budget.max_cost_usd:.2f}",
                        pool_id=self.pool_id,
                        budget_usd=self.budget.max_cost_usd,
                        spent_usd=self.total_cost,
                        requested_usd=cost,
                    )
                else:
                    warning = (
                        f"Pool {self.pool_id} budget exceeded (soft): "
                        f"${new_total:.2f} > ${self.budget.max_cost_usd:.2f}"
                    )
                    self._warnings.append(warning)
                    logger.warning(warning)

            # Check for warning threshold
            elif (
                new_total >= self.budget.warn_cost_usd
                and not self._warn_threshold_crossed
            ):
                self._warn_threshold_crossed = True
                warning = (
                    f"Pool {self.pool_id} approaching budget: "
                    f"${new_total:.2f} ({self.budget.warn_threshold_pct}% of "
                    f"${self.budget.max_cost_usd:.2f})"
                )
                self._warnings.append(warning)
                logger.warning(warning)

        entry = CostEntry(
            timestamp=datetime.now(),
            agent_type=agent_type,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            pool_id=self.pool_id,
            bead_id=bead_id,
            operation=operation,
        )

        self._entries.append(entry)
        return entry

    def can_afford(self, estimated_cost: float) -> bool:
        """Check if estimated cost is within budget.

        Args:
            estimated_cost: Estimated cost in USD

        Returns:
            True if within budget (or no budget set)
        """
        if self.budget is None:
            return True
        return self.total_cost + estimated_cost <= self.budget.max_cost_usd

    def check_budget(self, estimated_cost: float = 0.0) -> tuple[bool, str]:
        """Check budget status before operation.

        Args:
            estimated_cost: Estimated cost of upcoming operation

        Returns:
            Tuple of (allowed, message)
        """
        if self.budget is None:
            return True, ""

        projected = self.total_cost + estimated_cost
        if projected > self.budget.max_cost_usd:
            return False, (
                f"Budget exceeded: ${projected:.2f} > ${self.budget.max_cost_usd:.2f}"
            )
        return True, ""

    def summary(self) -> PoolCostSummary:
        """Generate cost summary for this pool.

        Returns:
            PoolCostSummary with aggregated metrics
        """
        if not self._entries:
            return PoolCostSummary(
                pool_id=self.pool_id,
                budget_max_usd=self.budget.max_cost_usd if self.budget else None,
                budget_remaining_usd=self.remaining_budget,
                warnings=self._warnings.copy(),
            )

        total_input = sum(e.input_tokens for e in self._entries)
        total_output = sum(e.output_tokens for e in self._entries)
        total_cost = sum(e.cost_usd for e in self._entries)

        # Cost by agent type
        cost_by_agent: Dict[str, float] = {}
        for e in self._entries:
            cost_by_agent[e.agent_type] = (
                cost_by_agent.get(e.agent_type, 0) + e.cost_usd
            )

        # Cost by bead
        cost_by_bead: Dict[str, float] = {}
        for e in self._entries:
            if e.bead_id:
                cost_by_bead[e.bead_id] = cost_by_bead.get(e.bead_id, 0) + e.cost_usd

        # Cost by model
        cost_by_model: Dict[str, float] = {}
        for e in self._entries:
            cost_by_model[e.model] = cost_by_model.get(e.model, 0) + e.cost_usd

        return PoolCostSummary(
            pool_id=self.pool_id,
            total_cost_usd=total_cost,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_requests=len(self._entries),
            cost_by_agent=cost_by_agent,
            cost_by_bead=cost_by_bead,
            cost_by_model=cost_by_model,
            budget_max_usd=self.budget.max_cost_usd if self.budget else None,
            budget_remaining_usd=self.remaining_budget,
            budget_utilization_pct=self.budget_utilization_pct,
            warnings=self._warnings.copy(),
        )

    def get_entries(self) -> List[CostEntry]:
        """Get all cost entries.

        Returns:
            List of CostEntry objects
        """
        return self._entries.copy()

    def get_entries_for_bead(self, bead_id: str) -> List[CostEntry]:
        """Get entries for a specific bead.

        Args:
            bead_id: Bead identifier

        Returns:
            List of CostEntry objects for this bead
        """
        return [e for e in self._entries if e.bead_id == bead_id]

    def reset(self) -> None:
        """Reset the ledger (clears all entries and warnings)."""
        self._entries = []
        self._warnings = []
        self._warn_threshold_crossed = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize ledger state to dictionary.

        Returns:
            Dictionary representation of the ledger
        """
        return {
            "pool_id": self.pool_id,
            "budget": self.budget.to_dict() if self.budget else None,
            "entries": [e.to_dict() for e in self._entries],
            "warnings": self._warnings,
            "warn_threshold_crossed": self._warn_threshold_crossed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CostLedger":
        """Create ledger from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            CostLedger instance
        """
        budget_data = data.get("budget")
        budget = PoolBudget.from_dict(budget_data) if budget_data else None

        ledger = cls(
            pool_id=str(data.get("pool_id", "")),
            budget=budget,
        )

        # Restore entries
        for entry_data in data.get("entries", []):
            entry = CostEntry.from_dict(entry_data)
            ledger._entries.append(entry)

        # Restore warnings
        ledger._warnings = list(data.get("warnings", []))
        ledger._warn_threshold_crossed = bool(data.get("warn_threshold_crossed", False))

        return ledger


# Global ledger registry for multi-pool tracking
_pool_ledgers: Dict[str, CostLedger] = {}


def get_pool_ledger(
    pool_id: str,
    budget: Optional[PoolBudget] = None,
) -> CostLedger:
    """Get or create a ledger for a pool.

    Args:
        pool_id: Pool identifier
        budget: Optional budget configuration (used only on creation)

    Returns:
        CostLedger for this pool
    """
    if pool_id not in _pool_ledgers:
        _pool_ledgers[pool_id] = CostLedger(pool_id=pool_id, budget=budget)
    return _pool_ledgers[pool_id]


def clear_pool_ledgers() -> None:
    """Clear all pool ledgers (for testing)."""
    global _pool_ledgers
    _pool_ledgers = {}


def get_all_pool_summaries() -> List[PoolCostSummary]:
    """Get summaries for all tracked pools.

    Returns:
        List of PoolCostSummary objects
    """
    return [ledger.summary() for ledger in _pool_ledgers.values()]


__all__ = [
    "CostLedger",
    "CostEntry",
    "PoolBudget",
    "PoolCostSummary",
    "PoolBudgetExceededError",
    "get_pool_ledger",
    "clear_pool_ledgers",
    "get_all_pool_summaries",
]
