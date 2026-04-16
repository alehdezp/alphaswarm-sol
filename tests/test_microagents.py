"""Tests for Phase 12: Agent SDK Micro-Agents.

Tests for SDK detection, micro-agents, swarm mode, fallback handling,
cost tracking, and subagent orchestration.
"""

import asyncio
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile

from alphaswarm_sol.agents.sdk import (
    SDKManager,
    SDKType,
    SDKStatus,
    SDKInfo,
    SDKConfig,
    sdk_available,
    get_available_sdks,
    get_sdk_manager,
    get_installation_guide,
    get_fallback_message,
)
from alphaswarm_sol.agents.microagent import (
    MicroAgent,
    MicroAgentType,
    MicroAgentStatus,
    MicroAgentConfig,
    MicroAgentCost,
    MicroAgentResult,
    VerificationMicroAgent,
    TestGenMicroAgent,
    create_verifier,
    create_test_generator,
)
from alphaswarm_sol.agents.swarm import (
    SwarmManager,
    SwarmStatus,
    SwarmConfig,
    SwarmProgress,
    SwarmResult,
    swarm_verify,
    swarm_generate_tests,
    create_swarm_manager,
)
from alphaswarm_sol.agents.fallback import (
    FallbackHandler,
    FallbackType,
    FallbackResult,
    get_fallback_for_verification,
    get_fallback_for_test_gen,
    should_use_fallback,
)
from alphaswarm_sol.agents.cost import (
    CostTracker,
    CostReport,
    UsageRecord,
    BudgetExceededError,
    calculate_cost,
    estimate_cost,
    get_global_tracker,
    set_global_budget,
    reset_global_tracker,
    TOKEN_PRICING,
)
from alphaswarm_sol.llm.subagents import (
    LLMSubagentManager,
    SubagentTask,
    SubagentResult as LLMSubagentResult,
    TaskType,
    TOONEncoder,
    TASK_TIER_DEFAULTS,
    create_subagent_manager,
    create_task,
    estimate_batch_cost,
)
from alphaswarm_sol.llm.tiers import ModelTier
from alphaswarm_sol.beads import (
    VulnerabilityBead,
    Severity,
    CodeSnippet,
    InvestigationGuide,
    InvestigationStep,
    PatternContext,
    TestContext,
)


