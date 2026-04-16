#!/usr/bin/env python3
"""AST-based import graph analyzer for src/alphaswarm_sol/testing/.

Builds a symbol-level caller map, EXCLUDING __init__.py barrel re-exports
from caller counts, to categorize each testing module as:
  TRULY_DEAD, TEST_ONLY, PRODUCTION_DEPENDENT, or TRANSITIVE.

Key design: The CLI imports 8 symbols via `from alphaswarm_sol.testing import X`.
That goes through __init__.py, which re-exports from actual modules. We track:
1. Which symbols the CLI needs (from __init__.py)
2. Which actual modules provide those symbols
3. Mark those modules as PRODUCTION_DEPENDENT
4. All other __init__.py re-exports are barrel-only (excluded from liveness)

Output: .vrs/debug/phase-3.1/import-graph.json
"""

import ast
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TESTING_PKG = "alphaswarm_sol.testing"
TESTING_DIR = ROOT / "src" / "alphaswarm_sol" / "testing"
SCAN_DIRS = [ROOT / "src" / "alphaswarm_sol", ROOT / "tests", ROOT / "scripts"]
OUTPUT = ROOT / ".vrs" / "debug" / "phase-3.1" / "import-graph.json"

# The 8 CLI-consumed symbols (from cli/main.py)
CLI_SYMBOLS = {
    "TestTier", "generate_with_fallback", "detect_project_structure",
    "write_scaffold_to_file", "batch_generate_with_quality",
    "QualityTracker", "TIER_DEFINITIONS", "format_tier_summary",
}

# __init__.py files that are barrel re-exporters
# Their re-export imports should NOT count as "real callers"
BARREL_INIT_FILES: set[str] = set()


def file_to_rel(path: Path) -> str:
    """Convert absolute path to project-relative string."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def is_init_file(path: Path) -> bool:
    return path.name == "__init__.py"


def extract_imports(filepath: Path) -> list[dict]:
    """Extract all import statements from a Python file using AST."""
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            names = [alias.name for alias in (node.names or [])]
            imports.append({"module": node.module, "names": names})
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({"module": alias.name, "names": []})
    return imports


def module_to_testing_file(module: str) -> str | None:
    """Map a dotted module path to a testing/ file path."""
    if not module.startswith(TESTING_PKG):
        return None
    rest = module[len(TESTING_PKG):]
    if not rest:
        return file_to_rel(TESTING_DIR / "__init__.py")
    parts = rest.lstrip(".").split(".")
    candidate = TESTING_DIR / "/".join(parts)
    if candidate.with_suffix(".py").exists():
        return file_to_rel(candidate.with_suffix(".py"))
    if (candidate / "__init__.py").exists():
        return file_to_rel(candidate / "__init__.py")
    return None


def classify_caller(filepath: Path) -> str:
    """Classify a file's role in the project."""
    rel = file_to_rel(filepath)
    if rel.startswith("tests/"):
        return "test"
    if rel.startswith("scripts/"):
        return "script"
    if rel.startswith("src/alphaswarm_sol/testing/"):
        return "testing-internal"
    if rel.startswith("src/"):
        return "production"
    return "other"


def trace_init_to_source() -> dict[str, str]:
    """Parse testing/__init__.py to map each re-exported symbol to its source module.

    Returns: {symbol_name: testing_file_rel_path}
    """
    init_path = TESTING_DIR / "__init__.py"
    source = init_path.read_text()
    tree = ast.parse(source)

    symbol_to_source: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            target = module_to_testing_file(node.module)
            if target:
                for alias in (node.names or []):
                    name = alias.asname if alias.asname else alias.name
                    symbol_to_source[name] = target
    return symbol_to_source


