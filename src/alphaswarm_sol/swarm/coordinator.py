"""
Swarm Coordinator

Orchestrates agent collaboration and manages swarm behavior.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set, Type
from enum import Enum
from datetime import datetime
import threading
import time
import logging

from .agents import (
    SwarmAgent, AgentRole, AgentState,
    ScannerAgent, AnalyzerAgent, ExploiterAgent, VerifierAgent, ReporterAgent
)
from .shared_memory import SharedMemory
from .task_board import TaskBoard, TaskType, TaskPriority, SwarmTask

logger = logging.getLogger(__name__)


class SwarmStatus(Enum):
    """Swarm operational status."""
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETING = "completing"  # Finishing remaining work
    STOPPED = "stopped"


class CoordinationStrategy(Enum):
    """How agents coordinate."""
    AUTONOMOUS = "autonomous"      # Agents work independently
    GUIDED = "guided"              # Coordinator assigns tasks
    HYBRID = "hybrid"              # Mix of both


@dataclass
class CoordinatorConfig:
    """Configuration for swarm coordinator."""
    # Agent counts
    num_scanners: int = 2
    num_analyzers: int = 2
    num_exploiters: int = 1
    num_verifiers: int = 2
    num_reporters: int = 1

    # Behavior
    strategy: CoordinationStrategy = CoordinationStrategy.AUTONOMOUS
    max_iterations: int = 100
    iteration_delay_ms: int = 100
    convergence_threshold: int = 3  # Iterations without new findings

    # Timeouts
    task_timeout_seconds: int = 300
    session_timeout_seconds: int = 3600  # 1 hour max

    # Thresholds
    min_confidence_for_finding: float = 0.75
    min_consensus_for_report: float = 0.6


@dataclass
class SwarmMetrics:
    """Metrics tracking for the swarm."""
    start_time: datetime = field(default_factory=datetime.now)
    iterations: int = 0
    tasks_created: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    hypotheses_proposed: int = 0
    hypotheses_verified: int = 0
    hypotheses_rejected: int = 0
    findings_discovered: int = 0
    exploits_generated: int = 0
    iterations_without_progress: int = 0

    def get_efficiency(self) -> float:
        """Calculate task efficiency."""
        total = self.tasks_completed + self.tasks_failed
        if total == 0:
            return 0.0
        return self.tasks_completed / total

    def get_discovery_rate(self) -> float:
        """Calculate discovery rate."""
        if self.iterations == 0:
            return 0.0
        return self.findings_discovered / self.iterations

    def to_dict(self) -> Dict[str, Any]:
        return {
            "iterations": self.iterations,
            "tasks_created": self.tasks_created,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "hypotheses_proposed": self.hypotheses_proposed,
            "findings_discovered": self.findings_discovered,
            "exploits_generated": self.exploits_generated,
            "efficiency": round(self.get_efficiency(), 3),
            "runtime_seconds": (datetime.now() - self.start_time).total_seconds(),
        }


class SwarmCoordinator:
    """
    Coordinates agent swarm behavior.

    Responsibilities:
    - Spawn and manage agents
    - Initialize shared infrastructure
    - Monitor progress and convergence
    - Handle agent failures
    """

    def __init__(self, config: Optional[CoordinatorConfig] = None):
        self.config = config or CoordinatorConfig()
        self.status = SwarmStatus.INITIALIZING

        # Infrastructure
        self.shared_memory = SharedMemory()
        self.task_board = TaskBoard()

        # Agents
        self.agents: Dict[str, SwarmAgent] = {}
        self._agent_counter = 0

        # Metrics
        self.metrics = SwarmMetrics()

        # Threading
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def initialize(self):
        """Initialize the swarm."""
        logger.info("Initializing agent swarm...")

        # Spawn agents
        self._spawn_agents()

        # Register all agents
        for agent in self.agents.values():
            agent.register(self.shared_memory, self.task_board)

        self.status = SwarmStatus.READY
        logger.info(f"Swarm initialized with {len(self.agents)} agents")

    def _spawn_agents(self):
        """Spawn all configured agents."""
        # Scanners
        for _ in range(self.config.num_scanners):
            self._add_agent(ScannerAgent)

        # Analyzers
        for _ in range(self.config.num_analyzers):
            self._add_agent(AnalyzerAgent)

        # Exploiters
        for _ in range(self.config.num_exploiters):
            self._add_agent(ExploiterAgent)

        # Verifiers
        for _ in range(self.config.num_verifiers):
            self._add_agent(VerifierAgent)

        # Reporters
        for _ in range(self.config.num_reporters):
            self._add_agent(ReporterAgent)

    def _add_agent(self, agent_class: Type[SwarmAgent]) -> SwarmAgent:
        """Add an agent to the swarm."""
        self._agent_counter += 1
        agent_id = f"{agent_class.__name__}-{self._agent_counter:03d}"
        agent = agent_class(agent_id)
        self.agents[agent_id] = agent
        return agent

    def add_initial_tasks(self, functions: List[Dict[str, Any]]):
        """Add initial scanning tasks for functions."""
        for func_data in functions:
            func_name = func_data.get("name", "unknown")
            task = self.task_board.create_task(
                task_type=TaskType.SCAN_FUNCTION,
                target=func_name,
                description=f"Initial scan of {func_name}",
                priority=TaskPriority.HIGH,
                parameters={"function_data": func_data},
                required_capabilities={"scan"},
            )
            self.metrics.tasks_created += 1

        logger.info(f"Added {len(functions)} initial scan tasks")

    def run_iteration(self) -> bool:
        """
        Run one iteration of the swarm.

        Returns True if there's more work to do.
        """
        if self.status not in [SwarmStatus.RUNNING, SwarmStatus.READY]:
            return False

        self.status = SwarmStatus.RUNNING
        self.metrics.iterations += 1

        # Track progress for convergence detection
        findings_before = len(self.shared_memory.findings)

        # Let each agent try to claim and process work
        for agent in self.agents.values():
            if agent.state == AgentState.IDLE:
                task = agent.claim_work()
                if task:
                    self.task_board.start_task(task.task_id, agent.agent_id)
                    result = agent.process_task(task)
                    agent.complete_work(task, result)

                    # Update metrics
                    if result.success:
                        self.metrics.tasks_completed += 1
                    else:
                        self.metrics.tasks_failed += 1

                    # Track follow-up tasks
                    self.metrics.tasks_created += len(result.follow_up_tasks)

        # Check for convergence
        findings_after = len(self.shared_memory.findings)
        if findings_after == findings_before:
            self.metrics.iterations_without_progress += 1
        else:
            self.metrics.iterations_without_progress = 0
            self.metrics.findings_discovered = findings_after

        # Check if done
        pending_tasks = self.task_board.get_pending_tasks()
        has_work = len(pending_tasks) > 0 or any(
            a.state == AgentState.WORKING for a in self.agents.values()
        )

        # Check convergence
        converged = self.metrics.iterations_without_progress >= self.config.convergence_threshold

        if not has_work or converged:
            logger.info(f"Swarm converging after {self.metrics.iterations} iterations")
            return False

        return True

    def run(self, max_iterations: Optional[int] = None) -> "SwarmMetrics":
        """
        Run the swarm until completion or max iterations.

        Returns final metrics.
        """
        max_iter = max_iterations or self.config.max_iterations
        self.status = SwarmStatus.RUNNING

        logger.info(f"Starting swarm run (max {max_iter} iterations)")

        for _ in range(max_iter):
            if self._stop_event.is_set():
                break

            has_more_work = self.run_iteration()

            if not has_more_work:
                break

            # Small delay between iterations
            time.sleep(self.config.iteration_delay_ms / 1000)

        # Finalize
        self._finalize()

        return self.metrics

    def _finalize(self):
        """Finalize swarm run."""
        self.status = SwarmStatus.COMPLETING

        # Create final report task if there are findings
        if self.shared_memory.findings:
            self.task_board.create_task(
                task_type=TaskType.WRITE_REPORT,
                target="final_report",
                description="Generate final audit report",
                priority=TaskPriority.HIGH,
                required_capabilities={"report"},
            )

            # Let reporter process it
            for agent in self.agents.values():
                if agent.role == AgentRole.REPORTER and agent.state == AgentState.IDLE:
                    task = agent.claim_work()
                    if task:
                        self.task_board.start_task(task.task_id, agent.agent_id)
                        result = agent.process_task(task)
                        agent.complete_work(task, result)
                        break

        self.status = SwarmStatus.STOPPED
        logger.info("Swarm run completed")

    def stop(self):
        """Stop the swarm."""
        self._stop_event.set()
        self.status = SwarmStatus.STOPPED

        for agent in self.agents.values():
            agent.state = AgentState.STOPPED

    def pause(self):
        """Pause the swarm."""
        self.status = SwarmStatus.PAUSED
        for agent in self.agents.values():
            if agent.state == AgentState.IDLE:
                agent.state = AgentState.PAUSED

    def resume(self):
        """Resume paused swarm."""
        self.status = SwarmStatus.RUNNING
        for agent in self.agents.values():
            if agent.state == AgentState.PAUSED:
                agent.state = AgentState.IDLE

    # === Query Methods ===

    def get_agent(self, agent_id: str) -> Optional[SwarmAgent]:
        """Get agent by ID."""
        return self.agents.get(agent_id)

    def get_agents_by_role(self, role: AgentRole) -> List[SwarmAgent]:
        """Get all agents of a role."""
        return [a for a in self.agents.values() if a.role == role]

    def get_active_agents(self) -> List[SwarmAgent]:
        """Get currently working agents."""
        return [a for a in self.agents.values() if a.state == AgentState.WORKING]

    def get_idle_agents(self) -> List[SwarmAgent]:
        """Get idle agents."""
        return [a for a in self.agents.values() if a.state == AgentState.IDLE]

    # === Statistics ===

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive swarm statistics."""
        agent_stats = {}
        for role in AgentRole:
            agents = self.get_agents_by_role(role)
            agent_stats[role.value] = {
                "count": len(agents),
                "working": sum(1 for a in agents if a.state == AgentState.WORKING),
                "idle": sum(1 for a in agents if a.state == AgentState.IDLE),
            }

        return {
            "status": self.status.value,
            "metrics": self.metrics.to_dict(),
            "agents": agent_stats,
            "shared_memory": self.shared_memory.get_statistics(),
            "task_board": self.task_board.get_statistics(),
        }

    def get_summary(self) -> str:
        """Get human-readable summary."""
        stats = self.get_statistics()
        lines = [
            "=== Swarm Summary ===",
            f"Status: {stats['status']}",
            f"Iterations: {stats['metrics']['iterations']}",
            f"Tasks: {stats['metrics']['tasks_completed']}/{stats['metrics']['tasks_created']}",
            f"Findings: {stats['metrics']['findings_discovered']}",
            f"Efficiency: {stats['metrics']['efficiency']:.1%}",
            "",
            "Agents:",
        ]

        for role, data in stats['agents'].items():
            lines.append(f"  {role}: {data['count']} ({data['working']} working)")

        lines.append("")
        lines.append(self.shared_memory.get_summary())

        return "\n".join(lines)

    def clear(self):
        """Clear all state."""
        self.shared_memory.clear()
        self.task_board.clear()
        self.metrics = SwarmMetrics()
        self.status = SwarmStatus.READY
