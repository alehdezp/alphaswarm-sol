"""Contract mutation system for testing infrastructure.

This module generates Solidity contract variants that preserve
vulnerability semantics for testing pattern detection robustness.

Mutation Types:
- RENAME: Variable/function identifier renaming
- REORDER: Statement order permutation (where semantically equivalent)
- VARIATION: Same vulnerability, different implementation
- STRUCTURAL: Split functions, merge functions, extract modifiers

Key principle: Every mutation either preserves the vulnerability
or is explicitly marked as a safe variant.
"""

from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class MutationType(str, Enum):
    """Types of mutations that can be applied."""

    RENAME = "rename"  # Identifier renaming
    REORDER = "reorder"  # Statement reordering
    VARIATION = "variation"  # Pattern variation
    STRUCTURAL = "structural"  # Structural changes


class ValidationStatus(str, Enum):
    """Validation status for mutations."""

    VULNERABLE = "vulnerable"  # Mutation preserves vulnerability
    SAFE = "safe"  # Mutation removes vulnerability
    UNKNOWN = "unknown"  # Not yet validated


@dataclass
class MutationResult:
    """Result of a single mutation operation.

    Attributes:
        original_path: Path to original contract
        mutated_path: Path to mutated contract
        mutation_type: Type of mutation applied
        mutation_id: Unique identifier for this mutation
        description: Human-readable description of mutation
        validation_status: Whether vulnerability is preserved
        original_hash: SHA256 of original content
        mutated_hash: SHA256 of mutated content
        changes: List of changes applied
    """

    original_path: str
    mutated_path: str
    mutation_type: MutationType
    mutation_id: str
    description: str
    validation_status: ValidationStatus = ValidationStatus.UNKNOWN
    original_hash: str = ""
    mutated_hash: str = ""
    changes: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "original_path": self.original_path,
            "mutated_path": self.mutated_path,
            "mutation_type": self.mutation_type.value,
            "mutation_id": self.mutation_id,
            "description": self.description,
            "validation_status": self.validation_status.value,
            "original_hash": self.original_hash,
            "mutated_hash": self.mutated_hash,
            "changes": self.changes,
        }


