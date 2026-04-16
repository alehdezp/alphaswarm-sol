"""
Tests for Import Remapping Resolution (Task 4.3)

Validates import path resolution for various project types and patterns.
"""

import tempfile
import unittest
from pathlib import Path

from alphaswarm_sol.testing.detection import detect_project_structure, ProjectType
from alphaswarm_sol.testing.remappings import (
    ImportResolver,
    extract_imports_from_source,
    extract_pragma_from_source,
    parse_import_statement,
)


class TestImportResolverFoundry(unittest.TestCase):
    """Tests for Foundry project import resolution."""

    def test_resolve_openzeppelin_with_explicit_remapping(self):
        """Resolve @openzeppelin when explicitly remapped in foundry.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "foundry.toml").write_text(
                '[profile.default]\n'
                'remappings = ["@openzeppelin/=lib/openzeppelin-contracts/"]\n'
            )
            # Create the actual file
            oz_path = root / "lib/openzeppelin-contracts/contracts/token/ERC20"
            oz_path.mkdir(parents=True)
            (oz_path / "ERC20.sol").touch()

            config = detect_project_structure(root)
            resolver = ImportResolver(config)

            result = resolver.resolve("@openzeppelin/contracts/token/ERC20/ERC20.sol")
            self.assertIsNotNone(result)
            self.assertIn("openzeppelin", result.lower())
            self.assertIn("ERC20.sol", result)

    def test_resolve_openzeppelin_via_common_patterns(self):
        """Resolve @openzeppelin via common pattern fallback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "foundry.toml").write_text('[profile.default]\n')
            # Create the standard Foundry location
            oz_path = root / "lib/openzeppelin-contracts/contracts/access"
            oz_path.mkdir(parents=True)
            (oz_path / "Ownable.sol").touch()

            config = detect_project_structure(root)
            resolver = ImportResolver(config)

            result = resolver.resolve("@openzeppelin/contracts/access/Ownable.sol")
            self.assertIsNotNone(result)
            self.assertEqual(result, "lib/openzeppelin-contracts/contracts/access/Ownable.sol")

    def test_resolve_forge_std(self):
        """Resolve forge-std imports."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "foundry.toml").write_text('[profile.default]\n')
            forge_path = root / "lib/forge-std/src"
            forge_path.mkdir(parents=True)
            (forge_path / "Test.sol").touch()

            config = detect_project_structure(root)
            resolver = ImportResolver(config)

            result = resolver.resolve("forge-std/Test.sol")
            self.assertEqual(result, "lib/forge-std/src/Test.sol")

    def test_resolve_solmate(self):
        """Resolve solmate imports."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "foundry.toml").write_text('[profile.default]\n')
            solmate_path = root / "lib/solmate/src/tokens"
            solmate_path.mkdir(parents=True)
            (solmate_path / "ERC20.sol").touch()

            config = detect_project_structure(root)
            resolver = ImportResolver(config)

            result = resolver.resolve("solmate/tokens/ERC20.sol")
            self.assertEqual(result, "lib/solmate/src/tokens/ERC20.sol")

    def test_resolve_with_remappings_txt(self):
        """Resolve using remappings.txt file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "foundry.toml").write_text('[profile.default]\n')
            (root / "remappings.txt").write_text("@oz/=lib/oz-contracts/\n")
            oz_path = root / "lib/oz-contracts/token"
            oz_path.mkdir(parents=True)
            (oz_path / "Token.sol").touch()

            config = detect_project_structure(root)
            resolver = ImportResolver(config)

            result = resolver.resolve("@oz/token/Token.sol")
            self.assertIsNotNone(result)
            self.assertIn("oz-contracts", result)


class TestImportResolverHardhat(unittest.TestCase):
    """Tests for Hardhat project import resolution."""

    def test_resolve_openzeppelin_hardhat(self):
        """Resolve @openzeppelin in Hardhat project via node_modules."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "hardhat.config.js").write_text("module.exports = {}")
            # Create node_modules structure
            oz_path = root / "node_modules/@openzeppelin/contracts/token/ERC20"
            oz_path.mkdir(parents=True)
            (oz_path / "ERC20.sol").touch()

            config = detect_project_structure(root)
            resolver = ImportResolver(config)

            result = resolver.resolve("@openzeppelin/contracts/token/ERC20/ERC20.sol")
            self.assertIsNotNone(result)
            self.assertIn("node_modules", result)

    def test_resolve_scoped_package_hardhat(self):
        """Resolve scoped packages in Hardhat."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "hardhat.config.ts").write_text("export default {}")
            pkg_path = root / "node_modules/@custom/lib"
            pkg_path.mkdir(parents=True)
            (pkg_path / "Contract.sol").touch()

            config = detect_project_structure(root)
            resolver = ImportResolver(config)

            result = resolver.resolve("@custom/lib/Contract.sol")
            self.assertIsNotNone(result)
            self.assertEqual(result, "node_modules/@custom/lib/Contract.sol")


class TestImportResolverFallbacks(unittest.TestCase):
    """Tests for fallback behavior."""

    def test_returns_none_for_unknown_import(self):
        """Return None for completely unknown imports."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "foundry.toml").write_text('[profile.default]\n')

            config = detect_project_structure(root)
            resolver = ImportResolver(config)

            result = resolver.resolve("nonexistent/Contract.sol")
            self.assertIsNone(result)

    def test_relative_import_passed_through(self):
        """Relative imports are passed through unchanged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "foundry.toml").write_text('[profile.default]\n')

            config = detect_project_structure(root)
            resolver = ImportResolver(config)

            result = resolver.resolve("./interfaces/IVault.sol")
            self.assertEqual(result, "./interfaces/IVault.sol")

            result2 = resolver.resolve("../utils/Helper.sol")
            self.assertEqual(result2, "../utils/Helper.sol")

    def test_resolve_for_test_with_todo(self):
        """resolve_for_test returns TODO comment for unresolvable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "foundry.toml").write_text('[profile.default]\n')

            config = detect_project_structure(root)
            resolver = ImportResolver(config)

            result = resolver.resolve_for_test("unknown/Contract.sol")
            self.assertIn("TODO", result)
            self.assertIn("Cannot resolve", result)

    def test_resolve_for_test_success(self):
        """resolve_for_test returns proper import statement."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "foundry.toml").write_text('[profile.default]\n')
            forge_path = root / "lib/forge-std/src"
            forge_path.mkdir(parents=True)
            (forge_path / "Test.sol").touch()

            config = detect_project_structure(root)
            resolver = ImportResolver(config)

            result = resolver.resolve_for_test("forge-std/Test.sol")
            self.assertTrue(result.startswith('import "'))
            self.assertTrue(result.endswith('";'))
            self.assertIn("forge-std", result)


class TestSuggestForgeStd(unittest.TestCase):
    """Tests for suggest_forge_std_import."""

    def test_suggest_when_forge_std_exists(self):
        """Suggest forge-std import when lib exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "foundry.toml").write_text('[profile.default]\n')
            (root / "lib/forge-std").mkdir(parents=True)

            config = detect_project_structure(root)
            resolver = ImportResolver(config)

            result = resolver.suggest_forge_std_import()
            self.assertEqual(result, 'import "forge-std/Test.sol";')

    def test_suggest_with_todo_for_hardhat(self):
        """Suggest TODO for Hardhat projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "hardhat.config.js").write_text("module.exports = {}")

            config = detect_project_structure(root)
            resolver = ImportResolver(config)

            result = resolver.suggest_forge_std_import()
            self.assertIn("TODO", result)
            self.assertIn("forge install", result)

    def test_suggest_with_explicit_remapping(self):
        """Suggest works with explicit forge-std remapping."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "foundry.toml").write_text(
                '[profile.default]\n'
                'remappings = ["forge-std/=lib/forge-std/src/"]\n'
            )

            config = detect_project_structure(root)
            resolver = ImportResolver(config)

            result = resolver.suggest_forge_std_import()
            self.assertEqual(result, 'import "forge-std/Test.sol";')


