"""Tests for context policy security.

Task 9.0: Tests for data minimization security.
"""

import unittest
from datetime import datetime

from alphaswarm_sol.llm.context import Context, ContextItem, Finding, ExternalCall
from alphaswarm_sol.llm.context_policy import (
    ContextPolicy,
    ContextPolicyLevel,
    ContextAuditEntry,
    require_explicit_relaxed,
    get_policy,
    validate_context_for_llm,
)


class TestContextItem(unittest.TestCase):
    """Test ContextItem class."""

    def test_create_item(self):
        """ContextItem can be created."""
        item = ContextItem(
            id="func1",
            type="function",
            name="withdraw",
            content="function withdraw() { ... }",
        )
        self.assertEqual(item.id, "func1")
        self.assertEqual(item.type, "function")
        self.assertEqual(item.name, "withdraw")

    def test_size_bytes(self):
        """size_bytes returns correct size."""
        item = ContextItem(
            id="func1",
            type="function",
            name="test",
            content="abc",  # 3 bytes
        )
        self.assertEqual(item.size_bytes(), 3)

    def test_to_dict(self):
        """to_dict serializes correctly."""
        item = ContextItem(
            id="func1",
            type="function",
            name="test",
            content="code",
            metadata={"key": "value"},
        )
        data = item.to_dict()
        self.assertEqual(data["id"], "func1")
        self.assertEqual(data["metadata"], {"key": "value"})

    def test_from_dict(self):
        """from_dict deserializes correctly."""
        data = {
            "id": "func1",
            "type": "function",
            "name": "test",
            "content": "code",
            "metadata": {"key": "value"},
        }
        item = ContextItem.from_dict(data)
        self.assertEqual(item.id, "func1")
        self.assertEqual(item.metadata["key"], "value")


class TestContext(unittest.TestCase):
    """Test Context class."""

    def _create_test_context(self) -> Context:
        """Create test context with multiple items."""
        ctx = Context()
        ctx.add(
            ContextItem(
                id="func1",
                type="function",
                name="withdraw",
                content="function withdraw() {...}",
            )
        )
        ctx.add(
            ContextItem(
                id="func2",
                type="function",
                name="deposit",
                content="function deposit() {...}",
            )
        )
        ctx.add(
            ContextItem(
                id="func3",
                type="function",
                name="helper",
                content="function helper() {...}",
            )
        )
        ctx.add(
            ContextItem(
                id="var1",
                type="state_variable",
                name="balances",
                content="mapping(address => uint) balances",
            )
        )
        return ctx

    def test_add_and_get(self):
        """Can add and retrieve items."""
        ctx = Context()
        item = ContextItem(id="test", type="function", name="test", content="code")
        ctx.add(item)
        self.assertEqual(ctx.get("test"), item)

    def test_get_all_ids(self):
        """get_all_ids returns all IDs."""
        ctx = self._create_test_context()
        ids = ctx.get_all_ids()
        self.assertIn("func1", ids)
        self.assertIn("func2", ids)
        self.assertIn("var1", ids)

    def test_filter_to_ids(self):
        """filter_to_ids creates new context with subset."""
        ctx = self._create_test_context()
        filtered = ctx.filter_to_ids({"func1", "var1"})

        self.assertIn("func1", filtered.get_all_ids())
        self.assertIn("var1", filtered.get_all_ids())
        self.assertNotIn("func2", filtered.get_all_ids())
        self.assertNotIn("func3", filtered.get_all_ids())

    def test_size_bytes(self):
        """size_bytes returns total size."""
        ctx = Context()
        ctx.add(ContextItem(id="a", type="t", name="n", content="abc"))  # 3 bytes
        ctx.add(ContextItem(id="b", type="t", name="n", content="12345"))  # 5 bytes
        self.assertEqual(ctx.size_bytes(), 8)

    def test_to_string(self):
        """to_string formats for LLM."""
        ctx = Context()
        ctx.add(
            ContextItem(id="func1", type="function", name="test", content="function test()")
        )
        output = ctx.to_string()
        self.assertIn("// function: test", output)
        self.assertIn("function test()", output)

    def test_len(self):
        """__len__ returns item count."""
        ctx = self._create_test_context()
        self.assertEqual(len(ctx), 4)

    def test_contains(self):
        """__contains__ checks for item ID."""
        ctx = self._create_test_context()
        self.assertIn("func1", ctx)
        self.assertNotIn("nonexistent", ctx)

    def test_merge(self):
        """merge combines two contexts."""
        ctx1 = Context()
        ctx1.add(ContextItem(id="a", type="t", name="n", content="1"))

        ctx2 = Context()
        ctx2.add(ContextItem(id="b", type="t", name="n", content="2"))

        merged = ctx1.merge(ctx2)
        self.assertIn("a", merged)
        self.assertIn("b", merged)


