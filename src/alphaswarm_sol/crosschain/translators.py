"""
Chain-Specific Translators

Convert between chain-specific operations and abstract Universal Vulnerability Ontology.
Each translator handles a specific blockchain platform.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set, Type
import re
import logging

from alphaswarm_sol.crosschain.ontology import (
    Chain,
    AbstractOperation,
    OperationType,
    AbstractVulnerabilitySignature,
)

logger = logging.getLogger(__name__)


class ChainTranslator(ABC):
    """
    Base class for chain-specific translators.

    Translates between platform-specific operations and abstract UVO operations.
    """

    chain: Chain

    @abstractmethod
    def to_abstract(self, operations: List[Any]) -> List[AbstractOperation]:
        """
        Convert chain-specific operations to abstract operations.

        Args:
            operations: Chain-specific operation list (e.g., VKG operations for EVM)

        Returns:
            List of AbstractOperation
        """
        pass

    @abstractmethod
    def from_abstract(
        self,
        abstract_ops: List[AbstractOperation]
    ) -> Dict[str, Any]:
        """
        Convert abstract operations to chain-specific pattern.

        Args:
            abstract_ops: List of abstract operations

        Returns:
            Chain-specific pattern definition (e.g., YAML pattern for VKG)
        """
        pass

    @abstractmethod
    def parse_source(self, source: str) -> List[Any]:
        """
        Parse source code to extract chain-specific operations.

        Args:
            source: Source code in the chain's language

        Returns:
            List of chain-specific operations
        """
        pass


class EVMTranslator(ChainTranslator):
    """
    Translator for EVM-based chains (Solidity).

    Converts VKG semantic operations to/from abstract UVO operations.
    """

    chain = Chain.EVM

    # Mapping from VKG operations to abstract operations
    VKG_TO_ABSTRACT = {
        "TRANSFERS_VALUE_OUT": (OperationType.TRANSFER_VALUE, "external"),
        "READS_USER_BALANCE": (OperationType.READ_VALUE, "balance"),
        "WRITES_USER_BALANCE": (OperationType.WRITE_VALUE, "balance"),
        "READS_ORACLE": (OperationType.READ_EXTERNAL, "oracle_price"),
        "CALLS_EXTERNAL": (OperationType.CALL_EXTERNAL, "external"),
        "CALLS_UNTRUSTED": (OperationType.CALL_UNTRUSTED, "untrusted"),
        "CHECKS_PERMISSION": (OperationType.CHECK_PERMISSION, "access"),
        "MODIFIES_OWNER": (OperationType.MODIFY_OWNER, "owner"),
        "MODIFIES_ROLES": (OperationType.MODIFY_PERMISSION, "roles"),
        "MODIFIES_CRITICAL_STATE": (OperationType.WRITE_STATE, "critical"),
        "READS_EXTERNAL_VALUE": (OperationType.READ_EXTERNAL, "value"),
    }

    # Reverse mapping
    ABSTRACT_TO_VKG = {v[0]: k for k, v in VKG_TO_ABSTRACT.items()}

    def to_abstract(self, operations: List[str]) -> List[AbstractOperation]:
        """Convert VKG operations to abstract operations."""
        abstract_ops = []

        for i, op in enumerate(operations):
            if op in self.VKG_TO_ABSTRACT:
                op_type, target = self.VKG_TO_ABSTRACT[op]
                abstract_ops.append(AbstractOperation(
                    operation=op_type,
                    target=target,
                    timing=i,
                ))
            else:
                # Try to infer from operation name
                inferred = self._infer_operation(op)
                if inferred:
                    abstract_ops.append(AbstractOperation(
                        operation=inferred[0],
                        target=inferred[1],
                        timing=i,
                    ))

        return abstract_ops

    def from_abstract(
        self,
        abstract_ops: List[AbstractOperation]
    ) -> Dict[str, Any]:
        """Convert abstract operations to VKG YAML pattern."""
        conditions = []

        for op in abstract_ops:
            # Map to VKG operation
            vkg_op = self.ABSTRACT_TO_VKG.get(op.operation)
            if vkg_op:
                conditions.append({
                    "has_operation": vkg_op
                })

        # Infer ordering constraints
        transfer_ops = [op for op in abstract_ops if op.operation == OperationType.TRANSFER_VALUE]
        write_ops = [op for op in abstract_ops if op.operation == OperationType.WRITE_VALUE]

        if transfer_ops and write_ops:
            # Check if transfer before write (CEI violation)
            if transfer_ops[0].timing < write_ops[0].timing:
                conditions.append({
                    "sequence_order": {
                        "before": "TRANSFERS_VALUE_OUT",
                        "after": "WRITES_USER_BALANCE"
                    }
                })

        return {
            "tier_a": {
                "all": conditions
            }
        }

    def parse_source(self, source: str) -> List[str]:
        """
        Parse Solidity source to extract operations.

        This is a simplified extraction - full analysis uses Slither via VKG builder.
        """
        operations = []

        # Simple pattern matching for common operations
        patterns = {
            r'\.call\s*\{': "CALLS_EXTERNAL",
            r'\.transfer\s*\(': "TRANSFERS_VALUE_OUT",
            r'\.send\s*\(': "TRANSFERS_VALUE_OUT",
            r'balances?\[': "READS_USER_BALANCE",
            r'msg\.sender': "CHECKS_PERMISSION",
            r'onlyOwner': "CHECKS_PERMISSION",
            r'owner\s*=': "MODIFIES_OWNER",
            r'latestRoundData': "READS_ORACLE",
        }

        for pattern, op in patterns.items():
            if re.search(pattern, source):
                if op not in operations:
                    operations.append(op)

        # Infer write operations after read
        if "READS_USER_BALANCE" in operations:
            if re.search(r'balances?\[.*\]\s*[-+]?=', source):
                operations.append("WRITES_USER_BALANCE")

        return operations

    def _infer_operation(self, op_name: str) -> Optional[tuple]:
        """Infer abstract operation from VKG operation name."""
        op_lower = op_name.lower()

        if "transfer" in op_lower and "value" in op_lower:
            return (OperationType.TRANSFER_VALUE, "value")
        if "read" in op_lower and "balance" in op_lower:
            return (OperationType.READ_VALUE, "balance")
        if "write" in op_lower and "balance" in op_lower:
            return (OperationType.WRITE_VALUE, "balance")
        if "oracle" in op_lower:
            return (OperationType.READ_EXTERNAL, "oracle")
        if "owner" in op_lower:
            return (OperationType.MODIFY_OWNER, "owner")

        return None


class SolanaTranslator(ChainTranslator):
    """
    Translator for Solana (Anchor framework).

    Handles Solana-specific patterns like CPIs, account validation, etc.
    """

    chain = Chain.SOLANA

    # Solana/Anchor patterns to abstract operations
    SOLANA_PATTERNS = {
        "invoke": (OperationType.CALL_EXTERNAL, "cpi"),
        "invoke_signed": (OperationType.CALL_EXTERNAL, "cpi_signed"),
        "transfer": (OperationType.TRANSFER_VALUE, "lamports"),
        "lamports": (OperationType.READ_VALUE, "lamports"),
        "account.data": (OperationType.READ_STATE, "account_data"),
        "set_lamports": (OperationType.WRITE_VALUE, "lamports"),
        "authority": (OperationType.CHECK_PERMISSION, "authority"),
        "signer": (OperationType.CHECK_PERMISSION, "signer"),
        "owner": (OperationType.CHECK_OWNER, "program_owner"),
    }

    def to_abstract(self, operations: List[str]) -> List[AbstractOperation]:
        """Convert Solana/Anchor operations to abstract operations."""
        abstract_ops = []

        for i, op in enumerate(operations):
            op_lower = op.lower()

            for pattern, (op_type, target) in self.SOLANA_PATTERNS.items():
                if pattern in op_lower:
                    abstract_ops.append(AbstractOperation(
                        operation=op_type,
                        target=target,
                        timing=i,
                    ))
                    break

        return abstract_ops

    def from_abstract(
        self,
        abstract_ops: List[AbstractOperation]
    ) -> Dict[str, Any]:
        """Convert abstract operations to Solana-specific checks."""
        checks = []

        for op in abstract_ops:
            if op.operation == OperationType.TRANSFER_VALUE:
                checks.append({
                    "type": "cpi_check",
                    "operation": "transfer",
                    "requires_signer": True
                })
            elif op.operation == OperationType.CALL_EXTERNAL:
                checks.append({
                    "type": "cpi_check",
                    "operation": "invoke",
                    "check_program_id": True
                })
            elif op.operation == OperationType.CHECK_PERMISSION:
                checks.append({
                    "type": "account_validation",
                    "check_signer": True
                })
            elif op.operation == OperationType.WRITE_VALUE:
                checks.append({
                    "type": "state_mutation",
                    "target": op.target
                })

        return {
            "chain": "solana",
            "checks": checks
        }

    def parse_source(self, source: str) -> List[str]:
        """Parse Rust/Anchor source code for operations."""
        operations = []

        patterns = [
            (r'invoke\s*\(', "invoke"),
            (r'invoke_signed\s*\(', "invoke_signed"),
            (r'transfer\s*\(', "transfer"),
            (r'\.lamports\s*\(', "lamports"),
            (r'ctx\.accounts\.\w+\.data', "account.data"),
            (r'set_lamports\s*\(', "set_lamports"),
            (r'#\[account\(.*signer.*\)\]', "signer"),
            (r'ctx\.accounts\.authority', "authority"),
        ]

        for pattern, op_name in patterns:
            if re.search(pattern, source, re.IGNORECASE):
                if op_name not in operations:
                    operations.append(op_name)

        return operations


class MoveTranslator(ChainTranslator):
    """
    Translator for Move language (Aptos, Sui).

    Handles Move's ownership and borrow semantics.
    """

    chain = Chain.MOVE

    MOVE_PATTERNS = {
        "borrow_global": (OperationType.READ_STATE, "global_resource"),
        "borrow_global_mut": (OperationType.WRITE_STATE, "global_resource"),
        "move_to": (OperationType.WRITE_STATE, "resource"),
        "move_from": (OperationType.READ_STATE, "resource"),
        "Coin::transfer": (OperationType.TRANSFER_VALUE, "coin"),
        "Coin::value": (OperationType.READ_VALUE, "coin_value"),
        "Coin::burn": (OperationType.BURN_VALUE, "coin"),
        "Coin::mint": (OperationType.MINT_VALUE, "coin"),
        "signer::address_of": (OperationType.CHECK_PERMISSION, "signer"),
        "assert!": (OperationType.CHECK_PERMISSION, "assertion"),
    }

    def to_abstract(self, operations: List[str]) -> List[AbstractOperation]:
        """Convert Move operations to abstract operations."""
        abstract_ops = []

        for i, op in enumerate(operations):
            for pattern, (op_type, target) in self.MOVE_PATTERNS.items():
                if pattern in op:
                    abstract_ops.append(AbstractOperation(
                        operation=op_type,
                        target=target,
                        timing=i,
                    ))
                    break

        return abstract_ops

    def from_abstract(
        self,
        abstract_ops: List[AbstractOperation]
    ) -> Dict[str, Any]:
        """Convert abstract operations to Move-specific checks."""
        checks = []

        for op in abstract_ops:
            if op.operation == OperationType.TRANSFER_VALUE:
                checks.append({
                    "function": "Coin::transfer",
                    "check_capability": True
                })
            elif op.operation == OperationType.READ_STATE:
                checks.append({
                    "function": "borrow_global",
                    "check_exists": True
                })
            elif op.operation == OperationType.WRITE_STATE:
                checks.append({
                    "function": "borrow_global_mut",
                    "check_ownership": True
                })
            elif op.operation == OperationType.CHECK_PERMISSION:
                checks.append({
                    "function": "signer::address_of",
                    "verify_signer": True
                })

        return {
            "chain": "move",
            "checks": checks
        }

    def parse_source(self, source: str) -> List[str]:
        """Parse Move source code for operations."""
        operations = []

        patterns = [
            (r'borrow_global<', "borrow_global"),
            (r'borrow_global_mut<', "borrow_global_mut"),
            (r'move_to\s*\(', "move_to"),
            (r'move_from<', "move_from"),
            (r'Coin::transfer', "Coin::transfer"),
            (r'Coin::value', "Coin::value"),
            (r'Coin::burn', "Coin::burn"),
            (r'Coin::mint', "Coin::mint"),
            (r'signer::address_of', "signer::address_of"),
            (r'assert!\s*\(', "assert!"),
        ]

        for pattern, op_name in patterns:
            if re.search(pattern, source, re.IGNORECASE):
                if op_name not in operations:
                    operations.append(op_name)

        return operations


@dataclass
class TranslatorRegistry:
    """Registry of chain translators."""

    _translators: Dict[Chain, ChainTranslator] = field(default_factory=dict)

    def __post_init__(self):
        # Register default translators
        self.register(EVMTranslator())
        self.register(SolanaTranslator())
        self.register(MoveTranslator())

    def register(self, translator: ChainTranslator):
        """Register a translator for a chain."""
        self._translators[translator.chain] = translator

    def get(self, chain: Chain) -> Optional[ChainTranslator]:
        """Get translator for a chain."""
        return self._translators.get(chain)

    def translate_to_abstract(
        self,
        chain: Chain,
        operations: List[Any]
    ) -> List[AbstractOperation]:
        """Translate chain operations to abstract."""
        translator = self.get(chain)
        if not translator:
            raise ValueError(f"No translator for chain: {chain}")
        return translator.to_abstract(operations)

    def translate_from_abstract(
        self,
        chain: Chain,
        abstract_ops: List[AbstractOperation]
    ) -> Dict[str, Any]:
        """Translate abstract operations to chain-specific pattern."""
        translator = self.get(chain)
        if not translator:
            raise ValueError(f"No translator for chain: {chain}")
        return translator.from_abstract(abstract_ops)

    def cross_translate(
        self,
        source_chain: Chain,
        target_chain: Chain,
        operations: List[Any]
    ) -> Dict[str, Any]:
        """
        Translate operations from one chain to another.

        Goes through abstract layer: source -> abstract -> target
        """
        # Step 1: Source to abstract
        abstract_ops = self.translate_to_abstract(source_chain, operations)

        # Step 2: Abstract to target
        return self.translate_from_abstract(target_chain, abstract_ops)

    @property
    def supported_chains(self) -> List[Chain]:
        """Get list of supported chains."""
        return list(self._translators.keys())


# Global registry instance
TRANSLATOR_REGISTRY = TranslatorRegistry()
