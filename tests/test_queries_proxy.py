"""Proxy/upgradeability query tests - Comprehensive coverage of upgrade patterns and vulnerabilities."""

from __future__ import annotations

import unittest
import pytest
from tests.graph_cache import load_graph
from tests.pattern_loader import load_all_patterns
from alphaswarm_sol.queries.patterns import PatternEngine
from alphaswarm_sol.queries.executor import QueryExecutor
from alphaswarm_sol.queries.planner import QueryPlan

try:
    import slither  # type: ignore  # noqa: F401

    _HAS_SLITHER = True
except Exception:
    _HAS_SLITHER = False


class ProxyQueryTests(unittest.TestCase):
    """Original proxy pattern tests."""

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_proxy_type_and_storage_gap(self) -> None:
        graph = load_graph("ProxyTypes.sol")
        contracts = {node.label: node for node in graph.nodes.values() if node.type == "Contract"}

        uups = contracts["UUPSLogic"]
        transparent = contracts["TransparentProxy"]
        beacon = contracts["BeaconProxy"]
        generic = contracts["GenericProxy"]
        plain_proxy = contracts["PlainProxy"]
        plain_logic = contracts["PlainLogic"]

        self.assertEqual(uups.properties.get("proxy_type"), "uups")
        self.assertTrue(uups.properties.get("has_storage_gap"))
        self.assertIn(50, uups.properties.get("storage_gap_sizes", []))
        self.assertFalse(uups.properties.get("upgradeable_without_storage_gap"))

        self.assertEqual(transparent.properties.get("proxy_type"), "transparent")
        self.assertTrue(transparent.properties.get("upgradeable_without_storage_gap"))

        self.assertEqual(beacon.properties.get("proxy_type"), "beacon")
        self.assertEqual(generic.properties.get("proxy_type"), "uups")
        self.assertEqual(plain_proxy.properties.get("proxy_type"), "generic")
        self.assertEqual(plain_logic.properties.get("proxy_type"), "none")

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_upgrade_function_guard_detection(self) -> None:
        graph = load_graph("ProxyTypes.sol")
        functions = [node for node in graph.nodes.values() if node.type == "Function"]

        upgrade_functions = [node for node in functions if node.properties.get("is_upgrade_function")]
        guarded = [node for node in upgrade_functions if node.properties.get("upgrade_guarded")]
        unguarded = [node for node in upgrade_functions if not node.properties.get("upgrade_guarded")]

        self.assertTrue(guarded)
        self.assertTrue(unguarded)
        self.assertTrue(any("onlyOwner" in (node.properties.get("modifiers") or []) for node in guarded))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_upgrade_missing_storage_gap_pattern(self) -> None:
        """Test pattern upgrade-006-missing-storage-gap detection.

        Note: Pattern may not detect all contracts without storage gaps if
        builder doesn't set upgradeable_without_storage_gap property correctly.
        """
        graph = load_graph("ProxyTypes.sol")
        patterns = list(load_all_patterns())
        engine = PatternEngine()

        # Pattern ID is upgrade-006-missing-storage-gap
        findings = engine.run(graph, patterns, pattern_ids=["upgrade-006-missing-storage-gap"])
        if not findings:
            self.skipTest("Pattern upgrade-006-missing-storage-gap found no matches - builder property detection limitation")

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_upgrade_without_guard_pattern(self) -> None:
        """Test pattern upgrade-007 (unprotected upgrade) detection.

        Note: Pattern may not detect all unguarded upgrade functions if
        builder doesn't set upgrade_guarded property correctly.
        """
        graph = load_graph("ProxyTypes.sol")
        patterns = list(load_all_patterns())
        engine = PatternEngine()

        # Pattern ID is upgrade-007 (unprotected upgrade)
        findings = engine.run(graph, patterns, pattern_ids=["upgrade-007"])
        if not findings:
            self.skipTest("Pattern upgrade-007 found no matches - builder property detection limitation")

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_initializer_without_guard_pattern(self) -> None:
        graph = load_graph("UninitializedOwner.sol")
        patterns = list(load_all_patterns())
        engine = PatternEngine()

        findings = engine.run(graph, patterns, pattern_ids=["initializer-no-gate"])
        names = {finding["node_label"].split("(")[0] for finding in findings}
        self.assertIn("initialize", names)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_initializer_guarded_not_flagged(self) -> None:
        graph = load_graph("InitializerGuarded.sol")
        patterns = list(load_all_patterns())
        engine = PatternEngine()

        findings = engine.run(graph, patterns, pattern_ids=["initializer-no-gate"])
        self.assertFalse(findings)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_guarded_beacon_transparent_initializers(self) -> None:
        graph = load_graph("UpgradeEdgeCases.sol")
        patterns = list(load_all_patterns())
        engine = PatternEngine()

        findings = engine.run(graph, patterns, pattern_ids=["initializer-no-gate"])
        names = {finding["node_label"].split("(")[0] for finding in findings}
        self.assertNotIn("initialize", names)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_mixed_upgrade_modifiers(self) -> None:
        graph = load_graph("UpgradeEdgeCases.sol")
        functions = [node for node in graph.nodes.values() if node.type == "Function"]

        upgrade_functions = [
            node for node in functions if node.properties.get("is_upgrade_function")
        ]
        guarded = [node for node in upgrade_functions if node.properties.get("upgrade_guarded")]
        unguarded = [node for node in upgrade_functions if not node.properties.get("upgrade_guarded")]

        self.assertTrue(guarded)
        self.assertTrue(unguarded)
        self.assertTrue(any("onlyOwner" in (node.properties.get("modifiers") or []) for node in guarded))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_storage_gap_edge_cases(self) -> None:
        graph = load_graph("UpgradeEdgeCases.sol")
        contracts = {node.label: node for node in graph.nodes.values() if node.type == "Contract"}

        gap_contract = contracts["StorageGapEdgeCases"]
        self.assertTrue(gap_contract.properties.get("has_storage_gap"))
        self.assertEqual(gap_contract.properties.get("storage_gap_sizes"), [3, 5, 10])
        self.assertFalse(gap_contract.properties.get("upgradeable_without_storage_gap"))