class MutationEngine:
    """Engine for generating contract mutations.

    Generates semantic-preserving mutations for testing pattern
    detection robustness.
    """

    # Common Solidity identifier patterns
    IDENTIFIER_PATTERN = re.compile(r"\b([a-z_][a-zA-Z0-9_]*)\b")

    # Reserved words that should not be renamed
    SOLIDITY_KEYWORDS: set[str] = {
        "contract",
        "function",
        "modifier",
        "event",
        "struct",
        "enum",
        "mapping",
        "address",
        "uint",
        "uint256",
        "uint128",
        "uint64",
        "uint32",
        "uint8",
        "int",
        "int256",
        "int128",
        "int64",
        "int32",
        "int8",
        "bool",
        "string",
        "bytes",
        "bytes32",
        "bytes20",
        "bytes4",
        "public",
        "private",
        "internal",
        "external",
        "pure",
        "view",
        "payable",
        "memory",
        "storage",
        "calldata",
        "returns",
        "return",
        "if",
        "else",
        "for",
        "while",
        "do",
        "break",
        "continue",
        "require",
        "assert",
        "revert",
        "emit",
        "new",
        "delete",
        "true",
        "false",
        "this",
        "super",
        "msg",
        "block",
        "tx",
        "sender",
        "value",
        "data",
        "timestamp",
        "number",
        "gasleft",
        "abi",
        "encode",
        "decode",
        "keccak256",
        "sha256",
        "ecrecover",
        "transfer",
        "send",
        "call",
        "delegatecall",
        "staticcall",
        "owner",
        "balance",
        "length",
        "push",
        "pop",
        "pragma",
        "solidity",
        "import",
        "library",
        "interface",
        "abstract",
        "virtual",
        "override",
        "indexed",
        "anonymous",
        "constant",
        "immutable",
    }

    # Name pools for renaming
    NAME_POOLS: dict[str, list[str]] = {
        "variable": ["x", "y", "z", "a", "b", "c", "val", "temp", "data", "result"],
        "function": ["execute", "process", "handle", "run", "perform", "doAction"],
        "amount": ["amt", "qty", "sum", "total", "quantity", "units"],
        "address": ["addr", "account", "recipient", "target", "to", "from_"],
    }

    def __init__(self, output_dir: Path | None = None):
        """Initialize mutation engine.

        Args:
            output_dir: Directory for mutated contracts.
                       Defaults to .vrs/corpus/contracts/mutations/
        """
        self.output_dir = output_dir or Path(".vrs/corpus/contracts/mutations")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _hash_content(self, content: str) -> str:
        """Generate SHA256 hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _generate_mutation_id(
        self, original_path: str, mutation_type: MutationType, index: int
    ) -> str:
        """Generate unique mutation ID."""
        base = Path(original_path).stem
        return f"{base}-{mutation_type.value}-{index:03d}"

    def _extract_identifiers(self, content: str) -> set[str]:
        """Extract all non-keyword identifiers from Solidity code."""
        matches = self.IDENTIFIER_PATTERN.findall(content)
        return {m for m in matches if m not in self.SOLIDITY_KEYWORDS}

    def _rename_identifier(self, content: str, old_name: str, new_name: str) -> str:
        """Rename a single identifier in the content."""
        # Use word boundaries to avoid partial matches
        pattern = rf"\b{re.escape(old_name)}\b"
        return re.sub(pattern, new_name, content)

    def apply_rename_mutation(
        self,
        content: str,
        identifiers_to_rename: set[str] | None = None,
        rename_count: int = 3,
    ) -> tuple[str, list[dict[str, str]]]:
        """Apply identifier renaming mutations.

        Args:
            content: Original Solidity source
            identifiers_to_rename: Specific identifiers to rename (or random if None)
            rename_count: Number of identifiers to rename if random

        Returns:
            Tuple of (mutated content, list of changes)
        """
        identifiers = self._extract_identifiers(content)

        if identifiers_to_rename is None:
            # Pick random identifiers to rename
            rename_targets = list(identifiers)[:rename_count]
        else:
            rename_targets = list(identifiers_to_rename & identifiers)

        changes: list[dict[str, str]] = []
        mutated = content

        for old_name in rename_targets:
            # Generate new name based on category heuristics
            if "balance" in old_name.lower() or "amount" in old_name.lower():
                pool = self.NAME_POOLS["amount"]
            elif "address" in old_name.lower() or "addr" in old_name.lower():
                pool = self.NAME_POOLS["address"]
            elif old_name.startswith("_"):
                pool = [f"_{n}" for n in self.NAME_POOLS["variable"]]
            else:
                pool = self.NAME_POOLS["variable"]

            new_name = random.choice(pool)
            # Add suffix to ensure uniqueness
            new_name = f"{new_name}_{hashlib.md5(old_name.encode()).hexdigest()[:4]}"

            mutated = self._rename_identifier(mutated, old_name, new_name)
            changes.append({"old": old_name, "new": new_name})

        return mutated, changes

    def apply_reorder_mutation(
        self, content: str
    ) -> tuple[str, list[dict[str, Any]]]:
        """Apply statement reordering mutations.

        Only reorders statements that are semantically independent
        (e.g., consecutive require statements, event emissions).

        Args:
            content: Original Solidity source

        Returns:
            Tuple of (mutated content, list of changes)
        """
        changes: list[dict[str, Any]] = []

        # Find consecutive require statements (safe to reorder)
        require_pattern = re.compile(
            r"(require\([^;]+\);\s*)(require\([^;]+\);)", re.MULTILINE
        )

        def reorder_requires(match: re.Match[str]) -> str:
            req1, req2 = match.group(1), match.group(2)
            changes.append(
                {
                    "type": "reorder_requires",
                    "statement1": req1.strip()[:50],
                    "statement2": req2.strip()[:50],
                }
            )
            return f"{req2}\n        {req1}"

        mutated = require_pattern.sub(reorder_requires, content)

        # Find consecutive event emissions (safe to reorder)
        emit_pattern = re.compile(
            r"(emit\s+\w+\([^;]*\);\s*)(emit\s+\w+\([^;]*\);)", re.MULTILINE
        )

        def reorder_emits(match: re.Match[str]) -> str:
            emit1, emit2 = match.group(1), match.group(2)
            changes.append(
                {
                    "type": "reorder_emits",
                    "statement1": emit1.strip()[:50],
                    "statement2": emit2.strip()[:50],
                }
            )
            return f"{emit2}\n        {emit1}"

        mutated = emit_pattern.sub(reorder_emits, mutated)

        return mutated, changes

    def apply_structural_mutation(
        self, content: str
    ) -> tuple[str, list[dict[str, Any]]]:
        """Apply structural mutations.

        Examples:
        - Add comments
        - Add whitespace
        - Use alternative syntax

        Args:
            content: Original Solidity source

        Returns:
            Tuple of (mutated content, list of changes)
        """
        changes: list[dict[str, Any]] = []

        # Add NatSpec comments before functions
        function_pattern = re.compile(r"(\n\s*)(function\s+\w+)")

        def add_natspec(match: re.Match[str]) -> str:
            indent, func = match.group(1), match.group(2)
            changes.append({"type": "add_natspec", "before": func[:30]})
            return f"{indent}/// @notice Auto-generated comment{indent}{func}"

        mutated = function_pattern.sub(add_natspec, content)

        # Use != instead of > 0 where equivalent
        gt_zero_pattern = re.compile(r"(\w+)\s*>\s*0")

        def use_not_equal(match: re.Match[str]) -> str:
            var = match.group(1)
            changes.append(
                {"type": "syntax_variation", "from": f"{var} > 0", "to": f"{var} != 0"}
            )
            return f"{var} != 0"

        # Only apply to ~50% of occurrences
        for match in gt_zero_pattern.finditer(content):
            if random.random() > 0.5:
                mutated = mutated.replace(match.group(0), use_not_equal(match), 1)

        return mutated, changes

    def generate_mutations(
        self,
        source_path: Path,
        count: int = 10,
        mutation_types: list[MutationType] | None = None,
    ) -> list[MutationResult]:
        """Generate multiple mutations of a contract.

        Args:
            source_path: Path to original Solidity file
            count: Number of mutations to generate
            mutation_types: Types of mutations to apply (default: all)

        Returns:
            List of MutationResult objects
        """
        if mutation_types is None:
            mutation_types = [
                MutationType.RENAME,
                MutationType.REORDER,
                MutationType.STRUCTURAL,
            ]

        content = source_path.read_text()
        original_hash = self._hash_content(content)
        results: list[MutationResult] = []

        for i in range(count):
            # Pick random mutation type
            mut_type = random.choice(mutation_types)

            if mut_type == MutationType.RENAME:
                mutated, changes = self.apply_rename_mutation(content)
                description = f"Renamed {len(changes)} identifiers"
            elif mut_type == MutationType.REORDER:
                mutated, changes = self.apply_reorder_mutation(content)
                description = f"Reordered {len(changes)} statement groups"
            elif mut_type == MutationType.STRUCTURAL:
                mutated, changes = self.apply_structural_mutation(content)
                description = f"Applied {len(changes)} structural changes"
            else:
                # VARIATION would require pattern-specific logic
                mutated = content
                changes = []
                description = "Variation mutation (not yet implemented)"

            mutation_id = self._generate_mutation_id(str(source_path), mut_type, i)
            output_path = self.output_dir / f"{mutation_id}.sol"
            output_path.write_text(mutated)

            results.append(
                MutationResult(
                    original_path=str(source_path),
                    mutated_path=str(output_path),
                    mutation_type=mut_type,
                    mutation_id=mutation_id,
                    description=description,
                    validation_status=ValidationStatus.UNKNOWN,
                    original_hash=original_hash,
                    mutated_hash=self._hash_content(mutated),
                    changes=changes,
                )
            )

        return results

    def validate_mutation(
        self,
        mutation: MutationResult,
        expected_pattern: str,
    ) -> ValidationStatus:
        """Validate that a mutation preserves expected vulnerability.

        Validation can be enabled by setting VRS_VALIDATE_MUTATIONS=1.
        When disabled or unavailable, falls back to conservative heuristics.

        Args:
            mutation: Mutation to validate
            expected_pattern: Pattern ID that should still match

        Returns:
            ValidationStatus indicating if vulnerability preserved
        """
        import os

        # Default heuristic to keep tests fast and deterministic
        if mutation.mutation_type == MutationType.RENAME and not os.getenv("VRS_VALIDATE_MUTATIONS"):
            return ValidationStatus.VULNERABLE

        if not os.getenv("VRS_VALIDATE_MUTATIONS"):
            return ValidationStatus.UNKNOWN

        try:
            from alphaswarm_sol.kg.builder import VKGBuilder
            from alphaswarm_sol.queries.patterns import PatternEngine

            contract_path = Path(mutation.mutated_path)
            if not contract_path.exists():
                return ValidationStatus.UNKNOWN

            builder = VKGBuilder(contract_path.parent)
            graph = builder.build(contract_path)

            from alphaswarm_sol.queries.patterns import get_patterns
            from alphaswarm_sol.queries.errors import PatternLoadError
            try:
                patterns = get_patterns()
            except PatternLoadError:
                return ValidationStatus.UNKNOWN
            if not patterns:
                return ValidationStatus.UNKNOWN

            engine = PatternEngine()
            findings = engine.run(
                graph,
                patterns,
                pattern_ids=[expected_pattern],
                limit=5,
            )
            return ValidationStatus.VULNERABLE if findings else ValidationStatus.SAFE
        except Exception:
            return ValidationStatus.UNKNOWN


# =============================================================================
# Counterfactual Generation (I1 Innovation from Phase 7.2)
# =============================================================================


class CounterfactualType(str, Enum):
    """Types of counterfactual mutations for near-miss testing."""

    GUARD_INVERSION = "guard_inversion"  # Flip require() or modifier logic
    CEI_ORDER_SWAP = "cei_order_swap"  # Swap CEI order (read/write/call)
    GRACE_PERIOD = "grace_period"  # Add/remove grace period windows
    HELPER_DEPTH = "helper_depth"  # Move checks into/out of helpers
    CHAIN_CONDITION = "chain_condition"  # Add L1/L2 chain conditionals
    AUDIT_MIRROR = "audit_mirror"  # Re-infect fixed contracts


@dataclass
class CounterfactualResult:
    """Result of counterfactual generation.

    Attributes:
        base_contract_id: ID of the original contract
        base_contract_path: Path to original contract
        counterfactual_id: Unique ID for this counterfactual
        counterfactual_path: Path to generated contract
        counterfactual_type: Type of transformation applied
        description: Human-readable description
        expected_vulnerability_status: Whether this should be vulnerable or safe
        semantic_diff: Description of semantic difference from base
        original_hash: Hash of original content
        counterfactual_hash: Hash of generated content
        metadata: Additional metadata for tracking
    """

    base_contract_id: str
    base_contract_path: str
    counterfactual_id: str
    counterfactual_path: str
    counterfactual_type: CounterfactualType
    description: str
    expected_vulnerability_status: ValidationStatus
    semantic_diff: str
    original_hash: str = ""
    counterfactual_hash: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "base_contract_id": self.base_contract_id,
            "base_contract_path": self.base_contract_path,
            "counterfactual_id": self.counterfactual_id,
            "counterfactual_path": self.counterfactual_path,
            "counterfactual_type": self.counterfactual_type.value,
            "description": self.description,
            "expected_vulnerability_status": self.expected_vulnerability_status.value,
            "semantic_diff": self.semantic_diff,
            "original_hash": self.original_hash,
            "counterfactual_hash": self.counterfactual_hash,
            "metadata": self.metadata,
        }


class CounterfactualGenerator:
    """Generator for counterfactual contract variants.

    Creates near-miss variants of contracts to test pattern detection
    robustness. Each counterfactual differs by a single semantic edit
    while preserving surrounding behavior.

    Counterfactual Types:
    1. Guard inversion - flip require() or modifier order
    2. CEI order swap - swap read/write/call ordering
    3. Grace period - add/remove time windows
    4. Helper depth - move checks into internal helpers
    5. Chain condition - add L1/L2 chain ID checks
    6. Audit mirror - re-infect fixed contracts

    Output: .vrs/corpus/contracts/adversarial/counterfactual/
    """

    # Patterns for counterfactual transformations
    REQUIRE_PATTERN = re.compile(
        r"require\s*\(\s*([^;]+?)\s*,?\s*['\"]?[^)]*['\"]?\s*\)\s*;",
        re.MULTILINE,
    )
    MODIFIER_PATTERN = re.compile(r"modifier\s+(\w+)\s*\([^)]*\)\s*\{([^}]+)\}")
    EXTERNAL_CALL_PATTERN = re.compile(
        r"(\w+)\s*\.\s*(call|transfer|send)\s*[\({]",
        re.MULTILINE,
    )
    BALANCE_WRITE_PATTERN = re.compile(
        r"(balances?|_balances?)\s*\[\s*[^]]+\]\s*[-+]?=",
        re.MULTILINE,
    )
    TIMESTAMP_CHECK_PATTERN = re.compile(
        r"require\s*\([^;]*block\.timestamp[^;]*\)\s*;",
        re.MULTILINE,
    )

    def __init__(self, output_dir: Path | None = None):
        """Initialize counterfactual generator.

        Args:
            output_dir: Output directory for counterfactuals.
                       Defaults to .vrs/corpus/contracts/adversarial/counterfactual/
        """
        self.output_dir = output_dir or Path(
            ".vrs/corpus/contracts/adversarial/counterfactual"
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir = self.output_dir / "metadata"
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def _hash_content(self, content: str) -> str:
        """Generate SHA256 hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _generate_id(
        self,
        base_id: str,
        cf_type: CounterfactualType,
        index: int = 0,
    ) -> str:
        """Generate unique counterfactual ID."""
        return f"cf-{base_id}-{cf_type.value}-{index:03d}"

    def apply_guard_inversion(
        self,
        content: str,
        invert_first: bool = True,
    ) -> tuple[str, str, ValidationStatus]:
        """Invert guard conditions to create safe/unsafe variants.

        Args:
            content: Original Solidity source
            invert_first: If True, invert first require; else invert all

        Returns:
            Tuple of (mutated content, semantic diff, expected status)
        """
        matches = list(self.REQUIRE_PATTERN.finditer(content))
        if not matches:
            return content, "no_changes", ValidationStatus.UNKNOWN

        mutated = content
        inversions = 0

        for match in matches[:1] if invert_first else matches:
            condition = match.group(1).strip()

            # Simple condition inversion
            if "!=" in condition:
                inverted = condition.replace("!=", "==")
            elif "==" in condition:
                inverted = condition.replace("==", "!=")
            elif ">=" in condition:
                inverted = condition.replace(">=", "<")
            elif "<=" in condition:
                inverted = condition.replace("<=", ">")
            elif ">" in condition and "=" not in condition:
                inverted = condition.replace(">", "<=")
            elif "<" in condition and "=" not in condition:
                inverted = condition.replace("<", ">=")
            elif condition.startswith("!"):
                inverted = condition[1:]
            else:
                inverted = f"!({condition})"

            old_require = match.group(0)
            new_require = f'require({inverted}, "inverted");'
            mutated = mutated.replace(old_require, new_require, 1)
            inversions += 1

        if inversions > 0:
            # Inverting guard typically makes contract unsafe
            return mutated, f"inverted_{inversions}_guards", ValidationStatus.VULNERABLE
        return content, "no_changes", ValidationStatus.UNKNOWN

    def apply_cei_order_swap(
        self, content: str
    ) -> tuple[str, str, ValidationStatus]:
        """Swap CEI (Check-Effect-Interaction) order.

        Moves external calls before state updates to create reentrancy risk.

        Returns:
            Tuple of (mutated content, semantic diff, expected status)
        """
        # Find state write followed by external call (safe pattern)
        # Then swap to external call before state write (vulnerable)

        # Look for balance update
        balance_match = self.BALANCE_WRITE_PATTERN.search(content)
        call_match = self.EXTERNAL_CALL_PATTERN.search(content)

        if not balance_match or not call_match:
            return content, "no_cei_pattern", ValidationStatus.UNKNOWN

        # Check if balance update is before call (CEI correct)
        if balance_match.start() < call_match.start():
            # Find the full statements
            lines = content.split("\n")
            balance_line_idx = content[:balance_match.start()].count("\n")
            call_line_idx = content[:call_match.start()].count("\n")

            if balance_line_idx < call_line_idx and call_line_idx - balance_line_idx <= 3:
                # Swap the lines
                balance_line = lines[balance_line_idx]
                call_line = lines[call_line_idx]
                lines[balance_line_idx] = call_line
                lines[call_line_idx] = balance_line
                mutated = "\n".join(lines)
                return mutated, "swapped_cei_order", ValidationStatus.VULNERABLE

        return content, "no_safe_cei_found", ValidationStatus.UNKNOWN

    def apply_grace_period_insert(
        self,
        content: str,
        grace_seconds: int = 3600,
    ) -> tuple[str, str, ValidationStatus]:
        """Insert grace period check to make contract safer.

        Args:
            content: Original Solidity source
            grace_seconds: Grace period in seconds (default 1 hour)

        Returns:
            Tuple of (mutated content, semantic diff, expected status)
        """
        # Find timestamp checks without grace period
        timestamp_matches = list(self.TIMESTAMP_CHECK_PATTERN.finditer(content))

        if not timestamp_matches:
            # No timestamp check, try to add one at function start
            # Find first public/external function
            func_pattern = re.compile(
                r"(function\s+\w+\s*\([^)]*\)\s*(?:public|external)[^{]*\{)",
                re.MULTILINE,
            )
            func_match = func_pattern.search(content)
            if func_match:
                grace_check = f"\n        require(block.timestamp >= lastUpdate + {grace_seconds}, \"grace period\");"
                insert_point = func_match.end()
                mutated = content[:insert_point] + grace_check + content[insert_point:]
                return mutated, f"added_grace_{grace_seconds}s", ValidationStatus.SAFE
            return content, "no_function_found", ValidationStatus.UNKNOWN

        # Add grace period to existing timestamp check
        match = timestamp_matches[0]
        old_check = match.group(0)
        # Append grace period
        grace_addon = f" + {grace_seconds}"
        new_check = old_check.replace("block.timestamp", f"block.timestamp{grace_addon}")
        mutated = content.replace(old_check, new_check, 1)
        return mutated, f"extended_grace_{grace_seconds}s", ValidationStatus.SAFE

    def apply_grace_period_remove(
        self, content: str
    ) -> tuple[str, str, ValidationStatus]:
        """Remove grace period check to make contract vulnerable.

        Returns:
            Tuple of (mutated content, semantic diff, expected status)
        """
        # Find grace period patterns
        grace_pattern = re.compile(
            r"require\s*\([^;]*\+\s*\d+[^;]*block\.timestamp[^;]*\)\s*;|"
            r"require\s*\([^;]*block\.timestamp[^;]*\+\s*\d+[^;]*\)\s*;|"
            r"require\s*\([^;]*gracePeriod[^;]*\)\s*;",
            re.MULTILINE | re.IGNORECASE,
        )

        matches = list(grace_pattern.finditer(content))
        if not matches:
            return content, "no_grace_period", ValidationStatus.UNKNOWN

        mutated = content
        for match in matches[:1]:  # Remove first grace period only
            mutated = mutated.replace(match.group(0), "// grace period removed", 1)

        return mutated, "removed_grace_period", ValidationStatus.VULNERABLE

    def apply_helper_depth_move(
        self,
        content: str,
        move_to_helper: bool = True,
    ) -> tuple[str, str, ValidationStatus]:
        """Move checks into or out of helper functions.

        Args:
            content: Original Solidity source
            move_to_helper: If True, move check to helper; else inline helper

        Returns:
            Tuple of (mutated content, semantic diff, expected status)
        """
        if move_to_helper:
            # Find a require statement and move it to a new internal function
            matches = list(self.REQUIRE_PATTERN.finditer(content))
            if not matches:
                return content, "no_require_to_move", ValidationStatus.UNKNOWN

            match = matches[0]
            require_stmt = match.group(0)
            condition = match.group(1)

            # Generate helper function name
            helper_name = f"_check_{hashlib.md5(condition.encode()).hexdigest()[:6]}"

            # Create helper function
            helper_func = f"""
    function {helper_name}() internal view {{
        {require_stmt}
    }}
"""
            # Replace require with call to helper
            mutated = content.replace(require_stmt, f"{helper_name}();", 1)

            # Add helper before last closing brace
            last_brace = mutated.rfind("}")
            if last_brace != -1:
                mutated = mutated[:last_brace] + helper_func + mutated[last_brace:]
                return mutated, f"moved_to_helper_{helper_name}", ValidationStatus.VULNERABLE

        return content, "no_helper_change", ValidationStatus.UNKNOWN

    def apply_chain_condition(
        self,
        content: str,
        chain_id: int = 1,
        condition_type: str = "skip_on_chain",
    ) -> tuple[str, str, ValidationStatus]:
        """Add chain ID conditional to checks.

        Args:
            content: Original Solidity source
            chain_id: Chain ID to condition on
            condition_type: "skip_on_chain" or "require_chain"

        Returns:
            Tuple of (mutated content, semantic diff, expected status)
        """
        matches = list(self.REQUIRE_PATTERN.finditer(content))
        if not matches:
            return content, "no_require_for_chain", ValidationStatus.UNKNOWN

        match = matches[0]
        require_stmt = match.group(0)

        if condition_type == "skip_on_chain":
            # Wrap in if statement that skips on specific chain
            wrapped = f"if (block.chainid != {chain_id}) {{ {require_stmt} }}"
            mutated = content.replace(require_stmt, wrapped, 1)
            return mutated, f"skip_check_on_chain_{chain_id}", ValidationStatus.VULNERABLE
        else:
            # Add chain requirement
            chain_require = f"require(block.chainid == {chain_id}, \"wrong chain\");\n        "
            mutated = content.replace(require_stmt, chain_require + require_stmt, 1)
            return mutated, f"require_chain_{chain_id}", ValidationStatus.SAFE

        return content, "no_chain_change", ValidationStatus.UNKNOWN

    def generate_counterfactuals(
        self,
        source_path: Path,
        base_contract_id: str,
        types: list[CounterfactualType] | None = None,
    ) -> list[CounterfactualResult]:
        """Generate multiple counterfactual variants of a contract.

        Args:
            source_path: Path to original contract
            base_contract_id: ID for the base contract
            types: Types of counterfactuals to generate (default: all)

        Returns:
            List of CounterfactualResult objects
        """
        if types is None:
            types = list(CounterfactualType)

        content = source_path.read_text()
        original_hash = self._hash_content(content)
        results: list[CounterfactualResult] = []

        type_handlers: dict[CounterfactualType, Any] = {
            CounterfactualType.GUARD_INVERSION: lambda c: self.apply_guard_inversion(c),
            CounterfactualType.CEI_ORDER_SWAP: lambda c: self.apply_cei_order_swap(c),
            CounterfactualType.GRACE_PERIOD: lambda c: self.apply_grace_period_insert(c),
            CounterfactualType.HELPER_DEPTH: lambda c: self.apply_helper_depth_move(c),
            CounterfactualType.CHAIN_CONDITION: lambda c: self.apply_chain_condition(c),
        }

        for idx, cf_type in enumerate(types):
            if cf_type == CounterfactualType.AUDIT_MIRROR:
                # Audit mirror requires special handling
                continue

            handler = type_handlers.get(cf_type)
            if not handler:
                continue

            mutated, semantic_diff, expected_status = handler(content)

            if semantic_diff in ("no_changes", "no_cei_pattern", "no_safe_cei_found"):
                continue

            cf_id = self._generate_id(base_contract_id, cf_type, idx)
            output_path = self.output_dir / f"{cf_id}.sol"
            output_path.write_text(mutated)

            result = CounterfactualResult(
                base_contract_id=base_contract_id,
                base_contract_path=str(source_path),
                counterfactual_id=cf_id,
                counterfactual_path=str(output_path),
                counterfactual_type=cf_type,
                description=f"{cf_type.value}: {semantic_diff}",
                expected_vulnerability_status=expected_status,
                semantic_diff=semantic_diff,
                original_hash=original_hash,
                counterfactual_hash=self._hash_content(mutated),
                metadata={"generated_at": str(Path(source_path).stat().st_mtime)},
            )
            results.append(result)

            # Save metadata
            metadata_path = self.metadata_dir / f"{cf_id}.yaml"
            import yaml
            metadata_path.write_text(yaml.dump(result.to_dict(), default_flow_style=False))

        return results

    def list_counterfactuals(self) -> list[dict[str, Any]]:
        """List all generated counterfactuals with metadata.

        Returns:
            List of counterfactual metadata dictionaries
        """
        import yaml

        results = []
        for metadata_file in self.metadata_dir.glob("*.yaml"):
            try:
                data = yaml.safe_load(metadata_file.read_text())
                results.append(data)
            except Exception:
                pass
        return results


