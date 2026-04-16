"""
Tests for Verification Checklist (Task 3.15)

Tests the verification checklist generator for findings.
"""

import unittest

from alphaswarm_sol.findings.verification import (
    VerificationMethod,
    VerificationStep,
    VerificationChecklist,
    generate_checklist,
    generate_reentrancy_checklist,
    generate_access_control_checklist,
    generate_oracle_checklist,
    generate_default_checklist,
)


class TestVerificationMethod(unittest.TestCase):
    """Tests for VerificationMethod enum."""

    def test_method_values(self):
        """Test all method values exist."""
        self.assertEqual(VerificationMethod.CODE_REVIEW.value, "code_review")
        self.assertEqual(VerificationMethod.STATIC_ANALYSIS.value, "static_analysis")
        self.assertEqual(VerificationMethod.DYNAMIC_TEST.value, "dynamic_test")
        self.assertEqual(VerificationMethod.FORMAL_VERIFICATION.value, "formal_verification")
        self.assertEqual(VerificationMethod.MANUAL_TEST.value, "manual_test")


class TestVerificationStep(unittest.TestCase):
    """Tests for VerificationStep dataclass."""

    def test_step_basic(self):
        """Test basic step creation."""
        step = VerificationStep(
            action="Check for reentrancy guard",
            method=VerificationMethod.CODE_REVIEW,
        )
        self.assertEqual(step.action, "Check for reentrancy guard")
        self.assertEqual(step.method, VerificationMethod.CODE_REVIEW)

    def test_step_full(self):
        """Test step with all fields."""
        step = VerificationStep(
            action="Check for nonReentrant modifier",
            method=VerificationMethod.CODE_REVIEW,
            expected="Modifier should be present",
            commands=["grep -n 'nonReentrant' Vault.sol"],
            if_true="Finding is FALSE POSITIVE",
            if_false="Finding is CONFIRMED",
        )
        self.assertEqual(step.expected, "Modifier should be present")
        self.assertEqual(len(step.commands), 1)

    def test_step_to_dict(self):
        """Test step serialization."""
        step = VerificationStep(
            action="Run test",
            method=VerificationMethod.DYNAMIC_TEST,
            commands=["forge test"],
        )
        d = step.to_dict()
        self.assertEqual(d["action"], "Run test")
        self.assertEqual(d["method"], "dynamic_test")
        self.assertIn("forge test", d["commands"])

    def test_step_from_dict(self):
        """Test step deserialization."""
        d = {
            "action": "Review code",
            "method": "code_review",
            "expected": "Safe patterns",
            "commands": ["cat file.sol"],
        }
        step = VerificationStep.from_dict(d)
        self.assertEqual(step.action, "Review code")
        self.assertEqual(step.method, VerificationMethod.CODE_REVIEW)

    def test_step_format_cli(self):
        """Test step CLI formatting."""
        step = VerificationStep(
            action="Check function modifiers",
            method=VerificationMethod.CODE_REVIEW,
            expected="nonReentrant modifier present",
            commands=["grep -n 'nonReentrant' Vault.sol"],
        )
        output = step.format_cli()
        self.assertIn("Check function modifiers", output)
        self.assertIn("Expected:", output)
        self.assertIn("Commands:", output)
        self.assertIn("grep", output)