class TestFinding(unittest.TestCase):
    """Test Finding class."""

    def test_create_finding(self):
        """Finding can be created."""
        finding = Finding(
            id="VKG-001",
            function_id="func1",
            state_reads=["var1"],
            state_writes=["var2"],
        )
        self.assertEqual(finding.id, "VKG-001")
        self.assertEqual(finding.function_id, "func1")

    def test_to_dict(self):
        """to_dict serializes correctly."""
        finding = Finding(
            id="VKG-001",
            function_id="func1",
            state_reads=["var1"],
            external_calls=[ExternalCall(target_id="target1")],
        )
        data = finding.to_dict()
        self.assertEqual(data["id"], "VKG-001")
        self.assertEqual(data["external_calls"][0]["target_id"], "target1")


class TestContextPolicyLevel(unittest.TestCase):
    """Test ContextPolicyLevel enum."""

    def test_levels_exist(self):
        """All three levels exist."""
        self.assertEqual(ContextPolicyLevel.STRICT.value, "strict")
        self.assertEqual(ContextPolicyLevel.STANDARD.value, "standard")
        self.assertEqual(ContextPolicyLevel.RELAXED.value, "relaxed")


class TestContextPolicy(unittest.TestCase):
    """Test ContextPolicy class."""

    def _create_test_context(self) -> Context:
        """Create test context with multiple items."""
        ctx = Context()
        ctx.add(
            ContextItem(
                id="func1",
                type="function",
                name="withdraw",
                content="function withdraw() {...}",
                metadata={"callers": ["func2"], "callees": [], "modifiers": ["mod1"]},
            )
        )
        ctx.add(
            ContextItem(
                id="func2",
                type="function",
                name="deposit",
                content="function deposit() {...}",
            )
        )
        ctx.add(
            ContextItem(
                id="func3",
                type="function",
                name="helper",
                content="function helper() {...}",
            )
        )
        ctx.add(
            ContextItem(
                id="var1",
                type="state_variable",
                name="balances",
                content="mapping(address => uint) balances",
            )
        )
        ctx.add(
            ContextItem(
                id="mod1",
                type="modifier",
                name="onlyOwner",
                content="modifier onlyOwner() {...}",
            )
        )
        return ctx

    def _create_test_finding(self) -> Finding:
        """Create test finding."""
        return Finding(
            id="VKG-001",
            function_id="func1",
            state_reads=["var1"],
            state_writes=["var1"],
        )

    def test_standard_is_default(self):
        """STANDARD is the default policy level."""
        policy = ContextPolicy()
        self.assertEqual(policy.level, ContextPolicyLevel.STANDARD)

    def test_strict_filters_to_finding_only(self):
        """STRICT policy only includes finding-related code."""
        ctx = self._create_test_context()
        finding = self._create_test_finding()

        policy = ContextPolicy(level=ContextPolicyLevel.STRICT)
        filtered = policy.filter_context(ctx, finding)

        # Should only include func1 and var1
        self.assertIn("func1", filtered.get_all_ids())
        self.assertIn("var1", filtered.get_all_ids())
        self.assertNotIn("func2", filtered.get_all_ids())
        self.assertNotIn("func3", filtered.get_all_ids())
        self.assertNotIn("mod1", filtered.get_all_ids())

    def test_standard_includes_one_hop(self):
        """STANDARD policy includes 1-hop dependencies."""
        ctx = self._create_test_context()
        finding = self._create_test_finding()

        policy = ContextPolicy(level=ContextPolicyLevel.STANDARD)
        filtered = policy.filter_context(ctx, finding)

        # Should include func1, var1, plus caller (func2) and modifier (mod1)
        self.assertIn("func1", filtered.get_all_ids())
        self.assertIn("var1", filtered.get_all_ids())
        self.assertIn("func2", filtered.get_all_ids())  # caller
        self.assertIn("mod1", filtered.get_all_ids())  # modifier
        self.assertNotIn("func3", filtered.get_all_ids())  # not related

    def test_relaxed_includes_all(self):
        """RELAXED policy includes all context."""
        ctx = self._create_test_context()
        finding = self._create_test_finding()

        policy = ContextPolicy(level=ContextPolicyLevel.RELAXED)
        filtered = policy.filter_context(ctx, finding)

        # Should include everything
        self.assertEqual(len(filtered), len(ctx))

    def test_audit_log_created(self):
        """Audit log captures context submissions."""
        ctx = self._create_test_context()
        finding = self._create_test_finding()

        policy = ContextPolicy(level=ContextPolicyLevel.STRICT, enable_audit=True)
        policy.filter_context(ctx, finding)

        audit = policy.get_audit_log()
        self.assertEqual(len(audit), 1)
        self.assertEqual(audit[0].finding_id, "VKG-001")
        self.assertEqual(audit[0].policy_level, ContextPolicyLevel.STRICT)
        self.assertTrue(len(audit[0].items_filtered) > 0)  # Some items were filtered

    def test_audit_disabled(self):
        """Audit can be disabled."""
        ctx = self._create_test_context()
        finding = self._create_test_finding()

        policy = ContextPolicy(level=ContextPolicyLevel.STRICT, enable_audit=False)
        policy.filter_context(ctx, finding)

        audit = policy.get_audit_log()
        self.assertEqual(len(audit), 0)

    def test_secret_detection_warns(self):
        """Secret detection warns about potential leaks."""
        ctx = Context()
        ctx.add(
            ContextItem(
                id="func1",
                type="function",
                name="test",
                content='string PRIVATE_KEY = "abc123"',
            )
        )

        policy = ContextPolicy()
        warnings = policy.validate_no_secrets(ctx)

        self.assertGreater(len(warnings), 0)
        self.assertTrue(any("private key" in w.lower() for w in warnings))

    def test_secret_detection_finds_api_key(self):
        """Secret detection finds API keys."""
        ctx = Context()
        ctx.add(
            ContextItem(
                id="func1",
                type="function",
                name="test",
                content='string API_KEY = "secret123"',
            )
        )

        policy = ContextPolicy()
        warnings = policy.validate_no_secrets(ctx)

        self.assertGreater(len(warnings), 0)

    def test_secret_detection_no_false_positive(self):
        """Secret detection doesn't flag normal code."""
        ctx = Context()
        ctx.add(
            ContextItem(
                id="func1",
                type="function",
                name="test",
                content="function withdraw(uint amount) { balances[msg.sender] -= amount; }",
            )
        )

        policy = ContextPolicy()
        warnings = policy.validate_no_secrets(ctx)

        self.assertEqual(len(warnings), 0)

    def test_get_stats(self):
        """get_stats returns statistics."""
        ctx = self._create_test_context()
        finding = self._create_test_finding()

        policy = ContextPolicy(level=ContextPolicyLevel.STRICT)
        policy.filter_context(ctx, finding)

        stats = policy.get_stats()
        self.assertEqual(stats["total_submissions"], 1)
        self.assertGreater(stats["total_bytes_sent"], 0)

    def test_clear_audit_log(self):
        """clear_audit_log clears the log."""
        ctx = self._create_test_context()
        finding = self._create_test_finding()

        policy = ContextPolicy(level=ContextPolicyLevel.STRICT)
        policy.filter_context(ctx, finding)
        self.assertEqual(len(policy.get_audit_log()), 1)

        policy.clear_audit_log()
        self.assertEqual(len(policy.get_audit_log()), 0)