class TestSuggestConsole(unittest.TestCase):
    """Tests for suggest_console_import."""

    def test_console_foundry(self):
        """Suggest forge-std console for Foundry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "foundry.toml").write_text('[profile.default]\n')

            config = detect_project_structure(root)
            resolver = ImportResolver(config)

            result = resolver.suggest_console_import()
            self.assertEqual(result, 'import "forge-std/console.sol";')

    def test_console_hardhat(self):
        """Suggest hardhat console for Hardhat."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "hardhat.config.js").write_text("module.exports = {}")

            config = detect_project_structure(root)
            resolver = ImportResolver(config)

            result = resolver.suggest_console_import()
            self.assertEqual(result, 'import "hardhat/console.sol";')


class TestExtractImports(unittest.TestCase):
    """Tests for extract_imports_from_source."""

    def test_extract_simple_import(self):
        """Extract simple import statement."""
        source = 'import "forge-std/Test.sol";'
        imports = extract_imports_from_source(source)
        self.assertEqual(imports, ["forge-std/Test.sol"])

    def test_extract_named_import(self):
        """Extract named import with braces."""
        source = 'import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";'
        imports = extract_imports_from_source(source)
        self.assertEqual(imports, ["@openzeppelin/contracts/token/ERC20/ERC20.sol"])

    def test_extract_multiple_named_imports(self):
        """Extract import with multiple named exports."""
        source = 'import {Ownable, Pausable} from "@openzeppelin/contracts/access/Ownable.sol";'
        imports = extract_imports_from_source(source)
        self.assertEqual(imports, ["@openzeppelin/contracts/access/Ownable.sol"])

    def test_extract_aliased_import(self):
        """Extract import with alias."""
        source = 'import {ERC20 as Token} from "./Token.sol";'
        imports = extract_imports_from_source(source)
        self.assertEqual(imports, ["./Token.sol"])

    def test_extract_wildcard_import(self):
        """Extract wildcard import."""
        source = 'import * as Utils from "./utils.sol";'
        imports = extract_imports_from_source(source)
        self.assertEqual(imports, ["./utils.sol"])

    def test_extract_multiple_imports(self):
        """Extract multiple import statements."""
        source = '''
        // SPDX-License-Identifier: MIT
        pragma solidity ^0.8.20;

        import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
        import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
        import "./interfaces/IVault.sol";
        import * as Utils from "./utils/Utils.sol";
        '''
        imports = extract_imports_from_source(source)
        self.assertEqual(len(imports), 4)
        self.assertIn("@openzeppelin/contracts/token/ERC20/ERC20.sol", imports)
        self.assertIn("@openzeppelin/contracts/access/Ownable.sol", imports)
        self.assertIn("./interfaces/IVault.sol", imports)
        self.assertIn("./utils/Utils.sol", imports)

    def test_extract_deduplicates(self):
        """Duplicate imports are deduplicated."""
        source = '''
        import "./Token.sol";
        import "./Token.sol";
        '''
        imports = extract_imports_from_source(source)
        self.assertEqual(len(imports), 1)
        self.assertEqual(imports[0], "./Token.sol")

    def test_extract_single_quotes(self):
        """Handle single-quoted imports."""
        source = "import '@openzeppelin/contracts/token/ERC20/ERC20.sol';"
        imports = extract_imports_from_source(source)
        self.assertEqual(imports, ["@openzeppelin/contracts/token/ERC20/ERC20.sol"])