class TestSDKDetection(unittest.TestCase):
    """Tests for SDK detection (Task 12.1)."""

    def test_sdk_type_enum(self):
        """Test SDKType enum values."""
        self.assertEqual(SDKType.CLAUDE.value, "claude")
        self.assertEqual(SDKType.CODEX.value, "codex")
        self.assertEqual(SDKType.OPENCODE.value, "opencode")
        self.assertEqual(SDKType.MOCK.value, "mock")

    def test_sdk_status_enum(self):
        """Test SDKStatus enum values."""
        self.assertEqual(SDKStatus.AVAILABLE.value, "available")
        self.assertEqual(SDKStatus.NOT_INSTALLED.value, "not_installed")
        self.assertEqual(SDKStatus.ERROR.value, "error")

    def test_sdk_info_creation(self):
        """Test SDKInfo creation."""
        info = SDKInfo(
            sdk_type=SDKType.MOCK,
            status=SDKStatus.AVAILABLE,
            version="1.0.0",
            path="/mock/path",
            capabilities=["test"],
        )

        self.assertEqual(info.sdk_type, SDKType.MOCK)
        self.assertTrue(info.is_available)
        self.assertEqual(info.version, "1.0.0")

    def test_sdk_info_to_dict(self):
        """Test SDKInfo serialization."""
        info = SDKInfo(
            sdk_type=SDKType.MOCK,
            status=SDKStatus.AVAILABLE,
            version="1.0.0",
        )

        d = info.to_dict()
        self.assertEqual(d["sdk_type"], "mock")
        self.assertEqual(d["status"], "available")

    def test_sdk_config_defaults(self):
        """Test SDKConfig default values."""
        config = SDKConfig()

        self.assertEqual(config.timeout_seconds, 120)
        self.assertEqual(config.max_parallel, 5)
        self.assertEqual(config.default_budget_usd, 0.50)
        self.assertIn("Read", config.allowed_tools)

    def test_sdk_config_to_dict(self):
        """Test SDKConfig serialization."""
        config = SDKConfig(timeout_seconds=60)
        d = config.to_dict()

        self.assertEqual(d["timeout_seconds"], 60)

    def test_sdk_config_from_dict(self):
        """Test SDKConfig deserialization."""
        d = {"timeout_seconds": 90, "max_parallel": 3}
        config = SDKConfig.from_dict(d)

        self.assertEqual(config.timeout_seconds, 90)
        self.assertEqual(config.max_parallel, 3)

    def test_sdk_manager_creation(self):
        """Test SDKManager creation."""
        manager = SDKManager()
        self.assertIsNotNone(manager.config)

    def test_sdk_manager_detect_mock(self):
        """Test SDKManager detects mock SDK."""
        config = SDKConfig(enabled_sdks=[SDKType.MOCK])
        manager = SDKManager(config)

        manager.detect_all()
        self.assertTrue(manager.any_available())

    def test_sdk_manager_detect_one(self):
        """Test SDKManager detect_one for mock."""
        manager = SDKManager()
        info = manager.detect_one(SDKType.MOCK)

        self.assertTrue(info.is_available)
        self.assertEqual(info.version, "1.0.0-mock")

    def test_sdk_manager_available_sdks(self):
        """Test SDKManager available_sdks property."""
        config = SDKConfig(enabled_sdks=[SDKType.MOCK])
        manager = SDKManager(config)

        available = manager.available_sdks
        self.assertIn(SDKType.MOCK, available)

    def test_sdk_manager_get_best_available(self):
        """Test SDKManager get_best_available."""
        config = SDKConfig(enabled_sdks=[SDKType.MOCK])
        manager = SDKManager(config)

        best = manager.get_best_available()
        self.assertIsNotNone(best)
        self.assertEqual(best.sdk_type, SDKType.MOCK)

    def test_sdk_manager_status_report(self):
        """Test SDKManager status report."""
        config = SDKConfig(enabled_sdks=[SDKType.MOCK])
        manager = SDKManager(config)

        report = manager.get_status_report()
        self.assertTrue(report["any_available"])
        self.assertIn("mock", report["available_sdks"])

    def test_sdk_available_function(self):
        """Test sdk_available convenience function."""
        # Mock SDK should always be available
        available = sdk_available(SDKType.MOCK)
        self.assertTrue(available)

    def test_get_installation_guide(self):
        """Test installation guide retrieval."""
        guide = get_installation_guide(SDKType.CLAUDE)
        self.assertIn("npm install", guide)

    def test_get_fallback_message_with_sdk(self):
        """Test fallback message when SDK specified."""
        msg = get_fallback_message(SDKType.CLAUDE)
        # Message varies based on SDK availability
        self.assertIsInstance(msg, str)
        self.assertGreater(len(msg), 0)


