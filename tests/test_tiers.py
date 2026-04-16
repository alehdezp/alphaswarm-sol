"""Tests for dependency tier system (Task 10.1)."""

import os
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from alphaswarm_sol.core.tiers import (
    Tier,
    Dependency,
    DEPENDENCIES,
    get_available_tiers,
    get_degradation_message,
    get_tier_dependencies,
    get_missing_dependencies,
    format_dependency_status,
)
from alphaswarm_sol.core.availability import (
    AvailabilityChecker,
    AvailabilityReport,
    SystemStatus,
    check_all_dependencies,
    get_effective_tier,
    is_tier_available,
    require_tier,
)


class TestTierEnum(unittest.TestCase):
    """Test Tier enum definition."""

    def test_tier_ordering(self):
        """Tiers are ordered by criticality (lower = more critical)."""
        self.assertLess(Tier.CORE, Tier.ENHANCEMENT)
        self.assertLess(Tier.ENHANCEMENT, Tier.OPTIONAL)
        self.assertLess(Tier.CORE, Tier.OPTIONAL)

    def test_tier_values(self):
        """Tier values are as expected."""
        self.assertEqual(Tier.CORE.value, 0)
        self.assertEqual(Tier.ENHANCEMENT.value, 1)
        self.assertEqual(Tier.OPTIONAL.value, 2)

    def test_tier_names(self):
        """Tier names are accessible."""
        self.assertEqual(Tier.CORE.name, "CORE")
        self.assertEqual(Tier.ENHANCEMENT.name, "ENHANCEMENT")
        self.assertEqual(Tier.OPTIONAL.name, "OPTIONAL")

    def test_tier_iteration(self):
        """Can iterate over all tiers."""
        tiers = list(Tier)
        self.assertEqual(len(tiers), 3)
        self.assertEqual(tiers[0], Tier.CORE)


class TestDependencyDefinitions(unittest.TestCase):
    """Test dependency definitions."""

    def test_core_dependencies_defined(self):
        """Core dependencies are defined."""
        core_deps = get_tier_dependencies(Tier.CORE)
        self.assertGreaterEqual(len(core_deps), 2)

        names = [d.name for d in core_deps]
        self.assertIn("python", names)
        self.assertIn("slither", names)

    def test_slither_is_core(self):
        """Slither is a core dependency."""
        self.assertEqual(DEPENDENCIES["slither"].tier, Tier.CORE)

    def test_aderyn_is_enhancement(self):
        """Aderyn is an enhancement dependency."""
        self.assertEqual(DEPENDENCIES["aderyn"].tier, Tier.ENHANCEMENT)

    def test_llm_is_enhancement(self):
        """LLM provider is an enhancement dependency."""
        self.assertEqual(DEPENDENCIES["llm_provider"].tier, Tier.ENHANCEMENT)

    def test_mcp_is_optional(self):
        """MCP is an optional dependency."""
        self.assertEqual(DEPENDENCIES["mcp"].tier, Tier.OPTIONAL)

    def test_all_dependencies_have_descriptions(self):
        """All dependencies have descriptions."""
        for name, dep in DEPENDENCIES.items():
            self.assertTrue(dep.description, f"{name} has no description")

    def test_enhancement_deps_have_install_hints(self):
        """Enhancement dependencies have install hints."""
        for dep in get_tier_dependencies(Tier.ENHANCEMENT):
            # LLM provider uses env var, not install command
            if dep.name != "llm_provider":
                self.assertTrue(
                    dep.install_hint or dep.env_var,
                    f"{dep.name} has no install hint",
                )


