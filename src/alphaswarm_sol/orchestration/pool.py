"""Pool storage and management for the orchestration layer.

This module provides persistent storage and management for Pool objects.
Follows patterns from src/alphaswarm_sol/beads/storage.py.

Storage Structure:
    .vrs/pools/
    ├── pool-abc123.yaml       # Pool manifest
    ├── pool-def456.yaml
    └── ...

Usage:
    from alphaswarm_sol.orchestration.pool import PoolStorage, PoolManager

    # Storage - direct file operations
    storage = PoolStorage(Path(".vrs/pools"))
    storage.save_pool(pool)
    pool = storage.get_pool("pool-abc123")

    # Manager - higher-level operations
    manager = PoolManager(Path(".vrs/pools"))
    pool = manager.create_pool(scope, initiated_by="/vkg:audit")
    manager.add_bead(pool.id, "VKG-042")
    manager.record_verdict(pool.id, verdict)
    manager.advance_phase(pool.id)

    # Budget-aware pool management
    manager = PoolManager(Path(".vrs/pools"))
    pool = manager.create_pool_with_budget(
        scope=Scope(files=["contracts/Vault.sol"]),
        budget_usd=10.0,
        hard_limit=True
    )
    manager.record_cost(pool.id, "vrs-attacker", "claude-3-5-sonnet", 1000, 500)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable

import yaml

from .schemas import Pool, PoolStatus, Scope, Verdict, VerdictConfidence
from ..metrics.cost_ledger import (
    CostLedger,
    PoolBudget,
    PoolCostSummary,
    PoolBudgetExceededError,
)

logger = logging.getLogger(__name__)


class PoolStorage:
    """File-based storage for Pool objects.

    Stores pools as YAML files in a directory. Each pool is saved
    as {pool_id}.yaml for human readability.

    Example:
        storage = PoolStorage(Path(".vrs/pools"))
        storage.save_pool(pool)
        loaded = storage.get_pool(pool.id)
    """

    def __init__(self, path: Path):
        """Initialize storage.

        Args:
            path: Directory path for storing pools.
                  Will be created if it doesn't exist.
        """
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)

    def save_pool(self, pool: Pool) -> Path:
        """Save a pool to storage.

        Args:
            pool: Pool to save

        Returns:
            Path to saved file
        """
        pool_path = self.path / f"{pool.id}.yaml"
        with open(pool_path, "w", encoding="utf-8") as f:
            yaml.dump(pool.to_dict(), f, default_flow_style=False, sort_keys=False)
        return pool_path

    def get_pool(self, pool_id: str) -> Optional[Pool]:
        """Load a pool by ID.

        Args:
            pool_id: Unique pool identifier

        Returns:
            Pool if found, None otherwise
        """
        pool_path = self.path / f"{pool_id}.yaml"
        if not pool_path.exists():
            return None

        with open(pool_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return Pool.from_dict(data)

    def list_pools(self) -> List[Pool]:
        """List all pools in storage.

        Returns:
            List of all Pool objects
        """
        pools = []
        for path in sorted(self.path.glob("*.yaml")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                pools.append(Pool.from_dict(data))
            except (yaml.YAMLError, KeyError) as e:
                # Skip corrupted files
                import sys
                print(f"Warning: Skipping corrupted pool file {path}: {e}", file=sys.stderr)
        return pools

    def list_pools_by_status(self, status: PoolStatus) -> List[Pool]:
        """List pools filtered by status.

        Args:
            status: PoolStatus to filter by

        Returns:
            List of matching Pool objects
        """
        all_pools = self.list_pools()
        return [p for p in all_pools if p.status == status]

    def list_active_pools(self) -> List[Pool]:
        """List pools that are actively processing.

        Returns:
            List of Pool objects with active status
        """
        all_pools = self.list_pools()
        return [p for p in all_pools if p.is_active]

    def delete_pool(self, pool_id: str) -> bool:
        """Delete a pool from storage.

        Args:
            pool_id: Unique pool identifier

        Returns:
            True if deleted, False if not found
        """
        pool_path = self.path / f"{pool_id}.yaml"
        if pool_path.exists():
            pool_path.unlink()
            return True
        return False

    def clear(self) -> int:
        """Clear all pools from storage.

        Returns:
            Count of pools deleted
        """
        count = 0
        for path in self.path.glob("*.yaml"):
            path.unlink()
            count += 1
        return count

    def count(self) -> int:
        """Count pools in storage.

        Returns:
            Total number of pools
        """
        return len(list(self.path.glob("*.yaml")))

    def exists(self, pool_id: str) -> bool:
        """Check if a pool exists.

        Args:
            pool_id: Unique pool identifier

        Returns:
            True if pool exists
        """
        pool_path = self.path / f"{pool_id}.yaml"
        return pool_path.exists()

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics.

        Returns:
            Dict with counts by status and aggregate metrics
        """
        pools = self.list_pools()

        by_status: Dict[str, int] = {}
        total_beads = 0
        total_verdicts = 0
        vulnerable_count = 0

        for pool in pools:
            # Count by status
            status = pool.status.value
            by_status[status] = by_status.get(status, 0) + 1

            # Aggregate metrics
            total_beads += len(pool.bead_ids)
            total_verdicts += len(pool.verdicts)
            vulnerable_count += pool.vulnerable_count

        return {
            "total_pools": len(pools),
            "by_status": by_status,
            "total_beads": total_beads,
            "total_verdicts": total_verdicts,
            "vulnerable_count": vulnerable_count,
        }


