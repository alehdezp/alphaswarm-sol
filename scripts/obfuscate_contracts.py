#!/usr/bin/env python3
"""Contract Obfuscation Script for GA Validation (Plan 07.3-02).

Creates obfuscated versions of vulnerable contracts to test semantic stability.
Renames identifiers, adds no-op logic, preserves vulnerability behavior.

Purpose: Prove "Names lie. Behavior does not." - PHILOSOPHY.md Pillar 2
"""

from __future__ import annotations

import hashlib
import random
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml


def hash_identifier(name: str, seed: int = 42) -> str:
    """Generate hash-based identifier for obfuscation.

    Args:
        name: Original identifier name
        seed: Random seed for consistency

    Returns:
        Obfuscated name like _0x7a3f
    """
    h = hashlib.md5(f"{name}:{seed}".encode()).hexdigest()[:4]
    return f"_0x{h}"


def find_user_defined_identifiers(source: str) -> Dict[str, str]:
    """Find user-defined identifiers in Solidity source.

    Args:
        source: Solidity source code

    Returns:
        Dict mapping original name to obfuscated name
    """
    identifiers: Dict[str, str] = {}

    # Contract names (but keep interfaces/libraries)
    for match in re.finditer(r'\bcontract\s+([A-Za-z_][A-Za-z0-9_]*)', source):
        name = match.group(1)
        if not name.startswith('I') and not name.startswith('Safe'):  # Keep interfaces
            identifiers[name] = hash_identifier(name)

    # Function names (except constructor, fallback, receive)
    for match in re.finditer(r'\bfunction\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', source):
        name = match.group(1)
        if name not in ('constructor', 'fallback', 'receive'):
            identifiers[name] = hash_identifier(name)

    # Variable names (state variables and parameters)
    for match in re.finditer(r'\b(mapping|uint256|address|bool|bytes|string)\s+(?:public\s+|private\s+|internal\s+)?([a-zA-Z_][a-zA-Z0-9_]*)', source):
        name = match.group(2)
        # Skip common Solidity keywords/built-ins
        if name not in ('msg', 'block', 'tx', 'this', 'now', 'sender', 'value', 'data'):
            identifiers[name] = hash_identifier(name)

    # Event names
    for match in re.finditer(r'\bevent\s+([A-Za-z_][A-Za-z0-9_]*)', source):
        name = match.group(1)
        identifiers[name] = hash_identifier(name)

    # Modifier names
    for match in re.finditer(r'\bmodifier\s+([a-zA-Z_][a-zA-Z0-9_]*)', source):
        name = match.group(1)
        identifiers[name] = hash_identifier(name)

    return identifiers


def obfuscate_identifiers(source: str, mappings: Dict[str, str]) -> str:
    """Apply identifier obfuscation to source code.

    Args:
        source: Original source code
        mappings: Dict mapping original names to obfuscated names

    Returns:
        Obfuscated source code
    """
    result = source

    # Sort by length descending to avoid partial replacements
    for original, obfuscated in sorted(mappings.items(), key=lambda x: -len(x[0])):
        # Use word boundaries to avoid partial matches
        pattern = rf'\b{re.escape(original)}\b'
        result = re.sub(pattern, obfuscated, result)

    return result


def add_noop_logic(source: str, seed: int = 42) -> str:
    """Add benign no-op logic to source code.

    Args:
        source: Source code to modify
        seed: Random seed for consistency

    Returns:
        Source code with no-op logic added
    """
    random.seed(seed)

    noop_patterns = [
        "if (1 > 0) { /* no-op */ }",
        "if (true) { /* preserved */ }",
        "uint256 _nop = 0; _nop = _nop;",
    ]

    # Find function bodies and add no-ops
    # Only add on lines that end with ';' and are complete statements
    lines = source.split('\n')
    result_lines = []
    in_function = False
    brace_depth = 0
    added_count = 0
    paren_depth = 0  # Track parentheses to avoid inserting in multi-line expressions

    for line in lines:
        result_lines.append(line)

        # Track parentheses
        paren_depth += line.count('(') - line.count(')')

        # Track function entry
        if 'function ' in line and '{' in line:
            in_function = True
            brace_depth = 1
            continue

        if in_function:
            brace_depth += line.count('{') - line.count('}')

            # Only add no-op after complete statements (end with ;) and not in multi-line expressions
            stripped = line.strip()
            is_complete_statement = (
                stripped.endswith(';') and
                paren_depth == 0 and
                not stripped.startswith('//') and
                not stripped.startswith('/*') and
                'return ' not in stripped  # Don't add after return statements
            )

            if brace_depth >= 1 and added_count < 3 and is_complete_statement:
                if random.random() < 0.25:  # 25% chance
                    indent = len(line) - len(line.lstrip())
                    noop = random.choice(noop_patterns)
                    result_lines.append(' ' * indent + noop)
                    added_count += 1

            if brace_depth <= 0:
                in_function = False
                added_count = 0

    return '\n'.join(result_lines)