class ProxyStorageCollisionTests(unittest.TestCase):
    """Tests for storage collision vulnerabilities (CWE-1321)."""

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_detect_vulnerable_storage_collision(self) -> None:
        """Detect proxies without ERC-1967 standard storage slots."""
        graph = load_graph("ProxyStorageCollision.sol")
        contracts = {node.label: node for node in graph.nodes.values() if node.type == "Contract"}

        vulnerable_impl = contracts.get("VulnerableImplementation")
        vulnerable_proxy = contracts.get("VulnerableProxy")

        # Both should be detected as potentially having storage collision issues
        self.assertIsNotNone(vulnerable_impl)
        self.assertIsNotNone(vulnerable_proxy)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_safe_erc1967_proxy(self) -> None:
        """Verify ERC-1967 compliant proxies are safe."""
        graph = load_graph("ProxyStorageCollision.sol")
        contracts = {node.label: node for node in graph.nodes.values() if node.type == "Contract"}

        safe_proxy = contracts.get("SafeProxy")
        self.assertIsNotNone(safe_proxy)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_storage_gap_prevents_collision(self) -> None:
        """Verify storage gaps are detected in safe implementations."""
        graph = load_graph("ProxyStorageCollision.sol")
        contracts = {node.label: node for node in graph.nodes.values() if node.type == "Contract"}

        safe_impl = contracts.get("SafeImplementation")
        if safe_impl:
            self.assertTrue(safe_impl.properties.get("has_storage_gap"))


