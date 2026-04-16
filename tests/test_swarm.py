"""
Tests for Autonomous Security Agent Swarm

Tests the complete swarm system including agents, coordination,
shared memory, task board, and full audit sessions.
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from alphaswarm_sol.swarm import (
    # Agents
    AgentRole,
    AgentState,
    SwarmAgent,
    ScannerAgent,
    AnalyzerAgent,
    ExploiterAgent,
    VerifierAgent,
    ReporterAgent,
    # Coordinator
    SwarmCoordinator,
    CoordinatorConfig,
    SwarmStatus,
    CoordinationStrategy,
    # Task Board
    SwarmTask,
    TaskPriority,
    TaskStatus,
    TaskBoard,
    TaskResult,
    # Shared Memory
    SharedMemory,
    MemoryEntry,
    MemoryType,
    Finding,
    Hypothesis,
    Evidence,
    # Session
    SwarmSession,
    SessionConfig,
    SessionResult,
    AuditReport,
)
from alphaswarm_sol.swarm.shared_memory import Severity
from alphaswarm_sol.swarm.task_board import TaskType


class TestSharedMemory(unittest.TestCase):
    """Tests for SharedMemory."""

    def setUp(self):
        self.memory = SharedMemory()

    def test_create_shared_memory(self):
        """Test shared memory creation."""
        self.assertIsNotNone(self.memory)
        self.assertEqual(len(self.memory.findings), 0)
        self.assertEqual(len(self.memory.hypotheses), 0)

    def test_add_finding(self):
        """Test adding a finding."""
        finding = Finding(
            finding_id="",
            vulnerability_type="reentrancy",
            severity=Severity.HIGH,
            title="Reentrancy in withdraw",
            description="External call before state update",
            target_function="withdraw",
        )

        finding_id = self.memory.add_finding(finding)

        self.assertIsNotNone(finding_id)
        self.assertIn(finding_id, self.memory.findings)
        self.assertEqual(self.memory.findings[finding_id].title, "Reentrancy in withdraw")

    def test_get_findings_by_severity(self):
        """Test getting findings by severity."""
        # Add multiple findings
        for sev in [Severity.CRITICAL, Severity.HIGH, Severity.HIGH, Severity.LOW]:
            finding = Finding(
                finding_id="",
                vulnerability_type="test",
                severity=sev,
                title=f"Finding {sev.value}",
                description="Test",
                target_function="test",
            )
            self.memory.add_finding(finding)

        high = self.memory.get_findings_by_severity(Severity.HIGH)
        self.assertEqual(len(high), 2)

    def test_add_hypothesis(self):
        """Test adding a hypothesis."""
        hypothesis = Hypothesis(
            hypothesis_id="",
            vulnerability_type="reentrancy",
            description="Potential reentrancy vulnerability",
            target_function="withdraw",
            proposed_by="scanner-001",
            confidence=0.7,
        )

        hyp_id = self.memory.add_hypothesis(hypothesis)

        self.assertIsNotNone(hyp_id)
        self.assertIn(hyp_id, self.memory.hypotheses)

    def test_hypothesis_support_opposition(self):
        """Test hypothesis support/opposition."""
        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            vulnerability_type="test",
            description="Test hypothesis",
            target_function="test",
        )
        self.memory.add_hypothesis(hypothesis)

        # Add support
        hypothesis.add_support("agent-1")
        hypothesis.add_support("agent-2")
        self.assertEqual(len(hypothesis.supporting_agents), 2)
        self.assertGreater(hypothesis.confidence, 0.5)

        # Add opposition
        hypothesis.add_opposition("agent-3")
        self.assertEqual(len(hypothesis.opposing_agents), 1)

    def test_promote_hypothesis_to_finding(self):
        """Test promoting hypothesis to finding."""
        hypothesis = Hypothesis(
            hypothesis_id="",
            vulnerability_type="reentrancy",
            description="Confirmed reentrancy",
            target_function="withdraw",
            confidence=0.9,
        )
        hyp_id = self.memory.add_hypothesis(hypothesis)

        finding = self.memory.promote_hypothesis_to_finding(
            hyp_id, Severity.HIGH, "verifier-001"
        )

        self.assertIsNotNone(finding)
        self.assertEqual(finding.vulnerability_type, "reentrancy")
        self.assertEqual(finding.severity, Severity.HIGH)
        self.assertEqual(hypothesis.status, "confirmed")

    def test_safe_zones(self):
        """Test safe zone management."""
        self.memory.mark_safe("safeFunction", "scanner-001")

        self.assertTrue(self.memory.is_safe("safeFunction"))
        self.assertFalse(self.memory.is_safe("unsafeFunction"))

    def test_attack_vectors(self):
        """Test attack vector management."""
        vector_id = self.memory.add_attack_vector(
            entry_point="deposit",
            steps=["Call deposit", "Reenter via fallback"],
            target="balance",
            impact="Drain funds",
            agent_id="exploiter-001",
        )

        self.assertIsNotNone(vector_id)
        self.assertEqual(len(self.memory.attack_vectors), 1)

    def test_query_by_function(self):
        """Test querying by function."""
        # Add finding for function
        finding = Finding(
            finding_id="",
            vulnerability_type="reentrancy",
            severity=Severity.HIGH,
            title="Test",
            description="Test",
            target_function="withdraw",
        )
        self.memory.add_finding(finding)

        result = self.memory.query_by_function("withdraw")
        self.assertEqual(len(result["findings"]), 1)

    def test_statistics(self):
        """Test statistics generation."""
        # Add some data
        self.memory.add_finding(Finding(
            finding_id="",
            vulnerability_type="test",
            severity=Severity.HIGH,
            title="Test",
            description="Test",
            target_function="test",
        ))
        self.memory.add_hypothesis(Hypothesis(
            hypothesis_id="",
            vulnerability_type="test",
            description="Test",
            target_function="test",
        ))

        stats = self.memory.get_statistics()
        self.assertEqual(stats["total_findings"], 1)
        self.assertEqual(stats["total_hypotheses"], 1)


class TestTaskBoard(unittest.TestCase):
    """Tests for TaskBoard."""

    def setUp(self):
        self.board = TaskBoard()

    def test_create_task(self):
        """Test task creation."""
        task = self.board.create_task(
            task_type=TaskType.SCAN_FUNCTION,
            target="withdraw",
            description="Scan withdraw function",
            priority=TaskPriority.HIGH,
        )

        self.assertIsNotNone(task.task_id)
        self.assertEqual(task.task_type, TaskType.SCAN_FUNCTION)
        self.assertEqual(task.status, TaskStatus.PENDING)

    def test_claim_task(self):
        """Test claiming a task."""
        self.board.create_task(
            task_type=TaskType.SCAN_FUNCTION,
            target="test",
            description="Test task",
        )

        task = self.board.claim_task("agent-001")

        self.assertIsNotNone(task)
        self.assertEqual(task.status, TaskStatus.CLAIMED)
        self.assertEqual(task.claimed_by, "agent-001")

    def test_claim_with_capabilities(self):
        """Test claiming task with capability requirements."""
        self.board.create_task(
            task_type=TaskType.SCAN_FUNCTION,
            target="test",
            description="Test",
            required_capabilities={"scan", "analyze"},
        )

        # Agent without capabilities can't claim
        task = self.board.claim_task("agent-001", capabilities={"scan"})
        self.assertIsNone(task)

        # Agent with capabilities can claim
        task = self.board.claim_task("agent-002", capabilities={"scan", "analyze"})
        self.assertIsNotNone(task)

    def test_complete_task(self):
        """Test completing a task."""
        self.board.create_task(
            task_type=TaskType.SCAN_FUNCTION,
            target="test",
            description="Test",
        )

        task = self.board.claim_task("agent-001")
        result = TaskResult(
            task_id=task.task_id,
            success=True,
            result_type="scan",
            result_data={"findings": []},
            agent_id="agent-001",
        )

        success = self.board.complete_task(task.task_id, "agent-001", result)
        self.assertTrue(success)
        self.assertEqual(task.status, TaskStatus.COMPLETED)

    def test_fail_and_retry(self):
        """Test task failure and retry."""
        task = self.board.create_task(
            task_type=TaskType.SCAN_FUNCTION,
            target="test",
            description="Test",
        )

        claimed = self.board.claim_task("agent-001")
        self.board.fail_task(claimed.task_id, "agent-001", "Test error")

        # Should be back in queue for retry
        self.assertEqual(task.retry_count, 1)
        self.assertEqual(task.status, TaskStatus.PENDING)

    def test_priority_ordering(self):
        """Test priority-based task ordering."""
        self.board.create_task(
            task_type=TaskType.SCAN_FUNCTION,
            target="low",
            description="Low priority",
            priority=TaskPriority.LOW,
        )
        self.board.create_task(
            task_type=TaskType.SCAN_FUNCTION,
            target="critical",
            description="Critical",
            priority=TaskPriority.CRITICAL,
        )

        # Should get critical first
        task = self.board.claim_task("agent-001")
        self.assertEqual(task.target, "critical")

    def test_task_dependencies(self):
        """Test task dependencies."""
        task1 = self.board.create_task(
            task_type=TaskType.SCAN_FUNCTION,
            target="first",
            description="First task",
        )
        task2 = self.board.create_task(
            task_type=TaskType.ANALYZE_FINDING,
            target="second",
            description="Second task",
            depends_on=[task1.task_id],
        )

        # Task2 should be blocked
        self.assertEqual(task2.status, TaskStatus.BLOCKED)

        # Complete task1
        claimed = self.board.claim_task("agent-001")
        result = TaskResult(
            task_id=claimed.task_id,
            success=True,
            result_type="scan",
            result_data={},
            agent_id="agent-001",
        )
        self.board.complete_task(claimed.task_id, "agent-001", result)

        # Task2 should be unblocked
        self.assertEqual(task2.status, TaskStatus.PENDING)

    def test_statistics(self):
        """Test board statistics."""
        self.board.create_task(
            task_type=TaskType.SCAN_FUNCTION,
            target="test",
            description="Test",
        )

        stats = self.board.get_statistics()
        self.assertEqual(stats["total_tasks"], 1)
        self.assertEqual(stats["pending"], 1)


class TestAgents(unittest.TestCase):
    """Tests for swarm agents."""

    def setUp(self):
        self.memory = SharedMemory()
        self.board = TaskBoard()

    def test_scanner_agent_creation(self):
        """Test scanner agent creation."""
        scanner = ScannerAgent("scanner-001")

        self.assertEqual(scanner.role, AgentRole.SCANNER)
        self.assertIn("scan", scanner.capabilities)
        self.assertEqual(scanner.state, AgentState.IDLE)

    def test_agent_registration(self):
        """Test agent registration."""
        scanner = ScannerAgent("scanner-001")
        scanner.register(self.memory, self.board)

        self.assertEqual(scanner.shared_memory, self.memory)
        self.assertEqual(scanner.task_board, self.board)

    def test_scanner_process_task(self):
        """Test scanner processing a task."""
        scanner = ScannerAgent("scanner-001")
        scanner.register(self.memory, self.board)

        task = SwarmTask(
            task_id="task-001",
            task_type=TaskType.SCAN_FUNCTION,
            priority=TaskPriority.HIGH,
            description="Scan test function",
            target="withdraw",
            parameters={
                "function_data": {
                    "has_external_call": True,
                    "state_write_after_external": True,
                    "has_reentrancy_guard": False,
                }
            },
        )

        result = scanner.process_task(task)

        self.assertTrue(result.success)
        self.assertEqual(result.result_type, "scan_result")
        # Should have proposed hypotheses
        self.assertGreater(len(self.memory.hypotheses), 0)

    def test_analyzer_agent(self):
        """Test analyzer agent."""
        analyzer = AnalyzerAgent("analyzer-001")
        analyzer.register(self.memory, self.board)

        # Add a hypothesis to analyze
        hypothesis = Hypothesis(
            hypothesis_id="",
            vulnerability_type="reentrancy",
            description="Test",
            target_function="withdraw",
            confidence=0.7,
        )
        self.memory.add_hypothesis(hypothesis)

        task = SwarmTask(
            task_id="task-001",
            task_type=TaskType.ANALYZE_FINDING,
            priority=TaskPriority.HIGH,
            description="Analyze",
            target="withdraw",
        )

        result = analyzer.process_task(task)
        self.assertTrue(result.success)

    def test_verifier_agent(self):
        """Test verifier agent."""
        verifier = VerifierAgent("verifier-001")
        verifier.register(self.memory, self.board)

        # Add a high-confidence hypothesis
        hypothesis = Hypothesis(
            hypothesis_id="",
            vulnerability_type="reentrancy",
            description="Confirmed reentrancy",
            target_function="withdraw",
            confidence=0.9,
        )
        hyp_id = self.memory.add_hypothesis(hypothesis)

        task = SwarmTask(
            task_id="task-001",
            task_type=TaskType.VERIFY_HYPOTHESIS,
            priority=TaskPriority.HIGH,
            description="Verify",
            target=hyp_id,
        )

        result = verifier.process_task(task)

        self.assertTrue(result.success)
        # High confidence hypothesis should be promoted to finding
        self.assertEqual(len(self.memory.findings), 1)

    def test_exploiter_agent(self):
        """Test exploiter agent."""
        exploiter = ExploiterAgent("exploiter-001")
        exploiter.register(self.memory, self.board)

        # Add a finding to exploit
        finding = Finding(
            finding_id="",
            vulnerability_type="reentrancy",
            severity=Severity.HIGH,
            title="Reentrancy",
            description="Test",
            target_function="withdraw",
        )
        finding_id = self.memory.add_finding(finding)

        task = SwarmTask(
            task_id="task-001",
            task_type=TaskType.BUILD_EXPLOIT,
            priority=TaskPriority.MEDIUM,
            description="Build exploit",
            target=finding_id,
        )

        result = exploiter.process_task(task)

        self.assertTrue(result.success)
        # Should have generated exploit code
        self.assertIsNotNone(self.memory.findings[finding_id].exploit_code)

    def test_reporter_agent(self):
        """Test reporter agent."""
        reporter = ReporterAgent("reporter-001")
        reporter.register(self.memory, self.board)

        # Add some findings
        self.memory.add_finding(Finding(
            finding_id="",
            vulnerability_type="reentrancy",
            severity=Severity.HIGH,
            title="Test Finding",
            description="Test",
            target_function="withdraw",
        ))

        task = SwarmTask(
            task_id="task-001",
            task_type=TaskType.WRITE_REPORT,
            priority=TaskPriority.LOW,
            description="Write report",
            target="final_report",
        )

        result = reporter.process_task(task)

        self.assertTrue(result.success)
        self.assertIn("report", result.result_data)

    def test_agent_propose_hypothesis(self):
        """Test agent proposing hypothesis."""
        scanner = ScannerAgent("scanner-001")
        scanner.register(self.memory, self.board)

        hyp_id = scanner.propose_hypothesis(
            vuln_type="reentrancy",
            description="Found reentrancy pattern",
            target_function="withdraw",
            confidence=0.8,
        )

        self.assertIsNotNone(hyp_id)
        self.assertIn(hyp_id, self.memory.hypotheses)

    def test_agent_claim_work(self):
        """Test agent claiming work."""
        scanner = ScannerAgent("scanner-001")
        scanner.register(self.memory, self.board)

        # Create a task
        self.board.create_task(
            task_type=TaskType.SCAN_FUNCTION,
            target="test",
            description="Test",
            required_capabilities={"scan"},
        )

        # Claim it
        task = scanner.claim_work()

        self.assertIsNotNone(task)
        self.assertEqual(scanner.state, AgentState.WORKING)


class TestSwarmCoordinator(unittest.TestCase):
    """Tests for SwarmCoordinator."""

    def setUp(self):
        self.config = CoordinatorConfig(
            num_scanners=1,
            num_analyzers=1,
            num_exploiters=1,
            num_verifiers=1,
            num_reporters=1,
            max_iterations=10,
            convergence_threshold=2,
        )

    def test_coordinator_initialization(self):
        """Test coordinator initialization."""
        coordinator = SwarmCoordinator(self.config)
        coordinator.initialize()

        self.assertEqual(coordinator.status, SwarmStatus.READY)
        self.assertEqual(len(coordinator.agents), 5)  # 5 agent types

    def test_add_initial_tasks(self):
        """Test adding initial tasks."""
        coordinator = SwarmCoordinator(self.config)
        coordinator.initialize()

        functions = [
            {"name": "withdraw", "visibility": "public", "writes_state": True},
            {"name": "deposit", "visibility": "public", "writes_state": True},
        ]
        coordinator.add_initial_tasks(functions)

        self.assertEqual(coordinator.metrics.tasks_created, 2)

    def test_run_iteration(self):
        """Test running a single iteration."""
        coordinator = SwarmCoordinator(self.config)
        coordinator.initialize()

        functions = [{"name": "test", "visibility": "public"}]
        coordinator.add_initial_tasks(functions)

        has_more = coordinator.run_iteration()

        self.assertFalse(has_more)  # Only one task, should complete quickly
        self.assertEqual(coordinator.metrics.iterations, 1)

    def test_run_to_completion(self):
        """Test running swarm to completion."""
        coordinator = SwarmCoordinator(self.config)
        coordinator.initialize()

        functions = [
            {"name": "withdraw", "has_external_call": True, "state_write_after_external": True},
        ]
        coordinator.add_initial_tasks(functions)

        metrics = coordinator.run(max_iterations=5)

        self.assertEqual(coordinator.status, SwarmStatus.STOPPED)
        self.assertGreater(metrics.iterations, 0)

    def test_get_agents_by_role(self):
        """Test getting agents by role."""
        coordinator = SwarmCoordinator(self.config)
        coordinator.initialize()

        scanners = coordinator.get_agents_by_role(AgentRole.SCANNER)
        self.assertEqual(len(scanners), 1)

    def test_stop_swarm(self):
        """Test stopping swarm."""
        coordinator = SwarmCoordinator(self.config)
        coordinator.initialize()
        coordinator.status = SwarmStatus.RUNNING

        coordinator.stop()

        self.assertEqual(coordinator.status, SwarmStatus.STOPPED)

    def test_pause_resume(self):
        """Test pausing and resuming swarm."""
        coordinator = SwarmCoordinator(self.config)
        coordinator.initialize()

        coordinator.pause()
        self.assertEqual(coordinator.status, SwarmStatus.PAUSED)

        coordinator.resume()
        self.assertEqual(coordinator.status, SwarmStatus.RUNNING)

    def test_statistics(self):
        """Test statistics generation."""
        coordinator = SwarmCoordinator(self.config)
        coordinator.initialize()

        stats = coordinator.get_statistics()

        self.assertEqual(stats["status"], "ready")
        self.assertIn("agents", stats)
        self.assertIn("metrics", stats)


class TestSwarmSession(unittest.TestCase):
    """Tests for SwarmSession."""

    def test_session_creation(self):
        """Test session creation."""
        session = SwarmSession()

        self.assertIsNotNone(session.session_id)
        self.assertEqual(session.status.value, "created")

    def test_session_configuration(self):
        """Test session configuration."""
        config = SessionConfig(
            session_name="test_audit",
            coordinator_config=CoordinatorConfig(
                num_scanners=1,
                num_analyzers=1,
            ),
        )
        session = SwarmSession(config)

        functions = [
            {"name": "test", "visibility": "public"},
        ]
        session.configure(functions)

        self.assertEqual(session.status.value, "configured")
        self.assertEqual(len(session.functions_to_audit), 1)

    def test_session_run(self):
        """Test running a session."""
        config = SessionConfig(
            coordinator_config=CoordinatorConfig(
                num_scanners=1,
                num_analyzers=1,
                num_exploiters=1,
                num_verifiers=1,
                num_reporters=1,
                max_iterations=5,
            ),
        )
        session = SwarmSession(config)

        functions = [
            {"name": "withdraw", "has_external_call": True},
        ]
        session.configure(functions)
        result = session.run(max_iterations=3)

        self.assertEqual(result.status.value, "completed")
        self.assertIsNotNone(result.report)

    def test_session_report_generation(self):
        """Test report generation."""
        config = SessionConfig(
            session_name="test_audit",
            auto_generate_report=True,
            coordinator_config=CoordinatorConfig(
                num_scanners=1,
                num_analyzers=1,
                num_exploiters=1,
                num_verifiers=1,
                num_reporters=1,
                max_iterations=5,
            ),
        )
        session = SwarmSession(config)

        functions = [{"name": "test"}]
        session.configure(functions)
        result = session.run(max_iterations=3)

        self.assertIsNotNone(result.report)
        self.assertEqual(result.report.session_name, "test_audit")

    def test_session_progress(self):
        """Test getting session progress."""
        session = SwarmSession()
        functions = [{"name": "test"}]
        session.configure(functions)

        progress = session.get_progress()

        self.assertEqual(progress["status"], "configured")


class TestAuditReport(unittest.TestCase):
    """Tests for AuditReport."""

    def test_report_creation(self):
        """Test report creation."""
        report = AuditReport(
            report_id="report-001",
            session_name="test",
            generated_at=datetime.now(),
            runtime_seconds=60.0,
            total_functions_scanned=10,
            total_findings=5,
            critical_findings=1,
            high_findings=2,
            medium_findings=2,
            low_findings=0,
            findings=[],
            recommendations=["Test recommendation"],
            metrics={},
            agent_contributions={},
        )

        self.assertEqual(report.total_findings, 5)
        self.assertIsNotNone(report.get_risk_score())

    def test_risk_score_calculation(self):
        """Test risk score calculation."""
        report = AuditReport(
            report_id="report-001",
            session_name="test",
            generated_at=datetime.now(),
            runtime_seconds=60.0,
            total_functions_scanned=10,
            total_findings=3,
            critical_findings=1,
            high_findings=1,
            medium_findings=1,
            low_findings=0,
            findings=[],
            recommendations=[],
            metrics={},
            agent_contributions={},
        )

        risk = report.get_risk_score()
        self.assertGreater(risk, 0)

    def test_grade_calculation(self):
        """Test grade calculation."""
        # Low risk = good grade
        low_risk = AuditReport(
            report_id="report-001",
            session_name="test",
            generated_at=datetime.now(),
            runtime_seconds=60.0,
            total_functions_scanned=10,
            total_findings=1,
            critical_findings=0,
            high_findings=0,
            medium_findings=0,
            low_findings=1,
            findings=[],
            recommendations=[],
            metrics={},
            agent_contributions={},
        )
        self.assertIn(low_risk.get_grade(), ["A+", "A"])

        # High risk = bad grade
        high_risk = AuditReport(
            report_id="report-002",
            session_name="test",
            generated_at=datetime.now(),
            runtime_seconds=60.0,
            total_functions_scanned=2,
            total_findings=5,
            critical_findings=3,
            high_findings=2,
            medium_findings=0,
            low_findings=0,
            findings=[],
            recommendations=[],
            metrics={},
            agent_contributions={},
        )
        self.assertIn(high_risk.get_grade(), ["D", "F"])

    def test_markdown_generation(self):
        """Test markdown report generation."""
        report = AuditReport(
            report_id="report-001",
            session_name="test_audit",
            generated_at=datetime.now(),
            runtime_seconds=60.0,
            total_functions_scanned=5,
            total_findings=1,
            critical_findings=0,
            high_findings=1,
            medium_findings=0,
            low_findings=0,
            findings=[{
                "title": "Test Finding",
                "severity": "high",
                "vulnerability_type": "reentrancy",
                "target_function": "withdraw",
                "confidence": 0.9,
                "description": "Test description",
            }],
            recommendations=["Fix the issue"],
            metrics={"iterations": 5},
            agent_contributions={"scanner-001": 3},
        )

        markdown = report.to_markdown()

        self.assertIn("# Security Audit Report", markdown)
        self.assertIn("Test Finding", markdown)
        self.assertIn("HIGH", markdown)


class TestEvidence(unittest.TestCase):
    """Tests for Evidence."""

    def test_evidence_creation(self):
        """Test evidence creation."""
        evidence = Evidence(
            evidence_id="evd-001",
            evidence_type="code_snippet",
            content="msg.sender.call{value: amount}()",
            source_agent="scanner-001",
            confidence=0.8,
        )

        self.assertEqual(evidence.evidence_type, "code_snippet")
        self.assertEqual(evidence.confidence, 0.8)


class TestHypothesis(unittest.TestCase):
    """Tests for Hypothesis."""

    def test_hypothesis_consensus_score(self):
        """Test consensus score calculation."""
        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            vulnerability_type="test",
            description="Test",
            target_function="test",
        )

        # Add support
        hypothesis.add_support("agent-1")
        hypothesis.add_support("agent-2")
        hypothesis.add_support("agent-3")

        # Add opposition
        hypothesis.add_opposition("agent-4")

        consensus = hypothesis.get_consensus_score()
        self.assertEqual(consensus, 0.75)  # 3/4 agree


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete swarm system."""

    def test_full_audit_pipeline(self):
        """Test a complete audit pipeline."""
        config = SessionConfig(
            session_name="integration_test",
            coordinator_config=CoordinatorConfig(
                num_scanners=2,
                num_analyzers=1,
                num_exploiters=1,
                num_verifiers=1,
                num_reporters=1,
                max_iterations=10,
                convergence_threshold=3,
            ),
        )

        session = SwarmSession(config)

        # Simulate a vulnerable contract
        functions = [
            {
                "name": "withdraw",
                "visibility": "public",
                "has_external_call": True,
                "state_write_after_external": True,
                "has_reentrancy_guard": False,
                "writes_state": True,
            },
            {
                "name": "deposit",
                "visibility": "public",
                "writes_state": True,
                "has_access_gate": True,
            },
            {
                "name": "getBalance",
                "visibility": "public",
                "writes_state": False,
            },
        ]

        session.configure(functions)
        result = session.run(max_iterations=5)

        self.assertTrue(result.is_successful())
        self.assertIsNotNone(result.report)
        self.assertEqual(result.report.total_functions_scanned, 3)

    def test_swarm_convergence(self):
        """Test that swarm converges when no new findings."""
        config = SessionConfig(
            coordinator_config=CoordinatorConfig(
                num_scanners=1,
                num_analyzers=1,
                num_verifiers=1,
                num_exploiters=1,
                num_reporters=1,
                max_iterations=20,
                convergence_threshold=2,
            ),
        )

        session = SwarmSession(config)

        # Safe functions - should converge quickly
        functions = [
            {"name": "safe1", "visibility": "internal"},
            {"name": "safe2", "visibility": "private"},
        ]

        session.configure(functions)
        result = session.run()

        # Should converge before max iterations
        self.assertLess(result.metrics.iterations, 20)

    def test_multi_agent_collaboration(self):
        """Test that multiple agents collaborate."""
        coordinator = SwarmCoordinator(CoordinatorConfig(
            num_scanners=2,
            num_analyzers=2,
            num_verifiers=2,
            num_exploiters=1,
            num_reporters=1,
            max_iterations=10,
        ))
        coordinator.initialize()

        # All agents should be registered
        self.assertEqual(len(coordinator.agents), 8)

        # All agents should share memory
        for agent in coordinator.agents.values():
            self.assertEqual(agent.shared_memory, coordinator.shared_memory)


if __name__ == "__main__":
    unittest.main()