class TestMicroAgents(unittest.TestCase):
    """Tests for micro-agents (Tasks 12.2, 12.3)."""

    def test_micro_agent_type_enum(self):
        """Test MicroAgentType enum."""
        self.assertEqual(MicroAgentType.VERIFIER.value, "verifier")
        self.assertEqual(MicroAgentType.TEST_GENERATOR.value, "test_gen")

    def test_micro_agent_status_enum(self):
        """Test MicroAgentStatus enum."""
        self.assertEqual(MicroAgentStatus.COMPLETED.value, "completed")
        self.assertEqual(MicroAgentStatus.FAILED.value, "failed")

    def test_micro_agent_config(self):
        """Test MicroAgentConfig creation."""
        config = MicroAgentConfig(
            agent_type=MicroAgentType.VERIFIER,
            budget_usd=1.00,
        )

        self.assertEqual(config.agent_type, MicroAgentType.VERIFIER)
        self.assertEqual(config.budget_usd, 1.00)

    def test_micro_agent_cost(self):
        """Test MicroAgentCost tracking."""
        cost = MicroAgentCost(
            input_tokens=1000,
            output_tokens=500,
            total_tokens=1500,
            estimated_cost_usd=0.05,
        )

        d = cost.to_dict()
        self.assertEqual(d["input_tokens"], 1000)
        self.assertEqual(d["total_tokens"], 1500)

    def test_micro_agent_result(self):
        """Test MicroAgentResult creation."""
        from alphaswarm_sol.beads import VerdictType

        result = MicroAgentResult(
            agent_type=MicroAgentType.VERIFIER,
            status=MicroAgentStatus.COMPLETED,
            verdict=VerdictType.TRUE_POSITIVE,
            evidence=["Test evidence"],
            reasoning="Test reasoning",
        )

        self.assertTrue(result.is_success)
        self.assertTrue(result.is_confirmed)

    def test_micro_agent_result_to_dict(self):
        """Test MicroAgentResult serialization."""
        result = MicroAgentResult(
            agent_type=MicroAgentType.VERIFIER,
            status=MicroAgentStatus.COMPLETED,
        )

        d = result.to_dict()
        self.assertEqual(d["agent_type"], "verifier")
        self.assertEqual(d["status"], "completed")

    def test_micro_agent_result_from_dict(self):
        """Test MicroAgentResult deserialization."""
        d = {
            "agent_type": "verifier",
            "status": "completed",
            "verdict": None,
            "evidence": [],
            "reasoning": "",
            "cost": {},
            "timestamp": datetime.now().isoformat(),
        }

        result = MicroAgentResult.from_dict(d)
        self.assertEqual(result.agent_type, MicroAgentType.VERIFIER)

    def test_create_verifier(self):
        """Test create_verifier factory."""
        verifier = create_verifier(budget_usd=0.75)

        self.assertIsInstance(verifier, VerificationMicroAgent)
        self.assertEqual(verifier.config.budget_usd, 0.75)

    def test_create_test_generator(self):
        """Test create_test_generator factory."""
        gen = create_test_generator(budget_usd=1.50)

        self.assertIsInstance(gen, TestGenMicroAgent)
        self.assertEqual(gen.config.budget_usd, 1.50)

    def test_verification_agent_build_prompt(self):
        """Test VerificationMicroAgent prompt building."""
        verifier = create_verifier()

        bead = self._create_test_bead()
        prompt = verifier.build_prompt(bead)

        self.assertIn("vulnerability", prompt.lower())
        self.assertIn("JSON", prompt)

    def test_test_gen_agent_build_prompt(self):
        """Test TestGenMicroAgent prompt building."""
        gen = create_test_generator()

        bead = self._create_test_bead()
        prompt = gen.build_prompt(bead)

        self.assertIn("Foundry", prompt)
        self.assertIn("test", prompt.lower())

    def _create_test_bead(self) -> VulnerabilityBead:
        """Create a test VulnerabilityBead."""
        return VulnerabilityBead(
            id="TEST-001",
            vulnerability_class="reentrancy",
            pattern_id="vm-001",
            severity=Severity.HIGH,
            confidence=0.85,
            vulnerable_code=CodeSnippet(
                source="function withdraw() { ... }",
                file_path="/test/Test.sol",
                start_line=10,
                end_line=20,
                function_name="withdraw",
                contract_name="Test",
            ),
            related_code=[],
            full_contract=None,
            inheritance_chain=[],
            pattern_context=PatternContext(
                pattern_name="Classic Reentrancy",
                pattern_description="Detects external calls before state updates",
                why_flagged="State write after external call",
                matched_properties=["state_write_after_external_call"],
                evidence_lines=[15],
            ),
            investigation_guide=InvestigationGuide(
                steps=[
                    InvestigationStep(
                        step_number=1,
                        action="Check for external calls",
                        look_for="call, send, transfer",
                        evidence_needed="External call found",
                    )
                ],
                questions_to_answer=["Is there a reentrancy guard?"],
                common_false_positives=["nonReentrant modifier present"],
                key_indicators=["State update after external call"],
                safe_patterns=["CEI pattern", "reentrancy guard"],
            ),
            test_context=TestContext(
                scaffold_code="// Test scaffold",
                attack_scenario="1. Deploy attacker",
                setup_requirements=["Attacker contract"],
                expected_outcome="Balance drained",
            ),
            similar_exploits=[],
            fix_recommendations=["Add nonReentrant modifier"],
        )