def main():
    # Step 1: Map __init__.py re-exports to source modules
    symbol_to_source = trace_init_to_source()

    # Which source modules provide CLI-needed symbols?
    cli_source_modules: set[str] = set()
    for sym in CLI_SYMBOLS:
        if sym in symbol_to_source:
            cli_source_modules.add(symbol_to_source[sym])

    print(f"CLI-consumed symbols trace to these source modules:")
    for m in sorted(cli_source_modules):
        syms = [s for s, src in symbol_to_source.items() if src == m and s in CLI_SYMBOLS]
        print(f"  {m}: {syms}")

    # Step 2: Collect all __init__.py barrel files
    for pyfile in TESTING_DIR.rglob("__init__.py"):
        BARREL_INIT_FILES.add(str(pyfile.resolve()))

    # Step 3: Collect all Python files to scan
    all_files: list[Path] = []
    for scan_dir in SCAN_DIRS:
        if scan_dir.exists():
            all_files.extend(scan_dir.rglob("*.py"))

    # Step 4: Build caller map (excluding barrel __init__.py imports)
    # For each testing file, track who imports from it
    file_callers: dict[str, dict[str, dict]] = defaultdict(lambda: defaultdict(lambda: {"type": "", "symbols": []}))
    barrel_callers: dict[str, list[str]] = defaultdict(list)

    for pyfile in all_files:
        caller_rel = file_to_rel(pyfile)
        caller_type = classify_caller(pyfile)
        is_barrel = str(pyfile.resolve()) in BARREL_INIT_FILES

        imports = extract_imports(pyfile)
        for imp in imports:
            target_file = module_to_testing_file(imp["module"])
            if target_file is None:
                continue

            if is_barrel:
                if caller_rel not in barrel_callers[target_file]:
                    barrel_callers[target_file].append(caller_rel)
            else:
                entry = file_callers[target_file][caller_rel]
                entry["type"] = caller_type
                entry["symbols"].extend(imp["names"])

    # Step 5: Enumerate all testing files
    testing_files: list[str] = []
    for pyfile in sorted(TESTING_DIR.rglob("*.py")):
        rel = file_to_rel(pyfile)
        if "__pycache__" in rel:
            continue
        testing_files.append(rel)

    # Step 6: Categorize each file
    results: dict[str, dict] = {}

    for tf in testing_files:
        callers = file_callers.get(tf, {})
        # Exclude self-references
        real_callers = {k: v for k, v in callers.items() if k != tf}

        production_callers = [k for k, v in real_callers.items() if v["type"] == "production"]
        test_callers = [k for k, v in real_callers.items() if v["type"] == "test"]
        script_callers = [k for k, v in real_callers.items() if v["type"] == "script"]
        internal_callers = [k for k, v in real_callers.items() if v["type"] == "testing-internal"]

        # Check if this module provides CLI symbols (transitively via __init__.py)
        is_cli_source = tf in cli_source_modules

        # Determine category
        if production_callers or is_cli_source:
            category = "PRODUCTION_DEPENDENT"
        elif test_callers or script_callers:
            category = "TEST_ONLY"
        elif internal_callers:
            category = "TRANSITIVE"
        else:
            category = "TRULY_DEAD"

        # For __init__.py itself: it's PRODUCTION_DEPENDENT (CLI imports from it)
        if tf == file_to_rel(TESTING_DIR / "__init__.py"):
            category = "PRODUCTION_DEPENDENT"

        all_symbols = set()
        for caller_info in real_callers.values():
            all_symbols.update(caller_info["symbols"])

        results[tf] = {
            "category": category,
            "is_cli_source": is_cli_source,
            "symbols_imported_by_callers": sorted(all_symbols),
            "real_callers": {
                "production": production_callers,
                "test": test_callers,
                "script": script_callers,
                "testing_internal": internal_callers,
            },
            "barrel_callers_excluded": barrel_callers.get(tf, []),
        }

    # Step 7: Resolve TRANSITIVE dependencies
    # Walk internal callers: if a TRANSITIVE file's only internal callers are
    # all TRULY_DEAD or TRANSITIVE->TRULY_DEAD, it's also TRULY_DEAD.
    changed = True
    iterations = 0
    while changed and iterations < 30:
        changed = False
        iterations += 1
        for tf, info in results.items():
            if info["category"] != "TRANSITIVE":
                continue
            internal = info["real_callers"]["testing_internal"]
            if not internal:
                info["category"] = "TRULY_DEAD"
                changed = True
                continue
            all_dead = all(
                results.get(c, {}).get("category") == "TRULY_DEAD"
                for c in internal
            )
            if all_dead:
                info["category"] = "TRULY_DEAD"
                changed = True

    # Also: modules that are only called by TEST_ONLY/TRULY_DEAD internal callers
    # and have no test/script callers should be TRANSITIVE -> check again
    # Second pass: files whose internal callers are all TEST_ONLY remain TRANSITIVE
    # (they support test infrastructure). But if internal callers are TRULY_DEAD,
    # they become TRULY_DEAD.

    # Step 8: LOC counts
    for tf, info in results.items():
        filepath = ROOT / tf
        if filepath.exists():
            try:
                info["loc"] = len(filepath.read_text(encoding="utf-8", errors="replace").splitlines())
            except Exception:
                info["loc"] = 0
        else:
            info["loc"] = 0

    # Step 9: Summary
    summary = defaultdict(int)
    loc_by_category = defaultdict(int)
    for info in results.values():
        summary[info["category"]] += 1
        loc_by_category[info["category"]] += info.get("loc", 0)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(ROOT),
        "cli_symbols": sorted(CLI_SYMBOLS),
        "cli_source_modules": sorted(cli_source_modules),
        "barrel_files_excluded": sorted(
            file_to_rel(Path(f)) for f in BARREL_INIT_FILES
        ),
        "files": results,
        "summary": dict(summary),
        "loc_by_category": dict(loc_by_category),
        "total_files": len(results),
        "total_loc": sum(info.get("loc", 0) for info in results.values()),
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(f"\nImport graph written to {OUTPUT}")
    print(f"Total files analyzed: {len(results)}")
    print(f"Total LOC: {output['total_loc']}")
    print()
    print("Category breakdown:")
    for cat in ["TRULY_DEAD", "TEST_ONLY", "PRODUCTION_DEPENDENT", "TRANSITIVE"]:
        count = summary.get(cat, 0)
        loc = loc_by_category.get(cat, 0)
        print(f"  {cat}: {count} files, {loc} LOC")

    # CLI symbol verification
    print()
    print("CLI-consumed symbol verification (must all be PRODUCTION_DEPENDENT):")
    for sym in sorted(CLI_SYMBOLS):
        source = symbol_to_source.get(sym, "UNKNOWN")
        if source in results:
            cat = results[source]["category"]
            status = "OK" if cat == "PRODUCTION_DEPENDENT" else f"FAIL ({cat})"
            print(f"  {sym}: {source} -> {status}")
        else:
            print(f"  {sym}: source={source} -> NOT IN RESULTS")

    # TRULY_DEAD files
    print()
    print("TRULY_DEAD files (safe to delete):")
    dead_files = [(tf, info) for tf, info in results.items() if info["category"] == "TRULY_DEAD"]
    total_dead_loc = 0
    for tf, info in sorted(dead_files):
        loc = info.get("loc", 0)
        total_dead_loc += loc
        print(f"  {tf} ({loc} LOC)")
    print(f"\nTotal TRULY_DEAD: {len(dead_files)} files, {total_dead_loc} LOC")

    # harness/ resolution
    print()
    harness_files = [tf for tf in results if "harness/" in tf and "workflow_harness" not in tf]
    if harness_files:
        print("harness/ directory resolution:")
        for hf in sorted(harness_files):
            info = results[hf]
            print(f"  {hf}: {info['category']} ({info.get('loc', 0)} LOC)")
            if info["real_callers"]["testing_internal"]:
                print(f"    internal callers: {info['real_callers']['testing_internal']}")
            if info["real_callers"]["test"]:
                print(f"    test callers: {info['real_callers']['test']}")

    # Validation: no TRULY_DEAD file has the CLI as a caller
    print()
    cli_file = "src/alphaswarm_sol/cli/main.py"
    violations = []
    for tf, info in results.items():
        if info["category"] == "TRULY_DEAD" and cli_file in info["real_callers"].get("production", []):
            violations.append(tf)
    if violations:
        print(f"VALIDATION FAILED: {len(violations)} TRULY_DEAD files have CLI as caller:")
        for v in violations:
            print(f"  {v}")
        sys.exit(1)
    else:
        print("VALIDATION PASSED: No TRULY_DEAD file has CLI as caller")


if __name__ == "__main__":
    main()
