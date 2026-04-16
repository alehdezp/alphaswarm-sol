"""Tests for LLM Investigation Patterns.

Task 13.11: Per-vulnerability investigation patterns that guide LLM reasoning.
"""

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

from alphaswarm_sol.investigation.schema import (
    InvestigationAction,
    InvestigationPattern,
    InvestigationProcedure,
    InvestigationResult,
    InvestigationStep,
    InvestigationTrigger,
    InvestigationVerdict,
    StepResult,
    TriggerSignal,
    VerdictCriteria,
)
from alphaswarm_sol.investigation.executor import (
    InvestigationContext,
    InvestigationExecutor,
)
from alphaswarm_sol.investigation.loader import (
    InvestigationLoader,
    get_loader,
    load_all_investigations,
    load_investigation_pattern,
)
from alphaswarm_sol.investigation.registry import (
    InvestigationRegistry,
    get_investigation,
    get_investigation_registry,
    list_investigations,
    reset_investigation_registry,
)


class TestInvestigationSchema(unittest.TestCase):
    """Test investigation schema definitions."""

    def test_investigation_action_enum(self):
        """Test InvestigationAction enum values."""
        self.assertEqual(InvestigationAction.EXPLORE_GRAPH.value, "explore_graph")
        self.assertEqual(InvestigationAction.LSP_REFERENCES.value, "lsp_references")
        self.assertEqual(InvestigationAction.LSP_DEFINITION.value, "lsp_definition")
        self.assertEqual(InvestigationAction.PPR_EXPAND.value, "ppr_expand")
        self.assertEqual(InvestigationAction.READ_CODE.value, "read_code")
        self.assertEqual(InvestigationAction.REASON.value, "reason")
        self.assertEqual(InvestigationAction.SYNTHESIZE.value, "synthesize")

    def test_investigation_verdict_enum(self):
        """Test InvestigationVerdict enum values."""
        self.assertEqual(InvestigationVerdict.VULNERABLE.value, "vulnerable")
        self.assertEqual(InvestigationVerdict.LIKELY_VULNERABLE.value, "likely_vulnerable")
        self.assertEqual(InvestigationVerdict.UNCERTAIN.value, "uncertain")
        self.assertEqual(InvestigationVerdict.LIKELY_SAFE.value, "likely_safe")
        self.assertEqual(InvestigationVerdict.SAFE.value, "safe")
        self.assertEqual(InvestigationVerdict.SKIPPED.value, "skipped")

    def test_trigger_signal_creation(self):
        """Test TriggerSignal creation."""
        signal = TriggerSignal(
            signal="Function writes balance",
            property="writes_user_balance",
            value=True,
            description="Triggers when function modifies user balance",
        )

        self.assertEqual(signal.signal, "Function writes balance")
        self.assertEqual(signal.property, "writes_user_balance")
        self.assertTrue(signal.value)

        # Test serialization
        data = signal.to_dict()
        restored = TriggerSignal.from_dict(data)
        self.assertEqual(restored.property, signal.property)

    def test_investigation_trigger_creation(self):
        """Test InvestigationTrigger creation."""
        trigger = InvestigationTrigger(
            description="Function modifies balance-like state",
            graph_signals=[
                TriggerSignal(property="writes_user_balance"),
                TriggerSignal(property="calls_external"),
            ],
            require_all=False,
        )

        self.assertEqual(len(trigger.graph_signals), 2)
        self.assertFalse(trigger.require_all)

        # Test serialization
        data = trigger.to_dict()
        restored = InvestigationTrigger.from_dict(data)
        self.assertEqual(len(restored.graph_signals), 2)

    def test_investigation_step_creation(self):
        """Test InvestigationStep creation."""
        step = InvestigationStep(
            id=1,
            action=InvestigationAction.EXPLORE_GRAPH,
            description="Find all balance-modifying functions",
            params={"graph_query": "FIND functions WHERE writes_state"},
            interpretation="Look for functions that modify balances",
            timeout_seconds=15,
        )

        self.assertEqual(step.id, 1)
        self.assertEqual(step.action, InvestigationAction.EXPLORE_GRAPH)
        self.assertIn("graph_query", step.params)

    def test_investigation_step_from_dict(self):
        """Test InvestigationStep parsing from dictionary."""
        data = {
            "id": 2,
            "action": "lsp_references",
            "description": "Find references",
            "target": "balances",
            "interpretation": "Check balance reads",
        }

        step = InvestigationStep.from_dict(data)

        self.assertEqual(step.id, 2)
        self.assertEqual(step.action, InvestigationAction.LSP_REFERENCES)
        self.assertEqual(step.params["target"], "balances")

    def test_verdict_criteria_creation(self):
        """Test VerdictCriteria creation."""
        criteria = VerdictCriteria(
            vulnerable="Clear path to break invariant",
            uncertain="Complex logic needs review",
            safe="Invariant preserved in all paths",
        )

        self.assertIn("Clear path", criteria.vulnerable)
        self.assertIn("Invariant preserved", criteria.safe)

        # Test serialization
        data = criteria.to_dict()
        self.assertIn("vulnerable", data)
        self.assertIn("safe", data)

    def test_investigation_procedure_creation(self):
        """Test InvestigationProcedure creation."""
        procedure = InvestigationProcedure(
            hypothesis="Balance tracking may be incorrect",
            steps=[
                InvestigationStep(
                    id=1,
                    action=InvestigationAction.EXPLORE_GRAPH,
                    description="Find balance functions",
                ),
                InvestigationStep(
                    id=2,
                    action=InvestigationAction.REASON,
                    description="Analyze findings",
                ),
            ],
            verdict_criteria=VerdictCriteria(
                vulnerable="Invariant can be broken",
                safe="Invariant always holds",
            ),
        )

        self.assertEqual(len(procedure.steps), 2)
        self.assertIn("Balance tracking", procedure.hypothesis)

    def test_investigation_pattern_creation(self):
        """Test InvestigationPattern creation."""
        pattern = InvestigationPattern(
            id="inv-test-001",
            name="Test Investigation",
            type="investigation",
            category="test",
            description="A test investigation pattern",
            tags=["test"],
            trigger=InvestigationTrigger(
                graph_signals=[TriggerSignal(property="writes_state")],
            ),
            investigation=InvestigationProcedure(
                hypothesis="Test hypothesis",
                steps=[
                    InvestigationStep(
                        id=1,
                        action=InvestigationAction.REASON,
                        description="Test step",
                    ),
                ],
            ),
        )

        self.assertEqual(pattern.id, "inv-test-001")
        self.assertEqual(pattern.type, "investigation")
        self.assertEqual(pattern.category, "test")

    def test_investigation_pattern_serialization(self):
        """Test InvestigationPattern serialization roundtrip."""
        pattern = InvestigationPattern(
            id="inv-test-002",
            name="Serialization Test",
            category="test",
            subcategories=["sub1", "sub2"],
            tags=["tag1", "tag2"],
        )

        data = pattern.to_dict()
        restored = InvestigationPattern.from_dict(data)

        self.assertEqual(restored.id, pattern.id)
        self.assertEqual(restored.name, pattern.name)
        self.assertEqual(restored.subcategories, pattern.subcategories)
        self.assertEqual(restored.tags, pattern.tags)

    def test_step_result_creation(self):
        """Test StepResult creation."""
        result = StepResult(
            step_id=1,
            action=InvestigationAction.EXPLORE_GRAPH,
            success=True,
            raw_output={"functions": ["withdraw", "deposit"]},
            llm_interpretation="Found 2 balance-modifying functions",
            evidence=["withdraw modifies balances", "deposit modifies balances"],
            tokens_used=150,
            duration_ms=250,
        )

        self.assertEqual(result.step_id, 1)
        self.assertTrue(result.success)
        self.assertEqual(result.tokens_used, 150)
        self.assertEqual(len(result.evidence), 2)

        # Test serialization
        data = result.to_dict()
        self.assertEqual(data["action"], "explore_graph")
        self.assertEqual(data["tokens_used"], 150)

    def test_investigation_result_creation(self):
        """Test InvestigationResult creation."""
        result = InvestigationResult(
            pattern_id="inv-bl-001",
            pattern_name="Accounting Invariant Violation",
            verdict=InvestigationVerdict.VULNERABLE,
            confidence=85,
            attack_path="1. Flash loan 2. Manipulate balance 3. Extract funds",
            evidence=["Function withdraw has CEI violation"],
            recommendation="Apply CEI pattern",
        )

        self.assertEqual(result.pattern_id, "inv-bl-001")
        self.assertEqual(result.verdict, InvestigationVerdict.VULNERABLE)
        self.assertEqual(result.confidence, 85)
        self.assertTrue(result.is_vulnerable)
        self.assertFalse(result.is_safe)

    def test_investigation_result_properties(self):
        """Test InvestigationResult computed properties."""
        result = InvestigationResult(
            pattern_id="inv-test",
            verdict=InvestigationVerdict.LIKELY_SAFE,
            step_results=[
                StepResult(
                    step_id=1,
                    action=InvestigationAction.EXPLORE_GRAPH,
                    success=True,
                ),
                StepResult(
                    step_id=2,
                    action=InvestigationAction.REASON,
                    success=True,
                ),
                StepResult(
                    step_id=3,
                    action=InvestigationAction.LSP_REFERENCES,
                    success=False,
                    error="LSP unavailable",
                ),
            ],
        )

        self.assertFalse(result.is_vulnerable)
        self.assertTrue(result.is_safe)
        self.assertEqual(result.steps_completed, 2)

    def test_investigation_result_summary(self):
        """Test InvestigationResult summary generation."""
        result = InvestigationResult(
            pattern_id="inv-bl-001",
            pattern_name="Accounting Invariant",
            verdict=InvestigationVerdict.VULNERABLE,
            confidence=90,
            attack_path="Flash loan attack sequence",
            evidence=["CEI violation", "Missing reentrancy guard"],
            recommendation="Apply CEI pattern and add reentrancy guard",
            total_tokens=500,
            cost_usd=0.0012,
        )

        summary = result.to_summary()

        self.assertIn("Accounting Invariant", summary)
        self.assertIn("VULNERABLE", summary)
        self.assertIn("90%", summary)
        self.assertIn("Flash loan", summary)
        self.assertIn("CEI violation", summary)