class TestDependencyAvailabilityCheck(unittest.TestCase):
    """Test dependency availability checking."""

    def test_dependency_with_check_fn_available(self):
        """Dependency with check_fn that returns True is available."""
        dep = Dependency(
            name="test",
            tier=Tier.CORE,
            description="Test",
            check_fn=lambda: True,
        )
        self.assertTrue(dep.is_available())

    def test_dependency_with_check_fn_unavailable(self):
        """Dependency with check_fn that returns False is unavailable."""
        dep = Dependency(
            name="test",
            tier=Tier.CORE,
            description="Test",
            check_fn=lambda: False,
        )
        self.assertFalse(dep.is_available())

    def test_dependency_with_check_fn_exception(self):
        """Dependency with check_fn that raises exception is unavailable."""
        dep = Dependency(
            name="test",
            tier=Tier.CORE,
            description="Test",
            check_fn=lambda: 1 / 0,  # Raises ZeroDivisionError
        )
        self.assertFalse(dep.is_available())

    def test_dependency_with_env_var_set(self):
        """Dependency with env_var set is available."""
        dep = Dependency(
            name="test",
            tier=Tier.CORE,
            description="Test",
            env_var="TEST_VAR_12345",
        )
        with patch.dict(os.environ, {"TEST_VAR_12345": "value"}):
            self.assertTrue(dep.is_available())

    def test_dependency_with_env_var_unset(self):
        """Dependency with env_var unset is unavailable."""
        dep = Dependency(
            name="test",
            tier=Tier.CORE,
            description="Test",
            env_var="NONEXISTENT_VAR_12345",
        )
        self.assertFalse(dep.is_available())

    def test_dependency_without_any_check(self):
        """Dependency without any check is always available."""
        dep = Dependency(
            name="test",
            tier=Tier.CORE,
            description="Test",
        )
        self.assertTrue(dep.is_available())

    def test_python_dependency_available(self):
        """Python dependency should always be available."""
        self.assertTrue(DEPENDENCIES["python"].is_available())

    def test_pattern_engine_available(self):
        """Pattern engine dependency should always be available."""
        self.assertTrue(DEPENDENCIES["pattern_engine"].is_available())

    def test_missing_command_unavailable(self):
        """Dependency with missing command is unavailable."""
        dep = Dependency(
            name="test",
            tier=Tier.CORE,
            description="Test",
            check_cmd="nonexistent_command_xyz123 --version",
        )
        self.assertFalse(dep.is_available())


class TestDependencyVersion(unittest.TestCase):
    """Test dependency version retrieval."""

    def test_get_version_no_check_cmd(self):
        """get_version returns None without check_cmd."""
        dep = Dependency(
            name="test",
            tier=Tier.CORE,
            description="Test",
        )
        self.assertIsNone(dep.get_version())

    def test_get_version_caching(self):
        """Version is cached after first call."""
        dep = Dependency(
            name="test",
            tier=Tier.CORE,
            description="Test",
            check_cmd="python --version",
        )
        version1 = dep.get_version()
        version2 = dep.get_version()
        self.assertEqual(version1, version2)


class TestAvailabilityReport(unittest.TestCase):
    """Test AvailabilityReport dataclass."""

    def test_report_creation(self):
        """Can create availability report."""
        report = AvailabilityReport(
            tier=Tier.CORE,
            available=["python", "slither"],
            unavailable=[],
            degraded=False,
            message="All available",
        )
        self.assertEqual(report.tier, Tier.CORE)
        self.assertFalse(report.degraded)

    def test_report_to_dict(self):
        """Report can be serialized to dict."""
        report = AvailabilityReport(
            tier=Tier.ENHANCEMENT,
            available=["foundry"],
            unavailable=["aderyn"],
            degraded=True,
            message="Degraded",
        )
        data = report.to_dict()

        self.assertEqual(data["tier"], "ENHANCEMENT")
        self.assertEqual(data["available"], ["foundry"])
        self.assertEqual(data["unavailable"], ["aderyn"])
        self.assertTrue(data["degraded"])

    def test_is_critical_core_degraded(self):
        """is_critical is True for degraded CORE tier."""
        report = AvailabilityReport(
            tier=Tier.CORE,
            available=[],
            unavailable=["slither"],
            degraded=True,
            message="Fatal",
        )
        self.assertTrue(report.is_critical)

    def test_is_critical_enhancement_degraded(self):
        """is_critical is False for degraded ENHANCEMENT tier."""
        report = AvailabilityReport(
            tier=Tier.ENHANCEMENT,
            available=[],
            unavailable=["aderyn"],
            degraded=True,
            message="Degraded",
        )
        self.assertFalse(report.is_critical)