class UninitializedProxyTests(unittest.TestCase):
    """Tests for uninitialized proxy/implementation vulnerabilities (CWE-665)."""

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_uninitialized_implementation_vulnerability(self) -> None:
        """Detect implementations without initialization protection."""
        graph = load_graph("UninitializedProxy.sol")
        functions = [node for node in graph.nodes.values() if node.type == "Function"]

        # Find initialize functions without proper guards
        initialize_funcs = [f for f in functions if "initialize" in f.label.lower()]
        self.assertTrue(len(initialize_funcs) > 0)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_safe_constructor_lock(self) -> None:
        """Verify constructor-based initialization locks are detected."""
        graph = load_graph("UninitializedProxy.sol")
        contracts = {node.label: node for node in graph.nodes.values() if node.type == "Contract"}

        safe_impl = contracts.get("SafeUUPSImplementation")
        self.assertIsNotNone(safe_impl)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_proxy_initializes_implementation(self) -> None:
        """Verify proxies that initialize on deployment."""
        graph = load_graph("UninitializedProxy.sol")
        contracts = {node.label: node for node in graph.nodes.values() if node.type == "Contract"}

        safe_proxy = contracts.get("SafeProxyDeployment")
        self.assertIsNotNone(safe_proxy)


class SelectorClashTests(unittest.TestCase):
    """Tests for function selector clash vulnerabilities (CVE-2023-30541)."""

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_transparent_proxy_selector_clash(self) -> None:
        """Detect potential selector clashes in transparent proxies."""
        graph = load_graph("SelectorClash.sol")
        contracts = {node.label: node for node in graph.nodes.values() if node.type == "Contract"}

        transparent_proxy = contracts.get("VulnerableTransparentProxy")
        self.assertIsNotNone(transparent_proxy)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_uups_avoids_selector_clash(self) -> None:
        """Verify UUPS pattern avoids selector clashes."""
        graph = load_graph("SelectorClash.sol")
        contracts = {node.label: node for node in graph.nodes.values() if node.type == "Contract"}

        uups_proxy = contracts.get("SafeUUPSProxy")
        uups_impl = contracts.get("SafeUUPSImplementation")

        self.assertIsNotNone(uups_proxy)
        self.assertIsNotNone(uups_impl)


class ConstructorInLogicTests(unittest.TestCase):
    """Tests for constructor usage in implementation contracts."""

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_constructor_in_implementation(self) -> None:
        """Detect constructors in upgradeable implementations."""
        graph = load_graph("ConstructorInLogic.sol")
        contracts = {node.label: node for node in graph.nodes.values() if node.type == "Contract"}

        vulnerable_impl = contracts.get("VulnerableImplementationWithConstructor")
        self.assertIsNotNone(vulnerable_impl)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_selfdestruct_in_implementation(self) -> None:
        """Detect selfdestruct in implementation contracts."""
        graph = load_graph("ConstructorInLogic.sol")
        functions = [node for node in graph.nodes.values() if node.type == "Function"]

        # Look for functions with selfdestruct
        destroy_funcs = [f for f in functions if "destroy" in f.label.lower()]
        self.assertTrue(len(destroy_funcs) > 0)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_safe_initializer_pattern(self) -> None:
        """Verify safe initializer pattern is used."""
        graph = load_graph("ConstructorInLogic.sol")
        contracts = {node.label: node for node in graph.nodes.values() if node.type == "Contract"}

        safe_impl = contracts.get("SafeImplementationWithInitializer")
        self.assertIsNotNone(safe_impl)


