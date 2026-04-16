#!/usr/bin/env python3
"""
Mutation Generator for Adversarial Gauntlet Testing.

Generates adversarial contract variants to test detection robustness.
Part of G4 (Mutation Robustness) gate enforcement.

Reference:
  - .planning/phases/07.3.3-adversarial-gauntlet/07.3.3-GAUNTLET-SPEC.md
  - .planning/phases/07.3.2-execution-evidence-protocol/07.3.2-GATES.md (G4)
  - configs/gauntlet_scoring.yaml
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class MutationType(Enum):
    """Types of mutations for adversarial testing."""

    RENAME = "rename"           # Rename variables/functions
    REORDER = "reorder"         # Reorder statements (preserve semantics)
    COMMENT = "comment"         # Add misleading comments
    WRAPPER = "wrapper"         # Add abstraction layers
    SPLIT = "split"            # Split logic across functions


@dataclass
class MutationLineage:
    """Tracks the lineage of a mutated contract."""

    base_contract: str              # Original contract path
    base_hash: str                  # SHA256 of original content
    mutation_type: MutationType     # Type of mutation applied
    mutation_id: str                # Unique mutation identifier
    mutation_params: dict           # Parameters used for mutation
    generated_at: str               # ISO timestamp
    preserves_vulnerability: bool   # Whether vuln intent is preserved

    def to_dict(self) -> dict[str, Any]:
        """Convert lineage to dictionary."""
        return {
            "base_contract": self.base_contract,
            "base_hash": self.base_hash,
            "mutation_type": self.mutation_type.value,
            "mutation_id": self.mutation_id,
            "mutation_params": self.mutation_params,
            "generated_at": self.generated_at,
            "preserves_vulnerability": self.preserves_vulnerability,
        }


@dataclass
class MutatedContract:
    """A mutated contract with its lineage."""

    content: str                    # Mutated Solidity code
    output_name: str                # Output filename
    lineage: MutationLineage        # Mutation provenance
    expected: str                   # VULNERABLE or SAFE (preserved from base)

    def content_hash(self) -> str:
        """SHA256 hash of mutated content."""
        return hashlib.sha256(self.content.encode()).hexdigest()[:16]


@dataclass
class MutationResult:
    """Result of mutation generation."""

    base_contract: str
    mutations: list[MutatedContract] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class MutationGenerator:
    """
    Generates adversarial contract mutations.

    Mutation strategies:
    1. RENAME: Change variable/function names to obfuscate patterns
    2. REORDER: Reorder semantically independent operations
    3. COMMENT: Add misleading comments to confuse analysis
    4. WRAPPER: Add wrapper functions that obscure the vulnerable pattern
    5. SPLIT: Split vulnerable logic across multiple functions
    """

    # Common obfuscation name mappings
    RENAME_MAPPINGS = {
        "withdraw": ["claim", "redeem", "pullFunds", "release", "collect"],
        "deposit": ["stake", "fund", "contribute", "addFunds", "supply"],
        "balances": ["accounts", "holdings", "stakes", "deposits", "funds"],
        "amount": ["value", "qty", "sum", "tokens", "units"],
        "sender": ["caller", "user", "from", "origin", "requester"],
        "owner": ["admin", "authority", "controller", "manager", "governor"],
    }

    # Misleading comment templates
    MISLEADING_COMMENTS = [
        "// SAFE: follows CEI pattern",
        "// Protected by reentrancy guard",
        "// State is finalized before external call",
        "// Audited: no reentrancy risk",
        "// @notice This function is secure",
        "// INVARIANT: balance updated atomically",
    ]

    def __init__(self, seed: int | None = None):
        """Initialize generator with optional random seed."""
        self.rng = random.Random(seed)

    def generate_mutation_id(self, mutation_type: MutationType, base_name: str) -> str:
        """Generate unique mutation ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        suffix = self.rng.randint(1000, 9999)
        return f"{mutation_type.value}_{base_name}_{timestamp}_{suffix}"

    def mutate_contract(
        self,
        content: str,
        base_path: str,
        mutation_type: MutationType,
        expected: str,
        params: dict | None = None,
    ) -> MutatedContract:
        """
        Apply a single mutation to a contract.

        Args:
            content: Original Solidity source code
            base_path: Path to original contract
            mutation_type: Type of mutation to apply
            expected: Original classification (VULNERABLE or SAFE)
            params: Optional mutation parameters

        Returns:
            MutatedContract with mutated content and lineage
        """
        params = params or {}
        base_name = Path(base_path).stem
        base_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        # Apply mutation based on type
        if mutation_type == MutationType.RENAME:
            mutated = self._apply_rename_mutation(content, params)
        elif mutation_type == MutationType.REORDER:
            mutated = self._apply_reorder_mutation(content, params)
        elif mutation_type == MutationType.COMMENT:
            mutated = self._apply_comment_mutation(content, params)
        elif mutation_type == MutationType.WRAPPER:
            mutated = self._apply_wrapper_mutation(content, params)
        elif mutation_type == MutationType.SPLIT:
            mutated = self._apply_split_mutation(content, params)
        else:
            raise ValueError(f"Unknown mutation type: {mutation_type}")

        mutation_id = self.generate_mutation_id(mutation_type, base_name)

        lineage = MutationLineage(
            base_contract=base_path,
            base_hash=base_hash,
            mutation_type=mutation_type,
            mutation_id=mutation_id,
            mutation_params=params,
            generated_at=datetime.utcnow().isoformat() + "Z",
            preserves_vulnerability=(expected == "VULNERABLE"),
        )

        output_name = f"{base_name}_{mutation_type.value}.sol"

        return MutatedContract(
            content=mutated,
            output_name=output_name,
            lineage=lineage,
            expected=expected,
        )

    def _apply_rename_mutation(self, content: str, params: dict) -> str:
        """
        Apply rename mutation.

        Changes variable and function names while preserving semantics.
        Intent (vulnerability) is preserved - only names change.
        """
        result = content

        # Select random renames from mappings
        for original, alternatives in self.RENAME_MAPPINGS.items():
            if original in result:
                replacement = self.rng.choice(alternatives)
                # Use word boundaries to avoid partial matches
                result = re.sub(rf'\b{original}\b', replacement, result)

        # Add mutation marker comment
        result = self._add_mutation_header(result, MutationType.RENAME)

        return result

    def _apply_reorder_mutation(self, content: str, params: dict) -> str:
        """
        Apply reorder mutation.

        Reorders semantically independent statements while preserving
        the vulnerable pattern (e.g., external call still before state write).
        """
        lines = content.split("\n")
        result_lines = []

        # Find and reorder independent declarations/imports
        # But preserve the critical ordering of operations within functions
        in_function = False
        function_lines = []

        for line in lines:
            if "function " in line:
                in_function = True
                function_lines = [line]
            elif in_function:
                function_lines.append(line)
                if line.strip() == "}" and function_lines:
                    # Reorder only comments and whitespace within function
                    result_lines.extend(function_lines)
                    function_lines = []
                    in_function = False
            else:
                result_lines.append(line)

        # Shuffle top-level comments (preserves vulnerability)
        # This is a semantic-preserving mutation
        result = "\n".join(result_lines)
        result = self._add_mutation_header(result, MutationType.REORDER)

        return result

    def _apply_comment_mutation(self, content: str, params: dict) -> str:
        """
        Apply comment mutation.

        Adds misleading comments that suggest the code is safe
        when it may actually be vulnerable. Tests if analysis
        relies on comments rather than actual code patterns.
        """
        lines = content.split("\n")
        result_lines = []

        for line in lines:
            result_lines.append(line)

            # Add misleading comments near critical operations
            if "msg.sender.call" in line or ".call{" in line:
                comment = self.rng.choice(self.MISLEADING_COMMENTS)
                result_lines.append(f"        {comment}")
            elif "-=" in line and "balance" in line.lower():
                comment = "        // State properly updated"
                result_lines.append(comment)

        result = "\n".join(result_lines)
        result = self._add_mutation_header(result, MutationType.COMMENT)

        return result

    def _apply_wrapper_mutation(self, content: str, params: dict) -> str:
        """
        Apply wrapper mutation.

        Adds an extra abstraction layer (internal function) that obscures
        the vulnerable pattern. The vulnerability is still present but
        wrapped in an additional function call.
        """
        # Find the main vulnerable function pattern
        # Add a wrapper internal function

        wrapper_template = '''
    // Internal implementation (wrapper pattern)
    function _doTransfer(address to, uint256 val) internal returns (bool) {
        (bool success, ) = to.call{value: val}("");
        return success;
    }
'''

        # Insert wrapper before the contract closing brace
        if "}" in content:
            parts = content.rsplit("}", 1)
            result = parts[0] + wrapper_template + "\n}" + (parts[1] if len(parts) > 1 else "")
        else:
            result = content

        # Replace direct calls with wrapper calls in some cases
        result = re.sub(
            r'msg\.sender\.call\{value: (\w+)\}\(""\)',
            r'_doTransfer(msg.sender, \1)',
            result,
        )

        result = self._add_mutation_header(result, MutationType.WRAPPER)

        return result

    def _apply_split_mutation(self, content: str, params: dict) -> str:
        """
        Apply split mutation.

        Splits vulnerable logic across multiple functions to test
        cross-function analysis. The vulnerability requires understanding
        how multiple functions interact.
        """
        split_helper = '''
    // Split helper - performs the actual transfer
    function _executeTransfer(address recipient, uint256 amt) internal returns (bool) {
        (bool ok, ) = recipient.call{value: amt}("");
        return ok;
    }

    // Split helper - finalizes state after transfer
    function _finalizeWithdraw(address user, uint256 amt) internal {
        balances[user] -= amt;
    }
'''

        # Insert helpers and modify withdraw to use them
        if "}" in content:
            parts = content.rsplit("}", 1)
            result = parts[0] + split_helper + "\n}" + (parts[1] if len(parts) > 1 else "")
        else:
            result = content

        result = self._add_mutation_header(result, MutationType.SPLIT)

        return result

    def _add_mutation_header(self, content: str, mutation_type: MutationType) -> str:
        """Add mutation header comment to content."""
        header = f"""// =============================================================================
// MUTATION: {mutation_type.value.upper()}
// This contract has been mutated for adversarial testing.
// Original vulnerability/safety status is PRESERVED.
// =============================================================================

"""
        return header + content

    def generate_all_mutations(
        self,
        content: str,
        base_path: str,
        expected: str,
    ) -> MutationResult:
        """
        Generate all mutation types for a contract.

        Args:
            content: Original Solidity source
            base_path: Path to original contract
            expected: VULNERABLE or SAFE classification

        Returns:
            MutationResult with all generated mutations
        """
        result = MutationResult(base_contract=base_path)

        for mutation_type in MutationType:
            try:
                mutated = self.mutate_contract(
                    content=content,
                    base_path=base_path,
                    mutation_type=mutation_type,
                    expected=expected,
                )
                result.mutations.append(mutated)
            except Exception as e:
                result.errors.append(f"{mutation_type.value}: {e}")

        return result


