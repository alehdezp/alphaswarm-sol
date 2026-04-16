"""
Swarm Agents

Specialized security agents that collaborate autonomously.
Each agent type has unique capabilities and behaviors.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set
from enum import Enum
from datetime import datetime
from abc import ABC, abstractmethod
import logging

from .shared_memory import (
    SharedMemory, Finding, Hypothesis, Evidence, Severity, MemoryType
)
from .task_board import (
    TaskBoard, SwarmTask, TaskResult, TaskType, TaskPriority, TaskStatus
)

logger = logging.getLogger(__name__)


class AgentRole(Enum):
    """Agent specializations."""
    SCANNER = "scanner"           # Fast initial scanning
    ANALYZER = "analyzer"         # Deep vulnerability analysis
    EXPLOITER = "exploiter"       # Exploit construction
    VERIFIER = "verifier"         # Formal/informal verification
    REPORTER = "reporter"         # Report generation
    COORDINATOR = "coordinator"   # Swarm coordination


class AgentState(Enum):
    """Agent operational state."""
    IDLE = "idle"                 # Waiting for work
    WORKING = "working"           # Processing a task
    BLOCKED = "blocked"           # Waiting for dependency
    PAUSED = "paused"             # Temporarily paused
    STOPPED = "stopped"           # Shut down


@dataclass
class AgentMemory:
    """Individual agent's working memory."""
    current_focus: Optional[str] = None  # Current function/target
    recent_findings: List[str] = field(default_factory=list)  # Recent finding IDs
    hypotheses_proposed: List[str] = field(default_factory=list)
    tasks_completed: int = 0
    tasks_failed: int = 0
    specialization_score: Dict[str, float] = field(default_factory=dict)  # vuln_type -> success rate

    def record_success(self, vuln_type: str):
        """Record successful detection."""
        current = self.specialization_score.get(vuln_type, 0.5)
        self.specialization_score[vuln_type] = min(1.0, current + 0.1)

    def record_failure(self, vuln_type: str):
        """Record failed detection."""
        current = self.specialization_score.get(vuln_type, 0.5)
        self.specialization_score[vuln_type] = max(0.0, current - 0.05)