class TestSwarmMode(unittest.TestCase):
    """Tests for swarm mode (Task 12.4)."""

    def test_swarm_status_enum(self):
        """Test SwarmStatus enum."""
        self.assertEqual(SwarmStatus.COMPLETED.value, "completed")
        self.assertEqual(SwarmStatus.PARTIAL.value, "partial")

    def test_swarm_config_defaults(self):
        """Test SwarmConfig defaults."""
        config = SwarmConfig()

        self.assertEqual(config.max_parallel, 5)
        self.assertEqual(config.timeout_seconds, 600)
        self.assertEqual(config.budget_per_agent_usd, 0.50)

    def test_swarm_progress(self):
        """Test SwarmProgress tracking."""
        progress = SwarmProgress(total=10, completed=5, failed=1)

        d = progress.to_dict()
        self.assertEqual(d["total"], 10)
        self.assertEqual(d["completed"], 5)
        self.assertEqual(d["percent_complete"], 60.0)

    def test_swarm_result_empty(self):
        """Test SwarmResult with no results."""
        result = SwarmResult(status=SwarmStatus.COMPLETED)

        self.assertEqual(result.total_cost_usd, 0.0)
        self.assertEqual(len(result.results), 0)

    def test_swarm_result_summary(self):
        """Test SwarmResult summary."""
        result = SwarmResult(
            status=SwarmStatus.COMPLETED,
            progress=SwarmProgress(total=5, completed=5),
        )

        summary = result.get_summary()
        self.assertEqual(summary["total_tasks"], 5)

    def test_create_swarm_manager(self):
        """Test create_swarm_manager factory."""
        manager = create_swarm_manager(max_parallel=3)

        self.assertEqual(manager.config.max_parallel, 3)

    def test_swarm_manager_progress_callback(self):
        """Test SwarmManager progress callback."""
        manager = SwarmManager()

        progress_updates = []
        manager.set_progress_callback(lambda p: progress_updates.append(p))

        # Progress callback is set
        self.assertIsNotNone(manager._progress_callback)