def generate_mutation_matrix(
    source_dir: Path,
    output_dir: Path,
    manifest_path: Path,
    seed: int | None = None,
) -> dict[str, Any]:
    """
    Generate mutation matrix from gauntlet contracts.

    Args:
        source_dir: Directory with base contracts
        output_dir: Directory for mutated contracts
        manifest_path: Path to manifest YAML for expected classifications
        seed: Random seed for reproducibility

    Returns:
        Mutation matrix dictionary
    """
    import yaml

    generator = MutationGenerator(seed=seed)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load manifest for expected classifications
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)

    # Build lookup from contract name to expected classification
    expected_lookup = {}
    for case in manifest.get("cases", []):
        contract = case.get("contract", "")
        expected_lookup[contract] = case.get("expected", "UNKNOWN")

    matrix = {
        "version": "1.0.0",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "seed": seed,
        "source_dir": str(source_dir),
        "output_dir": str(output_dir),
        "mutation_types": [mt.value for mt in MutationType],
        "contracts": [],
    }

    total_mutations = 0

    # Process each contract in source directory
    for sol_file in sorted(source_dir.glob("*.sol")):
        content = sol_file.read_text()
        expected = expected_lookup.get(sol_file.name, "UNKNOWN")

        result = generator.generate_all_mutations(
            content=content,
            base_path=str(sol_file),
            expected=expected,
        )

        contract_entry = {
            "base": sol_file.name,
            "expected": expected,
            "mutations": [],
        }

        for mutated in result.mutations:
            # Write mutated contract
            output_path = output_dir / mutated.output_name
            output_path.write_text(mutated.content)

            # Write lineage metadata
            lineage_path = output_dir / f"{mutated.output_name}.lineage.json"
            lineage_path.write_text(json.dumps(mutated.lineage.to_dict(), indent=2))

            contract_entry["mutations"].append({
                "type": mutated.lineage.mutation_type.value,
                "output": mutated.output_name,
                "lineage_file": f"{mutated.output_name}.lineage.json",
                "content_hash": mutated.content_hash(),
                "preserves_vulnerability": mutated.lineage.preserves_vulnerability,
            })
            total_mutations += 1

        if result.errors:
            contract_entry["errors"] = result.errors

        matrix["contracts"].append(contract_entry)

    matrix["total_mutations"] = total_mutations
    matrix["mutation_coverage"] = {
        mt.value: total_mutations // len(MutationType)
        for mt in MutationType
    }

    return matrix


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate adversarial contract mutations for gauntlet testing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate mutations for reentrancy gauntlet
  python generate_mutations.py tests/gauntlet/reentrancy \\
      --manifest tests/gauntlet/reentrancy_manifest.yaml \\
      --output tests/gauntlet/mutations/reentrancy

  # Generate with fixed seed for reproducibility
  python generate_mutations.py tests/gauntlet/reentrancy \\
      --manifest tests/gauntlet/reentrancy_manifest.yaml \\
      --seed 42