class TestAvailabilityChecker(unittest.TestCase):
    """Test AvailabilityChecker class."""

    def setUp(self):
        self.checker = AvailabilityChecker()
        self.checker.clear_cache()

    def test_check_all_returns_reports(self):
        """check_all returns reports for all tiers."""
        reports = self.checker.check_all()

        self.assertEqual(len(reports), len(Tier))
        self.assertTrue(all(isinstance(r, AvailabilityReport) for r in reports))

    def test_check_all_covers_all_tiers(self):
        """check_all covers all tier types."""
        reports = self.checker.check_all()
        tiers = {r.tier for r in reports}

        for tier in Tier:
            self.assertIn(tier, tiers)

    def test_cache_works(self):
        """Availability results are cached."""
        # First check
        reports1 = self.checker.check_all()

        # Modify cache to verify it's used
        self.checker._cache["python"] = False

        # Second check should use cache
        reports2 = self.checker.check_all()

        # Find python status in both
        core_report = next(r for r in reports2 if r.tier == Tier.CORE)
        self.assertIn("python", core_report.unavailable)

    def test_force_bypasses_cache(self):
        """force=True bypasses cache."""
        # First check
        self.checker.check_all()

        # Modify cache
        self.checker._cache["python"] = False

        # Force check should bypass cache
        reports = self.checker.check_all(force=True)
        core_report = next(r for r in reports if r.tier == Tier.CORE)
        self.assertIn("python", core_report.available)

    def test_clear_cache(self):
        """clear_cache clears the cache."""
        self.checker.check_all()
        self.assertGreater(len(self.checker._cache), 0)

        self.checker.clear_cache()
        self.assertEqual(len(self.checker._cache), 0)

    def test_check_dependency_by_name(self):
        """Can check single dependency by name."""
        self.assertTrue(self.checker.check_dependency("python"))

    def test_check_dependency_unknown(self):
        """Unknown dependency returns False."""
        self.assertFalse(self.checker.check_dependency("nonexistent_dep"))


class TestEffectiveTier(unittest.TestCase):
    """Test effective tier calculation."""

    def setUp(self):
        self.checker = AvailabilityChecker()
        self.checker.clear_cache()

    def test_effective_tier_with_all_available(self):
        """Effective tier is OPTIONAL when all available."""
        with patch.object(self.checker, "_check_dependency", return_value=True):
            tier = self.checker.get_effective_tier(raise_on_critical=False)
            self.assertEqual(tier, Tier.OPTIONAL)

    def test_effective_tier_core_degraded_raises(self):
        """get_effective_tier raises when CORE is degraded."""
        with patch.object(self.checker, "_check_dependency") as mock:
            # Make CORE dependencies unavailable
            def check(dep):
                return dep.tier != Tier.CORE

            mock.side_effect = check

            with self.assertRaises(RuntimeError) as context:
                self.checker.get_effective_tier(raise_on_critical=True)

            self.assertIn("Cannot run VKG", str(context.exception))

    def test_effective_tier_core_degraded_no_raise(self):
        """get_effective_tier returns CORE when CORE degraded and no raise."""
        with patch.object(self.checker, "_check_dependency") as mock:
            def check(dep):
                return dep.tier != Tier.CORE

            mock.side_effect = check

            tier = self.checker.get_effective_tier(raise_on_critical=False)
            self.assertEqual(tier, Tier.CORE)


class TestSystemStatus(unittest.TestCase):
    """Test SystemStatus retrieval."""

    def setUp(self):
        self.checker = AvailabilityChecker()
        self.checker.clear_cache()

    def test_get_system_status(self):
        """Can get system status."""
        status = self.checker.get_system_status()

        self.assertIsInstance(status, SystemStatus)
        self.assertIsInstance(status.effective_tier, Tier)
        self.assertIsInstance(status.can_run, bool)
        self.assertIsInstance(status.warnings, list)
        self.assertIsInstance(status.reports, list)

    def test_system_status_to_dict(self):
        """System status can be serialized."""
        status = self.checker.get_system_status()
        data = status.to_dict()

        self.assertIn("effective_tier", data)
        self.assertIn("can_run", data)
        self.assertIn("reports", data)


class TestDegradationMessages(unittest.TestCase):
    """Test degradation messaging."""

    def test_core_degradation_message(self):
        """Core degradation has CRITICAL message."""
        msg = get_degradation_message(Tier.CORE)
        self.assertIn("CRITICAL", msg)

    def test_enhancement_degradation_message(self):
        """Enhancement degradation indicates reduced capability."""
        msg = get_degradation_message(Tier.ENHANCEMENT)
        self.assertIn("core features only", msg.lower())

    def test_optional_degradation_message(self):
        """Optional degradation indicates non-critical."""
        msg = get_degradation_message(Tier.OPTIONAL)
        self.assertIn("optional", msg.lower())


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions."""

    def test_check_all_dependencies(self):
        """check_all_dependencies returns reports."""
        reports = check_all_dependencies()
        self.assertEqual(len(reports), len(Tier))

    def test_get_tier_dependencies(self):
        """get_tier_dependencies returns dependencies for tier."""
        core_deps = get_tier_dependencies(Tier.CORE)
        self.assertTrue(all(d.tier == Tier.CORE for d in core_deps))

    def test_get_missing_dependencies(self):
        """get_missing_dependencies returns missing deps."""
        # MCP is always unavailable in current implementation
        missing = get_missing_dependencies(Tier.OPTIONAL)
        names = [d.name for d in missing]
        self.assertIn("mcp", names)

    def test_is_tier_available_core(self):
        """is_tier_available works for CORE tier."""
        # CORE should always be available (python works)
        self.assertTrue(is_tier_available(Tier.CORE))

    def test_require_tier_available(self):
        """require_tier doesn't raise for available tier."""
        # CORE should always be available
        require_tier(Tier.CORE)  # Should not raise


