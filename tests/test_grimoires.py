"""Tests for Grimoires & Skills system.

Phase 13: Per-vulnerability testing playbooks.
"""

import json
import tempfile
import unittest
from pathlib import Path

from alphaswarm_sol.grimoires.schema import (
    Grimoire,
    GrimoireProcedure,
    GrimoireResult,
    GrimoireStep,
    GrimoireStepAction,
    GrimoireVerdict,
    StepEvidence,
    ToolsConfig,
    VerdictConfidence,
    VerdictRule,
)
from alphaswarm_sol.grimoires.registry import (
    GrimoireRegistry,
    get_grimoire,
    get_grimoire_for_category,
    get_registry,
    list_grimoires,
    register_grimoire,
    reset_registry,
)
from alphaswarm_sol.grimoires.executor import (
    ExecutionContext,
    GrimoireExecutor,
    StepResult,
)
from alphaswarm_sol.grimoires.skill import (
    Skill,
    SkillParameter,
    SkillRegistry,
    SkillResult,
    SkillStatus,
    get_skill_registry,
    invoke_skill,
    list_skills,
    register_skill,
    reset_skill_registry,
)
from alphaswarm_sol.grimoires.cost import (
    CostTracker,
    CostReport,
    StepCost,
    TokenUsage,
    ModelPricing,
    CostCategory,
    BudgetExceededError,
    create_cost_tracker,
    DEFAULT_PRICING,
)


class TestGrimoireSchema(unittest.TestCase):
    """Test grimoire schema definitions."""

    def test_grimoire_step_action_enum(self):
        """Test GrimoireStepAction enum values."""
        self.assertEqual(GrimoireStepAction.CHECK_GRAPH.value, "check_graph")
        self.assertEqual(GrimoireStepAction.GENERATE_TEST.value, "generate_test")
        self.assertEqual(GrimoireStepAction.EXECUTE_TEST.value, "execute_test")
        self.assertEqual(GrimoireStepAction.EXECUTE_FUZZ.value, "execute_fuzz")
        self.assertEqual(GrimoireStepAction.DETERMINE_VERDICT.value, "determine_verdict")

    def test_grimoire_verdict_enum(self):
        """Test GrimoireVerdict enum values."""
        self.assertEqual(GrimoireVerdict.VULNERABLE.value, "vulnerable")
        self.assertEqual(GrimoireVerdict.SAFE.value, "safe")
        self.assertEqual(GrimoireVerdict.LIKELY_VULNERABLE.value, "likely_vulnerable")
        self.assertEqual(GrimoireVerdict.LIKELY_SAFE.value, "likely_safe")
        self.assertEqual(GrimoireVerdict.UNCERTAIN.value, "uncertain")
        self.assertEqual(GrimoireVerdict.NEEDS_REVIEW.value, "needs_review")

    def test_verdict_confidence_enum(self):
        """Test VerdictConfidence enum values."""
        self.assertEqual(VerdictConfidence.HIGH.value, "high")
        self.assertEqual(VerdictConfidence.MEDIUM.value, "medium")
        self.assertEqual(VerdictConfidence.LOW.value, "low")
        self.assertEqual(VerdictConfidence.UNKNOWN.value, "unknown")

    def test_verdict_rule_creation(self):
        """Test VerdictRule creation and serialization."""
        rule = VerdictRule(
            condition="exploit_successful",
            verdict=GrimoireVerdict.VULNERABLE,
            confidence=VerdictConfidence.HIGH,
            explanation="Test confirmed vulnerability",
        )

        self.assertEqual(rule.condition, "exploit_successful")
        self.assertEqual(rule.verdict, GrimoireVerdict.VULNERABLE)
        self.assertEqual(rule.confidence, VerdictConfidence.HIGH)

        # Test serialization
        data = rule.to_dict()
        self.assertEqual(data["condition"], "exploit_successful")
        self.assertEqual(data["verdict"], "vulnerable")
        self.assertEqual(data["confidence"], "high")

        # Test deserialization
        rule2 = VerdictRule.from_dict(data)
        self.assertEqual(rule2.condition, rule.condition)
        self.assertEqual(rule2.verdict, rule.verdict)

    def test_grimoire_step_creation(self):
        """Test GrimoireStep creation and serialization."""
        step = GrimoireStep(
            step_number=1,
            name="Check Graph",
            action=GrimoireStepAction.CHECK_GRAPH,
            description="Query VKG for indicators",
            inputs=["graph_data"],
            outputs=["graph_matches"],
            tools=["foundry"],
            queries=["has_reentrancy_guard"],
            timeout_seconds=30,
        )

        self.assertEqual(step.step_number, 1)
        self.assertEqual(step.name, "Check Graph")
        self.assertEqual(step.action, GrimoireStepAction.CHECK_GRAPH)

        # Test serialization
        data = step.to_dict()
        self.assertEqual(data["step_number"], 1)
        self.assertEqual(data["action"], "check_graph")
        self.assertEqual(data["tools"], ["foundry"])

        # Test deserialization
        step2 = GrimoireStep.from_dict(data)
        self.assertEqual(step2.step_number, step.step_number)
        self.assertEqual(step2.action, step.action)

    def test_grimoire_procedure_creation(self):
        """Test GrimoireProcedure creation."""
        procedure = GrimoireProcedure()

        step1 = GrimoireStep(
            step_number=1,
            name="Step 1",
            action=GrimoireStepAction.CHECK_GRAPH,
        )
        step2 = GrimoireStep(
            step_number=2,
            name="Step 2",
            action=GrimoireStepAction.GENERATE_TEST,
        )

        procedure.add_step(step1).add_step(step2)
        self.assertEqual(len(procedure.steps), 2)

        rule = VerdictRule(
            condition="test",
            verdict=GrimoireVerdict.VULNERABLE,
            confidence=VerdictConfidence.HIGH,
        )
        procedure.add_verdict_rule(rule)
        self.assertEqual(len(procedure.verdict_rules), 1)

    def test_tools_config_creation(self):
        """Test ToolsConfig creation and serialization."""
        config = ToolsConfig(
            foundry_enabled=True,
            medusa_enabled=True,
            medusa_duration=120,
            fork_enabled=True,
            fork_rpc="https://mainnet.infura.io",
        )

        self.assertTrue(config.foundry_enabled)
        self.assertTrue(config.medusa_enabled)
        self.assertEqual(config.medusa_duration, 120)
        self.assertEqual(config.fork_rpc, "https://mainnet.infura.io")

        # Test serialization
        data = config.to_dict()
        config2 = ToolsConfig.from_dict(data)
        self.assertEqual(config2.foundry_enabled, config.foundry_enabled)
        self.assertEqual(config2.medusa_duration, config.medusa_duration)

    def test_grimoire_creation(self):
        """Test Grimoire creation and serialization."""
        grimoire = Grimoire(
            id="grimoire-test",
            name="Test Grimoire",
            category="test",
            subcategories=["unit", "integration"],
            skill="/test-grimoire",
            aliases=["/verify-test"],
            description="A test grimoire",
            version="1.0.0",
            author="Test Author",
            tags=["test", "example"],
        )

        self.assertEqual(grimoire.id, "grimoire-test")
        self.assertEqual(grimoire.category, "test")
        self.assertEqual(grimoire.skill, "/test-grimoire")

        # Test serialization
        data = grimoire.to_dict()
        self.assertEqual(data["id"], "grimoire-test")
        self.assertEqual(data["subcategories"], ["unit", "integration"])

        # Test deserialization
        grimoire2 = Grimoire.from_dict(data)
        self.assertEqual(grimoire2.id, grimoire.id)
        self.assertEqual(grimoire2.skill, grimoire.skill)

    def test_grimoire_get_step(self):
        """Test Grimoire.get_step method."""
        grimoire = Grimoire(
            id="grimoire-test",
            name="Test",
            category="test",
        )

        step1 = GrimoireStep(step_number=1, name="Step 1", action=GrimoireStepAction.CHECK_GRAPH)
        step2 = GrimoireStep(step_number=2, name="Step 2", action=GrimoireStepAction.GENERATE_TEST)

        grimoire.procedure.add_step(step1).add_step(step2)

        found = grimoire.get_step(1)
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "Step 1")

        not_found = grimoire.get_step(99)
        self.assertIsNone(not_found)

    def test_grimoire_get_required_tools(self):
        """Test Grimoire.get_required_tools method."""
        grimoire = Grimoire(
            id="grimoire-test",
            name="Test",
            category="test",
        )

        step1 = GrimoireStep(
            step_number=1,
            name="Step 1",
            action=GrimoireStepAction.CHECK_GRAPH,
            tools=["foundry", "anvil"],
        )
        step2 = GrimoireStep(
            step_number=2,
            name="Step 2",
            action=GrimoireStepAction.EXECUTE_FUZZ,
            tools=["medusa", "foundry"],
        )

        grimoire.procedure.add_step(step1).add_step(step2)

        tools = grimoire.get_required_tools()
        self.assertEqual(tools, ["anvil", "foundry", "medusa"])

    def test_step_evidence_creation(self):
        """Test StepEvidence creation and serialization."""
        evidence = StepEvidence(
            step_number=1,
            step_name="Check Graph",
            action=GrimoireStepAction.CHECK_GRAPH,
            success=True,
            output={"matches": 3},
            duration_ms=150,
            metadata={"key": "value"},
        )

        self.assertEqual(evidence.step_number, 1)
        self.assertTrue(evidence.success)
        self.assertEqual(evidence.duration_ms, 150)

        data = evidence.to_dict()
        self.assertEqual(data["step_number"], 1)
        self.assertEqual(data["action"], "check_graph")

    def test_grimoire_result_creation(self):
        """Test GrimoireResult creation and properties."""
        result = GrimoireResult(
            grimoire_id="grimoire-reentrancy",
            finding_id="finding-123",
            verdict=GrimoireVerdict.VULNERABLE,
            confidence=VerdictConfidence.HIGH,
            verdict_explanation="Test confirmed vulnerability",
            steps_completed=5,
            steps_total=5,
        )

        self.assertTrue(result.is_vulnerable)
        self.assertFalse(result.is_safe)
        self.assertTrue(result.is_high_confidence)

        result2 = GrimoireResult(
            grimoire_id="grimoire-reentrancy",
            verdict=GrimoireVerdict.SAFE,
            confidence=VerdictConfidence.MEDIUM,
        )

        self.assertFalse(result2.is_vulnerable)
        self.assertTrue(result2.is_safe)
        self.assertFalse(result2.is_high_confidence)

    def test_grimoire_result_to_summary(self):
        """Test GrimoireResult.to_summary method."""
        result = GrimoireResult(
            grimoire_id="grimoire-reentrancy",
            verdict=GrimoireVerdict.VULNERABLE,
            confidence=VerdictConfidence.HIGH,
            verdict_explanation="Test passed",
            steps_completed=3,
            steps_total=5,
            steps_failed=2,
            total_duration_ms=1500,
        )

        summary = result.to_summary()
        self.assertIn("grimoire-reentrancy", summary)
        self.assertIn("vulnerable", summary)
        self.assertIn("high", summary)
        self.assertIn("3/5", summary)


