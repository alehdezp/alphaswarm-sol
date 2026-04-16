"""Test vm-002-unprotected-transfer pattern (semantic, name-agnostic).

This test demonstrates the superiority of semantic operation-based detection
over name-based regex matching.

COMPARISON:
- OLD PATTERN (public-external-withdraw-no-gate):
  - Uses: property: label, op: regex, value: "withdraw|transfer|redeem"
  - MISSES: extract(), removeFunds(), claimTokens(), fn_0x123()
  - Implementation-DEPENDENT

- NEW PATTERN (vm-002-unprotected-transfer):
  - Uses: has_any_operation: [TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE]
  - CATCHES: ANY function that transfers value OR modifies balances
  - Implementation-AGNOSTIC
"""

import unittest
from pathlib import Path
from alphaswarm_sol.kg.builder import VKGBuilder
from alphaswarm_sol.queries.patterns import PatternEngine
from tests.pattern_loader import load_all_patterns


class TestVm002SemanticPattern(unittest.TestCase):
    """Test semantic operation-based unprotected value transfer detection."""

    @classmethod
    def setUpClass(cls):
        """Build knowledge graph from test contracts."""
        # Create test contract demonstrating name-agnostic detection
        test_contract = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract NameAgnosticValueTransfer {
    mapping(address => uint256) public balances;
    mapping(address => uint256) public funds;
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    // VULNERABLE: Standard naming (caught by both old and new patterns)
    function withdraw(uint256 amount) external {
        balances[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }

    // VULNERABLE: Non-standard naming (MISSED by old pattern, CAUGHT by new)
    function extract(uint256 amount) external {
        balances[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }

    // VULNERABLE: Obfuscated naming (MISSED by old pattern, CAUGHT by new)
    function removeFunds(uint256 amount) external {
        funds[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }

    // VULNERABLE: Balance modification (MISSED by old pattern, CAUGHT by new)
    function adjustBalance(address user, uint256 amount) external {
        balances[user] = amount;  // WRITES_USER_BALANCE
    }

    // VULNERABLE: Bytecode-level function (MISSED by old pattern, CAUGHT by new)
    function fn_0x123abc(uint256 amount) external {
        payable(msg.sender).transfer(amount);
    }

    // SAFE: Has access control (excluded by both patterns)
    function withdrawOwner(uint256 amount) external {
        require(msg.sender == owner, "Not owner");
        payable(msg.sender).transfer(amount);
    }

    // SAFE: View function (excluded by both patterns)
    function getBalance(address user) external view returns (uint256) {
        return balances[user];
    }

    // SAFE: Internal function (excluded by both patterns)
    function _internalTransfer(address to, uint256 amount) internal {
        payable(to).transfer(amount);
    }
}
        """

        # Write test contract
        test_dir = Path("tests/contracts")
        test_dir.mkdir(parents=True, exist_ok=True)
        contract_path = test_dir / "NameAgnosticValueTransfer.sol"
        contract_path.write_text(test_contract)

        # Build knowledge graph
        builder = VKGBuilder(Path.cwd())
        cls.graph = builder.build(contract_path)

    def test_semantic_pattern_loaded(self):
        """Test that the new semantic pattern loads correctly."""
        patterns = list(load_all_patterns())

        # Find our pattern
        vm002 = [p for p in patterns if p.id == "vm-002-unprotected-transfer"]
        self.assertEqual(len(vm002), 1, "vm-002 pattern should be loaded")

        pattern = vm002[0]
        self.assertEqual(pattern.name, "Unprotected Value Transfer Function")
        self.assertEqual(pattern.severity, "high")
        self.assertEqual(pattern.scope, "Function")

    def test_semantic_detects_standard_names(self):
        """Test that semantic pattern detects standard function names."""
        patterns = list(load_all_patterns())
        vm002 = [p for p in patterns if p.id == "vm-002-unprotected-transfer"][0]

        engine = PatternEngine()
        findings = engine.run(self.graph, [vm002])

        # Should detect withdraw() with standard name
        withdraw_findings = [
            f for f in findings
            if f.get("node_label", "").startswith("withdraw(")
        ]
        self.assertGreater(len(withdraw_findings), 0, "Should detect withdraw()")

    def test_semantic_detects_non_standard_names(self):
        """Test that semantic pattern detects NON-STANDARD function names.

        This is the KEY advantage over name-based patterns.
        """
        patterns = list(load_all_patterns())
        vm002 = [p for p in patterns if p.id == "vm-002-unprotected-transfer"][0]

        engine = PatternEngine()
        findings = engine.run(self.graph, [vm002])

        # Should detect extract() - non-standard name
        extract_findings = [
            f for f in findings
            if f.get("node_label", "").startswith("extract(")
        ]
        self.assertGreater(
            len(extract_findings), 0,
            "Should detect extract() despite non-standard naming"
        )

        # Should detect removeFunds() - non-standard name
        remove_findings = [
            f for f in findings
            if f.get("node_label", "").startswith("removeFunds(")
        ]
        self.assertGreater(
            len(remove_findings), 0,
            "Should detect removeFunds() despite non-standard naming"
        )

    def test_semantic_detects_balance_modification(self):
        """Test that semantic pattern detects BALANCE MODIFICATION.

        Functions that only modify balances (without transfers) should be caught.
        """
        patterns = list(load_all_patterns())
        vm002 = [p for p in patterns if p.id == "vm-002-unprotected-transfer"][0]

        engine = PatternEngine()
        findings = engine.run(self.graph, [vm002])

        # Should detect adjustBalance() - writes balance without transfer
        adjust_findings = [
            f for f in findings
            if f.get("node_label", "").startswith("adjustBalance(")
        ]
        self.assertGreater(
            len(adjust_findings), 0,
            "Should detect adjustBalance() for WRITES_USER_BALANCE operation"
        )

    def test_semantic_detects_obfuscated_names(self):
        """Test that semantic pattern detects OBFUSCATED function names.

        Functions with bytecode-level names like fn_0x123abc should be caught.
        """
        patterns = list(load_all_patterns())
        vm002 = [p for p in patterns if p.id == "vm-002-unprotected-transfer"][0]

        engine = PatternEngine()
        findings = engine.run(self.graph, [vm002])

        # Should detect fn_0x123abc() - obfuscated name
        obfuscated_findings = [
            f for f in findings
            if "fn_0x123abc" in f.get("node_label", "")
        ]
        self.assertGreater(
            len(obfuscated_findings), 0,
            "Should detect fn_0x123abc() despite obfuscated naming"
        )

    def test_semantic_excludes_safe_patterns(self):
        """Test that semantic pattern excludes safe patterns."""
        patterns = list(load_all_patterns())
        vm002 = [p for p in patterns if p.id == "vm-002-unprotected-transfer"][0]

        engine = PatternEngine()
        findings = engine.run(self.graph, [vm002])

        # Should NOT detect withdrawOwner() - has access control
        owner_findings = [
            f for f in findings
            if f.get("node_label", "").startswith("withdrawOwner(")
        ]
        self.assertEqual(
            len(owner_findings), 0,
            "Should NOT detect withdrawOwner() - has access control"
        )

        # Should NOT detect getBalance() - view function
        view_findings = [
            f for f in findings
            if f.get("node_label", "").startswith("getBalance(")
        ]
        self.assertEqual(
            len(view_findings), 0,
            "Should NOT detect getBalance() - view function"
        )

        # Should NOT detect _internalTransfer() - internal function
        internal_findings = [
            f for f in findings
            if f.get("node_label", "").startswith("_internalTransfer(")
        ]
        self.assertEqual(
            len(internal_findings), 0,
            "Should NOT detect _internalTransfer() - internal visibility"
        )

    def test_comparison_with_old_pattern(self):
        """COMPARISON TEST: Show how new pattern outperforms old pattern.

        This test demonstrates that the old name-based pattern MISSES vulnerabilities
        that the new semantic pattern CATCHES.
        """
        # Load all patterns and find both by ID
        all_patterns = list(load_all_patterns())

        vm002_new = [p for p in all_patterns if p.id == "vm-002-unprotected-transfer"]
        old_pattern = [p for p in all_patterns if p.id == "public-external-withdraw-no-gate"]

        if not vm002_new:
            self.skipTest("New pattern not found")
        if not old_pattern:
            self.skipTest("Old pattern not found")

        engine = PatternEngine()

        # Run new pattern
        new_findings = engine.run(self.graph, [vm002_new[0]])

        # Run old pattern (if available)
        old_findings = engine.run(self.graph, [old_pattern[0]])

        # New pattern should find MORE vulnerabilities
        print(f"\n{'='*70}")
        print(f"PATTERN COMPARISON RESULTS")
        print(f"{'='*70}")
        print(f"Old Pattern (name-based):  {len(old_findings)} findings")
        print(f"New Pattern (semantic):    {len(new_findings)} findings")
        print(f"{'='*70}")

        if len(new_findings) > 0:
            print(f"\nNew Pattern Findings:")
            for f in new_findings:
                label = f.get("node_label", "unknown")
                print(f"  ✓ {label}")

        if len(old_findings) > 0:
            print(f"\nOld Pattern Findings:")
            for f in old_findings:
                label = f.get("node_label", "unknown")
                print(f"  ✓ {label}")

        # New pattern should catch at least as many as old pattern
        self.assertGreaterEqual(
            len(new_findings), len(old_findings),
            "New semantic pattern should catch >= old name-based pattern"
        )


if __name__ == "__main__":
    unittest.main()