class TestInvestigationContext(unittest.TestCase):
    """Test InvestigationContext."""

    def test_context_creation(self):
        """Test InvestigationContext creation."""
        context = InvestigationContext(
            function_name="withdraw",
            contract_name="Vault",
            file_path="src/Vault.sol",
            node_properties={
                "writes_user_balance": True,
                "calls_external": True,
            },
        )

        self.assertEqual(context.function_name, "withdraw")
        self.assertEqual(context.contract_name, "Vault")

    def test_context_get(self):
        """Test InvestigationContext get method."""
        context = InvestigationContext(
            function_name="test",
            node_properties={"prop1": True, "prop2": "value"},
            variables={"var1": 123},
        )

        # Get direct attribute
        self.assertEqual(context.get("function_name"), "test")

        # Get from node_properties
        self.assertTrue(context.get("prop1"))
        self.assertEqual(context.get("prop2"), "value")

        # Get from variables
        self.assertEqual(context.get("var1"), 123)

        # Get default
        self.assertEqual(context.get("nonexistent", "default"), "default")

    def test_context_set(self):
        """Test InvestigationContext set method."""
        context = InvestigationContext()

        context.set("custom_var", "custom_value")

        self.assertEqual(context.get("custom_var"), "custom_value")
        self.assertIn("custom_var", context.variables)

    def test_context_has_property(self):
        """Test InvestigationContext has_property method."""
        context = InvestigationContext(
            node_properties={
                "prop_true": True,
                "prop_false": False,
                "prop_value": "specific",
            },
        )

        # Boolean property
        self.assertTrue(context.has_property("prop_true"))
        self.assertFalse(context.has_property("prop_false"))

        # Specific value
        self.assertTrue(context.has_property("prop_value", "specific"))
        self.assertFalse(context.has_property("prop_value", "other"))

        # Missing property
        self.assertFalse(context.has_property("nonexistent"))

    def test_context_to_dict(self):
        """Test InvestigationContext serialization."""
        context = InvestigationContext(
            function_name="test",
            contract_name="Contract",
            node_properties={"prop": True},
            variables={"var": 123},
        )

        data = context.to_dict()

        self.assertEqual(data["function_name"], "test")
        self.assertEqual(data["contract_name"], "Contract")
        self.assertTrue(data["prop"])
        self.assertEqual(data["var"], 123)