class TestGrimoireRegistry(unittest.TestCase):
    """Test grimoire registry."""

    def setUp(self):
        """Reset global registry before each test."""
        reset_registry()

    def test_registry_register_grimoire(self):
        """Test registering a grimoire."""
        registry = GrimoireRegistry()

        grimoire = Grimoire(
            id="grimoire-test",
            name="Test Grimoire",
            category="test",
            skill="/test-grimoire",
            aliases=["/verify-test"],
        )

        registry.register(grimoire)

        self.assertIn("grimoire-test", registry)
        self.assertEqual(len(registry), 1)

    def test_registry_get_grimoire(self):
        """Test getting a grimoire by ID."""
        registry = GrimoireRegistry()

        grimoire = Grimoire(
            id="grimoire-test",
            name="Test Grimoire",
            category="test",
        )
        registry.register(grimoire)

        found = registry.get("grimoire-test")
        self.assertIsNotNone(found)
        self.assertEqual(found.id, "grimoire-test")

        not_found = registry.get("nonexistent")
        self.assertIsNone(not_found)

    def test_registry_find_by_category(self):
        """Test finding grimoires by category."""
        registry = GrimoireRegistry()

        g1 = Grimoire(id="g1", name="G1", category="reentrancy")
        g2 = Grimoire(id="g2", name="G2", category="reentrancy")
        g3 = Grimoire(id="g3", name="G3", category="access-control")

        registry.register(g1)
        registry.register(g2)
        registry.register(g3)

        reentrancy = registry.find_by_category("reentrancy")
        self.assertEqual(len(reentrancy), 2)

        access = registry.find_by_category("access-control")
        self.assertEqual(len(access), 1)

    def test_registry_find_by_skill(self):
        """Test finding grimoire by skill name."""
        registry = GrimoireRegistry()

        grimoire = Grimoire(
            id="grimoire-test",
            name="Test",
            category="test",
            skill="/test-grimoire",
            aliases=["/verify-test", "/check-test"],
        )
        registry.register(grimoire)

        # Find by skill name
        found = registry.find_by_skill("/test-grimoire")
        self.assertIsNotNone(found)
        self.assertEqual(found.id, "grimoire-test")

        # Find by alias
        found_alias = registry.find_by_skill("/verify-test")
        self.assertIsNotNone(found_alias)
        self.assertEqual(found_alias.id, "grimoire-test")

    def test_registry_find_by_subcategory(self):
        """Test finding grimoires by subcategory."""
        registry = GrimoireRegistry()

        g1 = Grimoire(
            id="g1",
            name="G1",
            category="reentrancy",
            subcategories=["classic", "cross-function"],
        )
        g2 = Grimoire(
            id="g2",
            name="G2",
            category="reentrancy",
            subcategories=["read-only"],
        )

        registry.register(g1)
        registry.register(g2)

        classic = registry.find_by_subcategory("classic")
        self.assertEqual(len(classic), 1)
        self.assertEqual(classic[0].id, "g1")

    def test_registry_find_by_tags(self):
        """Test finding grimoires by tags."""
        registry = GrimoireRegistry()

        g1 = Grimoire(id="g1", name="G1", category="test", tags=["critical", "common"])
        g2 = Grimoire(id="g2", name="G2", category="test", tags=["critical", "rare"])
        g3 = Grimoire(id="g3", name="G3", category="test", tags=["low"])

        registry.register(g1)
        registry.register(g2)
        registry.register(g3)

        # Match any
        critical = registry.find_by_tags(["critical"])
        self.assertEqual(len(critical), 2)

        # Match all
        critical_common = registry.find_by_tags(["critical", "common"], match_all=True)
        self.assertEqual(len(critical_common), 1)

    def test_registry_unregister(self):
        """Test unregistering a grimoire."""
        registry = GrimoireRegistry()

        grimoire = Grimoire(
            id="grimoire-test",
            name="Test",
            category="test",
            skill="/test",
        )
        registry.register(grimoire)
        self.assertEqual(len(registry), 1)

        removed = registry.unregister("grimoire-test")
        self.assertTrue(removed)
        self.assertEqual(len(registry), 0)
        self.assertIsNone(registry.find_by_skill("/test"))

    def test_registry_list_all(self):
        """Test listing all grimoires."""
        registry = GrimoireRegistry()

        g1 = Grimoire(id="g1", name="G1", category="test")
        g2 = Grimoire(id="g2", name="G2", category="test")

        registry.register(g1)
        registry.register(g2)

        all_grimoires = registry.list_all()
        self.assertEqual(len(all_grimoires), 2)

    def test_registry_list_categories(self):
        """Test listing categories."""
        registry = GrimoireRegistry()

        g1 = Grimoire(id="g1", name="G1", category="reentrancy")
        g2 = Grimoire(id="g2", name="G2", category="access-control")
        g3 = Grimoire(id="g3", name="G3", category="oracle")

        registry.register(g1)
        registry.register(g2)
        registry.register(g3)

        categories = registry.list_categories()
        self.assertEqual(categories, ["access-control", "oracle", "reentrancy"])

    def test_registry_load_from_file(self):
        """Test loading grimoires from JSON file."""
        registry = GrimoireRegistry()

        grimoire_data = {
            "id": "grimoire-test",
            "name": "Test Grimoire",
            "category": "test",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(grimoire_data, f)
            temp_path = Path(f.name)

        try:
            count = registry.load_from_file(temp_path)
            self.assertEqual(count, 1)
            self.assertIsNotNone(registry.get("grimoire-test"))
        finally:
            temp_path.unlink()

    def test_registry_load_from_directory(self):
        """Test loading grimoires from directory."""
        registry = GrimoireRegistry()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create multiple grimoire files
            for i in range(3):
                data = {
                    "id": f"grimoire-{i}",
                    "name": f"Grimoire {i}",
                    "category": "test",
                }
                with open(tmppath / f"g{i}.json", "w") as f:
                    json.dump(data, f)

            count = registry.load_from_directory(tmppath)
            self.assertEqual(count, 3)

    def test_registry_save_to_file(self):
        """Test saving grimoires to file."""
        registry = GrimoireRegistry()

        g1 = Grimoire(id="g1", name="G1", category="test")
        g2 = Grimoire(id="g2", name="G2", category="test")

        registry.register(g1)
        registry.register(g2)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        try:
            count = registry.save_to_file(temp_path)
            self.assertEqual(count, 2)

            with open(temp_path) as f:
                data = json.load(f)
            self.assertEqual(len(data), 2)
        finally:
            temp_path.unlink()

    def test_global_registry_functions(self):
        """Test global registry helper functions."""
        reset_registry()

        grimoire = Grimoire(
            id="grimoire-test",
            name="Test",
            category="test-category",
        )
        register_grimoire(grimoire)

        found = get_grimoire("grimoire-test")
        self.assertIsNotNone(found)

        all_grimoires = list_grimoires()
        self.assertGreaterEqual(len(all_grimoires), 1)

        category_grimoire = get_grimoire_for_category("test-category")
        self.assertIsNotNone(category_grimoire)

    def test_registry_load_builtin(self):
        """Test loading built-in grimoires."""
        registry = GrimoireRegistry()
        count = registry.load_builtin()

        # Should load the 5 built-in grimoires we created
        self.assertGreaterEqual(count, 5)

        # Verify specific grimoires exist
        self.assertIsNotNone(registry.get("grimoire-reentrancy"))
        self.assertIsNotNone(registry.get("grimoire-access-control"))
        self.assertIsNotNone(registry.get("grimoire-oracle"))
        self.assertIsNotNone(registry.get("grimoire-flash-loan"))
        self.assertIsNotNone(registry.get("grimoire-dos"))


class TestGrimoireExecutor(unittest.TestCase):
    """Test grimoire execution engine."""

    def test_execution_context_creation(self):
        """Test ExecutionContext creation."""
        context = ExecutionContext(
            finding_id="finding-123",
            function_name="withdraw",
            contract_name="Vault",
            contract_path="src/Vault.sol",
        )

        self.assertEqual(context.finding_id, "finding-123")
        self.assertEqual(context.function_name, "withdraw")

    def test_execution_context_get_set(self):
        """Test ExecutionContext get/set methods."""
        context = ExecutionContext()

        context.set("test_key", "test_value")
        self.assertEqual(context.get("test_key"), "test_value")

        # Default value
        self.assertEqual(context.get("nonexistent", "default"), "default")

    def test_execution_context_has_tool(self):
        """Test ExecutionContext tool availability."""
        context = ExecutionContext(
            available_tools={"foundry", "anvil", "medusa"},
        )

        self.assertTrue(context.has_tool("foundry"))
        self.assertTrue(context.has_tool("anvil"))
        self.assertFalse(context.has_tool("echidna"))

        self.assertTrue(context.has_all_tools(["foundry", "anvil"]))
        self.assertFalse(context.has_all_tools(["foundry", "echidna"]))

    def test_step_result_creation(self):
        """Test StepResult creation."""
        result = StepResult(
            success=True,
            output={"matches": 5},
            duration_ms=100,
        )

        self.assertTrue(result.success)
        self.assertFalse(result.is_failure)
        self.assertFalse(result.skipped)

        # Failed result
        failed = StepResult(
            success=False,
            error="Something went wrong",
        )
        self.assertTrue(failed.is_failure)

        # Skipped result
        skipped = StepResult(
            success=True,
            skipped=True,
            skip_reason="Missing tools",
        )
        self.assertFalse(skipped.is_failure)

    def test_executor_basic_execution(self):
        """Test basic grimoire execution."""
        executor = GrimoireExecutor()

        # Create a simple grimoire
        grimoire = Grimoire(
            id="grimoire-test",
            name="Test Grimoire",
            category="test",
        )

        step1 = GrimoireStep(
            step_number=1,
            name="Check Graph",
            action=GrimoireStepAction.CHECK_GRAPH,
            outputs=["graph_matches"],
        )
        step2 = GrimoireStep(
            step_number=2,
            name="Determine Verdict",
            action=GrimoireStepAction.DETERMINE_VERDICT,
        )

        grimoire.procedure.add_step(step1).add_step(step2)
        grimoire.procedure.default_verdict = GrimoireVerdict.UNCERTAIN

        context = ExecutionContext(
            finding_id="finding-123",
            graph_data={"properties": {}},
        )

        result = executor.execute(grimoire, context)

        self.assertEqual(result.grimoire_id, "grimoire-test")
        self.assertEqual(result.finding_id, "finding-123")
        self.assertEqual(result.steps_total, 2)
        self.assertGreaterEqual(result.steps_completed, 1)

    def test_executor_with_verdict_rules(self):
        """Test executor verdict determination with rules."""
        executor = GrimoireExecutor()

        grimoire = Grimoire(
            id="grimoire-test",
            name="Test Grimoire",
            category="test",
        )

        step = GrimoireStep(
            step_number=1,
            name="Check",
            action=GrimoireStepAction.CHECK_GRAPH,
        )
        grimoire.procedure.add_step(step)

        rule = VerdictRule(
            condition="all_steps_passed",
            verdict=GrimoireVerdict.SAFE,
            confidence=VerdictConfidence.MEDIUM,
            explanation="All checks passed",
        )
        grimoire.procedure.add_verdict_rule(rule)

        context = ExecutionContext(
            graph_data={"properties": {}},
        )

        result = executor.execute(grimoire, context)

        # With all steps passing, should match the rule
        self.assertEqual(result.verdict, GrimoireVerdict.SAFE)

    def test_executor_optional_step_skip(self):
        """Test executor skips optional steps with missing tools."""
        executor = GrimoireExecutor()

        grimoire = Grimoire(
            id="grimoire-test",
            name="Test",
            category="test",
        )

        step = GrimoireStep(
            step_number=1,
            name="Fuzz",
            action=GrimoireStepAction.EXECUTE_FUZZ,
            tools=["medusa"],
            optional=True,
        )
        grimoire.procedure.add_step(step)

        context = ExecutionContext(
            available_tools=set(),  # No tools available
        )

        result = executor.execute(grimoire, context)

        # Optional step should be skipped, not fail
        self.assertEqual(result.steps_completed, 1)
        self.assertEqual(result.steps_failed, 0)

    def test_executor_condition_evaluation(self):
        """Test executor condition evaluation."""
        executor = GrimoireExecutor()

        context = ExecutionContext()
        context.set("test_true", True)
        context.set("test_false", False)

        # Simple conditions
        self.assertTrue(executor._evaluate_condition("test_true", context))
        self.assertFalse(executor._evaluate_condition("test_false", context))

        # Negation
        self.assertFalse(executor._evaluate_condition("!test_true", context))
        self.assertTrue(executor._evaluate_condition("!test_false", context))

        # AND
        self.assertFalse(executor._evaluate_condition("test_true && test_false", context))
        self.assertTrue(executor._evaluate_condition("test_true && !test_false", context))

        # OR
        self.assertTrue(executor._evaluate_condition("test_true || test_false", context))
        self.assertFalse(executor._evaluate_condition("!test_true || test_false", context))

    def test_executor_custom_handler(self):
        """Test executor with custom step handler."""
        executor = GrimoireExecutor()

        # Register custom handler
        def custom_handler(step, context):
            return StepResult(
                success=True,
                output={"custom": "result"},
            )

        executor.register_handler(GrimoireStepAction.COMPARE_PATTERNS, custom_handler)

        grimoire = Grimoire(
            id="grimoire-test",
            name="Test",
            category="test",
        )

        step = GrimoireStep(
            step_number=1,
            name="Compare",
            action=GrimoireStepAction.COMPARE_PATTERNS,
        )
        grimoire.procedure.add_step(step)

        context = ExecutionContext()
        result = executor.execute(grimoire, context)

        self.assertEqual(result.steps_completed, 1)


class TestSkillSystem(unittest.TestCase):
    """Test skill invocation system."""

    def setUp(self):
        """Reset registries before each test."""
        reset_registry()
        reset_skill_registry()

    def test_skill_parameter_creation(self):
        """Test SkillParameter creation and validation."""
        param = SkillParameter(
            name="finding",
            description="Finding ID",
            param_type="string",
            required=True,
        )

        # Valid value
        is_valid, error = param.validate("finding-123")
        self.assertTrue(is_valid)
        self.assertEqual(error, "")

        # Missing required value
        is_valid, error = param.validate(None)
        self.assertFalse(is_valid)
        self.assertIn("required", error)

    def test_skill_parameter_choices(self):
        """Test SkillParameter with choices."""
        param = SkillParameter(
            name="severity",
            description="Severity level",
            choices=["low", "medium", "high"],
        )

        is_valid, _ = param.validate("medium")
        self.assertTrue(is_valid)

        is_valid, error = param.validate("critical")
        self.assertFalse(is_valid)
        self.assertIn("must be one of", error)

    def test_skill_parameter_type_validation(self):
        """Test SkillParameter type validation."""
        int_param = SkillParameter(
            name="count",
            description="Count",
            param_type="int",
        )

        is_valid, _ = int_param.validate(5)
        self.assertTrue(is_valid)

        is_valid, _ = int_param.validate("5")
        self.assertTrue(is_valid)

        is_valid, error = int_param.validate("not a number")
        self.assertFalse(is_valid)

    def test_skill_creation(self):
        """Test Skill creation."""
        skill = Skill(
            name="/test-skill",
            description="A test skill",
            category="test",
            grimoire_id="grimoire-test",
            parameters=[
                SkillParameter(name="finding", description="Finding ID"),
            ],
            required_tools=["foundry"],
            aliases=["/verify-test"],
        )

        self.assertEqual(skill.name, "/test-skill")
        self.assertEqual(skill.grimoire_id, "grimoire-test")

    def test_skill_validate_args(self):
        """Test Skill argument validation."""
        skill = Skill(
            name="/test-skill",
            description="Test",
            parameters=[
                SkillParameter(name="finding", description="Finding", required=True),
                SkillParameter(name="verbose", description="Verbose", param_type="bool"),
            ],
        )

        # Valid args
        is_valid, errors = skill.validate_args({"finding": "f-123", "verbose": True})
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])

        # Missing required
        is_valid, errors = skill.validate_args({})
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_skill_result_creation(self):
        """Test SkillResult creation."""
        result = SkillResult(
            skill_name="/test-skill",
            status=SkillStatus.SUCCESS,
            message="Completed successfully",
        )

        self.assertTrue(result.is_success)
        self.assertIsNone(result.verdict)

        failed = SkillResult(
            skill_name="/test-skill",
            status=SkillStatus.FAILED,
            error="Something went wrong",
        )
        self.assertFalse(failed.is_success)

    def test_skill_result_with_grimoire_result(self):
        """Test SkillResult with grimoire result."""
        grimoire_result = GrimoireResult(
            grimoire_id="grimoire-test",
            verdict=GrimoireVerdict.VULNERABLE,
            confidence=VerdictConfidence.HIGH,
        )

        skill_result = SkillResult(
            skill_name="/test-skill",
            status=SkillStatus.SUCCESS,
            grimoire_result=grimoire_result,
        )

        self.assertEqual(skill_result.verdict, GrimoireVerdict.VULNERABLE)

    def test_skill_registry_register(self):
        """Test SkillRegistry registration."""
        registry = SkillRegistry()

        skill = Skill(
            name="/test-skill",
            description="Test",
            aliases=["/verify-test"],
        )
        registry.register(skill)

        self.assertIn("/test-skill", registry)
        self.assertEqual(len(registry), 1)

    def test_skill_registry_get(self):
        """Test SkillRegistry get by name and alias."""
        registry = SkillRegistry()

        skill = Skill(
            name="/test-skill",
            description="Test",
            aliases=["/verify-test"],
        )
        registry.register(skill)

        # Get by name
        found = registry.get("/test-skill")
        self.assertIsNotNone(found)

        # Get by alias
        found_alias = registry.get("/verify-test")
        self.assertIsNotNone(found_alias)
        self.assertEqual(found_alias.name, "/test-skill")

    def test_skill_registry_list(self):
        """Test SkillRegistry listing."""
        registry = SkillRegistry()

        s1 = Skill(name="/skill-1", description="S1", category="cat1")
        s2 = Skill(name="/skill-2", description="S2", category="cat2")
        s3 = Skill(name="/skill-3", description="S3", category="cat1", hidden=True)

        registry.register(s1)
        registry.register(s2)
        registry.register(s3)

        # List all (excluding hidden)
        visible = registry.list_all()
        self.assertEqual(len(visible), 2)

        # List all (including hidden)
        all_skills = registry.list_all(include_hidden=True)
        self.assertEqual(len(all_skills), 3)

        # List by category
        cat1 = registry.list_by_category("cat1")
        self.assertEqual(len(cat1), 2)  # Includes hidden

    def test_skill_registry_discover_from_grimoires(self):
        """Test SkillRegistry auto-discovery from grimoires."""
        # Register grimoires first
        grimoire = Grimoire(
            id="grimoire-test",
            name="Test",
            category="test",
            skill="/test-grimoire",
            description="Test grimoire skill",
        )
        register_grimoire(grimoire)

        registry = SkillRegistry()
        count = registry.discover_from_grimoires()

        self.assertGreaterEqual(count, 1)
        skill = registry.get("/test-grimoire")
        self.assertIsNotNone(skill)
        self.assertEqual(skill.grimoire_id, "grimoire-test")

    def test_skill_execute_grimoire_backed(self):
        """Test executing a grimoire-backed skill."""
        # Register grimoire
        grimoire = Grimoire(
            id="grimoire-test",
            name="Test",
            category="test",
            skill="/test-grimoire",
        )
        grimoire.procedure.default_verdict = GrimoireVerdict.SAFE
        register_grimoire(grimoire)

        registry = SkillRegistry()
        registry.discover_from_grimoires()

        context = ExecutionContext(finding_id="f-123")
        result = registry.execute("/test-grimoire", {}, context)

        self.assertEqual(result.skill_name, "/test-grimoire")
        self.assertIn(result.status, [SkillStatus.SUCCESS, SkillStatus.PARTIAL])

    def test_skill_execute_handler_backed(self):
        """Test executing a handler-backed skill."""
        def test_handler(args, context):
            return SkillResult(
                skill_name="/custom-skill",
                status=SkillStatus.SUCCESS,
                message="Custom handler executed",
                metadata={"args": args},
            )

        skill = Skill(
            name="/custom-skill",
            description="Custom skill",
            handler=test_handler,
        )

        registry = SkillRegistry()
        registry.register(skill)

        result = registry.execute("/custom-skill", {"key": "value"})

        self.assertTrue(result.is_success)
        self.assertEqual(result.metadata["args"]["key"], "value")

    def test_global_skill_functions(self):
        """Test global skill helper functions."""
        reset_skill_registry()

        skill = Skill(
            name="/test-skill",
            description="Test",
            category="test",
        )
        register_skill(skill)

        all_skills = list_skills()
        self.assertGreaterEqual(len(all_skills), 1)

        category_skills = list_skills(category="test")
        self.assertGreaterEqual(len(category_skills), 1)

    def test_invoke_skill_convenience(self):
        """Test invoke_skill convenience function."""
        reset_skill_registry()

        def handler(args, context):
            return SkillResult(
                skill_name="/quick-skill",
                status=SkillStatus.SUCCESS,
            )

        skill = Skill(
            name="/quick-skill",
            description="Quick skill",
            handler=handler,
        )
        register_skill(skill)

        result = invoke_skill("/quick-skill")
        self.assertTrue(result.is_success)

    def test_invoke_unknown_skill(self):
        """Test invoking unknown skill."""
        reset_skill_registry()

        result = invoke_skill("/nonexistent-skill")
        self.assertEqual(result.status, SkillStatus.FAILED)
        self.assertIn("Unknown skill", result.error)


