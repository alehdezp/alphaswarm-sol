"""
Tests for Project Structure Detection (Task 4.2)

Validates detection of Foundry, Hardhat, Brownie, and unknown projects.
"""

import tempfile
import unittest
from pathlib import Path

from alphaswarm_sol.testing.detection import (
    ProjectType,
    ProjectConfig,
    detect_project_structure,
    is_foundry_project,
    is_hardhat_project,
    get_test_file_extension,
)


class TestProjectTypeEnum(unittest.TestCase):
    """Tests for ProjectType enum."""

    def test_all_types_exist(self):
        """All project types are defined."""
        self.assertEqual(ProjectType.FOUNDRY.value, "foundry")
        self.assertEqual(ProjectType.HARDHAT.value, "hardhat")
        self.assertEqual(ProjectType.BROWNIE.value, "brownie")
        self.assertEqual(ProjectType.UNKNOWN.value, "unknown")


class TestProjectConfig(unittest.TestCase):
    """Tests for ProjectConfig dataclass."""

    def test_to_dict(self):
        """Can serialize ProjectConfig to dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config = ProjectConfig(
                project_type=ProjectType.FOUNDRY,
                root=root,
                src_dir=root / "src",
                test_dir=root / "test",
                remappings={"@oz/": "lib/openzeppelin/"},
                solc_version="0.8.20",
                dependencies=["forge-std"],
            )
            d = config.to_dict()
            self.assertEqual(d["project_type"], "foundry")
            self.assertIn("@oz/", d["remappings"])
            self.assertEqual(d["solc_version"], "0.8.20")


class TestDetectFoundryProject(unittest.TestCase):
    """Tests for Foundry project detection."""

    def test_detect_foundry_from_toml(self):
        """Detect Foundry project from foundry.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "foundry.toml").write_text('[profile.default]\nsrc = "src"\n')
            (root / "src").mkdir()

            config = detect_project_structure(root)
            self.assertEqual(config.project_type, ProjectType.FOUNDRY)
            self.assertEqual(config.src_dir, root / "src")

    def test_foundry_with_remappings_in_toml(self):
        """Parse remappings from foundry.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "foundry.toml").write_text(
                '[profile.default]\n'
                'remappings = ["@oz/=lib/openzeppelin-contracts/"]\n'
            )

            config = detect_project_structure(root)
            self.assertEqual(config.project_type, ProjectType.FOUNDRY)
            self.assertIn("@oz/", config.remappings)
            self.assertEqual(config.remappings["@oz/"], "lib/openzeppelin-contracts/")

    def test_foundry_with_remappings_txt(self):
        """Parse remappings from remappings.txt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "foundry.toml").write_text('[profile.default]\n')
            (root / "remappings.txt").write_text(
                "@openzeppelin/=lib/openzeppelin-contracts/\n"
                "forge-std/=lib/forge-std/src/\n"
            )

            config = detect_project_structure(root)
            self.assertIn("@openzeppelin/", config.remappings)
            self.assertIn("forge-std/", config.remappings)

    def test_foundry_detects_lib_dependencies(self):
        """Detect dependencies from lib/ directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "foundry.toml").write_text('[profile.default]\n')
            (root / "lib").mkdir()
            (root / "lib/forge-std").mkdir()
            (root / "lib/openzeppelin-contracts").mkdir()

            config = detect_project_structure(root)
            self.assertIn("forge-std", config.dependencies)
            self.assertIn("openzeppelin-contracts", config.dependencies)

    def test_foundry_with_solc_version(self):
        """Parse solc version from foundry.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "foundry.toml").write_text(
                '[profile.default]\n'
                'solc_version = "0.8.20"\n'
            )

            config = detect_project_structure(root)
            self.assertEqual(config.solc_version, "0.8.20")

    def test_foundry_custom_directories(self):
        """Parse custom src and test directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "foundry.toml").write_text(
                '[profile.default]\n'
                'src = "contracts"\n'
                'test = "tests"\n'
            )
            (root / "contracts").mkdir()
            (root / "tests").mkdir()

            config = detect_project_structure(root)
            self.assertEqual(config.src_dir, root / "contracts")
            self.assertEqual(config.test_dir, root / "tests")


class TestDetectHardhatProject(unittest.TestCase):
    """Tests for Hardhat project detection."""

    def test_detect_hardhat_from_config_js(self):
        """Detect Hardhat from hardhat.config.js."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "hardhat.config.js").write_text("module.exports = {}")
            (root / "contracts").mkdir()

            config = detect_project_structure(root)
            self.assertEqual(config.project_type, ProjectType.HARDHAT)

    def test_detect_hardhat_from_config_ts(self):
        """Detect Hardhat from hardhat.config.ts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "hardhat.config.ts").write_text("export default {}")
            (root / "contracts").mkdir()

            config = detect_project_structure(root)
            self.assertEqual(config.project_type, ProjectType.HARDHAT)

    def test_detect_hardhat_from_package_json(self):
        """Detect Hardhat from package.json dependency."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text(
                '{"devDependencies": {"hardhat": "^2.0"}}'
            )

            config = detect_project_structure(root)
            self.assertEqual(config.project_type, ProjectType.HARDHAT)

    def test_hardhat_has_openzeppelin_remapping(self):
        """Hardhat includes @openzeppelin remapping by default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "hardhat.config.js").write_text("module.exports = {}")

            config = detect_project_structure(root)
            self.assertIn("@openzeppelin/", config.remappings)

    def test_hardhat_uses_contracts_dir(self):
        """Hardhat uses contracts/ as source directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "hardhat.config.js").write_text("module.exports = {}")
            (root / "contracts").mkdir()

            config = detect_project_structure(root)
            self.assertEqual(config.src_dir, root / "contracts")