class TestInvestigationExecutor(unittest.TestCase):
    """Test InvestigationExecutor."""

    def test_executor_creation(self):
        """Test InvestigationExecutor creation."""
        executor = InvestigationExecutor()

        self.assertIsNone(executor.graph)
        self.assertIsNone(executor.lsp)
        self.assertIsNone(executor.ppr)
        self.assertIsNone(executor.llm)

    def test_executor_check_triggers_no_signals(self):
        """Test trigger checking with no signals."""
        executor = InvestigationExecutor()

        pattern = InvestigationPattern(
            id="inv-test",
            name="Test",
            trigger=InvestigationTrigger(),  # No signals
        )
        context = InvestigationContext()

        # No signals means always trigger
        result = executor._check_triggers(pattern, context)
        self.assertTrue(result)

    def test_executor_check_triggers_or_logic(self):
        """Test trigger checking with OR logic."""
        executor = InvestigationExecutor()

        pattern = InvestigationPattern(
            id="inv-test",
            name="Test",
            trigger=InvestigationTrigger(
                graph_signals=[
                    TriggerSignal(property="prop1"),
                    TriggerSignal(property="prop2"),
                ],
                require_all=False,  # OR logic
            ),
        )

        # Only one property true - should trigger
        context = InvestigationContext(
            node_properties={"prop1": True, "prop2": False},
        )
        self.assertTrue(executor._check_triggers(pattern, context))

        # Neither true - should not trigger
        context2 = InvestigationContext(
            node_properties={"prop1": False, "prop2": False},
        )
        self.assertFalse(executor._check_triggers(pattern, context2))

    def test_executor_check_triggers_and_logic(self):
        """Test trigger checking with AND logic."""
        executor = InvestigationExecutor()

        pattern = InvestigationPattern(
            id="inv-test",
            name="Test",
            trigger=InvestigationTrigger(
                graph_signals=[
                    TriggerSignal(property="prop1"),
                    TriggerSignal(property="prop2"),
                ],
                require_all=True,  # AND logic
            ),
        )

        # Both properties true - should trigger
        context = InvestigationContext(
            node_properties={"prop1": True, "prop2": True},
        )
        self.assertTrue(executor._check_triggers(pattern, context))

        # Only one true - should not trigger
        context2 = InvestigationContext(
            node_properties={"prop1": True, "prop2": False},
        )
        self.assertFalse(executor._check_triggers(pattern, context2))

    def test_executor_substitute_variables(self):
        """Test variable substitution."""
        executor = InvestigationExecutor()

        context = InvestigationContext(
            function_name="withdraw",
            contract_name="Vault",
        )

        text = "FIND functions WHERE name = ${function_name} IN ${contract_name}"
        result = executor._substitute_variables(text, context)

        self.assertIn("withdraw", result)
        self.assertIn("Vault", result)
        self.assertNotIn("${", result)

    def test_executor_basic_verdict(self):
        """Test basic verdict generation without LLM."""
        executor = InvestigationExecutor()

        step_results = [
            StepResult(
                step_id=1,
                action=InvestigationAction.EXPLORE_GRAPH,
                success=True,
                evidence=["Found vulnerability in withdraw"],
            ),
            StepResult(
                step_id=2,
                action=InvestigationAction.REASON,
                success=True,
                evidence=["Attack path exists"],
            ),
        ]

        verdict = executor._basic_verdict(step_results)

        self.assertIn(
            verdict["verdict"],
            [InvestigationVerdict.LIKELY_VULNERABLE, InvestigationVerdict.UNCERTAIN],
        )
        self.assertGreater(verdict["confidence"], 0)

    def test_executor_execute_skipped(self):
        """Test execution when triggers not met."""
        executor = InvestigationExecutor()

        pattern = InvestigationPattern(
            id="inv-test",
            name="Test",
            trigger=InvestigationTrigger(
                graph_signals=[
                    TriggerSignal(property="required_prop"),
                ],
            ),
        )

        # Context missing required property
        context = InvestigationContext(
            node_properties={"other_prop": True},
        )

        result = asyncio.run(executor.execute(pattern, context))

        self.assertEqual(result.verdict, InvestigationVerdict.SKIPPED)
        self.assertEqual(result.confidence, 100)
        self.assertIn("Trigger conditions not met", result.evidence)

    def test_executor_execute_simple_pattern(self):
        """Test execution of simple pattern."""
        executor = InvestigationExecutor()

        pattern = InvestigationPattern(
            id="inv-test",
            name="Simple Test",
            trigger=InvestigationTrigger(),  # Always triggers
            investigation=InvestigationProcedure(
                hypothesis="Test hypothesis",
                steps=[
                    InvestigationStep(
                        id=1,
                        action=InvestigationAction.READ_CODE,
                        description="Read function code",
                        params={"target": "${function_name}"},
                    ),
                ],
                verdict_criteria=VerdictCriteria(
                    safe="Code looks safe",
                ),
            ),
        )

        context = InvestigationContext(
            function_name="test",
            function_code="function test() public {}",
        )

        result = asyncio.run(executor.execute(pattern, context))

        self.assertEqual(result.pattern_id, "inv-test")
        self.assertIsNotNone(result.verdict)
        self.assertEqual(result.steps_completed, 1)

    def test_executor_register_custom_handler(self):
        """Test registering custom action handler."""
        executor = InvestigationExecutor()

        custom_output = {"custom": "result"}

        def custom_handler(step, context, previous):
            return custom_output

        executor.register_action_handler(
            InvestigationAction.EXPLORE_GRAPH,
            custom_handler,
        )

        self.assertIn(InvestigationAction.EXPLORE_GRAPH, executor._action_handlers)