class TestBuiltinGrimoires(unittest.TestCase):
    """Test built-in grimoire definitions."""

    @classmethod
    def setUpClass(cls):
        """Load built-in grimoires."""
        reset_registry()
        cls.registry = get_registry()

    def test_reentrancy_grimoire_structure(self):
        """Test reentrancy grimoire structure."""
        grimoire = self.registry.get("grimoire-reentrancy")
        self.assertIsNotNone(grimoire)

        self.assertEqual(grimoire.category, "reentrancy")
        self.assertEqual(grimoire.skill, "/test-reentrancy")
        self.assertIn("classic", grimoire.subcategories)
        self.assertIn("cross-function", grimoire.subcategories)

        # Check procedure
        self.assertGreater(len(grimoire.procedure.steps), 0)
        self.assertGreater(len(grimoire.procedure.verdict_rules), 0)

        # Check tools config
        self.assertTrue(grimoire.tools_config.foundry_enabled)

    def test_access_control_grimoire_structure(self):
        """Test access control grimoire structure."""
        grimoire = self.registry.get("grimoire-access-control")
        self.assertIsNotNone(grimoire)

        self.assertEqual(grimoire.category, "access-control")
        self.assertEqual(grimoire.skill, "/test-access")
        self.assertIn("missing-gate", grimoire.subcategories)

    def test_oracle_grimoire_structure(self):
        """Test oracle grimoire structure."""
        grimoire = self.registry.get("grimoire-oracle")
        self.assertIsNotNone(grimoire)

        self.assertEqual(grimoire.category, "oracle")
        self.assertEqual(grimoire.skill, "/test-oracle")
        self.assertTrue(grimoire.tools_config.fork_enabled)

    def test_flash_loan_grimoire_structure(self):
        """Test flash loan grimoire structure."""
        grimoire = self.registry.get("grimoire-flash-loan")
        self.assertIsNotNone(grimoire)

        self.assertEqual(grimoire.category, "flash-loan")
        self.assertEqual(grimoire.skill, "/test-flashloan")

    def test_dos_grimoire_structure(self):
        """Test DoS grimoire structure."""
        grimoire = self.registry.get("grimoire-dos")
        self.assertIsNotNone(grimoire)

        self.assertEqual(grimoire.category, "dos")
        self.assertEqual(grimoire.skill, "/test-dos")
        self.assertTrue(grimoire.tools_config.medusa_enabled)

    def test_mev_grimoire_structure(self):
        """Test MEV grimoire structure."""
        grimoire = self.registry.get("grimoire-mev")
        self.assertIsNotNone(grimoire)

        self.assertEqual(grimoire.category, "mev")
        self.assertEqual(grimoire.skill, "/test-mev")
        self.assertIn("sandwich", grimoire.subcategories)
        self.assertIn("frontrunning", grimoire.subcategories)
        self.assertIn("slippage", grimoire.subcategories)
        self.assertIn("deadline", grimoire.subcategories)
        self.assertTrue(grimoire.tools_config.fork_enabled)

    def test_token_grimoire_structure(self):
        """Test token grimoire structure."""
        grimoire = self.registry.get("grimoire-token")
        self.assertIsNotNone(grimoire)

        self.assertEqual(grimoire.category, "token")
        self.assertEqual(grimoire.skill, "/test-token")
        self.assertIn("fee-on-transfer", grimoire.subcategories)
        self.assertIn("rebasing", grimoire.subcategories)
        self.assertIn("erc777-hooks", grimoire.subcategories)
        self.assertIn("return-value", grimoire.subcategories)
        self.assertIn("approval-race", grimoire.subcategories)

        # Check procedure
        self.assertGreater(len(grimoire.procedure.steps), 0)
        self.assertGreater(len(grimoire.procedure.verdict_rules), 0)

    def test_upgrade_grimoire_structure(self):
        """Test upgrade grimoire structure."""
        grimoire = self.registry.get("grimoire-upgrade")
        self.assertIsNotNone(grimoire)

        self.assertEqual(grimoire.category, "upgrade")
        self.assertEqual(grimoire.skill, "/test-upgrade")
        self.assertIn("uninitialized-proxy", grimoire.subcategories)
        self.assertIn("storage-collision", grimoire.subcategories)
        self.assertIn("selfdestruct", grimoire.subcategories)
        self.assertIn("delegatecall", grimoire.subcategories)
        self.assertIn("implementation-takeover", grimoire.subcategories)
        self.assertTrue(grimoire.tools_config.fork_enabled)

    def test_crypto_grimoire_structure(self):
        """Test crypto grimoire structure."""
        grimoire = self.registry.get("grimoire-crypto")
        self.assertIsNotNone(grimoire)

        self.assertEqual(grimoire.category, "crypto")
        self.assertEqual(grimoire.skill, "/test-crypto")
        self.assertIn("signature-malleability", grimoire.subcategories)
        self.assertIn("ecrecover", grimoire.subcategories)
        self.assertIn("replay-attack", grimoire.subcategories)
        self.assertIn("weak-randomness", grimoire.subcategories)
        self.assertIn("hash-collision", grimoire.subcategories)

        # Check verdict rules include key crypto vulnerabilities
        verdict_conditions = [r.condition for r in grimoire.procedure.verdict_rules]
        has_ecrecover_rule = any("ecrecover" in c for c in verdict_conditions)
        self.assertTrue(has_ecrecover_rule, "Should have ecrecover-related verdict rule")

    def test_all_grimoires_have_skills(self):
        """Test all built-in grimoires are invocable as skills."""
        for grimoire in self.registry.list_all():
            self.assertTrue(
                grimoire.skill,
                f"Grimoire {grimoire.id} missing skill name",
            )

    def test_all_grimoires_have_verdict_rules(self):
        """Test all built-in grimoires have verdict rules."""
        for grimoire in self.registry.list_all():
            self.assertGreater(
                len(grimoire.procedure.verdict_rules),
                0,
                f"Grimoire {grimoire.id} has no verdict rules",
            )

    def test_all_grimoires_serializable(self):
        """Test all built-in grimoires can be serialized/deserialized."""
        for grimoire in self.registry.list_all():
            data = grimoire.to_dict()
            restored = Grimoire.from_dict(data)
            self.assertEqual(restored.id, grimoire.id)
            self.assertEqual(restored.category, grimoire.category)


