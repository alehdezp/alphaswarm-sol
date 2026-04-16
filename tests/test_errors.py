"""
Tests for VKG Error Handling

Tests the LLM-friendly error messages with recovery suggestions.
"""

import unittest

from alphaswarm_sol.errors import (
    AnalysisError,
    BuildError,
    ConfigError,
    ErrorCategory,
    FindingsError,
    QueryError,
    VKGError,
    compilation_error,
    finding_not_found_error,
    graph_not_found_error,
    invalid_status_error,
    no_contracts_error,
    no_findings_error,
    query_syntax_error,
    # Build Failure Diagnostics (Task 3.12)
    slither_not_found_error,
    slither_version_error,
    solc_not_found_error,
    import_resolution_error,
    pragma_version_error,
    circular_import_error,
    parse_error,
    # Proxy Resolution Warnings (Task 3.13)
    ProxyWarning,
    proxy_detected_warning,
    unresolved_implementation_warning,
    storage_collision_warning,
    delegatecall_to_unknown_warning,
    initializer_not_found_warning,
    multiple_implementations_warning,
)


class TestVKGError(unittest.TestCase):
    """Tests for base VKGError class."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = VKGError(
            message="Something went wrong",
            category=ErrorCategory.BUILD,
        )
        self.assertEqual(str(error), "Something went wrong")
        self.assertEqual(error.category, ErrorCategory.BUILD)

    def test_error_with_all_fields(self):
        """Test error with all optional fields."""
        error = VKGError(
            message="Build failed",
            category=ErrorCategory.BUILD,
            location="contracts/Vault.sol",
            details="Compilation error on line 42",
            suggestions=["Fix the syntax error", "Check dependencies"],
            recovery_commands=["forge build", "npm install"],
        )
        self.assertEqual(error.location, "contracts/Vault.sol")
        self.assertEqual(error.details, "Compilation error on line 42")
        self.assertEqual(len(error.suggestions), 2)
        self.assertEqual(len(error.recovery_commands), 2)

    def test_format_cli_basic(self):
        """Test CLI formatting with basic error."""
        error = VKGError(message="Test error")
        output = error.format_cli()
        self.assertIn("Error: Test error", output)
        self.assertIn("vkg --help", output)

    def test_format_cli_full(self):
        """Test CLI formatting with all fields."""
        error = VKGError(
            message="Build failed",
            category=ErrorCategory.BUILD,
            location="contracts/",
            details="No .sol files found",
            suggestions=["Check the path", "Ensure files exist"],
            recovery_commands=["vkg build src/"],
        )
        output = error.format_cli()

        self.assertIn("Error: Build failed", output)
        self.assertIn("Location: contracts/", output)
        self.assertIn("Details: No .sol files found", output)
        self.assertIn("To fix this:", output)
        self.assertIn("1. Check the path", output)
        self.assertIn("2. Ensure files exist", output)
        self.assertIn("Try running:", output)
        self.assertIn("vkg build src/", output)

    def test_to_dict(self):
        """Test conversion to dictionary."""
        error = VKGError(
            message="Test error",
            category=ErrorCategory.ANALYSIS,
            location="/path",
            details="More info",
            suggestions=["Try this"],
            recovery_commands=["cmd"],
        )
        d = error.to_dict()

        self.assertTrue(d["error"])
        self.assertEqual(d["message"], "Test error")
        self.assertEqual(d["category"], "analysis")
        self.assertEqual(d["location"], "/path")
        self.assertEqual(d["suggestions"], ["Try this"])
        self.assertEqual(d["recovery_commands"], ["cmd"])


class TestSpecializedErrors(unittest.TestCase):
    """Tests for specialized error classes."""

    def test_build_error(self):
        """Test BuildError."""
        error = BuildError(message="Build failed")
        self.assertEqual(error.category, ErrorCategory.BUILD)

    def test_analysis_error(self):
        """Test AnalysisError."""
        error = AnalysisError(message="Analysis failed")
        self.assertEqual(error.category, ErrorCategory.ANALYSIS)

    def test_query_error(self):
        """Test QueryError."""
        error = QueryError(message="Query failed")
        self.assertEqual(error.category, ErrorCategory.QUERY)

    def test_findings_error(self):
        """Test FindingsError."""
        error = FindingsError(message="Findings error")
        self.assertEqual(error.category, ErrorCategory.FINDINGS)

    def test_config_error(self):
        """Test ConfigError."""
        error = ConfigError(message="Config error")
        self.assertEqual(error.category, ErrorCategory.CONFIG)


class TestErrorFactoryFunctions(unittest.TestCase):
    """Tests for error factory functions."""

    def test_graph_not_found_error(self):
        """Test graph not found error factory."""
        error = graph_not_found_error("/path/to/graph.json")
        self.assertIsInstance(error, BuildError)
        self.assertIn("not found", str(error).lower())
        self.assertEqual(error.location, "/path/to/graph.json")
        self.assertTrue(len(error.suggestions) > 0)
        self.assertTrue(len(error.recovery_commands) > 0)

        output = error.format_cli()
        self.assertIn("vkg build", output)

    def test_no_contracts_error(self):
        """Test no contracts error factory."""
        error = no_contracts_error("contracts/")
        self.assertIsInstance(error, BuildError)
        self.assertIn("Solidity", str(error))
        self.assertEqual(error.location, "contracts/")

    def test_compilation_error(self):
        """Test compilation error factory."""
        error = compilation_error("Syntax error line 42")
        self.assertIsInstance(error, BuildError)
        self.assertIn("compilation", str(error).lower())
        self.assertIn("Syntax error line 42", error.details)

    def test_finding_not_found_error(self):
        """Test finding not found error factory."""
        error = finding_not_found_error("VKG-ABC123")
        self.assertIsInstance(error, FindingsError)
        self.assertIn("VKG-ABC123", str(error))

        output = error.format_cli()
        self.assertIn("vkg findings list", output)

    def test_invalid_status_error(self):
        """Test invalid status error factory."""
        error = invalid_status_error(
            "bad_status", ["pending", "confirmed", "false_positive"]
        )
        self.assertIsInstance(error, FindingsError)
        self.assertIn("bad_status", str(error))
        self.assertIn("pending", error.details)
        self.assertIn("confirmed", error.details)

    def test_no_findings_error(self):
        """Test no findings error factory."""
        error = no_findings_error()
        self.assertIsInstance(error, AnalysisError)
        self.assertIn("No vulnerabilities", str(error))
        # This should suggest alternatives, not just fail
        self.assertTrue(len(error.suggestions) > 0)

    def test_query_syntax_error(self):
        """Test query syntax error factory."""
        error = query_syntax_error(
            "bad query here",
            "Unexpected token at position 5",
        )
        self.assertIsInstance(error, QueryError)
        self.assertEqual(error.location, "bad query here")
        self.assertIn("Unexpected token", error.details)

        output = error.format_cli()
        self.assertIn("vkg query", output)
        self.assertIn("vkg schema", output)


class TestErrorRecoveryGuidance(unittest.TestCase):
    """Tests verifying error messages provide actionable recovery guidance."""

    def test_all_errors_have_help_reference(self):
        """Test all formatted errors include help reference."""
        errors = [
            VKGError("test"),
            BuildError("test"),
            AnalysisError("test"),
            QueryError("test"),
            FindingsError("test"),
            ConfigError("test"),
        ]
        for error in errors:
            output = error.format_cli()
            self.assertIn("vkg --help", output)

    def test_factory_errors_have_commands(self):
        """Test factory-created errors include recovery commands."""
        errors = [
            graph_not_found_error("/path"),
            no_contracts_error("/path"),
            compilation_error("details"),
            finding_not_found_error("VKG-123"),
            query_syntax_error("query", "details"),
        ]
        for error in errors:
            self.assertTrue(
                len(error.recovery_commands) > 0,
                f"{type(error).__name__} should have recovery commands",
            )

    def test_build_errors_suggest_vkg_build(self):
        """Test build errors suggest rebuilding."""
        errors = [
            graph_not_found_error("/path"),
            no_contracts_error("/path"),
        ]
        for error in errors:
            output = error.format_cli()
            self.assertIn("vkg build", output)

    def test_findings_errors_suggest_list(self):
        """Test findings errors suggest listing findings."""
        error = finding_not_found_error("VKG-MISSING")
        output = error.format_cli()
        self.assertIn("vkg findings list", output)


class TestBuildFailureDiagnostics(unittest.TestCase):
    """Tests for build failure diagnostic errors (Task 3.12)."""

    def test_slither_not_found_error(self):
        """Test Slither not found error."""
        error = slither_not_found_error()
        self.assertIsInstance(error, BuildError)
        self.assertIn("Slither not found", str(error))

        output = error.format_cli()
        self.assertIn("pip install slither-analyzer", output)
        self.assertIn("which slither", output)

    def test_slither_version_error(self):
        """Test Slither version incompatibility error."""
        error = slither_version_error("0.9.0", "0.10.0")
        self.assertIsInstance(error, BuildError)
        self.assertIn("0.9.0", str(error))
        self.assertIn("0.10.0", error.details)

        output = error.format_cli()
        self.assertIn("pip install --upgrade slither-analyzer", output)

    def test_solc_not_found_error(self):
        """Test solc not found error."""
        error = solc_not_found_error()
        self.assertIsInstance(error, BuildError)
        self.assertIn("solc", str(error).lower())

        output = error.format_cli()
        self.assertIn("solc-select", output)

    def test_solc_not_found_with_version(self):
        """Test solc not found error with required version."""
        error = solc_not_found_error("0.8.20")
        self.assertIn("0.8.20", str(error))

    def test_import_resolution_error(self):
        """Test import resolution error."""
        error = import_resolution_error(
            "@openzeppelin/contracts/token/ERC20/ERC20.sol",
            "contracts/Token.sol"
        )
        self.assertIsInstance(error, BuildError)
        self.assertIn("@openzeppelin", str(error))
        self.assertEqual(error.location, "contracts/Token.sol")

        output = error.format_cli()
        self.assertIn("npm install", output)
        self.assertIn("forge install", output)

    def test_pragma_version_error(self):
        """Test pragma version error."""
        error = pragma_version_error(
            "contracts/Vault.sol",
            "^0.8.20",
            ["0.8.17", "0.8.18", "0.8.19"]
        )
        self.assertIsInstance(error, BuildError)
        self.assertIn("^0.8.20", str(error))
        self.assertIn("0.8.17", error.details)
        self.assertEqual(error.location, "contracts/Vault.sol")

        output = error.format_cli()
        self.assertIn("solc-select", output)

    def test_pragma_version_truncates_long_list(self):
        """Test pragma version error truncates available versions."""
        error = pragma_version_error(
            "contracts/Vault.sol",
            "^0.8.20",
            ["0.8.0", "0.8.1", "0.8.2", "0.8.3", "0.8.4", "0.8.5", "0.8.6"]
        )
        # Should show first 5 and add "..."
        self.assertIn("...", error.details)

    def test_circular_import_error(self):
        """Test circular import error."""
        error = circular_import_error(["A.sol", "B.sol", "C.sol", "A.sol"])
        self.assertIsInstance(error, BuildError)
        self.assertIn("Circular import", str(error))
        self.assertIn("A.sol → B.sol → C.sol → A.sol", error.details)

    def test_parse_error(self):
        """Test Solidity parse error."""
        error = parse_error(
            "contracts/Vault.sol",
            42,
            "Expected ';' but found '}'"
        )
        self.assertIsInstance(error, BuildError)
        self.assertIn("parse error", str(error).lower())
        self.assertEqual(error.location, "contracts/Vault.sol:42")
        self.assertIn("Expected ';'", error.details)

        output = error.format_cli()
        self.assertIn("cat -n", output)
        self.assertIn("Vault.sol", output)

    def test_all_build_diagnostics_have_recovery(self):
        """Test all build diagnostic errors have recovery commands."""
        errors = [
            slither_not_found_error(),
            slither_version_error("0.9.0", "0.10.0"),
            solc_not_found_error(),
            import_resolution_error("@oz/ERC20", "Token.sol"),
            pragma_version_error("Vault.sol", "^0.8.20", ["0.8.19"]),
            circular_import_error(["A.sol", "B.sol"]),
            parse_error("Vault.sol", 42, "Syntax error"),
        ]
        for error in errors:
            self.assertTrue(
                len(error.recovery_commands) > 0,
                f"{str(error)[:50]} should have recovery commands"
            )
            self.assertTrue(
                len(error.suggestions) > 0,
                f"{str(error)[:50]} should have suggestions"
            )


class TestProxyWarnings(unittest.TestCase):
    """Tests for proxy resolution warnings (Task 3.13)."""

    def test_proxy_warning_basic(self):
        """Test basic ProxyWarning creation."""
        warning = ProxyWarning(
            message="Test warning",
            contract="Proxy.sol",
            proxy_type="EIP-1967",
            impact="Analysis may be incomplete",
            recommendations=["Do this", "Do that"],
        )
        self.assertEqual(warning.message, "Test warning")
        self.assertEqual(warning.contract, "Proxy.sol")
        self.assertEqual(warning.proxy_type, "EIP-1967")
        self.assertEqual(len(warning.recommendations), 2)

    def test_proxy_warning_format_cli(self):
        """Test proxy warning CLI formatting."""
        warning = ProxyWarning(
            message="Test warning",
            contract="Proxy.sol",
            proxy_type="EIP-1967",
            impact="Analysis incomplete",
            recommendations=["Fix this"],
        )
        output = warning.format_cli()
        self.assertIn("Warning: Test warning", output)
        self.assertIn("Contract: Proxy.sol", output)
        self.assertIn("Proxy Type: EIP-1967", output)
        self.assertIn("Impact: Analysis incomplete", output)
        self.assertIn("1. Fix this", output)

    def test_proxy_warning_to_dict(self):
        """Test proxy warning JSON conversion."""
        warning = ProxyWarning(
            message="Test warning",
            contract="Proxy.sol",
        )
        d = warning.to_dict()
        self.assertTrue(d["warning"])
        self.assertEqual(d["message"], "Test warning")
        self.assertEqual(d["contract"], "Proxy.sol")

    def test_proxy_detected_with_impl(self):
        """Test proxy detected warning with implementation."""
        warning = proxy_detected_warning(
            "TransparentProxy.sol",
            "EIP-1967",
            implementation_found=True
        )
        self.assertIn("implementation", warning.message.lower())
        self.assertEqual(warning.proxy_type, "EIP-1967")
        self.assertTrue(len(warning.recommendations) > 0)
        # Should mention both proxy and implementation
        self.assertIn("implementation", warning.impact.lower())

    def test_proxy_detected_without_impl(self):
        """Test proxy detected warning without implementation."""
        warning = proxy_detected_warning(
            "TransparentProxy.sol",
            "EIP-1967",
            implementation_found=False
        )
        self.assertIn("without implementation", warning.message.lower())
        self.assertIn("INCOMPLETE", warning.impact)

    def test_unresolved_implementation_warning(self):
        """Test unresolved implementation warning."""
        warning = unresolved_implementation_warning("Proxy.sol")
        self.assertIn("resolve", warning.message.lower())
        self.assertIn("INCOMPLETE", warning.impact)
        self.assertTrue(len(warning.recommendations) > 0)

    def test_unresolved_implementation_with_address(self):
        """Test unresolved implementation warning with address."""
        warning = unresolved_implementation_warning(
            "Proxy.sol",
            impl_address="0x1234...abcd"
        )
        self.assertIn("0x1234...abcd", warning.message)

    def test_storage_collision_warning(self):
        """Test storage collision warning."""
        warning = storage_collision_warning(
            "Proxy.sol",
            "Implementation.sol",
            ["slot0", "slot1"]
        )
        self.assertIn("collision", warning.message.lower())
        self.assertIn("slot0", warning.impact)
        self.assertIn("slot1", warning.impact)

    def test_storage_collision_truncates_slots(self):
        """Test storage collision warning truncates long slot list."""
        slots = [f"slot{i}" for i in range(10)]
        warning = storage_collision_warning("Proxy.sol", "Impl.sol", slots)
        # Should show first 5 and indicate more
        self.assertIn("+5 more", warning.impact)

    def test_delegatecall_to_unknown_warning(self):
        """Test delegatecall to unknown target warning."""
        warning = delegatecall_to_unknown_warning(
            "Proxy.sol",
            "execute",
            "targets[msg.sender]"
        )
        self.assertIn("execute", warning.message)
        self.assertIn("targets[msg.sender]", warning.impact)
        self.assertEqual(warning.proxy_type, "dynamic")

    def test_initializer_not_found_warning(self):
        """Test initializer not found warning."""
        warning = initializer_not_found_warning(
            "UpgradeableToken.sol",
            ["initialize", "__Token_init"]
        )
        self.assertIn("initializer", warning.message.lower())
        self.assertIn("initialize", warning.impact)
        self.assertIn("__Token_init", warning.impact)

    def test_multiple_implementations_warning(self):
        """Test multiple implementations warning."""
        warning = multiple_implementations_warning(
            "DiamondProxy.sol",
            ["FacetA", "FacetB", "FacetC"]
        )
        self.assertIn("Multiple", warning.message)
        self.assertIn("FacetA", warning.impact)
        self.assertIn("FacetB", warning.impact)
        self.assertIn("diamond", warning.proxy_type.lower())

    def test_all_proxy_warnings_have_recommendations(self):
        """Test all proxy warnings include recommendations."""
        warnings = [
            proxy_detected_warning("P.sol", "EIP-1967", True),
            proxy_detected_warning("P.sol", "EIP-1967", False),
            unresolved_implementation_warning("P.sol"),
            storage_collision_warning("P.sol", "I.sol", ["slot0"]),
            delegatecall_to_unknown_warning("P.sol", "exec", "target"),
            initializer_not_found_warning("P.sol", ["init"]),
            multiple_implementations_warning("P.sol", ["A", "B"]),
        ]
        for warning in warnings:
            self.assertTrue(
                len(warning.recommendations) > 0,
                f"Warning '{warning.message}' should have recommendations"
            )
            self.assertTrue(
                warning.impact,
                f"Warning '{warning.message}' should have impact description"
            )

    def test_all_proxy_warnings_format_correctly(self):
        """Test all proxy warnings format for CLI output."""
        warnings = [
            proxy_detected_warning("P.sol", "EIP-1967", True),
            unresolved_implementation_warning("P.sol"),
            storage_collision_warning("P.sol", "I.sol", ["slot0"]),
            delegatecall_to_unknown_warning("P.sol", "exec", "target"),
            initializer_not_found_warning("P.sol", ["init"]),
            multiple_implementations_warning("P.sol", ["A", "B"]),
        ]
        for warning in warnings:
            output = warning.format_cli()
            self.assertIn("Warning:", output)
            self.assertIn("Contract:", output)


if __name__ == "__main__":
    unittest.main()