class TestRequireExplicitRelaxed(unittest.TestCase):
    """Test require_explicit_relaxed decorator."""

    def test_relaxed_without_flag_raises(self):
        """RELAXED policy without flag raises error."""

        @require_explicit_relaxed
        def send_context(context, policy, i_understand_risk=False):
            return True

        ctx = Context()
        policy = ContextPolicy(level=ContextPolicyLevel.RELAXED)

        with self.assertRaises(ValueError) as cm:
            send_context(ctx, policy)

        self.assertIn("i_understand_risk", str(cm.exception))

    def test_relaxed_with_flag_works(self):
        """RELAXED policy with flag works."""

        @require_explicit_relaxed
        def send_context(context, policy, i_understand_risk=False):
            return True

        ctx = Context()
        policy = ContextPolicy(level=ContextPolicyLevel.RELAXED)

        result = send_context(ctx, policy, i_understand_risk=True)
        self.assertTrue(result)

    def test_standard_doesnt_require_flag(self):
        """STANDARD policy doesn't require flag."""

        @require_explicit_relaxed
        def send_context(context, policy, i_understand_risk=False):
            return True

        ctx = Context()
        policy = ContextPolicy(level=ContextPolicyLevel.STANDARD)

        result = send_context(ctx, policy)
        self.assertTrue(result)