class TestGrimoireIntegration(unittest.TestCase):
    """Integration tests for grimoire system."""

    def setUp(self):
        """Reset registries."""
        reset_registry()
        reset_skill_registry()

    def test_full_grimoire_execution_flow(self):
        """Test complete grimoire execution flow."""
        # Load built-in grimoires
        registry = get_registry()

        # Get reentrancy grimoire
        grimoire = registry.get("grimoire-reentrancy")
        self.assertIsNotNone(grimoire)

        # Create context
        context = ExecutionContext(
            finding_id="VKG-001",
            function_name="withdraw",
            contract_name="Vault",
            contract_path="src/Vault.sol",
            graph_data={"properties": {"state_write_after_external_call": True}},
            node_properties={
                "has_reentrancy_guard": False,
                "state_write_after_external_call": True,
            },
        )
        context.set("sequence_violated", True)

        # Execute
        executor = GrimoireExecutor()
        result = executor.execute(grimoire, context)

        # Verify execution completed
        self.assertEqual(result.grimoire_id, "grimoire-reentrancy")
        self.assertGreater(result.steps_completed, 0)
        self.assertIsNotNone(result.verdict)
        self.assertIn(
            result.verdict,
            [
                GrimoireVerdict.VULNERABLE,
                GrimoireVerdict.LIKELY_VULNERABLE,
                GrimoireVerdict.UNCERTAIN,
            ],
        )

    def test_skill_invocation_flow(self):
        """Test complete skill invocation flow."""
        # Setup registries - must load grimoires first, then skills
        grimoire_registry = get_registry()  # This loads built-in grimoires

        # Create fresh skill registry and discover from grimoires
        skill_registry = SkillRegistry()
        skill_registry.discover_from_grimoires()

        # Verify skills discovered
        self.assertGreater(len(skill_registry), 0)

        # Verify the skill exists
        skill = skill_registry.get("/test-access")
        self.assertIsNotNone(skill)
        self.assertEqual(skill.grimoire_id, "grimoire-access-control")

        # Invoke skill with required context
        # Note: required_context from grimoire becomes required parameters
        context = ExecutionContext(
            finding_id="VKG-002",
            function_name="setAdmin",
            contract_name="AccessControl",
            graph_data={"properties": {}},
            node_properties={"has_access_gate": False},
        )

        # Provide required grimoire context
        args = {
            "function_code": "function setAdmin(address _admin) public { admin = _admin; }",
            "access_modifiers": [],
            "state_variables_written": ["admin"],
        }

        result = skill_registry.execute("/test-access", args, context)

        self.assertEqual(result.skill_name, "/test-access")
        self.assertIsNotNone(result.grimoire_result)

    def test_multiple_grimoire_execution(self):
        """Test executing multiple grimoires on same finding."""
        registry = get_registry()
        executor = GrimoireExecutor()

        context = ExecutionContext(
            finding_id="VKG-003",
            function_name="swap",
            contract_name="DEX",
            graph_data={"properties": {}},
        )

        results = []
        for grimoire in registry.list_all()[:3]:  # Test first 3
            result = executor.execute(grimoire, context)
            results.append(result)

        self.assertEqual(len(results), 3)
        for result in results:
            self.assertIsNotNone(result.verdict)