class TestInvestigationLoader(unittest.TestCase):
    """Test InvestigationLoader."""

    def test_loader_creation(self):
        """Test InvestigationLoader creation."""
        loader = InvestigationLoader()
        self.assertIsInstance(loader._cache, dict)

    def test_loader_load_file(self):
        """Test loading pattern from file."""
        loader = InvestigationLoader()

        # Create temp YAML file
        yaml_content = """
id: inv-test-loader
name: Loader Test
type: investigation
category: test
trigger:
  graph_signals:
    - property: test_prop
investigation:
  hypothesis: Test
  steps:
    - id: 1
      action: reason
      description: Test step
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            temp_path = Path(f.name)

        try:
            pattern = loader.load_file(temp_path)

            self.assertIsNotNone(pattern)
            self.assertEqual(pattern.id, "inv-test-loader")
            self.assertEqual(pattern.type, "investigation")

            # Should be cached
            cached = loader.get_cached("inv-test-loader")
            self.assertIsNotNone(cached)
        finally:
            temp_path.unlink()

    def test_loader_skip_non_investigation(self):
        """Test that non-investigation patterns are skipped."""
        loader = InvestigationLoader()

        yaml_content = """
id: pattern-not-investigation
name: Regular Pattern
type: detection
category: test
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            temp_path = Path(f.name)

        try:
            pattern = loader.load_file(temp_path)
            self.assertIsNone(pattern)
        finally:
            temp_path.unlink()

    def test_loader_load_directory(self):
        """Test loading patterns from directory."""
        loader = InvestigationLoader()

        # Create temp directory with patterns
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test patterns
            for i in range(3):
                yaml_content = f"""
id: inv-dir-{i}
name: Dir Pattern {i}
type: investigation
category: test
"""
                (temp_path / f"inv-{i}.yaml").write_text(yaml_content)

            # Add a non-investigation pattern
            (temp_path / "not-inv.yaml").write_text("""
id: not-inv
name: Not Investigation
type: detection
""")

            patterns = loader.load_directory(temp_path)

            self.assertEqual(len(patterns), 3)
            ids = [p.id for p in patterns]
            self.assertIn("inv-dir-0", ids)
            self.assertIn("inv-dir-1", ids)
            self.assertIn("inv-dir-2", ids)