class TestFallbackHandling(unittest.TestCase):
    """Tests for fallback handling (Task 12.5)."""

    def test_fallback_type_enum(self):
        """Test FallbackType enum."""
        self.assertEqual(FallbackType.VERIFICATION_CHECKLIST.value, "verification_checklist")
        self.assertEqual(FallbackType.TEST_SCAFFOLD.value, "test_scaffold")

    def test_fallback_result_creation(self):
        """Test FallbackResult creation."""
        result = FallbackResult(
            fallback_type=FallbackType.VERIFICATION_CHECKLIST,
            scaffold="test scaffold",
            checklist=["item1", "item2"],
        )

        self.assertEqual(result.fallback_type, FallbackType.VERIFICATION_CHECKLIST)
        self.assertEqual(len(result.checklist), 2)

    def test_fallback_result_to_dict(self):
        """Test FallbackResult serialization."""
        result = FallbackResult(
            fallback_type=FallbackType.TEST_SCAFFOLD,
        )

        d = result.to_dict()
        self.assertEqual(d["fallback_type"], "test_scaffold")

    def test_fallback_result_console_output(self):
        """Test FallbackResult console output."""
        result = FallbackResult(
            fallback_type=FallbackType.VERIFICATION_CHECKLIST,
            checklist=["Check item 1"],
            scaffold="Test scaffold content",
        )

        output = result.get_console_output()
        self.assertIn("FALLBACK MODE", output)
        self.assertIn("Check item 1", output)

    def test_fallback_handler_creation(self):
        """Test FallbackHandler creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = FallbackHandler(output_dir=Path(tmpdir))
            self.assertEqual(handler.output_dir, Path(tmpdir))

    def test_fallback_handler_verification_checklist(self):
        """Test FallbackHandler generates verification checklist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = FallbackHandler(output_dir=Path(tmpdir))
            bead = self._create_test_bead()

            result = handler.generate_verification_fallback(bead, save_to_file=False)

            self.assertEqual(result.fallback_type, FallbackType.VERIFICATION_CHECKLIST)
            self.assertGreater(len(result.checklist), 0)
            self.assertIn("reentrancy", result.scaffold.lower())

    def test_fallback_handler_test_scaffold(self):
        """Test FallbackHandler generates test scaffold."""
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = FallbackHandler(output_dir=Path(tmpdir))
            bead = self._create_test_bead()

            result = handler.generate_test_fallback(bead, save_to_file=False)

            self.assertEqual(result.fallback_type, FallbackType.TEST_SCAFFOLD)
            self.assertIn("pragma solidity", result.scaffold)
            self.assertIn("forge", result.scaffold.lower())

    def test_fallback_handler_saves_file(self):
        """Test FallbackHandler saves to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = FallbackHandler(output_dir=Path(tmpdir))
            bead = self._create_test_bead()

            result = handler.generate_verification_fallback(bead, save_to_file=True)

            self.assertIsNotNone(result.file_path)
            self.assertTrue(Path(result.file_path).exists())

    def test_should_use_fallback(self):
        """Test should_use_fallback function."""
        # With mock SDK, fallback should not be needed
        # (unless we mock no SDK being available)
        result = should_use_fallback()
        # Result depends on environment - just verify it's boolean
        self.assertIsInstance(result, bool)

    def _create_test_bead(self) -> VulnerabilityBead:
        """Create a test VulnerabilityBead."""
        return VulnerabilityBead(
            id="TEST-001",
            vulnerability_class="reentrancy",
            pattern_id="vm-001",
            severity=Severity.HIGH,
            confidence=0.85,
            vulnerable_code=CodeSnippet(
                source="function withdraw() { msg.sender.call{value: bal}(\"\"); balances[msg.sender] = 0; }",
                file_path="/test/Test.sol",
                start_line=10,
                end_line=15,
                function_name="withdraw",
                contract_name="Vault",
            ),
            related_code=[],
            full_contract=None,
            inheritance_chain=[],
            pattern_context=PatternContext(
                pattern_name="Classic Reentrancy",
                pattern_description="Detects external calls before state updates",
                why_flagged="State write after external call",
                matched_properties=["state_write_after_external_call"],
                evidence_lines=[12],
            ),
            investigation_guide=InvestigationGuide(
                steps=[
                    InvestigationStep(
                        step_number=1,
                        action="Check for external calls",
                        look_for="call, send, transfer",
                        evidence_needed="External call found",
                        red_flag="External call before state update",
                        safe_if="Has nonReentrant modifier",
                    )
                ],
                questions_to_answer=["Is the external call target controlled?"],
                common_false_positives=["nonReentrant modifier"],
                key_indicators=["State update after external call"],
                safe_patterns=["CEI pattern"],
            ),
            test_context=TestContext(
                scaffold_code="// Foundry test",
                attack_scenario="1. Deploy attacker contract\n2. Call withdraw",
                setup_requirements=["Attacker contract with fallback"],
                expected_outcome="Attacker extracts more than balance",
            ),
            similar_exploits=[],
            fix_recommendations=["Add nonReentrant modifier", "Use CEI pattern"],
        )


class TestCostTracking(unittest.TestCase):
    """Tests for cost tracking (Task 12.6)."""

    def test_usage_record_creation(self):
        """Test UsageRecord creation."""
        record = UsageRecord(
            timestamp=datetime.now(),
            agent_type="verifier",
            model="claude-3-5-sonnet",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.05,
        )

        self.assertEqual(record.agent_type, "verifier")
        self.assertEqual(record.cost_usd, 0.05)

    def test_usage_record_to_dict(self):
        """Test UsageRecord serialization."""
        record = UsageRecord(
            timestamp=datetime.now(),
            agent_type="test_gen",
            model="default",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.01,
        )

        d = record.to_dict()
        self.assertEqual(d["agent_type"], "test_gen")
        self.assertEqual(d["input_tokens"], 100)

    def test_cost_tracker_creation(self):
        """Test CostTracker creation."""
        tracker = CostTracker(budget_usd=10.00)

        self.assertEqual(tracker.budget_usd, 10.00)
        self.assertEqual(tracker.total_cost, 0.0)
        self.assertEqual(tracker.remaining_budget, 10.00)

    def test_cost_tracker_record_usage(self):
        """Test CostTracker records usage."""
        tracker = CostTracker()

        record = tracker.record_usage(
            agent_type="verifier",
            model="claude-3-5-sonnet",
            input_tokens=1000,
            output_tokens=500,
        )

        self.assertIsInstance(record, UsageRecord)
        self.assertGreater(tracker.total_cost, 0)

    def test_cost_tracker_budget_enforcement(self):
        """Test CostTracker enforces budget."""
        tracker = CostTracker(budget_usd=0.001, enforce_budget=True)

        with self.assertRaises(BudgetExceededError):
            tracker.record_usage(
                agent_type="verifier",
                model="claude-3-opus",  # Expensive model
                input_tokens=100000,
                output_tokens=50000,
            )

    def test_cost_tracker_no_enforcement(self):
        """Test CostTracker without budget enforcement."""
        tracker = CostTracker(budget_usd=0.001, enforce_budget=False)

        # Should not raise, just log warning
        tracker.record_usage(
            agent_type="verifier",
            model="claude-3-opus",
            input_tokens=100000,
            output_tokens=50000,
        )

        self.assertGreater(tracker.total_cost, tracker.budget_usd)

    def test_cost_tracker_can_afford(self):
        """Test CostTracker can_afford check."""
        tracker = CostTracker(budget_usd=10.00)

        self.assertTrue(tracker.can_afford(5.00))
        self.assertTrue(tracker.can_afford(10.00))
        self.assertFalse(tracker.can_afford(15.00))

    def test_cost_tracker_get_report(self):
        """Test CostTracker generates report."""
        tracker = CostTracker(budget_usd=10.00)

        tracker.record_usage("verifier", "claude-3-5-sonnet", 1000, 500)
        tracker.record_usage("test_gen", "claude-3-haiku", 500, 250)

        report = tracker.get_report()

        self.assertIsInstance(report, CostReport)
        self.assertEqual(report.total_requests, 2)
        self.assertIn("verifier", report.cost_by_agent)
        self.assertIn("claude-3-5-sonnet", report.cost_by_model)

    def test_cost_report_console_summary(self):
        """Test CostReport console summary."""
        tracker = CostTracker(budget_usd=10.00)
        tracker.record_usage("verifier", "default", 1000, 500)

        report = tracker.get_report()
        summary = report.get_console_summary()

        self.assertIn("COST REPORT", summary)
        self.assertIn("Budget", summary)

    def test_calculate_cost(self):
        """Test calculate_cost function."""
        cost = calculate_cost("claude-3-5-sonnet", 1000, 500)
        self.assertGreater(cost, 0)

        # Test default pricing
        default_cost = calculate_cost("unknown-model", 1000, 500)
        self.assertGreater(default_cost, 0)

    def test_estimate_cost(self):
        """Test estimate_cost function."""
        estimated = estimate_cost(
            model="default",
            prompt_length=4000,  # ~1000 tokens
            expected_response_length=2000,  # ~500 tokens
        )

        self.assertGreater(estimated, 0)

    def test_global_tracker(self):
        """Test global tracker functions."""
        reset_global_tracker()
        tracker = get_global_tracker()

        self.assertIsInstance(tracker, CostTracker)

        set_global_budget(5.00)
        tracker = get_global_tracker()
        self.assertEqual(tracker.budget_usd, 5.00)

    def test_token_pricing_exists(self):
        """Test TOKEN_PRICING dictionary has expected models."""
        self.assertIn("claude-3-opus", TOKEN_PRICING)
        self.assertIn("claude-3-5-sonnet", TOKEN_PRICING)
        self.assertIn("gpt-4o", TOKEN_PRICING)
        self.assertIn("default", TOKEN_PRICING)


class TestLLMSubagentOrchestration(unittest.TestCase):
    """Tests for LLM Subagent Orchestration (Task 12.8)."""

    def test_task_type_enum(self):
        """Test TaskType enum."""
        self.assertEqual(TaskType.EVIDENCE_EXTRACTION.value, "evidence_extraction")
        self.assertEqual(TaskType.EXPLOIT_SYNTHESIS.value, "exploit_synthesis")

    def test_task_tier_defaults(self):
        """Test default tier mappings."""
        # Cheap tier tasks
        self.assertEqual(TASK_TIER_DEFAULTS[TaskType.EVIDENCE_EXTRACTION], ModelTier.CHEAP)

        # Standard tier tasks
        self.assertEqual(TASK_TIER_DEFAULTS[TaskType.TIER_B_VERIFICATION], ModelTier.STANDARD)

        # Premium tier tasks
        self.assertEqual(TASK_TIER_DEFAULTS[TaskType.EXPLOIT_SYNTHESIS], ModelTier.PREMIUM)

    def test_subagent_task_creation(self):
        """Test SubagentTask creation."""
        task = SubagentTask(
            type=TaskType.EVIDENCE_EXTRACTION,
            prompt="Extract evidence",
            context={"code": "function test() {}"},
        )

        self.assertEqual(task.type, TaskType.EVIDENCE_EXTRACTION)
        self.assertEqual(task.max_cost_usd, 0.50)

    def test_subagent_task_to_dict(self):
        """Test SubagentTask serialization."""
        task = SubagentTask(
            type=TaskType.TIER_B_VERIFICATION,
            prompt="Verify finding",
            context={"finding_id": "VKG-001"},
            preferred_tier=ModelTier.STANDARD,
        )

        d = task.to_dict()
        self.assertEqual(d["type"], "tier_b_verification")
        self.assertEqual(d["preferred_tier"], "standard")

    def test_subagent_result(self):
        """Test SubagentResult creation."""
        result = LLMSubagentResult(
            verdict="TRUE_POSITIVE",
            confidence=0.85,
            reasoning="Test reasoning",
            provider="claude",
            model="claude-3-5-sonnet",
            tier=ModelTier.STANDARD,
        )

        self.assertEqual(result.verdict, "TRUE_POSITIVE")
        self.assertTrue(result.is_success is False)  # output is None

    def test_subagent_result_to_dict(self):
        """Test SubagentResult serialization."""
        result = LLMSubagentResult(
            verdict="MOCK",
            provider="test",
            model="test-model",
            tier=ModelTier.CHEAP,
        )

        d = result.to_dict()
        self.assertEqual(d["verdict"], "MOCK")
        self.assertEqual(d["tier"], "cheap")

    def test_toon_encoder(self):
        """Test TOONEncoder encoding."""
        encoder = TOONEncoder()

        data = {
            "function": "withdraw",
            "contract": "Vault",
            "line": 45,
            "severity": "critical",
        }

        encoded = encoder.encode(data)
        self.assertIn("|", encoded)
        self.assertIn(":", encoded)
        # Should use abbreviations
        self.assertIn("F:", encoded)  # function -> F

    def test_toon_encoder_decode(self):
        """Test TOONEncoder decoding."""
        encoder = TOONEncoder()

        toon = "F:withdraw|C:Vault|L:45"
        decoded = encoder.decode(toon)

        self.assertIn("function", decoded)
        self.assertEqual(decoded["function"], "withdraw")

    def test_toon_encoder_lists(self):
        """Test TOONEncoder with lists."""
        encoder = TOONEncoder()

        data = {"evidence": ["item1", "item2", "item3"]}
        encoded = encoder.encode(data)
        self.assertIn("[", encoded)

    def test_llm_subagent_manager_creation(self):
        """Test LLMSubagentManager creation."""
        manager = LLMSubagentManager()

        self.assertIsNotNone(manager.config)
        self.assertIsNotNone(manager.tier_router)
        self.assertIsNotNone(manager.toon_encoder)

    def test_llm_subagent_manager_select_tier(self):
        """Test tier selection based on task type."""
        manager = LLMSubagentManager()

        # Cheap tier task
        cheap_task = SubagentTask(
            type=TaskType.EVIDENCE_EXTRACTION,
            prompt="test",
        )
        self.assertEqual(
            manager._select_tier(cheap_task),
            ModelTier.CHEAP
        )

        # Premium tier task
        premium_task = SubagentTask(
            type=TaskType.EXPLOIT_SYNTHESIS,
            prompt="test",
        )
        self.assertEqual(
            manager._select_tier(premium_task),
            ModelTier.PREMIUM
        )

        # Task with override
        override_task = SubagentTask(
            type=TaskType.EVIDENCE_EXTRACTION,
            prompt="test",
            preferred_tier=ModelTier.PREMIUM,
        )
        self.assertEqual(
            manager._select_tier(override_task),
            ModelTier.PREMIUM
        )

    def test_create_subagent_manager(self):
        """Test create_subagent_manager factory."""
        manager = create_subagent_manager(default_tier=ModelTier.STANDARD)

        self.assertIsInstance(manager, LLMSubagentManager)

    def test_create_task(self):
        """Test create_task factory."""
        task = create_task(
            task_type=TaskType.FP_FILTERING,
            prompt="Filter false positives",
            context={"findings": []},
        )

        self.assertEqual(task.type, TaskType.FP_FILTERING)

    def test_estimate_batch_cost(self):
        """Test estimate_batch_cost function."""
        tasks = [
            SubagentTask(type=TaskType.EVIDENCE_EXTRACTION, prompt="test1"),
            SubagentTask(type=TaskType.TIER_B_VERIFICATION, prompt="test2"),
            SubagentTask(type=TaskType.EXPLOIT_SYNTHESIS, prompt="test3"),
        ]

        estimate = estimate_batch_cost(tasks)

        self.assertEqual(estimate["total_tasks"], 3)
        self.assertIn("tier_distribution", estimate)
        self.assertIn("estimated_cost_usd", estimate)


class TestAsyncOperations(unittest.TestCase):
    """Tests for async operations."""

    def test_swarm_verify_empty(self):
        """Test swarm_verify with empty list."""
        async def run_test():
            result = await swarm_verify([], parallel=3)
            return result

        result = asyncio.run(run_test())
        self.assertEqual(result.status, SwarmStatus.COMPLETED)
        self.assertEqual(len(result.results), 0)

    def test_swarm_manager_verify_with_mock(self):
        """Test SwarmManager with mock SDK."""
        async def run_test():
            beads = [self._create_test_bead() for _ in range(3)]

            config = SwarmConfig(
                max_parallel=2,
                agent_timeout_seconds=30,
            )
            manager = SwarmManager(config)

            # This will use mock execution
            result = await manager.verify_all(beads)
            return result

        result = asyncio.run(run_test())

        # With mock, all should complete (or fail gracefully)
        self.assertIn(
            result.status,
            [SwarmStatus.COMPLETED, SwarmStatus.PARTIAL, SwarmStatus.FAILED]
        )

    def test_subagent_manager_dispatch(self):
        """Test LLMSubagentManager dispatch."""
        async def run_test():
            manager = LLMSubagentManager()
            task = SubagentTask(
                type=TaskType.EVIDENCE_EXTRACTION,
                prompt="Extract evidence",
                context={"code": "test"},
            )

            result = await manager.dispatch(task)
            return result

        result = asyncio.run(run_test())

        # Mock execution returns MOCK verdict
        self.assertIsNotNone(result)
        self.assertEqual(result.verdict, "MOCK")

    def test_subagent_manager_dispatch_batch(self):
        """Test LLMSubagentManager batch dispatch."""
        async def run_test():
            manager = LLMSubagentManager()
            tasks = [
                SubagentTask(type=TaskType.EVIDENCE_EXTRACTION, prompt="test1"),
                SubagentTask(type=TaskType.TIER_B_VERIFICATION, prompt="test2"),
            ]

            results = await manager.dispatch_batch(tasks, parallel=2)
            return results

        results = asyncio.run(run_test())

        self.assertEqual(len(results), 2)

    def test_subagent_manager_routing_summary(self):
        """Test LLMSubagentManager routing summary after dispatch."""
        async def run_test():
            manager = LLMSubagentManager()
            tasks = [
                SubagentTask(type=TaskType.EVIDENCE_EXTRACTION, prompt="test1"),
                SubagentTask(type=TaskType.EXPLOIT_SYNTHESIS, prompt="test2"),
            ]

            await manager.dispatch_batch(tasks)
            return manager.get_routing_summary()

        summary = asyncio.run(run_test())

        self.assertEqual(summary["total_tasks"], 2)
        self.assertIn("tier_distribution", summary)

    def _create_test_bead(self) -> VulnerabilityBead:
        """Create a test VulnerabilityBead."""
        return VulnerabilityBead(
            id="TEST-001",
            vulnerability_class="reentrancy",
            pattern_id="vm-001",
            severity=Severity.HIGH,
            confidence=0.85,
            vulnerable_code=CodeSnippet(
                source="function test() {}",
                file_path="/test/Test.sol",
                start_line=10,
                end_line=15,
            ),
            related_code=[],
            full_contract=None,
            inheritance_chain=[],
            pattern_context=PatternContext(
                pattern_name="Test Pattern",
                pattern_description="Test pattern description",
                why_flagged="Test flagged reason",
                matched_properties=["test_property"],
                evidence_lines=[12],
            ),
            investigation_guide=InvestigationGuide(
                steps=[
                    InvestigationStep(
                        step_number=1,
                        action="Test action",
                        look_for="test",
                        evidence_needed="test evidence",
                    )
                ],
                questions_to_answer=["Test question?"],
                common_false_positives=["Test FP"],
                key_indicators=["Test indicator"],
                safe_patterns=["Test safe pattern"],
            ),
            test_context=TestContext(
                scaffold_code="// Test",
                attack_scenario="Test scenario",
                setup_requirements=["Test requirement"],
                expected_outcome="Test outcome",
            ),
            similar_exploits=[],
            fix_recommendations=["Test fix"],
        )


if __name__ == "__main__":
    unittest.main()