class TestFormatDependencyStatus(unittest.TestCase):
    """Test status formatting."""

    def test_format_available(self):
        """Available dependency shows OK."""
        dep = Dependency(
            name="test",
            tier=Tier.CORE,
            description="Test dependency",
            check_fn=lambda: True,
        )
        output = format_dependency_status(dep)
        self.assertIn("[OK]", output)
        self.assertIn("test", output)

    def test_format_unavailable(self):
        """Unavailable dependency shows MISSING."""
        dep = Dependency(
            name="test",
            tier=Tier.CORE,
            description="Test dependency",
            check_fn=lambda: False,
            install_hint="pip install test",
        )
        output = format_dependency_status(dep)
        self.assertIn("[MISSING]", output)
        self.assertIn("pip install test", output)


class TestFormatReport(unittest.TestCase):
    """Test report formatting."""

    def setUp(self):
        self.checker = AvailabilityChecker()

    def test_format_report_basic(self):
        """Can format basic report."""
        output = self.checker.format_report(verbose=False)
        self.assertIn("VKG Dependency Status", output)
        self.assertIn("CORE", output)

    def test_format_report_verbose(self):
        """Verbose report includes more details."""
        output = self.checker.format_report(verbose=True)
        self.assertIn("VKG Dependency Status", output)
        # Verbose includes descriptions
        self.assertIn("Python runtime", output)


class TestLLMProviderCheck(unittest.TestCase):
    """Test LLM provider availability check."""

    def test_llm_available_with_anthropic(self):
        """LLM is available with ANTHROPIC_API_KEY."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            dep = DEPENDENCIES["llm_provider"]
            # Clear any cache
            dep._version_cache = None
            self.assertTrue(dep.is_available())

    def test_llm_available_with_openai(self):
        """LLM is available with OPENAI_API_KEY."""
        env = {"OPENAI_API_KEY": "test-key"}
        # Clear other keys
        for key in ["ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY"]:
            env[key] = ""

        with patch.dict(os.environ, env, clear=False):
            dep = DEPENDENCIES["llm_provider"]
            self.assertTrue(dep.is_available())

    def test_llm_unavailable_without_keys(self):
        """LLM is unavailable without API keys."""
        env = {
            "ANTHROPIC_API_KEY": "",
            "OPENAI_API_KEY": "",
            "GOOGLE_API_KEY": "",
            "GROQ_API_KEY": "",
            "DEEPSEEK_API_KEY": "",
            "OPENROUTER_API_KEY": "",
        }
        with patch.dict(os.environ, env, clear=False):
            dep = DEPENDENCIES["llm_provider"]
            self.assertFalse(dep.is_available())


class TestOfflineIntegration(unittest.TestCase):
    """Test offline mode integration with tiers."""

    def test_get_current_tier_offline(self):
        """get_current_tier returns CORE in offline mode."""
        with patch.dict(os.environ, {"VKG_OFFLINE": "1"}):
            from alphaswarm_sol.offline import get_current_tier

            tier = get_current_tier()
            self.assertEqual(tier, Tier.CORE)

    def test_can_use_tier_b_offline(self):
        """can_use_tier_b returns False in offline mode."""
        with patch.dict(os.environ, {"VKG_OFFLINE": "1"}):
            from alphaswarm_sol.offline import can_use_tier_b

            self.assertFalse(can_use_tier_b())

    def test_get_current_tier_online(self):
        """get_current_tier works in online mode."""
        with patch.dict(os.environ, {"VKG_OFFLINE": ""}):
            from alphaswarm_sol.offline import get_current_tier

            tier = get_current_tier()
            # Should return some valid tier
            self.assertIn(tier, list(Tier))


if __name__ == "__main__":
    unittest.main()
