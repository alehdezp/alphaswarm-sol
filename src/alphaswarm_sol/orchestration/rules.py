"""Orchestration rules and constraints for the orchestration layer.

This module defines rules governing pool lifecycle, verdict validation,
and agent batching policies.

Design Principles:
1. All verdicts require human review (PHILOSOPHY.md)
2. Debate outcomes always set human_flag=True
3. Missing context defaults to uncertain
4. Batching follows role priority (attackers -> defenders -> verifiers)

Usage:
    from alphaswarm_sol.orchestration.rules import OrchestrationRules, BatchingPolicy

    rules = OrchestrationRules()

    # Check if verdict passes rules
    violations = rules.check_verdict_rules(verdict)
    if violations:
        for v in violations:
            print(f"Violation: {v.message}")

    # Check if pool can advance phase
    can_advance, reason = rules.can_advance_phase(pool)
    if not can_advance:
        print(f"Cannot advance: {reason}")

    # Get default batching policy
    policy = DEFAULT_BATCHING
    print(f"First batch: {policy.first_batch}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .schemas import (
    DebateRecord,
    Pool,
    PoolStatus,
    Verdict,
    VerdictConfidence,
)


class RuleType(Enum):
    """Types of orchestration rules."""

    VERDICT = "verdict"
    POOL = "pool"
    PHASE = "phase"
    BATCHING = "batching"
    HUMAN_FLAG = "human_flag"


class RuleSeverity(Enum):
    """Severity of rule violations."""

    ERROR = "error"  # Must be fixed before proceeding
    WARNING = "warning"  # Should be reviewed but not blocking
    INFO = "info"  # Informational only


@dataclass
class RuleViolation:
    """Represents a violation of an orchestration rule.

    Attributes:
        rule_type: Category of the rule
        severity: How serious the violation is
        message: Human-readable description
        rule_id: Identifier for the specific rule
        context: Additional context about the violation
        suggested_fix: How to resolve the violation
    """

    rule_type: RuleType
    severity: RuleSeverity
    message: str
    rule_id: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    suggested_fix: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "rule_type": self.rule_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "rule_id": self.rule_id,
            "context": self.context,
            "suggested_fix": self.suggested_fix,
        }

    @property
    def is_error(self) -> bool:
        """Check if this is a blocking error."""
        return self.severity == RuleSeverity.ERROR


@dataclass
class BatchingPolicy:
    """Policy for batching agent execution.

    Defines the order in which agents should be spawned and executed.
    Per 04-CONTEXT.md: attackers first, then defenders, then verifiers.

    Attributes:
        first_batch: Agent roles to run first
        second_batch: Agent roles to run second
        third_batch: Agent roles to run third
        parallel_within_batch: Whether agents in same batch can run in parallel
        max_parallel: Maximum parallel agents per batch
        timeout_seconds: Timeout for each batch
    """

    first_batch: List[str] = field(default_factory=lambda: ["attacker"])
    second_batch: List[str] = field(default_factory=lambda: ["defender"])
    third_batch: List[str] = field(default_factory=lambda: ["verifier"])
    parallel_within_batch: bool = True
    max_parallel: int = 3
    timeout_seconds: int = 300

    def get_batch_order(self) -> List[List[str]]:
        """Get ordered list of batches.

        Returns:
            List of batches, each batch is a list of agent roles
        """
        batches = []
        if self.first_batch:
            batches.append(self.first_batch)
        if self.second_batch:
            batches.append(self.second_batch)
        if self.third_batch:
            batches.append(self.third_batch)
        return batches

    def get_role_batch(self, role: str) -> int:
        """Get which batch number a role belongs to.

        Args:
            role: Agent role name

        Returns:
            Batch number (1, 2, or 3), or 0 if not found
        """
        if role in self.first_batch:
            return 1
        if role in self.second_batch:
            return 2
        if role in self.third_batch:
            return 3
        return 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "first_batch": self.first_batch,
            "second_batch": self.second_batch,
            "third_batch": self.third_batch,
            "parallel_within_batch": self.parallel_within_batch,
            "max_parallel": self.max_parallel,
            "timeout_seconds": self.timeout_seconds,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BatchingPolicy":
        """Create BatchingPolicy from dictionary."""
        return cls(
            first_batch=list(data.get("first_batch", ["attacker"])),
            second_batch=list(data.get("second_batch", ["defender"])),
            third_batch=list(data.get("third_batch", ["verifier"])),
            parallel_within_batch=bool(data.get("parallel_within_batch", True)),
            max_parallel=int(data.get("max_parallel", 3)),
            timeout_seconds=int(data.get("timeout_seconds", 300)),
        )


# Default batching policy per 04-CONTEXT.md
DEFAULT_BATCHING = BatchingPolicy(
    first_batch=["attacker"],
    second_batch=["defender"],
    third_batch=["verifier"],
    parallel_within_batch=True,
    max_parallel=3,
    timeout_seconds=300,
)


class OrchestrationRules:
    """Orchestration rules and constraints.

    Enforces rules for:
    - Verdict validation (evidence requirements, human flags)
    - Pool lifecycle (phase transitions, status constraints)
    - Agent batching (role order, parallelism)

    Example:
        rules = OrchestrationRules()

        # Check verdict
        violations = rules.check_verdict_rules(verdict)
        if any(v.is_error for v in violations):
            print("Verdict has blocking errors")

        # Check pool phase transition
        can_advance, reason = rules.can_advance_phase(pool)
        if can_advance:
            pool.advance_phase()
    """

    def __init__(
        self,
        batching_policy: Optional[BatchingPolicy] = None,
        require_evidence_for_likely: bool = True,
        require_evidence_for_confirmed: bool = True,
        require_debate_for_confirmed: bool = False,
        min_beads_for_execute: int = 1,
    ):
        """Initialize rules with configuration.

        Args:
            batching_policy: Policy for agent batching (default: DEFAULT_BATCHING)
            require_evidence_for_likely: Whether LIKELY requires evidence
            require_evidence_for_confirmed: Whether CONFIRMED requires evidence
            require_debate_for_confirmed: Whether CONFIRMED requires debate
            min_beads_for_execute: Minimum beads required to enter EXECUTE phase
        """
        self.batching_policy = batching_policy or DEFAULT_BATCHING
        self.require_evidence_for_likely = require_evidence_for_likely
        self.require_evidence_for_confirmed = require_evidence_for_confirmed
        self.require_debate_for_confirmed = require_debate_for_confirmed
        self.min_beads_for_execute = min_beads_for_execute

    def check_verdict_rules(self, verdict: Verdict) -> List[RuleViolation]:
        """Check verdict against all rules.

        Args:
            verdict: Verdict to validate

        Returns:
            List of rule violations (empty if all pass)
        """
        violations: List[RuleViolation] = []

        # Rule V-01: Human flag must always be True
        if not verdict.human_flag:
            violations.append(
                RuleViolation(
                    rule_type=RuleType.HUMAN_FLAG,
                    severity=RuleSeverity.ERROR,
                    message="Human flag must always be True per PHILOSOPHY.md",
                    rule_id="V-01",
                    context={"human_flag": verdict.human_flag},
                    suggested_fix="Set human_flag=True",
                )
            )

        # Rule V-02: CONFIRMED verdict requires evidence
        if (
            verdict.confidence == VerdictConfidence.CONFIRMED
            and verdict.is_vulnerable
            and self.require_evidence_for_confirmed
        ):
            if not verdict.evidence_packet or not verdict.evidence_packet.items:
                violations.append(
                    RuleViolation(
                        rule_type=RuleType.VERDICT,
                        severity=RuleSeverity.ERROR,
                        message="CONFIRMED verdict requires evidence",
                        rule_id="V-02",
                        context={
                            "confidence": verdict.confidence.value,
                            "has_evidence": bool(verdict.evidence_packet),
                        },
                        suggested_fix="Downgrade to LIKELY or add evidence",
                    )
                )

        # Rule V-03: CONFIRMED may require debate completion
        if (
            verdict.confidence == VerdictConfidence.CONFIRMED
            and verdict.is_vulnerable
            and self.require_debate_for_confirmed
        ):
            if not verdict.debate or not verdict.debate.is_complete:
                violations.append(
                    RuleViolation(
                        rule_type=RuleType.VERDICT,
                        severity=RuleSeverity.WARNING,
                        message="CONFIRMED verdict should have completed debate",
                        rule_id="V-03",
                        context={
                            "has_debate": bool(verdict.debate),
                            "debate_complete": verdict.debate.is_complete if verdict.debate else False,
                        },
                        suggested_fix="Complete debate before CONFIRMED status",
                    )
                )

        # Rule V-04: LIKELY verdict requires at least some evidence
        if (
            verdict.confidence == VerdictConfidence.LIKELY
            and verdict.is_vulnerable
            and self.require_evidence_for_likely
        ):
            if not verdict.evidence_packet or not verdict.evidence_packet.items:
                violations.append(
                    RuleViolation(
                        rule_type=RuleType.VERDICT,
                        severity=RuleSeverity.ERROR,
                        message="LIKELY verdict requires evidence",
                        rule_id="V-04",
                        context={
                            "confidence": verdict.confidence.value,
                            "has_evidence": bool(verdict.evidence_packet),
                        },
                        suggested_fix="Downgrade to UNCERTAIN or add evidence",
                    )
                )

        # Rule V-05: Positive verdict requires rationale
        if verdict.is_vulnerable and verdict.confidence.is_positive():
            if not verdict.rationale or not verdict.rationale.strip():
                violations.append(
                    RuleViolation(
                        rule_type=RuleType.VERDICT,
                        severity=RuleSeverity.ERROR,
                        message="Positive verdict requires rationale",
                        rule_id="V-05",
                        context={"rationale": verdict.rationale},
                        suggested_fix="Add rationale explaining the verdict",
                    )
                )

        # Rule V-06: Debate with disagreement should flag for human
        if verdict.debate and verdict.debate.dissenting_opinion:
            violations.append(
                RuleViolation(
                    rule_type=RuleType.VERDICT,
                    severity=RuleSeverity.INFO,
                    message="Debate has dissenting opinion - prioritize for human review",
                    rule_id="V-06",
                    context={
                        "dissenting_opinion": verdict.debate.dissenting_opinion[:100],
                    },
                    suggested_fix="Ensure human reviewer sees dissenting opinion",
                )
            )

        return violations

    def check_pool_rules(self, pool: Pool) -> List[RuleViolation]:
        """Check pool against all rules.

        Args:
            pool: Pool to validate

        Returns:
            List of rule violations (empty if all pass)
        """
        violations: List[RuleViolation] = []

        # Rule P-01: Pool must have scope
        if not pool.scope.files:
            violations.append(
                RuleViolation(
                    rule_type=RuleType.POOL,
                    severity=RuleSeverity.ERROR,
                    message="Pool must have at least one file in scope",
                    rule_id="P-01",
                    context={"files_count": len(pool.scope.files)},
                    suggested_fix="Add files to pool scope",
                )
            )

        # Rule P-02: EXECUTE phase requires beads
        if pool.status == PoolStatus.EXECUTE:
            if len(pool.bead_ids) < self.min_beads_for_execute:
                violations.append(
                    RuleViolation(
                        rule_type=RuleType.POOL,
                        severity=RuleSeverity.ERROR,
                        message=f"EXECUTE phase requires at least {self.min_beads_for_execute} bead(s)",
                        rule_id="P-02",
                        context={"bead_count": len(pool.bead_ids)},
                        suggested_fix="Add beads before entering EXECUTE phase",
                    )
                )

        # Rule P-03: COMPLETE should have verdicts for all beads
        if pool.status == PoolStatus.COMPLETE:
            pending = pool.pending_beads
            if pending:
                violations.append(
                    RuleViolation(
                        rule_type=RuleType.POOL,
                        severity=RuleSeverity.WARNING,
                        message="COMPLETE pool has beads without verdicts",
                        rule_id="P-03",
                        context={
                            "pending_beads": pending,
                            "total_beads": len(pool.bead_ids),
                        },
                        suggested_fix="Add verdicts for all beads or remove incomplete beads",
                    )
                )

        # Rule P-04: FAILED pool should have failure reason
        if pool.status == PoolStatus.FAILED:
            if "failure_reason" not in pool.metadata:
                violations.append(
                    RuleViolation(
                        rule_type=RuleType.POOL,
                        severity=RuleSeverity.WARNING,
                        message="FAILED pool should have failure_reason in metadata",
                        rule_id="P-04",
                        context={"metadata_keys": list(pool.metadata.keys())},
                        suggested_fix="Add failure_reason to metadata",
                    )
                )

            # Rule P-04a: FAILED pool should have failure_type (Phase 07.1.1-06)
            if "failure_type" not in pool.metadata:
                violations.append(
                    RuleViolation(
                        rule_type=RuleType.POOL,
                        severity=RuleSeverity.WARNING,
                        message="FAILED pool should have failure_type in metadata",
                        rule_id="P-04a",
                        context={"metadata_keys": list(pool.metadata.keys())},
                        suggested_fix="Add failure_type to metadata (from FailureType enum)",
                    )
                )

            # Rule P-04b: FAILED pool should have failure_details (Phase 07.1.1-06)
            if "failure_details" not in pool.metadata:
                violations.append(
                    RuleViolation(
                        rule_type=RuleType.POOL,
                        severity=RuleSeverity.INFO,
                        message="FAILED pool should have failure_details in metadata",
                        rule_id="P-04b",
                        context={"metadata_keys": list(pool.metadata.keys())},
                        suggested_fix="Add failure_details for audit trail",
                    )
                )

        # Rule P-05: All verdicts should pass verdict rules
        for finding_id, verdict in pool.verdicts.items():
            verdict_violations = self.check_verdict_rules(verdict)
            for v in verdict_violations:
                v.context["finding_id"] = finding_id
                violations.append(v)

        return violations

    def can_advance_phase(self, pool: Pool) -> Tuple[bool, str]:
        """Check if pool can advance to next phase.

        Args:
            pool: Pool to check

        Returns:
            Tuple of (can_advance: bool, reason: str)
        """
        # Terminal states cannot advance
        if pool.status.is_terminal():
            return False, f"Pool is in terminal status: {pool.status.value}"

        # Paused state cannot advance
        if pool.status == PoolStatus.PAUSED:
            return False, "Pool is paused, resume before advancing"

        # Phase-specific requirements
        current = pool.status
        next_phase = current.next_phase()

        if next_phase is None:
            return False, "No next phase available"

        # INTAKE -> CONTEXT: no special requirements
        if current == PoolStatus.INTAKE:
            return True, ""

        # CONTEXT -> BEADS: need scope files
        if current == PoolStatus.CONTEXT:
            if not pool.scope.files:
                return False, "Cannot advance to BEADS: no files in scope"
            return True, ""

        # BEADS -> EXECUTE: need at least min_beads
        if current == PoolStatus.BEADS:
            if len(pool.bead_ids) < self.min_beads_for_execute:
                return False, f"Cannot advance to EXECUTE: need at least {self.min_beads_for_execute} bead(s), have {len(pool.bead_ids)}"
            return True, ""

        # EXECUTE -> VERIFY: all beads should have some analysis
        if current == PoolStatus.EXECUTE:
            # This is a soft requirement - we allow advancing even without full coverage
            return True, ""

        # VERIFY -> INTEGRATE: debate should be complete for all beads
        if current == PoolStatus.VERIFY:
            # Soft requirement - allow advancing
            return True, ""

        # INTEGRATE -> COMPLETE: all beads should have verdicts
        if current == PoolStatus.INTEGRATE:
            pending = pool.pending_beads
            if pending:
                return False, f"Cannot complete: {len(pending)} bead(s) without verdicts"
            return True, ""

        return True, ""

    def get_next_batch(
        self,
        current_batch: int,
        completed_roles: List[str],
    ) -> Tuple[List[str], int]:
        """Get the next batch of agent roles to execute.

        Args:
            current_batch: Current batch number (1-3)
            completed_roles: Roles that have completed

        Returns:
            Tuple of (roles to execute, batch number)
        """
        batches = self.batching_policy.get_batch_order()

        # Find next batch that has incomplete roles
        for batch_num, roles in enumerate(batches, start=1):
            if batch_num <= current_batch:
                continue
            incomplete = [r for r in roles if r not in completed_roles]
            if incomplete:
                return incomplete, batch_num

        # All batches complete
        return [], 0

    def should_pause_for_human(
        self,
        pool: Pool,
        reason: str = "",
    ) -> Tuple[bool, str]:
        """Check if pool should pause for human input.

        Args:
            pool: Pool to check
            reason: Specific reason to check

        Returns:
            Tuple of (should_pause: bool, reason: str)
        """
        # Check all verdicts for human-requiring conditions
        for finding_id, verdict in pool.verdicts.items():
            # Debate disagreement always requires human
            if verdict.debate and verdict.debate.dissenting_opinion:
                return True, f"Debate disagreement in {finding_id}"

            # Uncertain verdict may need human input
            if verdict.confidence == VerdictConfidence.UNCERTAIN:
                return True, f"Uncertain verdict in {finding_id}"

        return False, ""

    def validate_batching(
        self,
        roles: List[str],
        batch_number: int,
    ) -> List[RuleViolation]:
        """Validate that roles are appropriate for the batch.

        Args:
            roles: Agent roles to validate
            batch_number: Which batch they're in

        Returns:
            List of violations
        """
        violations: List[RuleViolation] = []
        batches = self.batching_policy.get_batch_order()

        if batch_number < 1 or batch_number > len(batches):
            violations.append(
                RuleViolation(
                    rule_type=RuleType.BATCHING,
                    severity=RuleSeverity.ERROR,
                    message=f"Invalid batch number: {batch_number}",
                    rule_id="B-01",
                    context={"batch_number": batch_number, "max_batch": len(batches)},
                )
            )
            return violations

        expected_roles = batches[batch_number - 1]
        unexpected = [r for r in roles if r not in expected_roles]

        if unexpected:
            violations.append(
                RuleViolation(
                    rule_type=RuleType.BATCHING,
                    severity=RuleSeverity.WARNING,
                    message=f"Roles {unexpected} not in batch {batch_number}",
                    rule_id="B-02",
                    context={
                        "unexpected_roles": unexpected,
                        "expected_roles": expected_roles,
                    },
                    suggested_fix=f"Expected roles for batch {batch_number}: {expected_roles}",
                )
            )

        return violations


# Export for module
__all__ = [
    "RuleType",
    "RuleSeverity",
    "RuleViolation",
    "BatchingPolicy",
    "DEFAULT_BATCHING",
    "OrchestrationRules",
]