class TestInvestigationRegistry(unittest.TestCase):
    """Test InvestigationRegistry."""

    def setUp(self):
        """Reset registry before each test."""
        reset_investigation_registry()

    def test_registry_creation(self):
        """Test InvestigationRegistry creation."""
        registry = InvestigationRegistry()
        self.assertEqual(len(registry), 0)

    def test_registry_register(self):
        """Test pattern registration."""
        registry = InvestigationRegistry()

        pattern = InvestigationPattern(
            id="inv-test",
            name="Test",
            category="test-cat",
            tags=["tag1", "tag2"],
        )
        registry.register(pattern)

        self.assertEqual(len(registry), 1)
        self.assertIn("inv-test", registry)

    def test_registry_get(self):
        """Test getting pattern by ID."""
        registry = InvestigationRegistry()

        pattern = InvestigationPattern(id="inv-get-test", name="Get Test")
        registry.register(pattern)

        found = registry.get("inv-get-test")
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "Get Test")

        missing = registry.get("nonexistent")
        self.assertIsNone(missing)

    def test_registry_find_by_category(self):
        """Test finding patterns by category."""
        registry = InvestigationRegistry()

        p1 = InvestigationPattern(id="inv-1", name="P1", category="cat1")
        p2 = InvestigationPattern(id="inv-2", name="P2", category="cat2")
        p3 = InvestigationPattern(id="inv-3", name="P3", category="cat1")

        registry.register(p1)
        registry.register(p2)
        registry.register(p3)

        cat1_patterns = registry.find_by_category("cat1")
        self.assertEqual(len(cat1_patterns), 2)

        cat2_patterns = registry.find_by_category("cat2")
        self.assertEqual(len(cat2_patterns), 1)

    def test_registry_find_by_tag(self):
        """Test finding patterns by tag."""
        registry = InvestigationRegistry()

        p1 = InvestigationPattern(id="inv-1", name="P1", tags=["defi", "oracle"])
        p2 = InvestigationPattern(id="inv-2", name="P2", tags=["defi"])
        p3 = InvestigationPattern(id="inv-3", name="P3", tags=["access"])

        registry.register(p1)
        registry.register(p2)
        registry.register(p3)

        defi_patterns = registry.find_by_tag("defi")
        self.assertEqual(len(defi_patterns), 2)

        oracle_patterns = registry.find_by_tag("oracle")
        self.assertEqual(len(oracle_patterns), 1)

    def test_registry_find_by_trigger(self):
        """Test finding patterns by trigger match."""
        registry = InvestigationRegistry()

        p1 = InvestigationPattern(
            id="inv-1",
            name="P1",
            trigger=InvestigationTrigger(
                graph_signals=[TriggerSignal(property="writes_balance")],
            ),
        )
        p2 = InvestigationPattern(
            id="inv-2",
            name="P2",
            trigger=InvestigationTrigger(
                graph_signals=[TriggerSignal(property="calls_external")],
            ),
        )

        registry.register(p1)
        registry.register(p2)

        # Properties that match p1 only
        matches = registry.find_by_trigger({"writes_balance": True})
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].id, "inv-1")

        # Properties that match p2 only
        matches2 = registry.find_by_trigger({"calls_external": True})
        self.assertEqual(len(matches2), 1)
        self.assertEqual(matches2[0].id, "inv-2")

        # Properties that match both
        matches_both = registry.find_by_trigger({
            "writes_balance": True,
            "calls_external": True,
        })
        self.assertEqual(len(matches_both), 2)

    def test_registry_unregister(self):
        """Test pattern unregistration."""
        registry = InvestigationRegistry()

        pattern = InvestigationPattern(
            id="inv-unreg",
            name="Unreg",
            category="cat",
            tags=["tag"],
        )
        registry.register(pattern)

        self.assertEqual(len(registry), 1)

        result = registry.unregister("inv-unreg")
        self.assertTrue(result)
        self.assertEqual(len(registry), 0)

        # Unregister nonexistent
        result2 = registry.unregister("nonexistent")
        self.assertFalse(result2)

    def test_registry_list_all(self):
        """Test listing all patterns."""
        registry = InvestigationRegistry()

        for i in range(5):
            registry.register(InvestigationPattern(id=f"inv-{i}", name=f"P{i}"))

        all_patterns = registry.list_all()
        self.assertEqual(len(all_patterns), 5)

    def test_registry_list_categories(self):
        """Test listing categories."""
        registry = InvestigationRegistry()

        registry.register(InvestigationPattern(id="inv-1", name="P1", category="cat1"))
        registry.register(InvestigationPattern(id="inv-2", name="P2", category="cat2"))
        registry.register(InvestigationPattern(id="inv-3", name="P3", category="cat1"))

        categories = registry.list_categories()
        self.assertEqual(len(categories), 2)
        self.assertIn("cat1", categories)
        self.assertIn("cat2", categories)