class TestExtractPragma(unittest.TestCase):
    """Tests for extract_pragma_from_source."""

    def test_extract_caret_version(self):
        """Extract pragma with caret version."""
        source = "pragma solidity ^0.8.20;"
        pragma = extract_pragma_from_source(source)
        self.assertEqual(pragma, "^0.8.20")

    def test_extract_range_version(self):
        """Extract pragma with range."""
        source = "pragma solidity >=0.8.0 <0.9.0;"
        pragma = extract_pragma_from_source(source)
        self.assertEqual(pragma, ">=0.8.0 <0.9.0")

    def test_extract_exact_version(self):
        """Extract exact pragma version."""
        source = "pragma solidity 0.8.20;"
        pragma = extract_pragma_from_source(source)
        self.assertEqual(pragma, "0.8.20")

    def test_extract_from_full_source(self):
        """Extract pragma from full source file."""
        source = '''
        // SPDX-License-Identifier: MIT
        pragma solidity ^0.8.20;

        contract Test {}
        '''
        pragma = extract_pragma_from_source(source)
        self.assertEqual(pragma, "^0.8.20")

    def test_returns_none_when_missing(self):
        """Return None when no pragma found."""
        source = "contract Test {}"
        pragma = extract_pragma_from_source(source)
        self.assertIsNone(pragma)