class PoolManager:
    """High-level pool management operations.

    Provides convenient methods for common pool operations, wrapping
    the underlying storage layer. Supports budget enforcement and cost tracking.

    Example:
        manager = PoolManager(Path(".vrs/pools"))
        pool = manager.create_pool(
            scope=Scope(files=["contracts/Vault.sol"]),
            initiated_by="/vkg:audit"
        )
        manager.add_bead(pool.id, "VKG-042")
        manager.record_verdict(pool.id, verdict)
        manager.advance_phase(pool.id)

    Budget-aware example:
        manager = PoolManager(Path(".vrs/pools"))
        pool = manager.create_pool_with_budget(
            scope=Scope(files=["contracts/Vault.sol"]),
            budget_usd=10.0
        )
        # This will raise PoolBudgetExceededError if budget exceeded
        manager.record_cost(pool.id, "vrs-attacker", "claude-3-5-sonnet", 1000, 500)
    """

    def __init__(self, storage_path: Path):
        """Initialize manager with storage path.

        Args:
            storage_path: Path for pool storage
        """
        self.storage = PoolStorage(storage_path)
        self._cost_ledgers: Dict[str, CostLedger] = {}

    def create_pool(
        self,
        scope: Scope,
        pool_id: Optional[str] = None,
        initiated_by: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Pool:
        """Create a new pool from scope.

        Args:
            scope: Audit scope definition
            pool_id: Optional custom ID (auto-generated if not provided)
            initiated_by: What triggered pool creation
            metadata: Optional metadata

        Returns:
            Created Pool object
        """
        pool = Pool(
            id=pool_id or "",  # Empty triggers auto-generation
            scope=scope,
            initiated_by=initiated_by,
            metadata=metadata or {},
        )
        self.storage.save_pool(pool)
        return pool

    def get_pool(self, pool_id: str) -> Optional[Pool]:
        """Get a pool by ID.

        Args:
            pool_id: Pool identifier

        Returns:
            Pool if found, None otherwise
        """
        return self.storage.get_pool(pool_id)

    def add_bead(self, pool_id: str, bead_id: str) -> bool:
        """Add a bead to a pool.

        Args:
            pool_id: Pool identifier
            bead_id: Bead identifier to add

        Returns:
            True if added successfully, False if pool not found
        """
        pool = self.storage.get_pool(pool_id)
        if pool is None:
            return False

        pool.add_bead(bead_id)
        self.storage.save_pool(pool)
        return True

    def add_beads(self, pool_id: str, bead_ids: List[str]) -> bool:
        """Add multiple beads to a pool.

        Args:
            pool_id: Pool identifier
            bead_ids: List of bead identifiers to add

        Returns:
            True if added successfully, False if pool not found
        """
        pool = self.storage.get_pool(pool_id)
        if pool is None:
            return False

        for bead_id in bead_ids:
            pool.add_bead(bead_id)
        self.storage.save_pool(pool)
        return True

    def remove_bead(self, pool_id: str, bead_id: str) -> bool:
        """Remove a bead from a pool.

        Args:
            pool_id: Pool identifier
            bead_id: Bead identifier to remove

        Returns:
            True if removed, False if pool not found or bead not in pool
        """
        pool = self.storage.get_pool(pool_id)
        if pool is None:
            return False

        if pool.remove_bead(bead_id):
            self.storage.save_pool(pool)
            return True
        return False

    def record_verdict(self, pool_id: str, verdict: Verdict) -> bool:
        """Record a verdict for a finding in a pool.

        Args:
            pool_id: Pool identifier
            verdict: Verdict to record

        Returns:
            True if recorded, False if pool not found
        """
        pool = self.storage.get_pool(pool_id)
        if pool is None:
            return False

        pool.record_verdict(verdict)
        self.storage.save_pool(pool)
        return True

    def advance_phase(self, pool_id: str) -> Optional[PoolStatus]:
        """Advance pool to next phase.

        Args:
            pool_id: Pool identifier

        Returns:
            New status if advanced, None if pool not found or terminal
        """
        pool = self.storage.get_pool(pool_id)
        if pool is None:
            return None

        if pool.advance_phase():
            self.storage.save_pool(pool)
            return pool.status
        return None

    def set_status(self, pool_id: str, status: PoolStatus) -> bool:
        """Set pool status directly.

        Args:
            pool_id: Pool identifier
            status: New status

        Returns:
            True if updated, False if pool not found
        """
        pool = self.storage.get_pool(pool_id)
        if pool is None:
            return False

        pool.set_status(status)
        self.storage.save_pool(pool)
        return True

    def fail_pool(self, pool_id: str, reason: str = "") -> bool:
        """Mark pool as failed.

        Args:
            pool_id: Pool identifier
            reason: Failure reason

        Returns:
            True if updated, False if pool not found
        """
        pool = self.storage.get_pool(pool_id)
        if pool is None:
            return False

        pool.fail(reason)
        self.storage.save_pool(pool)
        return True

    def pause_pool(self, pool_id: str, reason: str = "") -> bool:
        """Pause pool for human input.

        Args:
            pool_id: Pool identifier
            reason: Pause reason

        Returns:
            True if paused, False if pool not found
        """
        pool = self.storage.get_pool(pool_id)
        if pool is None:
            return False

        pool.pause(reason)
        self.storage.save_pool(pool)
        return True

    def resume_pool(self, pool_id: str) -> bool:
        """Resume pool from paused state.

        Args:
            pool_id: Pool identifier

        Returns:
            True if resumed, False if pool not found
        """
        pool = self.storage.get_pool(pool_id)
        if pool is None:
            return False

        pool.resume()
        self.storage.save_pool(pool)
        return True

    def get_pending_beads(self, pool_id: str) -> List[str]:
        """Get beads without verdicts.

        Args:
            pool_id: Pool identifier

        Returns:
            List of bead IDs without verdicts, empty if pool not found
        """
        pool = self.storage.get_pool(pool_id)
        if pool is None:
            return []
        return pool.pending_beads

    def get_pools_by_status(self, status: PoolStatus) -> List[Pool]:
        """Get pools filtered by status.

        Args:
            status: Status to filter by

        Returns:
            List of matching pools
        """
        return self.storage.list_pools_by_status(status)

    def get_active_pools(self) -> List[Pool]:
        """Get actively processing pools.

        Returns:
            List of pools with active status
        """
        return self.storage.list_active_pools()

    def delete_pool(self, pool_id: str) -> bool:
        """Delete a pool.

        Args:
            pool_id: Pool identifier

        Returns:
            True if deleted, False if not found
        """
        return self.storage.delete_pool(pool_id)

    def update_pool(
        self,
        pool_id: str,
        updater: Callable[[Pool], None],
    ) -> bool:
        """Update a pool with a custom function.

        Args:
            pool_id: Pool identifier
            updater: Function that modifies the pool

        Returns:
            True if updated, False if pool not found
        """
        pool = self.storage.get_pool(pool_id)
        if pool is None:
            return False

        updater(pool)
        self.storage.save_pool(pool)
        return True

    # =========================================================================
    # Budget and Cost Management
    # =========================================================================

    def create_pool_with_budget(
        self,
        scope: Scope,
        budget_usd: float,
        pool_id: Optional[str] = None,
        initiated_by: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        hard_limit: bool = True,
        warn_threshold_pct: float = 80.0,
    ) -> Pool:
        """Create a pool with budget enforcement.

        Args:
            scope: Audit scope definition
            budget_usd: Maximum cost for this pool in USD
            pool_id: Optional custom ID
            initiated_by: What triggered pool creation
            metadata: Optional metadata
            hard_limit: If True, raises error on budget exceeded
            warn_threshold_pct: Percentage at which to issue warnings

        Returns:
            Created Pool object with budget configured
        """
        pool = self.create_pool(
            scope=scope,
            pool_id=pool_id,
            initiated_by=initiated_by,
            metadata=metadata,
        )

        # Store budget info in pool metadata
        pool.metadata["budget"] = {
            "max_cost_usd": budget_usd,
            "warn_threshold_pct": warn_threshold_pct,
            "hard_limit": hard_limit,
        }
        self.storage.save_pool(pool)

        # Create cost ledger for this pool
        budget = PoolBudget(
            max_cost_usd=budget_usd,
            warn_threshold_pct=warn_threshold_pct,
            hard_limit=hard_limit,
        )
        self._cost_ledgers[pool.id] = CostLedger(pool_id=pool.id, budget=budget)

        return pool

    def get_cost_ledger(self, pool_id: str) -> Optional[CostLedger]:
        """Get the cost ledger for a pool.

        Args:
            pool_id: Pool identifier

        Returns:
            CostLedger if exists, None otherwise
        """
        # Check memory cache first
        if pool_id in self._cost_ledgers:
            return self._cost_ledgers[pool_id]

        # Try to restore from pool metadata
        pool = self.storage.get_pool(pool_id)
        if pool is None:
            return None

        budget_data = pool.metadata.get("budget")
        if budget_data:
            budget = PoolBudget.from_dict(budget_data)
            ledger = CostLedger(pool_id=pool_id, budget=budget)
            self._cost_ledgers[pool_id] = ledger
            return ledger

        # No budget configured, return unbounded ledger
        ledger = CostLedger(pool_id=pool_id)
        self._cost_ledgers[pool_id] = ledger
        return ledger

    def record_cost(
        self,
        pool_id: str,
        agent_type: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        bead_id: Optional[str] = None,
        operation: Optional[str] = None,
    ) -> bool:
        """Record a cost entry for a pool.

        Args:
            pool_id: Pool identifier
            agent_type: Type of agent
            model: Model used
            input_tokens: Input tokens consumed
            output_tokens: Output tokens generated
            bead_id: Optional bead ID for attribution
            operation: Optional operation description

        Returns:
            True if recorded successfully

        Raises:
            PoolBudgetExceededError: If budget exceeded in hard limit mode
        """
        ledger = self.get_cost_ledger(pool_id)
        if ledger is None:
            return False

        try:
            ledger.record(
                agent_type=agent_type,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                bead_id=bead_id,
                operation=operation,
            )
            return True
        except PoolBudgetExceededError:
            # Re-raise to let caller handle
            raise

    def check_budget(
        self,
        pool_id: str,
        estimated_cost: float = 0.0,
    ) -> tuple[bool, str]:
        """Check if a pool has budget for an operation.

        Args:
            pool_id: Pool identifier
            estimated_cost: Estimated cost of upcoming operation

        Returns:
            Tuple of (allowed, message)
        """
        ledger = self.get_cost_ledger(pool_id)
        if ledger is None:
            return True, ""  # No ledger means no budget constraints

        return ledger.check_budget(estimated_cost)

    def can_afford(self, pool_id: str, estimated_cost: float) -> bool:
        """Check if pool can afford an estimated cost.

        Args:
            pool_id: Pool identifier
            estimated_cost: Estimated cost in USD

        Returns:
            True if within budget
        """
        ledger = self.get_cost_ledger(pool_id)
        if ledger is None:
            return True
        return ledger.can_afford(estimated_cost)

    def get_cost_summary(self, pool_id: str) -> Optional[PoolCostSummary]:
        """Get cost summary for a pool.

        Args:
            pool_id: Pool identifier

        Returns:
            PoolCostSummary if ledger exists, None otherwise
        """
        ledger = self.get_cost_ledger(pool_id)
        if ledger is None:
            return None
        return ledger.summary()

    def get_all_cost_summaries(self) -> List[PoolCostSummary]:
        """Get cost summaries for all tracked pools.

        Returns:
            List of PoolCostSummary objects
        """
        return [ledger.summary() for ledger in self._cost_ledgers.values()]

    def set_pool_budget(
        self,
        pool_id: str,
        budget_usd: float,
        hard_limit: bool = True,
        warn_threshold_pct: float = 80.0,
    ) -> bool:
        """Set or update budget for an existing pool.

        Args:
            pool_id: Pool identifier
            budget_usd: Maximum cost in USD
            hard_limit: If True, raises error on budget exceeded
            warn_threshold_pct: Warning threshold percentage

        Returns:
            True if updated, False if pool not found
        """
        pool = self.storage.get_pool(pool_id)
        if pool is None:
            return False

        # Update pool metadata
        pool.metadata["budget"] = {
            "max_cost_usd": budget_usd,
            "warn_threshold_pct": warn_threshold_pct,
            "hard_limit": hard_limit,
        }
        self.storage.save_pool(pool)

        # Update or create ledger
        budget = PoolBudget(
            max_cost_usd=budget_usd,
            warn_threshold_pct=warn_threshold_pct,
            hard_limit=hard_limit,
        )

        if pool_id in self._cost_ledgers:
            # Update existing ledger's budget
            self._cost_ledgers[pool_id].budget = budget
        else:
            # Create new ledger
            self._cost_ledgers[pool_id] = CostLedger(pool_id=pool_id, budget=budget)

        return True

    def fail_pool_on_budget(self, pool_id: str) -> bool:
        """Mark pool as failed due to budget exceeded.

        Args:
            pool_id: Pool identifier

        Returns:
            True if updated, False if pool not found
        """
        pool = self.storage.get_pool(pool_id)
        if pool is None:
            return False

        summary = self.get_cost_summary(pool_id)
        reason = "Budget exceeded"
        if summary:
            reason = (
                f"Budget exceeded: ${summary.total_cost_usd:.2f} > "
                f"${summary.budget_max_usd:.2f}"
            )

        pool.fail(reason)
        self.storage.save_pool(pool)
        return True


# Export for module
__all__ = [
    "PoolStorage",
    "PoolManager",
    "PoolBudgetExceededError",
]