class TestVerificationChecklist(unittest.TestCase):
    """Tests for VerificationChecklist dataclass."""

    def test_checklist_basic(self):
        """Test basic checklist creation."""
        checklist = VerificationChecklist(
            finding_id="VKG-ABC123",
            pattern="reentrancy",
        )
        self.assertEqual(checklist.finding_id, "VKG-ABC123")
        self.assertEqual(checklist.pattern, "reentrancy")

    def test_checklist_with_steps(self):
        """Test checklist with steps."""
        checklist = VerificationChecklist(
            finding_id="VKG-ABC123",
            pattern="reentrancy",
            steps=[
                VerificationStep(action="Step 1", method=VerificationMethod.CODE_REVIEW),
                VerificationStep(action="Step 2", method=VerificationMethod.DYNAMIC_TEST),
            ],
            estimated_time="10 minutes",
            skill_level="intermediate",
        )
        self.assertEqual(len(checklist.steps), 2)
        self.assertEqual(checklist.estimated_time, "10 minutes")

    def test_checklist_to_dict(self):
        """Test checklist serialization."""
        checklist = VerificationChecklist(
            finding_id="VKG-ABC123",
            pattern="access-control",
            steps=[
                VerificationStep(action="Check", method=VerificationMethod.CODE_REVIEW),
            ],
        )
        d = checklist.to_dict()
        self.assertEqual(d["finding_id"], "VKG-ABC123")
        self.assertEqual(len(d["steps"]), 1)

    def test_checklist_from_dict(self):
        """Test checklist deserialization."""
        d = {
            "finding_id": "VKG-XYZ789",
            "pattern": "oracle",
            "steps": [
                {"action": "Verify", "method": "code_review"},
            ],
            "estimated_time": "15 minutes",
        }
        checklist = VerificationChecklist.from_dict(d)
        self.assertEqual(checklist.finding_id, "VKG-XYZ789")
        self.assertEqual(len(checklist.steps), 1)

    def test_checklist_format_cli(self):
        """Test checklist CLI formatting."""
        checklist = VerificationChecklist(
            finding_id="VKG-ABC123",
            pattern="reentrancy",
            steps=[
                VerificationStep(action="Check guard", method=VerificationMethod.CODE_REVIEW),
            ],
            estimated_time="10 minutes",
            skill_level="intermediate",
        )
        output = checklist.format_cli()
        self.assertIn("VKG-ABC123", output)
        self.assertIn("reentrancy", output)
        self.assertIn("Check guard", output)
        self.assertIn("10 minutes", output)

    def test_checklist_to_markdown(self):
        """Test checklist Markdown formatting."""
        checklist = VerificationChecklist(
            finding_id="VKG-ABC123",
            pattern="reentrancy",
            steps=[
                VerificationStep(
                    action="Check guard",
                    method=VerificationMethod.CODE_REVIEW,
                    expected="Guard present",
                    commands=["grep nonReentrant Vault.sol"],
                ),
            ],
            estimated_time="10 minutes",
        )
        md = checklist.to_markdown()
        self.assertIn("## Verification Checklist", md)
        self.assertIn("VKG-ABC123", md)
        self.assertIn("```bash", md)
        self.assertIn("grep", md)