class TestParseImportStatement(unittest.TestCase):
    """Tests for parse_import_statement."""

    def test_parse_simple_import(self):
        """Parse simple import."""
        path, symbols = parse_import_statement('import "./Token.sol";')
        self.assertEqual(path, "./Token.sol")
        self.assertEqual(symbols, [])

    def test_parse_named_import(self):
        """Parse named import."""
        path, symbols = parse_import_statement('import {ERC20} from "./Token.sol";')
        self.assertEqual(path, "./Token.sol")
        self.assertEqual(symbols, ["ERC20"])

    def test_parse_multiple_named(self):
        """Parse multiple named imports."""
        path, symbols = parse_import_statement('import {Foo, Bar, Baz} from "./Lib.sol";')
        self.assertEqual(path, "./Lib.sol")
        self.assertEqual(len(symbols), 3)
        self.assertIn("Foo", symbols)
        self.assertIn("Bar", symbols)

    def test_parse_aliased_import(self):
        """Parse aliased import."""
        path, symbols = parse_import_statement('import {ERC20 as Token} from "./Token.sol";')
        self.assertEqual(path, "./Token.sol")
        # Should extract base name, not alias
        self.assertEqual(symbols, ["ERC20"])

    def test_parse_wildcard_import(self):
        """Parse wildcard import."""
        path, symbols = parse_import_statement('import * as Utils from "./utils.sol";')
        self.assertEqual(path, "./utils.sol")
        self.assertEqual(symbols, ["* as Utils"])

    def test_parse_invalid_returns_none(self):
        """Return None for invalid input."""
        path, symbols = parse_import_statement("not an import")
        self.assertIsNone(path)
        self.assertEqual(symbols, [])


class TestResolverCaching(unittest.TestCase):
    """Tests for resolver caching behavior."""

    def test_caches_resolutions(self):
        """Resolver caches resolution results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "foundry.toml").write_text('[profile.default]\n')

            config = detect_project_structure(root)
            resolver = ImportResolver(config)

            # First call
            resolver.resolve("./test.sol")
            # Second call should use cache
            resolver.resolve("./test.sol")

            stats = resolver.get_resolution_stats()
            self.assertEqual(stats["total"], 1)  # Only one unique resolution

    def test_get_resolution_stats(self):
        """Get resolution statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "foundry.toml").write_text('[profile.default]\n')
            (root / "lib/forge-std/src").mkdir(parents=True)
            (root / "lib/forge-std/src/Test.sol").touch()

            config = detect_project_structure(root)
            resolver = ImportResolver(config)

            resolver.resolve("forge-std/Test.sol")  # Success
            resolver.resolve("unknown/File.sol")    # Failure

            stats = resolver.get_resolution_stats()
            self.assertEqual(stats["resolved"], 1)
            self.assertEqual(stats["unresolved"], 1)
            self.assertEqual(stats["total"], 2)


class TestResolveContractImport(unittest.TestCase):
    """Tests for resolve_contract_import."""

    def test_resolve_contract_in_src(self):
        """Resolve contract path within src directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "foundry.toml").write_text('[profile.default]\n')
            (root / "src").mkdir()
            contract_path = root / "src" / "Token.sol"
            contract_path.touch()

            config = detect_project_structure(root)
            resolver = ImportResolver(config)

            result = resolver.resolve_contract_import(contract_path)
            self.assertIn("Token.sol", result)

    def test_resolve_absolute_path(self):
        """Handle absolute path input."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "foundry.toml").write_text('[profile.default]\n')
            (root / "src").mkdir()
            contract_path = root / "src" / "Vault.sol"
            contract_path.touch()

            config = detect_project_structure(root)
            resolver = ImportResolver(config)

            result = resolver.resolve_contract_import(contract_path)
            self.assertIn("Vault.sol", result)


if __name__ == "__main__":
    unittest.main()