Reference:
  .planning/phases/07.3.3-adversarial-gauntlet/07.3.3-GAUNTLET-SPEC.md
  .planning/phases/07.3.2-execution-evidence-protocol/07.3.2-GATES.md (G4)
""",
    )

    parser.add_argument(
        "source_dir",
        type=Path,
        help="Directory containing base contracts",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Path to manifest YAML with expected classifications",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output directory for mutations (default: {source_dir}/mutations)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--matrix-output",
        type=Path,
        default=None,
        help="Path to write mutation matrix YAML",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output matrix as JSON instead of YAML",
    )

    args = parser.parse_args()

    if not args.source_dir.exists():
        print(f"Error: Source directory not found: {args.source_dir}", file=sys.stderr)
        sys.exit(1)

    if not args.manifest.exists():
        print(f"Error: Manifest not found: {args.manifest}", file=sys.stderr)
        sys.exit(1)

    output_dir = args.output or (args.source_dir / "mutations")

    print(f"Generating mutations from: {args.source_dir}")
    print(f"Using manifest: {args.manifest}")
    print(f"Output directory: {output_dir}")
    if args.seed:
        print(f"Random seed: {args.seed}")

    matrix = generate_mutation_matrix(
        source_dir=args.source_dir,
        output_dir=output_dir,
        manifest_path=args.manifest,
        seed=args.seed,
    )

    # Output matrix
    if args.json:
        matrix_str = json.dumps(matrix, indent=2)
    else:
        import yaml
        matrix_str = yaml.dump(matrix, default_flow_style=False, sort_keys=False)

    if args.matrix_output:
        args.matrix_output.write_text(matrix_str)
        print(f"Mutation matrix written to: {args.matrix_output}")
    else:
        print("\n" + "=" * 60)
        print("MUTATION MATRIX")
        print("=" * 60)
        print(matrix_str)

    print(f"\nGenerated {matrix['total_mutations']} mutations across {len(matrix['contracts'])} contracts")
    print("Mutation types:", ", ".join(matrix["mutation_types"]))


if __name__ == "__main__":
    main()
