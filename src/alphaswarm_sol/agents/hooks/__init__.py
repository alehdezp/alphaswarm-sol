"""Hook system for agent work distribution.

This module implements the "hook" (inbox) system per PHILOSOPHY.md:
"Each agent has a hook (inbox) with a prioritized bead queue"

Components:
- PrioritizedBeadQueue: Min-heap queue ordering beads by priority
- AgentInbox: Per-agent work inbox with queue and state
- HookStorage: Persistence for hook state across sessions
- AgentRole: Enum for agent roles in the system

Usage:
    from alphaswarm_sol.agents.hooks import (
        AgentInbox, AgentRole, InboxConfig,
        PrioritizedBeadQueue, BeadPriority,
        HookStorage
    )

    # Create inbox for attacker agent
    inbox = AgentInbox(AgentRole.ATTACKER)
    inbox.assign(bead)

    # Claim work
    claim = inbox.claim_work()
    if claim:
        process(claim.bead)
        inbox.complete_work(claim.bead.id)
"""

from enum import Enum

from alphaswarm_sol.agents.hooks.queue import (
    BeadPriority,
    PrioritizedBead,
    PrioritizedBeadQueue,
)
from alphaswarm_sol.agents.hooks.inbox import (
    AgentInbox,
    InboxConfig,
    WorkClaim,
)
from alphaswarm_sol.agents.hooks.storage import HookStorage


class AgentRole(str, Enum):
    """Roles for agents in the multi-agent verification system.

    Per 05.2-CONTEXT.md agent design:
    - ATTACKER: Constructs exploit paths (claude-opus-4)
    - DEFENDER: Finds guards/mitigations (claude-sonnet-4)
    - VERIFIER: Cross-checks evidence (claude-opus-4)
    - COORDINATOR: Routes beads to agents
    - SUPERVISOR: Handles escalations and arbitration

    Usage:
        role = AgentRole.ATTACKER
        inbox = AgentInbox(role)
    """

    ATTACKER = "attacker"
    DEFENDER = "defender"
    VERIFIER = "verifier"
    COORDINATOR = "coordinator"
    SUPERVISOR = "supervisor"


__all__ = [
    # Queue
    "BeadPriority",
    "PrioritizedBead",
    "PrioritizedBeadQueue",
    # Inbox
    "AgentInbox",
    "InboxConfig",
    "WorkClaim",
    # Storage
    "HookStorage",
    # Role
    "AgentRole",
]