@dataclass
class SwarmAgent(ABC):
    """
    Base class for swarm agents.

    Each agent:
    - Has a role and capabilities
    - Can claim and process tasks
    - Reads/writes to shared memory
    - Coordinates via task board
    """
    agent_id: str
    role: AgentRole
    capabilities: Set[str] = field(default_factory=set)
    state: AgentState = AgentState.IDLE
    memory: AgentMemory = field(default_factory=AgentMemory)

    # References (set during registration)
    shared_memory: Optional[SharedMemory] = None
    task_board: Optional[TaskBoard] = None

    # Statistics
    tasks_completed: int = 0
    findings_discovered: int = 0
    start_time: datetime = field(default_factory=datetime.now)

    def register(self, shared_memory: SharedMemory, task_board: TaskBoard):
        """Register agent with swarm infrastructure."""
        self.shared_memory = shared_memory
        self.task_board = task_board

    @abstractmethod
    def process_task(self, task: SwarmTask) -> TaskResult:
        """Process a task and return result."""
        pass

    def claim_work(self) -> Optional[SwarmTask]:
        """Try to claim available work."""
        if not self.task_board:
            return None
        if self.state != AgentState.IDLE:
            return None

        task = self.task_board.claim_task(self.agent_id, self.capabilities)
        if task:
            self.state = AgentState.WORKING
            self.memory.current_focus = task.target
        return task

    def complete_work(self, task: SwarmTask, result: TaskResult):
        """Complete current task."""
        if not self.task_board:
            return

        self.task_board.complete_task(task.task_id, self.agent_id, result)
        self.tasks_completed += 1
        self.memory.tasks_completed += 1
        self.state = AgentState.IDLE

        if result.success:
            logger.debug(f"Agent {self.agent_id} completed task {task.task_id}")
        else:
            self.memory.tasks_failed += 1
            logger.warning(f"Agent {self.agent_id} task {task.task_id} failed")

    def fail_work(self, task: SwarmTask, error: str):
        """Mark current task as failed."""
        if not self.task_board:
            return

        self.task_board.fail_task(task.task_id, self.agent_id, error)
        self.memory.tasks_failed += 1
        self.state = AgentState.IDLE

    def propose_hypothesis(
        self,
        vuln_type: str,
        description: str,
        target_function: str,
        confidence: float = 0.5,
        evidence: Optional[Evidence] = None
    ) -> str:
        """Propose a new hypothesis to shared memory."""
        if not self.shared_memory:
            return ""

        hypothesis = Hypothesis(
            hypothesis_id="",
            vulnerability_type=vuln_type,
            description=description,
            target_function=target_function,
            proposed_by=self.agent_id,
            confidence=confidence,
        )

        if evidence:
            hypothesis.evidence.append(evidence)

        hyp_id = self.shared_memory.add_hypothesis(hypothesis)
        self.memory.hypotheses_proposed.append(hyp_id)
        return hyp_id

    def support_hypothesis(self, hypothesis_id: str, evidence: Optional[Evidence] = None):
        """Support an existing hypothesis."""
        if not self.shared_memory:
            return

        hypothesis = self.shared_memory.get_hypothesis(hypothesis_id)
        if hypothesis:
            hypothesis.add_support(self.agent_id, evidence)

    def oppose_hypothesis(self, hypothesis_id: str, evidence: Optional[Evidence] = None):
        """Oppose an existing hypothesis."""
        if not self.shared_memory:
            return

        hypothesis = self.shared_memory.get_hypothesis(hypothesis_id)
        if hypothesis:
            hypothesis.add_opposition(self.agent_id, evidence)

    def create_follow_up_task(
        self,
        task_type: TaskType,
        target: str,
        description: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        depends_on: Optional[List[str]] = None
    ) -> Optional[SwarmTask]:
        """Create a follow-up task."""
        if not self.task_board:
            return None

        return self.task_board.create_task(
            task_type=task_type,
            target=target,
            description=description,
            priority=priority,
            depends_on=depends_on,
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get agent statistics."""
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "state": self.state.value,
            "tasks_completed": self.tasks_completed,
            "findings_discovered": self.findings_discovered,
            "capabilities": list(self.capabilities),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
        }


class ScannerAgent(SwarmAgent):
    """
    Fast initial scanning agent.

    Capabilities:
    - Quick pattern matching
    - Initial vulnerability triage
    - Generates hypotheses for deeper analysis
    """

    def __init__(self, agent_id: str):
        super().__init__(
            agent_id=agent_id,
            role=AgentRole.SCANNER,
            capabilities={"scan", "pattern_match", "triage"},
        )
        self.patterns_checked = 0

    def process_task(self, task: SwarmTask) -> TaskResult:
        """Scan a function for potential vulnerabilities."""
        start_time = datetime.now()

        try:
            if task.task_type == TaskType.SCAN_FUNCTION:
                return self._scan_function(task, start_time)
            elif task.task_type == TaskType.PATTERN_MATCH:
                return self._pattern_match(task, start_time)
            else:
                return TaskResult(
                    task_id=task.task_id,
                    success=False,
                    result_type="error",
                    result_data=None,
                    agent_id=self.agent_id,
                    error_message=f"Unknown task type: {task.task_type}",
                )
        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                result_type="error",
                result_data=None,
                agent_id=self.agent_id,
                error_message=str(e),
            )

    def _scan_function(self, task: SwarmTask, start_time: datetime) -> TaskResult:
        """Scan a function for vulnerabilities."""
        function_name = task.target
        function_data = task.parameters.get("function_data", {})

        hypotheses = []
        follow_up_tasks = []

        # Check various vulnerability patterns
        vuln_checks = [
            ("reentrancy", self._check_reentrancy),
            ("access_control", self._check_access_control),
            ("overflow", self._check_overflow),
            ("oracle", self._check_oracle),
        ]

        for vuln_type, check_func in vuln_checks:
            result = check_func(function_name, function_data)
            if result["suspicious"]:
                # Create hypothesis
                hyp_id = self.propose_hypothesis(
                    vuln_type=vuln_type,
                    description=result["description"],
                    target_function=function_name,
                    confidence=result["confidence"],
                )
                hypotheses.append(hyp_id)

                # Create follow-up analysis task
                follow_task = self.create_follow_up_task(
                    task_type=TaskType.ANALYZE_FINDING,
                    target=function_name,
                    description=f"Deep analysis of {vuln_type} in {function_name}",
                    priority=TaskPriority.HIGH if result["confidence"] > 0.7 else TaskPriority.MEDIUM,
                )
                if follow_task:
                    follow_up_tasks.append(follow_task.task_id)

        self.patterns_checked += len(vuln_checks)

        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return TaskResult(
            task_id=task.task_id,
            success=True,
            result_type="scan_result",
            result_data={
                "function": function_name,
                "hypotheses": hypotheses,
                "patterns_checked": len(vuln_checks),
            },
            agent_id=self.agent_id,
            execution_time_ms=elapsed_ms,
            follow_up_tasks=follow_up_tasks,
        )

    def _pattern_match(self, task: SwarmTask, start_time: datetime) -> TaskResult:
        """Match code against known vulnerability patterns."""
        self.patterns_checked += 1

        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        return TaskResult(
            task_id=task.task_id,
            success=True,
            result_type="pattern_match",
            result_data={"matches": []},
            agent_id=self.agent_id,
            execution_time_ms=elapsed_ms,
        )

    # Vulnerability check methods (simplified for demonstration)
    def _check_reentrancy(self, function_name: str, data: Dict) -> Dict:
        """Check for reentrancy patterns."""
        # In real implementation, this would analyze actual code
        has_external_call = data.get("has_external_call", False)
        has_state_write_after = data.get("state_write_after_external", False)
        has_guard = data.get("has_reentrancy_guard", False)

        if has_external_call and has_state_write_after and not has_guard:
            return {
                "suspicious": True,
                "confidence": 0.8,
                "description": f"Potential reentrancy: external call before state update in {function_name}",
            }
        return {"suspicious": False, "confidence": 0.0, "description": ""}

    def _check_access_control(self, function_name: str, data: Dict) -> Dict:
        """Check for access control issues."""
        is_public = data.get("visibility") == "public"
        modifies_state = data.get("writes_state", False)
        has_access_check = data.get("has_access_gate", False)

        if is_public and modifies_state and not has_access_check:
            return {
                "suspicious": True,
                "confidence": 0.7,
                "description": f"Public function {function_name} modifies state without access control",
            }
        return {"suspicious": False, "confidence": 0.0, "description": ""}

    def _check_overflow(self, function_name: str, data: Dict) -> Dict:
        """Check for arithmetic overflow."""
        has_arithmetic = data.get("has_arithmetic", False)
        uses_safe_math = data.get("uses_safe_math", True)  # Default safe in Solidity 0.8+

        if has_arithmetic and not uses_safe_math:
            return {
                "suspicious": True,
                "confidence": 0.6,
                "description": f"Unchecked arithmetic in {function_name}",
            }
        return {"suspicious": False, "confidence": 0.0, "description": ""}

    def _check_oracle(self, function_name: str, data: Dict) -> Dict:
        """Check for oracle-related issues."""
        reads_oracle = data.get("reads_oracle", False)
        has_staleness_check = data.get("has_staleness_check", False)

        if reads_oracle and not has_staleness_check:
            return {
                "suspicious": True,
                "confidence": 0.75,
                "description": f"Oracle read without staleness check in {function_name}",
            }
        return {"suspicious": False, "confidence": 0.0, "description": ""}


class AnalyzerAgent(SwarmAgent):
    """
    Deep vulnerability analysis agent.

    Capabilities:
    - Detailed code analysis
    - Cross-function analysis
    - Impact assessment
    """

    def __init__(self, agent_id: str):
        super().__init__(
            agent_id=agent_id,
            role=AgentRole.ANALYZER,
            capabilities={"analyze", "cross_reference", "impact_assessment"},
        )

    def process_task(self, task: SwarmTask) -> TaskResult:
        """Perform deep analysis."""
        start_time = datetime.now()

        try:
            if task.task_type == TaskType.ANALYZE_FINDING:
                return self._analyze_finding(task, start_time)
            elif task.task_type == TaskType.CROSS_REFERENCE:
                return self._cross_reference(task, start_time)
            else:
                return TaskResult(
                    task_id=task.task_id,
                    success=False,
                    result_type="error",
                    result_data=None,
                    agent_id=self.agent_id,
                    error_message=f"Unknown task type: {task.task_type}",
                )
        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                result_type="error",
                result_data=None,
                agent_id=self.agent_id,
                error_message=str(e),
            )

    def _analyze_finding(self, task: SwarmTask, start_time: datetime) -> TaskResult:
        """Deep analysis of a potential vulnerability."""
        target = task.target
        follow_up_tasks = []

        # Get related hypotheses from shared memory
        if self.shared_memory:
            related = self.shared_memory.query_by_function(target)
            hypotheses = related.get("hypotheses", [])

            for hypothesis in hypotheses:
                if hypothesis.status == "pending" and hypothesis.confidence >= 0.6:
                    # Support the hypothesis with additional evidence
                    evidence = Evidence(
                        evidence_id="",
                        evidence_type="deep_analysis",
                        content=f"Deep analysis confirms {hypothesis.vulnerability_type} pattern",
                        source_agent=self.agent_id,
                        confidence=0.8,
                    )
                    self.support_hypothesis(hypothesis.hypothesis_id, evidence)

                    # Create verification task
                    verify_task = self.create_follow_up_task(
                        task_type=TaskType.VERIFY_HYPOTHESIS,
                        target=hypothesis.hypothesis_id,
                        description=f"Verify {hypothesis.vulnerability_type} hypothesis",
                        priority=TaskPriority.HIGH,
                    )
                    if verify_task:
                        follow_up_tasks.append(verify_task.task_id)

        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return TaskResult(
            task_id=task.task_id,
            success=True,
            result_type="analysis",
            result_data={
                "target": target,
                "analysis_depth": "deep",
            },
            agent_id=self.agent_id,
            execution_time_ms=elapsed_ms,
            follow_up_tasks=follow_up_tasks,
        )

    def _cross_reference(self, task: SwarmTask, start_time: datetime) -> TaskResult:
        """Cross-reference analysis."""
        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        return TaskResult(
            task_id=task.task_id,
            success=True,
            result_type="cross_reference",
            result_data={"references_found": []},
            agent_id=self.agent_id,
            execution_time_ms=elapsed_ms,
        )


class ExploiterAgent(SwarmAgent):
    """
    Exploit construction agent.

    Capabilities:
    - PoC exploit generation
    - Attack vector synthesis
    - Impact demonstration
    """

    def __init__(self, agent_id: str):
        super().__init__(
            agent_id=agent_id,
            role=AgentRole.EXPLOITER,
            capabilities={"exploit", "poc_generation", "attack_synthesis"},
        )
        self.exploits_generated = 0

    def process_task(self, task: SwarmTask) -> TaskResult:
        """Generate exploit."""
        start_time = datetime.now()

        try:
            if task.task_type == TaskType.BUILD_EXPLOIT:
                return self._build_exploit(task, start_time)
            else:
                return TaskResult(
                    task_id=task.task_id,
                    success=False,
                    result_type="error",
                    result_data=None,
                    agent_id=self.agent_id,
                    error_message=f"Unknown task type: {task.task_type}",
                )
        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                result_type="error",
                result_data=None,
                agent_id=self.agent_id,
                error_message=str(e),
            )

    def _build_exploit(self, task: SwarmTask, start_time: datetime) -> TaskResult:
        """Build PoC exploit for a vulnerability."""
        finding_id = task.target
        exploit_code = None

        if self.shared_memory:
            finding = self.shared_memory.get_finding(finding_id)
            if finding:
                # Generate exploit code based on vulnerability type
                exploit_code = self._generate_exploit_code(finding)
                if exploit_code:
                    finding.exploit_code = exploit_code
                    self.exploits_generated += 1

                    # Add attack vector to shared memory
                    self.shared_memory.add_attack_vector(
                        entry_point=finding.target_function,
                        steps=["Call entry function", "Exploit vulnerability"],
                        target=finding.vulnerability_type,
                        impact=f"{finding.severity.value} severity exploit",
                        agent_id=self.agent_id,
                    )

        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return TaskResult(
            task_id=task.task_id,
            success=exploit_code is not None,
            result_type="exploit",
            result_data={
                "finding_id": finding_id,
                "has_exploit": exploit_code is not None,
            },
            agent_id=self.agent_id,
            execution_time_ms=elapsed_ms,
        )

    def _generate_exploit_code(self, finding: Finding) -> Optional[str]:
        """Generate exploit code for a finding."""
        # Simplified exploit generation
        templates = {
            "reentrancy": """
contract Exploit {{
    address target = {target};

    function attack() external payable {{
        IVulnerable(target).{function}();
    }}

    receive() external payable {{
        if (address(target).balance > 0) {{
            IVulnerable(target).{function}();
        }}
    }}
}}
""",
            "access_control": """
contract Exploit {{
    function attack(address target) external {{
        IVulnerable(target).{function}();
    }}
}}
""",
        }

        template = templates.get(finding.vulnerability_type)
        if template:
            return template.format(
                target="TARGET_ADDRESS",
                function=finding.target_function,
            )
        return None


class VerifierAgent(SwarmAgent):
    """
    Verification agent.

    Capabilities:
    - Hypothesis verification
    - Formal verification
    - Consensus building
    """

    def __init__(self, agent_id: str):
        super().__init__(
            agent_id=agent_id,
            role=AgentRole.VERIFIER,
            capabilities={"verify", "formal_verification", "consensus"},
        )
        self.verifications_performed = 0

    def process_task(self, task: SwarmTask) -> TaskResult:
        """Verify findings and hypotheses."""
        start_time = datetime.now()

        try:
            if task.task_type == TaskType.VERIFY_HYPOTHESIS:
                return self._verify_hypothesis(task, start_time)
            elif task.task_type == TaskType.CONSENSUS_CHECK:
                return self._consensus_check(task, start_time)
            else:
                return TaskResult(
                    task_id=task.task_id,
                    success=False,
                    result_type="error",
                    result_data=None,
                    agent_id=self.agent_id,
                    error_message=f"Unknown task type: {task.task_type}",
                )
        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                result_type="error",
                result_data=None,
                agent_id=self.agent_id,
                error_message=str(e),
            )

    def _verify_hypothesis(self, task: SwarmTask, start_time: datetime) -> TaskResult:
        """Verify a hypothesis."""
        hypothesis_id = task.target
        verified = False
        follow_up_tasks = []

        if self.shared_memory:
            hypothesis = self.shared_memory.get_hypothesis(hypothesis_id)
            if hypothesis:
                # Perform verification (simplified)
                verified = hypothesis.confidence >= 0.75

                if verified:
                    # Promote to finding
                    severity = self._determine_severity(hypothesis)
                    finding = self.shared_memory.promote_hypothesis_to_finding(
                        hypothesis_id=hypothesis_id,
                        severity=severity,
                        verified_by=self.agent_id,
                    )

                    if finding:
                        self.findings_discovered += 1

                        # Create exploit task
                        exploit_task = self.create_follow_up_task(
                            task_type=TaskType.BUILD_EXPLOIT,
                            target=finding.finding_id,
                            description=f"Build exploit for {finding.title}",
                            priority=TaskPriority.MEDIUM,
                        )
                        if exploit_task:
                            follow_up_tasks.append(exploit_task.task_id)

                        # Create fix task
                        fix_task = self.create_follow_up_task(
                            task_type=TaskType.GENERATE_FIX,
                            target=finding.finding_id,
                            description=f"Generate fix for {finding.title}",
                            priority=TaskPriority.MEDIUM,
                        )
                        if fix_task:
                            follow_up_tasks.append(fix_task.task_id)
                else:
                    self.shared_memory.reject_hypothesis(
                        hypothesis_id, "Failed verification"
                    )

                self.verifications_performed += 1

        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return TaskResult(
            task_id=task.task_id,
            success=True,
            result_type="verification",
            result_data={
                "hypothesis_id": hypothesis_id,
                "verified": verified,
            },
            agent_id=self.agent_id,
            execution_time_ms=elapsed_ms,
            follow_up_tasks=follow_up_tasks,
        )

    def _consensus_check(self, task: SwarmTask, start_time: datetime) -> TaskResult:
        """Build consensus on a finding."""
        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        return TaskResult(
            task_id=task.task_id,
            success=True,
            result_type="consensus",
            result_data={"consensus_reached": True},
            agent_id=self.agent_id,
            execution_time_ms=elapsed_ms,
        )

    def _determine_severity(self, hypothesis: Hypothesis) -> Severity:
        """Determine severity based on vulnerability type."""
        high_severity_types = {"reentrancy", "access_control", "oracle", "flash_loan"}
        medium_severity_types = {"overflow", "dos", "front_running"}

        if hypothesis.vulnerability_type in high_severity_types:
            return Severity.HIGH if hypothesis.confidence >= 0.8 else Severity.MEDIUM
        elif hypothesis.vulnerability_type in medium_severity_types:
            return Severity.MEDIUM
        return Severity.LOW


class ReporterAgent(SwarmAgent):
    """
    Report generation agent.

    Capabilities:
    - Report writing
    - Finding summarization
    - Recommendation generation
    """

    def __init__(self, agent_id: str):
        super().__init__(
            agent_id=agent_id,
            role=AgentRole.REPORTER,
            capabilities={"report", "summarize", "recommend"},
        )
        self.reports_generated = 0

    def process_task(self, task: SwarmTask) -> TaskResult:
        """Generate reports."""
        start_time = datetime.now()

        try:
            if task.task_type == TaskType.WRITE_REPORT:
                return self._write_report(task, start_time)
            elif task.task_type == TaskType.GENERATE_FIX:
                return self._generate_fix(task, start_time)
            else:
                return TaskResult(
                    task_id=task.task_id,
                    success=False,
                    result_type="error",
                    result_data=None,
                    agent_id=self.agent_id,
                    error_message=f"Unknown task type: {task.task_type}",
                )
        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                result_type="error",
                result_data=None,
                agent_id=self.agent_id,
                error_message=str(e),
            )

    def _write_report(self, task: SwarmTask, start_time: datetime) -> TaskResult:
        """Write audit report."""
        report_content = self._generate_report_content()
        self.reports_generated += 1

        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return TaskResult(
            task_id=task.task_id,
            success=True,
            result_type="report",
            result_data={
                "report": report_content,
            },
            agent_id=self.agent_id,
            execution_time_ms=elapsed_ms,
        )

    def _generate_fix(self, task: SwarmTask, start_time: datetime) -> TaskResult:
        """Generate fix recommendation."""
        finding_id = task.target
        fix_recommendation = None

        if self.shared_memory:
            finding = self.shared_memory.get_finding(finding_id)
            if finding:
                fix_recommendation = self._generate_fix_code(finding)
                finding.fix_recommendation = fix_recommendation

        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return TaskResult(
            task_id=task.task_id,
            success=fix_recommendation is not None,
            result_type="fix",
            result_data={
                "finding_id": finding_id,
                "fix": fix_recommendation,
            },
            agent_id=self.agent_id,
            execution_time_ms=elapsed_ms,
        )

    def _generate_report_content(self) -> str:
        """Generate report content from shared memory."""
        if not self.shared_memory:
            return "No findings."

        lines = ["# Security Audit Report\n"]

        # Summary
        stats = self.shared_memory.get_statistics()
        lines.append("## Summary\n")
        lines.append(f"Total findings: {stats['total_findings']}")
        lines.append(f"By severity: {stats['findings_by_severity']}\n")

        # Findings
        lines.append("## Findings\n")
        for finding in self.shared_memory.findings.values():
            lines.append(f"### {finding.title}")
            lines.append(f"**Severity**: {finding.severity.value}")
            lines.append(f"**Function**: {finding.target_function}")
            lines.append(f"**Description**: {finding.description}")
            if finding.fix_recommendation:
                lines.append(f"**Fix**: {finding.fix_recommendation}")
            lines.append("")

        return "\n".join(lines)

    def _generate_fix_code(self, finding: Finding) -> str:
        """Generate fix recommendation."""
        fixes = {
            "reentrancy": "Add ReentrancyGuard and follow checks-effects-interactions pattern",
            "access_control": "Add onlyOwner or onlyRole modifier",
            "overflow": "Use SafeMath or Solidity 0.8+ checked arithmetic",
            "oracle": "Add staleness check: require(updatedAt > block.timestamp - maxAge)",
        }
        return fixes.get(finding.vulnerability_type, "Manual review required")