def swap_independent_lines(source: str, seed: int = 42) -> str:
    """Swap independent lines where semantically safe.

    Args:
        source: Source code
        seed: Random seed

    Returns:
        Source code with some lines swapped
    """
    random.seed(seed)

    # Find pairs of consecutive variable declarations and swap some
    lines = source.split('\n')
    result_lines = lines.copy()

    i = 0
    while i < len(result_lines) - 1:
        line1 = result_lines[i].strip()
        line2 = result_lines[i + 1].strip()

        # Only swap simple declarations that don't depend on each other
        if (re.match(r'^(uint256|address|bool)\s+\w+\s*;', line1) and
            re.match(r'^(uint256|address|bool)\s+\w+\s*;', line2) and
            random.random() < 0.2):  # 20% chance
            # Check they don't reference each other
            var1 = re.search(r'\s+(\w+)\s*;', line1)
            var2 = re.search(r'\s+(\w+)\s*;', line2)
            if var1 and var2:
                v1, v2 = var1.group(1), var2.group(1)
                if v1 not in line2 and v2 not in line1:
                    result_lines[i], result_lines[i + 1] = result_lines[i + 1], result_lines[i]
                    i += 2
                    continue
        i += 1

    return '\n'.join(result_lines)


def obfuscate_contract(source: str, seed: int = 42) -> Tuple[str, Dict[str, str]]:
    """Apply full obfuscation to a contract.

    Args:
        source: Original source code
        seed: Random seed for reproducibility

    Returns:
        Tuple of (obfuscated_source, identifier_mappings)
    """
    # Step 1: Find identifiers
    mappings = find_user_defined_identifiers(source)

    # Step 2: Apply identifier renaming
    result = obfuscate_identifiers(source, mappings)

    # Step 3: Add no-op logic
    result = add_noop_logic(result, seed)

    # Step 4: Swap some independent lines
    result = swap_independent_lines(result, seed)

    return result, mappings


