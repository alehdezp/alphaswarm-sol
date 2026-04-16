"""
Autonomous Security Agent Swarm

A swarm of specialized security agents that collaborate to discover,
verify, and exploit vulnerabilities without human intervention.

Key Components:
- AgentRole: Specialized agent types (Scanner, Analyzer, Exploiter, Verifier, Reporter)
- SwarmAgent: Individual agent with state, memory, and capabilities
- SwarmCoordinator: Orchestrates agent collaboration
- TaskBoard: Shared task queue with priorities
- SharedMemory: Collective knowledge base
- SwarmSession: Complete autonomous audit session
"""

from .agents import (
    AgentRole,
    AgentState,
    SwarmAgent,
    ScannerAgent,
    AnalyzerAgent,
    ExploiterAgent,
    VerifierAgent,
    ReporterAgent,
)

from .coordinator import (
    SwarmCoordinator,
    CoordinatorConfig,
    SwarmStatus,
    CoordinationStrategy,
)

from .task_board import (
    SwarmTask,
    TaskPriority,
    TaskStatus,
    TaskBoard,
    TaskResult,
)

from .shared_memory import (
    SharedMemory,
    MemoryEntry,
    MemoryType,
    Finding,
    Hypothesis,
    Evidence,
)

from .session import (
    SwarmSession,
    SessionConfig,
    SessionResult,
    AuditReport,
)

__all__ = [
    # Agents
    "AgentRole",
    "AgentState",
    "SwarmAgent",
    "ScannerAgent",
    "AnalyzerAgent",
    "ExploiterAgent",
    "VerifierAgent",
    "ReporterAgent",
    # Coordinator
    "SwarmCoordinator",
    "CoordinatorConfig",
    "SwarmStatus",
    "CoordinationStrategy",
    # Task Board
    "SwarmTask",
    "TaskPriority",
    "TaskStatus",
    "TaskBoard",
    "TaskResult",
    # Shared Memory
    "SharedMemory",
    "MemoryEntry",
    "MemoryType",
    "Finding",
    "Hypothesis",
    "Evidence",
    # Session
    "SwarmSession",
    "SessionConfig",
    "SessionResult",
    "AuditReport",
]