class TestBuiltinInvestigationPatterns(unittest.TestCase):
    """Test built-in investigation patterns."""

    @classmethod
    def setUpClass(cls):
        """Load built-in patterns."""
        reset_investigation_registry()
        cls.registry = get_investigation_registry()

    def test_accounting_invariant_pattern(self):
        """Test inv-bl-001 accounting invariant pattern."""
        pattern = self.registry.get("inv-bl-001")

        if pattern is None:
            self.skipTest("inv-bl-001 not found in registry")

        self.assertEqual(pattern.category, "business-logic")
        self.assertEqual(pattern.type, "investigation")
        self.assertIn("accounting", pattern.tags)

        # Check trigger
        self.assertGreater(len(pattern.trigger.graph_signals), 0)

        # Check steps
        self.assertGreater(len(pattern.investigation.steps), 0)

        # Check verdict criteria
        criteria = pattern.investigation.verdict_criteria
        self.assertTrue(criteria.vulnerable)
        self.assertTrue(criteria.safe)

    def test_privilege_escalation_pattern(self):
        """Test inv-cc-001 privilege escalation pattern."""
        pattern = self.registry.get("inv-cc-001")

        if pattern is None:
            self.skipTest("inv-cc-001 not found in registry")

        self.assertEqual(pattern.category, "cross-contract")
        self.assertIn("privilege-escalation", pattern.tags)

    def test_price_manipulation_pattern(self):
        """Test inv-econ-001 price manipulation pattern."""
        pattern = self.registry.get("inv-econ-001")

        if pattern is None:
            self.skipTest("inv-econ-001 not found in registry")

        self.assertEqual(pattern.category, "economic")
        self.assertIn("flash-loan", pattern.tags)

    def test_dangerous_config_pattern(self):
        """Test inv-cfg-001 dangerous config pattern."""
        pattern = self.registry.get("inv-cfg-001")

        if pattern is None:
            self.skipTest("inv-cfg-001 not found in registry")

        self.assertEqual(pattern.category, "config")

    def test_all_patterns_have_hypothesis(self):
        """Test all patterns have a hypothesis."""
        for pattern in self.registry.list_all():
            self.assertTrue(
                pattern.investigation.hypothesis,
                f"Pattern {pattern.id} missing hypothesis",
            )

    def test_all_patterns_have_steps(self):
        """Test all patterns have investigation steps."""
        for pattern in self.registry.list_all():
            self.assertGreater(
                len(pattern.investigation.steps),
                0,
                f"Pattern {pattern.id} has no steps",
            )

    def test_all_patterns_have_verdict_criteria(self):
        """Test all patterns have verdict criteria."""
        for pattern in self.registry.list_all():
            criteria = pattern.investigation.verdict_criteria
            self.assertTrue(
                criteria.vulnerable or criteria.safe,
                f"Pattern {pattern.id} missing verdict criteria",
            )


