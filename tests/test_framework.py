"""
Tests for Framework Detection Module

Validates:
1. Framework detection from config files
2. Directory structure inference
3. Import resolution
"""

import tempfile
import unittest
from pathlib import Path


class FrameworkDetectionTests(unittest.TestCase):
    """Tests for framework detection."""

    def test_import_framework_module(self):
        """Framework module can be imported."""
        from alphaswarm_sol.kg.framework import detect_framework, Framework
        self.assertIsNotNone(detect_framework)
        self.assertIsNotNone(Framework)

    def test_detect_foundry(self):
        """Detects Foundry from foundry.toml."""
        from alphaswarm_sol.kg.framework import detect_framework, Framework

        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / "foundry.toml").write_text('[profile.default]\nsrc = "src"\n')
            (project / "src").mkdir()
            (project / "lib").mkdir()

            info = detect_framework(project)

            self.assertEqual(info.framework, Framework.FOUNDRY)
            self.assertIsNotNone(info.config_path)

    def test_detect_hardhat(self):
        """Detects Hardhat from hardhat.config.js."""
        from alphaswarm_sol.kg.framework import detect_framework, Framework

        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / "hardhat.config.js").write_text("module.exports = {}")
            (project / "contracts").mkdir()
            (project / "node_modules").mkdir()

            info = detect_framework(project)

            self.assertEqual(info.framework, Framework.HARDHAT)

    def test_detect_hardhat_ts(self):
        """Detects Hardhat from hardhat.config.ts."""
        from alphaswarm_sol.kg.framework import detect_framework, Framework

        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / "hardhat.config.ts").write_text("export default {}")

            info = detect_framework(project)

            self.assertEqual(info.framework, Framework.HARDHAT)

    def test_detect_truffle(self):
        """Detects Truffle from truffle-config.js."""
        from alphaswarm_sol.kg.framework import detect_framework, Framework

        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / "truffle-config.js").write_text("module.exports = {}")

            info = detect_framework(project)

            self.assertEqual(info.framework, Framework.TRUFFLE)

    def test_infer_foundry_from_structure(self):
        """Infers Foundry from src/lib structure."""
        from alphaswarm_sol.kg.framework import detect_framework, Framework

        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / "src").mkdir()
            (project / "lib").mkdir()

            info = detect_framework(project)

            self.assertEqual(info.framework, Framework.FOUNDRY)

    def test_infer_hardhat_from_structure(self):
        """Infers Hardhat from contracts/node_modules structure."""
        from alphaswarm_sol.kg.framework import detect_framework, Framework

        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / "contracts").mkdir()
            (project / "node_modules").mkdir()

            info = detect_framework(project)

            self.assertEqual(info.framework, Framework.HARDHAT)

    def test_unknown_framework(self):
        """Returns unknown for unrecognized structure."""
        from alphaswarm_sol.kg.framework import detect_framework, Framework

        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            # Empty directory

            info = detect_framework(project)

            self.assertEqual(info.framework, Framework.UNKNOWN)

    def test_framework_info_to_dict(self):
        """FrameworkInfo can be serialized."""
        from alphaswarm_sol.kg.framework import detect_framework

        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / "foundry.toml").write_text("")
            (project / "src").mkdir()

            info = detect_framework(project)
            d = info.to_dict()

            self.assertIn("framework", d)
            self.assertEqual(d["framework"], "foundry")


class RemappingTests(unittest.TestCase):
    """Tests for import remapping resolution."""

    def test_parse_remappings_txt(self):
        """Parses remappings.txt correctly."""
        from alphaswarm_sol.kg.framework import detect_framework

        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / "foundry.toml").write_text("")
            (project / "remappings.txt").write_text(
                "@openzeppelin/=lib/openzeppelin-contracts/\n"
                "forge-std/=lib/forge-std/src/\n"
            )

            info = detect_framework(project)

            self.assertIsNotNone(info.remappings)
            self.assertIn("@openzeppelin/", info.remappings)
            self.assertEqual(info.remappings["@openzeppelin/"], "lib/openzeppelin-contracts/")

    def test_resolve_import_with_remapping(self):
        """Resolves imports using remappings."""
        from alphaswarm_sol.kg.framework import detect_framework, resolve_import

        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / "foundry.toml").write_text("")
            (project / "remappings.txt").write_text("@oz/=lib/oz/\n")
            (project / "lib" / "oz").mkdir(parents=True)
            (project / "lib" / "oz" / "Token.sol").write_text("// token")

            info = detect_framework(project)
            resolved = resolve_import("@oz/Token.sol", info, project)

            self.assertIsNotNone(resolved)
            self.assertTrue(resolved.exists())


class DVDeFiFrameworkTests(unittest.TestCase):
    """Tests framework detection on DVDeFi."""

    def test_detect_dvdefi_framework(self):
        """Detects DVDeFi as Foundry project."""
        from alphaswarm_sol.kg.framework import detect_framework, Framework

        dvdefi_path = Path(__file__).parent.parent / "examples" / "damm-vuln-defi"
        if not dvdefi_path.exists():
            self.skipTest("DVDeFi not found")

        info = detect_framework(dvdefi_path)

        self.assertEqual(info.framework, Framework.FOUNDRY)
        self.assertIsNotNone(info.lib_paths)


if __name__ == "__main__":
    unittest.main()
