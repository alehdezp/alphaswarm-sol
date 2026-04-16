"""Thin routing layer for orchestration (ORCH-01).

The router ONLY:
- Looks at pool status
- Applies simple routing rules
- Returns routing decisions

The router NEVER:
- Analyzes code or findings
- Makes security judgments
- Contains domain logic

Phase 07.1.1-03: Work Queue Integration
    RouteDecision now includes payload_hash for deterministic queueing.
    The hash is computed from action + sorted target_beads for deduplication.

Usage:
    from alphaswarm_sol.orchestration.router import Router, RouteAction, route_pool

    router = Router()
    pool = Pool(id="test", scope=Scope(files=["Vault.sol"]))
    decision = router.route(pool)

    # Access payload hash for queue deduplication
    print(decision.payload_hash)

    # Or use convenience function
    decision = route_pool(pool)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any

from .schemas import Pool, PoolStatus, VerdictConfidence


class RouteAction(Enum):
    """Simple routing actions.

    Each action maps to a handler that will be invoked by the execution loop.
    Actions are verbs describing what should happen next.

    Usage:
        if decision.action == RouteAction.SPAWN_ATTACKERS:
            spawn_attacker_agents(pool, decision.target_beads)
    """

    BUILD_GRAPH = "build_graph"
    DETECT_PATTERNS = "detect_patterns"
    LOAD_CONTEXT = "load_context"
    CREATE_BEADS = "create_beads"
    SPAWN_ATTACKERS = "spawn_attackers"
    SPAWN_DEFENDERS = "spawn_defenders"
    SPAWN_VERIFIERS = "spawn_verifiers"
    RUN_DEBATE = "run_debate"
    COLLECT_VERDICTS = "collect_verdicts"
    GENERATE_REPORT = "generate_report"
    FLAG_FOR_HUMAN = "flag_for_human"
    COMPLETE = "complete"
    WAIT = "wait"  # Nothing to do right now


@dataclass
class RouteDecision:
    """Output of routing decision.

    Attributes:
        action: What action to take
        target_beads: List of bead IDs to process (if applicable)
        reason: Brief explanation for logging
        metadata: Additional routing metadata
        payload_hash: Deterministic hash for queue deduplication (Phase 07.1.1-03)

    Usage:
        decision = RouteDecision(
            action=RouteAction.SPAWN_ATTACKERS,
            target_beads=["VKG-001", "VKG-002"],
            reason="2 beads need attacker analysis"
        )
        print(decision.payload_hash)  # Deterministic hash for dedup
    """

    action: RouteAction
    target_beads: List[str] = field(default_factory=list)
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def payload_hash(self) -> str:
        """Deterministic hash for queue deduplication.

        Phase 07.1.1-03: Computes SHA256 from action + sorted beads.
        Same inputs always produce same hash for idempotent queueing.

        Returns:
            16-character hex hash
        """
        # Sort beads for determinism
        sorted_beads = sorted(self.target_beads)
        payload = {
            "action": self.action.value,
            "beads": sorted_beads,
        }
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]


class Router:
    """Thin routing layer - no deep reasoning.

    Routes based on:
    1. Pool status (which phase we're in)
    2. Bead verdicts (what's resolved vs pending)
    3. Simple rules (not analysis)

    The router is stateless - same input always produces same output.

    Example:
        router = Router()
        pool = Pool(id="test", scope=Scope(files=["Vault.sol"]))
        decision = router.route(pool)
        print(decision.action)  # RouteAction.BUILD_GRAPH
    """

    # Phase -> Action mapping for simple status-based routing
    PHASE_ROUTES: Dict[PoolStatus, RouteAction] = {
        PoolStatus.INTAKE: RouteAction.BUILD_GRAPH,
        PoolStatus.CONTEXT: RouteAction.LOAD_CONTEXT,
        PoolStatus.BEADS: RouteAction.CREATE_BEADS,
        PoolStatus.EXECUTE: RouteAction.SPAWN_ATTACKERS,  # First action in execute
        PoolStatus.VERIFY: RouteAction.COLLECT_VERDICTS,
        PoolStatus.INTEGRATE: RouteAction.GENERATE_REPORT,
        PoolStatus.COMPLETE: RouteAction.COMPLETE,
        PoolStatus.FAILED: RouteAction.WAIT,
        PoolStatus.PAUSED: RouteAction.WAIT,
    }

    def route(self, pool: Pool) -> RouteDecision:
        """Determine next action for pool.

        Pure function - no side effects, no state mutation.

        Args:
            pool: Pool to route

        Returns:
            RouteDecision with next action
        """
        # Handle terminal/paused states
        if pool.status == PoolStatus.FAILED:
            return RouteDecision(
                action=RouteAction.WAIT,
                reason=f"Pool failed: {pool.metadata.get('failure_reason', 'unknown')}",
            )

        if pool.status == PoolStatus.PAUSED:
            return RouteDecision(
                action=RouteAction.WAIT,
                reason=f"Pool paused: {pool.metadata.get('pause_reason', 'awaiting human')}",
            )

        # Special case: EXECUTE phase has sub-routing (batch by role)
        if pool.status == PoolStatus.EXECUTE:
            return self._route_execute_phase(pool)

        # Special case: VERIFY phase checks if debate needed
        if pool.status == PoolStatus.VERIFY:
            return self._route_verify_phase(pool)

        # Check handler completion metadata before blindly re-dispatching.
        # Without this, handlers that complete but don't advance the pool
        # status cause infinite loops (the same action repeats forever).
        if pool.status == PoolStatus.INTAKE:
            if pool.metadata.get("graph_built"):
                return RouteDecision(
                    action=RouteAction.WAIT,
                    reason="Graph built, INTAKE phase complete — ready to advance",
                )
            return RouteDecision(
                action=RouteAction.BUILD_GRAPH,
                reason="Need to build knowledge graph",
            )

        if pool.status == PoolStatus.CONTEXT:
            if pool.metadata.get("context_loaded"):
                return RouteDecision(
                    action=RouteAction.WAIT,
                    reason="Context loaded, CONTEXT phase complete — ready to advance",
                )
            if pool.metadata.get("patterns_detected"):
                return RouteDecision(
                    action=RouteAction.LOAD_CONTEXT,
                    reason="Patterns detected, loading context",
                )
            return RouteDecision(
                action=RouteAction.DETECT_PATTERNS,
                reason="Need to detect patterns first",
            )

        if pool.status == PoolStatus.BEADS:
            if pool.metadata.get("beads_created"):
                return RouteDecision(
                    action=RouteAction.WAIT,
                    reason="Beads created, BEADS phase complete — ready to advance",
                )
            return RouteDecision(
                action=RouteAction.CREATE_BEADS,
                reason="Need to create beads from findings",
            )

        if pool.status == PoolStatus.INTEGRATE:
            if pool.metadata.get("report_generated"):
                return RouteDecision(
                    action=RouteAction.WAIT,
                    reason="Report generated, INTEGRATE phase complete — ready to advance",
                )
            return RouteDecision(
                action=RouteAction.GENERATE_REPORT,
                reason="Need to generate final report",
            )

        # Fallback for any unhandled status
        action = self.PHASE_ROUTES.get(pool.status, RouteAction.WAIT)

        return RouteDecision(
            action=action,
            reason=f"Pool in {pool.status.value} phase",
        )

    def _route_execute_phase(self, pool: Pool) -> RouteDecision:
        """Route within execute phase (attacker -> defender -> verifier).

        Batch spawning by role as per 04-CONTEXT.md decision:
        1. Attackers first - all at once
        2. Defenders after all attackers done
        3. Verifiers after all defenders done

        Args:
            pool: Pool in EXECUTE status

        Returns:
            RouteDecision for next batch
        """
        # Check what's been done via metadata tracking
        beads_with_attacker = self._beads_with_work(pool, "attacker")
        beads_with_defender = self._beads_with_work(pool, "defender")
        beads_with_verifier = self._beads_with_work(pool, "verifier")

        all_beads = set(pool.bead_ids)

        # Attackers first
        if beads_with_attacker < all_beads:
            pending = list(all_beads - beads_with_attacker)
            return RouteDecision(
                action=RouteAction.SPAWN_ATTACKERS,
                target_beads=pending,
                reason=f"{len(pending)} beads need attacker analysis",
            )

        # Then defenders (only after all attackers done)
        if beads_with_defender < beads_with_attacker:
            pending = list(beads_with_attacker - beads_with_defender)
            return RouteDecision(
                action=RouteAction.SPAWN_DEFENDERS,
                target_beads=pending,
                reason=f"{len(pending)} beads need defender analysis",
            )

        # Then verifiers (only after all defenders done)
        if beads_with_verifier < beads_with_defender:
            pending = list(beads_with_defender - beads_with_verifier)
            return RouteDecision(
                action=RouteAction.SPAWN_VERIFIERS,
                target_beads=pending,
                reason=f"{len(pending)} beads need verification",
            )

        # All done - ready to advance phase
        return RouteDecision(
            action=RouteAction.WAIT,
            reason="Execute phase complete, ready for verify",
        )

    def _route_verify_phase(self, pool: Pool) -> RouteDecision:
        """Route verification - check if debate needed.

        Per 04-CONTEXT.md: debate is triggered when there's disagreement
        (uncertain verdict after attacker/defender analysis).

        Args:
            pool: Pool in VERIFY status

        Returns:
            RouteDecision for debate, human flag, or collect
        """
        # Find beads needing debate (disagreement between attacker/defender)
        needs_debate = []
        needs_human = []

        for bead_id in pool.bead_ids:
            verdict = pool.verdicts.get(bead_id)
            if verdict is None:
                continue

            # Uncertain verdicts need debate
            if verdict.confidence == VerdictConfidence.UNCERTAIN:
                needs_debate.append(bead_id)
            # Human-flagged verdicts need review
            elif verdict.human_flag:
                needs_human.append(bead_id)

        # Route to debate first if there are disagreements
        if needs_debate:
            return RouteDecision(
                action=RouteAction.RUN_DEBATE,
                target_beads=needs_debate,
                reason=f"{len(needs_debate)} beads have disagreement, need debate",
            )

        # Then flag for human if needed
        if needs_human:
            return RouteDecision(
                action=RouteAction.FLAG_FOR_HUMAN,
                target_beads=needs_human,
                reason=f"{len(needs_human)} beads flagged for human review",
            )

        # All clear - collect verdicts
        return RouteDecision(
            action=RouteAction.COLLECT_VERDICTS,
            reason="All verdicts collected, no debates needed",
        )

    def _beads_with_work(self, pool: Pool, agent_type: str) -> set:
        """Get beads that have been processed by agent type.

        Checks work tracking in pool metadata (not deep analysis).
        This is a simple lookup, not reasoning.

        Args:
            pool: Pool to check
            agent_type: Type of agent ("attacker", "defender", "verifier")

        Returns:
            Set of bead IDs processed by this agent type
        """
        processed = pool.metadata.get(f"{agent_type}_processed", [])
        return set(processed)


def route_pool(pool: Pool) -> RouteDecision:
    """Convenience function for routing a pool.

    Args:
        pool: Pool to route

    Returns:
        RouteDecision with next action

    Example:
        decision = route_pool(pool)
        if decision.action == RouteAction.SPAWN_ATTACKERS:
            spawn_attackers(decision.target_beads)
    """
    return Router().route(pool)


# Export for module
__all__ = [
    "RouteAction",
    "RouteDecision",
    "Router",
    "route_pool",
]