class TestGlobalFunctions(unittest.TestCase):
    """Test global convenience functions."""

    def setUp(self):
        """Reset registries."""
        reset_investigation_registry()

    def test_get_investigation_registry(self):
        """Test get_investigation_registry function."""
        registry = get_investigation_registry()
        self.assertIsInstance(registry, InvestigationRegistry)

        # Should return same instance
        registry2 = get_investigation_registry()
        self.assertIs(registry, registry2)

    def test_get_investigation(self):
        """Test get_investigation function."""
        # First register a pattern
        registry = get_investigation_registry()
        pattern = InvestigationPattern(id="inv-global-test", name="Global Test")
        registry.register(pattern)

        found = get_investigation("inv-global-test")
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "Global Test")

    def test_list_investigations(self):
        """Test list_investigations function."""
        registry = get_investigation_registry()

        registry.register(InvestigationPattern(
            id="inv-list-1", name="P1", category="cat1", tags=["tag1"],
        ))
        registry.register(InvestigationPattern(
            id="inv-list-2", name="P2", category="cat2", tags=["tag1"],
        ))

        # List all
        all_patterns = list_investigations()
        self.assertGreaterEqual(len(all_patterns), 2)

        # List by category
        cat1 = list_investigations(category="cat1")
        self.assertEqual(len(cat1), 1)

        # List by tag
        tag1 = list_investigations(tag="tag1")
        self.assertEqual(len(tag1), 2)


if __name__ == "__main__":
    unittest.main()