class TestGetPolicy(unittest.TestCase):
    """Test get_policy helper function."""

    def test_get_strict_policy(self):
        """get_policy returns strict policy."""
        policy = get_policy("strict")
        self.assertEqual(policy.level, ContextPolicyLevel.STRICT)

    def test_get_standard_policy(self):
        """get_policy returns standard policy."""
        policy = get_policy("standard")
        self.assertEqual(policy.level, ContextPolicyLevel.STANDARD)

    def test_get_relaxed_policy(self):
        """get_policy returns relaxed policy."""
        policy = get_policy("relaxed")
        self.assertEqual(policy.level, ContextPolicyLevel.RELAXED)

    def test_case_insensitive(self):
        """get_policy is case insensitive."""
        policy = get_policy("STANDARD")
        self.assertEqual(policy.level, ContextPolicyLevel.STANDARD)

    def test_invalid_level_raises(self):
        """get_policy raises on invalid level."""
        with self.assertRaises(ValueError):
            get_policy("invalid")


class TestValidateContextForLlm(unittest.TestCase):
    """Test validate_context_for_llm function."""

    def test_safe_context_is_valid(self):
        """Safe context is valid."""
        ctx = Context()
        ctx.add(
            ContextItem(
                id="func1",
                type="function",
                name="test",
                content="function test() {}",
            )
        )

        is_valid, warnings = validate_context_for_llm(ctx)
        self.assertTrue(is_valid)
        self.assertEqual(len(warnings), 0)

    def test_context_with_secrets_is_invalid(self):
        """Context with secrets is invalid."""
        ctx = Context()
        ctx.add(
            ContextItem(
                id="func1",
                type="function",
                name="test",
                content="string PRIVATE_KEY = 'test'",
            )
        )

        is_valid, warnings = validate_context_for_llm(ctx)
        self.assertFalse(is_valid)
        self.assertGreater(len(warnings), 0)


class TestContextAuditEntry(unittest.TestCase):
    """Test ContextAuditEntry class."""

    def test_to_dict(self):
        """to_dict serializes correctly."""
        entry = ContextAuditEntry(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            finding_id="VKG-001",
            policy_level=ContextPolicyLevel.STRICT,
            bytes_sent=100,
            items_included=["func1"],
            items_filtered=["func2", "func3"],
        )
        data = entry.to_dict()
        self.assertEqual(data["finding_id"], "VKG-001")
        self.assertEqual(data["policy_level"], "strict")
        self.assertEqual(data["bytes_sent"], 100)

    def test_from_dict(self):
        """from_dict deserializes correctly."""
        data = {
            "timestamp": "2024-01-01T12:00:00",
            "finding_id": "VKG-001",
            "policy_level": "strict",
            "bytes_sent": 100,
            "items_included": ["func1"],
            "items_filtered": ["func2"],
        }
        entry = ContextAuditEntry.from_dict(data)
        self.assertEqual(entry.finding_id, "VKG-001")
        self.assertEqual(entry.policy_level, ContextPolicyLevel.STRICT)


if __name__ == "__main__":
    unittest.main()