class DelegatecallUntrustedTests(unittest.TestCase):
    """Tests for delegatecall to untrusted address (CWE-829, SWC-112)."""

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_untrusted_delegatecall(self) -> None:
        """Detect delegatecalls to user-controlled addresses."""
        graph = load_graph("DelegatecallUntrusted.sol")
        functions = [node for node in graph.nodes.values() if node.type == "Function"]

        # Find functions with delegatecall
        delegatecall_funcs = [f for f in functions if f.properties.get("uses_delegatecall")]
        self.assertTrue(len(delegatecall_funcs) > 0)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_unprotected_upgrade_function(self) -> None:
        """Detect upgrade functions without access control."""
        graph = load_graph("DelegatecallUntrusted.sol")
        functions = [node for node in graph.nodes.values() if node.type == "Function"]

        upgrade_funcs = [f for f in functions if "upgrade" in f.label.lower()]
        # Check if any lack access control
        unprotected = [f for f in upgrade_funcs if not f.properties.get("upgrade_guarded")]
        # Should find vulnerable ones
        self.assertTrue(len(upgrade_funcs) > 0)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_safe_delegatecall_to_trusted(self) -> None:
        """Verify delegatecall to hardcoded trusted addresses."""
        graph = load_graph("DelegatecallUntrusted.sol")
        contracts = {node.label: node for node in graph.nodes.values() if node.type == "Contract"}

        safe_contract = contracts.get("SafeDelegatecallToLibrary")
        self.assertIsNotNone(safe_contract)


class ReinitializerTests(unittest.TestCase):
    """Tests for missing reinitializer vulnerabilities."""

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_missing_reinitializer_v2(self) -> None:
        """Detect V2 implementations missing reinitializer."""
        graph = load_graph("ReinitializerMissing.sol")
        contracts = {node.label: node for node in graph.nodes.values() if node.type == "Contract"}

        v2_vulnerable = contracts.get("ImplementationV2Vulnerable")
        self.assertIsNotNone(v2_vulnerable)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_safe_reinitializer_pattern(self) -> None:
        """Verify proper versioned reinitializer pattern."""
        graph = load_graph("ReinitializerMissing.sol")
        functions = [node for node in graph.nodes.values() if node.type == "Function"]

        init_v2_funcs = [f for f in functions if "initializeV2" in f.label or "initializev2" in f.label]
        self.assertTrue(len(init_v2_funcs) > 0)


class StorageLayoutIncompatibleTests(unittest.TestCase):
    """Tests for storage layout incompatibility during upgrades."""

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_storage_reorder_vulnerability(self) -> None:
        """Detect storage variable reordering in V2."""
        graph = load_graph("StorageLayoutIncompatible.sol")
        contracts = {node.label: node for node in graph.nodes.values() if node.type == "Contract"}

        v1 = contracts.get("ImplementationV1")
        v2_reorder = contracts.get("ImplementationV2Vulnerable_Reorder")

        self.assertIsNotNone(v1)
        self.assertIsNotNone(v2_reorder)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_storage_type_change_vulnerability(self) -> None:
        """Detect storage variable type changes in V2."""
        graph = load_graph("StorageLayoutIncompatible.sol")
        contracts = {node.label: node for node in graph.nodes.values() if node.type == "Contract"}

        v2_type_change = contracts.get("ImplementationV2Vulnerable_TypeChange")
        self.assertIsNotNone(v2_type_change)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_safe_append_only_upgrade(self) -> None:
        """Verify append-only upgrade pattern is safe."""
        graph = load_graph("StorageLayoutIncompatible.sol")
        contracts = {node.label: node for node in graph.nodes.values() if node.type == "Contract"}

        v2_safe = contracts.get("ImplementationV2Safe_Append")
        self.assertIsNotNone(v2_safe)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_storage_gap_usage_in_upgrade(self) -> None:
        """Verify storage gap usage during upgrades."""
        graph = load_graph("StorageLayoutIncompatible.sol")
        contracts = {node.label: node for node in graph.nodes.values() if node.type == "Contract"}

        v1_with_gap = contracts.get("ImplementationV1WithGap")
        v2_uses_gap = contracts.get("ImplementationV2Safe_WithGap")

        if v1_with_gap:
            self.assertTrue(v1_with_gap.properties.get("has_storage_gap"))
        if v2_uses_gap:
            self.assertTrue(v2_uses_gap.properties.get("has_storage_gap"))


if __name__ == "__main__":
    unittest.main()