class TestCostTracking(unittest.TestCase):
    """Test cost tracking system."""

    def test_token_usage_creation(self):
        """Test TokenUsage creation and properties."""
        usage = TokenUsage(
            input_tokens=1000,
            output_tokens=500,
            cached_tokens=200,
        )

        self.assertEqual(usage.total_tokens, 1500)
        self.assertEqual(usage.effective_input_tokens, 800)

    def test_token_usage_add(self):
        """Test TokenUsage addition."""
        usage1 = TokenUsage(input_tokens=1000, output_tokens=500)
        usage2 = TokenUsage(input_tokens=500, output_tokens=250, cached_tokens=100)

        combined = usage1.add(usage2)

        self.assertEqual(combined.input_tokens, 1500)
        self.assertEqual(combined.output_tokens, 750)
        self.assertEqual(combined.cached_tokens, 100)

    def test_token_usage_to_dict(self):
        """Test TokenUsage serialization."""
        usage = TokenUsage(input_tokens=1000, output_tokens=500)
        data = usage.to_dict()

        self.assertEqual(data["input_tokens"], 1000)
        self.assertEqual(data["output_tokens"], 500)
        self.assertEqual(data["total_tokens"], 1500)

    def test_model_pricing_calculate_cost(self):
        """Test ModelPricing cost calculation."""
        pricing = ModelPricing(
            model_name="test-model",
            input_price_per_million=1.0,
            output_price_per_million=3.0,
            cached_input_price_per_million=0.1,
        )

        usage = TokenUsage(
            input_tokens=1_000_000,
            output_tokens=500_000,
            cached_tokens=200_000,
        )

        cost = pricing.calculate_cost(usage)

        # 800k effective input * $1/1M = $0.80
        # 200k cached * $0.1/1M = $0.02
        # 500k output * $3/1M = $1.50
        # Total = $2.32
        self.assertAlmostEqual(cost, 2.32, places=2)

    def test_default_pricing_exists(self):
        """Test default pricing for common models."""
        self.assertIn("claude-3-opus", DEFAULT_PRICING)
        self.assertIn("claude-3-sonnet", DEFAULT_PRICING)
        self.assertIn("claude-3-haiku", DEFAULT_PRICING)
        self.assertIn("gpt-4-turbo", DEFAULT_PRICING)
        self.assertIn("default", DEFAULT_PRICING)

    def test_step_cost_creation(self):
        """Test StepCost creation and serialization."""
        cost = StepCost(
            step_number=1,
            step_name="Analyze",
            category=CostCategory.LLM_TOKENS,
            tokens=TokenUsage(input_tokens=1000, output_tokens=500),
            cost_usd=0.005,
            duration_ms=150,
            model="claude-3-haiku",
        )

        self.assertEqual(cost.step_number, 1)
        self.assertEqual(cost.category, CostCategory.LLM_TOKENS)

        data = cost.to_dict()
        self.assertEqual(data["step_number"], 1)
        self.assertEqual(data["category"], "llm_tokens")

    def test_cost_report_add_step(self):
        """Test CostReport accumulation."""
        report = CostReport(
            grimoire_id="grimoire-test",
            budget_usd=1.0,
        )

        cost1 = StepCost(
            step_number=1,
            step_name="Step 1",
            category=CostCategory.LLM_TOKENS,
            tokens=TokenUsage(input_tokens=1000, output_tokens=500),
            cost_usd=0.25,
        )
        cost2 = StepCost(
            step_number=2,
            step_name="Step 2",
            category=CostCategory.LLM_TOKENS,
            tokens=TokenUsage(input_tokens=500, output_tokens=250),
            cost_usd=0.15,
        )

        report.add_step_cost(cost1)
        report.add_step_cost(cost2)

        self.assertEqual(len(report.step_costs), 2)
        self.assertAlmostEqual(report.total_cost_usd, 0.40, places=2)
        self.assertEqual(report.total_tokens.input_tokens, 1500)
        self.assertEqual(report.total_tokens.output_tokens, 750)
        self.assertFalse(report.budget_exceeded)
        self.assertAlmostEqual(report.budget_remaining, 0.60, places=2)

    def test_cost_report_budget_exceeded(self):
        """Test CostReport budget exceeded detection."""
        report = CostReport(
            grimoire_id="grimoire-test",
            budget_usd=0.10,
        )

        cost = StepCost(
            step_number=1,
            step_name="Expensive",
            category=CostCategory.LLM_TOKENS,
            cost_usd=0.50,
        )

        report.add_step_cost(cost)

        self.assertTrue(report.budget_exceeded)
        self.assertLess(report.budget_remaining, 0)

    def test_cost_report_to_summary(self):
        """Test CostReport summary generation."""
        report = CostReport(
            grimoire_id="grimoire-test",
            finding_id="VKG-001",
            budget_usd=1.0,
        )

        cost = StepCost(
            step_number=1,
            step_name="Analyze",
            category=CostCategory.LLM_TOKENS,
            tokens=TokenUsage(input_tokens=1000, output_tokens=500),
            cost_usd=0.25,
        )
        report.add_step_cost(cost)

        summary = report.to_summary()

        self.assertIn("grimoire-test", summary)
        self.assertIn("VKG-001", summary)
        self.assertIn("$0.25", summary)
        self.assertIn("Budget", summary)

    def test_cost_tracker_creation(self):
        """Test CostTracker creation."""
        tracker = CostTracker(
            grimoire_id="grimoire-test",
            finding_id="VKG-001",
            budget_usd=2.0,
        )

        self.assertEqual(tracker.grimoire_id, "grimoire-test")
        self.assertEqual(tracker.budget_usd, 2.0)

    def test_cost_tracker_track_llm_cost(self):
        """Test CostTracker LLM cost tracking."""
        tracker = CostTracker(
            grimoire_id="grimoire-test",
            budget_usd=2.0,
        )

        cost = tracker.track_llm_cost(
            step_number=1,
            step_name="Analyze",
            tokens=TokenUsage(input_tokens=10000, output_tokens=5000),
            model="claude-3-haiku",
            duration_ms=150,
        )

        self.assertEqual(cost.step_number, 1)
        self.assertGreater(cost.cost_usd, 0)

        report = tracker.get_report()
        self.assertEqual(len(report.step_costs), 1)
        self.assertEqual(report.total_tokens.input_tokens, 10000)

    def test_cost_tracker_track_compute_cost(self):
        """Test CostTracker compute cost tracking."""
        tracker = CostTracker(grimoire_id="grimoire-test")

        cost = tracker.track_compute_cost(
            step_number=1,
            step_name="Execute Test",
            cost_usd=0.01,
            duration_ms=5000,
        )

        self.assertEqual(cost.category, CostCategory.COMPUTE)

        report = tracker.get_report()
        self.assertIn(CostCategory.COMPUTE.value, report.cost_by_category)

    def test_cost_tracker_track_api_cost(self):
        """Test CostTracker API cost tracking."""
        tracker = CostTracker(grimoire_id="grimoire-test")

        cost = tracker.track_api_cost(
            step_number=1,
            step_name="Fork RPC",
            cost_usd=0.001,
            api_name="alchemy",
        )

        self.assertEqual(cost.category, CostCategory.API_CALLS)
        self.assertEqual(cost.metadata["api_name"], "alchemy")

    def test_cost_tracker_budget_check(self):
        """Test CostTracker budget checking."""
        tracker = CostTracker(
            grimoire_id="grimoire-test",
            budget_usd=0.10,
        )

        self.assertFalse(tracker.is_budget_exceeded())
        self.assertAlmostEqual(tracker.get_remaining_budget(), 0.10, places=2)

        # Add expensive operation
        tracker.track_llm_cost(
            step_number=1,
            step_name="Expensive",
            tokens=TokenUsage(input_tokens=1_000_000, output_tokens=500_000),
            model="claude-3-opus",
        )

        self.assertTrue(tracker.is_budget_exceeded())
        self.assertLess(tracker.get_remaining_budget(), 0)

    def test_cost_tracker_get_pricing(self):
        """Test CostTracker pricing lookup."""
        tracker = CostTracker(grimoire_id="grimoire-test")

        # Exact match
        pricing = tracker.get_pricing("claude-3-haiku")
        self.assertEqual(pricing.model_name, "claude-3-haiku")

        # Partial match
        pricing = tracker.get_pricing("claude-3-haiku-20241022")
        self.assertEqual(pricing.model_name, "claude-3-haiku")

        # Fallback to default
        pricing = tracker.get_pricing("unknown-model-xyz")
        self.assertEqual(pricing.model_name, "default")

    def test_cost_tracker_total_cost(self):
        """Test CostTracker total cost tracking."""
        tracker = CostTracker(grimoire_id="grimoire-test")

        tracker.track_llm_cost(
            step_number=1,
            step_name="Step 1",
            tokens=TokenUsage(input_tokens=1000, output_tokens=500),
            model="claude-3-haiku",
        )
        tracker.track_compute_cost(
            step_number=2,
            step_name="Step 2",
            cost_usd=0.01,
        )

        self.assertGreater(tracker.get_total_cost(), 0.01)

    def test_create_cost_tracker_convenience(self):
        """Test create_cost_tracker convenience function."""
        tracker = create_cost_tracker(
            grimoire_id="grimoire-test",
            finding_id="VKG-001",
            budget_usd=1.0,
        )

        self.assertIsInstance(tracker, CostTracker)
        self.assertEqual(tracker.grimoire_id, "grimoire-test")

    def test_cost_category_enum(self):
        """Test CostCategory enum values."""
        self.assertEqual(CostCategory.LLM_TOKENS.value, "llm_tokens")
        self.assertEqual(CostCategory.COMPUTE.value, "compute")
        self.assertEqual(CostCategory.API_CALLS.value, "api_calls")

    def test_cost_report_to_dict(self):
        """Test CostReport serialization."""
        report = CostReport(
            grimoire_id="grimoire-test",
            finding_id="VKG-001",
            budget_usd=1.0,
        )

        cost = StepCost(
            step_number=1,
            step_name="Test",
            category=CostCategory.LLM_TOKENS,
            cost_usd=0.25,
        )
        report.add_step_cost(cost)

        data = report.to_dict()

        self.assertEqual(data["grimoire_id"], "grimoire-test")
        self.assertEqual(data["finding_id"], "VKG-001")
        self.assertEqual(len(data["step_costs"]), 1)
        self.assertIsNotNone(data["budget_usd"])

    def test_budget_exceeded_error(self):
        """Test BudgetExceededError exception."""
        error = BudgetExceededError(
            budget=1.0,
            spent=1.5,
            grimoire_id="grimoire-test",
        )

        self.assertEqual(error.budget, 1.0)
        self.assertEqual(error.spent, 1.5)
        self.assertIn("grimoire-test", str(error))
        self.assertIn("$1.50", str(error))


if __name__ == "__main__":
    unittest.main()