class TestChecklistGenerators(unittest.TestCase):
    """Tests for pattern-specific checklist generators."""

    def test_generate_reentrancy_checklist(self):
        """Test reentrancy checklist generation."""
        checklist = generate_reentrancy_checklist(
            "VKG-ABC123",
            "Vault.sol",
            "withdraw"
        )
        self.assertEqual(checklist.finding_id, "VKG-ABC123")
        self.assertIn("reentrancy", checklist.pattern.lower())
        self.assertGreater(len(checklist.steps), 0)

        # Should include specific reentrancy checks
        actions = [s.action for s in checklist.steps]
        has_guard_check = any("guard" in a.lower() or "nonReentrant" in a for a in actions)
        self.assertTrue(has_guard_check, "Should check for reentrancy guard")

    def test_generate_access_control_checklist(self):
        """Test access control checklist generation."""
        checklist = generate_access_control_checklist(
            "VKG-DEF456",
            "Token.sol",
            "mint"
        )
        self.assertEqual(checklist.finding_id, "VKG-DEF456")
        self.assertIn("access", checklist.pattern.lower())
        self.assertGreater(len(checklist.steps), 0)

        # Should include access control checks
        actions = [s.action for s in checklist.steps]
        has_modifier_check = any("modifier" in a.lower() or "access" in a.lower() for a in actions)
        self.assertTrue(has_modifier_check, "Should check for access modifiers")

    def test_generate_oracle_checklist(self):
        """Test oracle checklist generation."""
        checklist = generate_oracle_checklist(
            "VKG-GHI789",
            "LendingPool.sol",
            "liquidate"
        )
        self.assertEqual(checklist.finding_id, "VKG-GHI789")
        self.assertIn("oracle", checklist.pattern.lower())
        self.assertGreater(len(checklist.steps), 0)

        # Should include oracle-specific checks
        actions = [s.action for s in checklist.steps]
        has_staleness_check = any("staleness" in a.lower() or "price" in a.lower() for a in actions)
        self.assertTrue(has_staleness_check, "Should check for price staleness")

    def test_generate_default_checklist(self):
        """Test default checklist generation."""
        checklist = generate_default_checklist(
            "VKG-JKL012",
            "unknown-pattern",
            "SomeContract.sol",
            "someFunction"
        )
        self.assertEqual(checklist.finding_id, "VKG-JKL012")
        self.assertEqual(checklist.pattern, "unknown-pattern")
        self.assertGreater(len(checklist.steps), 0)

    def test_generate_checklist_dispatches_reentrancy(self):
        """Test generate_checklist dispatches to reentrancy."""
        checklist = generate_checklist(
            "VKG-ABC123",
            "reentrancy-classic",
            "Vault.sol",
            "withdraw"
        )
        # Should use reentrancy-specific steps
        self.assertGreater(len(checklist.steps), 2)  # More than default

    def test_generate_checklist_dispatches_access(self):
        """Test generate_checklist dispatches to access control."""
        checklist = generate_checklist(
            "VKG-DEF456",
            "auth-001",
            "Token.sol",
            "mint"
        )
        # Should use access control-specific steps
        self.assertIn("access", checklist.pattern.lower())

    def test_generate_checklist_dispatches_oracle(self):
        """Test generate_checklist dispatches to oracle."""
        checklist = generate_checklist(
            "VKG-GHI789",
            "oracle-manipulation",
            "LendingPool.sol",
            "liquidate"
        )
        # Should use oracle-specific steps
        self.assertIn("oracle", checklist.pattern.lower())

    def test_generate_checklist_uses_default(self):
        """Test generate_checklist uses default for unknown patterns."""
        checklist = generate_checklist(
            "VKG-XYZ000",
            "some-unknown-pattern",
            "Contract.sol",
            "function"
        )
        self.assertEqual(checklist.pattern, "some-unknown-pattern")

    def test_all_checklists_have_commands(self):
        """Test all generated checklists include runnable commands."""
        checklists = [
            generate_reentrancy_checklist("id", "C.sol", "f"),
            generate_access_control_checklist("id", "C.sol", "f"),
            generate_oracle_checklist("id", "C.sol", "f"),
            generate_default_checklist("id", "p", "C.sol", "f"),
        ]
        for checklist in checklists:
            has_commands = any(len(s.commands) > 0 for s in checklist.steps)
            self.assertTrue(
                has_commands,
                f"Checklist for {checklist.pattern} should have commands"
            )

    def test_all_checklists_have_expectations(self):
        """Test all generated checklists include expected outcomes."""
        checklists = [
            generate_reentrancy_checklist("id", "C.sol", "f"),
            generate_access_control_checklist("id", "C.sol", "f"),
            generate_oracle_checklist("id", "C.sol", "f"),
        ]
        for checklist in checklists:
            has_expectations = any(s.expected for s in checklist.steps)
            self.assertTrue(
                has_expectations,
                f"Checklist for {checklist.pattern} should have expectations"
            )


class TestVerificationRoundTrip(unittest.TestCase):
    """Tests for serialization round trips."""

    def test_step_round_trip(self):
        """Test step survives round trip."""
        step = VerificationStep(
            action="Complex action",
            method=VerificationMethod.FORMAL_VERIFICATION,
            expected="Formal proof",
            commands=["cmd1", "cmd2"],
            if_true="Safe",
            if_false="Unsafe",
        )
        d = step.to_dict()
        step2 = VerificationStep.from_dict(d)
        self.assertEqual(step.action, step2.action)
        self.assertEqual(step.method, step2.method)
        self.assertEqual(step.commands, step2.commands)

    def test_checklist_round_trip(self):
        """Test checklist survives round trip."""
        checklist = VerificationChecklist(
            finding_id="VKG-ROUND",
            pattern="test-pattern",
            steps=[
                VerificationStep(action="S1", method=VerificationMethod.CODE_REVIEW),
                VerificationStep(action="S2", method=VerificationMethod.DYNAMIC_TEST),
            ],
            estimated_time="5 minutes",
            skill_level="beginner",
        )
        d = checklist.to_dict()
        checklist2 = VerificationChecklist.from_dict(d)

        self.assertEqual(checklist.finding_id, checklist2.finding_id)
        self.assertEqual(checklist.pattern, checklist2.pattern)
        self.assertEqual(len(checklist.steps), len(checklist2.steps))
        self.assertEqual(checklist.estimated_time, checklist2.estimated_time)


if __name__ == "__main__":
    unittest.main()