class TestDetectBrownieProject(unittest.TestCase):
    """Tests for Brownie project detection."""

    def test_detect_brownie(self):
        """Detect Brownie from brownie-config.yaml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "brownie-config.yaml").write_text("project: test\n")

            config = detect_project_structure(root)
            self.assertEqual(config.project_type, ProjectType.BROWNIE)
            self.assertEqual(config.src_dir, root / "contracts")
            self.assertEqual(config.test_dir, root / "tests")


class TestDetectUnknownProject(unittest.TestCase):
    """Tests for unknown project detection."""

    def test_detect_unknown_empty_dir(self):
        """Return UNKNOWN for empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            config = detect_project_structure(root)
            self.assertEqual(config.project_type, ProjectType.UNKNOWN)

    def test_detect_unknown_sol_files_only(self):
        """Return UNKNOWN for directory with only .sol files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "Contract.sol").write_text("// solidity")

            config = detect_project_structure(root)
            self.assertEqual(config.project_type, ProjectType.UNKNOWN)

    def test_unknown_finds_src_dir(self):
        """Unknown project detection finds src/ directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "src").mkdir()

            config = detect_project_structure(root)
            self.assertEqual(config.src_dir, root / "src")

    def test_unknown_finds_contracts_dir(self):
        """Unknown project detection finds contracts/ directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "contracts").mkdir()

            config = detect_project_structure(root)
            self.assertEqual(config.src_dir, root / "contracts")


class TestDetectionPriority(unittest.TestCase):
    """Tests for detection priority order."""

    def test_foundry_takes_priority_over_hardhat(self):
        """Foundry takes priority when both configs exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "foundry.toml").write_text('[profile.default]\n')
            (root / "hardhat.config.js").write_text("module.exports = {}")

            config = detect_project_structure(root)
            self.assertEqual(config.project_type, ProjectType.FOUNDRY)

    def test_hardhat_takes_priority_over_brownie(self):
        """Hardhat config takes priority over Brownie."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "hardhat.config.js").write_text("module.exports = {}")
            (root / "brownie-config.yaml").write_text("project: test\n")

            config = detect_project_structure(root)
            self.assertEqual(config.project_type, ProjectType.HARDHAT)


class TestHelperFunctions(unittest.TestCase):
    """Tests for helper functions."""

    def test_is_foundry_project(self):
        """is_foundry_project correctly identifies Foundry projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "foundry.toml").write_text('[profile.default]\n')

            self.assertTrue(is_foundry_project(root))

    def test_is_not_foundry_project(self):
        """is_foundry_project returns False for non-Foundry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self.assertFalse(is_foundry_project(root))

    def test_is_hardhat_project(self):
        """is_hardhat_project correctly identifies Hardhat projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "hardhat.config.ts").write_text("export default {}")

            self.assertTrue(is_hardhat_project(root))

    def test_is_not_hardhat_project(self):
        """is_hardhat_project returns False for non-Hardhat."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self.assertFalse(is_hardhat_project(root))


class TestGetTestFileExtension(unittest.TestCase):
    """Tests for get_test_file_extension function."""

    def test_foundry_extension(self):
        """Foundry uses .t.sol extension."""
        self.assertEqual(get_test_file_extension(ProjectType.FOUNDRY), ".t.sol")

    def test_hardhat_extension(self):
        """Hardhat uses .ts extension."""
        self.assertEqual(get_test_file_extension(ProjectType.HARDHAT), ".ts")

    def test_brownie_extension(self):
        """Brownie uses .py extension."""
        self.assertEqual(get_test_file_extension(ProjectType.BROWNIE), ".py")

    def test_unknown_defaults_to_foundry(self):
        """Unknown projects default to .t.sol."""
        self.assertEqual(get_test_file_extension(ProjectType.UNKNOWN), ".t.sol")


class TestEdgeCases(unittest.TestCase):
    """Tests for edge cases and error handling."""

    def test_invalid_foundry_toml(self):
        """Handle invalid foundry.toml gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "foundry.toml").write_text("invalid toml {{{")
            (root / "src").mkdir()

            # Should still detect as Foundry, just without parsed config
            config = detect_project_structure(root)
            self.assertEqual(config.project_type, ProjectType.FOUNDRY)

    def test_invalid_package_json(self):
        """Handle invalid package.json gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text("not valid json")

            # Should fall through to UNKNOWN
            config = detect_project_structure(root)
            self.assertEqual(config.project_type, ProjectType.UNKNOWN)

    def test_remappings_txt_with_comments(self):
        """Handle comments in remappings.txt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "foundry.toml").write_text('[profile.default]\n')
            (root / "remappings.txt").write_text(
                "# This is a comment\n"
                "@oz/=lib/oz/\n"
                "# Another comment\n"
            )

            config = detect_project_structure(root)
            self.assertIn("@oz/", config.remappings)
            self.assertNotIn("#", str(config.remappings))

    def test_string_path_input(self):
        """Accept string path as input."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "foundry.toml").write_text('[profile.default]\n')

            # Pass as string, not Path
            config = detect_project_structure(tmpdir)
            self.assertEqual(config.project_type, ProjectType.FOUNDRY)


if __name__ == "__main__":
    unittest.main()