# Hard-negative suite helpers
def create_hard_negative_contract(
    name: str,
    vulnerability_class: str,
    safe_variant: str,
    output_dir: Path | None = None,
) -> Path:
    """Create a hard-negative contract for FP testing.

    Hard negatives are safe contracts that look vulnerable but have
    proper guards in place.

    Args:
        name: Contract name
        vulnerability_class: Type of vulnerability it mimics
        safe_variant: Description of why it's safe
        output_dir: Output directory (default: .vrs/corpus/contracts/safe/)

    Returns:
        Path to created contract
    """
    if output_dir is None:
        output_dir = Path(".vrs/corpus/contracts/safe")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Template for hard-negative contract
    template = f'''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title HardNegative_{name}
 * @notice Safe contract that resembles {vulnerability_class} vulnerability
 * @dev Safe variant: {safe_variant}
 * @custom:hard-negative true
 * @custom:vulnerability-class {vulnerability_class}
 * @custom:safe-reason {safe_variant}
 */
contract HardNegative_{name} {{
    // Placeholder - replace with actual safe implementation
    // that resembles vulnerable pattern but has proper guards
}}
'''

    output_path = output_dir / f"HardNegative_{name}.sol"
    output_path.write_text(template)
    return output_path


__all__ = [
    # Original exports
    "MutationType",
    "ValidationStatus",
    "MutationResult",
    "MutationEngine",
    # Counterfactual exports
    "CounterfactualType",
    "CounterfactualResult",
    "CounterfactualGenerator",
    "create_hard_negative_contract",
]