def create_obfuscated_suite(
    source_dir: Path,
    output_dir: Path,
    max_contracts: int = 20,
) -> List[Dict]:
    """Create obfuscated versions of vulnerable contracts.

    Args:
        source_dir: Directory with source contracts
        output_dir: Directory for obfuscated outputs
        max_contracts: Maximum number of contracts to process

    Returns:
        List of manifest entries
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Select diverse vulnerable contracts (updated to use existing test contracts)
    vulnerable_contracts = [
        # Reentrancy variants
        "ReentrancyClassic.sol",
        "CrossFunctionReentrancy.sol",
        "ValueMovementReentrancy.sol",
        "Erc777Reentrancy.sol",
        "MEVFlashLoanReentrancy.sol",
        "ReadOnlyReentrancy.sol",
        "AuthReentrancyNoGuard.sol",
        "ReadOnlyOracleReentrancy.sol",
        # Access control
        "ArbitraryDelegatecall.sol",
        "AccessGateWrongVariable.sol",
        "AccessGateStringCompare.sol",
        "AccessGateIfReturn.sol",
        # Arithmetic
        "AmountDivisionNoCheck.sol",
        "AmountPrecision.sol",
        "ArrayUnboundedLoop.sol",
        # Randomness
        "BlockhashWeakRNG.sol",
        "BlockNumberRNG.sol",
        "BlockTimestampManipulation.sol",
        # Other patterns
        "ApprovalRaceCondition.sol",
        "CallbackNoAuth.sol",
    ]

    manifest_entries = []
    processed = 0

    for contract_name in vulnerable_contracts:
        if processed >= max_contracts:
            break

        source_path = source_dir / contract_name
        if not source_path.exists():
            print(f"Skipping {contract_name} (not found)")
            continue

        print(f"Obfuscating {contract_name}...")

        # Read source
        source = source_path.read_text()

        # Obfuscate
        obfuscated, mappings = obfuscate_contract(source, seed=42 + processed)

        # Write obfuscated version
        obf_name = source_path.stem + "_obf.sol"
        obf_path = output_dir / obf_name
        obf_path.write_text(obfuscated)

        # Create manifest entry
        manifest_entries.append({
            "original": str(source_path.relative_to(source_dir.parent.parent)),
            "obfuscated": obf_name,
            "identifier_count": len(mappings),
            "expected_vulnerabilities": get_expected_vulns(contract_name),
        })

        processed += 1
        print(f"  -> {obf_name} ({len(mappings)} identifiers renamed)")

    return manifest_entries


def get_expected_vulns(contract_name: str) -> List[str]:
    """Get expected vulnerability patterns for a contract.

    Args:
        contract_name: Name of the contract file

    Returns:
        List of expected vulnerability pattern IDs
    """
    vuln_map = {
        # Reentrancy variants
        "ReentrancyClassic.sol": ["reentrancy-classic"],
        "CrossFunctionReentrancy.sol": ["reentrancy-cross-function"],
        "ValueMovementReentrancy.sol": ["reentrancy-classic"],
        "Erc777Reentrancy.sol": ["reentrancy-erc777"],
        "MEVFlashLoanReentrancy.sol": ["reentrancy-flash-loan"],
        "ReadOnlyReentrancy.sol": ["reentrancy-read-only"],
        "AuthReentrancyNoGuard.sol": ["reentrancy-classic"],
        "ReadOnlyOracleReentrancy.sol": ["reentrancy-read-only"],
        # Access control
        "ArbitraryDelegatecall.sol": ["arbitrary-delegatecall"],
        "AccessGateWrongVariable.sol": ["weak-access-control"],
        "AccessGateStringCompare.sol": ["weak-access-control"],
        "AccessGateIfReturn.sol": ["weak-access-control"],
        # Arithmetic
        "AmountDivisionNoCheck.sol": ["precision-loss"],
        "AmountPrecision.sol": ["precision-loss"],
        "ArrayUnboundedLoop.sol": ["dos-unbounded-loop"],
        # Randomness
        "BlockhashWeakRNG.sol": ["weak-randomness"],
        "BlockNumberRNG.sol": ["weak-randomness"],
        "BlockTimestampManipulation.sol": ["timestamp-manipulation"],
        # Other patterns
        "ApprovalRaceCondition.sol": ["approval-race"],
        "CallbackNoAuth.sol": ["callback-no-auth"],
    }
    return vuln_map.get(contract_name, [])


def main() -> int:
    """Main entry point."""
    # Default paths
    source_dir = Path("tests/contracts")
    output_dir = Path(".vrs/testing/corpus/obfuscated")

    if not source_dir.exists():
        print(f"ERROR: Source directory not found: {source_dir}")
        return 1

    print("Creating obfuscated contract test suite...")
    print(f"  Source: {source_dir}")
    print(f"  Output: {output_dir}")
    print()

    # Create obfuscated contracts
    manifest_entries = create_obfuscated_suite(
        source_dir=source_dir,
        output_dir=output_dir,
        max_contracts=20,
    )

    print()
    print(f"Created {len(manifest_entries)} obfuscated contracts")

    # Write manifest
    manifest_path = output_dir / "MANIFEST.yaml"
    manifest = {
        "version": "1.0",
        "created_at": "2026-01-29",
        "purpose": "Semantic Stability Score (SSS) validation",
        "contracts": manifest_entries,
    }

    with open(manifest_path, 'w') as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)

    print(f"Manifest written to: {manifest_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
